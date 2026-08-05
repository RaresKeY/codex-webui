import { useEffect, useMemo, useRef, useState, type ComponentType, type FormEvent } from 'react'
import {
  Activity, AlertCircle, ArrowUp, Bot, Box, CalendarClock, Check, ChevronDown,
  ChevronRight, Circle, Clock3, Code2, Copy, Cpu, Database, Download, Edit3,
  File, FileCode2, FileJson, FileText, Files, Folder, FolderGit2, FolderOpen, Gauge,
  GitBranch, HardDrive, Image, Images, LayoutGrid, Menu, MessageSquareText, MoreHorizontal,
  PanelLeftClose, PanelRightClose, Play, Plus, RefreshCw, Save, Search, Settings,
  ShieldCheck, Sparkles, Terminal, Trash2, Wifi, WifiOff, X,
} from 'lucide-react'
import { assignConversationProject, connectConversation, createConversation, createProject, createSchedule, deleteImage, importImages, listImages, loadBootstrap, loadEvents, loadFile, loadWorkspaceTree, requestUpdate, respondApproval, runSchedule, saveFile, searchConversations, sendPrompt, updateSchedule } from './api'
import type { BootstrapPayload, ConnectionState, Conversation, EventKind, Project, Schedule, StreamEvent, View, WorkspaceFile } from './types'

const iconSize = 17

function IconButton({ label, children, onClick, active = false, disabled = false }: { label: string; children: React.ReactNode; onClick?: () => void; active?: boolean; disabled?: boolean }) {
  return <button className={`icon-button ${active ? 'active' : ''}`} aria-label={label} title={label} onClick={onClick} disabled={disabled}>{children}</button>
}

function StatusDot({ status }: { status: Conversation['status'] }) {
  return <span className={`status-dot ${status}`} aria-label={status}>{status === 'running' && <span />}</span>
}

function ConnectionPill({ state }: { state: ConnectionState }) {
  const online = state === 'online'
  return <span className={`connection-pill ${state}`}>{online ? <Wifi size={12} /> : <WifiOff size={12} />}{online ? 'Local' : state === 'demo' ? 'Demo data' : state}</span>
}

function AppRail({ view, setView, openLeft, openRight }: { view: View; setView: (v: View) => void; openLeft: () => void; openRight: () => void }) {
  const items: Array<[View, string, ComponentType<{ size?: number }>]> = [
    ['chat', 'Chats', MessageSquareText], ['projects', 'Projects', LayoutGrid], ['schedules', 'Scheduled tasks', CalendarClock],
    ['images', 'Image library', Images], ['settings', 'Settings', Settings],
  ]
  return <nav className="app-rail" aria-label="Application">
    <button className="brand" onClick={() => setView('chat')} aria-label="Codex Web UI home"><Sparkles size={19} /><span>CW</span></button>
    <div className="rail-main">
      {items.map(([key, label, Icon]) => <button key={key} onClick={() => setView(key)} className={view === key ? 'active' : ''} aria-label={label} title={label}><Icon size={19} /></button>)}
    </div>
    <div className="rail-mobile-controls">
      <button onClick={openLeft} aria-label="Open chats"><PanelLeftClose size={19} /></button>
      <button onClick={openRight} aria-label="Open files"><PanelRightClose size={19} /></button>
    </div>
    <div className="avatar" title="Local user">RK</div>
  </nav>
}

function ProjectMark({ project }: { project?: Project }) {
  return <span className="project-mark" style={{ '--project-color': project?.color ?? '#9ba8a0' } as React.CSSProperties}>{project?.name.slice(0, 2).toUpperCase() ?? '—'}</span>
}

