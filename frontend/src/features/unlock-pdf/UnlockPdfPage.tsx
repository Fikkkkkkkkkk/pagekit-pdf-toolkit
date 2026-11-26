import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { PdfProgress } from '../../shared/components/PdfProgress'
import { usePdfProgress } from '../../shared/components/usePdfProgress'
import { unlockPdf } from './api'
import type { UnlockedResult } from './types'
import './unlock-pdf.css'

const MAX_FILE_BYTES = 25 * 1024 * 1024

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(2)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function UnlockPdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<UnlockedResult | null>(null)
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
    const chosen = event.target.files?.[0]
    event.target.value = ''
    if (!chosen) return
    clearResult()
    setFile(null)
    setPassword('')
    setError('')
    if (!chosen.name.toLowerCase().endsWith('.pdf')) { setError('Choose a file with a .pdf extension.'); return }
    if (!chosen.size) { setError('This PDF is empty. Choose a readable file.'); return }
    if (chosen.size > MAX_FILE_BYTES) { setError('The PDF is over the 25 MB limit.'); return }
    setFile(chosen)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    if (!file) { setError('Choose a password-protected PDF.'); return }
    if (!password.trim()) { setError('Enter the known password for this PDF.'); return }
    clearResult()
    setError('')
    setBusy(true)
    try {
      const blob = await progress.run((callbacks, signal) => unlockPdf(file, password, callbacks, signal))
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-unlocked.pdf', size: blob.size })
      setPassword('')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The PDF could not be unlocked. Check the password and try again.')
    } finally {
      setBusy(false)
    }
  }

  return <section className="unlock-page"><div className="container">
    <a className="unlock-back" href="#catalog">← All tools</a>
    <div className="unlock-intro"><span className="eyebrow">SECURITY & REVIEW</span><h1>Unlock PDF<span className="accent-dot">.</span></h1><p>Use the password you know to make a copy that opens without it.</p></div>
    <form onSubmit={handleSubmit}>
      <div className="unlock-panel"><div className="unlock-heading"><span className="unlock-step">01</span><div><h2>Choose your locked PDF</h2><p>Upload one password-protected PDF. Your original stays unchanged.</p></div></div>
        <label className="unlock-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseFile} disabled={busy} /><span className="unlock-picker__icon"><Icon name="unlock" /></span><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
        {file && <p className="unlock-file"><strong>{file.name}</strong> · {fileSize(file.size)}</p>}
      </div>
      {file && <div className="unlock-panel"><div className="unlock-heading"><span className="unlock-step">02</span><div><h2>Enter its opening password</h2><p>PageKit uses only the password you provide. It cannot guess or recover one.</p></div></div>
        <label className="unlock-password">Known password<input type={showPassword ? 'text' : 'password'} value={password} onChange={event => { setPassword(event.target.value); clearResult(); setError('') }} autoComplete="off" disabled={busy} required /></label>
        <label className="unlock-show"><input type="checkbox" checked={showPassword} onChange={event => setShowPassword(event.target.checked)} disabled={busy} /> Show password</label>
        <p className="unlock-note">The unlocked copy can be opened by anyone who receives it. Keep it somewhere appropriate for its contents. PageKit does not log or save your password.</p>
      </div>}
      <PdfProgress state={progress.state} onCancel={progress.cancel} />
      {error && <div className="unlock-error" role="alert"><strong>Could not unlock this PDF</strong><p>{error}</p></div>}
      {file && <div className="unlock-action"><div><strong>Ready to unlock your PDF?</strong><p>PageKit will create a separate copy without an opening password.</p></div><button type="submit" disabled={busy}>{busy ? 'Unlocking PDF…' : 'Unlock PDF'}</button></div>}
      {result && <div className="unlock-result" role="status"><span aria-hidden="true">✓</span><div><h2>Your unlocked PDF is ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download unlocked PDF</a></div>}
    </form><p className="unlock-privacy">Your upload is removed from temporary server storage after processing. Abandoned files are cleared after 15 minutes at startup or on later requests.</p>
  </div></section>
}
