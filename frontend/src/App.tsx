import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ComponentType, type FormEvent } from 'react'
import {
  Activity, AlertCircle, ArrowUp, Bot, Box, CalendarClock, Check, ChevronDown,
  ChevronRight, Circle, Clock3, Code2, Copy, Cpu, Database, Download, Edit3,
  File, FileCode2, FileJson, FileText, Files, Folder, FolderGit2, FolderOpen,
  GitBranch, Image, Images, LayoutGrid, Menu, MessageSquareText, MoreHorizontal,
  PanelLeftOpen, PanelRightClose, Play, Plus, RefreshCw, Save, Search, Settings,
  ShieldCheck, Sparkles, Terminal, Trash2, UserRound, Wifi, WifiOff, X,
} from 'lucide-react'
import { assignConversationProject, connectConversation, createConversation, createProject, createSchedule, deleteImage, importImages, listImages, loadBackgroundTerminals, loadBootstrap, loadConversations, loadOptionalMetadata, loadConversationSnapshot, loadFile, loadRealtimeCapability, loadWorkspaceChanges, loadWorkspaceTree, renameConversation, requestUpdate, respondApproval, runSchedule, saveFile, searchConversations, sendPrompt, turnStartFailureMessage, updateSchedule } from './api'
import type { RoutingDecision, RoutingStage } from './api'
import { deriveConversationTitle, isUntitledConversation } from './conversation-title'
import { ConversationListItem } from './ConversationListItem'
import { CONTEXT_TOOLS, DEFAULT_CONTEXT_TOOL, contextualConversations, type ContextToolId } from './context-tools'
import { groupEventFeed } from './event-groups'
import { MarkdownContent } from './MarkdownContent'
import { Composer } from './Composer'
import { InlineImages } from './InlineImages'
import { contextUsageLabel } from './context-usage'
import { RealtimeVoiceSession } from './realtime'
import { exactTokenCountLabel, formatTokenCount } from './token-format'
import { IDLE_TURN, isTurnActive, mergeStreamEvent, reduceTurnLifecycle, settleStreamEvents, stampAssistantMessageModel, type TurnAction } from './turn-lifecycle'
import type { BackgroundTerminal, BootstrapPayload, ConnectionState, Conversation, EventKind, LiveUpdate, Project, RealtimeCapability, RealtimeSignal, Schedule, StreamEvent, TurnLifecycle, TurnSignal, View, VoiceState, WorkspaceChanges, WorkspaceFile } from './types'

const iconSize = 17
const narrowLayoutQuery = '(max-width: 1000px)'

function isNarrowLayout() {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia(narrowLayoutQuery).matches
}

function IconButton({ label, children, onClick, active = false, disabled = false }: { label: string; children: React.ReactNode; onClick?: () => void; active?: boolean; disabled?: boolean }) {
  return <button type="button" className={`icon-button ${active ? 'active' : ''}`} aria-label={label} title={label} onClick={onClick} disabled={disabled}>{children}</button>
}

function StatusDot({ status }: { status: Conversation['status'] }) {
  return <span className={`status-dot ${status}`} aria-label={status} />
}

function ConnectionPill({ state }: { state: ConnectionState }) {
  const online = state === 'online'
  return <span className={`connection-pill ${state}`}>{online ? <Wifi size={12} /> : <WifiOff size={12} />}{online ? 'Local' : state === 'demo' ? 'Demo data' : state}</span>
}

function ProjectMark({ project }: { project?: Project }) {
  return <span className="project-mark" style={{ '--project-color': project?.color ?? '#9ba8a0' } as React.CSSProperties}>{project?.name.slice(0, 2).toUpperCase() ?? '—'}</span>
}

function ChatSidebar({ data, activeId, view, setView, onSelect, onClose, onNewChat, historyState, onRetryHistory }: { data: BootstrapPayload; activeId: string; view: View; setView: (view: View) => void; onSelect: (conversation: Conversation) => void; onClose: () => void; onNewChat: () => void; historyState: 'loading' | 'ready' | 'error'; onRetryHistory: () => void }) {
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
    <header className="sidebar-header"><button className="sidebar-brand" onClick={() => setView('chat')}><img src="/favicon-v2.png" width={26} height={26} alt="" /><span>Codex<small>2</small></span></button><IconButton label="Close conversations" onClick={onClose}><X size={iconSize} /></IconButton></header>
    <button className="new-chat" onClick={onNewChat}><Edit3 size={18} />New chat</button>
    <label className="search-field"><Search size={15} className={searching ? 'searching' : ''} /><input value={query} onChange={e => { setQuery(e.target.value); if (!e.target.value) setRemoteChats(null) }} placeholder="Search chats" aria-label="Search all resumable chats" />{query && <button onClick={() => { setQuery(''); setRemoteChats(null) }} aria-label="Clear search"><X size={13} /></button>}</label>
    <nav className="sidebar-nav" aria-label="Workspace">
      {([["projects", "Projects", FolderGit2], ["schedules", "Tasks", CalendarClock], ["images", "Images", Images]] as const).map(([key, label, Icon]) => <button key={key} className={view === key ? 'active' : ''} aria-current={view === key ? 'page' : undefined} onClick={() => setView(key)}><Icon size={18} />{label}</button>)}
    </nav>
    <div className="project-filter" role="tablist" aria-label="Filter by project">
      <button className={projectFilter === 'all' ? 'active' : ''} onClick={() => setProjectFilter('all')}>All</button>
      {data.projects.slice(0, 2).map(project => <button key={project.id} className={projectFilter === project.id ? 'active' : ''} onClick={() => setProjectFilter(project.id)}><span style={{ background: project.color }} />{project.name}</button>)}
    </div>
    <div className="chat-list" aria-live="polite">
      {historyState === 'loading' && <p className="history-notice" role="status">Loading conversations…</p>}
      {historyState === 'error' && <p className="history-notice" role="alert">Conversations could not be loaded. <button type="button" onClick={onRetryHistory}>Retry</button></p>}
      <div className="list-label"><span>{chats.length} resumable</span><button aria-label={`Sort ${newestFirst ? 'oldest' : 'newest'} first`} onClick={() => setNewestFirst(value => !value)}><ArrowUp size={13} className={newestFirst ? '' : 'flip'} /> {newestFirst ? 'Recent' : 'Oldest'}</button></div>
      {chats.map(chat => <ConversationListItem key={chat.id} conversation={chat} project={data.projects.find(project => project.id === chat.projectId)} active={chat.id === activeId && view === 'chat'} onSelect={() => onSelect(chat)} statusIndicator={chat.status === 'running' ? <StatusDot status={chat.status} /> : undefined} />)}
      {!chats.length && historyState === 'ready' && <div className="empty-state compact"><Search size={22} /><p>No conversations match.</p></div>}
    </div>
    <footer className="sidebar-footer"><button className="profile-button" onClick={() => setView('settings')} aria-label="Open settings"><span className="avatar"><Terminal size={16} /></span><span><strong>Local workspace</strong><small>{data.demo ? 'Preview mode' : 'Connected through Codex'}</small></span><Settings size={17} /></button></footer>
  </aside>
}

const eventIcons: Record<EventKind, ComponentType<{ size?: number }>> = { message: Bot, image: Image, reasoning: Sparkles, command: Terminal, file: FileCode2, approval: ShieldCheck, status: Activity }

function EventState({ event }: { event: StreamEvent }) {
  return <span className={`event-state ${event.state}`}>{event.state}</span>
}

function MessageModel({ model }: { model: string }) {
  return <span className="message-model" title={`Model used: ${model}`}><Cpu size={10} /><span>{model}</span></span>
}

