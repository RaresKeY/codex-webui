import { describe, expect, it } from 'vitest'
import { groupEventFeed } from './event-groups'
import type { StreamEvent } from './types'

const event = (id: string, kind: StreamEvent['kind']): StreamEvent => ({
  id, kind, content: id, timestamp: 'Now', state: 'done',
})

describe('event feed grouping', () => {
  it('groups consecutive commands under one stable entry', () => {
    expect(groupEventFeed([
      event('message-1', 'message'),
      event('command-1', 'command'),
      event('command-2', 'command'),
      event('file-1', 'file'),
    ])).toEqual([
      { type: 'event', event: event('message-1', 'message') },
      { type: 'commands', id: 'commands-command-1', commands: [event('command-1', 'command'), event('command-2', 'command')] },
      { type: 'event', event: event('file-1', 'file') },
    ])
  })

  it('keeps commands separated by another event in separate groups', () => {
    const grouped = groupEventFeed([
      event('command-1', 'command'),
      event('approval-1', 'approval'),
      event('command-2', 'command'),
    ])
    expect(grouped.map(entry => entry.type)).toEqual(['commands', 'event', 'commands'])
  })
})
