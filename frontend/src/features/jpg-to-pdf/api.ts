import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'
import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import type { Orientation, PageSize, SelectedImage } from './types'

export async function imagesToPdf(images: SelectedImage[], pageSize: PageSize, orientation: Orientation,
  progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  images.forEach(image => body.append('files', image.file))
  body.append('page_size', pageSize)
  body.append('orientation', orientation)
  return (await postPdfWithProgress('/api/jpg-to-pdf', body, progress, signal)).blob
}