function CommandCard({ event }: { event: StreamEvent }) {
  const commandLine = event.content.split('\n').find(line => line.trim())?.trim() || event.title || 'Command'
  return <details className={`command-card ${event.state ?? ''}`}>
    <summary><ChevronRight size={13} className="disclosure-chevron" /><Terminal size={13} /><span><strong>{event.title ?? 'Command'}</strong><code>{commandLine}</code></span><EventState event={event} /><time>{event.timestamp}</time></summary>
    <div className="command-card-body"><pre><code><span className="prompt">$</span> {event.content}</code></pre>{event.meta && <div className="event-meta">{Object.entries(event.meta).map(([key, val]) => <span key={key}>{key}: <strong>{String(val)}</strong></span>)}</div>}</div>
  </details>
}

function CommandGroup({ commands }: { commands: StreamEvent[] }) {
  const aggregateState: StreamEvent['state'] = commands.some(command => command.state === 'running')
    ? 'running'
    : commands.some(command => command.state === 'failed')
      ? 'failed'
      : commands.every(command => command.state === 'done')
        ? 'done'
        : 'pending'
  const aggregateEvent = { ...commands.at(-1)!, state: aggregateState }
  const label = aggregateState === 'running'
    ? `${commands.length} ${commands.length === 1 ? 'command' : 'commands'} running`
    : `${commands.length} ${commands.length === 1 ? 'command' : 'commands'} ran`
  return <details className={`command-group ${aggregateState}`}>
    <summary><span className="event-icon"><Terminal size={15} /></span><span className="command-group-label"><strong>{label}</strong><small>Show command activity</small></span><EventState event={aggregateEvent} /><time>{aggregateEvent.timestamp}</time><ChevronRight size={14} className="disclosure-chevron" /></summary>
    <div className="command-group-items">{commands.map(command => <CommandCard event={command} key={command.id} />)}</div>
  </details>
}

function EventCard({ event, conversationId, fallbackModel, onApproval }: { event: StreamEvent; conversationId: string; fallbackModel: string; onApproval: (id: string, approved: boolean) => void }) {
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
  if (event.kind === 'message' || event.kind === 'image') {
    const assistantRunning = event.role !== 'user' && event.state === 'running'
    const messageModel = typeof event.meta?.model === 'string' ? event.meta.model : fallbackModel
    if (!event.content && !event.images?.length) return null
    return <article className={`message ${event.role ?? 'assistant'} ${event.state ?? ''} ${assistantRunning ? 'streaming' : ''}`}>
      <div className="message-avatar">{event.role === 'user' ? <UserRound size={17} /> : <Bot size={17} />}</div>
      <div className="message-body">
        <div className="message-author">{event.role === 'user' ? 'You' : 'Codex'}{event.role !== 'user' && <MessageModel model={messageModel} />}<time>{event.timestamp}</time></div>
        {event.content
          ? event.role === 'user'
            ? <p>{event.content}</p>
            : <div className={`message-rendered ${assistantRunning ? 'streaming' : ''}`} aria-live={assistantRunning ? 'polite' : undefined}><MarkdownContent source={event.content} /></div>
          : null}
        {!!event.images?.length && <InlineImages images={event.images} />}
        {event.role !== 'user' && event.content && !assistantRunning && <div className="message-actions"><button onClick={() => void navigator.clipboard.writeText(event.content)}><Copy size={13} />Copy</button></div>}
      </div>
    </article>
  }
  if (event.kind === 'command') return <CommandCard event={event} />
  if (event.kind === 'reasoning' && !event.content) return null
  if (event.kind === 'reasoning') return <details className="reasoning-disclosure"><summary><Sparkles size={15} /><span>Thought summary</span><ChevronRight size={14} className="disclosure-chevron" /></summary><MarkdownContent source={event.content} compact /></details>
  const Icon = eventIcons[event.kind]
  return <article className={`event-card ${event.kind} ${event.state ?? ''}`}>
    <div className="event-icon"><Icon size={15} /></div>
    <div className="event-content">
      <header><span>{event.title ?? event.kind}</span><EventState event={event} /><time>{event.timestamp}</time></header>
      <p className={event.kind === 'file' ? 'file-lines' : ''}>{event.content}</p>
      {event.meta && <div className="event-meta">{Object.entries(event.meta).map(([key, val]) => <span key={key}>{key}: <strong>{String(val)}</strong></span>)}</div>}
      {event.kind === 'approval' && event.state === 'pending' && <>{approvalError && <p className="approval-error" role="alert">{approvalError}</p>}<div className="approval-actions">{!event.meta?.unsupported && <button className="button primary" disabled={responding} onClick={() => answerApproval(true)}><Check size={14} />{responding ? 'Sending…' : 'Allow once'}</button>}<button className="button" disabled={responding} onClick={() => answerApproval(false)}><X size={14} />{responding ? 'Sending…' : event.meta?.unsupported ? 'Cancel safely' : 'Deny'}</button></div></>}
    </div>
  </article>
}

function ContextRing({ percent, known }: { percent: number; known: boolean }) {
  return <span className="context-ring" style={{ '--context': `${percent * 3.6}deg` } as React.CSSProperties}><span>{known ? `${percent}%` : '—'}</span></span>
}

interface ChatSurfaceProps {
  conversation: Conversation
  project?: Project
  projects: Project[]
  models: string[]
  events: StreamEvent[]
  turn: TurnLifecycle
  historyLoading: boolean
  connection: ConnectionState
  realtimeSignal: RealtimeSignal | null
  voiceCapability: RealtimeCapability
  setEvents: React.Dispatch<React.SetStateAction<StreamEvent[]>>
  onTurnAction: (action: TurnAction) => void
  onConversationStatus: (status: Conversation['status']) => void
  onTurnModel: (model: string) => void
  onAssignProject: (projectId: string) => void
  onRename: (title: string) => Promise<void>
  leftOpen: boolean
  toggleLeft: () => void
  openRight: () => void
}

