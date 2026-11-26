import type { NumberPosition } from './types'
import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'

export async function addPageNumbers(file: File, position: NumberPosition, start: number, progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('position', position)
  body.append('start', String(start))

  return (await postPdfWithProgress('/api/add-page-numbers', body, progress, signal)).blob
}
