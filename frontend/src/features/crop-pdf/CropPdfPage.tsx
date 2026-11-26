import { UsageHint } from '../../shared/components/UsageHint'
import { useEffect, useRef, useState, type ChangeEvent, type FormEvent, type PointerEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { PdfProgress } from '../../shared/components/PdfProgress'
import { usePdfProgress } from '../../shared/components/usePdfProgress'
import { cropPdf } from './api'
import { renderPreview } from './preview'
import type { CropArea, CroppedResult, PagePreview } from './types'
import './crop-pdf.css'

const INITIAL_CROP: CropArea = { left: 0.05, top: 0.05, right: 0.95, bottom: 0.95 }
const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value))

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function pointInPage(event: PointerEvent<HTMLDivElement>) {
  const box = event.currentTarget.getBoundingClientRect()
  return { x: clamp((event.clientX - box.left) / box.width, 0, 1), y: clamp((event.clientY - box.top) / box.height, 0, 1) }
}

export function CropPdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<PagePreview | null>(null)
  const [crop, setCrop] = useState<CropArea>(INITIAL_CROP)
  const [busy, setBusy] = useState(false)
  const [busyMessage, setBusyMessage] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState<CroppedResult | null>(null)
  const resultUrl = useRef<string | null>(null)
  const progress = usePdfProgress()
  const drag = useRef<{ x: number; y: number; previous: CropArea } | null>(null)

  useEffect(() => () => { if (resultUrl.current) URL.revokeObjectURL(resultUrl.current) }, [])

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
    resultUrl.current = null
    setResult(null)
    progress.reset()
  }

  async function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0]
    event.target.value = ''
    if (!chosen) return
    clearResult()
    setFile(null)
    setPreview(null)
    setCrop(INITIAL_CROP)
    setError('')
    setNotice('')
    setBusy(true)
    setBusyMessage('Preparing a page preview…')
    try {
      const nextPreview = await renderPreview(chosen, 1)
      setFile(chosen)
      setPreview(nextPreview)
      setNotice(`${nextPreview.pageCount} ${nextPreview.pageCount === 1 ? 'page' : 'pages'} ready. Select the area to keep.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not open this PDF.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  async function choosePreviewPage(event: ChangeEvent<HTMLSelectElement>) {
    if (!file) return
    const pageNumber = Number(event.target.value)
    clearResult()
    setBusy(true)
    setBusyMessage(`Preparing page ${pageNumber} preview…`)
    setError('')
    setNotice('')
    try {
      setPreview(await renderPreview(file, pageNumber))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not preview that page.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  function startDrag(event: PointerEvent<HTMLDivElement>) {
    if (busy) return
    const point = pointInPage(event)
    drag.current = { ...point, previous: crop }
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function moveDrag(event: PointerEvent<HTMLDivElement>) {
    if (!drag.current) return
    const point = pointInPage(event)
    const { x, y } = drag.current
    setCrop({ left: Math.min(x, point.x), top: Math.min(y, point.y), right: Math.max(x, point.x), bottom: Math.max(y, point.y) })
  }

  function endDrag(event: PointerEvent<HTMLDivElement>) {
    if (!drag.current) return
    const point = pointInPage(event)
    const { x, y, previous } = drag.current
    drag.current = null
    const next = { left: Math.min(x, point.x), top: Math.min(y, point.y), right: Math.max(x, point.x), bottom: Math.max(y, point.y) }
    if (next.right - next.left < 0.02 || next.bottom - next.top < 0.02) {
      setCrop(previous)
      setNotice('Drag across the page to select a larger area, or use the percentage fields.')
    } else {
      clearResult()
      setCrop(next)
      setNotice('Crop area updated. Check the result preview before creating the PDF.')
      setError('')
    }
    event.currentTarget.releasePointerCapture(event.pointerId)
  }

  function cancelDrag() {
    if (!drag.current) return
    setCrop(drag.current.previous)
    drag.current = null
  }

  function setPercent(field: 'left' | 'top' | 'width' | 'height', raw: string) {
    const value = clamp(Number(raw) || 0, 0, 100) / 100
    clearResult()
    setCrop(current => {
      if (field === 'left') return { ...current, left: Math.min(value, current.right - 0.01) }
      if (field === 'top') return { ...current, top: Math.min(value, current.bottom - 0.01) }
      if (field === 'width') return { ...current, right: Math.min(1, current.left + Math.max(0.01, value)) }
      return { ...current, bottom: Math.min(1, current.top + Math.max(0.01, value)) }
    })
    setError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file || !preview) { setError('Choose one PDF to crop.'); return }
    if (crop.right - crop.left < 0.01 || crop.bottom - crop.top < 0.01) { setError('Select a larger crop area.'); return }
    clearResult()
    setBusy(true)
    setBusyMessage('Creating your cropped PDF…')
    setError('')
    setNotice('')
    try {
      const blob = await progress.run((callbacks, signal) => cropPdf(file, crop, callbacks, signal))
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-cropped.pdf', size: blob.size })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The PDF could not be cropped. Try again.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  const width = crop.right - crop.left
  const height = crop.bottom - crop.top

  return <section className="crop-page"><div className="container">
    <a className="crop-back" href="#catalog">← All tools</a>
    <div className="crop-intro"><span className="eyebrow">ORGANIZE YOUR DOCUMENTS</span><h1>Crop PDF<span className="accent-dot">.</span></h1><p>Choose the part of a page you want to keep visible across the whole PDF.</p></div>
    <form onSubmit={handleSubmit}>
      <div className="usage-layout">
        <div className="crop-panel"><div className="crop-section-heading"><span className="crop-step">01</span><div><h2>Choose your PDF</h2><p>Preview a page, then select the area to keep.</p></div></div>
          <label className="crop-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseFile} disabled={busy} /><span className="crop-picker__icon"><Icon name="crop" /></span><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
          {file && preview && <p className="crop-file-label"><strong>{file.name}</strong> · {fileSize(file.size)} · {preview.pageCount} {preview.pageCount === 1 ? 'page' : 'pages'}</p>}
        </div>
        <UsageHint icon="crop" title="Keep the right area" steps={[{ title: 'Pick a sample page', detail: 'Pick a page that shows the area you need.' }, { title: 'Draw the crop', detail: 'Drag a rectangle or refine its percentages.' }, { title: 'Check every page', detail: 'The same relative crop hides outer areas on all pages.' }]} />
      </div>

      {file && preview && <div className="crop-panel"><div className="crop-section-heading"><span className="crop-step">02</span><div><h2>Select the visible area</h2><p>Drag across the page, or enter percentages below. The same relative area will be used on every page.</p></div></div>
        {preview.pageCount > 1 && <label className="crop-page-choice">Page to preview<select value={preview.pageNumber} onChange={choosePreviewPage} disabled={busy}>{Array.from({ length: preview.pageCount }, (_, index) => <option key={index} value={index + 1}>Page {index + 1}</option>)}</select></label>}
        <div className="crop-workspace"><div><strong>Source page {preview.pageNumber}</strong><p>Drag to draw a new crop rectangle.</p><div className="crop-stage" role="img" aria-label={`Page ${preview.pageNumber} with selected crop area`} style={{ width: Math.min(preview.width, 340), aspectRatio: `${preview.width} / ${preview.height}` }} onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={cancelDrag}><img src={preview.thumbnail} alt="" draggable={false} /><span className="crop-selection" style={{ left: `${crop.left * 100}%`, top: `${crop.top * 100}%`, width: `${width * 100}%`, height: `${height * 100}%` }} /></div></div><div><strong>Cropped preview</strong><p>Content outside this view will be hidden in the downloaded PDF.</p>{width >= 0.02 && height >= 0.02 ? <div className="crop-result-preview" style={{ width: preview.width * width, aspectRatio: `${preview.width * width} / ${preview.height * height}` }}><img src={preview.thumbnail} alt={`Approximate cropped preview of page ${preview.pageNumber}`} style={{ width: `${100 / width}%`, height: `${100 / height}%`, left: `${-crop.left / width * 100}%`, top: `${-crop.top / height * 100}%` }} /></div> : <p>Drag farther to select a larger area.</p>}</div></div>
        <fieldset className="crop-percentages"><legend>Fine-tune crop area (percent of visible page)</legend><label>Left edge<input type="number" min="0" max="99" step="1" value={Math.round(crop.left * 100)} onChange={event => setPercent('left', event.target.value)} disabled={busy} />%</label><label>Top edge<input type="number" min="0" max="99" step="1" value={Math.round(crop.top * 100)} onChange={event => setPercent('top', event.target.value)} disabled={busy} />%</label><label>Width<input type="number" min="1" max="100" step="1" value={Math.round(width * 100)} onChange={event => setPercent('width', event.target.value)} disabled={busy} />%</label><label>Height<input type="number" min="1" max="100" step="1" value={Math.round(height * 100)} onChange={event => setPercent('height', event.target.value)} disabled={busy} />%</label></fieldset>
      </div>}

      {busy && progress.state.stage === 'idle' && <p className="crop-status" role="status">{busyMessage}</p>}
      <PdfProgress state={progress.state} onCancel={progress.cancel} />
      {notice && !busy && <p className="crop-status" role="status">{notice}</p>}
      {error && <div className="crop-error" role="alert"><strong>Couldn’t crop this PDF</strong><p>{error}</p></div>}
      {file && preview && <div className="crop-action-panel"><div><strong>Ready to crop your PDF?</strong><p>Cropping hides content outside the selected area. It does not securely erase that content from the PDF.</p></div><button type="submit" disabled={busy}>{busy ? 'Creating PDF…' : 'Create cropped PDF'}</button></div>}
      {result && <div className="crop-success" role="status"><span className="crop-success__icon">✓</span><div><h2>Your PDF is ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download cropped PDF</a></div>}
    </form>
    <p className="crop-privacy">Uploads are removed from temporary server storage after processing. Abandoned files are cleared after 15 minutes at startup or on later requests.</p>
  </div></section>
}
