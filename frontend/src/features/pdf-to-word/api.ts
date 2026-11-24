export async function convertPdfToWord(file: File): Promise<{ blob: Blob; name: string }> {
  const body = new FormData()
  body.append('file', file)

  let response: Response
  try {
    response = await fetch('/api/pdf-to-word', { method: 'POST', body })
  } catch {
    throw new Error('Could not connect to PageKit. Check that the Flask backend is running, then try again.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: string } | null
    throw new Error(payload?.error || 'The PDF could not be converted. Check the file and try again.')
  }
  const disposition = response.headers.get('Content-Disposition') || ''
  const name = /filename="?([^";]+)"?/.exec(disposition)?.[1] || `PageKit-converted-${Date.now()}.docx`
  return { blob: await response.blob(), name }
}
