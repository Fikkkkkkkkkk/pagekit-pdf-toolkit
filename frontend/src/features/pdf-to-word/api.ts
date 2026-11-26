import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'

export async function convertPdfToWord(file: File, progress: PdfProgressCallbacks, signal: AbortSignal): Promise<{ blob: Blob; name: string }> {
  const body = new FormData()
  body.append('file', file)

  const { blob, disposition } = await postPdfWithProgress('/api/pdf-to-word', body, progress, signal)
  const name = /filename="?([^";]+)"?/.exec(disposition)?.[1] || `PageKit-converted-${Date.now()}.docx`
  return { blob, name }
}
