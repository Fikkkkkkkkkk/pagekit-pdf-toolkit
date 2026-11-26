import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { rotatePdf } from './api'
import { renderThumbnails } from './thumbnails'
import type { RotatePage, RotateResult } from './types'
import './rotate-pdf.css'

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function RotatePdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [pages, setPages] = useState<RotatePage[]>([])
  const [busy, setBusy] = useState(false)
  const [busyMessage, setBusyMessage] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState<RotateResult | null>(null)
  const resultUrl = useRef<string | null>(null)

  useEffect(() => () => { if (resultUrl.current) URL.revokeObjectURL(resultUrl.current) }, [])

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
    resultUrl.current = null
    setResult(null)
  }

  async function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0]
    event.target.value = ''
    if (!chosen) return
    clearResult()
    setFile(null)
    setPages([])
    setError('')
    setNotice('')
    setBusy(true)
    setBusyMessage('Preparing page previews…')
    try {
      const previews = await renderThumbnails(chosen)
      setFile(chosen)
      setPages(previews)
      setNotice(`${previews.length} ${previews.length === 1 ? 'page' : 'pages'} ready. Turn the pages that need rotating.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not open this PDF.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  function turnPage(number: number, direction: -1 | 1) {
    clearResult()
    setPages(current => current.map(page => page.number === number ? { ...page, rotation: (page.rotation + direction * 90 + 360) % 360 } : page))
    setNotice(`Page ${number} turned ${direction === 1 ? 'clockwise' : 'counterclockwise'}. Review the preview below.`)
    setError('')
  }

  function turnAll(direction: -1 | 1) {
    clearResult()
    setPages(current => current.map(page => ({ ...page, rotation: (page.rotation + direction * 90 + 360) % 360 })))
    setNotice(`All pages turned ${direction === 1 ? 'clockwise' : 'counterclockwise'}. Review the previews below.`)
    setError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file || !pages.length) { setError('Choose one PDF to rotate.'); return }
    clearResult()
    setBusy(true)
    setBusyMessage('Creating your rotated PDF…')
    setError('')
    setNotice('')
    try {
      const blob = await rotatePdf(file, pages)
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-rotated.pdf', size: blob.size })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The PDF could not be rotated. Try again.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  const changedCount = pages.filter(page => page.rotation !== 0).length

  return <section className="rotate-page"><div className="container">
    <a className="rotate-back" href="#catalog">← All tools</a>
    <div className="rotate-intro"><span className="eyebrow">ORGANIZE YOUR DOCUMENTS</span><h1>Rotate PDF<span className="accent-dot">.</span></h1><p>Turn individual pages or the whole document in 90° steps.</p></div>
    <form onSubmit={handleSubmit}>
      <div className="rotate-panel"><div className="rotate-section-heading"><span className="rotate-step">01</span><div><h2>Choose your PDF</h2><p>We’ll show every page so you can check which way it should face.</p></div></div>
        <label className="rotate-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseFile} disabled={busy} /><span className="rotate-picker__icon"><Icon name="rotate" /></span><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
        {file && <p className="rotate-file-label"><strong>{file.name}</strong> · {fileSize(file.size)} · {pages.length} {pages.length === 1 ? 'page' : 'pages'}</p>}
      </div>

      {file && <div className="rotate-panel"><div className="rotate-section-heading"><span className="rotate-step">02</span><div><h2>Turn and preview pages</h2><p>Use each page’s controls, or turn every page together. Pages stay in their original order.</p></div></div>
        <div className="rotate-all"><span>All pages</span><div><button type="button" onClick={() => turnAll(-1)} disabled={busy} aria-label="Rotate all pages counterclockwise 90 degrees">↶ Turn left</button><button type="button" onClick={() => turnAll(1)} disabled={busy} aria-label="Rotate all pages clockwise 90 degrees">↷ Turn right</button></div></div>
        <p className="rotate-page-count">{changedCount} {changedCount === 1 ? 'page' : 'pages'} turned · {pages.length} total</p>
        <ol className="rotate-grid">{pages.map(page => <li className="rotate-card" key={page.number}><div className="rotate-card__preview"><span className="rotate-card__number">{page.number}</span><img src={page.thumbnail} alt={`Preview of PDF page ${page.number}, rotated ${page.rotation} degrees clockwise`} style={{ transform: `rotate(${page.rotation}deg)` }} /></div><div className="rotate-card__info"><strong>Page {page.number}</strong><span>{page.rotation === 0 ? 'Original orientation' : `${page.rotation}° clockwise`}</span></div><div className="rotate-card__actions"><button type="button" disabled={busy} onClick={() => turnPage(page.number, -1)} aria-label={`Rotate page ${page.number} counterclockwise 90 degrees`}>↶ Left</button><button type="button" disabled={busy} onClick={() => turnPage(page.number, 1)} aria-label={`Rotate page ${page.number} clockwise 90 degrees`}>↷ Right</button></div></li>)}</ol>
      </div>}

      {busy && <p className="rotate-status" role="status">{busyMessage}</p>}
      {notice && !busy && <p className="rotate-status" role="status">{notice}</p>}
      {error && <div className="rotate-error" role="alert"><strong>Couldn’t rotate this PDF</strong><p>{error}</p></div>}
      {file && <div className="rotate-action-panel"><div><strong>Ready to make your PDF?</strong><p>Your original file stays unchanged. Pages without a selected turn keep their orientation.</p></div><button type="submit" disabled={busy || changedCount === 0}>{busy ? 'Creating PDF…' : 'Create rotated PDF'}</button></div>}
      {result && <div className="rotate-success" role="status"><span className="rotate-success__icon">✓</span><div><h2>Your PDF is ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download rotated PDF</a></div>}
    </form>
    <p className="rotate-privacy">Uploads are removed from temporary server storage after processing. Abandoned files are cleared after 15 minutes at startup or on later requests.</p>
  </div></section>
}
