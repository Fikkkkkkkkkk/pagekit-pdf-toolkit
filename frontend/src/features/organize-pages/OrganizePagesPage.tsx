import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { organizePages } from './api'
import { PageThumbnail } from './PageThumbnail'
import { renderThumbnails } from './thumbnails'
import type { OrganizedResult, PageItem } from './types'
import './organize-pages.css'

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function OrganizePagesPage() {
  const [original, setOriginal] = useState<File | null>(null)
  const [added, setAdded] = useState<File | null>(null)
  const [pages, setPages] = useState<PageItem[]>([])
  const [insertAt, setInsertAt] = useState(0)
  const [usedInsertion, setUsedInsertion] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [busyMessage, setBusyMessage] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [result, setResult] = useState<OrganizedResult | null>(null)
  const resultUrl = useRef<string | null>(null)
  const draggedId = useRef<string | null>(null)

  useEffect(() => () => { if (resultUrl.current) URL.revokeObjectURL(resultUrl.current) }, [])

  function clearResult() {
    if (resultUrl.current) URL.revokeObjectURL(resultUrl.current)
    resultUrl.current = null
    setResult(null)
  }

  async function chooseOriginal(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    clearResult()
    setOriginal(null)
    setAdded(null)
    setPages([])
    setUsedInsertion(null)
    setBusy(true)
    setBusyMessage('Preparing page previews…')
    setError('')
    setNotice('')
    try {
      const thumbnails = await renderThumbnails(file, 'original')
      setOriginal(file)
      setAdded(null)
      setPages(thumbnails)
      setInsertAt(thumbnails.length)
      setUsedInsertion(null)
      setNotice(`${thumbnails.length} ${thumbnails.length === 1 ? 'page' : 'pages'} ready to organize.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not open this PDF.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  async function chooseAdded(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !original || added) return
    clearResult()
    setBusy(true)
    setBusyMessage('Preparing pages from the second PDF…')
    setError('')
    setNotice('')
    try {
      const thumbnails = await renderThumbnails(file, 'added')
      clearResult()
      setAdded(file)
      setPages(current => [...current.slice(0, insertAt), ...thumbnails, ...current.slice(insertAt)])
      setUsedInsertion(insertAt)
      setNotice(`${thumbnails.length} ${thumbnails.length === 1 ? 'page' : 'pages'} added. Review the new order below.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not open the second PDF.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  function movePage(id: string, direction: -1 | 1) {
    const index = pages.findIndex(item => item.id === id)
    const other = index + direction
    if (index < 0 || other < 0 || other >= pages.length) return
    const next = [...pages]
    ;[next[index], next[other]] = [next[other], next[index]]
    clearResult()
    setPages(next)
    setNotice(`Page moved to position ${other + 1}.`)
    setError('')
  }

  function deletePage(id: string) {
    if (pages.length <= 1) { setError('At least one page must remain. You cannot delete every page.'); return }
    const next = pages.filter(item => item.id !== id)
    clearResult()
    setPages(next)
    if (added && !next.some(item => item.source === 'added')) { setAdded(null); setUsedInsertion(null) }
    setInsertAt(Math.min(insertAt, next.length))
    setNotice('Page removed. Review the new order before downloading.')
    setError('')
  }

  function removeAdded() {
    const next = pages.filter(item => item.source !== 'added')
    clearResult()
    setPages(next)
    setAdded(null)
    setUsedInsertion(null)
    setInsertAt(Math.min(insertAt, next.length))
    setNotice('Pages from the second PDF removed.')
    setError('')
  }

  function onDragStart(event: DragEvent<HTMLElement>, id: string) {
    draggedId.current = id
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', id)
  }

  function onDrop(event: DragEvent<HTMLElement>, targetId: string) {
    event.preventDefault()
    const sourceId = draggedId.current
    draggedId.current = null
    if (!sourceId || sourceId === targetId) return
    const next = [...pages]
    const from = next.findIndex(item => item.id === sourceId)
    if (from < 0) return
    const [item] = next.splice(from, 1)
    const to = next.findIndex(page => page.id === targetId)
    if (to < 0) return
    next.splice(to, 0, item)
    clearResult()
    setPages(next)
    setNotice(`Page moved to position ${to + 1}.`)
    setError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!original) { setError('Choose one PDF to organize.'); return }
    if (!pages.length) { setError('At least one page must remain.'); return }
    clearResult()
    setBusy(true)
    setBusyMessage('Creating your organized PDF…')
    setError('')
    setNotice('')
    try {
      const blob = await organizePages(original, added, pages, usedInsertion)
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-organized.pdf', size: blob.size })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The pages could not be organized. Try again.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  return <section className="organize-page"><div className="container">
    <a className="organize-back" href="#catalog">← All tools</a>
    <div className="organize-intro"><span className="eyebrow">ORGANIZE YOUR DOCUMENTS</span><h1>Organize pages<span className="accent-dot">.</span></h1><p>Move, remove, and add pages until your document is just right.</p></div>
    <form onSubmit={handleSubmit}>
      <div className="organize-panel"><div className="organize-section-heading"><span className="organize-step">01</span><div><h2>Choose your PDF</h2><p>We’ll show each page so you can plan the new order.</p></div></div>
        <label className="organize-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseOriginal} disabled={busy} /><span className="organize-picker__icon"><Icon name="pages" /></span><strong>{original ? 'Choose a different original PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
        {original && <p className="organize-file-label"><strong>{original.name}</strong> · {fileSize(original.size)} · {pages.filter(item => item.source === 'original').length} original pages kept</p>}
      </div>

      {original && <><div className="organize-panel"><div className="organize-section-heading"><span className="organize-step">02</span><div><h2>Add pages from another PDF</h2><p>Choose where its pages go. You can rearrange them afterward.</p></div></div>
        {added ? <div className="organize-added-file"><div><strong>{added.name}</strong><span>{fileSize(added.size)} · {pages.filter(item => item.source === 'added').length} pages kept</span></div><button type="button" onClick={removeAdded} disabled={busy}>Remove second PDF</button></div> : <div className="organize-add-controls"><label htmlFor="organize-insert">Insert pages</label><select id="organize-insert" value={insertAt} onChange={event => setInsertAt(Number(event.target.value))} disabled={busy}>{Array.from({ length: pages.length + 1 }, (_, index) => <option key={index} value={index}>{index === 0 ? 'At the beginning' : `After current page ${index}`}</option>)}</select><label className="organize-add-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseAdded} disabled={busy} />Choose second PDF</label></div>}
      </div>

      <div className="organize-panel"><div className="organize-section-heading"><span className="organize-step">03</span><div><h2>Preview your new order</h2><p>Drag thumbnails to reorder, or use their up and down buttons. Delete pages you don’t need.</p></div></div>
        <p className="organize-page-count">{pages.length} {pages.length === 1 ? 'page' : 'pages'} in your new PDF</p>
        <ol className="organize-grid">{pages.map((item, index) => <PageThumbnail key={item.id} item={item} position={index + 1} total={pages.length} busy={busy} onMove={movePage} onDelete={deletePage} onDragStart={onDragStart} onDragOver={event => event.preventDefault()} onDrop={onDrop} />)}</ol>
      </div></>}

      {busy && <p className="organize-status" role="status">{busyMessage}</p>}
      {notice && !busy && <p className="organize-status" role="status">{notice}</p>}
      {error && <div className="organize-message organize-message--error" role="alert"><strong>Couldn’t organize these pages</strong><p>{error}</p></div>}
      {original && <div className="organize-action-panel"><div><strong>Ready to make your PDF?</strong><p>The original files stay unchanged. Your chosen order becomes a new document.</p></div><button type="submit" disabled={busy || !pages.length}>{busy ? 'Creating PDF…' : 'Create organized PDF'}</button></div>}
      {result && <div className="organize-success" role="status"><span className="organize-success__icon">✓</span><div><h2>Your PDF is ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download organized PDF</a></div>}
    </form>
    <p className="organize-privacy">Uploads are removed from temporary server storage after processing. Abandoned files are cleared after 15 minutes at startup or on later requests.</p>
  </div></section>
}
