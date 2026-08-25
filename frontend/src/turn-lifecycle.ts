import type { StreamEvent, TurnLifecycle } from './types'

export const IDLE_TURN: TurnLifecycle = { phase: 'idle' }

export type TurnAction =
  | { type: 'submitted'; requestId: string }
  | { type: 'acknowledged'; requestId: string; turnId?: string }
  | { type: 'started'; turnId: string }
  | { type: 'activity'; turnId?: string }
  | { type: 'delta'; turnId?: string }
  | { type: 'error'; turnId?: string; message: string; willRetry: boolean }
  | { type: 'completed'; turnId: string; status: 'completed' | 'interrupted' | 'failed'; error?: string }
  | { type: 'request-failed'; requestId: string; message: string }
  | { type: 'snapshot'; lifecycle: TurnLifecycle }

export function isTurnActive(turn: TurnLifecycle): boolean {
  return turn.phase === 'waiting' || turn.phase === 'streaming'
}

function isTerminal(turn: TurnLifecycle): boolean {
  return turn.phase === 'completed' || turn.phase === 'interrupted' || turn.phase === 'failed'
}

function belongsToCurrent(turn: TurnLifecycle, turnId?: string): boolean {
  return !turn.turnId || !turnId || turn.turnId === turnId
}

export function reduceTurnLifecycle(turn: TurnLifecycle, action: TurnAction): TurnLifecycle {
  switch (action.type) {
    case 'submitted':
      return { phase: 'waiting', requestId: action.requestId }
    case 'acknowledged':
      if (!isTurnActive(turn) || turn.requestId !== action.requestId) return turn
      if (turn.turnId && action.turnId && turn.turnId !== action.turnId) return turn
      return { ...turn, turnId: action.turnId ?? turn.turnId }
    case 'started': {
      if (isTerminal(turn) && turn.turnId === action.turnId) return turn
      const sameTurn = belongsToCurrent(turn, action.turnId)
      return {
        phase: sameTurn && turn.phase === 'streaming' ? 'streaming' : 'waiting',
        turnId: action.turnId,
        requestId: sameTurn ? turn.requestId : undefined,
      }
    }
    case 'activity':
      if (isTerminal(turn) && belongsToCurrent(turn, action.turnId)) return turn
      if (isTurnActive(turn) && belongsToCurrent(turn, action.turnId)) {
        return { ...turn, turnId: action.turnId ?? turn.turnId }
      }
      return { phase: 'waiting', turnId: action.turnId }
    case 'delta':
      if (isTerminal(turn) && belongsToCurrent(turn, action.turnId)) return turn
      if (isTurnActive(turn) && belongsToCurrent(turn, action.turnId)) {
        return { ...turn, phase: 'streaming', turnId: action.turnId ?? turn.turnId }
      }
      return { phase: 'streaming', turnId: action.turnId }
    case 'error':
      if (isTerminal(turn) && belongsToCurrent(turn, action.turnId)) return turn
      return {
        ...turn,
        phase: isTurnActive(turn) ? turn.phase : 'waiting',
        turnId: action.turnId ?? turn.turnId,
        error: action.message,
      }
    case 'completed':
      if (isTurnActive(turn) && !belongsToCurrent(turn, action.turnId)) return turn
      return { phase: action.status, turnId: action.turnId, error: action.error ?? turn.error }
    case 'request-failed':
      if (!isTurnActive(turn) || turn.requestId !== action.requestId) return turn
      return { phase: 'failed', requestId: action.requestId, error: action.message }
    case 'snapshot':
      return action.lifecycle
  }
}

export function mergeStreamEvent(current: StreamEvent[], incoming: StreamEvent): StreamEvent[] {
  let index = current.findIndex(event => event.id === incoming.id)
  if (index < 0 && incoming.kind === 'message' && incoming.role === 'user') {
    for (let candidate = current.length - 1; candidate >= 0; candidate -= 1) {
      const event = current[candidate]
      if (event.kind === 'message' && event.role === 'user' && event.meta?.optimistic === true && event.content === incoming.content) {
        index = candidate
        break
      }
    }
  }
  if (index < 0) return [...current, { ...incoming, append: false }]
  const existing = current[index]
  const content = incoming.append
    ? `${existing.content}${incoming.content}`
    : incoming.state === 'done' && existing.content.length > incoming.content.length
      ? existing.content
      : incoming.content || existing.content
  const next = [...current]
  const meta = { ...existing.meta, ...incoming.meta }
  delete meta.optimistic
  next[index] = { ...existing, ...incoming, content, append: false, meta }
  return next
}

export function stampAssistantMessageModel(events: StreamEvent[], model: string): StreamEvent[] {
  if (!model) return events
  let changed = false
  const stamped = events.map(event => {
    if (event.kind !== 'message' || event.role === 'user' || typeof event.meta?.model === 'string') return event
    changed = true
    return { ...event, meta: { ...event.meta, model } }
  })
  return changed ? stamped : events
}

export function settleStreamEvents(events: StreamEvent[], status: 'completed' | 'interrupted' | 'failed'): StreamEvent[] {
  return events.map(event => {
    if (event.state !== 'running' || event.meta?.realtime === true) return event
    return { ...event, state: status === 'completed' ? 'done' : 'failed' }
  })
}
