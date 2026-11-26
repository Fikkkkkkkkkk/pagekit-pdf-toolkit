import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'
import type { CompressionLevel } from './types'

export async function compressPdf(file: File, level: CompressionLevel, progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('level', level)
  return (await postPdfWithProgress('/api/compress-pdf', body, progress, signal)).blob
}
