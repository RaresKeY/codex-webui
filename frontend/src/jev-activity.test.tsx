import { renderToStaticMarkup } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { loadJevActivity, loadJevTurn } from './api'
import { activityStatus, mergeActivity, jevTranscript, EMPTY_JEV_CHAT, type JevActivity } from './jev-activity'
import { JevContext } from './JevContext'
import { notificationUpdate } from './api'

const record: JevActivity = { id: 1, thread_id: 'chat', turn_id: null, source: 'auto', status: 'pending', stage: 'routing', started_at: '2026-10-06T10:00:00Z', updated_at: '2026-10-06T10:00:00Z', duration_ms: 0, decision: null }
afterEach(() => vi.unstubAllGlobals())

describe('Jev activity', () => {
  it('updates existing records while retaining older pages and ordering new attempts', () => {
    const stopped = { ...record, status: 'stopped' as const }
    expect(mergeActivity([record], [stopped, { ...record, id: 2 }])).toEqual([{ ...record, id: 2 }, stopped])
    expect(record.status).toBe('pending')
    expect(activityStatus({ ...record, status: 'submitted', turn_id: 't1' })).toBe('Turn submitted')
  })

  it('reads bounded older pages and checks actual native turns without mutations', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ data: [record], nextCursor: 1 })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ threadId: 'chat', turnId: 't1', status: 'completed' })))
    vi.stubGlobal('fetch', fetch)
    expect(await loadJevActivity('chat', 3)).toEqual({ data: [record], nextCursor: 1 })
    expect(await loadJevTurn(1)).toMatchObject({ status: 'completed' })
    expect(fetch.mock.calls.map(call => call[0])).toEqual(['/api/threads/chat/jev/activity?before=3', '/api/jev/activity/1/turn'])
    expect(fetch.mock.calls.every(call => call[1].method === undefined)).toBe(true)
  })

  it('rejects unsupported activity and turn states instead of claiming success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ data: [{ ...record, status: 'invented' }], nextCursor: null })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'invented' }))))
    await expect(loadJevActivity('chat')).rejects.toThrow('could not be read')
    await expect(loadJevTurn(1)).rejects.toThrow('unavailable')
  })

  it('renders an accessible loading state with navigation and history boundaries', () => {
    const html = renderToStaticMarkup(<JevContext threadId="chat" state={{ ...EMPTY_JEV_CHAT, loading: true }} onLoad={() => {}} />)
    expect(html).toContain('Jev process')
    expect(html).toContain('role="status"')
    expect(html).toContain('Earlier turns have no reconstructed routing record')
    expect(html).toContain('Reload Jev history')
  })
})


describe('per-turn Jev projection', () => {
  it('binds historical runs between their user input and output without creating manual or preview steps', () => {
    const events = [{ id: 'u', kind: 'message' as const, role: 'user' as const, content: 'ask', timestamp: '', meta: { turnId: 't1' } }, { id: 'a', kind: 'message' as const, role: 'assistant' as const, content: 'reply', timestamp: '', meta: { turnId: 't1' } }]
    const result = jevTranscript(events, [{ ...record, status: 'submitted', turn_id: 't1' }, { ...record, id: 2, source: 'manual' }, { ...record, id: 3, source: 'preview' }])
    expect(result.map(event => event.id)).toEqual(['u', 'jev-1', 'a'])
    expect(events).toHaveLength(2)
  })
  it('does not replace newer streamed progress with an older hydration response', () => {
    const current = { ...record, status: 'submitted' as const, updated_at: '2026-10-06T10:00:02Z' }
    expect(mergeActivity([current], [record])).toEqual([current])
  })
  it('accepts only correctly scoped activity events', () => {
    expect(notificationUpdate({ method: 'webui/jevActivity', params: { threadId: 'chat', activity: record } })).toEqual({ jevActivity: record })
    expect(notificationUpdate({ method: 'webui/jevActivity', params: { threadId: 'other', activity: record } })).toBeNull()
  })
  it('rejects another chat’s records from a history read', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: [{ ...record, thread_id: 'other' }], nextCursor: null }))))
    await expect(loadJevActivity('chat')).rejects.toThrow('could not be read')
  })
})
