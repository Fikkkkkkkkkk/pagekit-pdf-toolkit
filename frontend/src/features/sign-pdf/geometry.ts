import type { Placement } from './types'

const clamp = (value: number, lower: number, upper: number) => Math.max(lower, Math.min(upper, value))

/** Constrain the entire rotated image, rather than only its unrotated box. */
export function fitPlacement(placement: Placement, pageWidth: number, pageHeight: number): Placement {
  const radians = placement.angle * Math.PI / 180
  const cosine = Math.abs(Math.cos(radians))
  const sine = Math.abs(Math.sin(radians))
  const bounds = (width: number, height: number) => ({
    halfX: (cosine * width + sine * height * pageHeight / pageWidth) / 2,
    halfY: (sine * width * pageWidth / pageHeight + cosine * height) / 2,
  })
  const initial = bounds(placement.width, placement.height)
  const scale = Math.min(1, .999999 / (2 * initial.halfX), .999999 / (2 * initial.halfY))
  const width = placement.width * scale
  const height = placement.height * scale
  const { halfX, halfY } = bounds(width, height)
  const allowedHalfX = Math.max(halfX, width / 2)
  const allowedHalfY = Math.max(halfY, height / 2)
  const centerX = clamp(placement.x + placement.width / 2, allowedHalfX, 1 - allowedHalfX)
  const centerY = clamp(placement.y + placement.height / 2, allowedHalfY, 1 - allowedHalfY)
  return { ...placement, width, height, x: clamp(centerX - width / 2, 0, 1 - width), y: clamp(centerY - height / 2, 0, 1 - height) }
}
