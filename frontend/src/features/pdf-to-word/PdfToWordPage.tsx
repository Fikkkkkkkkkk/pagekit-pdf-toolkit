import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { convertPdfToWord } from './api'
import type { WordResult } from './types'
import './pdf-to-word.css'

const MAX_FILE_BYTES = 25 * 1024 * 1024

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function PdfToWordPage() {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<WordResult | null>(null)
  const resultUrl = useRef<string | null>(null)

  useEffect(() => () => { if (resultUrl.current) URL.revokeObjectURL(resultUrl.current) }, [])

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
    resultUrl.current = null
    setResult(null)
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0]
    event.target.value = ''
    if (!selected) return
    clearResult()
    setFile(null)
    if (!selected.name.toLowerCase().endsWith('.pdf')) { setError('Choose a file with a .pdf extension.'); return }
    if (!selected.size) { setError('This PDF is empty. Choose a readable file.'); return }
    if (selected.size > MAX_FILE_BYTES) { setError('This PDF is over the 25 MB file limit.'); return }
    setError('')
    setFile(selected)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file) { setError('Choose one PDF to convert.'); return }
    clearResult()
    setError('')
    setLoading(true)
    try {
      const { blob, name } = await convertPdfToWord(file)
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name, size: blob.size })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The PDF could not be converted. Try again.')
    } finally {
      setLoading(false)
    }
  }

  return <section className="word-page"><div className="container">
    <a className="word-back" href="#catalog">← All tools</a>
    <div className="word-intro"><span className="eyebrow">CONVERT YOUR DOCUMENTS</span><h1>PDF to Word<span className="accent-dot">.</span></h1><p>Turn selectable PDF text into a Word document you can edit.</p></div>
    <div className="word-layout">
      <form className="word-panel" onSubmit={handleSubmit}>
        <div className="word-panel__heading"><span className="word-step">01</span><div><h2>Choose one PDF</h2><p>All pages will be included in the DOCX.</p></div></div>
        <label className="word-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseFile} disabled={loading} /><span className="word-picker__icon"><Icon name="word" /></span><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
        {file && <div className="word-file"><span className="word-file__icon"><Icon name="pages" /></span><span><strong title={file.name}>{file.name}</strong><small>{fileSize(file.size)}</small></span><button type="button" onClick={() => { setFile(null); clearResult(); setError('') }} disabled={loading} aria-label={`Remove ${file.name}`}>×</button></div>}
        {error && <div className="word-message word-message--error" role="alert"><strong>Couldn’t convert this PDF</strong><p>{error}</p></div>}
        <button className="word-submit" type="submit" disabled={loading || !file}>{loading ? 'Converting your PDF…' : 'Convert to Word'}</button>
        {loading && <p className="word-loading" role="status">Creating an editable DOCX. This may take a moment.</p>}
        {result && <div className="word-success" role="status"><span className="word-success__icon">✓</span><div><h2>Your Word file is ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download DOCX</a></div>}
        <p className="word-privacy">Your PDF is processed locally by the PageKit backend and removed from temporary storage after conversion.</p>
      </form>
      <aside className="word-side"><div className="word-side__card"><span className="word-side__icon"><Icon name="edit" /></span><h2>Made for editable notes</h2><p>PageKit extracts selectable text in page order and includes images it can read. Paragraphs, page breaks, and basic page size are carried into the Word file.</p><div className="word-side__limit"><strong>What to expect</strong><p>PDF and Word lay out content differently. Columns, tables, fonts, and exact image positions may change. Review the DOCX before submitting it.</p></div></div><div className="word-side__note"><Icon name="scan" /><p>Scanned or image-only pages need OCR. OCR is not available yet, so PageKit will explain the issue instead of sending a blank Word file.</p></div></aside>
    </div>
  </div></section>
}
