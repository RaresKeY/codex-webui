import { afterEach, describe, expect, it, vi } from 'vitest'
import { loadChatPermissions, setChatPermissions, loadChatExecution, setChatExecution } from './api'

afterEach(() => vi.unstubAllGlobals())
describe('chat permission acknowledgement', () => {
  it('loads the saved chat choice with a cancellable read', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({mode:'full-auto'})))
    vi.stubGlobal('fetch', fetch)
    const controller = new AbortController()
    expect(await loadChatPermissions('one/two', controller.signal)).toBe('full-auto')
    expect(fetch.mock.calls[0][0]).toBe('/api/threads/one%2Ftwo/permissions')
  })
  it('sends one explicit mode change and requires matching native acknowledgement', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({mode:'yolo',acknowledged:true})))
    vi.stubGlobal('fetch', fetch)
    expect(await setChatPermissions('one', 'yolo')).toBe('yolo')
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({mode:'yolo'})
    expect(fetch.mock.calls[0][1].method).toBe('PATCH')
  })
  it('does not accept missing acknowledgement, changed mode, or unknown persisted choices', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({mode:'yolo'})))
      .mockResolvedValueOnce(new Response(JSON.stringify({mode:'default',acknowledged:true})))
      .mockResolvedValueOnce(new Response(JSON.stringify({mode:'unknown'})))
    vi.stubGlobal('fetch', fetch)
    await expect(setChatPermissions('one','yolo')).rejects.toThrow('did not confirm')
    await expect(setChatPermissions('one','yolo')).rejects.toThrow('did not confirm')
    await expect(loadChatPermissions('one')).rejects.toThrow('unknown permissions')
    expect(fetch).toHaveBeenCalledTimes(3)
  })
  it('surfaces a rejected change and never retries it', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Wait for the current turn to finish.'}), {status:409}))
    vi.stubGlobal('fetch', fetch)
    await expect(setChatPermissions('one','yolo')).rejects.toMatchObject({status:409})
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})


describe('per-chat execution acknowledgement', () => {
  it('loads a chat choice and saves one matching acknowledged selection', async () => {
    const choice = { model: 'gpt-6.1-sol', effort: 'high' } as const
    const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(choice)))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...choice, acknowledged: true })))
    vi.stubGlobal('fetch', fetch)
    expect(await loadChatExecution('one/two')).toEqual(choice)
    expect(fetch.mock.calls[0][0]).toBe('/api/threads/one%2Ftwo/execution')
    expect(await setChatExecution('one', choice)).toEqual(choice)
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual(choice)
    expect(fetch).toHaveBeenCalledTimes(2)
  })
  it('rejects mismatched acknowledgements and unknown persisted settings without retrying', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({model:'auto',effort:'low',acknowledged:true})))
      .mockResolvedValueOnce(new Response(JSON.stringify({model:'other',effort:'high'})))
    vi.stubGlobal('fetch', fetch)
    await expect(setChatExecution('one',{model:'gpt-6.1-sol',effort:'high'})).rejects.toThrow('could not be confirmed')
    await expect(loadChatExecution('one')).rejects.toThrow('could not be confirmed')
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
