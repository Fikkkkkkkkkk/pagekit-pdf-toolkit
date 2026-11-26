import { UsageHint } from '../../shared/components/UsageHint'
import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Icon } from '../../shared/components/Icon'
import { PdfProgress } from '../../shared/components/PdfProgress'
import { usePdfProgress } from '../../shared/components/usePdfProgress'
import { protectPdf } from './api'
import type { ProtectedResult } from './types'
import './protect-pdf.css'

const MAX_FILE_BYTES = 25 * 1024 * 1024

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(2)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function ProtectPdfPage() {
  const [file, setFile] = useState<File | null>(null)
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ProtectedResult | null>(null)
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
    setError('')
    setFile(null)
    if (!chosen.name.toLowerCase().endsWith('.pdf')) { setError('Choose a file with a .pdf extension.'); return }
    if (!chosen.size) { setError('This PDF is empty. Choose a readable file.'); return }
    if (chosen.size > MAX_FILE_BYTES) { setError('The PDF is over the 25 MB limit.'); return }
    setFile(chosen)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    if (!file) { setError('Choose one PDF to protect.'); return }
    if (!password.trim()) { setError('Enter a password to open the protected PDF.'); return }
    if (password !== confirmation) { setError('The passwords do not match. Enter the same password twice.'); return }
    clearResult()
    setError('')
    setBusy(true)
    try {
      const blob = await progress.run((callbacks, signal) => protectPdf(file, password, confirmation, callbacks, signal))
      const url = URL.createObjectURL(blob)
      resultUrl.current = url
      setResult({ url, name: 'PageKit-protected.pdf', size: blob.size })
      setPassword('')
      setConfirmation('')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The PDF could not be protected. Try again.')
    } finally {
      setBusy(false)
    }
  }

  return <section className="protect-page"><div className="container">
    <a className="protect-back" href="#catalog">← All tools</a>
    <div className="protect-intro"><span className="eyebrow">SECURITY & REVIEW</span><h1>Protect PDF<span className="accent-dot">.</span></h1><p>Create a copy that asks for your password before opening.</p></div>
    <form onSubmit={handleSubmit}>
      <div className="usage-layout">
        <div className="protect-panel"><div className="protect-heading"><span className="protect-step">01</span><div><h2>Choose your PDF</h2><p>Your original stays unchanged. Choose an unlocked PDF.</p></div></div>
          <label className="protect-picker"><input type="file" accept=".pdf,application/pdf" onChange={chooseFile} disabled={busy} /><span className="protect-picker__icon"><Icon name="lock" /></span><strong>{file ? 'Choose a different PDF' : 'Choose a PDF file'}</strong><span>PDF only · up to 25 MB</span></label>
          {file && <p className="protect-file"><strong>{file.name}</strong> · {fileSize(file.size)}</p>}
        </div>
        <UsageHint icon="lock" title="Keep the password safe" steps={[{ title: 'Start with an unlocked PDF', detail: 'The original file stays as it is.' }, { title: 'Set a password', detail: 'Enter it twice and keep it somewhere safe.' }, { title: 'Check the copy', detail: 'Open the download to confirm it asks for the password.' }]} />
      </div>
      {file && <div className="protect-panel"><div className="protect-heading"><span className="protect-step">02</span><div><h2>Set an opening password</h2><p>Anyone opening the new PDF will need this password. Keep a copy somewhere safe.</p></div></div>
        <div className="protect-fields"><label>Password<input type={showPassword ? 'text' : 'password'} value={password} onChange={event => { setPassword(event.target.value); clearResult(); setError('') }} autoComplete="new-password" disabled={busy} required /></label><label>Confirm password<input type={showPassword ? 'text' : 'password'} value={confirmation} onChange={event => { setConfirmation(event.target.value); clearResult(); setError('') }} autoComplete="new-password" disabled={busy} required /></label></div>
        <label className="protect-show"><input type="checkbox" checked={showPassword} onChange={event => setShowPassword(event.target.checked)} disabled={busy} /> Show passwords</label>
        <p className="protect-note">PageKit uses AES-256 encryption locally. It does not save your password. A lost password cannot be recovered by PageKit.</p>
      </div>}
      <PdfProgress state={progress.state} onCancel={progress.cancel} />
      {error && <div className="protect-error" role="alert"><strong>Could not protect this PDF</strong><p>{error}</p></div>}
      {file && <div className="protect-action"><div><strong>Ready to protect your PDF?</strong><p>The protected copy will be a separate download.</p></div><button type="submit" disabled={busy}>{busy ? 'Protecting PDF…' : 'Protect PDF'}</button></div>}
      {result && <div className="protect-result" role="status"><span aria-hidden="true">✓</span><div><h2>Your protected PDF is ready</h2><p>{result.name} · {fileSize(result.size)}</p></div><a href={result.url} download={result.name}>Download protected PDF</a></div>}
    </form>
    <p className="protect-privacy">Your upload is removed from temporary server storage after processing. Abandoned files are cleared after 15 minutes at startup or on later requests.</p>
  </div></section>
}
