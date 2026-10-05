import { afterEach, describe, expect, it, vi } from 'vitest'
import { sendPrompt } from './api'

const decision = { model: 'gpt-6.1-sol', effort: 'low', modelConfidence: .8, effortConfidence: .7, contextMissing: null, reviewNeeded: false, policy: '2026-10-05-v5' }
const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
afterEach(() => vi.unstubAllGlobals())

describe('Jev → model change → original ask', () => {
  it('awaits each stage and sends the exact ask with the chosen model and effort', async () => {
    let finishRoute!: (value: Response) => void
    let finishResume!: (value: Response) => void
    const fetch = vi.fn().mockImplementationOnce(() => new Promise<Response>(resolve => { finishRoute = resolve }))
      .mockImplementationOnce(() => new Promise<Response>(resolve => { finishResume = resolve })).mockResolvedValueOnce(ok({ turn: { id: 't1' } }))
    vi.stubGlobal('fetch', fetch)
    const progress = vi.fn()
    const pending = sendPrompt('thread/one', 'My exact ask\nwith context', progress)
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch.mock.calls[0][0]).toBe('/api/threads/thread%2Fone/route')
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ input: 'My exact ask\nwith context' })
    finishRoute(ok(decision))
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
    expect(fetch.mock.calls[1][0]).toBe('/api/threads/thread%2Fone/resume')
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ model: decision.model })
    finishResume(ok({}))
    expect(await pending).toEqual({ turnId: 't1', decision })
    expect(fetch.mock.calls[2][0]).toBe('/api/threads/thread%2Fone/turns')
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual({ input: 'My exact ask\nwith context', model: decision.model, effort: decision.effort })
    expect(progress.mock.calls.map(call => call[0])).toEqual(['routing', 'switching', 'sending'])
  })

  it('does not change models or execute if routing fails and does not retry', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Jev failed' }), { status: 409 }))
    vi.stubGlobal('fetch', fetch)
    await expect(sendPrompt('one', 'ask')).rejects.toThrow('Jev failed')
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('does not send an ask after a rejected model change', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(ok(decision)).mockResolvedValueOnce(new Response('{}', { status: 409 }))
    vi.stubGlobal('fetch', fetch)
    await expect(sendPrompt('one', 'ask')).rejects.toThrow()
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('rejects an unsupported route before applying it', async () => {
    const fetch = vi.fn().mockResolvedValue(ok({ ...decision, model: 'unknown' }))
    vi.stubGlobal('fetch', fetch)
    await expect(sendPrompt('one', 'ask')).rejects.toThrow('unsupported')
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('stops a conflicting Luna high-effort route before model change', async () => {
    const fetch = vi.fn().mockResolvedValue(ok({ ...decision, model: 'gpt-6-luna', effort: 'high', reviewNeeded: true }))
    vi.stubGlobal('fetch', fetch)
    await expect(sendPrompt('one', 'ask')).rejects.toThrow('Review the routing policy')
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('cancels a pending route on conversation navigation before changing model', async () => {
    const controller = new AbortController()
    const fetch = vi.fn().mockImplementation(async () => { controller.abort(); return ok(decision) })
    vi.stubGlobal('fetch', fetch)
    await expect(sendPrompt('one', 'ask', undefined, controller.signal)).rejects.toThrow()
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
