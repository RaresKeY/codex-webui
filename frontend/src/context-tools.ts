import type { Conversation } from './types'

export const CONTEXT_TOOLS = [
  { id: 'jev', label: 'Jev', availability: 'available', backing: 'Thread-scoped routing records and events', description: 'This chat’s turn preparation, model choices and Jev diagnostics.' },
  { id: 'outputs', label: 'Outputs', availability: 'available', backing: 'App Server notifications', description: 'Recent command, file, status, and approval activity from this conversation.' },
  { id: 'browser', label: 'Browser', availability: 'available', backing: 'Experimental Jev browser adapter', description: 'Live restricted Chromium page with visible agent actions. Linux browser companion required; new chats receive the browser tool.' },
  { id: 'terminal', label: 'Terminal', availability: 'available', backing: 'thread/backgroundTerminals/list', description: 'Read-only monitoring for background terminals owned by this Codex thread. Starting arbitrary shell commands is intentionally not exposed.' },
  { id: 'side-chats', label: 'Side chats', availability: 'available', backing: 'thread/list', description: 'Open recent related Codex threads beside the primary conversation without creating a second transcript model.' },
  { id: 'explorer', label: 'Explorer', availability: 'available', backing: 'Bounded workspace adapter', description: 'Browse, preview, and edit text files inside the configured local workspace boundary.' },
  { id: 'changes', label: 'Changes', availability: 'available', backing: 'Bounded read-only Git adapter', description: 'Review Git status for a conversation folder when it is inside the configured workspace.' },
] as const

export type ContextToolId = typeof CONTEXT_TOOLS[number]['id']

export const DEFAULT_CONTEXT_TOOL: ContextToolId = 'explorer'

export function contextualConversations(conversations: Conversation[], current: Conversation, limit = 12): Conversation[] {
  return conversations
    .filter(conversation => conversation.id !== current.id)
    .map((conversation, index) => ({
      conversation,
      index,
      score: (conversation.projectId && conversation.projectId === current.projectId ? 2 : 0)
        + (conversation.cwd && conversation.cwd === current.cwd ? 1 : 0),
    }))
    .sort((left, right) => right.score - left.score || left.index - right.index)
    .slice(0, Math.max(0, limit))
    .map(item => item.conversation)
}
