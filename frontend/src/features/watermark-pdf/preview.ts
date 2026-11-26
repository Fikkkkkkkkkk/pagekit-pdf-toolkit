import type { PagePreview } from './types'

const MAX_FILE_BYTES = 25 * 1024 * 1024

export async function renderPage(file: File | Blob, pageNumber: number): Promise<PagePreview> {
  if (file instanceof File) {
    if (!file.name.toLowerCase().endsWith('.pdf')) throw new Error('Choose a file with a .pdf extension.')
    if (!file.size) throw new Error('This PDF is empty. Choose a readable file.')
    if (file.size > MAX_FILE_BYTES) throw new Error('This PDF is over the 25 MB limit.')
  }
  const { getDocument, GlobalWorkerOptions } = await import('pdfjs-dist')
  GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()
  const task = getDocument({ data: await file.arrayBuffer() })
  try {
    const pdf = await task.promise
    if (pdf.numPages < 1) throw new Error('This PDF has no pages.')
    if (pageNumber < 1 || pageNumber > pdf.numPages) throw new Error('Choose a page in this PDF.')
    const page = await pdf.getPage(pageNumber)
    const unscaled = page.getViewport({ scale: 1 })
    const viewport = page.getViewport({ scale: Math.min(1100 / unscaled.width, 1400 / unscaled.height) })
    const canvas = document.createElement('canvas')
    canvas.width = Math.ceil(viewport.width)
    canvas.height = Math.ceil(viewport.height)
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Page previews are unavailable in this browser.')
    await page.render({ canvas, canvasContext: context, viewport }).promise
    page.cleanup()
    return { pageCount: pdf.numPages, image: canvas.toDataURL('image/png'), width: unscaled.width, height: unscaled.height }
  } catch (caught) {
    if (caught instanceof Error && caught.name === 'PasswordException') {
      throw new Error('This PDF is password protected. Choose an unlocked PDF.')
    }
    if (caught instanceof Error && (caught.message.includes('preview') || caught.message.includes('no pages') || caught.message.includes('Choose a page'))) throw caught
    throw new Error('This PDF could not be previewed. Choose a readable PDF and try again.')
  } finally {
    await task.destroy()
  }
}
