import { AlertCircle, LoaderCircle } from 'lucide-react'
import type { Conversation } from './types'
export function ChatActivityMark({ chat }: { chat: Pick<Conversation, 'status' | 'unread'> }) {
  if (chat.status === 'running') return <LoaderCircle size={14} className="spin chat-activity-spinner" role="img" aria-label="Running" />
  if (chat.status === 'failed') return <AlertCircle size={14} className="chat-activity-error" role="img" aria-label="Failed" />
  return chat.unread ? <span className="chat-unread-dot" role="img" aria-label="Finished · unread" /> : null
}
