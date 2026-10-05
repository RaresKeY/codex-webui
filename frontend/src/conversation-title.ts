export const UNTITLED_CONVERSATION = 'Untitled conversation'

export function isUntitledConversation(title: string): boolean {
  return !title.trim() || title.trim() === UNTITLED_CONVERSATION
}

export function deriveConversationTitle(prompt: string, maxLength = 60): string {
  const firstMeaningfulLine = prompt.split(/\r?\n/).map(line => line.trim()).find(Boolean) ?? ''
  const cleaned = firstMeaningfulLine
    .replace(/^#{1,6}\s+/, '')
    .replace(/^[-*+]\s+/, '')
    .replace(/\[([^\]]+)]\([^)]*\)/g, '$1')
    .replace(/[`*_~]+/g, '')
    .replace(/\s+/g, ' ')
    .replace(/^(?:please\s+|can you\s+|could you\s+|would you\s+)+/i, '')
    .trim()
  const sentence = cleaned.match(/^.*?[.!?](?:\s|$)/)?.[0] ?? cleaned
  const title = sentence.trim().replace(/[.!?]+$/, '').trim()
  if (!title) return UNTITLED_CONVERSATION
  const normalizedTitle = `${title.charAt(0).toLocaleUpperCase()}${title.slice(1)}`
  if (normalizedTitle.length <= maxLength) return normalizedTitle

  const available = Math.max(1, maxLength - 1)
  const candidate = normalizedTitle.slice(0, available + 1)
  const wordBoundary = candidate.lastIndexOf(' ')
  const cutAt = wordBoundary >= Math.floor(available * 0.6) ? wordBoundary : available
  return `${normalizedTitle.slice(0, cutAt).trimEnd()}…`
}