function ChatSidebar({ data, activeId, onSelect, onClose, onNewChat }: { data: BootstrapPayload; activeId: string; onSelect: (conversation: Conversation) => void; onClose: () => void; onNewChat: () => void }) {
  const [query, setQuery] = useState('')
  const [projectFilter, setProjectFilter] = useState<string>('all')
  const [newestFirst, setNewestFirst] = useState(true)
  const [remoteChats, setRemoteChats] = useState<Conversation[] | null>(null)
  const [searching, setSearching] = useState(false)
  useEffect(() => {
    if (!query.trim()) return
    const timer = window.setTimeout(() => {
      setSearching(true)
      void searchConversations(query.trim()).then(setRemoteChats).catch(() => setRemoteChats(null)).finally(() => setSearching(false))
    }, 280)
    return () => window.clearTimeout(timer)
  }, [query])
  const chats = (query.trim() && remoteChats ? remoteChats : data.conversations).filter(chat => {
    const matchesQuery = `${chat.title} ${chat.preview}`.toLowerCase().includes(query.toLowerCase())
    return matchesQuery && (projectFilter === 'all' || chat.projectId === projectFilter)
  })
  if (!newestFirst) chats.reverse()
  return <aside className="chat-sidebar">
    <header className="sidebar-header"><div><span className="eyebrow">Local Codex</span><h1>Conversations</h1></div><IconButton label="Close conversations" onClick={onClose}><X size={iconSize} /></IconButton></header>
    <button className="new-chat" onClick={onNewChat}><Plus size={16} />New conversation<span className="shortcut">⌘ N</span></button>
    <label className="search-field"><Search size={15} className={searching ? 'searching' : ''} /><input value={query} onChange={e => { setQuery(e.target.value); if (!e.target.value) setRemoteChats(null) }} placeholder="Search all resumable chats" aria-label="Search all resumable chats" />{query && <button onClick={() => { setQuery(''); setRemoteChats(null) }} aria-label="Clear search"><X size={13} /></button>}</label>
    <div className="project-filter" role="tablist" aria-label="Filter by project">
      <button className={projectFilter === 'all' ? 'active' : ''} onClick={() => setProjectFilter('all')}>All</button>
      {data.projects.slice(0, 2).map(project => <button key={project.id} className={projectFilter === project.id ? 'active' : ''} onClick={() => setProjectFilter(project.id)}><span style={{ background: project.color }} />{project.name}</button>)}
    </div>
    <div className="chat-list" aria-live="polite">
      <div className="list-label"><span>{chats.length} resumable</span><button aria-label={`Sort ${newestFirst ? 'oldest' : 'newest'} first`} onClick={() => setNewestFirst(value => !value)}><ArrowUp size={13} className={newestFirst ? '' : 'flip'} /> {newestFirst ? 'Recent' : 'Oldest'}</button></div>
      {chats.map(chat => {
        const project = data.projects.find(p => p.id === chat.projectId)
        return <button className={`chat-row ${chat.id === activeId ? 'active' : ''}`} key={chat.id} onClick={() => onSelect(chat)}>
          <ProjectMark project={project} />
          <span className="chat-row-copy"><span className="chat-title"><StatusDot status={chat.status} />{chat.title}</span><span className="chat-preview">{chat.preview}</span><span className="chat-meta"><span>{project?.name}</span><span>·</span><span>{chat.updatedAt}</span><span>·</span><span>{chat.model}</span></span></span>
        </button>
      })}
      {!chats.length && <div className="empty-state compact"><Search size={22} /><p>No conversations match.</p></div>}
    </div>
    <footer className="sidebar-footer"><HardDrive size={15} /><span><strong>On-device sessions</strong><small>Stored in ~/.codex</small></span><ShieldCheck size={16} /></footer>
  </aside>
}

const eventIcons: Record<EventKind, ComponentType<{ size?: number }>> = { message: Bot, reasoning: Sparkles, command: Terminal, file: FileCode2, approval: ShieldCheck, status: Activity }

function mergeStreamEvent(current: StreamEvent[], incoming: StreamEvent): StreamEvent[] {
  const index = current.findIndex(event => event.id === incoming.id)
  if (index < 0) return [...current, { ...incoming, append: false }]
  const existing = current[index]
  const content = incoming.append
    ? `${existing.content}${incoming.content}`
    : incoming.state === 'done' && existing.content.length > incoming.content.length
      ? existing.content
      : incoming.content || existing.content
  const next = [...current]
  next[index] = { ...existing, ...incoming, content, append: false, meta: { ...existing.meta, ...incoming.meta } }
  return next
}

function EventCard({ event, conversationId, onApproval }: { event: StreamEvent; conversationId: string; onApproval: (id: string, approved: boolean) => void }) {
  const [responding, setResponding] = useState(false)
  const [approvalError, setApprovalError] = useState('')
  const answerApproval = (approved: boolean) => {
    if (responding) return
    setResponding(true)
    setApprovalError('')
    void respondApproval(conversationId, event.id, approved, String(event.meta?.method ?? ''))
      .then(() => onApproval(event.id, approved))
      .catch(() => setApprovalError('Response was not accepted. The request remains pending; retry or use Codex CLI.'))
      .finally(() => setResponding(false))
  }
  if (event.kind === 'message') return <article className={`message ${event.role ?? 'assistant'}`}>
    <div className="message-avatar">{event.role === 'user' ? 'RK' : <Bot size={17} />}</div>
    <div className="message-body"><div className="message-author">{event.role === 'user' ? 'You' : 'Codex'}<time>{event.timestamp}</time></div><p>{event.content}</p>{event.role !== 'user' && <div className="message-actions"><button onClick={() => void navigator.clipboard.writeText(event.content)}><Copy size={13} />Copy</button></div>}</div>
  </article>
  const Icon = eventIcons[event.kind]
  return <article className={`event-card ${event.kind} ${event.state ?? ''}`}>
    <div className="event-icon"><Icon size={15} /></div>
    <div className="event-content">
      <header><span>{event.title ?? event.kind}</span><span className={`event-state ${event.state}`}>{event.state === 'running' && <RefreshCw size={11} className="spin" />}{event.state}</span><time>{event.timestamp}</time></header>
      {event.kind === 'command' ? <pre><code><span className="prompt">$</span> {event.content}</code></pre> : <p className={event.kind === 'file' ? 'file-lines' : ''}>{event.content}</p>}
      {event.meta && <div className="event-meta">{Object.entries(event.meta).map(([key, val]) => <span key={key}>{key}: <strong>{String(val)}</strong></span>)}</div>}
      {event.kind === 'approval' && event.state === 'pending' && <>{approvalError && <p className="approval-error" role="alert">{approvalError}</p>}<div className="approval-actions">{!event.meta?.unsupported && <button className="button primary" disabled={responding} onClick={() => answerApproval(true)}><Check size={14} />{responding ? 'Sending…' : 'Allow once'}</button>}<button className="button" disabled={responding} onClick={() => answerApproval(false)}><X size={14} />{responding ? 'Sending…' : event.meta?.unsupported ? 'Cancel safely' : 'Deny'}</button></div></>}
    </div>
  </article>
}

