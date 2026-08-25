import { describe, expect, it } from 'vitest'
import { deriveConversationTitle, isUntitledConversation, UNTITLED_CONVERSATION } from './conversation-title'

describe('conversation titles', () => {
  it('derives a concise provisional title without a model call', () => {
    expect(deriveConversationTitle('Can you fix the empty Reasoning Summary cards in the web UI?')).toBe('Fix the empty Reasoning Summary cards in the web UI')
    expect(deriveConversationTitle('\n## Render **Markdown** correctly\nMore details here.')).toBe('Render Markdown correctly')
  })

  it('uses the first sentence and truncates only on a useful boundary', () => {
    expect(deriveConversationTitle('Fix markdown rendering. Also repair code block copy actions.')).toBe('Fix markdown rendering')
    const title = deriveConversationTitle('Implement a deliberately very long conversation title that must fit cleanly in the compact sidebar', 48)
    expect(title.length).toBeLessThanOrEqual(48)
    expect(title.endsWith('…')).toBe(true)
  })

  it('recognizes only the generated fallback as safe to replace', () => {
    expect(isUntitledConversation('')).toBe(true)
    expect(isUntitledConversation(UNTITLED_CONVERSATION)).toBe(true)
    expect(isUntitledConversation('Manual project name')).toBe(false)
  })
})
