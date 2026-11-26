import type { PdfProgressState } from './progressTypes'
import './pdf-progress.css'

export function PdfProgress({ state, onCancel }: { state: PdfProgressState; onCancel: () => void }) {
  if (state.stage === 'idle') return null
  const percent = state.stage === 'complete' ? 100 : state.stage === 'uploading'
    ? state.uploadPercent === 100 ? null : state.uploadPercent : state.work && state.work.total > 0
      ? Math.min(99, Math.floor(state.work.completed / state.work.total * 100)) : null
  const label = state.stage === 'uploading' ? state.uploadPercent === 100 ? 'Upload complete' : 'Uploading PDF'
    : state.stage === 'complete' ? 'Output ready' : state.work?.phase || 'Preparing PDF'
  const detail = state.stage === 'uploading'
    ? state.uploadPercent === 100 ? 'All upload bytes sent. Preparing to process the PDF.' : 'Upload bytes sent'
    : state.stage === 'complete' ? 'The output is ready to download.' : state.work?.total
      ? `${state.work.completed} of ${state.work.total} work units complete` : 'Counting work units...'

  return <div className="pdf-progress" role="status" aria-live="polite">
    <div className="pdf-progress__heading"><strong>{label}</strong><span>{percent === null ? state.stage === 'uploading' && state.uploadPercent === 100 ? 'Preparing...' : 'Measuring...' : `${percent}%`}</span></div>
    <progress max={100} value={percent ?? undefined} aria-label={`${label} progress`} />
    <div className="pdf-progress__footer"><span>{detail}</span>{state.stage !== 'complete' && <button type="button" onClick={onCancel}>Cancel</button>}</div>
  </div>
}