function ContextRing({ percent }: { percent: number }) {
  return <span className="context-ring" style={{ '--context': `${percent * 3.6}deg` } as React.CSSProperties}><span>{percent}%</span></span>
}

function Composer({ conversation, models, onSend }: { conversation: Conversation; models: string[]; onSend: (prompt: string, model: string, effort: string) => void }) {
  const [value, setValue] = useState('')
  const [model, setModel] = useState(conversation.model)
  const [effort, setEffort] = useState('High')
  const submit = (event: FormEvent) => { event.preventDefault(); if (!value.trim()) return; onSend(value.trim(), model, effort.toLowerCase()); setValue('') }
  return <div className="composer-wrap">
    <form className="composer" onSubmit={submit}>
      <textarea value={value} onChange={e => setValue(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} placeholder="Ask Codex to inspect, change, or run something…" aria-label="Message Codex" rows={2} />
      <div className="composer-tools">
        <div><IconButton label="Add context (not available yet)" disabled><Plus size={16} /></IconButton><button className="select-button"><Cpu size={14} /><select value={model} onChange={e => setModel(e.target.value)} aria-label="Model">{models.map(option => <option key={option}>{option}</option>)}</select><ChevronDown size={12} /></button><button className="select-button"><Gauge size={14} /><select value={effort} onChange={e => setEffort(e.target.value)} aria-label="Reasoning effort"><option>Low</option><option>Medium</option><option>High</option><option>Max</option></select><ChevronDown size={12} /></button></div>
        <div className="send-cluster"><span>Enter to send</span><button className="send-button" disabled={!value.trim()} aria-label="Send message"><ArrowUp size={17} /></button></div>
      </div>
    </form>
    <p className="composer-note">Codex can make mistakes. Review commands and workspace changes.</p>
  </div>
}

function ChatSurface({ conversation, project, projects, models, events, connection, setEvents, onAssignProject, openLeft, openRight }: { conversation: Conversation; project?: Project; projects: Project[]; models: string[]; events: StreamEvent[]; connection: ConnectionState; setEvents: React.Dispatch<React.SetStateAction<StreamEvent[]>>; onAssignProject: (projectId: string) => void; openLeft: () => void; openRight: () => void }) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [events])
  const onSend = (content: string, model: string, effort: string) => {
    const event: StreamEvent = { id: crypto.randomUUID(), kind: 'message', role: 'user', content, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
    setEvents(current => [...current, event])
    void sendPrompt(conversation.id, content, model, effort).catch(() => {
      const failure: StreamEvent = connection === 'demo'
        ? { id: crypto.randomUUID(), kind: 'message', role: 'assistant', content: 'Demo mode is active. Connect the local service to run this prompt through Codex CLI.', timestamp: 'Now' }
        : { id: crypto.randomUUID(), kind: 'status', title: 'Turn could not start', content: 'Codex could not start this turn; check connection and approval settings. Your prompt remains above for retry.', timestamp: 'Now', state: 'failed' }
      window.setTimeout(() => setEvents(current => [...current, failure]), 450)
    })
  }
  return <main className="chat-surface">
    <header className="chat-header">
      <IconButton label="Open conversations" onClick={openLeft}><Menu size={18} /></IconButton>
      <div className="chat-heading"><div><StatusDot status={conversation.status} /><h2>{conversation.title}</h2></div><span><FolderGit2 size={12} />{project?.name} · {conversation.cwd}</span></div>
      <div className="chat-header-actions"><label className="chat-project-select" title="Assign project"><FolderGit2 size={13} /><select value={conversation.projectId} onChange={event => onAssignProject(event.target.value)} aria-label="Assign conversation to project">{projects.map(option => <option key={option.id} value={option.id}>{option.name}</option>)}</select><ChevronDown size={11} /></label><ConnectionPill state={connection} /><button className="context-button" title="Context usage"><ContextRing percent={conversation.contextPercent} /><span>Context<br /><strong>{conversation.contextPercent}% used</strong></span></button><IconButton label="Open workspace" onClick={openRight}><Files size={18} /></IconButton><IconButton label="More conversation options (not available yet)" disabled><MoreHorizontal size={18} /></IconButton></div>
    </header>
    <section className="event-feed" aria-label="Conversation events">
      <div className="session-divider"><span>Session resumed</span><small>Today · {conversation.model} · {conversation.cwd}</small></div>
      {events.map(event => <EventCard event={event} conversationId={conversation.id} key={event.id} onApproval={(id, approved) => setEvents(current => current.map(item => item.id === id ? { ...item, state: approved ? 'done' : 'failed', content: approved ? `${item.content}\nApproved for this run.` : `${item.content}\nDenied.` } : item))} />)}
      {conversation.status === 'running' && <div className="working-indicator"><span /><span /><span /> Codex is working</div>}
      <div ref={endRef} />
    </section>
    <Composer conversation={conversation} models={models} onSend={onSend} />
  </main>
}