function ChatSurface({ conversation, project, projects, events, turn, historyLoading, connection, realtimeSignal, voiceCapability, setEvents, onTurnAction, onConversationStatus, onTurnModel, onAssignProject, onRename, leftOpen, toggleLeft, openRight }: ChatSurfaceProps) {
  const feedRef = useRef<HTMLElement>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)
  const [voiceState, setVoiceState] = useState<VoiceState>('idle')
  const [voiceMessage, setVoiceMessage] = useState('')
  const [renaming, setRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState(conversation.title)
  const [renameError, setRenameError] = useState('')
  const [savingName, setSavingName] = useState(false)
  const [selectedModel, setSelectedModel] = useState(conversation.model)
  const [routingStage, setRoutingStage] = useState<RoutingStage | null>(null)
  const [decision, setDecision] = useState<RoutingDecision | null>(null)
  const submitting = useRef(false)
  const sendController = useRef<AbortController | null>(null)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; sendController.current?.abort() } }, [])
  const autoTitleThread = useRef('')
  const currentTitle = useRef(conversation.title)
  const voiceSession = useMemo(() => new RealtimeVoiceSession((state, message) => { setVoiceState(state); setVoiceMessage(message ?? '') }), [])
  const turnActive = isTurnActive(turn)
  const voiceUnavailableReason = !voiceCapability.available
    ? voiceCapability.reason ?? 'Realtime voice is unavailable for this conversation.'
    : !voiceSession.supported
      ? 'This browser cannot open a WebRTC microphone session.'
      : ''
  const effectiveVoiceState: VoiceState = voiceUnavailableReason ? 'unsupported' : voiceState
  const effectiveVoiceMessage = voiceUnavailableReason || voiceMessage
  const voiceEnabled = !voiceUnavailableReason && connection === 'online'
  useLayoutEffect(() => {
    if (stickToBottom.current) endRef.current?.scrollIntoView({ block: 'end' })
  }, [events, turn.phase])
  useEffect(() => {
    if (realtimeSignal) void voiceSession.handle(realtimeSignal).catch(error => { setVoiceState('error'); setVoiceMessage(error instanceof Error ? error.message : 'Realtime voice failed.') })
  }, [realtimeSignal, voiceSession])
  useEffect(() => () => { void voiceSession.stop(true).catch(() => undefined) }, [conversation.id, voiceSession])
  useEffect(() => { currentTitle.current = conversation.title }, [conversation.title])
  const openRename = () => {
    setRenameValue(conversation.title)
    setRenameError('')
    setRenaming(true)
  }
  const closeRename = () => {
    if (savingName) return
    setRenaming(false)
    setRenameValue(conversation.title)
    setRenameError('')
  }
  const submitRename = (event: FormEvent) => {
    event.preventDefault()
    const nextTitle = renameValue.trim()
    if (!nextTitle || savingName) return
    currentTitle.current = nextTitle
    setSavingName(true)
    setRenameError('')
    void onRename(nextTitle)
      .then(() => setRenaming(false))
      .catch(() => setRenameError('The name could not be saved. Retry after checking the local service.'))
      .finally(() => setSavingName(false))
  }
  const toggleVoice = () => {
    if (voiceState === 'live' || voiceState === 'connecting') void voiceSession.stop(true).catch(error => { setVoiceState('error'); setVoiceMessage(error instanceof Error ? error.message : 'Could not stop realtime voice.') })
    else void voiceSession.start(conversation.id).catch(() => undefined)
  }
  const onSend = async (content: string, plugins: string[]): Promise<boolean> => {
    if (submitting.current || historyLoading || turnActive || voiceState === 'live' || voiceState === 'connecting') return false
    submitting.current = true
    const controller = new AbortController()
    sendController.current = controller
    const requestId = crypto.randomUUID()
    setEvents(current => [...current, { id: crypto.randomUUID(), kind: 'message', role: 'user', content, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), meta: { optimistic: true } }])
    try {
      const result = await sendPrompt(conversation.id, content, (stage, chosen) => {
        if (!mounted.current) return
        setRoutingStage(stage)
        if (chosen) { setDecision(chosen); setSelectedModel(chosen.model); onTurnModel(chosen.model) }
        // Register before the single HTTP request so late progress cannot reset
        // a turn that already completed on the event socket.
        if (stage === 'routing') { onTurnAction({ type: 'submitted', requestId }); onConversationStatus('running') }
      }, controller.signal, plugins)
      if (!mounted.current) return true
      onTurnAction({ type: 'acknowledged', requestId, turnId: result.turnId })
      if (isUntitledConversation(currentTitle.current) && autoTitleThread.current !== conversation.id) {
        const provisionalTitle = deriveConversationTitle(content)
        autoTitleThread.current = conversation.id
        currentTitle.current = provisionalTitle
        void onRename(provisionalTitle).catch(() => { autoTitleThread.current = ''; currentTitle.current = conversation.title; setRenameError('The name could not be saved. Rename this conversation manually.') })
      }
      return true
    } catch (error) {
      if (!mounted.current) return false
      onTurnAction({ type: 'request-failed', requestId, message: 'This message could not be sent.' })
      onConversationStatus('failed')
      setEvents(current => [...current, { id: crypto.randomUUID(), kind: 'status', title: 'Message not sent', content: connection === 'demo' ? 'This is a visual preview. Start the companion to route messages through Jev and Codex.' : turnStartFailureMessage(error), timestamp: 'Now', state: 'failed' }])
      return false
    } finally {
      submitting.current = false
      if (mounted.current) setRoutingStage(null)
    }
  }
  const feedEntries = groupEventFeed(events)
  return <main className={`chat-surface ${events.length === 0 ? 'empty-chat' : ''} ${leftOpen ? '' : 'left-panel-closed'}`}>
    <header className="chat-header">
      <IconButton label={`${leftOpen ? 'Collapse' : 'Expand'} conversations`} onClick={toggleLeft}>{leftOpen ? <Menu size={18} /> : <PanelLeftOpen size={18} />}</IconButton>
      <div className="chat-heading">
        <div><StatusDot status={conversation.status} /><h2 className="conversation-title" onDoubleClick={openRename} title="Double-click to rename">{conversation.title}</h2><button type="button" className="rename-trigger" onClick={openRename} aria-label="Rename conversation" title="Rename conversation"><Edit3 size={12} /></button></div>
        <span><FolderGit2 size={12} />{project?.name} · {conversation.cwd}</span>{renameError && !renaming && <small className="chat-name-error" role="alert">{renameError}</small>}
      </div>
      <div className="chat-header-actions"><span className="chat-model-select" title={decision ? `Chosen by Jev · ${decision.effort} reasoning` : 'Jev will choose a model for your next message'}><Sparkles size={14} /><span>Auto</span><strong>{decision ? selectedModel.replace('gpt-', '') : 'Jev'}</strong></span><label className="chat-project-select" title="Assign project"><FolderGit2 size={14} /><select value={conversation.projectId} onChange={event => onAssignProject(event.target.value)} aria-label="Assign conversation to project">{projects.map(option => <option key={option.id} value={option.id}>{option.name}</option>)}</select></label><ConnectionPill state={connection} /><span className="context-button" tabIndex={0} aria-label={contextUsageLabel(conversation)} title={contextUsageLabel(conversation)}><ContextRing percent={conversation.contextPercent} known={conversation.contextWindowTokens !== undefined} /></span><IconButton label="Open context panel" onClick={openRight}><PanelRightClose size={18} /></IconButton></div>
    </header>
    <section className="event-feed" aria-label="Conversation events" ref={feedRef} onScroll={() => { const feed = feedRef.current; if (feed) stickToBottom.current = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 120 }}>
      {events.length === 0 && <div className="chat-welcome"><span className="welcome-mark"><Sparkles size={32} /></span><h1>What are we building?</h1><p>A clear space to think, create, and get things done.</p><div className="welcome-hints"><span><Code2 size={16} />Build something</span><span><Search size={16} />Explore a project</span><span><Sparkles size={16} />Refine an idea</span></div></div>}
      {feedEntries.map(entry => entry.type === 'commands'
        ? <CommandGroup commands={entry.commands} key={entry.id} />
        : <EventCard event={entry.event} conversationId={conversation.id} fallbackModel={conversation.model} key={entry.event.id} onApproval={(id, approved) => setEvents(current => current.map(item => item.id === id ? { ...item, state: approved ? 'done' : 'failed', content: approved ? `${item.content}\nApproved for this run.` : `${item.content}\nDenied.` } : item))} />)}
      {(routingStage || turnActive || historyLoading) && <div className="chat-progress" role="status" aria-live="polite"><RefreshCw size={14} className="spin" /><span>{routingStage === 'routing' ? 'Choosing the right model…' : routingStage === 'switching' ? `Switching to ${decision?.model}…` : routingStage === 'sending' ? 'Sending your message…' : turnActive ? turn.phase === 'streaming' ? 'Responding…' : 'Thinking…' : 'Loading conversation…'}</span></div>}
      <div ref={endRef} />
    </section>
    <Composer cwd={conversation.cwd} busy={historyLoading || turnActive || routingStage !== null || voiceState === 'live' || voiceState === 'connecting'} onSend={onSend} voiceEnabled={voiceEnabled} voiceState={effectiveVoiceState} voiceMessage={effectiveVoiceMessage} onVoiceToggle={toggleVoice} />
    {renaming && <Modal title="Rename conversation" description="Choose a concise name that will be easy to find later." onClose={closeRename}><form className="modal-form rename-modal-form" onSubmit={submitRename}><label>Conversation name<input autoFocus maxLength={200} value={renameValue} onChange={event => setRenameValue(event.target.value)} onFocus={event => event.currentTarget.select()} onKeyDown={event => { if (event.key === 'Escape') closeRename() }} aria-label="Conversation name" /></label>{renameError && <p className="modal-error" role="alert">{renameError}</p>}<footer><button type="button" className="button" disabled={savingName} onClick={closeRename}>Cancel</button><button className="button primary" disabled={!renameValue.trim() || savingName}>{savingName ? 'Saving…' : 'Save'}</button></footer></form></Modal>}
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

