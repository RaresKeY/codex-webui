import { describe, expect, it } from 'vitest'
import { IDLE_TURN, isTurnActive, mergeStreamEvent, reduceTurnLifecycle, settleStreamEvents, stampAssistantMessageModel } from './turn-lifecycle'
import type { StreamEvent } from './types'

describe('turn lifecycle', () => {
  it('covers submitted, waiting, first delta, ongoing deltas, and completion', () => {
    let turn = reduceTurnLifecycle(IDLE_TURN, { type: 'submitted', requestId: 'request-1' })
    expect(turn).toEqual({ phase: 'waiting', requestId: 'request-1' })
    turn = reduceTurnLifecycle(turn, { type: 'started', turnId: 'turn-1' })
    expect(turn).toMatchObject({ phase: 'waiting', turnId: 'turn-1' })
    turn = reduceTurnLifecycle(turn, { type: 'delta', turnId: 'turn-1' })
    expect(turn.phase).toBe('streaming')
    turn = reduceTurnLifecycle(turn, { type: 'delta', turnId: 'turn-1' })
    expect(isTurnActive(turn)).toBe(true)
    turn = reduceTurnLifecycle(turn, { type: 'completed', turnId: 'turn-1', status: 'completed' })
    expect(turn).toEqual({ phase: 'completed', turnId: 'turn-1', error: undefined })
    expect(isTurnActive(turn)).toBe(false)
  })

  it.each(['failed', 'interrupted'] as const)('clears activity for a %s terminal turn', status => {
    const active = { phase: 'waiting', turnId: 'turn-1' } as const
    const terminal = reduceTurnLifecycle(active, { type: 'completed', turnId: 'turn-1', status })
    expect(terminal.phase).toBe(status)
    expect(isTurnActive(terminal)).toBe(false)
  })

  it('keeps a retryable error active until the authoritative terminal event', () => {
    const active = reduceTurnLifecycle(
      { phase: 'streaming', turnId: 'turn-1' },
      { type: 'error', turnId: 'turn-1', message: 'temporary', willRetry: true },
    )
    expect(active).toMatchObject({ phase: 'streaming', error: 'temporary' })
    expect(isTurnActive(active)).toBe(true)
  })

  it('does not resurrect a completed turn when the HTTP acknowledgement arrives late', () => {
    const terminal = { phase: 'completed', turnId: 'turn-1', requestId: 'request-1' } as const
    expect(reduceTurnLifecycle(terminal, { type: 'acknowledged', requestId: 'request-1', turnId: 'turn-1' })).toBe(terminal)
    expect(reduceTurnLifecycle(terminal, { type: 'delta', turnId: 'turn-1' })).toBe(terminal)
  })

  it('hydrates an in-progress snapshot after reconnect', () => {
    const hydrated = reduceTurnLifecycle(
      { phase: 'failed', turnId: 'old-turn' },
      { type: 'snapshot', lifecycle: { phase: 'streaming', turnId: 'live-turn' } },
    )
    expect(hydrated).toEqual({ phase: 'streaming', turnId: 'live-turn' })
  })
})

describe('stream event merging', () => {
  const delta = (content: string): StreamEvent => ({
    id: 'assistant-1', kind: 'message', role: 'assistant', content,
    timestamp: 'Now', state: 'running', append: true,
  })

  it('appends transcript deltas into one assistant message and accepts the final item once', () => {
    let events = mergeStreamEvent([], { ...delta(''), append: false })
    events = mergeStreamEvent(events, delta('Hel'))
    events = mergeStreamEvent(events, delta('lo'))
    events = mergeStreamEvent(events, { ...delta('Hello'), state: 'done', append: false })
    expect(events).toHaveLength(1)
    expect(events[0]).toMatchObject({ content: 'Hello', state: 'done', append: false })
  })

  it('preserves streamed readable reasoning when a completed item has no summary text', () => {
    let events = mergeStreamEvent([], {
      id: 'reasoning-1', kind: 'reasoning', title: 'Reasoning summary', content: 'Inspect',
      timestamp: 'Now', state: 'running', append: true,
    })
    events = mergeStreamEvent(events, {
      id: 'reasoning-1', kind: 'reasoning', title: 'Reasoning summary', content: '',
      timestamp: 'Now', state: 'done', append: false,
    })
    expect(events[0]).toMatchObject({ content: 'Inspect', state: 'done', append: false })
  })

  it('settles unfinished item affordances at terminal turn completion but leaves realtime transcripts alone', () => {
    const settled = settleStreamEvents([
      delta('partial'),
      { ...delta('voice'), id: 'voice', meta: { realtime: true } },
      { id: 'command', kind: 'command', content: 'pwd', timestamp: 'Now', state: 'running' },
    ], 'interrupted')
    expect(settled.map(event => event.state)).toEqual(['failed', 'running', 'failed'])
  })

  it('reconciles the authoritative user item with its optimistic message', () => {
    const optimistic: StreamEvent = {
      id: 'local-user', kind: 'message', role: 'user', content: 'Inspect this', timestamp: 'Now',
      meta: { optimistic: true },
    }
    const merged = mergeStreamEvent([optimistic], {
      id: 'server-user', kind: 'message', role: 'user', content: 'Inspect this', timestamp: 'Now', state: 'done',
    })
    expect(merged).toHaveLength(1)
    expect(merged[0]).toMatchObject({ id: 'server-user', content: 'Inspect this', state: 'done' })
    expect(merged[0].meta?.optimistic).toBeUndefined()
  })

  it('stamps assistant model provenance once without relabeling an active stream', () => {
    let events = stampAssistantMessageModel(mergeStreamEvent([], delta('Hel')), 'gpt-5.6-sol')
    events = stampAssistantMessageModel(mergeStreamEvent(events, delta('lo')), 'gpt-5.6-terra')
    expect(events[0]).toMatchObject({ content: 'Hello', meta: { model: 'gpt-5.6-sol' } })

    const user = { id: 'user-1', kind: 'message', role: 'user', content: 'Hi', timestamp: 'Now' } satisfies StreamEvent
    expect(stampAssistantMessageModel([user], 'gpt-5.6-sol')[0].meta).toBeUndefined()
  })
})
