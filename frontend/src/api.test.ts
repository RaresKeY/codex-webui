import { describe, expect, it } from 'vitest'
import { normalizeConversation, normalizeItem, normalizeUsage, notificationUpdate } from './api'

describe('Codex 0.145 adapters', () => {
  it('restores authoritative assistant and plan text', () => {
    expect(normalizeItem({ id: 'a1', type: 'agentMessage', text: 'Done.' }, 0)).toMatchObject({
      id: 'a1', kind: 'message', role: 'assistant', content: 'Done.',
    })
    expect(normalizeItem({ id: 'p1', type: 'plan', text: 'Inspect, then change.' }, 1)).toMatchObject({
      id: 'p1', kind: 'reasoning', title: 'Plan', content: 'Inspect, then change.',
    })
  })

  it('marks pinned system-error threads as failed', () => {
    expect(normalizeConversation({ id: 't1', status: { type: 'systemError' } }).status).toBe('failed')
    expect(normalizeConversation({ id: 't2', status: { type: 'notLoaded' } }).status).toBe('ready')
  })

  it('formats file changes and completed command output', () => {
    expect(normalizeItem({
      id: 'f1', type: 'fileChange', status: 'completed',
      changes: [{ kind: 'update', path: 'src/app.ts', diff: '@@ changed @@' }],
    }, 0)?.content).toBe('update · src/app.ts\n@@ changed @@')
    expect(normalizeItem({
      id: 'c1', type: 'commandExecution', status: 'completed', command: 'pwd',
      aggregatedOutput: '/workspace\n', exitCode: 0,
    }, 0)).toMatchObject({ content: 'pwd\n/workspace\n', state: 'done', meta: { exitCode: 0 } })
  })

  it('maps deltas and authoritative context usage', () => {
    expect(notificationUpdate({ method: 'item/agentMessage/delta', params: { itemId: 'a1', delta: 'Hi' } })).toMatchObject({
      event: { id: 'a1', content: 'Hi', append: true },
    })
    expect(notificationUpdate({
      method: 'thread/tokenUsage/updated',
      params: { tokenUsage: { total: { totalTokens: 25 }, modelContextWindow: 100 } },
    })).toEqual({ contextPercent: 25 })
  })

  it('unwraps nested account usage without inventing unavailable values', () => {
    expect(normalizeUsage({
      rateLimits: { rateLimits: { primary: { usedPercent: 37 }, secondary: { usedPercent: 62 } } },
      usage: { summary: { lifetimeTokens: 1234, peakDailyTokens: null, currentStreakDays: 4 } },
    }, 3)).toMatchObject({
      fiveHourPercent: 37, weeklyPercent: 62, lifetimeTokens: 1234,
      peakDailyTokens: null, currentStreakDays: 4,
    })
  })
})
