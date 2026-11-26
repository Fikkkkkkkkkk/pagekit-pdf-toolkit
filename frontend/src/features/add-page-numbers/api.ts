import type { NumberPosition } from './types'

export async function addPageNumbers(file: File, position: NumberPosition, start: number): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('position', position)
  body.append('start', String(start))

  let response: Response
  try {
    response = await fetch('/api/add-page-numbers', { method: 'POST', body })
  } catch {
    throw new Error('Could not connect to PageKit. Check that the Flask backend is running, then try again.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: string } | null
    throw new Error(payload?.error || 'Page numbers could not be added. Check your PDF and try again.')
  }
  return response.blob()
}