const contextToolIcons: Record<ContextToolId, ComponentType<{ size?: number }>> = {
  outputs: Activity,
  browser: LayoutGrid,
  terminal: Terminal,
  'side-chats': MessageSquareText,
  explorer: Files,
  changes: GitBranch,
}

function OutputsContext({ events }: { events: StreamEvent[] }) {
  const outputs = events.filter(event => event.kind === 'command' || event.kind === 'file' || event.kind === 'approval' || event.kind === 'status').slice(-12).reverse()
  return <section className="context-output-view" id="context-tool-outputs" role="tabpanel" aria-label="Outputs">
    <div className="context-section-heading"><div><span>Conversation activity</span><small>{outputs.length} recent items</small></div><Activity size={16} /></div>
    <div className="context-output-list">
      {outputs.map(event => {
        const Icon = eventIcons[event.kind]
        return <article className="context-output-row" key={event.id}><span className={`context-output-icon ${event.kind}`}><Icon size={14} /></span><div><strong>{event.title ?? event.kind}</strong><p>{event.content}</p><small>{event.timestamp}{event.state ? ` · ${event.state}` : ''}</small></div></article>
      })}
      {!outputs.length && <div className="context-empty"><Activity size={24} /><strong>No outputs yet</strong><span>Command, file, status, and approval activity will appear here.</span></div>}
    </div>
  </section>
}

function PlannedContext({ toolId }: { toolId: ContextToolId }) {
  const tool = CONTEXT_TOOLS.find(item => item.id === toolId) ?? CONTEXT_TOOLS[0]
  const Icon = contextToolIcons[tool.id]
  return <section className="context-placeholder" id={`context-tool-${tool.id}`} role="tabpanel" aria-label={tool.label}>
    <span className="context-placeholder-icon"><Icon size={24} /></span>
    <span className="eyebrow">Planned surface</span>
    <h3>{tool.label}</h3>
    <p>{tool.description}</p>
    <small>{tool.backing}. No private desktop interface is being assumed.</small>
  </section>
}

function formatTerminalMemory(rssKb?: number) {
  if (rssKb === undefined) return 'Memory unavailable'
  return rssKb >= 1024 * 1024 ? `${(rssKb / 1024 / 1024).toFixed(1)} GB` : rssKb >= 1024 ? `${(rssKb / 1024).toFixed(1)} MB` : `${rssKb} KB`
}

function TerminalContext({ conversationId, demo }: { conversationId?: string; demo: boolean }) {
  const [terminals, setTerminals] = useState<BackgroundTerminal[]>([])
  const [state, setState] = useState<'loading' | 'ready' | 'error'>(conversationId && !demo ? 'loading' : 'ready')
  const [error, setError] = useState('')
  const [unavailableReason, setUnavailableReason] = useState('')
  const refresh = () => {
    if (!conversationId || demo) return
    setState('loading')
    setError('')
    setUnavailableReason('')
    void loadBackgroundTerminals(conversationId).then(result => { setTerminals(result.items); setUnavailableReason(result.unavailableReason ?? ''); setState('ready') }).catch(reason => {
      setState('error')
      setError(reason instanceof Error ? reason.message : 'Background terminal inventory is unavailable.')
    })
  }
  useEffect(() => {
    if (!conversationId || demo) return
    let disposed = false
    void loadBackgroundTerminals(conversationId).then(result => {
      if (!disposed) { setTerminals(result.items); setUnavailableReason(result.unavailableReason ?? ''); setState('ready') }
    }).catch(reason => {
      if (!disposed) { setState('error'); setError(reason instanceof Error ? reason.message : 'Background terminal inventory is unavailable.') }
    })
    return () => { disposed = true }
  }, [conversationId, demo])
  return <section className="context-output-view terminal-context" id="context-tool-terminal" role="tabpanel" aria-label="Terminal">
    <div className="context-section-heading"><div><span>Background processes</span><small>Read-only · this Codex thread</small></div><IconButton label="Refresh background processes" onClick={refresh}><RefreshCw size={15} className={state === 'loading' ? 'spin' : ''} /></IconButton></div>
    <div className="terminal-list">
      {terminals.map(terminal => <article className="terminal-row" key={terminal.processId}>
        <header><span className="terminal-live"><Circle size={7} fill="currentColor" />Running</span><small>{terminal.osPid !== undefined ? `PID ${terminal.osPid}` : `Process ${terminal.processId}`}</small></header>
        <pre><code>{terminal.command || 'Background command'}</code></pre>
        <footer><span title={terminal.cwd}>{terminal.cwd}</span><span>{terminal.cpuPercent !== undefined ? `${terminal.cpuPercent.toFixed(1)}% CPU` : 'CPU unavailable'} · {formatTerminalMemory(terminal.rssKb)}</span></footer>
      </article>)}
      {state === 'loading' && !terminals.length && <div className="context-empty"><RefreshCw size={23} className="spin" /><strong>Checking background processes</strong><span>Reading the public thread-scoped terminal inventory.</span></div>}
      {state === 'error' && <div className="context-empty error"><AlertCircle size={23} /><strong>Process inventory unavailable</strong><span>{error}</span></div>}
      {state === 'ready' && !terminals.length && unavailableReason && <div className="context-empty"><AlertCircle size={23} /><strong>Process inventory limited</strong><span>{unavailableReason}</span></div>}
      {state === 'ready' && !terminals.length && !unavailableReason && <div className="context-empty"><Terminal size={24} /><strong>No background processes</strong><span>Commands started by Codex still appear under Outputs; this surface never starts arbitrary shell commands.</span></div>}
    </div>
  </section>
}

function SideChatsContext({ conversations, current, onSelect }: { conversations: Conversation[]; current?: Conversation; onSelect: (conversation: Conversation) => void }) {
  const related = current ? contextualConversations(conversations, current) : conversations.slice(0, 12)
  return <section className="context-output-view" id="context-tool-side-chats" role="tabpanel" aria-label="Side chats">
    <div className="context-section-heading"><div><span>Related conversations</span><small>Backed by the local Codex thread index</small></div><MessageSquareText size={16} /></div>
    <div className="side-chat-list">
      {related.map(conversation => <button className="side-chat-row" key={conversation.id} onClick={() => onSelect(conversation)}>
        <StatusDot status={conversation.status} /><span><strong>{conversation.title}</strong><small>{conversation.preview}</small><em>{conversation.updatedAt} · {conversation.model}</em></span><ChevronRight size={14} />
      </button>)}
      {!related.length && <div className="context-empty"><MessageSquareText size={24} /><strong>No related conversations</strong><span>Recent resumable Codex threads will appear here.</span></div>}
    </div>
  </section>
}

