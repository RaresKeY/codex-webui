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

export interface JevActivityPage { data: JevActivity[]; nextCursor: number | null }
export interface JevTurn { threadId: string; turnId: string; status: 'inProgress' | 'completed' | 'interrupted' | 'failed' | 'unknown' }

export function activityStatus(item: JevActivity): string {
  if (item.status === 'pending') return { routing: item.source === 'manual' ? 'Selecting model' : 'Routing', switching: 'Applying model', sending: 'Submitting turn' }[item.stage]
  return { submitted: 'Turn submitted', classified: 'Preview complete', stopped: 'Stopped', interrupted: 'Interrupted' }[item.status]
}

export function mergeActivity(current: JevActivity[], incoming: JevActivity[]): JevActivity[] {
  const records = new Map(current.map(item => [item.id, item]))
  incoming.forEach(item => records.set(item.id, item))
  return [...records.values()].sort((a, b) => b.id - a.id)
}
