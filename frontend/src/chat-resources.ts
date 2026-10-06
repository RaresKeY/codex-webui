import type { StreamEvent } from './types'

export function safeWebsite(value: unknown): string | null {
  if (typeof value !== 'string' || value.length > 2048) return null
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch { return null }
}

export function chatResources(events: StreamEvent[]) {
  const sources = new Map<string, { url: string; title: string }>()
  const outputs = new Map<string, { id: string; title: string }>()
  for (const event of events) {
    if (event.role === 'user') continue
    for (const source of event.sources ?? []) {
      const url = safeWebsite(source.url)
      if (url && sources.size < 100) sources.set(url, { url, title: source.title.slice(0, 300) })
    }
    if (event.kind === 'message') {
      for (const match of event.content.matchAll(/(?<!!)\[([^\]\n]{1,300})\]\((https?:\/\/[^\s)]{1,2048})\)/g)) {
        const url = safeWebsite(match[2])
        if (url && sources.size < 100) sources.set(url, { url, title: match[1] })
      }
    }
    for (const path of event.state === 'failed' ? [] : event.outputPaths ?? []) if (outputs.size < 100) outputs.set(path, { id: path, title: path.split('/').at(-1) || path })
    if (outputs.size < 100 && event.kind === 'image' && event.images?.some(image => image.alt === 'Generated image') && event.state !== 'failed') outputs.set(event.id, { id: event.id, title: 'Generated image' })
  }
  return { sources: [...sources.values()], outputs: [...outputs.values()] }
}

export type TurnFeedEntry = { type: 'event'; event: StreamEvent } | { type: 'work'; id: string; events: StreamEvent[] }
export function groupTurnFeed(events: StreamEvent[]): TurnFeedEntry[] {
  const entries: TurnFeedEntry[] = [], work = new Map<string, Extract<TurnFeedEntry, { type: 'work' }>>()
  for (const event of events) {
    const turnId = typeof event.meta?.turnId === 'string' ? event.meta.turnId : ''
    const intermediate = ['reasoning', 'command', 'file', 'search'].includes(event.kind) || event.kind === 'message' && event.meta?.phase === 'commentary'
    if (turnId && intermediate && !event.meta?.jevActivityId) {
      let group = work.get(turnId)
      if (!group) { group = { type: 'work', id: turnId, events: [] }; work.set(turnId, group); entries.push(group) }
      group.events.push(event)
    } else entries.push({ type: 'event', event })
  }
  return entries
}

export function workLabel(events: StreamEvent[], active: boolean): string {
  if (active) return 'Working…'
  const duration = events.find(event => typeof event.meta?.turnDurationMs === 'number')?.meta?.turnDurationMs
  return typeof duration === 'number' && Number.isFinite(duration) && duration >= 0 ? duration < 1000 ? 'Worked for <1s' : `Worked for ${Math.round(duration / 1000)}s` : 'Worked'
}

// The native fork boundary is a whole turn, so only its last visible reply can
// represent “from here”; older unknown-phase interim messages stay readable.
export function isResponseBranchPoint(events: StreamEvent[], event: StreamEvent): boolean {
  const turnId = event.meta?.turnId
  if (typeof turnId !== 'string' || event.role !== 'assistant' || !['message', 'image'].includes(event.kind) || event.meta?.phase === 'commentary') return false
  for (let index = events.length - 1; index >= 0; index--) {
    const candidate = events[index]
    if (candidate.role === 'assistant' && ['message', 'image'].includes(candidate.kind) && candidate.meta?.phase !== 'commentary' && candidate.meta?.turnId === turnId) return candidate.id === event.id
  }
  return false
}
