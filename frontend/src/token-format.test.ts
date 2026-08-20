import { describe, expect, it } from 'vitest'
import { exactTokenCountLabel, formatTokenCount } from './token-format'

describe('settings token formatting', () => {
  it('preserves unavailable and existing unscaled, thousands, and millions output', () => {
    expect(formatTokenCount(null)).toBe('Unavailable')
    expect(formatTokenCount(999)).toBe('999')
    expect(formatTokenCount(1_499)).toBe('1K')
    expect(formatTokenCount(1_500)).toBe('2K')
    expect(formatTokenCount(2_066_100)).toBe('2.07M')
  })

  it('uses billions for billion-scale lifetime and peak-daily values', () => {
    const lifetimeTokens = 12_345_678_901
    const peakDailyTokens = 1_004_000_000

    expect(formatTokenCount(lifetimeTokens)).toBe('12.35B')
    expect(formatTokenCount(peakDailyTokens)).toBe('1.00B')
  })

  it('provides the exact count for accessible text and hover disclosure', () => {
    expect(exactTokenCountLabel(null)).toBe('Unavailable')
    expect(exactTokenCountLabel(1)).toBe('1 token')
    expect(exactTokenCountLabel(12_345_678_901)).toBe('12,345,678,901 tokens')
  })
})
