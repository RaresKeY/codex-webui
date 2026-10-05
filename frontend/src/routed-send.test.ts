import { afterEach, describe, expect, it, vi } from 'vitest'
import { notificationUpdate, sendPrompt } from './api'

const decision = { model: 'gpt-6.1-sol', effort: 'low', modelConfidence: .8, effortConfidence: .7, contextMissing: null, reviewNeeded: false, policy: '2026-10-05-v5' }
const result = { turn: { id: 't1' }, decision, modelChangeAcknowledged: true }
const encode = (frame: unknown) => new TextEncoder().encode(JSON.stringify(frame) + '\n')
const stream = (frames: unknown[]) => new Response(new ReadableStream({ start(controller) {
  frames.forEach(frame => controller.enqueue(encode(frame)))
  controller.close()
} }), { status: 201, headers: { 'Content-Type': 'application/x-ndjson' } })
afterEach(() => vi.unstubAllGlobals())

describe('server-owned Jev → acknowledged model binding → original ask', () => {
  it('sends one request with the exact padded input and consumes server progress', async () => {
    let channel!: ReadableStreamDefaultController<Uint8Array>
    const body = new ReadableStream<Uint8Array>({ start(controller) { channel = controller } })
    const fetch = vi.fn().mockResolvedValue(new Response(body, { status: 201, headers: { 'Content-Type': 'application/x-ndjson' } }))
    vi.stubGlobal('fetch', fetch)
    const progress = vi.fn()
    const ask = ' \tMy exact ask\nUnicode: café 🙂\n\n '
    const pending = sendPrompt('thread/one', ask, progress)
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch.mock.calls[0][0]).toBe('/api/threads/thread%2Fone/messages')
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ input: ask })
    expect(fetch.mock.calls[0][1].headers.Accept).toBe('application/x-ndjson')
    channel.enqueue(encode({ stage: 'routing' }))
    channel.enqueue(encode({ stage: 'switching', decision }))
    await vi.waitFor(() => expect(progress).toHaveBeenLastCalledWith('switching', decision))
    expect(fetch).toHaveBeenCalledTimes(1)
    channel.enqueue(encode({ stage: 'sending', decision }))
    const final = encode({ result })
    channel.enqueue(final.slice(0, 9)); channel.enqueue(final.slice(9))
    channel.close()
    expect(await pending).toEqual({ turnId: 't1', decision })
    expect(progress.mock.calls.map(call => call[0])).toEqual(['routing', 'switching', 'sending'])
  })

  it('does not retry a rejected request', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Jev failed' }), { status: 409 }))
    vi.stubGlobal('fetch', fetch)
    await expect(sendPrompt('one', 'ask')).rejects.toThrow('Jev failed')
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('propagates a streamed model-change rejection without retry or false success', async () => {
    const fetch = vi.fn().mockResolvedValue(stream([{ stage: 'routing' }, { stage: 'switching', decision }, { error: { status: 502, message: 'Codex could not apply the selected model.' } }]))
    vi.stubGlobal('fetch', fetch)
    await expect(sendPrompt('one', 'ask')).rejects.toMatchObject({ status: 502, message: 'Codex could not apply the selected model.' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('rejects malformed decisions and missing acknowledgements', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(stream([{ stage: 'switching', decision: { ...decision, model: 'unknown' } }]))
      .mockResolvedValueOnce(stream([{ result: { ...result, modelChangeAcknowledged: false } }]))
    vi.stubGlobal('fetch', fetch)
    await expect(sendPrompt('one', 'ask')).rejects.toThrow('unsupported')
    await expect(sendPrompt('one', 'ask')).rejects.toThrow('could not confirm')
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('does not infer success when the stream ends before an acknowledged turn', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(stream([{ stage: 'routing' }, { stage: 'switching', decision }])))
    await expect(sendPrompt('one', 'ask')).rejects.toThrow('could not confirm')
  })

  it('cancels the single request and stream on conversation navigation', async () => {
    const controller = new AbortController()
    const fetch = vi.fn().mockResolvedValue(stream([{ stage: 'routing' }, { stage: 'switching', decision }, { result }]))
    vi.stubGlobal('fetch', fetch)
    await expect(sendPrompt('one', 'ask', stage => { if (stage === 'switching') controller.abort() }, controller.signal)).rejects.toThrow()
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch.mock.calls[0][1].signal).toBe(controller.signal)
  })

  it('recognizes model provenance on the thread event channel before turn output', () => {
    expect(notificationUpdate({ method: 'webui/modelSelected', params: { threadId: 'one', model: 'gpt-6-luna' } })).toEqual({ selectedModel: 'gpt-6-luna' })
  })
})