function ContextPanel({ files, demo, events, conversations, currentConversation, activeTool, onToolChange, onSelectConversation, onClose }: { files: WorkspaceFile[]; demo: boolean; events: StreamEvent[]; conversations: Conversation[]; currentConversation?: Conversation; activeTool: ContextToolId; onToolChange: (tool: ContextToolId) => void; onSelectConversation: (conversation: Conversation) => void; onClose: () => void }) {
  const [tree, setTree] = useState(files)
  const [treeError, setTreeError] = useState('')
  const [selected, setSelected] = useState<WorkspaceFile | null>(null)
  const [content, setContent] = useState('')
  const [editing, setEditing] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [previewError, setPreviewError] = useState('')
  const [changes, setChanges] = useState<WorkspaceChanges>({ files: [] })
  const [changesState, setChangesState] = useState<'loading' | 'ready' | 'error'>(demo ? 'ready' : 'loading')
  const [changesError, setChangesError] = useState('')
  useEffect(() => { if (!selected) return; void loadFile(selected.path, demo).then(result => { setContent(result.content); setPreviewError(result.error ?? '') }) }, [selected, demo])
  const selectFile = (file: WorkspaceFile) => { setEditing(false); setDirty(false); setPreviewError(''); setSelected(file) }
  const modified = useMemo(() => {
    const walk = (items: WorkspaceFile[]): WorkspaceFile[] => items.flatMap(item => [item, ...(item.children ? walk(item.children) : [])])
    return walk(tree).filter(file => file.status)
  }, [tree])
  useEffect(() => {
    if (demo) return
    let disposed = false
    void loadWorkspaceChanges(currentConversation?.cwd ?? '.').then(result => {
      if (!disposed) { setChanges(result); setChangesState('ready'); setChangesError('') }
    }).catch(reason => {
      if (!disposed) { setChanges({ files: [] }); setChangesState('error'); setChangesError(reason instanceof Error ? reason.message : 'Workspace changes are unavailable.') }
    })
    return () => { disposed = true }
  }, [currentConversation?.cwd, demo])
  const refreshChanges = () => {
    if (demo) return
    setChangesState('loading')
    setChangesError('')
    void loadWorkspaceChanges(currentConversation?.cwd ?? '.').then(result => { setChanges(result); setChangesState('ready') }).catch(reason => {
      setChanges({ files: [] })
      setChangesState('error')
      setChangesError(reason instanceof Error ? reason.message : 'Workspace changes are unavailable.')
    })
  }
  const expandFolder = (folder: WorkspaceFile) => {
    if (demo) return
    void loadWorkspaceTree(folder.path).then(children => setTree(current => {
      const patch = (items: WorkspaceFile[]): WorkspaceFile[] => items.map(item => item.path === folder.path ? { ...item, children } : item.children ? { ...item, children: patch(item.children) } : item)
      return patch(current)
    })).catch(() => undefined)
  }
  useEffect(() => {
    if (demo || activeTool !== 'explorer') return
    let disposed = false
    void loadWorkspaceTree('.').then(items => { if (!disposed) { setTree(items); setTreeError('') } }).catch(() => { if (!disposed) setTreeError('Workspace files could not be loaded. Use Refresh to try again.') })
    return () => { disposed = true }
  }, [activeTool, demo])
  const refreshTree = () => {
    if (demo) { setTree(files); return }
    void loadWorkspaceTree('.').then(items => { setTree(items); setTreeError('') }).catch(() => setTreeError('Workspace files could not be loaded. Use Refresh to try again.'))
  }
  const activeDefinition = CONTEXT_TOOLS.find(tool => tool.id === activeTool) ?? CONTEXT_TOOLS[0]
  const workspaceActive = activeTool === 'explorer' || activeTool === 'changes'
  const reportedChanges = demo ? modified : changes.files
  return <aside className="context-panel" aria-label="Context panel">
    <header className="context-panel-header"><div><span className="eyebrow">Context panel</span><h2>{activeDefinition.label}</h2></div><div>{workspaceActive && <IconButton label={activeTool === 'changes' ? 'Refresh workspace changes' : 'Refresh workspace'} onClick={activeTool === 'changes' ? refreshChanges : refreshTree}><RefreshCw size={15} className={activeTool === 'changes' && changesState === 'loading' ? 'spin' : ''} /></IconButton>}<IconButton label="Close context panel" onClick={onClose}><X size={17} /></IconButton></div></header>
    <div className="context-tool-tabs" role="tablist" aria-label="Context tools">
      {CONTEXT_TOOLS.map(tool => {
        const Icon = contextToolIcons[tool.id]
        return <button key={tool.id} role="tab" aria-selected={activeTool === tool.id} aria-controls={`context-tool-${tool.id}`} className={activeTool === tool.id ? 'active' : ''} onClick={() => onToolChange(tool.id)} title={`${tool.label} · ${tool.availability === 'planned' ? 'planned' : tool.backing}`}><Icon size={15} /><span>{tool.label}</span>{tool.id === 'changes' && <i>{reportedChanges.length}</i>}{tool.availability === 'planned' && <b aria-label="Planned" />}</button>
      })}
    </div>
    {activeTool === 'outputs' && <OutputsContext events={events} />}
    {activeTool === 'browser' && <PlannedContext toolId={activeTool} />}
    {activeTool === 'terminal' && <TerminalContext key={currentConversation?.id ?? 'none'} conversationId={currentConversation?.id} demo={demo} />}
    {activeTool === 'side-chats' && <SideChatsContext conversations={conversations} current={currentConversation} onSelect={onSelectConversation} />}
    {workspaceActive && <section className="workspace-context" id={`context-tool-${activeTool}`} role="tabpanel" aria-label={activeDefinition.label}>
      <div className="workspace-path"><FolderOpen size={14} /><span>{activeTool === 'changes' ? changes.repoRoot ? `Changes · ${changes.repoRoot}` : 'Changed files' : 'Workspace root'}</span></div>
      <div className="file-tree" aria-label={activeTool === 'changes' ? 'Workspace changes' : 'Workspace files'}>
        {activeTool === 'explorer' && treeError && <p className="history-notice" role="alert">{treeError}</p>}
        {(activeTool === 'explorer' ? tree : reportedChanges).map(file => <FileTreeItem key={file.id} file={file} level={0} activePath={selected?.path ?? null} onSelect={selectFile} onExpand={expandFolder} />)}
        {activeTool === 'changes' && changesState === 'loading' && !reportedChanges.length && <div className="context-empty"><RefreshCw size={23} className="spin" /><strong>Reading Git status</strong><span>Only the selected conversation folder inside the configured workspace is inspected.</span></div>}
        {activeTool === 'changes' && changesState === 'error' && <div className="context-empty error"><AlertCircle size={23} /><strong>Changes unavailable</strong><span>{changesError}</span></div>}
        {activeTool === 'changes' && changesState === 'ready' && !reportedChanges.length && <div className="context-empty"><GitBranch size={24} /><strong>No reported changes</strong><span>The bounded Git adapter reports a clean worktree.</span></div>}
      </div>
      <section className={`file-preview ${selected ? 'open' : ''}`}>
        {selected ? <>
          <header><div><FileTypeIcon file={selected} /><span title={selected.path}>{selected.name}</span>{dirty && <Circle size={7} fill="currentColor" />}</div><div>{!previewError && editing && <IconButton label="Save file" onClick={() => { void saveFile(selected.path, content).then(() => setDirty(false)).catch(() => undefined) }}><Save size={14} /></IconButton>}{!previewError && <IconButton label={editing ? 'Stop editing' : 'Edit file'} onClick={() => setEditing(!editing)}>{editing ? <Check size={14} /> : <Edit3 size={14} />}</IconButton>}<IconButton label="Close preview" onClick={() => setSelected(null)}><X size={14} /></IconButton></div></header>
          <div className="preview-path">{selected.path}</div>
          {previewError ? <div className="preview-error"><AlertCircle size={20} /><strong>Preview unavailable</strong><span>{previewError}</span><small>This file stays read-only until it can be loaded safely.</small></div> : editing ? <textarea className="code-editor" value={content} onChange={e => { setContent(e.target.value); setDirty(true) }} spellCheck={false} aria-label={`Edit ${selected.name}`} /> : <pre className="code-preview"><code>{content}</code></pre>}
        </> : <div className="preview-empty"><Code2 size={27} /><span>Select a file to preview</span><small>Text files can be edited in place</small></div>}
      </section>
    </section>}
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
  const [error, setError] = useState('')
  useEffect(() => {
    if (data.demo) return
    let disposed = false
    void listImages().then(images => { if (!disposed) onChange(images) }).catch(() => { if (!disposed) setError('Images could not be loaded. Use Refresh to try again.') })
    return () => { disposed = true }
  }, [data.demo, onChange])
  const source = data.images.length ? data.images : data.demo ? imageTiles.map(([name], index) => ({ id: `demo-${index}`, name, url: '', mime: 'image/png', size: 0, modifiedAt: 'Demo preview' })) : []
  const tiles = source.filter(asset => asset.name.toLowerCase().includes(query.toLowerCase())).map((asset, index) => ({ ...asset, color: imageTiles[index % imageTiles.length][1] }))
  const upload = (files: File[]) => { setBusy(true); setError(''); void importImages(files).then(uploaded => onChange([...uploaded, ...data.images])).catch(() => setError('Image import failed. Check the file format and local service.')).finally(() => setBusy(false)) }
  const refresh = () => { setBusy(true); setError(''); void listImages().then(onChange).catch(() => setError('Images could not be loaded. Use Refresh to try again.')).finally(() => setBusy(false)) }
  const remove = (id: string) => { if (id.startsWith('demo-')) return; void deleteImage(id).then(() => onChange(data.images.filter(image => image.id !== id))).catch(() => setError('Image deletion failed. Refresh the library before retrying.')) }
  return <div className="page"><PageHeader eyebrow="Assets" title="Image library" description="Browse generated images and workspace previews kept on this device." action={<><input ref={fileInput} className="visually-hidden" type="file" accept="image/*" multiple onChange={event => event.target.files && upload([...event.target.files])} /><button className="button primary" onClick={() => fileInput.current?.click()} disabled={busy}><Plus size={15} />{busy ? 'Working…' : 'Import images'}</button></>} /><div className="library-toolbar"><label className="search-field"><Search size={15} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search images" aria-label="Search images" /></label><button className="button" onClick={refresh} disabled={busy}><RefreshCw size={14} className={busy ? 'spin' : ''} />Refresh</button><button className="button" disabled title="Grid is the only available layout"><LayoutGrid size={14} />Grid</button></div>{error && <p role="alert">{error}</p>}<div className="image-grid">{tiles.map((asset, index) => <article className="image-card" key={asset.id}><div className={`generated-art ${asset.color}`}>{asset.url ? <InlineImages images={[{ url: asset.url, alt: asset.name }]} /> : <><div className="art-orbit" /><div className="art-core"><Image size={27} /></div><span>{index + 1}</span></>}</div><div><h3>{asset.name}</h3><p>{asset.size ? `${Math.round(asset.size / 1024)} KB · ${asset.modifiedAt}` : asset.modifiedAt}</p></div><button aria-label={`Delete ${asset.name}`} onClick={() => remove(asset.id)} disabled={asset.id.startsWith('demo-')}><Trash2 size={16} /></button></article>)}</div>{!tiles.length && !error && <div className="empty-state image-empty"><Images size={28} /><p>No images match this search.</p></div>}</div>
}

