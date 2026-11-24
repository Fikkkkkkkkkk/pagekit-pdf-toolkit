export async function splitPdf(file: File, ranges: string): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('ranges', ranges)

  let response: Response
  try {
    response = await fetch('/api/split-pdf', { method: 'POST', body })
  } catch {
    throw new Error('Could not connect to PageKit. Check that the Flask backend is running, then try again.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: string } | null
    throw new Error(payload?.error || 'The split failed. Check your PDF and page ranges, then try again.')
  }
  return response.blob()
}
