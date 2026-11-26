import { useEffect, useRef, useState } from 'react'
import { canvasAsset } from './preview'
import type { SignatureAsset } from './types'

export function SignatureCanvas({ onSave, disabled }: { onSave: (asset: SignatureAsset) => void; disabled: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef(false)
  const [hasInk, setHasInk] = useState(false)
  useEffect(() => {
    const context = canvasRef.current?.getContext('2d')
    if (context) { context.strokeStyle = '#17213c'; context.lineWidth = 3; context.lineCap = 'round'; context.lineJoin = 'round' }
  }, [])
  const position = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    return { x: (event.clientX - rect.left) * event.currentTarget.width / rect.width,
      y: (event.clientY - rect.top) * event.currentTarget.height / rect.height }
  }
  return <div className="sign-draw"><canvas ref={canvasRef} width={640} height={220} aria-label="Draw your signature" onPointerDown={event => {
    if (disabled) return
    event.currentTarget.setPointerCapture(event.pointerId)
    drawing.current = true
    const point = position(event)
    const context = event.currentTarget.getContext('2d')!
    context.beginPath(); context.moveTo(point.x, point.y); context.lineTo(point.x + .01, point.y); context.stroke()
    setHasInk(true)
  }} onPointerMove={event => {
    if (!drawing.current) return
    const point = position(event); const context = event.currentTarget.getContext('2d')!
    context.lineTo(point.x, point.y); context.stroke()
  }} onPointerUp={() => { drawing.current = false }} onPointerCancel={() => { drawing.current = false }} />
    <div><button type="button" disabled={disabled} onClick={() => { canvasRef.current?.getContext('2d')?.clearRect(0, 0, 640, 220); setHasInk(false) }}>Clear drawing</button>
      <button type="button" disabled={disabled || !hasInk} onClick={async () => { if (canvasRef.current) onSave(await canvasAsset(canvasRef.current)) }}>Use drawing</button></div>
  </div>
}
