import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'
import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'

export async function packageJpgs(pages: File[], progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  pages.forEach(page => body.append('pages', page))
  return (await postPdfWithProgress('/api/pdf-to-jpg', body, progress, signal)).blob
}
