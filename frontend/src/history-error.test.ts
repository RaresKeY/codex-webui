import { afterEach, expect, it, vi } from 'vitest'
import { ApiError, loadConversationSnapshot, turnStartFailureMessage } from './api'

afterEach(() => vi.unstubAllGlobals())

it('shows the bounded history-mode recovery message and retains an idle lifecycle', async () => {
  const detail = 'This conversation uses an unsupported history mode. Start a new chat.'
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail }), { status: 409 })))
  const snapshot = await loadConversationSnapshot('old-paginated-thread')
  expect(snapshot.events).toHaveLength(1)
  expect(snapshot.events[0].content).toBe(detail)
  expect(snapshot.turn.phase).toBe('idle')
  expect(turnStartFailureMessage(new ApiError(409, detail))).toContain('Start a new chat')
})
