import type { RotatePage } from './types'
import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'

export async function rotatePdf(file: File, pages: RotatePage[], progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('rotations', JSON.stringify(pages.map(page => page.rotation)))

  return (await postPdfWithProgress('/api/rotate-pdf', body, progress, signal)).blob
}
