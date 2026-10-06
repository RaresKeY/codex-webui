import { describe, expect, it, vi } from 'vitest'
import { chatResources, groupTurnFeed, isResponseBranchPoint, safeWebsite, workLabel } from './chat-resources'
import { forkConversation, normalizeItem, notificationUpdate } from './api'
import type { StreamEvent } from './types'
const item = (id: string, kind: StreamEvent['kind'], meta = {}): StreamEvent => ({ id, kind, content: id, timestamp: 'Recently', meta: { turnId: 't1', ...meta } })
describe('turn presentation', () => {
  it('collapses only known intermediate work while keeping answers and approvals visible', () => {
    const entries = groupTurnFeed([item('user', 'message'), item('commentary', 'message', { phase: 'commentary' }), item('search', 'search'), item('approval', 'approval'), item('answer', 'message', { phase: 'final_answer' }), item('legacy', 'message'), item('next', 'reasoning', { turnId: 't2' })])
    expect(entries.map(entry => entry.type === 'work' ? entry.events.map(event => event.id) : entry.event.id)).toEqual(['user', ['commentary', 'search'], 'approval', 'answer', 'legacy', ['next']])
    expect(workLabel([item('command', 'command', { durationMs: 3000 })], false)).toBe('Worked')
    expect(workLabel([item('command', 'command', { turnDurationMs: 27000 })], false)).toBe('Worked for 27s')
    expect(workLabel([], true)).toBe('Working…')
  })
  it('accepts real website sources, deduplicates, and rejects unsafe protocols and user credentials', () => {
    expect(safeWebsite('javascript:alert(1)')).toBeNull()
    expect(safeWebsite('https://user:password@example.org')).toBeNull()
    const answer = item('answer', 'message'); answer.content = '[Publisher](https://example.org/paper) [Bad](javascript:alert(1)) ![Image](https://other.org/a.png)'
    const search = item('search', 'search'); search.sources = [{ title: 'Result', url: 'https://example.org/paper' }]
    const user = { ...answer, id: 'user', role: 'user' as const, content: '[User input](https://ignored.org)' }
    expect(chatResources([search, answer, user]).sources).toEqual([{ title: 'Publisher', url: 'https://example.org/paper' }])
  })
  it('projects native public commentary, search results, and exact turn timing', () => {
    expect(normalizeItem({ type: 'agentMessage', id: 'a', text: 'Checking', phase: 'commentary' }, 0)?.meta?.phase).toBe('commentary')
    expect(normalizeItem({ type: 'webSearch', id: 's', query: 'research', results: [{ title: 'Paper', url: 'https://example.org' }, { url: 'file:///secret' }] }, 0)?.sources).toEqual([{ title: 'Paper', url: 'https://example.org/' }])
    expect(notificationUpdate({ method: 'turn/completed', params: { turn: { id: 't', status: 'completed', durationMs: 27000, completedAt: 1791300000 } } })?.turnInfo).toEqual({ turnId: 't', meta: { turnStatus: 'completed', turnDurationMs: 27000, completedAtMs: 1791300000000 } })
  })
})


it('branches once through an exact turn and rejects missing native identity without synthesizing one', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ thread: { id: 'branch', turns: [] } }), { status: 201 }))
  vi.stubGlobal('fetch', fetch)
  try {
    expect((await forkConversation('source', 'early')).id).toBe('branch')
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch.mock.calls[0][0]).toBe('/api/threads/source/fork')
    expect(fetch.mock.calls[0][1].body).toBe(JSON.stringify({ turn_id: 'early' }))
    fetch.mockResolvedValue(new Response(JSON.stringify({ thread: {} }), { status: 201 }))
    await expect(forkConversation('source', 'early')).rejects.toThrow('Branch was not confirmed')
    expect(fetch).toHaveBeenCalledTimes(2)
  } finally { vi.unstubAllGlobals() }
})

it('offers a native turn branch only at its last visible reply, including legacy unknown phases', () => {
  const earlier = { ...item('early', 'message'), role: 'assistant' as const }
  const final = { ...item('final', 'message', { phase: 'final_answer' }), role: 'assistant' as const }
  expect(isResponseBranchPoint([earlier, final], earlier)).toBe(false)
  expect(isResponseBranchPoint([earlier, final], final)).toBe(true)
  expect(isResponseBranchPoint([{ ...earlier, meta: {} }], earlier)).toBe(false)
})

it('preserves work order across approval boundaries and ignores empty trailing replies', () => {
  const entries = groupTurnFeed([item('before', 'command'), item('approval', 'approval'), item('after', 'command')])
  expect(entries.map(entry => entry.type === 'work' ? entry.events.map(event => event.id) : entry.event.id)).toEqual([['before'], 'approval', ['after']])
  const answer = { ...item('answer', 'message'), role: 'assistant' as const }
  expect(isResponseBranchPoint([answer, { ...answer, id: 'empty', content: '' }], answer)).toBe(true)
})
it('does not collect links from code examples or unterminated fences', () => {
  const answer = item('answer', 'message')
  answer.content = '[Real](https://real.org)\n\n`[Inline](https://inline.org)`\n\n```md\n[Example](https://example.org)\n```\n\n    [Indented](https://indented.org)\n\n~~~\n[Unclosed](https://unclosed.org)'
  expect(chatResources([answer]).sources.map(source => source.url)).toEqual(['https://real.org/'])
})
