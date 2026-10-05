import { imageSource } from './images'
import type { Conversation, ImageAsset, StreamEvent } from './types'

export interface ChatImageAsset extends ImageAsset { conversationId: string; conversationTitle: string }

export function chatImageAssets(events: StreamEvent[], conversation: Conversation): ChatImageAsset[] {
  const seen = new Set<string>()
  return events.flatMap(event => {
    const markdownSource = event.content.replace(/^([ \t]*)(`{3,}|~{3,})[^\n]*\n[\s\S]*?^\1\2[^\n]*(?:\n|$)/gm, '').replace(/`+[^`]*`+/g, '')
    const markdown = [...markdownSource.matchAll(/!\[([^\]]*)\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\s*\)/g)].map(match => ({ url: match[2].replace(/^<|>$/g, ''), alt: match[1] || 'Chat image' }))
    return [...(event.images ?? []), ...markdown].flatMap(image => {
      let source = image.url
      if (source.startsWith('/api/workspace/image?path=')) {
        try { source = new URL(source, 'http://local').searchParams.get('path') ?? '' } catch { return [] }
      }
      const url = imageSource(source, conversation.cwd)
      if (!url || seen.has(url)) return []
      seen.add(url)
      return [{ id: `chat:${conversation.id}:${event.id}:${seen.size}`, name: image.alt, url, mime: 'image/*', size: 0, modifiedAt: conversation.updatedAt, conversationId: conversation.id, conversationTitle: conversation.title }]
    })
  })
}