function FileTypeIcon({ file }: { file: WorkspaceFile }) {
  if (file.type === 'folder') return <Folder size={15} className="folder-icon" />
  if (file.language === 'typescript' || file.language === 'python') return <FileCode2 size={15} className={`file-icon ${file.language}`} />
  if (file.language === 'json') return <FileJson size={15} className="file-icon json" />
  if (file.language === 'markdown') return <FileText size={15} className="file-icon markdown" />
  if (file.language === 'css') return <FileCode2 size={15} className="file-icon css" />
  return <File size={15} className="file-icon" />
}

function FileTreeItem({ file, level, activePath, onSelect, onExpand }: { file: WorkspaceFile; level: number; activePath: string | null; onSelect: (file: WorkspaceFile) => void; onExpand: (file: WorkspaceFile) => void }) {
  const [expanded, setExpanded] = useState(level < 1 && file.children !== undefined)
  return <div>
    <button className={`tree-row ${activePath === file.path ? 'active' : ''}`} style={{ paddingLeft: `${10 + level * 14}px` }} onClick={() => { if (file.type === 'folder') { if (!expanded && file.children === undefined) onExpand(file); setExpanded(!expanded) } else onSelect(file) }}>
      {file.type === 'folder' ? expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} /> : <span className="tree-spacer" />}<FileTypeIcon file={file} /><span>{file.name}</span>{file.status && <i className={file.status}>{file.status[0].toUpperCase()}</i>}
    </button>
    {file.type === 'folder' && expanded && file.children?.map(child => <FileTreeItem key={child.id} file={child} level={level + 1} activePath={activePath} onSelect={onSelect} onExpand={onExpand} />)}
  </div>
}

function WorkspacePanel({ files, demo, onClose }: { files: WorkspaceFile[]; demo: boolean; onClose: () => void }) {
  const [tree, setTree] = useState(files)
  const [tab, setTab] = useState<'files' | 'changes'>('files')
  const [selected, setSelected] = useState<WorkspaceFile | null>(null)
  const [content, setContent] = useState('')
  const [editing, setEditing] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [previewError, setPreviewError] = useState('')
  useEffect(() => { if (!selected) return; void loadFile(selected.path, demo).then(result => { setContent(result.content); setPreviewError(result.error ?? '') }) }, [selected, demo])
  const selectFile = (file: WorkspaceFile) => { setEditing(false); setDirty(false); setPreviewError(''); setSelected(file) }
  const modified = useMemo(() => {
    const walk = (items: WorkspaceFile[]): WorkspaceFile[] => items.flatMap(item => [item, ...(item.children ? walk(item.children) : [])])
    return walk(tree).filter(file => file.status)
  }, [tree])
  const expandFolder = (folder: WorkspaceFile) => {
    if (demo) return
    void loadWorkspaceTree(folder.path).then(children => setTree(current => {
      const patch = (items: WorkspaceFile[]): WorkspaceFile[] => items.map(item => item.path === folder.path ? { ...item, children } : item.children ? { ...item, children: patch(item.children) } : item)
      return patch(current)
    })).catch(() => undefined)
  }
  const refreshTree = () => {
    if (demo) { setTree(files); return }
    void loadWorkspaceTree('.').then(setTree).catch(() => undefined)
  }
  return <aside className="workspace-panel">
    <header className="workspace-header"><div><span className="eyebrow">Workspace</span><h2>Explorer</h2></div><div><IconButton label="Refresh workspace" onClick={refreshTree}><RefreshCw size={15} /></IconButton><IconButton label="Close workspace" onClick={onClose}><X size={17} /></IconButton></div></header>
    <div className="workspace-tabs"><button className={tab === 'files' ? 'active' : ''} onClick={() => setTab('files')}><Files size={14} />Files</button><button className={tab === 'changes' ? 'active' : ''} onClick={() => setTab('changes')}><GitBranch size={14} />Changes <span>{modified.length}</span></button></div>
    <div className="workspace-path"><FolderOpen size={14} /><span>Workspace root</span></div>
    <div className="file-tree" aria-label="Workspace files">
      {(tab === 'files' ? tree : modified).map(file => <FileTreeItem key={file.id} file={file} level={0} activePath={selected?.path ?? null} onSelect={selectFile} onExpand={expandFolder} />)}
    </div>
    <section className={`file-preview ${selected ? 'open' : ''}`}>
      {selected ? <>
        <header><div><FileTypeIcon file={selected} /><span title={selected.path}>{selected.name}</span>{dirty && <Circle size={7} fill="currentColor" />}</div><div>{!previewError && editing && <IconButton label="Save file" onClick={() => { void saveFile(selected.path, content).then(() => setDirty(false)).catch(() => undefined) }}><Save size={14} /></IconButton>}{!previewError && <IconButton label={editing ? 'Stop editing' : 'Edit file'} onClick={() => setEditing(!editing)}>{editing ? <Check size={14} /> : <Edit3 size={14} />}</IconButton>}<IconButton label="Close preview" onClick={() => setSelected(null)}><X size={14} /></IconButton></div></header>
        <div className="preview-path">{selected.path}</div>
        {previewError ? <div className="preview-error"><AlertCircle size={20} /><strong>Preview unavailable</strong><span>{previewError}</span><small>This file stays read-only until it can be loaded safely.</small></div> : editing ? <textarea className="code-editor" value={content} onChange={e => { setContent(e.target.value); setDirty(true) }} spellCheck={false} aria-label={`Edit ${selected.name}`} /> : <pre className="code-preview"><code>{content}</code></pre>}
      </> : <div className="preview-empty"><Code2 size={27} /><span>Select a file to preview</span><small>Text files can be edited in place</small></div>}
    </section>
  </aside>
}

