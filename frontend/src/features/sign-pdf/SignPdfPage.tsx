import { UsageHint } from '../../shared/components/UsageHint'
import { useEffect, useRef, useState, type ChangeEvent, type FormEvent, type PointerEvent } from 'react'
import { PdfProgress } from '../../shared/components/PdfProgress'
import { usePdfProgress } from '../../shared/components/usePdfProgress'
import { signPdf } from './api'
import { fitPlacement } from './geometry'
import { SignatureCanvas } from './SignatureCanvas'
import { canvasAsset, imageAsset, renderPage } from './preview'
import type { PagePreview, Placement, SignatureAsset } from './types'
import './sign-pdf.css'

type Mode = 'draw' | 'type' | 'upload'

export function SignPdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [source, setSource] = useState<PagePreview | null>(null)
  const [shown, setShown] = useState<PagePreview | null>(null)
  const [page, setPage] = useState(1)
  const [asset, setAsset] = useState<SignatureAsset | null>(null)
  const [placements, setPlacements] = useState<Placement[]>([])
  const [mode, setMode] = useState<Mode>('draw')
  const [typed, setTyped] = useState('')
  const [result, setResult] = useState<{ blob: Blob; url: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [previewBusy, setPreviewBusy] = useState(false)
  const [error, setError] = useState('')
  const [previewError, setPreviewError] = useState('')
  const assetUrl = useRef<string | null>(null)
  const resultUrl = useRef<string | null>(null)
  const stage = useRef<HTMLDivElement>(null)
  const drag = useRef<{ x: number; y: number; original: Placement } | null>(null)
  const progress = usePdfProgress()

  useEffect(() => () => { if (assetUrl.current) URL.revokeObjectURL(assetUrl.current); if (resultUrl.current) URL.revokeObjectURL(resultUrl.current) }, [])
  const selected = placements.find(item => item.page === page)

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
    resultUrl.current = null
    setResult(null)
    setPreviewError('')
    progress.reset()
  }
  function useAsset(next: SignatureAsset) {
    if (assetUrl.current) URL.revokeObjectURL(assetUrl.current)
    assetUrl.current = next.url
    setAsset(next)
    setPlacements([])
    clearResult()
    if (file) { setShown(null); setPreviewBusy(true); void renderPage(file, page).then(setShown).catch(() => setPreviewError('The source page could not be previewed.')).finally(() => setPreviewBusy(false)) }
    setError('')
  }
  async function choosePdf(event: ChangeEvent<HTMLInputElement>) {
    const next = event.target.files?.[0]
    event.target.value = ''
    if (!next) return
    clearResult(); setFile(null); setSource(null); setShown(null); setPlacements([]); setPage(1); setError(''); setBusy(true)
    try { const preview = await renderPage(next, 1); setFile(next); setSource(preview); setShown(preview) }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'This PDF could not be opened.') }
    finally { setBusy(false) }
  }
  async function showPage(next: number) {
    if (!file || previewBusy) return
    setPage(next); setShown(null); setPreviewBusy(true); setPreviewError('')
    try { setShown(await renderPage(result?.blob ?? file, next)) }
    catch { setPreviewError('This page could not be previewed. You can still download the output.'); }
    finally { setPreviewBusy(false) }
  }
  function updatePlacement(patch: Partial<Placement>) {
    if (!shown) return
    clearResult()
    setPlacements(current => current.map(item => item.page === page ? fitPlacement({ ...item, ...patch }, shown.width, shown.height) : item))
  }
  function addPlacement() {
    if (!asset || !shown) return
    const width = .32
    const height = Math.min(.3, width * (asset.height / asset.width) * (shown.width / shown.height))
    const next = fitPlacement({ page, x: .5 - width / 2, y: .65, width, height, angle: selected?.angle ?? 0 }, shown.width, shown.height)
    setPlacements(current => [...current.filter(item => item.page !== page), next])
    clearResult()
  }
  function onMove(event: PointerEvent<HTMLDivElement>) {
    if (!drag.current || !stage.current || !selected) return
    const rect = stage.current.getBoundingClientRect()
    updatePlacement({ x: drag.current.original.x + (event.clientX - drag.current.x) / rect.width,
      y: drag.current.original.y + (event.clientY - drag.current.y) / rect.height })
  }
  async function typedAsset() {
    if (!typed.trim()) { setError('Type a signature first.'); return }
    const canvas = document.createElement('canvas')
    canvas.width = 900; canvas.height = 220
    const context = canvas.getContext('2d')!
    context.fillStyle = '#17213c'; context.font = 'italic 82px cursive'; context.textBaseline = 'middle'
    context.fillText(typed.trim().slice(0, 55), 16, 110, 868)
    useAsset(await canvasAsset(canvas))
  }
  async function uploadAsset(event: ChangeEvent<HTMLInputElement>) {
    const next = event.target.files?.[0]; event.target.value = ''
    if (!next) return
    try { useAsset(await imageAsset(next)) }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'This image could not be opened.') }
  }
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy || !file || !asset || !placements.length) { setError('Choose a PDF, create a signature, and place it on at least one page.'); return }
    clearResult(); setError(''); setBusy(true)
    try {
      const blob = await progress.run((callbacks, signal) => signPdf(file, asset.blob, placements, callbacks, signal))
      const url = URL.createObjectURL(blob); resultUrl.current = url; setResult({ blob, url })
      setPreviewBusy(true)
      try { setShown(await renderPage(blob, page)) }
      catch { setShown(null); setPreviewError('The PDF is ready, but its preview could not be shown. Download and inspect the result.') }
      finally { setPreviewBusy(false) }
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'The signature could not be added.') }
    finally { setBusy(false) }
  }

  return <section className="sign-page"><div className="container">
    <a className="sign-back" href="#catalog">← All tools</a>
    <div className="sign-intro"><span className="eyebrow">SECURITY & REVIEW</span><h1>Sign PDF<span className="accent-dot">.</span></h1><p>Add a visible signature to selected pages of a new PDF copy.</p><div className="sign-notice"><strong>Visual signature only.</strong> This does not create a cryptographic digital signature or verify the signer’s identity.</div></div>
    <form onSubmit={submit}>
      <div className="usage-layout">
        <div className="sign-panel"><div className="sign-heading"><span>01</span><div><h2>Choose your PDF</h2><p>One unlocked PDF, up to 25 MB. The original stays unchanged.</p></div></div>
          <label className="sign-picker"><input type="file" accept=".pdf,application/pdf" onChange={choosePdf} disabled={busy} /><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><small>PDF only · up to 25 MB</small></label>
          {file && source && <p className="sign-file">{file.name} · {source.pageCount} {source.pageCount === 1 ? 'page' : 'pages'}</p>}</div>
        <UsageHint icon="sign" title="Place a visual mark" steps={[{ title: 'Open the document', detail: 'Open the page you want to mark.' }, { title: 'Create a signature', detail: 'Draw, type, or upload an image.' }, { title: 'Place and review', detail: 'Move, resize, or turn it on each chosen page; inspect the result.' }]} />
      </div>
      {file && source && <div className="sign-panel"><div className="sign-heading"><span>02</span><div><h2>Create your signature</h2><p>Draw, type, or upload a PNG or JPG. Your mark will remain an image in the PDF.</p></div></div>
        <div className="sign-modes" role="group" aria-label="Signature method">{(['draw', 'type', 'upload'] as const).map(item => <button key={item} type="button" className={mode === item ? 'active' : ''} aria-pressed={mode === item} onClick={() => setMode(item)} disabled={busy}>{item === 'draw' ? 'Draw' : item === 'type' ? 'Type' : 'Upload image'}</button>)}</div>
        {mode === 'draw' && <SignatureCanvas onSave={useAsset} disabled={busy} />}
        {mode === 'type' && <div className="sign-type"><label>Signature text<input value={typed} onChange={event => setTyped(event.target.value)} maxLength={55} placeholder="Type your name" disabled={busy} /></label><button type="button" onClick={() => void typedAsset()} disabled={busy}>Use typed signature</button><small>Appearance depends on the fonts available in your browser.</small></div>}
        {mode === 'upload' && <label className="sign-upload">Choose a PNG or JPG signature image, up to 10 MB<input type="file" accept="image/png,image/jpeg" onChange={uploadAsset} disabled={busy} /></label>}
        {asset && <div className="sign-asset"><strong>Current signature</strong><img src={asset.url} alt="Your selected signature" /></div>}
      </div>}
      {file && source && <div className="sign-panel"><div className="sign-heading"><span>03</span><div><h2>Place and preview</h2><p>Choose a page and add the mark. Repeat for other pages; drag it or use the position and size controls.</p></div></div>
        <div className="sign-editor"><div className="sign-controls"><label>Page<select value={page} onChange={event => void showPage(Number(event.target.value))} disabled={busy || previewBusy}>{Array.from({ length: source.pageCount }, (_, index) => <option key={index} value={index + 1}>Page {index + 1}{placements.some(item => item.page === index + 1) ? ' · signature placed' : ''}</option>)}</select></label>
          {!result && <><button type="button" onClick={addPlacement} disabled={!asset || busy || previewBusy}>{selected ? 'Center signature on this page' : 'Add signature to this page'}</button>{selected && <><label>Width <span>{Math.round(selected.width * 100)}% of page</span><input type="range" min="5" max="80" value={Math.round(selected.width * 100)} onChange={event => { const width = Number(event.target.value) / 100; const height = Math.min(.9, width * (asset?.height ?? 1) / (asset?.width ?? 1) * (shown?.width ?? 1) / (shown?.height ?? 1)); updatePlacement({ width, height, x: Math.min(selected.x, 1 - width), y: Math.min(selected.y, 1 - height) }) }} disabled={busy} /></label><label>Angle <span>{selected.angle}&deg;</span><input type="range" min="-180" max="180" step="1" value={selected.angle} onChange={event => updatePlacement({ angle: Number(event.target.value) })} disabled={busy} /></label><button type="button" onClick={() => updatePlacement({ angle: 0 })} disabled={busy || selected.angle === 0}>Reset angle to 0&deg;</button><label>Horizontal position <span>{Math.round(selected.x * 100)}%</span><input type="range" min="0" max={Math.round((1 - selected.width) * 100)} value={Math.round(selected.x * 100)} onChange={event => updatePlacement({ x: Number(event.target.value) / 100 })} disabled={busy} /></label><label>Vertical position <span>{Math.round(selected.y * 100)}%</span><input type="range" min="0" max={Math.round((1 - selected.height) * 100)} value={Math.round(selected.y * 100)} onChange={event => updatePlacement({ y: Number(event.target.value) / 100 })} disabled={busy} /></label><button type="button" className="sign-remove" onClick={() => { setPlacements(current => current.filter(item => item.page !== page)); clearResult() }} disabled={busy}>Remove from this page</button></>}</>}
          <p>{placements.length} {placements.length === 1 ? 'page has' : 'pages have'} a signature.</p></div>
          <div className="sign-preview"><strong>{result ? 'Actual generated PDF preview' : 'Approximate placement preview'}</strong><div className="sign-preview-stage">{shown ? <div className="sign-preview-page" ref={stage}><img className="sign-preview-image" src={shown.image} alt={`${result ? 'Generated' : 'Original'} PDF page ${page}`} />{!result && selected && asset && <div className="sign-overlay" role="img" aria-label={`Signature placed on page ${page}`} style={{ left: `${selected.x * 100}%`, top: `${selected.y * 100}%`, width: `${selected.width * 100}%`, height: `${selected.height * 100}%`, transform: `rotate(${selected.angle}deg)` }} onPointerDown={event => { if (busy) return; event.currentTarget.setPointerCapture(event.pointerId); drag.current = { x: event.clientX, y: event.clientY, original: selected } }} onPointerMove={onMove} onPointerUp={() => { drag.current = null }} onPointerCancel={() => { drag.current = null }}><img src={asset.url} alt="" /></div>}</div> : <p role="status">{previewBusy ? 'Rendering page…' : 'Preview unavailable.'}</p>}</div>{previewError && <p role="alert">{previewError}</p>}</div></div>
      </div>}
      {busy && progress.state.stage === 'idle' && <p role="status">Preparing PDF preview…</p>}
      <PdfProgress state={progress.state} onCancel={progress.cancel} />
      {error && <div className="sign-error" role="alert"><strong>Could not sign this PDF</strong><p>{error}</p></div>}
      {file && source && <div className="sign-action"><div><strong>{result ? 'Your visually signed PDF is ready' : 'Ready to create your copy?'}</strong><p>{result ? 'Review the actual pages above before downloading.' : 'The original PDF stays unchanged.'}</p></div>{result ? <a href={result.url} download="PageKit-visual-signature.pdf">Download signed PDF</a> : <button type="submit" disabled={busy || !asset || !placements.length}>{busy ? 'Creating PDF…' : 'Create signed PDF'}</button>}</div>}
    </form><p className="sign-privacy">Files are removed from temporary server storage after processing. Abandoned files are cleared at startup or on later requests once they are 15 minutes old.</p>
  </div></section>
}
