import type { PageItem } from './types'
import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'

export async function organizePages(
  original: File,
  added: File | null,
  pages: PageItem[],
  insertionPosition: number | null,
  progress: PdfProgressCallbacks,
  signal: AbortSignal,
): Promise<Blob> {
  const body = new FormData()
  body.append('original', original)
  if (added) {
    body.append('added', added)
    body.append('insertion_position', String(insertionPosition))
  }
  body.append('order', JSON.stringify(pages.map(({ source, page }) => ({ source, page }))))

  return (await postPdfWithProgress('/api/organize-pages', body, progress, signal)).blob
}
