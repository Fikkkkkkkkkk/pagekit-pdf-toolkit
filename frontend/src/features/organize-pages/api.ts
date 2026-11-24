import type { PageItem } from './types'

export async function organizePages(
  original: File,
  added: File | null,
  pages: PageItem[],
  insertionPosition: number | null,
): Promise<Blob> {
  const body = new FormData()
  body.append('original', original)
  if (added) {
    body.append('added', added)
    body.append('insertion_position', String(insertionPosition))
  }
  body.append('order', JSON.stringify(pages.map(({ source, page }) => ({ source, page }))))

  let response: Response
  try {
    response = await fetch('/api/organize-pages', { method: 'POST', body })
  } catch {
    throw new Error('Could not connect to PageKit. Check that the Flask backend is running, then try again.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: string } | null
    throw new Error(payload?.error || 'The pages could not be organized. Check your PDFs and try again.')
  }
  return response.blob()
}
