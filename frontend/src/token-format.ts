const exactTokenFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 20,
  useGrouping: true,
})

export function formatTokenCount(value: number | null): string {
  if (value === null) return 'Unavailable'
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`
  if (value >= 1_000) return `${Math.round(value / 1_000)}K`
  return String(value)
}

export function exactTokenCountLabel(value: number | null): string {
  if (value === null) return 'Unavailable'
  return `${exactTokenFormatter.format(value)} ${value === 1 ? 'token' : 'tokens'}`
}
