export interface JevDecision {
  model?: string
  effort?: string
  policy?: string
  modelConfidence?: number
  effortConfidence?: number
  modelProbabilities?: Record<string, number>
  effortProbabilities?: Record<string, number>
  usage?: { input_tokens: number; output_tokens: number }
  preparation?: Partial<Record<'online_search' | 'fresh_information' | 'project_context', { choice: 'yes' | 'no' | 'unclear'; confidence: number; probabilities: Record<string, number> }>>
}

export interface JevActivity {
  id: number
  thread_id: string
  turn_id: string | null
  source: 'auto' | 'manual' | 'preview'
  status: 'pending' | 'submitted' | 'classified' | 'stopped' | 'interrupted'
  stage: 'routing' | 'switching' | 'sending'
  started_at: string
  updated_at: string
  duration_ms: number | null
  decision: JevDecision | null
}

export interface JevChatState { items: JevActivity[]; cursor: number | null; loading: boolean; error: string }
export const EMPTY_JEV_CHAT: JevChatState = { items: [], cursor: null, loading: false, error: '' }

export interface JevActivityPage { data: JevActivity[]; nextCursor: number | null }
export interface JevTurn { threadId: string; turnId: string; status: 'inProgress' | 'completed' | 'interrupted' | 'failed' | 'unknown' }

export function activityStatus(item: JevActivity): string {
  if (item.status === 'pending') return { routing: item.source === 'manual' ? 'Selecting model' : 'Routing', switching: 'Applying model', sending: 'Submitting turn' }[item.stage]
  return { submitted: 'Turn submitted', classified: 'Preview complete', stopped: 'Stopped', interrupted: 'Interrupted' }[item.status]
}

export function mergeActivity(current: JevActivity[], incoming: JevActivity[]): JevActivity[] {
  const records = new Map(current.map(item => [item.id, item]))
  incoming.forEach(item => { const previous = records.get(item.id); if (!previous || item.updated_at >= previous.updated_at) records.set(item.id, item) })
  return [...records.values()].sort((a, b) => b.id - a.id)
}


export function validActivity(value: unknown): value is JevActivity {
  if (!value || typeof value !== 'object') return false
  const item = value as JevActivity
  return Number.isSafeInteger(item.id) && item.id > 0 && typeof item.thread_id === 'string'
    && ['auto', 'manual', 'preview'].includes(item.source) && ['pending', 'submitted', 'classified', 'stopped', 'interrupted'].includes(item.status)
    && ['routing', 'switching', 'sending'].includes(item.stage) && typeof item.started_at === 'string' && typeof item.updated_at === 'string'
    && (item.turn_id === null || typeof item.turn_id === 'string')
    && (item.decision === null || typeof item.decision === 'object')
}

function lastIndex(events: import('./types').StreamEvent[], matches: (event: import('./types').StreamEvent) => boolean): number {
  for (let index = events.length - 1; index >= 0; index--) if (matches(events[index])) return index
  return -1
}

export function jevTranscript(events: import('./types').StreamEvent[], records: JevActivity[]): import('./types').StreamEvent[] {
  const result = events.filter(event => !event.meta?.jevActivityId)
  for (const record of [...records].sort((a, b) => a.id - b.id)) {
    if (record.source !== 'auto') continue
    const first = record.turn_id ? result.findIndex(event => event.meta?.turnId === record.turn_id && event.role !== 'user') : -1
    const lastUser = record.turn_id ? lastIndex(result, event => event.meta?.turnId === record.turn_id && event.role === 'user') : -1
    const pendingUser = !record.turn_id && record.status === 'pending' ? lastIndex(result, event => event.role === 'user') : -1
    const index = first >= 0 ? first : lastUser >= 0 ? lastUser + 1 : pendingUser >= 0 ? pendingUser + 1 : result.length
    result.splice(index, 0, { id: `jev-${record.id}`, kind: 'status', title: 'Jev', content: activityStatus(record), timestamp: '',
      meta: { jevActivityId: record.id }, state: record.status === 'pending' ? 'running' : record.status === 'submitted' ? 'done' : 'failed' })
  }
  return result
}