function ProgressBar({ value }: { value: number | null }) { return <div className="progress"><span style={{ width: `${value ?? 0}%` }} /></div> }

function TokenCount({ value }: { value: number | null }) {
  const exactLabel = exactTokenCountLabel(value)
  return <strong title={exactLabel}><span aria-hidden="true">{formatTokenCount(value)}</span><span className="visually-hidden">{exactLabel}</span></strong>
}

function SettingsPage({ data, connection }: { data: BootstrapPayload; connection: ConnectionState }) {
  const [updating, setUpdating] = useState(false)
  const update = () => { setUpdating(true); void requestUpdate().catch(() => undefined).finally(() => window.setTimeout(() => setUpdating(false), 800)) }
  const exportData = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `codex-webui-export-${new Date().toISOString().slice(0, 10)}.json`; anchor.click()
    URL.revokeObjectURL(url)
  }
  const localCompanion = data.runtime === 'localhost-companion'
  return <div className="page settings-page"><PageHeader eyebrow="Local service" title="Settings" description="Manage Codex, usage visibility, storage, and app updates." /><section className="settings-section"><h3>Account & connection</h3><div className="settings-card account-card"><div className="avatar large"><UserRound size={22} /></div><div><strong>Local Codex user</strong><span>Authenticated through Codex CLI</span></div><ConnectionPill state={connection} /><button className="button" onClick={() => location.reload()}>Reconnect</button></div></section><section className="settings-section"><h3>Usage & limits {data.demo && <em className="demo-label">Demo values</em>}</h3><div className="usage-grid"><article><header><span>Primary limit</span><strong>{data.usage.fiveHourPercent === null ? 'Unavailable' : `${data.usage.fiveHourPercent}%`}</strong></header><ProgressBar value={data.usage.fiveHourPercent} /><p>Resets: {data.usage.resetsAt}</p></article><article><header><span>Secondary limit</span><strong>{data.usage.weeklyPercent === null ? 'Unavailable' : `${data.usage.weeklyPercent}%`}</strong></header><ProgressBar value={data.usage.weeklyPercent} /><p>Reported by Codex CLI</p></article><article className="token-card"><div><span>Lifetime tokens</span><TokenCount value={data.usage.lifetimeTokens} /></div><div><span>Peak daily</span><TokenCount value={data.usage.peakDailyTokens} /></div><div><span>Current streak</span><strong>{data.usage.currentStreakDays === null ? 'Unavailable' : `${data.usage.currentStreakDays}d`}</strong></div></article></div><p className="settings-hint"><AlertCircle size={13} />Limit availability depends on the data exposed by your installed Codex CLI.</p></section><section className="settings-section"><h3>Runtime</h3><div className="settings-list"><div><span className="settings-icon"><Box size={16} /></span><span><strong>Codex Web UI</strong><small>{localCompanion ? 'Loopback Mac companion · host toolchain' : data.updatesEnabled ? 'Container image · constrained updater configured' : 'Container image · update with tools/update.sh'}</small></span><button className="button" onClick={update} disabled={updating || !data.updatesEnabled} title={data.updatesEnabled ? 'Request a configured update' : 'Updates are managed from the local checkout'}><RefreshCw size={14} className={updating ? 'spin' : ''} />{updating ? 'Requesting…' : data.updatesEnabled ? 'Request update' : 'Checkout-managed'}</button></div><div><span className="settings-icon"><Terminal size={16} /></span><span><strong>Codex CLI</strong><small>{localCompanion ? 'Installed on this Mac · existing Codex login' : 'Bundled in container'}{data.codexVersion ? ` · ${data.codexVersion}` : ''}</small></span><button className="button" onClick={() => window.open('/api/health', '_blank', 'noopener,noreferrer')}>View diagnostics</button></div><div><span className="settings-icon"><Database size={16} /></span><span><strong>Current bootstrap</strong><small>Projects, indexed sessions, schedules, images, and usage</small></span><button className="button" onClick={exportData}><Download size={14} />Export JSON</button></div></div></section></div>
}