function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <header className="page-header"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2><p>{description}</p></div>{action}</header>
}

function Modal({ title, description, onClose, children }: { title: string; description: string; onClose: () => void; children: React.ReactNode }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><header><div><h3 id="modal-title">{title}</h3><p>{description}</p></div><IconButton label="Close dialog" onClick={onClose}><X size={17} /></IconButton></header>{children}</section></div>
}

function ProjectsPage({ projects, conversations, onAdd }: { projects: Project[]; conversations: Conversation[]; onAdd: (project: Project) => void }) {
  const [creating, setCreating] = useState(false)
  const [busy, setBusy] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [workspace, setWorkspace] = useState('.')
  const submit = (event: FormEvent) => {
    event.preventDefault(); if (!name.trim()) return; setBusy(true)
    void createProject({ name: name.trim(), description: description.trim(), workspace: workspace.trim() || '.', color: '#87d4a6' }).then(project => { onAdd(project); setCreating(false); setName(''); setDescription(''); setWorkspace('.') }).finally(() => setBusy(false))
  }
  return <div className="page"><PageHeader eyebrow="Organization" title="Projects" description="Keep workspaces, instructions, and resumable conversations together." action={<button className="button primary" onClick={() => setCreating(true)}><Plus size={15} />Add project</button>} /><div className="metric-row"><div><span>Projects</span><strong>{projects.length}</strong><small>local workspaces</small></div><div><span>Sessions</span><strong>{conversations.length}</strong><small>indexed and resumable</small></div><div><span>Active now</span><strong>{conversations.filter(c => c.status === 'running').length}</strong><small>Codex processes</small></div></div><div className="project-grid">{projects.map(project => <article className="project-card" key={project.id}><header><ProjectMark project={project} /><button disabled title="Project editing is not available yet" aria-label="Project editing is not available yet"><MoreHorizontal size={17} /></button></header><h3>{project.name}</h3><p><Folder size={13} />{project.path === '.' ? 'Workspace root' : project.path}</p><div className="project-stats"><span><MessageSquareText size={13} />{project.chatCount} chats</span><span>Updated {project.updatedAt}</span></div><footer><button disabled title="Assign or open projects from a conversation">Project overview <ChevronRight size={14} /></button></footer></article>)}<button className="add-project-card" onClick={() => setCreating(true)}><Plus size={22} /><span>Create a project</span><small>Group local conversations</small></button></div>{creating && <Modal title="Create project" description="Set the workspace new conversations should open in." onClose={() => setCreating(false)}><form className="modal-form" onSubmit={submit}><label>Project name<input autoFocus value={name} onChange={event => setName(event.target.value)} placeholder="My local project" required /></label><label>Workspace path<input value={workspace} onChange={event => setWorkspace(event.target.value)} placeholder="projects/my-app" required /></label><label>Description<textarea value={description} onChange={event => setDescription(event.target.value)} placeholder="What belongs in this project?" rows={3} /></label><footer><button type="button" className="button" onClick={() => setCreating(false)}>Cancel</button><button className="button primary" disabled={busy || !name.trim()}>{busy ? 'Creating…' : 'Create project'}</button></footer></form></Modal>}</div>
}

