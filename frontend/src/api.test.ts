import { describe, expect, it } from 'vitest'
import { ApiError, normalizeBackgroundTerminals, normalizeConversation, normalizeItem, normalizeThreadLifecycle, normalizeUsage, normalizeWorkspaceChanges, notificationUpdate, turnStartFailureMessage } from './api'

describe('Codex 0.147 adapters', () => {
  it('restores authoritative assistant and plan text', () => {
    expect(normalizeItem({ id: 'a1', type: 'agentMessage', text: 'Done.' }, 0)).toMatchObject({
      id: 'a1', kind: 'message', role: 'assistant', content: 'Done.',
    })
    expect(normalizeItem({ id: 'p1', type: 'plan', text: 'Inspect, then change.' }, 1)).toMatchObject({
      id: 'p1', kind: 'reasoning', title: 'Plan', content: 'Inspect, then change.',
    })
    expect(normalizeItem({ id: 'r1', type: 'reasoning', summary: ['Inspect the adapter.', 'Verify the result.'], content: ['private raw reasoning'] }, 2)).toMatchObject({
      id: 'r1', kind: 'reasoning', title: 'Reasoning summary', content: 'Inspect the adapter.\nVerify the result.',
    })
    expect(normalizeItem({ id: 'r2', type: 'reasoning', summary: [], content: ['private raw reasoning'] }, 3)).toMatchObject({
      id: 'r2', kind: 'reasoning', title: 'Reasoning summary', content: '',
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

  it('normalizes read-only terminal inventory and bounded Git changes', () => {
    expect(normalizeBackgroundTerminals({ data: [{
      itemId: 'item-1', processId: '42', command: 'pnpm test', cwd: '/workspace/app',
      osPid: 100, cpuPercent: 2.5, rssKb: 4096,
    }], unavailableReason: 'Owned elsewhere' })).toEqual({
      items: [{
        itemId: 'item-1', processId: '42', command: 'pnpm test', cwd: '/workspace/app',
        osPid: 100, cpuPercent: 2.5, rssKb: 4096,
      }],
      unavailableReason: 'Owned elsewhere',
    })
    expect(normalizeWorkspaceChanges({
      repoRoot: 'app', truncated: false,
      data: [{ path: 'app/src/main.ts', name: 'main.ts', status: 'modified' }],
    })).toMatchObject({ repoRoot: 'app', files: [{ path: 'app/src/main.ts', status: 'modified', language: 'typescript' }] })
  })

  it('maps deltas and authoritative context usage', () => {
    expect(notificationUpdate({ method: 'item/agentMessage/delta', params: { itemId: 'a1', delta: 'Hi' } })).toMatchObject({
      event: { id: 'a1', content: 'Hi', append: true },
    })
    expect(notificationUpdate({ method: 'item/reasoning/summaryTextDelta', params: { itemId: 'r1', summaryIndex: 0, delta: 'Inspect' } })).toMatchObject({
      event: { id: 'r1', content: 'Inspect', append: true },
    })
    expect(notificationUpdate({ method: 'item/reasoning/summaryPartAdded', params: { itemId: 'r1', summaryIndex: 1 } })).toMatchObject({
      event: { id: 'r1', content: '\n\n', append: true },
    })
    expect(notificationUpdate({
      method: 'thread/tokenUsage/updated',
      params: { tokenUsage: { total: { totalTokens: 25 }, modelContextWindow: 100 } },
    })).toEqual({ contextPercent: 25 })
  })

  it('maps authoritative turn lifecycle notifications separately from item progress', () => {
    expect(notificationUpdate({
      method: 'turn/started', params: { threadId: 'thread-1', turn: { id: 'turn-1', status: 'inProgress' } },
    })).toEqual({ turn: { kind: 'started', turnId: 'turn-1' } })
    expect(notificationUpdate({
      method: 'item/agentMessage/delta', params: { threadId: 'thread-1', turnId: 'turn-1', itemId: 'a1', delta: 'Hi' },
    })).toMatchObject({ turn: { kind: 'delta', turnId: 'turn-1' }, event: { state: 'running', append: true } })
    expect(notificationUpdate({
      method: 'error', params: { threadId: 'thread-1', turnId: 'turn-1', error: { message: 'temporary' }, willRetry: true },
    })).toEqual({ turn: { kind: 'error', turnId: 'turn-1', message: 'temporary', willRetry: true } })
    expect(notificationUpdate({
      method: 'turn/completed', params: { threadId: 'thread-1', turn: { id: 'turn-1', status: 'interrupted', error: null } },
    })).toEqual({ turn: { kind: 'completed', turnId: 'turn-1', status: 'interrupted', error: undefined } })
  })

  it('restores waiting and streaming lifecycle from authoritative thread history', () => {
    expect(normalizeThreadLifecycle({ thread: { turns: [{ id: 'turn-1', status: 'inProgress', items: [] }] } })).toEqual({
      phase: 'waiting', turnId: 'turn-1',
    })
    expect(normalizeThreadLifecycle({ thread: { turns: [{ id: 'turn-1', status: 'inProgress', items: [{ type: 'agentMessage', text: 'partial' }] }] } })).toEqual({
      phase: 'streaming', turnId: 'turn-1',
    })
    expect(normalizeThreadLifecycle({ thread: { turns: [{ id: 'turn-1', status: 'failed', error: { message: 'boom' } }] } })).toEqual({
      phase: 'failed', turnId: 'turn-1', error: 'boom',
    })
  })

  it('keeps first-turn failures actionable without blaming approval settings', () => {
    expect(turnStartFailureMessage(new ApiError(502, 'no rollout found for thread id new-1'))).toContain('new conversation')
    expect(turnStartFailureMessage(new ApiError(503, 'offline'))).toContain('reconnect')
    expect(turnStartFailureMessage(new Error('unknown'))).not.toContain('approval')
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

  it('maps the generated realtime SDP and transcript notifications', () => {
    expect(notificationUpdate({
      method: 'thread/realtime/sdp',
      params: { threadId: 'thread-voice', sdp: 'v=0\r\no=answer' },
    })).toEqual({
      realtime: { kind: 'sdp', threadId: 'thread-voice', sdp: 'v=0\r\no=answer' },
    })
    expect(notificationUpdate({
      method: 'thread/realtime/transcript/delta',
      params: { threadId: 'thread-voice', role: 'user', delta: 'hello' },
    }, 'voice-part-1')).toMatchObject({
      event: { id: 'voice-part-1', role: 'user', content: 'hello', append: true },
    })
    expect(notificationUpdate({
      method: 'thread/realtime/error',
      params: { threadId: 'thread-voice', message: 'backend unavailable' },
    })).toEqual({
      realtime: { kind: 'error', threadId: 'thread-voice', message: 'backend unavailable' },
    })
  })
})
