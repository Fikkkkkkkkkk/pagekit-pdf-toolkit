import type { PagePreview, SignatureAsset } from './types'

export async function renderPage(file: File | Blob, pageNumber: number): Promise<PagePreview> {
  if (file instanceof File) {
    if (!file.name.toLowerCase().endsWith('.pdf')) throw new Error('Choose a .pdf file.')
    if (!file.size || file.size > 25 * 1024 * 1024) throw new Error('Choose a nonempty PDF up to 25 MB.')
  }
  const { getDocument, GlobalWorkerOptions } = await import('pdfjs-dist')
  GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()
  const task = getDocument({ data: await file.arrayBuffer() })
  try {
    const pdf = await task.promise
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
    if (caught instanceof Error && caught.name === 'PasswordException') throw new Error('This PDF is password protected. Choose an unlocked PDF.')
    if (caught instanceof Error && (caught.message.includes('Choose a page') || caught.message.includes('preview'))) throw caught
    throw new Error('This PDF could not be previewed. Choose a readable PDF.')
  } finally {
    await task.destroy()
  }
}

export function canvasAsset(canvas: HTMLCanvasElement): Promise<SignatureAsset> {
  return new Promise((resolve, reject) => canvas.toBlob(blob => {
    if (!blob) { reject(new Error('The signature image could not be created.')); return }
    resolve({ blob, url: URL.createObjectURL(blob), width: canvas.width, height: canvas.height })
  }, 'image/png'))
}

export async function imageAsset(file: File): Promise<SignatureAsset> {
  if (!['image/png', 'image/jpeg'].includes(file.type) || file.size > 10 * 1024 * 1024) {
    throw new Error('Choose a PNG or JPG signature image up to 10 MB.')
  }
  const image = await createImageBitmap(file, { imageOrientation: 'from-image' })
  try {
    if (image.width * image.height > 12_000_000) throw new Error('Choose an image below 12 megapixels.')
    const canvas = document.createElement('canvas')
    canvas.width = image.width
    canvas.height = image.height
    canvas.getContext('2d')?.drawImage(image, 0, 0)
    return await canvasAsset(canvas)
  } finally { image.close() }
}
