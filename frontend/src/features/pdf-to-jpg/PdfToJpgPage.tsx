import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { usePdfProgress } from '../../shared/components/usePdfProgress'
import { packageJpgs } from './api'
import { convertPages, previewPages } from './render'
import type { JpgQuality, PageProgress, PageThumbnail, ZipResult } from './types'
import './pdf-to-jpg.css'

const qualities: { value: JpgQuality; label: string; detail: string }[] = [
  { value: 'compact', label: 'Compact', detail: 'Smaller JPGs; more visible compression' },
  { value: 'balanced', label: 'Balanced', detail: 'Good reading quality and moderate size' },
  { value: 'high', label: 'High', detail: 'More detail; larger ZIP' },
]

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(2)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function PdfToJpgPage() {
  const [file, setFile] = useState<File | null>(null)
  const [thumbnails, setThumbnails] = useState<PageThumbnail[]>([])
  const [quality, setQuality] = useState<JpgQuality>('balanced')
  const [previewBusy, setPreviewBusy] = useState(false)
  const [busy, setBusy] = useState(false)
  const [stage, setStage] = useState<'idle' | 'rendering' | 'packaging' | 'complete'>('idle')
  const [pageProgress, setPageProgress] = useState<PageProgress | null>(null)
  const [previewProgress, setPreviewProgress] = useState<PageProgress | null>(null)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ZipResult | null>(null)
  const resultUrl = useRef<string | null>(null)
  const previewController = useRef<AbortController | null>(null)
  const conversionController = useRef<AbortController | null>(null)
  const upload = usePdfProgress()

  useEffect(() => () => {
    previewController.current?.abort()
    conversionController.current?.abort()
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
  }, [])

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
    resultUrl.current = null
    setResult(null)
    setStage('idle')
    setPageProgress(null)
    upload.reset()
  }

  async function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0]
    event.target.value = ''
    if (!chosen) return
    clearResult()
    setFile(null)
    setThumbnails([])
    setError('')
    setPreviewProgress(null)
    setPreviewBusy(true)
    const controller = new AbortController()
    previewController.current = controller
    try {
      const pages = await previewPages(chosen, setPreviewProgress, controller.signal)
      setFile(chosen)
      setThumbnails(pages)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'This PDF could not be previewed. Try another file.')
    } finally {
      previewController.current = null
      setPreviewBusy(false)
      setPreviewProgress(null)
    }
  }

  function cancel() {
    previewController.current?.abort()
    conversionController.current?.abort()
    upload.cancel()
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || !file) return
    clearResult()
    setError('')
    setBusy(true)
    setStage('rendering')
    const controller = new AbortController()
    conversionController.current = controller
    try {
      const pages = await convertPages(file, quality, setPageProgress, controller.signal)
      conversionController.current = null
      setStage('packaging')
      const blob = await upload.run((callbacks, signal) => packageJpgs(pages, callbacks, signal))
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-jpg-pages.zip', size: blob.size })
      setStage('complete')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The PDF could not be converted. Try another file.')
      setStage('idle')
      setPageProgress(null)
    } finally {
      conversionController.current = null
      setBusy(false)
    }
  }

  const work = upload.state.work
  const percent = result ? 100 : stage === 'rendering' && pageProgress?.total
    ? Math.min(99, Math.floor(pageProgress.completed / pageProgress.total * 100))
    : stage === 'packaging' && upload.state.stage === 'uploading'
      ? upload.state.uploadPercent === 100 ? 99 : upload.state.uploadPercent
      : stage === 'packaging' && work?.total
        ? Math.min(99, Math.floor(work.completed / work.total * 100)) : null
  const phase = result ? 'ZIP ready' : stage === 'rendering' ? 'Converting PDF pages to JPG'
    : stage === 'packaging' && upload.state.stage === 'uploading' ? 'Uploading JPG pages to local Flask'
      : stage === 'packaging' ? work?.phase || 'Packaging JPG pages' : ''

  return <section className="pdfjpg-page"><div className="container">
    <a className="pdfjpg-back" href="#catalog">← All tools</a>
    <div className="pdfjpg-intro"><span className="eyebrow">CONVERT YOUR FILES</span><h1>PDF to JPG<span className="accent-dot">.</span></h1><p>Save every PDF page as a JPG, together in one ZIP.</p></div>
    <form onSubmit={handleSubmit}>
      <div className="pdfjpg-panel"><div className="pdfjpg-heading"><span className="pdfjpg-step">01</span><div><h2>Choose your PDF</h2><p>One unlocked PDF, up to 25 MB. Your original stays unchanged.</p></div></div>
        <label className="pdfjpg-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseFile} disabled={previewBusy || busy} /><span className="pdfjpg-picker__icon"><Icon name="image" /></span><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
        {file && <p className="pdfjpg-file"><strong>{file.name}</strong> · {fileSize(file.size)} · {thumbnails.length} {thumbnails.length === 1 ? 'page' : 'pages'}</p>}
        {previewBusy && <div className="pdfjpg-progress" role="status"><strong>Preparing page previews</strong><span>{previewProgress ? `${previewProgress.completed} of ${previewProgress.total} pages` : 'Opening PDF…'}</span><progress max={previewProgress?.total || 1} value={previewProgress?.completed || 0} /><button type="button" onClick={cancel}>Cancel</button></div>}
      </div>

      {thumbnails.length > 0 && <div className="pdfjpg-panel"><div className="pdfjpg-heading"><span className="pdfjpg-step">02</span><div><h2>Review the pages</h2><p>Every page shown here will become one JPG in the same order.</p></div></div><ol className="pdfjpg-thumbnails">{thumbnails.map(page => <li key={page.number}><img src={page.image} alt={`Preview of PDF page ${page.number}`} /><span>Page {page.number}</span></li>)}</ol></div>}

      {file && <div className="pdfjpg-panel"><div className="pdfjpg-heading"><span className="pdfjpg-step">03</span><div><h2>Choose JPG quality</h2><p>Higher quality keeps more detail and can make the ZIP larger.</p></div></div><fieldset className="pdfjpg-qualities"><legend>Image quality</legend>{qualities.map(item => <label key={item.value} className={quality === item.value ? 'selected' : ''}><input type="radio" name="quality" value={item.value} checked={quality === item.value} onChange={() => { clearResult(); setQuality(item.value) }} disabled={busy} /><strong>{item.label}</strong><span>{item.detail}</span></label>)}</fieldset><p className="pdfjpg-note">Pages are rendered locally in your browser at up to 144 dpi and 2400 pixels per side. The JPGs are sent only to your local Flask server for ZIP packaging.</p></div>}

      {(busy || result) && <div className="pdfjpg-progress" role="status" aria-live="polite"><div><strong>{phase}</strong><span>{percent === null ? 'Preparing…' : `${percent}%`}</span></div><progress max={100} value={percent ?? undefined} aria-label={`${phase} progress`} /><p>{stage === 'rendering' && pageProgress ? `${pageProgress.completed} of ${pageProgress.total} pages converted` : stage === 'packaging' && work?.total ? `${work.completed} of ${work.total} ZIP work units complete` : result ? 'The ZIP is ready to download.' : 'Processing locally…'}</p>{busy && <button type="button" onClick={cancel}>Cancel</button>}</div>}
      {error && <div className="pdfjpg-error" role="alert"><strong>Could not convert this PDF</strong><p>{error}</p></div>}
      {file && <div className="pdfjpg-action"><div><strong>{thumbnails.length} {thumbnails.length === 1 ? 'page' : 'pages'} ready to convert</strong><p>The ZIP will contain page-001.jpg, page-002.jpg, and so on.</p></div><button type="submit" disabled={busy || previewBusy || !thumbnails.length}>{busy ? 'Converting pages…' : 'Convert to JPG'}</button></div>}
      {result && <div className="pdfjpg-result" role="status"><span aria-hidden="true">✓</span><div><h2>Your JPG pages are ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download ZIP</a></div>}
    </form><p className="pdfjpg-privacy">The PDF stays in your browser. Converted JPGs are sent to your local Flask server only to create the ZIP and are not saved as server files.</p>
  </div></section>
}
