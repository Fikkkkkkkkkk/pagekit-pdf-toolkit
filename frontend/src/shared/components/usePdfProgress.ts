import { useEffect, useRef, useState } from 'react'
import type { PdfProgressCallbacks, PdfProgressState } from './progressTypes'

const idle: PdfProgressState = { stage: 'idle', uploadPercent: null, work: null }

export function usePdfProgress() {
  const [state, setState] = useState<PdfProgressState>(idle)
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => () => controllerRef.current?.abort(), [])

  async function run<T>(task: (callbacks: PdfProgressCallbacks, signal: AbortSignal) => Promise<T>): Promise<T> {
    if (controllerRef.current) throw new Error('A PDF request is already in progress.')
    const controller = new AbortController()
    controllerRef.current = controller
    setState({ stage: 'uploading', uploadPercent: null, work: null })
    const callbacks: PdfProgressCallbacks = {
      onUploadProgress: uploadPercent => setState(current => ({ ...current, uploadPercent })),
      onUploadComplete: () => setState(current => ({ ...current, stage: 'processing', uploadPercent: 100 })),
      onWorkProgress: work => setState(current => ({ ...current, stage: 'processing', work })),
    }
    try {
      const result = await task(callbacks, controller.signal)
      setState(current => ({ ...current, stage: 'complete' }))
      return result
    } catch (error) {
      setState(idle)
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new Error('Processing was cancelled. You can try again.')
      }
      throw error
    } finally {
      controllerRef.current = null
    }
  }

  function reset() {
    if (!controllerRef.current) setState(idle)
  }

  return { state, run, reset, cancel: () => controllerRef.current?.abort() }
}