function actionForTurnSignal(signal: TurnSignal): TurnAction {
  if (signal.kind === 'started') return { type: 'started', turnId: signal.turnId }
  if (signal.kind === 'activity') return { type: 'activity', turnId: signal.turnId }
  if (signal.kind === 'delta') return { type: 'delta', turnId: signal.turnId }
  if (signal.kind === 'error') return { type: 'error', turnId: signal.turnId, message: signal.message, willRetry: signal.willRetry }
  return { type: 'completed', turnId: signal.turnId, status: signal.status, error: signal.error }
}

function conversationStatusForTurn(turn: TurnLifecycle): Conversation['status'] | null {
  if (isTurnActive(turn)) return 'running'
  if (turn.phase === 'failed') return 'failed'
  if (turn.phase === 'interrupted') return 'paused'
  if (turn.phase === 'completed') return 'ready'
  return null
}

export default function App() {
  const [data, setData] = useState<BootstrapPayload | null>(null)
  const [bootAttempt, setBootAttempt] = useState(0)
  const [bootError, setBootError] = useState('')
  const [historyAttempt, setHistoryAttempt] = useState(0)
  const [historyState, setHistoryState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [creationState, setCreationState] = useState<'idle' | 'loading' | 'error'>('idle')
  const creating = useRef(false)
  const choseConversation = useRef(false)
  const ready = data !== null
  const [connection, setConnection] = useState<ConnectionState>('connecting')
  const [view, setView] = useState<View>('chat')
  const [activeId, setActiveId] = useState('')
  const activeIdRef = useRef('')
  const activeModelRef = useRef('')
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [turn, setTurn] = useState<TurnLifecycle>(IDLE_TURN)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [realtimeSignal, setRealtimeSignal] = useState<RealtimeSignal | null>(null)
  const [voiceCapability, setVoiceCapability] = useState<RealtimeCapability>({ available: false, reason: 'Checking realtime voice support…' })
  const [leftOpen, setLeftOpen] = useState(() => !isNarrowLayout())
  const [rightOpen, setRightOpen] = useState(false)
  const [activeContextTool, setActiveContextTool] = useState<ContextToolId>(DEFAULT_CONTEXT_TOOL)

  useLayoutEffect(() => { activeIdRef.current = activeId }, [activeId])

  useEffect(() => {
    const controller = new AbortController()
    void loadBootstrap(controller.signal).then(result => {
      if (controller.signal.aborted) return
      const first = result.data.conversations[0]
      setData(result.data); setConnection(result.connection)
      activeModelRef.current = first?.model ?? result.data.models[0] ?? ''
      activeIdRef.current = first?.id ?? ''
      setActiveId(first?.id ?? '')
    }).catch(() => { if (!controller.signal.aborted) setBootError('The local workspace could not be opened. Check the service, then retry.') })
    return () => controller.abort()
  }, [bootAttempt])
  useEffect(() => {
    if (!ready) return
    const controller = new AbortController()
    void loadConversations(controller.signal).then(conversations => {
      if (controller.signal.aborted) return
      setData(current => {
        if (!current) return current
        const existing = new Set(current.conversations.map(chat => chat.id))
        const added = conversations.filter(chat => !existing.has(chat.id)).map(chat => ({ ...chat, projectId: chat.projectId || current.projects[0]?.id || '' }))
        const merged = [...current.conversations, ...added]
        return { ...current, conversations: merged, projects: current.projects.map(project => ({ ...project, chatCount: merged.filter(chat => chat.projectId === project.id).length })) }
      })
      if (!activeIdRef.current && !choseConversation.current && conversations[0]) {
        activeIdRef.current = conversations[0].id
        activeModelRef.current = conversations[0].model
        setActiveId(conversations[0].id)
      }
      setHistoryState('ready')
    }).catch(() => { if (!controller.signal.aborted) setHistoryState('error') })
    return () => controller.abort()
  }, [ready, historyAttempt])
  useEffect(() => {
    if (!ready) return
    const controller = new AbortController()
    void loadOptionalMetadata(controller.signal).then(metadata => {
      if (!controller.signal.aborted) setData(current => current ? { ...current, ...metadata } : current)
    })
    return () => controller.abort()
  }, [ready])
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia(narrowLayoutQuery)
    const closePanels = (event: MediaQueryListEvent) => {
      if (!event.matches) return
      setLeftOpen(false)
      setRightOpen(false)
    }
    media.addEventListener('change', closePanels)
    return () => media.removeEventListener('change', closePanels)
  }, [])
  useEffect(() => {
    if (!activeId) return
    let disposed = false
    let hydrating = true
    let hydrationVersion = 0
    let hydrationController: AbortController | null = null
    const queuedUpdates: LiveUpdate[] = []
    const setConversationStatus = (status: Conversation['status']) => setData(current => current ? {
      ...current,
      conversations: current.conversations.map(conversation => conversation.id === activeId ? { ...conversation, status } : conversation),
    } : current)
    const applyUpdate = (update: LiveUpdate) => {
      if (update.selectedModel) {
        activeModelRef.current = update.selectedModel
        setData(current => current ? { ...current, conversations: current.conversations.map(chat => chat.id === activeId ? { ...chat, model: update.selectedModel!, contextPercent: 0, contextUsedTokens: undefined, contextWindowTokens: undefined } : chat) } : current)
      }
      if (update.event) setEvents(current => stampAssistantMessageModel(mergeStreamEvent(current, update.event!), activeModelRef.current))
      if (update.contextUsedTokens !== undefined) setData(current => current ? { ...current, conversations: current.conversations.map(conversation => conversation.id === activeId ? { ...conversation, contextPercent: update.contextPercent ?? 0, contextUsedTokens: update.contextUsedTokens, contextWindowTokens: update.contextWindowTokens } : conversation) } : current)
      if (update.conversationTitle !== undefined) setData(current => current ? { ...current, conversations: current.conversations.map(conversation => conversation.id === activeId ? { ...conversation, title: update.conversationTitle! } : conversation) } : current)
      if (update.realtime) setRealtimeSignal(update.realtime)
      if (update.turn) {
        const signal = update.turn
        setTurn(current => reduceTurnLifecycle(current, actionForTurnSignal(signal)))
        if (signal.kind === 'completed') {
          setConversationStatus(signal.status === 'completed' ? 'ready' : signal.status === 'interrupted' ? 'paused' : 'failed')
          setEvents(current => settleStreamEvents(current, signal.status))
          if (signal.status === 'failed' && signal.error) {
            setEvents(current => mergeStreamEvent(current, { id: `turn-error-${signal.turnId}`, kind: 'status', title: 'Turn failed', content: signal.error!, timestamp: 'Now', state: 'failed' }))
          }
        } else {
          setConversationStatus('running')
        }
      }
    }
    const hydrate = async () => {
      hydrating = true
      const version = ++hydrationVersion
      hydrationController?.abort()
      hydrationController = new AbortController()
      queueMicrotask(() => { if (!disposed) setHistoryLoading(true) })
      const snapshot = await loadConversationSnapshot(activeId, data?.demo ?? false, hydrationController.signal)
      if (disposed || version !== hydrationVersion) return
      setEvents(stampAssistantMessageModel(snapshot.events, activeModelRef.current))
      setTurn(snapshot.turn)
      const status = conversationStatusForTurn(snapshot.turn)
      if (status) setConversationStatus(status)
      hydrating = false
      setHistoryLoading(false)
      queuedUpdates.splice(0).forEach(applyUpdate)
    }
    queueMicrotask(() => {
      if (disposed) return
      setEvents([])
      setHistoryLoading(true)
      setTurn(IDLE_TURN)
      setRealtimeSignal(null)
      setVoiceCapability({ available: false, reason: 'Checking realtime voice support…' })
    })
    void loadRealtimeCapability(activeId).then(capability => { if (!disposed) setVoiceCapability(capability) }).catch(() => {
      if (!disposed) setVoiceCapability({ available: false, reason: data?.realtimeVoiceReason ?? 'Realtime voice support could not be verified for this conversation.' })
    })
    void hydrate()
    const disconnect = connectConversation(activeId, update => {
      if (hydrating) queuedUpdates.push(update)
      else applyUpdate(update)
    }, setConnection, () => { void hydrate() })
    return () => { disposed = true; hydrationController?.abort(); disconnect() }
  }, [activeId, data?.demo, data?.realtimeVoiceReason])

  const changeImages = useCallback((images: BootstrapPayload['images']) => setData(current => current ? { ...current, images } : current), [])

  if (!data) return <div className="loading-screen"><div className="loading-mark"><Sparkles size={26} /></div>{bootError ? <><span role="alert">{bootError}</span><button className="button" onClick={() => { setBootError(''); setBootAttempt(current => current + 1) }}>Retry opening workspace</button></> : <><span>Opening local workspace</span><div className="loading-bar"><i /></div></>}</div>
  const activeConversation = data.conversations.find(chat => chat.id === activeId) ?? data.conversations[0]
  const activeProject = data.projects.find(project => project.id === activeConversation?.projectId)
  const openLeft = () => { if (isNarrowLayout()) setRightOpen(false); setLeftOpen(true) }
  const toggleLeft = () => { if (!leftOpen && isNarrowLayout()) setRightOpen(false); setLeftOpen(value => !value) }
  const openRight = () => { if (isNarrowLayout()) setLeftOpen(false); setRightOpen(true) }
  const showView = (next: View) => { setView(next); if (isNarrowLayout()) { setLeftOpen(false); setRightOpen(false) } }
  const selectConversation = (conversation: Conversation) => {
    choseConversation.current = true
    activeIdRef.current = conversation.id
    setData(current => current ? { ...current, conversations: current.conversations.some(item => item.id === conversation.id) ? current.conversations : [conversation, ...current.conversations] } : current)
    activeModelRef.current = conversation.model
    setActiveId(conversation.id)
    showView('chat')
  }
  const renameConversationTitle = async (conversationId: string, title: string) => {
    const previous = data.conversations.find(conversation => conversation.id === conversationId)?.title ?? 'Untitled conversation'
    setData(current => current ? { ...current, conversations: current.conversations.map(conversation => conversation.id === conversationId ? { ...conversation, title } : conversation) } : current)
    try {
      await renameConversation(conversationId, title)
    } catch (error) {
      setData(current => current ? { ...current, conversations: current.conversations.map(conversation => conversation.id === conversationId && conversation.title === title ? { ...conversation, title: previous } : conversation) } : current)
      throw error
    }
  }
  const newChat = () => {
    if (creating.current) return
    choseConversation.current = true
    creating.current = true
    setCreationState('loading')
    void createConversation({ projectId: activeProject?.id, cwd: activeProject?.path !== '.' ? activeProject?.path : activeConversation?.cwd, model: data.models[0] }).then(conversation => {
      setData(current => current ? { ...current, conversations: [conversation, ...current.conversations.filter(chat => chat.id !== conversation.id)] } : current)
      activeModelRef.current = conversation.model
      activeIdRef.current = conversation.id
      setActiveId(conversation.id)
      setCreationState('idle')
    }).catch(() => { setCreationState('error') }).finally(() => { creating.current = false })
    showView('chat')
  }
  return <div className={`app-shell ${leftOpen ? 'left-open' : 'left-closed'} ${rightOpen ? 'right-open' : 'right-closed'}`}>
    {!leftOpen && view !== 'chat' && <button className="global-menu icon-button" aria-label="Expand conversations" onClick={openLeft}><Menu size={20} /></button>}
    {leftOpen && <ChatSidebar view={view} setView={showView} data={data} activeId={activeId} onSelect={selectConversation} onClose={() => setLeftOpen(false)} onNewChat={newChat} historyState={historyState} onRetryHistory={() => { setHistoryState('loading'); setHistoryAttempt(current => current + 1) }} />}
    <div className="mobile-scrim left" onClick={() => setLeftOpen(false)} />
    <div className="content-area">
      {creationState === 'error' && <p className="creation-notice" role="alert">Conversation could not be created. Check the local Codex service. <button className="button" onClick={newChat}>Retry</button></p>}
      {creationState === 'loading' && <p className="creation-notice" role="status">Creating conversation…</p>}
      {view === 'chat' && activeConversation && <ChatSurface key={activeConversation.id} conversation={activeConversation} project={activeProject} projects={data.projects} models={data.models} events={events} turn={turn} historyLoading={historyLoading} connection={connection} realtimeSignal={realtimeSignal} voiceCapability={voiceCapability} setEvents={setEvents} onTurnAction={action => { if (activeIdRef.current === activeConversation.id) setTurn(current => reduceTurnLifecycle(current, action)) }} onConversationStatus={status => setData(current => current ? { ...current, conversations: current.conversations.map(chat => chat.id === activeConversation.id ? { ...chat, status } : chat) } : current)} onTurnModel={model => { activeModelRef.current = model }} onAssignProject={projectId => { const previous = activeConversation.projectId; setData(current => current ? { ...current, conversations: current.conversations.map(chat => chat.id === activeConversation.id ? { ...chat, projectId } : chat) } : current); void assignConversationProject(activeConversation.id, projectId).catch(() => setData(current => current ? { ...current, conversations: current.conversations.map(chat => chat.id === activeConversation.id ? { ...chat, projectId: previous } : chat) } : current)) }} onRename={title => renameConversationTitle(activeConversation.id, title)} leftOpen={leftOpen} toggleLeft={toggleLeft} openRight={openRight} />}
      {view === 'chat' && !activeConversation && <main className="chat-surface"><header className="chat-header"><IconButton label="Expand conversations" onClick={openLeft}><Menu size={20} /></IconButton><span>Codex 2</span><ConnectionPill state={connection} /></header><section className="chat-welcome"><span className="welcome-mark"><Sparkles size={32} /></span><h1>What are we building?</h1><p>Start a conversation in your local workspace.</p><button className="button primary start-chat" disabled={creationState === 'loading'} onClick={newChat}><Edit3 size={17} />New chat</button></section></main>}
      {view === 'projects' && <ProjectsPage projects={data.projects} conversations={data.conversations} onAdd={project => setData(current => current ? { ...current, projects: [...current.projects, project] } : current)} />}
      {view === 'schedules' && <SchedulesPage schedules={data.schedules} onAdd={schedule => setData(current => current ? { ...current, schedules: [schedule, ...current.schedules] } : current)} onUpdate={schedule => setData(current => current ? { ...current, schedules: current.schedules.map(item => item.id === schedule.id ? schedule : item) } : current)} />}
      {view === 'images' && <ImagesPage data={data} onChange={changeImages} />}
      {view === 'settings' && <SettingsPage data={data} connection={connection} />}
    </div>
    {rightOpen && <ContextPanel files={data.files} demo={data.demo} events={events} conversations={data.conversations} currentConversation={activeConversation} activeTool={activeContextTool} onToolChange={setActiveContextTool} onSelectConversation={selectConversation} onClose={() => setRightOpen(false)} />}
    <div className="mobile-scrim right" onClick={() => setRightOpen(false)} />
  </div>
}
