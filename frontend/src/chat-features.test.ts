import { afterEach, describe, expect, it, vi } from 'vitest'
import { loadBootstrap, loadConversations, loadOptionalMetadata, normalizeItem, notificationUpdate } from './api'
import { contextUsage, contextUsageLabel } from './context-usage'
import { contentImages, imageSource } from './images'
import { mentionedPluginIds, pluginQuery } from './plugin-mentions'
import type { Conversation } from './types'

const png = 'data:image/png;base64,aGVsbG8='
const plugins = [{ id: 'my.notes@local', name: 'my.notes', displayName: 'Notes', description: '' }]

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

describe('composer plugin mentions', () => {
  it('recognizes an @ query at the caret without matching email addresses', () => {
    expect(pluginQuery('Use @my.n now', 9)).toEqual({ query: 'my.n', start: 4, end: 9 })
    expect(pluginQuery('@my.notes tail', 3)).toEqual({ query: 'my', start: 0, end: 9 })
    expect(pluginQuery('person@example.com', 18)).toBeNull()
    expect(pluginQuery('(@', 2)).toEqual({ query: '', start: 1, end: 2 })
  })
  it('only submits explicitly selected plugins still mentioned in the exact draft', () => {
    expect(mentionedPluginIds('  @my.notes find this\n ', plugins, ['my.notes@local'])).toEqual(['my.notes@local'])
    for (const value of ['deleted', 'person@my.notes', '@myXnotes', '@my.notes-extra', 'é@my.notes', '@my.notesé', '@my.notes_']) {
      expect(mentionedPluginIds(value, plugins, ['my.notes@local'])).toEqual([])
    }
    expect(mentionedPluginIds('@my.notes', plugins, [])).toEqual([])
  })
})

describe('image display adapters', () => {
  it('supports native user, image generation, image view and tool image formats', () => {
    expect(normalizeItem({ type: 'userMessage', content: [{ type: 'text', text: 'Look' }, { type: 'localImage', path: '/workspace/a.png' }] }, 0)).toMatchObject({ content: 'Look', images: [{ url: '/api/workspace/image?path=%2Fworkspace%2Fa.png' }] })
    expect(normalizeItem({ type: 'imageGeneration', result: 'aGVsbG8=', status: 'completed' }, 0)).toMatchObject({ kind: 'image', images: [{ url: png }] })
    expect(normalizeItem({ type: 'imageGeneration', result: png }, 0)?.images?.[0].url).toBe(png)
    expect(normalizeItem({ type: 'imageView', path: 'a.png' }, 0)?.images?.[0].url).toContain('path=a.png')
    expect(normalizeItem({ type: 'mcpToolCall', result: { content: [{ type: 'image', data: 'aGVsbG8=', mimeType: 'image/png' }] } }, 0)?.images?.[0].url).toBe(png)
    expect(normalizeItem({ type: 'dynamicToolCall', contentItems: [{ type: 'inputImage', imageUrl: png }] }, 0)?.images?.[0].url).toBe(png)
    expect(contentImages([{ type: 'input_image', image_url: png }])[0].url).toBe(png)
    expect(normalizeItem({ type: 'imageGeneration', failure: { type: 'usageLimitExceeded' } }, 0)?.content).toContain('failed')
  })
  it('blocks remote requests and unsafe image schemes while rooting local paths', () => {
    for (const value of ['javascript:alert(1)', 'https://example.com/p.png', '//example.com/p.png', 'data:image/svg+xml;base64,abcd', 'file://remote/a.png']) {
      expect(imageSource(value)).toBeUndefined()
    }
    expect(imageSource('file:///workspace/a%20b.png')).toBe('/api/workspace/image?path=%2Fworkspace%2Fa%20b.png')
    expect(imageSource('../escape.png')).toBe('/api/workspace/image?path=..%2Fescape.png')
    expect(imageSource(png)).toBe(png)
    expect(imageSource('x'.repeat(28_000_001))).toBeUndefined()
  })
  it('never displays private reasoning deltas', () => {
    expect(notificationUpdate({ method: 'item/reasoning/textDelta', params: { itemId: 'private', delta: 'secret' } })).toBeNull()
  })
})

describe('context occupancy', () => {
  it('uses the latest context total rather than accumulated lifetime tokens', () => {
    const stats = contextUsage({ total: { totalTokens: 900000 }, last: { totalTokens: 12500 }, modelContextWindow: 100000 })
    expect(stats).toEqual({ contextUsedTokens: 12500, contextWindowTokens: 100000, contextPercent: 13 })
    expect(contextUsageLabel({ ...stats } as Conversation)).toContain('12,500 / 100,000 tokens · 87,500 remaining')
    expect(contextUsage({ last: { totalTokens: 0 }, modelContextWindow: 100 })).toMatchObject({ contextPercent: 0 })
  })
  it('keeps unknown or invalid totals explicit', () => {
    expect(contextUsage({ total: { totalTokens: 10 }, modelContextWindow: 100 })).toEqual({})
    expect(contextUsage({ last: { totalTokens: -1 }, modelContextWindow: 100 })).toEqual({})
    const stats = contextUsage({ last: { totalTokens: 5 }, modelContextWindow: null })
    expect(stats).toEqual({ contextUsedTokens: 5 })
    expect(contextUsageLabel(stats as Conversation)).toContain('Total context unavailable')
    expect(contextUsageLabel({} as Conversation)).toContain('not been reported')
  })
})

describe('bounded startup reads', () => {
  it('shows bootstrap failures instead of silently substituting demo data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'offline' }), { status: 503 })))
    await expect(loadBootstrap()).rejects.toMatchObject({ status: 503 })
  })
  it('rejects malformed bootstrap and degraded history instead of showing a false empty workspace', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}')))
    await expect(loadBootstrap()).rejects.toMatchObject({ status: 502 })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ degraded: true, data: [], error: 'private diagnostic' }))))
    await expect(loadConversations()).rejects.toMatchObject({ status: 503 })
  })
  it('times out even when the JSON body never arrives, without retrying', async () => {
    vi.useFakeTimers()
    const fetch = vi.fn((_url, init: RequestInit) => Promise.resolve({ ok: true, status: 200, json: () => new Promise((_, reject) => init.signal?.addEventListener('abort', () => reject(new Error('aborted')), { once: true })) }))
    vi.stubGlobal('fetch', fetch)
    const result = expect(loadBootstrap()).rejects.toMatchObject({ status: 504 })
    await vi.advanceTimersByTimeAsync(8001)
    await result
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('retains optional metadata that succeeds and preserves the default model pool if empty', async () => {
    vi.stubGlobal('fetch', vi.fn((url: string) => Promise.resolve(url.endsWith('/models') ? new Response('{}', { status: 503 }) : new Response(JSON.stringify({ usage: { summary: { lifetimeTokens: 42 } } })))))
    expect(await loadOptionalMetadata()).toMatchObject({ usage: { lifetimeTokens: 42 } })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: [] }))))
    expect((await loadOptionalMetadata()).models).toBeUndefined()
  })
  it('honors caller cancellation', async () => {
    const controller = new AbortController()
    vi.stubGlobal('fetch', vi.fn((_url, init: RequestInit) => new Promise((_, reject) => init.signal?.addEventListener('abort', () => reject(new Error('cancelled')), { once: true }))))
    const result = expect(loadBootstrap(controller.signal)).rejects.toThrow('cancelled')
    controller.abort()
    await result
  })
})
