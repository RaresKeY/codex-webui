/** Resolve local Markdown links; canonical containment is enforced by the API. */
export function workspaceLink(href: string, cwd?: string): string | null {
  if (!href || href.startsWith('#') || href.startsWith('//') || /^[a-z][a-z\d+.-]*:/i.test(href) || Array.from(href).some(char => char.charCodeAt(0) < 32)) return null
  let path: string
  try { path = decodeURIComponent(href.split(/[?#]/, 1)[0]) } catch { return null }
  if (!path || Array.from(path).some(char => char.charCodeAt(0) < 32)) return null
  return path.startsWith('/') ? path : `${cwd || '.'}/${path}`
}
