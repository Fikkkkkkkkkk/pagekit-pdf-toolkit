import type { PagePreview } from './types'

const MAX_FILE_BYTES = 25 * 1024 * 1024

export async function renderPreview(file: File, pageNumber: number): Promise<PagePreview> {
  if (!file.name.toLowerCase().endsWith('.pdf')) throw new Error('Choose a file with a .pdf extension.')
  if (!file.size) throw new Error('This PDF is empty. Choose a readable file.')
  if (file.size > MAX_FILE_BYTES) throw new Error('This PDF is over the 25 MB file limit.')

  const { getDocument, GlobalWorkerOptions } = await import('pdfjs-dist')
  GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()
  const loadingTask = getDocument({ data: await file.arrayBuffer() })
  try {
    const document = await loadingTask.promise
    if (document.numPages < 1) throw new Error('This PDF has no pages to crop.')
    if (pageNumber < 1 || pageNumber > document.numPages) throw new Error('That page is outside this PDF.')
    const page = await document.getPage(pageNumber)
    const unscaled = page.getViewport({ scale: 1 })
    const viewport = page.getViewport({ scale: Math.min(340 / unscaled.width, 440 / unscaled.height) })
    const canvas = window.document.createElement('canvas')
    canvas.width = Math.ceil(viewport.width)
    canvas.height = Math.ceil(viewport.height)
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Page previews are unavailable in this browser.')
    await page.render({ canvas, canvasContext: context, viewport }).promise
    page.cleanup()
    return { pageCount: document.numPages, pageNumber, width: canvas.width, height: canvas.height, thumbnail: canvas.toDataURL('image/png') }
  } catch (caught) {
    if (caught instanceof Error && caught.name === 'PasswordException') {
      throw new Error('This PDF is password protected. Choose an unlocked PDF.')
    }
    if (caught instanceof Error && (caught.message.includes('previews') || caught.message.includes('no pages') || caught.message.includes('outside'))) throw caught
    throw new Error('This PDF could not be previewed. Choose a readable PDF and try again.')
  } finally {
    await loadingTask.destroy()
  }
}
