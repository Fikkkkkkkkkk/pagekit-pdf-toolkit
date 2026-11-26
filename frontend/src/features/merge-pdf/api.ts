import type { SelectedPdf } from './types'
import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'

export async function mergePdfs(files: SelectedPdf[], progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  files.forEach(item => body.append('files', item.file))

  return (await postPdfWithProgress('/api/merge-pdf', body, progress, signal)).blob
}
