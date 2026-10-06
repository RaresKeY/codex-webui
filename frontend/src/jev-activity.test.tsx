import { renderToStaticMarkup } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { loadJevActivity, loadJevTurn } from './api'
import { activityStatus, mergeActivity, type JevActivity } from './jev-activity'
import { JevActivityPage } from './JevActivityPage'

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
    expect(await loadJevActivity(3)).toEqual({ data: [record], nextCursor: 1 })
    expect(await loadJevTurn(1)).toMatchObject({ status: 'completed' })
    expect(fetch.mock.calls.map(call => call[0])).toEqual(['/api/jev/activity?before=3', '/api/jev/activity/1/turn'])
    expect(fetch.mock.calls.every(call => call[1].method === undefined)).toBe(true)
  })

  it('rejects unsupported activity and turn states instead of claiming success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ data: [{ ...record, status: 'invented' }], nextCursor: null })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'invented' }))))
    await expect(loadJevActivity()).rejects.toThrow('could not be read')
    await expect(loadJevTurn(1)).rejects.toThrow('unavailable')
  })

  it('renders an accessible loading state with navigation and history boundaries', () => {
    const html = renderToStaticMarkup(<JevActivityPage chats={[]} onOpen={async () => {}} onMenu={() => {}} leftOpen={false} />)
    expect(html).toContain('Jev activity')
    expect(html).toContain('role="status"')
    expect(html).toContain('earlier turns have no routing record')
    expect(html).toContain('Expand conversations')
  })
})
