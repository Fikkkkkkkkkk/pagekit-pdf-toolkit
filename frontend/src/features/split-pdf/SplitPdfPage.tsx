import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { PdfProgress } from '../../shared/components/PdfProgress'
import { usePdfProgress } from '../../shared/components/usePdfProgress'
import { splitPdf } from './api'
import type { SplitResult } from './types'
import './split-pdf.css'

const MAX_FILE_BYTES = 25 * 1024 * 1024

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function SplitPdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [ranges, setRanges] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SplitResult | null>(null)
  const resultUrl = useRef<string | null>(null)
  const progress = usePdfProgress()

  useEffect(() => () => { if (resultUrl.current) URL.revokeObjectURL(resultUrl.current) }, [])

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
    resultUrl.current = null
    setResult(null)
    progress.reset()
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0]
    event.target.value = ''
    if (!selected) return
    clearResult()
    setFile(null)
    if (!selected.name.toLowerCase().endsWith('.pdf')) { setError('Choose a file with a .pdf extension.'); return }
    if (!selected.size) { setError('This file is empty. Choose a readable PDF.'); return }
    if (selected.size > MAX_FILE_BYTES) { setError('The PDF is over the 25 MB file limit.'); return }
    setError('')
    setFile(selected)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (loading) return
    if (!file) { setError('Choose one PDF file to split.'); return }
    if (!ranges.trim()) { setError('Enter at least one page range, such as 1-3, 5, 8-10.'); return }
    clearResult()
    setError('')
    setLoading(true)
    try {
      const blob = await progress.run((callbacks, signal) => splitPdf(file, ranges, callbacks, signal))
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-split.zip', size: blob.size })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The split failed. Check your PDF and page ranges, then try again.')
    } finally {
      setLoading(false)
    }
  }

  return <section className="split-page"><div className="container">
    <a className="split-back" href="#catalog">← All tools</a>
    <div className="split-intro"><span className="eyebrow">ORGANIZE YOUR DOCUMENTS</span><h1>Split PDF<span className="accent-dot">.</span></h1><p>Choose the exact pages you need. Each range becomes its own PDF in one easy download.</p></div>
    <div className="split-layout">
      <form className="split-panel" onSubmit={handleSubmit}>
        <div className="split-panel__heading"><span className="split-step">01</span><div><h2>Choose one PDF</h2><p>Your original document stays unchanged.</p></div></div>
        <label className="split-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseFile} disabled={loading} /><span className="split-picker__icon"><Icon name="split" /></span><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
        {file && <div className="split-file"><span className="split-file__icon"><Icon name="pages" /></span><span><strong title={file.name}>{file.name}</strong><small>{fileSize(file.size)}</small></span><button type="button" onClick={() => { setFile(null); clearResult(); setError('') }} disabled={loading} aria-label={`Remove ${file.name}`}>×</button></div>}
        <div className="split-range-heading"><span className="split-step">02</span><div><h2>Enter page ranges</h2><p>Each comma-separated range creates a separate PDF.</p></div></div>
        <label className="split-range-label" htmlFor="split-ranges">Page ranges</label>
        <input id="split-ranges" className="split-range-input" type="text" inputMode="text" placeholder="1-3, 5, 8-10" value={ranges} onChange={event => { setRanges(event.target.value); clearResult(); setError('') }} disabled={loading} aria-describedby="split-range-help" />
        <p id="split-range-help" className="split-range-help">Use page numbers or inclusive ranges. Keep them in the order you want them in the ZIP. Ranges must not overlap.</p>
        {error && <div className="split-message split-message--error" role="alert"><strong>Couldn’t split this PDF</strong><p>{error}</p></div>}
        <button className="split-submit" type="submit" disabled={loading || !file || !ranges.trim()}>{loading ? 'Creating your PDFs…' : 'Split PDF'}</button>
        <PdfProgress state={progress.state} onCancel={progress.cancel} />
        {result && <div className="split-success" role="status"><span className="split-success__icon">✓</span><div><h2>Your ZIP is ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download ZIP</a></div>}
        <p className="split-privacy">Your PDF is processed for this request and removed from temporary server storage after splitting.</p>
      </form>
      <aside className="split-side"><div className="split-side__card"><span className="split-side__icon"><Icon name="pages" /></span><h2>One range, one PDF</h2><p>For example, <strong>1-3, 5, 8-10</strong> creates three PDFs: pages 1–3, page 5, and pages 8–10. The ZIP lists them in that order.</p><div className="split-side__example"><span>01-pages-1-3.pdf</span><span>02-pages-5.pdf</span><span>03-pages-8-10.pdf</span></div></div><div className="split-side__note"><Icon name="lock" /><p>Password-protected or unreadable PDFs can’t be split. Range errors show what to fix before you retry.</p></div></aside>
    </div>
  </div></section>
}
