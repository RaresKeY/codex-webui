import type { Conversation } from './types'
import { describe, expect, it } from 'vitest'
import { recoverChatActivity, reconcileChat, reduceChatActivity } from './chat-activity'
describe('background chat activity', () => {
 it('shows running, then unread only for an unseen completed turn', () => {
  const running = reduceChatActivity(undefined, { kind: 'started', turnId: 'a' }, false)
  expect(running).toMatchObject({ status: 'running', unread: false })
  expect(reduceChatActivity(running, { kind: 'completed', turnId: 'a', status: 'completed' }, false)).toMatchObject({ status: 'ready', unread: true })
  expect(reduceChatActivity(running, { kind: 'completed', turnId: 'a', status: 'completed' }, true).unread).toBe(false)
 })
 it('rejects an old completion after a newer turn starts', () => {
  const running = reduceChatActivity(undefined, { kind: 'started', turnId: 'b' }, false)
  expect(reduceChatActivity(running, { kind: 'completed', turnId: 'a', status: 'completed' }, false)).toEqual(running)
 })
 it('keeps retried errors active and distinguishes failed/interrupted completion', () => {
  const running = reduceChatActivity(undefined, { kind: 'started', turnId: 'a' }, false)
  expect(reduceChatActivity(running, { kind: 'error', turnId: 'a', message: '', willRetry: true }, false)).toEqual(running)
  expect(reduceChatActivity(running, { kind: 'completed', turnId: 'a', status: 'failed' }, false)).toMatchObject({ status: 'failed', unread: false })
  expect(reduceChatActivity(running, { kind: 'completed', turnId: 'a', status: 'interrupted' }, false)).toMatchObject({ status: 'paused', unread: false })
 })
})

describe('activity recovery', () => {
 const chat = { id: 'a', projectId: 'p', title: 'Old', preview: '', updatedAt: 'Now', status: 'running', cwd: '.', model: 'gpt-6.1-sol', contextPercent: 0, updatedAtEpoch: 200 } as Conversation
 it('does not restore an already-read dot on a repeated completion', () => {
  const done = reduceChatActivity(undefined, { kind: 'completed', turnId: 'a', status: 'completed' }, false)
  expect(reduceChatActivity({ ...done, unread: false }, { kind: 'completed', turnId: 'a', status: 'completed' }, false).unread).toBe(false)
 })
 it('preserves failure and interruption when native metadata says idle', () => {
  for (const status of ['failed', 'paused'] as const) expect(reconcileChat({ ...chat, status }, { ...chat, status: 'ready' }, false)).toMatchObject({ status, unread: false })
 })
 it('clears old unread state for new work and refreshes native metadata', () => {
  expect(reconcileChat({ ...chat, status: 'ready', unread: true }, { ...chat, title: 'New', updatedAtEpoch: 300 }, false)).toMatchObject({ status: 'running', unread: false, title: 'New', updatedAtEpoch: 300 })
 })
 it('marks recovered completion unread only when unseen and retains local recency', () => {
  expect(reconcileChat(chat, { ...chat, status: 'ready', updatedAtEpoch: 100 }, false)).toMatchObject({ unread: true, updatedAtEpoch: 200 })
  expect(reconcileChat(chat, { ...chat, status: 'ready' }, true).unread).toBe(false)
 })
})

it('accepts the new completion after reconnect misses its start', () => {
 const old = reduceChatActivity(undefined, { kind: 'completed', turnId: 'old', status: 'completed' }, true)
 const recovered = recoverChatActivity(old, 'running')
 expect(reduceChatActivity(recovered, { kind: 'completed', turnId: 'new', status: 'completed' }, false)).toMatchObject({ status: 'ready', unread: true, turnId: 'new' })
})

it('does not overwrite acknowledged chat settings with history defaults', () => {
 const local = { id: 'a', projectId: 'chosen', title: 'Old', preview: '', updatedAt: 'Now', status: 'ready', cwd: '/chosen', model: 'gpt-6-luna', contextPercent: 30, pinned: true } as Conversation
 expect(reconcileChat(local, { ...local, projectId: '', model: 'gpt-6.1-sol', contextPercent: 0, pinned: false, title: 'Native title' }, false)).toMatchObject({ projectId: 'chosen', model: 'gpt-6-luna', contextPercent: 30, pinned: true, title: 'Native title' })
})

it('accepts a new completion when its start was missed, but rejects older terminal events', () => {
 const old = reduceChatActivity(undefined, { kind: 'completed', turnId: 'old', status: 'completed' }, true)
 const next = reduceChatActivity(old, { kind: 'completed', turnId: 'new', status: 'completed' }, false)
 expect(next).toMatchObject({ turnId: 'new', unread: true })
 const read = { ...next, unread: false }
 expect(reduceChatActivity(read, { kind: 'completed', turnId: 'old', status: 'completed' }, false)).toEqual(read)
 expect(reduceChatActivity(read, { kind: 'started', turnId: 'new' }, false)).toEqual(read)
})
