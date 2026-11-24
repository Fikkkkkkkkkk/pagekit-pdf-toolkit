import type { DragEvent } from 'react'
import type { PageItem } from './types'

type Props = {
  item: PageItem
  position: number
  total: number
  busy: boolean
  onMove: (id: string, direction: -1 | 1) => void
  onDelete: (id: string) => void
  onDragStart: (event: DragEvent<HTMLElement>, id: string) => void
  onDragOver: (event: DragEvent<HTMLElement>) => void
  onDrop: (event: DragEvent<HTMLElement>, id: string) => void
}

export function PageThumbnail({ item, position, total, busy, onMove, onDelete, onDragStart, onDragOver, onDrop }: Props) {
  const label = `${item.source === 'original' ? 'Original' : 'Added'} PDF page ${item.page}`
  return <li className="organize-page-card" draggable={!busy} onDragStart={event => onDragStart(event, item.id)} onDragOver={onDragOver} onDrop={event => onDrop(event, item.id)}>
    <div className="organize-page-card__preview"><span className="organize-page-card__position">{position}</span><img src={item.thumbnail} alt={`Preview of ${label}`} /></div>
    <div className="organize-page-card__info"><strong>{label}</strong><span>Position {position} of {total}</span></div>
    <div className="organize-page-card__actions"><button type="button" disabled={busy || position === 1} onClick={() => onMove(item.id, -1)} aria-label={`Move ${label} up`}>↑</button><button type="button" disabled={busy || position === total} onClick={() => onMove(item.id, 1)} aria-label={`Move ${label} down`}>↓</button><button type="button" disabled={busy} onClick={() => onDelete(item.id)} aria-label={`Delete ${label}`}>×</button></div>
  </li>
}
