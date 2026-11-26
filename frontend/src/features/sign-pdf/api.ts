import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'
import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import type { Placement } from './types'

export async function signPdf(file: File, signature: Blob, placements: Placement[],
  callbacks: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('signature', signature, 'signature.png')
  body.append('placements', JSON.stringify(placements))
  return (await postPdfWithProgress('/api/sign-pdf', body, callbacks, signal)).blob
}
