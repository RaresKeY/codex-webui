import type { Conversation, LiveUpdate } from './types'

export function contextUsage(value: unknown): Pick<LiveUpdate, 'contextPercent' | 'contextUsedTokens' | 'contextWindowTokens'> {
  if (!value || typeof value !== 'object') return {}
  const usage = value as Record<string, unknown>
  const last = usage.last && typeof usage.last === 'object' ? usage.last as Record<string, unknown> : {}
  const used = last.totalTokens ?? last.total_tokens
  const limit = usage.modelContextWindow ?? usage.model_context_window
  if (typeof used !== 'number' || !Number.isSafeInteger(used) || used < 0) return {}
  if (typeof limit !== 'number' || !Number.isSafeInteger(limit) || limit <= 0) return { contextUsedTokens: used }
  return { contextUsedTokens: used, contextWindowTokens: limit, contextPercent: Math.min(100, Math.round(used / limit * 100)) }
}

export function contextUsageLabel(conversation: Conversation): string {
  if (conversation.contextUsedTokens === undefined) return 'Context usage has not been reported by Codex yet.'
  const used = conversation.contextUsedTokens.toLocaleString('en-US')
  if (conversation.contextWindowTokens === undefined) return `${used} tokens used · Total context unavailable`
  const total = conversation.contextWindowTokens.toLocaleString('en-US')
  const remaining = Math.max(0, conversation.contextWindowTokens - conversation.contextUsedTokens).toLocaleString('en-US')
  return `Context ${conversation.contextPercent}% used · ${used} / ${total} tokens · ${remaining} remaining`
}