function SchedulesPage({ schedules, onAdd, onUpdate }: { schedules: Schedule[]; onAdd: (schedule: Schedule) => void; onUpdate: (schedule: Schedule) => void }) {
  const [creating, setCreating] = useState(false)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ name: '', prompt: '', type: 'interval' as 'interval' | 'cron', schedule: '86400', workspace: '.' })
  const toggle = (schedule: Schedule) => {
    const optimistic = { ...schedule, enabled: !schedule.enabled }; onUpdate(optimistic)
    void updateSchedule(schedule.id, { enabled: optimistic.enabled }).then(onUpdate).catch(() => onUpdate(schedule))
  }
  const submit = (event: FormEvent) => {
    event.preventDefault(); if (!form.name.trim() || !form.prompt.trim() || !form.schedule.trim()) return; setBusy(true)
    void createSchedule({ name: form.name.trim(), prompt: form.prompt.trim(), schedule_type: form.type, schedule: form.schedule.trim(), workspace: form.workspace.trim() || '.', enabled: true }).then(schedule => { onAdd(schedule); setCreating(false); setForm({ name: '', prompt: '', type: 'interval', schedule: '86400', workspace: '.' }) }).finally(() => setBusy(false))
  }
  return <div className="page"><PageHeader eyebrow="Automations" title="Scheduled tasks" description="Run Codex prompts on this device at a predictable cadence." action={<button className="button primary" onClick={() => setCreating(true)}><Plus size={15} />New task</button>} /><div className="notice"><ShieldCheck size={17} /><span><strong>Tasks run locally.</strong> Commands that require approval will pause and wait for you.</span></div><div className="schedule-list">{schedules.map(schedule => <article className={`schedule-row ${!schedule.enabled ? 'disabled' : ''}`} key={schedule.id}><button className={`toggle ${schedule.enabled ? 'on' : ''}`} onClick={() => toggle(schedule)} aria-label={`${schedule.enabled ? 'Disable' : 'Enable'} ${schedule.name}`}><span /></button><div className="schedule-icon"><CalendarClock size={18} /></div><div className="schedule-copy"><h3>{schedule.name}</h3><p>{schedule.prompt}</p><div><span><Clock3 size={12} />{schedule.cadence}</span><span><Play size={12} />Next: {schedule.nextRun}</span></div></div><div className="schedule-actions"><button aria-label="Run task" onClick={() => void runSchedule(schedule.id).catch(() => undefined)}><Play size={15} /></button><button disabled title="Task editing is not available yet" aria-label="Task editing is not available yet"><MoreHorizontal size={16} /></button></div></article>)}</div>{creating && <Modal title="New scheduled task" description="Use an interval in seconds or a five-part cron expression." onClose={() => setCreating(false)}><form className="modal-form" onSubmit={submit}><label>Task name<input autoFocus value={form.name} onChange={event => setForm(value => ({ ...value, name: event.target.value }))} placeholder="Morning repository health" required /></label><label>Prompt<textarea value={form.prompt} onChange={event => setForm(value => ({ ...value, prompt: event.target.value }))} placeholder="Check CI and summarize failures…" rows={4} required /></label><div className="form-row"><label>Schedule type<select value={form.type} onChange={event => setForm(value => ({ ...value, type: event.target.value as 'interval' | 'cron', schedule: event.target.value === 'cron' ? '0 8 * * *' : '86400' }))}><option value="interval">Interval</option><option value="cron">Cron</option></select></label><label>{form.type === 'cron' ? 'Cron expression' : 'Seconds'}<input value={form.schedule} onChange={event => setForm(value => ({ ...value, schedule: event.target.value }))} required /></label></div><label>Workspace<input value={form.workspace} onChange={event => setForm(value => ({ ...value, workspace: event.target.value }))} placeholder="." /></label><footer><button type="button" className="button" onClick={() => setCreating(false)}>Cancel</button><button className="button primary" disabled={busy}>{busy ? 'Creating…' : 'Create task'}</button></footer></form></Modal>}</div>
}

const imageTiles = [
  ['Isometric server rack', 'emerald'], ['Apartment TV concept', 'amber'], ['Review phone variants', 'blue'], ['GPU tower material pass', 'violet'], ['Workspace wireframe', 'slate'], ['Delivery drone silhouette', 'coral'],
]
function ImagesPage({ data, onChange }: { data: BootstrapPayload; onChange: (images: BootstrapPayload['images']) => void }) {
  const fileInput = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const source = data.images.length ? data.images : data.demo ? imageTiles.map(([name], index) => ({ id: `demo-${index}`, name, url: '', mime: 'image/png', size: 0, modifiedAt: 'Demo preview' })) : []
  const tiles = source.filter(asset => asset.name.toLowerCase().includes(query.toLowerCase())).map((asset, index) => ({ ...asset, color: imageTiles[index % imageTiles.length][1] }))
  const upload = (files: File[]) => { setBusy(true); void importImages(files).then(uploaded => onChange([...uploaded, ...data.images])).finally(() => setBusy(false)) }
  const refresh = () => { setBusy(true); void listImages().then(onChange).finally(() => setBusy(false)) }
  const remove = (id: string) => { if (id.startsWith('demo-')) return; void deleteImage(id).then(() => onChange(data.images.filter(image => image.id !== id))) }
  return <div className="page"><PageHeader eyebrow="Assets" title="Image library" description="Browse generated images and workspace previews kept on this device." action={<><input ref={fileInput} className="visually-hidden" type="file" accept="image/*" multiple onChange={event => event.target.files && upload([...event.target.files])} /><button className="button primary" onClick={() => fileInput.current?.click()} disabled={busy}><Plus size={15} />{busy ? 'Working…' : 'Import images'}</button></>} /><div className="library-toolbar"><label className="search-field"><Search size={15} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search images" aria-label="Search images" /></label><button className="button" onClick={refresh} disabled={busy}><RefreshCw size={14} className={busy ? 'spin' : ''} />Refresh</button><button className="button" disabled title="Grid is the only available layout"><LayoutGrid size={14} />Grid</button></div><div className="image-grid">{tiles.map((asset, index) => <article className="image-card" key={asset.id}><div className={`generated-art ${asset.color}`}>{asset.url ? <img src={asset.url} alt={asset.name} /> : <><div className="art-orbit" /><div className="art-core"><Image size={27} /></div><span>{index + 1}</span></>}</div><div><h3>{asset.name}</h3><p>{asset.size ? `${Math.round(asset.size / 1024)} KB · ${asset.modifiedAt}` : asset.modifiedAt}</p></div><button aria-label={`Delete ${asset.name}`} onClick={() => remove(asset.id)} disabled={asset.id.startsWith('demo-')}><Trash2 size={16} /></button></article>)}</div>{!tiles.length && <div className="empty-state image-empty"><Images size={28} /><p>No images match this search.</p></div>}</div>
}

