export type WatermarkPosition =
  | 'top-left' | 'top-center' | 'top-right'
  | 'middle-left' | 'middle-center' | 'middle-right'
  | 'bottom-left' | 'bottom-center' | 'bottom-right'

export type WatermarkOptions = {
  text: string
  position: WatermarkPosition
  rotation: number
  color: string
  opacity: number
  fontFamily: 'helvetica' | 'times' | 'courier'
  fontSize: number
  bold: boolean
  italic: boolean
  underline: boolean
  mosaic: boolean
  layer: 'over' | 'behind'
}

export type PagePreview = { pageCount: number; image: string; width: number; height: number }
export type WatermarkedResult = { blob: Blob; url: string; name: string; size: number }
