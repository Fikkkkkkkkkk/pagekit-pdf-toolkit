export type NumberPosition = 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right'

export type PdfPreview = {
  pageCount: number
  thumbnail: string
}

export type NumberedResult = {
  url: string
  name: string
  size: number
}
