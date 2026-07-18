import { describe, expect, it } from 'vitest'
import { clamp, formatPercent } from './utils'

describe('format helpers', () => {
  it('formats signed percentages', () => {
    expect(formatPercent(3.1415)).toBe('+3.14%')
    expect(formatPercent(-2)).toBe('-2.00%')
  })

  it('clamps scores', () => {
    expect(clamp(105, 0, 100)).toBe(100)
    expect(clamp(-5, 0, 100)).toBe(0)
  })
})
