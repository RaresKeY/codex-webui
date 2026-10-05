import { useId, type ReactNode } from 'react'
import { MoreHorizontal } from 'lucide-react'
import type { Conversation, Project } from './types'
import './conversation-list-item.css'

export function ConversationListItem({ conversation, project, active, onSelect, statusIndicator }: {
  conversation: Conversation
  project?: Project
  active: boolean
  onSelect: () => void
  statusIndicator?: ReactNode
}) {
  const detailsId = useId()
  const directoryName = conversation.cwd.split(/[\\/]/).filter(Boolean).at(-1)
  const projectName = project?.name || (directoryName && directoryName !== '.' ? directoryName : 'Workspace')
  const preview = conversation.preview || 'No preview available.'
  const description = `${conversation.title}\nProject: ${projectName}\nUpdated: ${conversation.updatedAt}\n${preview}\nModel: ${conversation.model}`

  return <div className="conversation-list-item">
    <button type="button" className={`chat-row ${active ? 'active' : ''}`} onClick={onSelect} title={description} aria-describedby={detailsId}>
      <span className="chat-title">{statusIndicator}<span className="conversation-list-title">{conversation.title}</span></span>
      {conversation.status === 'running' && <span className="chat-running-label">Working</span>}
    </button>
    <details className="conversation-details">
      <summary aria-label={`Details for ${conversation.title}`} title="Conversation details"><MoreHorizontal size={16} /></summary>
      <div className="conversation-details-body" id={detailsId}>
        <strong>{projectName}</strong>
        <span className="conversation-details-updated">Updated <time>{conversation.updatedAt}</time></span>
        <p>{preview}</p>
        <span className="conversation-details-model">{conversation.model}</span>
      </div>
    </details>
  </div>
}
