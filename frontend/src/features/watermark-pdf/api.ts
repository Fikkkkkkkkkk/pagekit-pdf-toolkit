import { postPdfWithProgress } from '../../shared/components/postPdfWithProgress'
import type { PdfProgressCallbacks } from '../../shared/components/progressTypes'
import type { WatermarkOptions } from './types'

export async function watermarkPdf(file: File, options: WatermarkOptions,
  progress: PdfProgressCallbacks, signal: AbortSignal): Promise<Blob> {
  const body = new FormData()
  body.append('file', file)
  body.append('text', options.text)
  body.append('position', options.position)
  body.append('rotation', String(options.rotation))
  body.append('color', options.color)
  body.append('opacity', String(options.opacity))
  body.append('font_family', options.fontFamily)
  body.append('font_size', String(options.fontSize))
  body.append('bold', String(options.bold))
  body.append('italic', String(options.italic))
  body.append('underline', String(options.underline))
  body.append('mosaic', String(options.mosaic))
  body.append('layer', options.layer)
  return (await postPdfWithProgress('/api/watermark-pdf', body, progress, signal)).blob
}
