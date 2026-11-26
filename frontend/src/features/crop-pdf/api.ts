import type { CropArea } from './types'

export async function cropPdf(file: File, crop: CropArea): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('crop', JSON.stringify(crop))
  let response: Response
  try {
    response = await fetch('/api/crop-pdf', { method: 'POST', body })
  } catch {
    throw new Error('Could not connect to PageKit. Check that the Flask backend is running, then try again.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: string } | null
    throw new Error(payload?.error || 'The PDF could not be cropped. Check your file and try again.')
  }
  return response.blob()
}
