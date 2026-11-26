import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'

export async function protectPdf(file: File, password: string, confirmation: string,
  progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('password', password)
  body.append('confirmation', confirmation)
  return (await postPdfWithProgress('/api/protect-pdf', body, progress, signal)).blob
}
