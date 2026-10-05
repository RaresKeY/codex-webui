import { describe, expect, it } from 'vitest'
import { mentionQuery, mentionSuggestions, retainedMentions } from './mentions'
import { stampAssistantMessageModel } from './turn-lifecycle'
import type { Mention, StreamEvent } from './types'

const skill: Mention = { id: 'skill:one', kind: 'skill', name: 'docs:review', displayName: 'Review', description: '', insertText: '$docs:review' }

describe('combined mention menu', () => {
  it('searches @ and native $ names, namespaces and file paths without matching emails', () => {
    expect(mentionQuery('Use @docs:rev', 13)).toEqual({ query: 'docs:rev', start: 4, end: 13 })
    expect(mentionQuery('$docs:rev', 9)?.query).toBe('docs:rev')
    expect(mentionQuery('@src/main.py', 12)?.query).toBe('src/main.py')
    expect(mentionQuery('person@example.com', 18)).toBeNull()
  })
  it('keeps only explicit selections whose exact invocation remains present', () => {
    expect(retainedMentions('  $docs:review do this\n ', [skill])).toEqual([skill])
    for (const value of ['deleted', 'é$docs:review', '$docs:review-more', '$docs:reviewé', '$docs:review/sub']) expect(retainedMentions(value, [skill])).toEqual([])
    const file = { ...skill, kind: 'file' as const, insertText: '@"src/my file.py"' }
    expect(retainedMentions('Read @"src/my file.py".', [file])).toEqual([file])
    expect(retainedMentions('Read @"src/my file.py" please.', [file])).toEqual([file])
  })
  it('gives every available category room and retains native fuzzy file matches', () => {
    const entries = Array.from({ length: 20 }, (_, i) => ({ ...skill, id: `skill:${i}` }))
    const plugin = { ...skill, id: 'plugin:one', kind: 'plugin' as const }
    const app = { ...skill, id: 'app:one', kind: 'app' as const }
    const file = { ...skill, id: 'file:one', kind: 'file' as const, name: 'fuzzy match', displayName: 'fuzzy match' }
    const result = mentionSuggestions([...entries, plugin, app, file], 'docs')
    expect(result).toHaveLength(12)
    expect(result.slice(0, 4).map(entry => entry.kind)).toEqual(['skill', 'plugin', 'app', 'file'])
  })
})

describe('per-message effort provenance', () => {
  it('retains a message selection when the next turn changes model and effort', () => {
    const event: StreamEvent = { id: 'answer', kind: 'message', role: 'assistant', content: '4', timestamp: 'Now' }
    const stamped = stampAssistantMessageModel([event], 'gpt-6-luna', 'low')
    expect(stampAssistantMessageModel(stamped, 'gpt-6.1-sol', 'high')[0].meta).toEqual({ model: 'gpt-6-luna', effort: 'low' })
    const historical = { ...event, meta: { model: 'gpt-6-luna' } }
    expect(stampAssistantMessageModel([historical], 'gpt-6.1-sol', 'high')[0].meta?.effort).toBeUndefined()
  })
})
