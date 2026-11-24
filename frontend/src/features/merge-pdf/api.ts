import type { SelectedPdf } from './types'

export async function mergePdfs(files: SelectedPdf[]): Promise<Blob> {
  const body = new FormData()
  files.forEach(item => body.append('files', item.file))

  let response: Response
  try {
    response = await fetch('/api/merge-pdf', { method: 'POST', body })
  } catch {
    throw new Error('Could not connect to PageKit. Check that the Flask backend is running, then try again.')
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: string } | null
    throw new Error(payload?.error || 'The merge failed. Check your PDFs and try again.')
  }
  return response.blob()
}