function ProgressBar({ value }: { value: number | null }) { return <div className="progress"><span style={{ width: `${value ?? 0}%` }} /></div> }

function SettingsPage({ data, connection }: { data: BootstrapPayload; connection: ConnectionState }) {
  const [updating, setUpdating] = useState(false)
  const update = () => { setUpdating(true); void requestUpdate().catch(() => undefined).finally(() => window.setTimeout(() => setUpdating(false), 800)) }
  const compact = (value: number | null) => value === null ? 'Unavailable' : value >= 1_000_000 ? `${(value / 1_000_000).toFixed(2)}M` : value >= 1_000 ? `${Math.round(value / 1_000)}K` : String(value)
  const exportData = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `codex-webui-export-${new Date().toISOString().slice(0, 10)}.json`; anchor.click()
    URL.revokeObjectURL(url)
  }
  return <div className="page settings-page"><PageHeader eyebrow="Local service" title="Settings" description="Manage Codex, usage visibility, storage, and app updates." /><section className="settings-section"><h3>Account & connection</h3><div className="settings-card account-card"><div className="avatar large">RK</div><div><strong>Local Codex user</strong><span>Authenticated through Codex CLI</span></div><ConnectionPill state={connection} /><button className="button" onClick={() => location.reload()}>Reconnect</button></div></section><section className="settings-section"><h3>Usage & limits {data.demo && <em className="demo-label">Demo values</em>}</h3><div className="usage-grid"><article><header><span>Primary limit</span><strong>{data.usage.fiveHourPercent === null ? 'Unavailable' : `${data.usage.fiveHourPercent}%`}</strong></header><ProgressBar value={data.usage.fiveHourPercent} /><p>Resets: {data.usage.resetsAt}</p></article><article><header><span>Secondary limit</span><strong>{data.usage.weeklyPercent === null ? 'Unavailable' : `${data.usage.weeklyPercent}%`}</strong></header><ProgressBar value={data.usage.weeklyPercent} /><p>Reported by Codex CLI</p></article><article className="token-card"><div><span>Lifetime tokens</span><strong>{compact(data.usage.lifetimeTokens)}</strong></div><div><span>Peak daily</span><strong>{compact(data.usage.peakDailyTokens)}</strong></div><div><span>Current streak</span><strong>{data.usage.currentStreakDays === null ? 'Unavailable' : `${data.usage.currentStreakDays}d`}</strong></div></article></div><p className="settings-hint"><AlertCircle size={13} />Limit availability depends on the data exposed by your installed Codex CLI.</p></section><section className="settings-section"><h3>Runtime</h3><div className="settings-list"><div><span className="settings-icon"><Box size={16} /></span><span><strong>Codex Web UI</strong><small>{data.updatesEnabled ? 'Container image · constrained updater configured' : 'Container image · update with tools/update.sh'}</small></span><button className="button" onClick={update} disabled={updating || !data.updatesEnabled} title={data.updatesEnabled ? 'Request a configured update' : 'Run tools/update.sh on the host'}><RefreshCw size={14} className={updating ? 'spin' : ''} />{updating ? 'Requesting…' : data.updatesEnabled ? 'Request update' : 'Operator-managed'}</button></div><div><span className="settings-icon"><Terminal size={16} /></span><span><strong>Codex CLI</strong><small>Bundled in container{data.codexVersion ? ` · ${data.codexVersion}` : ''}</small></span><button className="button" onClick={() => window.open('/api/health', '_blank', 'noopener,noreferrer')}>View diagnostics</button></div><div><span className="settings-icon"><Database size={16} /></span><span><strong>Current bootstrap</strong><small>Projects, indexed sessions, schedules, images, and usage</small></span><button className="button" onClick={exportData}><Download size={14} />Export JSON</button></div></div></section></div>
}

