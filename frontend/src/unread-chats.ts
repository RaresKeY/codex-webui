const KEY = 'codex-webui-2:unread-chats'
export function readUnreadChats(): Set<string> {
  try { const value: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]'); return new Set(Array.isArray(value) ? value.filter((id): id is string => typeof id === 'string' && id.length < 256).slice(-100) : []) } catch { return new Set() }
}
export function saveUnreadChats(ids: Set<string>): void {
  try { localStorage.setItem(KEY, JSON.stringify([...ids].slice(-100))) } catch { /* Storage may be unavailable; live state still works. */ }
}
