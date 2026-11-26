import { UsageHint } from '../../shared/components/UsageHint'
import { useEffect, useRef, useState, type ChangeEvent, type CSSProperties, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { PdfProgress } from '../../shared/components/PdfProgress'
import { usePdfProgress } from '../../shared/components/usePdfProgress'
import { watermarkPdf } from './api'
import { renderPage } from './preview'
import type { PagePreview, WatermarkOptions, WatermarkPosition, WatermarkedResult } from './types'
import './watermark-pdf.css'

const positions: { value: WatermarkPosition; label: string }[] = [
  { value: 'top-left', label: 'Top left' }, { value: 'top-center', label: 'Top center' }, { value: 'top-right', label: 'Top right' },
  { value: 'middle-left', label: 'Middle left' }, { value: 'middle-center', label: 'Center' }, { value: 'middle-right', label: 'Middle right' },
  { value: 'bottom-left', label: 'Bottom left' }, { value: 'bottom-center', label: 'Bottom center' }, { value: 'bottom-right', label: 'Bottom right' },
]
const initialOptions: WatermarkOptions = {
  text: '', position: 'middle-center', rotation: -30, color: '#5964a8', opacity: 30,
  fontFamily: 'helvetica', fontSize: 36, bold: false, italic: false, underline: false,
  mosaic: false, layer: 'over',
}
const fontStyles = { helvetica: 'Arial, sans-serif', times: '"Times New Roman", serif', courier: '"Courier New", monospace' }
const widthFactors = { helvetica: 0.52, times: 0.49, courier: 0.6 }
const mosaicPoints = [13, 38, 63, 88].flatMap(top => [16, 50, 84].map(left => ({ left, top, anchor: '-50%' })))

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(2)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function ApproximateOverlay({ options, preview }: { options: WatermarkOptions; preview: PagePreview }) {
  const [vertical, horizontal] = options.position.split('-') as ['top' | 'middle' | 'bottom', 'left' | 'center' | 'right']
  const points = options.mosaic ? mosaicPoints : [{
    left: { left: 16, center: 50, right: 84 }[horizontal],
    top: { top: 16, middle: 50, bottom: 84 }[vertical],
    anchor: { left: '0%', center: '-50%', right: '-100%' }[horizontal],
  }]
  const label = options.text || 'Your watermark'
  const maxWidth = options.mosaic ? 0.27 : 0.82
  const effectiveSize = Math.min(options.fontSize, preview.width * maxWidth / Math.max(label.length * widthFactors[options.fontFamily], 1))
  const common: CSSProperties = {
    color: options.color, opacity: options.opacity / 100,
    fontFamily: fontStyles[options.fontFamily], fontSize: `${effectiveSize / preview.width * 100}cqw`,
    fontWeight: options.bold ? 700 : 400, fontStyle: options.italic ? 'italic' : 'normal',
    textDecoration: options.underline ? 'underline' : 'none',
    mixBlendMode: options.layer === 'behind' ? 'multiply' : 'normal',
  }
  return <>{points.map((point, index) => <span key={index} className="watermark-preview__overlay" aria-hidden="true" style={{ ...common, left: `${point.left}%`, top: `${point.top}%`, transform: `rotate(${-options.rotation}deg) translate(${point.anchor}, -50%)` }}>{label}</span>)}</>
}

export function WatermarkPdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [source, setSource] = useState<PagePreview | null>(null)
  const [options, setOptions] = useState<WatermarkOptions>(initialOptions)
  const [result, setResult] = useState<WatermarkedResult | null>(null)
  const [resultPreview, setResultPreview] = useState<PagePreview | null>(null)
  const [previewPage, setPreviewPage] = useState(1)
  const [busy, setBusy] = useState(false)
  const [previewBusy, setPreviewBusy] = useState(false)
  const [error, setError] = useState('')
  const [previewError, setPreviewError] = useState('')
  const resultUrl = useRef<string | null>(null)
  const progress = usePdfProgress()

  useEffect(() => () => { if (resultUrl.current) URL.revokeObjectURL(resultUrl.current) }, [])

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
    resultUrl.current = null
    setResult(null)
    setResultPreview(null)
    setPreviewPage(1)
    setPreviewError('')
    progress.reset()
  }

  async function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0]
    event.target.value = ''
    if (!chosen) return
    clearResult()
    setFile(null)
    setSource(null)
    setError('')
    setBusy(true)
    try {
      const preview = await renderPage(chosen, 1)
      setFile(chosen)
      setSource(preview)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'This PDF could not be opened.')
    } finally {
      setBusy(false)
    }
  }

  function updateOptions(patch: Partial<WatermarkOptions>) {
    clearResult()
    setOptions(current => ({ ...current, ...patch }))
    setError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || !file) return
    if (!options.text.trim()) { setError('Enter text for the watermark.'); return }
    if (options.text.length > 80) { setError('Use up to 80 characters of watermark text.'); return }
    if (!Number.isInteger(options.fontSize) || options.fontSize < 8 || options.fontSize > 72) { setError('Choose a font size from 8 to 72 points.'); return }
    clearResult()
    setError('')
    setBusy(true)
    try {
      const blob = await progress.run((callbacks, signal) => watermarkPdf(file, options, callbacks, signal))
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ blob, url, name: 'PageKit-watermarked.pdf', size: blob.size })
      setPreviewBusy(true)
      try {
        setResultPreview(await renderPage(blob, 1))
      } catch {
        setPreviewError('The PDF is ready, but its preview could not be shown here. Open the downloaded copy to inspect it.')
      } finally {
        setPreviewBusy(false)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The watermark could not be added. Try again.')
    } finally {
      setBusy(false)
    }
  }

  async function showPage(pageNumber: number) {
    if (!result || previewBusy) return
    setPreviewPage(pageNumber)
    setResultPreview(null)
    setPreviewError('')
    setPreviewBusy(true)
    try {
      setResultPreview(await renderPage(result.blob, pageNumber))
    } catch {
      setPreviewError('This page could not be previewed. You can still download the PDF.')
    } finally {
      setPreviewBusy(false)
    }
  }

  return <section className="watermark-page"><div className="container">
    <a className="watermark-back" href="#catalog">← All tools</a>
    <div className="watermark-intro"><span className="eyebrow">EDIT YOUR DOCUMENTS</span><h1>Watermark PDF<span className="accent-dot">.</span></h1><p>Place a customizable text mark on every page of a new PDF copy.</p></div>
    <form onSubmit={handleSubmit}>
      <div className="usage-layout">
        <div className="watermark-panel"><div className="watermark-heading"><span className="watermark-step">01</span><div><h2>Choose your PDF</h2><p>Upload one unlocked PDF. Your original stays unchanged.</p></div></div>
          <label className="watermark-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseFile} disabled={busy} /><span className="watermark-picker__icon"><Icon name="watermark" /></span><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
          {file && source && <p className="watermark-file"><strong>{file.name}</strong> · {fileSize(file.size)} · {source.pageCount} {source.pageCount === 1 ? 'page' : 'pages'}</p>}
        </div>
        <UsageHint icon="watermark" title="Make the mark fit" steps={[{ title: 'Preview the source page', detail: 'Preview the first page of your document.' }, { title: 'Design the text', detail: 'Set position, style, opacity, and layering.' }, { title: 'Inspect the result', detail: 'The live view is approximate; review the generated PDF.' }]} />
      </div>

      {file && source && <div className="watermark-panel"><div className="watermark-heading"><span className="watermark-step">02</span><div><h2>Design your watermark</h2><p>The same settings apply to every page. Changes appear in the approximate preview.</p></div></div>
        <div className="watermark-editor">
          <div className="watermark-controls">
            <label className="watermark-text">Watermark text<input type="text" value={options.text} onChange={event => updateOptions({ text: event.target.value })} maxLength={80} placeholder="Type your watermark, e.g. DRAFT" disabled={busy} required /><small>One line, up to 80 Western European characters.</small></label>
            <div className="watermark-font-row"><label>Font family<select value={options.fontFamily} onChange={event => updateOptions({ fontFamily: event.target.value as WatermarkOptions['fontFamily'] })} disabled={busy}><option value="helvetica">Helvetica</option><option value="times">Times</option><option value="courier">Courier</option></select></label><label>Size (pt)<input type="number" min="8" max="72" step="1" value={options.fontSize} onChange={event => updateOptions({ fontSize: Number(event.target.value) })} disabled={busy} required /></label></div>
            <div className="watermark-style" role="group" aria-label="Text style"><button type="button" aria-label="Bold" aria-pressed={options.bold} className={options.bold ? 'selected' : ''} onClick={() => updateOptions({ bold: !options.bold })} disabled={busy}><strong>B</strong></button><button type="button" aria-label="Italic" aria-pressed={options.italic} className={options.italic ? 'selected' : ''} onClick={() => updateOptions({ italic: !options.italic })} disabled={busy}><em>I</em></button><button type="button" aria-label="Underline" aria-pressed={options.underline} className={options.underline ? 'selected' : ''} onClick={() => updateOptions({ underline: !options.underline })} disabled={busy}><u>U</u></button></div>
            <fieldset className="watermark-position-field"><legend>Position</legend><div className="watermark-position-grid" role="group" aria-label="Watermark position">{positions.map(item => <button key={item.value} type="button" aria-label={item.label} aria-pressed={options.position === item.value && !options.mosaic} className={options.position === item.value && !options.mosaic ? 'selected' : ''} onClick={() => updateOptions({ position: item.value })} disabled={busy || options.mosaic}><span aria-hidden="true" /></button>)}</div></fieldset>
            <label className="watermark-check"><input type="checkbox" checked={options.mosaic} onChange={event => updateOptions({ mosaic: event.target.checked })} disabled={busy} /><span><strong>Mosaic</strong><small>Repeat the watermark across the page. The single-position grid is not used.</small></span></label>
            <div className="watermark-tuning"><label>Rotation <span>{options.rotation}°</span><input type="range" min="-180" max="180" step="5" value={options.rotation} onChange={event => updateOptions({ rotation: Number(event.target.value) })} disabled={busy} /></label><label>Color<input type="color" value={options.color} onChange={event => updateOptions({ color: event.target.value })} disabled={busy} /></label><label>Opacity <span>{options.opacity}%</span><input type="range" min="1" max="100" value={options.opacity} onChange={event => updateOptions({ opacity: Number(event.target.value) })} disabled={busy} /></label></div>
            <fieldset className="watermark-layer"><legend>Layer</legend><div><label><input type="radio" name="layer" checked={options.layer === 'over'} onChange={() => updateOptions({ layer: 'over' })} disabled={busy} /> Over content</label><label><input type="radio" name="layer" checked={options.layer === 'behind'} onChange={() => updateOptions({ layer: 'behind' })} disabled={busy} /> Behind content</label></div><p>Behind may be hidden by opaque page backgrounds. The live preview approximates layering; check the generated PDF.</p></fieldset>
          </div>
          <div className="watermark-preview"><div className="watermark-preview__heading"><strong>{result ? 'Actual generated PDF preview' : 'Approximate live preview'}</strong>{result ? <label>Page <select value={previewPage} onChange={event => void showPage(Number(event.target.value))} disabled={previewBusy}>{Array.from({ length: resultPreview?.pageCount ?? source.pageCount }, (_, index) => <option value={index + 1} key={index}>{index + 1}</option>)}</select> of {resultPreview?.pageCount ?? source.pageCount}</label> : <p>First source page. Placement and layering are approximate; create the PDF to inspect the real result.</p>}</div><div className="watermark-preview__stage">{result ? resultPreview ? <div className="watermark-preview__page"><img src={resultPreview.image} alt={`Actual watermarked PDF, page ${previewPage}`} /></div> : <p role="status">{previewBusy ? 'Rendering the generated page…' : 'Preview unavailable. You can still download the PDF.'}</p> : <div className="watermark-preview__page"><img src={source.image} alt="First page of the original PDF" /><ApproximateOverlay options={options} preview={source} /></div>}</div>{previewError && <p className="watermark-preview__error" role="alert">{previewError}</p>}</div>
        </div>
      </div>}

      {busy && progress.state.stage === 'idle' && <p className="watermark-status" role="status">Preparing a page preview…</p>}
      <PdfProgress state={progress.state} onCancel={progress.cancel} />
      {error && <div className="watermark-error" role="alert"><strong>Could not watermark this PDF</strong><p>{error}</p></div>}
      {file && source && <div className="watermark-action"><div><strong>{result ? 'Your watermarked PDF is ready' : 'Ready to add the watermark?'}</strong><p>{result ? `${result.name} · ${fileSize(result.size)}. Review the actual page above.` : 'The original PDF stays unchanged.'}</p></div>{result ? <a href={result.url} download={result.name}>Download watermarked PDF</a> : <button type="submit" disabled={busy}>{busy ? 'Creating PDF…' : 'Create watermarked PDF'}</button>}</div>}
    </form><p className="watermark-privacy">Uploads are removed from temporary server storage after processing. Abandoned files are cleared after 15 minutes at startup or on later requests.</p>
  </div></section>
}
