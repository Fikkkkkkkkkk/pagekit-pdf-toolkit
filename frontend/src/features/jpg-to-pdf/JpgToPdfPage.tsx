import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { PdfProgress } from '../../shared/components/PdfProgress'
import { usePdfProgress } from '../../shared/components/usePdfProgress'
import { imagesToPdf } from './api'
import type { ImagePdfResult, Orientation, PageSize, SelectedImage } from './types'
import './jpg-to-pdf.css'

const MAX_FILES = 20
const MAX_FILE_BYTES = 25 * 1024 * 1024
const MAX_TOTAL_BYTES = 100 * 1024 * 1024
const allowed = /\.(jpe?g|png)$/i
const pageSizes: { value: PageSize; title: string; detail: string }[] = [
  { value: 'a4', title: 'A4', detail: 'For assignments and notes' },
  { value: 'letter', title: 'Letter', detail: 'For US-size documents' },
  { value: 'fit', title: 'Fit to image', detail: 'One page per image shape' },
]

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function JpgToPdfPage() {
  const [images, setImages] = useState<SelectedImage[]>([])
  const imagesRef = useRef<SelectedImage[]>([])
  imagesRef.current = images
  const [pageSize, setPageSize] = useState<PageSize>('a4')
  const [orientation, setOrientation] = useState<Orientation>('portrait')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ImagePdfResult | null>(null)
  const resultUrl = useRef<string | null>(null)
  const progress = usePdfProgress()

  useEffect(() => () => {
    imagesRef.current.forEach(image => URL.revokeObjectURL(image.url))
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
  }, [])

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
    resultUrl.current = null
    setResult(null)
    progress.reset()
  }

  function addImages(event: ChangeEvent<HTMLInputElement>) {
    const chosen = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (!chosen.length) return
    if (images.length + chosen.length > MAX_FILES) { setError(`Choose no more than ${MAX_FILES} images.`); return }
    const invalid = chosen.find(file => !allowed.test(file.name))
    if (invalid) { setError(`“${invalid.name}” must be a JPG or PNG image.`); return }
    const empty = chosen.find(file => !file.size)
    if (empty) { setError(`“${empty.name}” is empty. Choose a readable image.`); return }
    const large = chosen.find(file => file.size > MAX_FILE_BYTES)
    if (large) { setError(`“${large.name}” is over the 25 MB limit.`); return }
    if (images.reduce((sum, item) => sum + item.file.size, 0) + chosen.reduce((sum, item) => sum + item.size, 0) > MAX_TOTAL_BYTES) {
      setError('The selected images exceed the 100 MB total limit. Remove an image and try again.'); return
    }
    clearResult()
    setError('')
    setImages(current => [...current, ...chosen.map(file => ({ id: crypto.randomUUID(), file, url: URL.createObjectURL(file) }))])
  }

  function reorder(from: number, to: number) {
    if (from === to || from < 0 || to < 0 || from >= images.length || to >= images.length) return
    const updated = [...images]
    updated.splice(to, 0, ...updated.splice(from, 1))
    clearResult()
    setImages(updated)
    setError('')
  }

  function remove(id: string) {
    const removed = images.find(item => item.id === id)
    if (removed) URL.revokeObjectURL(removed.url)
    clearResult()
    setImages(images.filter(item => item.id !== id))
    setError('')
  }

  function dropImage(event: DragEvent<HTMLLIElement>, to: number) {
    event.preventDefault()
    if (busy) return
    const source = event.dataTransfer.getData('application/x-pagekit-image-index')
    if (!source) return
    const from = Number(source)
    if (Number.isInteger(from)) reorder(from, to)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    if (!images.length) { setError('Choose at least one JPG or PNG image.'); return }
    clearResult()
    setError('')
    setBusy(true)
    try {
      const blob = await progress.run((callbacks, signal) => imagesToPdf(images, pageSize, orientation, callbacks, signal))
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-images.pdf', size: blob.size })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The images could not be combined. Check them and try again.')
    } finally {
      setBusy(false)
    }
  }

  return <section className="jpg-page"><div className="container">
    <a className="jpg-back" href="#catalog">← All tools</a>
    <div className="jpg-intro"><span className="eyebrow">CONVERT YOUR FILES</span><h1>JPG to PDF<span className="accent-dot">.</span></h1><p>Turn JPG and PNG images into one PDF in the order you choose.</p></div>
    <form onSubmit={handleSubmit}>
      <div className="jpg-panel"><div className="jpg-heading"><span className="jpg-step">01</span><div><h2>Choose your images</h2><p>Add up to 20 JPG or PNG images. They become PDF pages from first to last.</p></div></div>
        <label className="jpg-picker"><input type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" multiple onChange={addImages} disabled={busy} /><span className="jpg-picker__icon"><Icon name="image" /></span><strong>{images.length ? 'Add more images' : 'Choose JPG or PNG images'}</strong><span>Up to 20 files · 25 MB each · 100 MB total</span></label>
      </div>

      <div className="jpg-panel"><div className="jpg-heading"><span className="jpg-step">02</span><div><h2>Review page order</h2><p>Drag images into place, or use the move buttons. Remove anything you do not need.</p></div></div>
        {images.length ? <ol className="jpg-images">{images.map((item, index) => <li key={item.id} className="jpg-image" draggable={!busy} onDragStart={event => { event.dataTransfer.effectAllowed = 'move'; event.dataTransfer.setData('application/x-pagekit-image-index', String(index)) }} onDragOver={event => event.preventDefault()} onDrop={event => dropImage(event, index)}><span className="jpg-image__number">{index + 1}</span><div className="jpg-image__thumb"><img src={item.url} alt={`Preview of ${item.file.name}`} /></div><div className="jpg-image__details"><strong title={item.file.name}>{item.file.name}</strong><small>{fileSize(item.file.size)}</small></div><div className="jpg-image__actions"><button type="button" onClick={() => reorder(index, index - 1)} disabled={busy || index === 0} aria-label={`Move ${item.file.name} up`}>↑</button><button type="button" onClick={() => reorder(index, index + 1)} disabled={busy || index === images.length - 1} aria-label={`Move ${item.file.name} down`}>↓</button><button type="button" onClick={() => remove(item.id)} disabled={busy} aria-label={`Remove ${item.file.name}`}>×</button></div></li>)}</ol> : <div className="jpg-empty"><Icon name="image" /><p>Image previews will appear here so you can check their order.</p></div>}
      </div>

      <div className="jpg-panel"><div className="jpg-heading"><span className="jpg-step">03</span><div><h2>Choose page settings</h2><p>Each image will fill as much of its page as possible without stretching.</p></div></div>
        <fieldset className="jpg-options"><legend>Page size</legend><div className="jpg-sizes">{pageSizes.map(item => <label key={item.value} className={pageSize === item.value ? 'selected' : ''}><input type="radio" name="page-size" value={item.value} checked={pageSize === item.value} onChange={() => { clearResult(); setPageSize(item.value) }} disabled={busy} /><strong>{item.title}</strong><span>{item.detail}</span></label>)}</div></fieldset>
        <fieldset className="jpg-options"><legend>Orientation</legend><div className="jpg-orientations"><label className={orientation === 'portrait' ? 'selected' : ''}><input type="radio" name="orientation" checked={orientation === 'portrait'} onChange={() => { clearResult(); setOrientation('portrait') }} disabled={busy} /> Portrait</label><label className={orientation === 'landscape' ? 'selected' : ''}><input type="radio" name="orientation" checked={orientation === 'landscape'} onChange={() => { clearResult(); setOrientation('landscape') }} disabled={busy} /> Landscape</label></div></fieldset>
        <p className="jpg-note">A4 and Letter keep images upright with white margins. Fit to image uses each image’s shape and rotates it when needed to match your chosen orientation. Transparent PNG areas become white.</p>
      </div>

      <PdfProgress state={progress.state} onCancel={progress.cancel} />
      {error && <div className="jpg-error" role="alert"><strong>Could not create this PDF</strong><p>{error}</p></div>}
      <div className="jpg-action"><div><strong>{images.length ? `${images.length} ${images.length === 1 ? 'image' : 'images'} ready` : 'Add images to begin'}</strong><p>Page order follows the list above. Your original images stay unchanged.</p></div><button type="submit" disabled={busy || !images.length}>{busy ? 'Creating PDF…' : 'Create PDF'}</button></div>
      {result && <div className="jpg-result" role="status"><span aria-hidden="true">✓</span><div><h2>Your PDF is ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download PDF</a></div>}
    </form><p className="jpg-privacy">Uploads are removed from temporary server storage after processing. Abandoned request folders are cleared after 15 minutes at startup or on later requests.</p>
  </div></section>
}
