import { useId, useRef, useState, type ReactNode } from 'react'
import { MoreHorizontal } from 'lucide-react'
import type { Conversation, Project } from './types'
import './conversation-list-item.css'

export function ConversationListItem({ conversation, project, active, onSelect, statusIndicator, onPin, onArchive, onRestore, onDelete }: {
  conversation: Conversation
  project?: Project
  active: boolean
  onSelect: () => void
  statusIndicator?: ReactNode
  onPin?: () => Promise<void>
  onArchive?: () => Promise<void>
  onRestore?: () => Promise<void>
  onDelete?: () => void
}) {
  const detailsId = useId()
  const busy = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const directoryName = conversation.cwd.split(/[\\/]/).filter(Boolean).at(-1)
  const projectName = project?.name || (conversation.projectId ? directoryName || 'Project' : 'No project')
  const preview = conversation.preview || 'No preview available.'
  const description = `${conversation.title}\nProject: ${projectName}\nUpdated: ${conversation.updatedAt}\n${preview}\nModel: ${conversation.model}`

  const action = async (operation: () => Promise<void>, label: string) => {
    if (busy.current) return
    busy.current = true
    setSaving(true); setError('')
    try { await operation() } catch { setError(`Could not ${label} this chat. Refresh and try again.`) } finally { busy.current = false; setSaving(false) }
  }
  return <div className="conversation-list-item">
    <button type="button" className={`chat-row ${active ? 'active' : ''}`} onClick={onSelect} aria-current={active ? 'page' : undefined} title={onRestore ? `Restore and open chat\n${description}` : description} aria-describedby={detailsId}>
      <span className="chat-title">{statusIndicator}<span className="conversation-list-title">{conversation.title}</span></span>
      {conversation.status === 'running' && <span className="chat-running-label">Working</span>}
    </button>
    <details className="conversation-details">
      <summary aria-label={`Details for ${conversation.title}`} title="Conversation details"><MoreHorizontal size={16} /></summary>
      <div className="conversation-details-body" id={detailsId}>
        {onPin && <button className="chat-pin-action" disabled={saving} onClick={() => { setSaving(true); setError(''); void onPin().catch(() => setError('Could not update pin. Try again.')).finally(() => setSaving(false)) }}>{saving ? 'Saving…' : conversation.pinned ? 'Unpin chat' : 'Pin chat'}</button>}
        {onArchive && <button type="button" className="chat-menu-action" disabled={saving || conversation.status === 'running'} title={conversation.status === 'running' ? 'Wait for the current turn to finish' : undefined} onClick={() => void action(onArchive, 'archive')}>Archive chat</button>}
        {onRestore && <button type="button" className="chat-menu-action" disabled={saving} onClick={() => void action(onRestore, 'restore')}>Restore chat</button>}
        {onDelete && <button type="button" className="chat-menu-action danger" disabled={saving || conversation.status === 'running'} onClick={event => { event.currentTarget.closest('details')?.removeAttribute('open'); onDelete() }}>Delete chat</button>}
        {saving && <p role="status">Saving…</p>}
          {error && <p role="alert">{error}</p>}
          <strong>{projectName}</strong>
        <span className="conversation-details-updated">Updated <time>{conversation.updatedAt}</time></span>
        <p>{preview}</p>
        <span className="conversation-details-model">{conversation.model}</span>
      </div>
    </details>
  </div>
}
