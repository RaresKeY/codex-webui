/** Address-bar convenience only; the backend remains the navigation authority. */
export function browserAddress(value: string): string | null {
  const address = value.trim()
  if (!address || /\s/.test(address)) return null
  try {
    const url = new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(address) ? address : `https://${address.replace(/^\/\//, '')}`)
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) return null
    return url.href
  } catch { return null }
}
