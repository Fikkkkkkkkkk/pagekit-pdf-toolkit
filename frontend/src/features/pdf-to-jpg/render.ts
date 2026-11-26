import type { JpgQuality, PageThumbnail, PageProgress } from './types'
import type { PDFPageProxy } from 'pdfjs-dist'

const MAX_FILE_BYTES = 25 * 1024 * 1024
const MAX_JPG_BYTES = 25 * 1024 * 1024
const MAX_TOTAL_BYTES = 100 * 1024 * 1024
const jpegQuality: Record<JpgQuality, number> = { compact: 0.65, balanced: 0.82, high: 0.95 }

function cancelled(signal: AbortSignal) {
  if (signal.aborted) throw new DOMException('Cancelled', 'AbortError')
}

async function openPdf(file: File) {
  if (!file.name.toLowerCase().endsWith('.pdf')) throw new Error('Choose a file with a .pdf extension.')
  if (!file.size) throw new Error('This PDF is empty. Choose a readable file.')
  if (file.size > MAX_FILE_BYTES) throw new Error('This PDF is over the 25 MB limit.')
  const { getDocument, GlobalWorkerOptions } = await import('pdfjs-dist')
  GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()
  const task = getDocument({ data: await file.arrayBuffer() })
  return task
}

async function renderCanvas(page: PDFPageProxy, maxWidth: number, maxHeight: number, signal: AbortSignal): Promise<HTMLCanvasElement> {
  const unscaled = page.getViewport({ scale: 1 })
  const viewport = page.getViewport({ scale: Math.min(2, maxWidth / unscaled.width, maxHeight / unscaled.height) })
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.ceil(viewport.width))
  canvas.height = Math.max(1, Math.ceil(viewport.height))
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Page rendering is unavailable in this browser.')
  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, canvas.width, canvas.height)
  const renderTask = page.render({ canvas, canvasContext: context, viewport, background: '#ffffff' })
  const abort = () => renderTask.cancel()
  signal.addEventListener('abort', abort, { once: true })
  try {
    await renderTask.promise
    cancelled(signal)
    return canvas
  } finally {
    signal.removeEventListener('abort', abort)
    page.cleanup()
  }
}

function renderError(caught: unknown, signal: AbortSignal): Error {
  if (signal.aborted) return new Error('Conversion was cancelled. You can try again.')
  if (caught instanceof Error && caught.name === 'PasswordException') return new Error('This PDF is password protected. Choose an unlocked PDF.')
  if (caught instanceof Error && (caught.message.includes('25 MB') || caught.message.includes('extension') || caught.message.includes('empty') || caught.message.includes('no pages') || caught.message.includes('rendering') || caught.message.includes('converted JPG'))) return caught
  return new Error('This PDF could not be rendered. Choose a readable PDF and try again.')
}

export async function previewPages(file: File, onProgress: (progress: PageProgress) => void,
  signal: AbortSignal): Promise<PageThumbnail[]> {
  const task = await openPdf(file)
  try {
    cancelled(signal)
    const pdf = await task.promise
    if (pdf.numPages < 1) throw new Error('This PDF has no pages to convert.')
    const thumbnails: PageThumbnail[] = []
    onProgress({ completed: 0, total: pdf.numPages })
    for (let number = 1; number <= pdf.numPages; number += 1) {
      cancelled(signal)
      const page = await pdf.getPage(number)
      const canvas = await renderCanvas(page, 170, 210, signal)
      thumbnails.push({ number, image: canvas.toDataURL('image/png') })
      canvas.width = 0
      canvas.height = 0
      onProgress({ completed: number, total: pdf.numPages })
    }
    return thumbnails
  } catch (caught) {
    throw renderError(caught, signal)
  } finally {
    await task.destroy()
  }
}

export async function convertPages(file: File, quality: JpgQuality,
  onProgress: (progress: PageProgress) => void, signal: AbortSignal): Promise<File[]> {
  const task = await openPdf(file)
  try {
    cancelled(signal)
    const pdf = await task.promise
    if (pdf.numPages < 1) throw new Error('This PDF has no pages to convert.')
    const pages: File[] = []
    const digits = Math.max(3, String(pdf.numPages).length)
    let totalBytes = 0
    onProgress({ completed: 0, total: pdf.numPages })
    for (let number = 1; number <= pdf.numPages; number += 1) {
      cancelled(signal)
      const page = await pdf.getPage(number)
      const canvas = await renderCanvas(page, 2400, 2400, signal)
      const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('This page could not be converted to a JPG.')), 'image/jpeg', jpegQuality[quality]))
      canvas.width = 0
      canvas.height = 0
      cancelled(signal)
      if (blob.size > MAX_JPG_BYTES) throw new Error(`Page ${number} produced a JPG over 25 MB. Choose a lower quality.`)
      totalBytes += blob.size
      if (totalBytes > MAX_TOTAL_BYTES) throw new Error('The converted JPGs exceed 100 MB. Choose a lower quality.')
      pages.push(new File([blob], `page-${String(number).padStart(digits, '0')}.jpg`, { type: 'image/jpeg' }))
      onProgress({ completed: number, total: pdf.numPages })
    }
    cancelled(signal)
    return pages
  } catch (caught) {
    throw renderError(caught, signal)
  } finally {
    await task.destroy()
  }
}
