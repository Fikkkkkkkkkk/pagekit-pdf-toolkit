export type CompressionLevel = 'gentle' | 'balanced' | 'strong'

export type PdfPreview = { pageCount: number; thumbnail: string }

export type CompressionResult = {
  url: string
  name: string
  originalSize: number
  outputSize: number
}
