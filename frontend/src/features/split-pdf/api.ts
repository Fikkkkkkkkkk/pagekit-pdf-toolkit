import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'

export async function splitPdf(file: File, ranges: string, progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('ranges', ranges)

  return (await postPdfWithProgress('/api/split-pdf', body, progress, signal)).blob
}
