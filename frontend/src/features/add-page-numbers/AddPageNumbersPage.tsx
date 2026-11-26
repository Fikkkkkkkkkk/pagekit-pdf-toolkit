import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { PdfProgress } from '../../shared/components/PdfProgress'
import { usePdfProgress } from '../../shared/components/usePdfProgress'
import { addPageNumbers } from './api'
import { renderPreview } from './preview'
import type { NumberedResult, NumberPosition, PdfPreview } from './types'
import './add-page-numbers.css'

const positions: { value: NumberPosition; label: string }[] = [
  { value: 'top-left', label: 'Top left' },
  { value: 'top-center', label: 'Top center' },
  { value: 'top-right', label: 'Top right' },
  { value: 'bottom-left', label: 'Bottom left' },
  { value: 'bottom-center', label: 'Bottom center' },
  { value: 'bottom-right', label: 'Bottom right' },
]

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function AddPageNumbersPage() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<PdfPreview | null>(null)
  const [position, setPosition] = useState<NumberPosition>('bottom-center')
  const [start, setStart] = useState('1')
  const [busy, setBusy] = useState(false)
  const [busyMessage, setBusyMessage] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState<NumberedResult | null>(null)
  const resultUrl = useRef<string | null>(null)
  const progress = usePdfProgress()

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
    setError('')
    setNotice('')
    setBusy(true)
    setBusyMessage('Preparing a page preview…')
    try {
      const nextPreview = await renderPreview(chosen)
      setFile(chosen)
      setPreview(nextPreview)
      setNotice(`${nextPreview.pageCount} ${nextPreview.pageCount === 1 ? 'page' : 'pages'} ready to number.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not open this PDF.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  function changePosition(next: NumberPosition) {
    clearResult()
    setPosition(next)
    setError('')
  }

  function changeStart(next: string) {
    clearResult()
    setStart(next)
    setError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    if (!file || !preview) { setError('Choose one PDF to number.'); return }
    const firstNumber = Number(start)
    if (!/^[0-9]+$/.test(start) || !Number.isSafeInteger(firstNumber) || firstNumber < 1 || firstNumber + preview.pageCount - 1 > 999999) {
      setError(`Choose a starting number from 1 to ${999999 - preview.pageCount + 1} for this PDF.`)
      return
    }
    clearResult()
    setBusy(true)
    setBusyMessage('Creating your numbered PDF…')
    setError('')
    setNotice('')
    try {
      const blob = await progress.run((callbacks, signal) => addPageNumbers(file, position, firstNumber, callbacks, signal))
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-numbered.pdf', size: blob.size })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Page numbers could not be added. Try again.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  return <section className="number-page"><div className="container">
    <a className="number-back" href="#catalog">← All tools</a>
    <div className="number-intro"><span className="eyebrow">ORGANIZE YOUR DOCUMENTS</span><h1>Add page numbers<span className="accent-dot">.</span></h1><p>Make your notes and citations easier to follow.</p></div>
    <form onSubmit={handleSubmit}>
      <div className="number-panel"><div className="number-section-heading"><span className="number-step">01</span><div><h2>Choose your PDF</h2><p>We’ll show the first page so you can choose where numbers go.</p></div></div>
        <label className="number-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseFile} disabled={busy} /><span className="number-picker__icon"><Icon name="numbers" /></span><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
        {file && preview && <p className="number-file-label"><strong>{file.name}</strong> · {fileSize(file.size)} · {preview.pageCount} {preview.pageCount === 1 ? 'page' : 'pages'}</p>}
      </div>

      {file && preview && <div className="number-panel"><div className="number-section-heading"><span className="number-step">02</span><div><h2>Set the numbering</h2><p>Numbers appear in the same spot on every page. The first page starts at your chosen number.</p></div></div>
        <div className="number-options"><fieldset><legend>Number position</legend><div className="number-position-grid">{positions.map(option => <label key={option.value} className={position === option.value ? 'number-position selected' : 'number-position'}><input type="radio" name="position" value={option.value} checked={position === option.value} onChange={() => changePosition(option.value)} disabled={busy} />{option.label}</label>)}</div></fieldset><label className="number-start">Starting number<input type="number" min="1" max={Math.max(1, 999999 - preview.pageCount + 1)} step="1" value={start} onChange={event => changeStart(event.target.value)} disabled={busy} required /></label></div>
        <div className="number-preview"><div><strong>Placement preview</strong><p>First page shown. The number position is approximate; review the downloaded PDF for overlap with existing content.</p></div><div className="number-preview__sheet"><img src={preview.thumbnail} alt="Preview of the first PDF page" /><span className={`number-preview__marker number-preview__marker--${position}`} aria-label={`Page number ${start || '1'} at ${position.replace('-', ' ')}`}>{start || '1'}</span></div></div>
      </div>}

      {busy && progress.state.stage === 'idle' && <p className="number-status" role="status">{busyMessage}</p>}
      <PdfProgress state={progress.state} onCancel={progress.cancel} />
      {notice && !busy && <p className="number-status" role="status">{notice}</p>}
      {error && <div className="number-error" role="alert"><strong>Couldn’t add page numbers</strong><p>{error}</p></div>}
      {file && preview && <div className="number-action-panel"><div><strong>Ready to number your PDF?</strong><p>All source pages and their order stay unchanged. A new numbered copy will be created.</p></div><button type="submit" disabled={busy}>{busy ? 'Creating PDF…' : 'Create numbered PDF'}</button></div>}
      {result && <div className="number-success" role="status"><span className="number-success__icon">✓</span><div><h2>Your PDF is ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download numbered PDF</a></div>}
    </form>
    <p className="number-privacy">Uploads are removed from temporary server storage after processing. Abandoned files are cleared after 15 minutes at startup or on later requests.</p>
  </div></section>
}
