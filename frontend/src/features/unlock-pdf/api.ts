import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'
import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'

export async function unlockPdf(file: File, password: string,
  progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('password', password)
  return (await postPdfWithProgress('/api/unlock-pdf', body, progress, signal)).blob
}
