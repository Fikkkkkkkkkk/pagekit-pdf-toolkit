import type { PdfProgressCallbacks, WorkProgress } from './progressTypes'

export type PdfResponse = { blob: Blob; disposition: string }

function wait(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve() }, 300)
    const abort = () => { clearTimeout(timer); reject(new DOMException('Cancelled', 'AbortError')) }
    signal.addEventListener('abort', abort, { once: true })
    if (signal.aborted) abort()
  })
}

export async function postPdfWithProgress(
  url: string, body: FormData, callbacks: PdfProgressCallbacks, signal: AbortSignal,
): Promise<PdfResponse> {
  const created = await fetch('/api/progress', { method: 'POST', signal })
  if (!created.ok) throw new Error('Could not start progress tracking. Try again.')
  const { id } = await created.json() as { id: string }
  let finished = false

  async function poll() {
    while (!finished && !signal.aborted) {
      try {
        const response = await fetch(`/api/progress/${id}`, { cache: 'no-store', signal })
        if (response.ok) {
          const update = await response.json() as WorkProgress
          if (!finished) callbacks.onWorkProgress(update)
        }
      } catch {
        if (signal.aborted) return
      }
      if (!finished) await wait(signal).catch(() => undefined)
    }
  }

  try {
    return await new Promise<PdfResponse>((resolve, reject) => {
      const request = new XMLHttpRequest()
      request.open('POST', url)
      request.setRequestHeader('X-PageKit-Progress-ID', id)
      request.responseType = 'blob'
      const abort = () => request.abort()
      const cleanup = () => { finished = true; signal.removeEventListener('abort', abort) }
      signal.addEventListener('abort', abort, { once: true })
      request.upload.addEventListener('progress', event => callbacks.onUploadProgress(
        event.lengthComputable && event.total > 0
          ? Math.min(99, Math.floor(event.loaded / event.total * 100)) : null,
      ))
      request.upload.addEventListener('load', () => { callbacks.onUploadComplete(); void poll() })
      request.addEventListener('load', async () => {
        cleanup()
        if (request.status >= 200 && request.status < 300) {
          resolve({ blob: request.response as Blob, disposition: request.getResponseHeader('Content-Disposition') || '' })
          return
        }
        let message = 'The PDF could not be processed. Check your files and try again.'
        try {
          const payload = JSON.parse(await (request.response as Blob).text()) as { error?: string }
          if (payload.error) message = payload.error
        } catch { /* Keep the fallback for non-JSON errors. */ }
        reject(new Error(message))
      })
      request.addEventListener('error', () => {
        cleanup()
        reject(new Error('Could not connect to PageKit. Check that the Flask backend is running, then try again.'))
      })
      request.addEventListener('abort', () => {
        cleanup()
        reject(new DOMException('Cancelled', 'AbortError'))
      })
      if (signal.aborted) { cleanup(); reject(new DOMException('Cancelled', 'AbortError')); return }
      request.send(body)
    })
  } finally {
    finished = true
    await fetch(`/api/progress/${id}`, { method: 'DELETE' }).catch(() => undefined)
  }
}
