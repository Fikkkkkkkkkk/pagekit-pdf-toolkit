export type CropArea = { left: number; top: number; right: number; bottom: number }

export type PagePreview = {
  pageCount: number
  pageNumber: number
  width: number
  height: number
  thumbnail: string
}

export type CroppedResult = { url: string; name: string; size: number }
