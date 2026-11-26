import type { CropArea } from './types'
import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'

export async function cropPdf(file: File, crop: CropArea, progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('crop', JSON.stringify(crop))
  return (await postPdfWithProgress('/api/crop-pdf', body, progress, signal)).blob
}
