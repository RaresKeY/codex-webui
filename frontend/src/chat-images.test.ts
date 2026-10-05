import { describe, expect, it } from 'vitest'
import { chatImageAssets } from './chat-images'
import type { Conversation, StreamEvent } from './types'
const chat: Conversation = { id: 'chat', title: 'Design', cwd: '/workspace/project', projectId: '', preview: '', updatedAt: 'Today', status: 'ready', model: '', contextPercent: 0 }
const event = (content: string, images: StreamEvent['images'] = []): StreamEvent => ({ id: 'item', kind: 'message', role: 'assistant', content, images, timestamp: 'Now', state: 'done' })
describe('chat image gallery', () => {
  it('includes attached/generated images and inline local Markdown with source chat', () => {
    const assets = chatImageAssets([event('![Preview](./preview.png)', [{ url: 'data:image/png;base64,YQ==', alt: 'Generated image' }])], chat)
    expect(assets).toHaveLength(2)
    expect(assets[0]).toMatchObject({ conversationId: 'chat', conversationTitle: 'Design' })
    expect(assets[1].url).toBe('/api/workspace/image?path=%2Fworkspace%2Fproject%2F.%2Fpreview.png')
  })
  it('deduplicates images within a chat and roots normalized relative paths', () => {
    expect(chatImageAssets([event('![same](image.png)', [{ url: '/api/workspace/image?path=image.png', alt: 'Attachment' }])], chat)).toHaveLength(1)
  })
  it('excludes remote images and code examples', () => {
    expect(chatImageAssets([event('![Remote](https://example.com/private.png)\n```md\n![Example](example.png)\n```\n`![Inline](example.png)`')], chat)).toEqual([])
  })
})
