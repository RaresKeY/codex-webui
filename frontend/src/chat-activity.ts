import type { Conversation, TurnSignal } from './types'
export interface ChatActivity { status: Conversation['status']; unread: boolean; turnId?: string; previousTurnIds?: string[] }
export function reduceChatActivity(current: ChatActivity | undefined, signal: TurnSignal, viewed: boolean): ChatActivity {
  const previous = current ?? { status: 'ready', unread: false }
  const previousTurnIds = previous.turnId && previous.turnId !== signal.turnId ? [...(previous.previousTurnIds ?? []), previous.turnId].slice(-20) : previous.previousTurnIds
  if (signal.turnId && previous.previousTurnIds?.includes(signal.turnId)) return previous
  if (signal.kind === 'started') return previous.turnId === signal.turnId ? previous : { status: 'running', unread: false, turnId: signal.turnId, previousTurnIds }
  if (signal.kind === 'completed') {
    if (previous.status === 'running' && previous.turnId && previous.turnId !== signal.turnId) return previous
    if (previous.turnId === signal.turnId && previous.status !== 'running') return previous
    return { status: signal.status === 'completed' ? 'ready' : signal.status === 'interrupted' ? 'paused' : 'failed', unread: signal.status === 'completed' && !viewed, turnId: signal.turnId, previousTurnIds }
  }
  if (signal.kind === 'error' && !signal.willRetry && (!previous.turnId || previous.turnId === signal.turnId)) return { ...previous, status: 'failed', unread: false }
  return previous
}

// Native idle metadata cannot erase a terminal outcome learned from an event.
export function reconcileChat(chat: Conversation, fresh: Conversation, viewed: boolean): Conversation {
  const status = fresh.status === 'ready' && (chat.status === 'failed' || chat.status === 'paused') ? chat.status : fresh.status
  return { ...chat, title: fresh.title, ...(fresh.lastTurnModel ? { lastTurnModel: fresh.lastTurnModel, lastTurnEffort: fresh.lastTurnEffort } : {}), preview: fresh.preview, updatedAt: fresh.updatedAt, status, unread: status === 'running' ? false : Boolean(chat.unread || (chat.status === 'running' && status === 'ready' && !viewed)), updatedAtEpoch: Math.max(chat.updatedAtEpoch ?? 0, fresh.updatedAtEpoch ?? 0) }
}

// A reconnect can miss the next turn/start; do not retain the previous turn ID.
export function recoverChatActivity(current: ChatActivity | undefined, status: Conversation['status']): ChatActivity | undefined {
  return status === 'running' && current && current.status !== 'running' ? { status: 'running', unread: false, previousTurnIds: [...(current.previousTurnIds ?? []), ...(current.turnId ? [current.turnId] : [])].slice(-20) } : current
}
