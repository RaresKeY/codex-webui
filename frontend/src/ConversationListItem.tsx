import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { Archive, ArchiveRestore, MoreHorizontal, Pin, PinOff, Trash2 } from 'lucide-react'
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
  const details = useRef<HTMLDetailsElement>(null)
  const trigger = useRef<HTMLElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (!open || !menu.current || !trigger.current) return
    const surface = menu.current
    const close = (focus = false) => { if (details.current) details.current.open = false; if (focus) trigger.current?.focus() }
    // The native top layer avoids clipping in the scrollable history sidebar.
    surface.showPopover?.()
    const position = () => {
      const anchor = trigger.current?.getBoundingClientRect()
      if (!anchor) return
      const bounds = surface.getBoundingClientRect()
      surface.style.left = `${Math.max(8, Math.min(innerWidth - bounds.width - 8, anchor.left))}px`
      surface.style.top = `${Math.max(8, Math.min(innerHeight - bounds.height - 8, anchor.bottom + 4))}px`
    }
    position()
    const outside = (event: PointerEvent) => { if (!details.current?.contains(event.target as Node)) close() }
    const keyboard = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(true) } }
    const otherMenu = (event: Event) => { if ((event as CustomEvent).detail !== details.current) close() }
    document.dispatchEvent(new CustomEvent('chat-menu-open', { detail: details.current }))
    document.addEventListener('chat-menu-open', otherMenu)
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', keyboard, true)
    window.addEventListener('resize', position)
    window.addEventListener('scroll', position, true)
    return () => {
      surface.hidePopover?.()
      document.removeEventListener('chat-menu-open', otherMenu)
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('keydown', keyboard, true)
      window.removeEventListener('resize', position)
      window.removeEventListener('scroll', position, true)
    }
  }, [open])
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
    <details ref={details} className="conversation-details" onToggle={event => setOpen(event.currentTarget.open)}>
      <summary ref={trigger} aria-expanded={open} aria-label={`Details for ${conversation.title}`} title="Chat actions"><MoreHorizontal size={16} /></summary>
      <div ref={menu} className="conversation-details-body" popover="manual" role="group" aria-label="Chat actions">
        {onPin && <button type="button" className="chat-pin-action conversation-menu-action" disabled={saving} onClick={() => void action(onPin, 'update pin for')}>{conversation.pinned ? <PinOff size={15} /> : <Pin size={15} />}<span>{conversation.pinned ? 'Unpin chat' : 'Pin chat'}</span></button>}
        {(onArchive || onRestore || onDelete) && onPin && <hr />}
        {onArchive && <button type="button" className="chat-menu-action conversation-menu-action" disabled={saving || conversation.status === 'running'} title={conversation.status === 'running' ? 'Wait for the current turn to finish' : undefined} onClick={() => void action(onArchive, 'archive')}><Archive size={15} /><span>Archive chat</span></button>}
        {onRestore && <button type="button" className="chat-menu-action conversation-menu-action" disabled={saving} onClick={() => void action(onRestore, 'restore')}><ArchiveRestore size={15} /><span>Restore chat</span></button>}
        {onDelete && <button type="button" className="chat-menu-action conversation-menu-action danger" disabled={saving || conversation.status === 'running'} onClick={event => { event.currentTarget.closest('details')?.removeAttribute('open'); onDelete() }}><Trash2 size={15} /><span>Delete chat</span></button>}
        {saving && <p role="status">Saving…</p>}
        {error && <p role="alert">{error}</p>}
      </div>
    </details>
    <span className="conversation-description" id={detailsId}>{description}</span>
  </div>
}