export default function App() {
  const [data, setData] = useState<BootstrapPayload | null>(null)
  const [connection, setConnection] = useState<ConnectionState>('connecting')
  const [view, setView] = useState<View>('chat')
  const [activeId, setActiveId] = useState('')
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [leftOpen, setLeftOpen] = useState(true)
  const [rightOpen, setRightOpen] = useState(true)

  useEffect(() => { void loadBootstrap().then(result => { setData(result.data); setConnection(result.connection); setActiveId(result.data.conversations[0]?.id ?? '') }) }, [])
  useEffect(() => {
    if (!activeId) return
    void loadEvents(activeId, data?.demo ?? false).then(setEvents)
    return connectConversation(activeId, update => {
      if (update.event) setEvents(current => mergeStreamEvent(current, update.event!))
      if (update.contextPercent !== undefined) setData(current => current ? { ...current, conversations: current.conversations.map(conversation => conversation.id === activeId ? { ...conversation, contextPercent: update.contextPercent! } : conversation) } : current)
    }, setConnection)
  }, [activeId, data?.demo])

  if (!data) return <div className="loading-screen"><div className="loading-mark"><Sparkles size={26} /></div><span>Opening local workspace</span><div className="loading-bar"><i /></div></div>
  const activeConversation = data.conversations.find(chat => chat.id === activeId) ?? data.conversations[0]
  const activeProject = data.projects.find(project => project.id === activeConversation?.projectId)
  return <div className={`app-shell ${leftOpen ? 'left-open' : 'left-closed'} ${rightOpen ? 'right-open' : 'right-closed'}`}>
    <AppRail view={view} setView={setView} openLeft={() => setLeftOpen(true)} openRight={() => setRightOpen(true)} />
    {leftOpen && <ChatSidebar data={data} activeId={activeId} onSelect={conversation => { setData(current => current ? { ...current, conversations: current.conversations.some(item => item.id === conversation.id) ? current.conversations : [conversation, ...current.conversations] } : current); setActiveId(conversation.id); setView('chat') }} onClose={() => setLeftOpen(false)} onNewChat={() => {
      void createConversation({ projectId: activeProject?.id, cwd: activeProject?.path !== '.' ? activeProject?.path : activeConversation?.cwd, model: data.models[0] }).then(conversation => {
        setData(current => current ? { ...current, conversations: [conversation, ...current.conversations] } : current)
        setActiveId(conversation.id)
      }).catch(() => {
        if (data.demo) {
          const conversation: Conversation = { id: crypto.randomUUID(), projectId: activeProject?.id ?? data.projects[0].id, title: 'New demo conversation', preview: 'Visual-only local session preview', updatedAt: 'Now', status: 'ready', cwd: activeProject?.path ?? '/workspace', model: 'gpt-5.6-sol', contextPercent: 0 }
          setData(current => current ? { ...current, conversations: [conversation, ...current.conversations] } : current)
          setActiveId(conversation.id)
        } else {
          setEvents(current => [...current, { id: crypto.randomUUID(), kind: 'status', title: 'Conversation not created', content: 'Codex could not create a local thread. Check the connection and selected workspace.', timestamp: 'Now', state: 'failed' }])
        }
      })
      setView('chat')
    }} />}
    <div className="mobile-scrim left" onClick={() => setLeftOpen(false)} />
    <div className="content-area">
      {view === 'chat' && activeConversation && <ChatSurface conversation={activeConversation} project={activeProject} projects={data.projects} models={data.models} events={events} connection={connection} setEvents={setEvents} onAssignProject={projectId => { const previous = activeConversation.projectId; setData(current => current ? { ...current, conversations: current.conversations.map(chat => chat.id === activeConversation.id ? { ...chat, projectId } : chat) } : current); void assignConversationProject(activeConversation.id, projectId).catch(() => setData(current => current ? { ...current, conversations: current.conversations.map(chat => chat.id === activeConversation.id ? { ...chat, projectId: previous } : chat) } : current)) }} openLeft={() => setLeftOpen(true)} openRight={() => setRightOpen(true)} />}
      {view === 'projects' && <ProjectsPage projects={data.projects} conversations={data.conversations} onAdd={project => setData(current => current ? { ...current, projects: [...current.projects, project] } : current)} />}
      {view === 'schedules' && <SchedulesPage schedules={data.schedules} onAdd={schedule => setData(current => current ? { ...current, schedules: [schedule, ...current.schedules] } : current)} onUpdate={schedule => setData(current => current ? { ...current, schedules: current.schedules.map(item => item.id === schedule.id ? schedule : item) } : current)} />}
      {view === 'images' && <ImagesPage data={data} onChange={images => setData(current => current ? { ...current, images } : current)} />}
      {view === 'settings' && <SettingsPage data={data} connection={connection} />}
    </div>
    {rightOpen && <WorkspacePanel files={data.files} demo={data.demo} onClose={() => setRightOpen(false)} />}
    <div className="mobile-scrim right" onClick={() => setRightOpen(false)} />
  </div>
}
