export type WorkProgress = { phase: string; completed: number; total: number }

export type PdfProgressCallbacks = {
  onUploadProgress: (percent: number | null) => void
  onUploadComplete: () => void
  onWorkProgress: (progress: WorkProgress) => void
}

export type PdfProgressState = {
  stage: 'idle' | 'uploading' | 'processing' | 'complete'
  uploadPercent: number | null
  work: WorkProgress | null
}
