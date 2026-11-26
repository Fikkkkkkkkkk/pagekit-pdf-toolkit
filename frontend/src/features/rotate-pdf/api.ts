import type { RotatePage } from './types'

export async function rotatePdf(file: File, pages: RotatePage[]): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('rotations', JSON.stringify(pages.map(page => page.rotation)))

  let response: Response
  try {
    response = await fetch('/api/rotate-pdf', { method: 'POST', body })
  } catch {
    throw new Error('Could not connect to PageKit. Check that the Flask backend is running, then try again.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: string } | null
    throw new Error(payload?.error || 'The PDF could not be rotated. Check your file and try again.')
  }
  return response.blob()
}
