import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { mergePdfs } from './api'
import type { MergeResult, SelectedPdf } from './types'
import './merge-pdf.css'

const MAX_FILES = 20
const MAX_FILE_BYTES = 25 * 1024 * 1024
const MAX_TOTAL_BYTES = 100 * 1024 * 1024

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function MergePdfPage() {
  const [files, setFiles] = useState<SelectedPdf[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<MergeResult | null>(null)
  const resultUrl = useRef<string | null>(null)

  useEffect(() => () => { if (resultUrl.current) URL.revokeObjectURL(resultUrl.current) }, [])

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
    resultUrl.current = null
    setResult(null)
  }

  function addFiles(event: ChangeEvent<HTMLInputElement>) {
    const chosen = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (!chosen.length) return
    const combined = [...files, ...chosen.map(file => ({ id: crypto.randomUUID(), file }))]
    if (combined.length > MAX_FILES) { setError(`Choose no more than ${MAX_FILES} PDFs.`); return }
    const invalid = chosen.find(item => !item.name.toLowerCase().endsWith('.pdf'))
    if (invalid) { setError(`“${invalid.name}” is not a PDF. Choose a .pdf file.`); return }
    const empty = chosen.find(item => !item.size)
    if (empty) { setError(`“${empty.name}” is empty. Choose a readable PDF.`); return }
    const large = chosen.find(item => item.size > MAX_FILE_BYTES)
    if (large) { setError(`“${large.name}” is over the 25 MB file limit.`); return }
    if (combined.reduce((sum, item) => sum + item.file.size, 0) > MAX_TOTAL_BYTES) { setError('The selected PDFs exceed the 100 MB total limit. Remove a file and try again.'); return }
    clearResult()
    setError('')
    setFiles(combined)
  }

  function moveFile(index: number, direction: -1 | 1) {
    const other = index + direction
    if (other < 0 || other >= files.length) return
    const updated = [...files]
    ;[updated[index], updated[other]] = [updated[other], updated[index]]
    clearResult()
    setFiles(updated)
    setError('')
  }

  function removeFile(id: string) {
    clearResult()
    setFiles(files.filter(item => item.id !== id))
    setError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (files.length < 2) { setError('Choose at least two PDFs to merge.'); return }
    clearResult()
    setError('')
    setLoading(true)
    try {
      const blob = await mergePdfs(files)
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-merged.pdf', size: blob.size })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The merge failed. Check your PDFs and try again.')
    } finally {
      setLoading(false)
    }
  }

  return <section className="merge-page"><div className="container">
    <a className="merge-back" href="#catalog">← All tools</a>
    <div className="merge-intro"><span className="eyebrow">ORGANIZE YOUR DOCUMENTS</span><h1>Merge PDF<span className="accent-dot">.</span></h1><p>Bring your notes, readings, or handouts together in the order you choose.</p></div>
    <div className="merge-layout">
      <form className="merge-panel" onSubmit={handleSubmit}>
        <div className="merge-panel__heading"><span className="merge-step">01</span><div><h2>Choose your PDFs</h2><p>Add two or more files. They’ll be merged from top to bottom.</p></div></div>
        <label className="merge-picker"><input type="file" accept=".pdf,application/pdf" multiple onChange={addFiles} disabled={loading} /><span className="merge-picker__icon"><Icon name="merge" /></span><strong>Choose PDF files</strong><span>PDF only · up to 20 files · 25 MB each · 100 MB total</span></label>
        <div className="merge-order-heading"><h2>File order</h2><span>{files.length} {files.length === 1 ? 'file' : 'files'}</span></div>
        {files.length ? <ol className="merge-file-list">{files.map((item, index) => <li key={item.id} className="merge-file"><span className="merge-file__number">{index + 1}</span><span className="merge-file__icon"><Icon name="pages" /></span><span className="merge-file__details"><strong title={item.file.name}>{item.file.name}</strong><small>{fileSize(item.file.size)}</small></span><div className="merge-file__actions"><button type="button" onClick={() => moveFile(index, -1)} disabled={loading || index === 0} aria-label={`Move ${item.file.name} up`}>↑</button><button type="button" onClick={() => moveFile(index, 1)} disabled={loading || index === files.length - 1} aria-label={`Move ${item.file.name} down`}>↓</button><button type="button" onClick={() => removeFile(item.id)} disabled={loading} aria-label={`Remove ${item.file.name}`}>×</button></div></li>)}</ol> : <div className="merge-empty"><Icon name="pages" /><p>Your PDFs will appear here so you can check their order.</p></div>}
        {error && <div className="merge-message merge-message--error" role="alert"><strong>Couldn’t merge these files</strong><p>{error}</p></div>}
        <button className="merge-submit" type="submit" disabled={loading || files.length < 2}>{loading ? 'Merging your PDFs…' : 'Merge PDFs'}</button>
        {loading && <p className="merge-loading" role="status">Processing your files. This may take a moment.</p>}
        {result && <div className="merge-success" role="status"><span className="merge-success__icon">✓</span><div><h2>Your PDF is ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download merged PDF</a></div>}
        <p className="merge-privacy">Your files are processed for this request and removed from temporary server storage after the merge.</p>
      </form>
      <aside className="merge-side"><div className="merge-side__card"><span className="merge-side__icon"><Icon name="pages" /></span><h2>A tidy PDF, in three steps</h2><ol><li><strong>Add PDFs</strong><span>Select at least two documents.</span></li><li><strong>Set the order</strong><span>Use the up and down controls, or remove a file.</span></li><li><strong>Merge & download</strong><span>Get one combined PDF in your chosen order.</span></li></ol></div><div className="merge-side__note"><Icon name="lock" /><p>Password-protected or unreadable PDFs can’t be merged. If a file fails, replace it and try again.</p></div></aside>
    </div>
  </div></section>
}
