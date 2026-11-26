import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { PdfProgress } from '../../shared/components/PdfProgress'
import { usePdfProgress } from '../../shared/components/usePdfProgress'
import { compressPdf } from './api'
import { renderPreview } from './preview'
import type { CompressionLevel, CompressionResult, PdfPreview } from './types'
import './compress-pdf.css'

const levels: { value: CompressionLevel; label: string; description: string }[] = [
  { value: 'gentle', label: 'Gentle', description: 'Lossless stream compression. Best quality; often saves little on PDFs that are already optimized.' },
  { value: 'balanced', label: 'Balanced', description: 'Recompresses eligible images at moderate JPEG quality; downsamples those above 185 dpi at their displayed size.' },
  { value: 'strong', label: 'Strong', description: 'Uses stronger JPEG compression and downsamples eligible images above 120 dpi. Fine detail may noticeably soften.' },
]

function fileSize(bytes: number) {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${bytes} bytes`
}

function changeMessage(result: CompressionResult) {
  const difference = result.originalSize - result.outputSize
  const percent = Math.abs(difference / result.originalSize * 100)
  const amount = percent < 0.05 ? 'less than 0.1%' : `${percent.toFixed(1)}%`
  if (difference < 0) return `The output is ${amount} larger. This file did not benefit from the chosen compression level.`
  if (difference === 0) return 'The output is the same size. This file did not benefit from the chosen compression level.'
  if (percent < 1) return `The output is only ${amount} smaller. This PDF may already be optimized.`
  return `Saved ${amount} (${fileSize(difference)}). Check image quality before sharing.`
}

export function CompressPdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<PdfPreview | null>(null)
  const [level, setLevel] = useState<CompressionLevel>('balanced')
  const [busy, setBusy] = useState(false)
  const [busyMessage, setBusyMessage] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState<CompressionResult | null>(null)
  const resultUrl = useRef<string | null>(null)
  const progress = usePdfProgress()

  useEffect(() => () => {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
  }, [])

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
    setError('')
    setNotice('')
    setBusy(true)
    setBusyMessage('Preparing a page preview…')
    try {
      const nextPreview = await renderPreview(chosen)
      setFile(chosen)
      setPreview(nextPreview)
      setNotice(`${nextPreview.pageCount} ${nextPreview.pageCount === 1 ? 'page' : 'pages'} ready to compress.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not open this PDF.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  function chooseLevel(next: CompressionLevel) {
    clearResult()
    setLevel(next)
    setError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    if (!file || !preview) { setError('Choose one PDF to compress.'); return }
    clearResult()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const blob = await progress.run((callbacks, signal) => compressPdf(file, level, callbacks, signal))
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-compressed.pdf', originalSize: file.size, outputSize: blob.size })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The PDF could not be compressed. Try again.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  const savedPercent = result ? (result.originalSize - result.outputSize) / result.originalSize * 100 : 0

  return <section className="compress-page"><div className="container">
    <a className="compress-back" href="#catalog">← All tools</a>
    <div className="compress-intro"><span className="eyebrow">OPTIMIZE YOUR DOCUMENTS</span><h1>Compress PDF<span className="accent-dot">.</span></h1><p>Try a smaller copy for upload or sharing, with a quality level you control.</p></div>
    <form onSubmit={handleSubmit}>
      <div className="compress-panel"><div className="compress-section-heading"><span className="compress-step">01</span><div><h2>Choose your PDF</h2><p>We’ll show its size and a source-page preview.</p></div></div>
        <label className="compress-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseFile} disabled={busy} /><span className="compress-picker__icon"><Icon name="compress" /></span><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
        {file && preview && <p className="compress-file-label"><strong>{file.name}</strong> · {fileSize(file.size)} · {preview.pageCount} {preview.pageCount === 1 ? 'page' : 'pages'}</p>}
      </div>

      {file && preview && <div className="compress-panel"><div className="compress-section-heading"><span className="compress-step">02</span><div><h2>Choose a compression level</h2><p>Stronger compression can reduce image quality. Text and page order stay in place.</p></div></div>
        <div className="compress-options"><fieldset><legend>Compression level</legend><div className="compress-levels">{levels.map(option => <label key={option.value} className={level === option.value ? 'compress-level selected' : 'compress-level'}><input type="radio" name="level" value={option.value} checked={level === option.value} onChange={() => chooseLevel(option.value)} disabled={busy} /><span><strong>{option.label}</strong><small>{option.description}</small></span></label>)}</div></fieldset><div className="compress-preview"><strong>Source PDF preview</strong><img src={preview.thumbnail} alt="Preview of the first page before compression" /><span>This shows the original first page, not the compressed result. Inspect the downloaded copy for image quality.</span></div></div>
      </div>}

      {busy && progress.state.stage === 'idle' && <p className="compress-status" role="status">{busyMessage}</p>}
      <PdfProgress state={progress.state} onCancel={progress.cancel} />
      {notice && !busy && <p className="compress-status" role="status">{notice}</p>}
      {error && <div className="compress-error" role="alert"><strong>Couldn’t compress this PDF</strong><p>{error}</p></div>}
      {file && preview && <div className="compress-action-panel"><div><strong>Ready to try compression?</strong><p>The original file stays unchanged. Some PDFs are already optimized and may not get smaller.</p></div><button type="submit" disabled={busy}>{busy ? 'Compressing…' : 'Compress PDF'}</button></div>}
      {result && <div className="compress-result" role="status"><div className="compress-result__heading"><span className="compress-result__icon">✓</span><div><h2>Compression complete — your PDF copy is ready</h2><p>{changeMessage(result)} Inspect the downloaded copy for image quality; the preview above shows the source PDF.</p></div></div><dl className="compress-stats"><div><dt>Original size</dt><dd>{fileSize(result.originalSize)}</dd></div><div><dt>Output size</dt><dd>{fileSize(result.outputSize)}</dd></div><div><dt>Percentage saved</dt><dd>{savedPercent > -0.05 && savedPercent < 0.05 ? '≈0%' : `${savedPercent.toFixed(1)}%`}</dd></div></dl><a href={result.url} download={result.name}>Download PDF copy</a></div>}
    </form>
    <p className="compress-privacy">Uploads are removed from temporary server storage after processing. Abandoned folders are cleared after 15 minutes at startup or on later requests.</p>
  </div></section>
}
