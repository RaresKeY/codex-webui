import { describe, expect, it } from 'vitest'
import { CONTEXT_TOOLS, DEFAULT_CONTEXT_TOOL, contextualConversations } from './context-tools'
import type { Conversation } from './types'

describe('context tool registry', () => {
  it('keeps a stable, scalable tool order around the primary conversation', () => {
    expect(CONTEXT_TOOLS.map(tool => tool.id)).toEqual([
      'outputs',
      'browser',
      'terminal',
      'side-chats',
      'explorer',
      'changes',
    ])
  })

  it('defaults to Explorer and leaves only the desktop-private Browser surface planned', () => {
    expect(DEFAULT_CONTEXT_TOOL).toBe('explorer')
    expect(CONTEXT_TOOLS.filter(tool => tool.availability === 'available').map(tool => tool.id)).toEqual([
      'outputs',
      'terminal',
      'side-chats',
      'explorer',
      'changes',
    ])
    expect(CONTEXT_TOOLS.filter(tool => tool.availability === 'planned').map(tool => tool.id)).toEqual([
      'browser',
    ])
  })

  it('ranks related side chats without duplicating the open conversation', () => {
    const chat = (id: string, projectId: string, cwd: string): Conversation => ({
      id, projectId, cwd, title: id, preview: '', updatedAt: 'Now', status: 'ready', model: 'gpt-5.6-sol', contextPercent: 0,
    })
    const current = chat('current', 'project-a', '/workspace/a')
    expect(contextualConversations([
      chat('unrelated', 'project-b', '/workspace/b'),
      current,
      chat('same-project', 'project-a', '/workspace/c'),
      chat('same-folder', 'project-b', '/workspace/a'),
    ], current).map(item => item.id)).toEqual(['same-project', 'same-folder', 'unrelated'])
  })
})
