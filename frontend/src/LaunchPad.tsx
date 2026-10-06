import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { ArrowUp, Menu, Plus } from 'lucide-react'
import { createConversation, renameConversation, sendPrompt, turnStartFailureMessage } from './api'
import { deriveConversationTitle } from './conversation-title'
import { ChatActivityMark } from './ChatActivityMark'
import type { Conversation, Project } from './types'

interface LaunchJob { id: string; prompt: string; title: string; projectId: string; stage: string; threadId?: string; error?: string }
export function LaunchPad({ visible, chats, projects, onCreated, onPrepared, onFailed, onSelect, onMenu, leftOpen, projectMode = false, selectedProjectId, projectControls, onSent }: { visible: boolean; chats: Conversation[]; projects: Project[]; onCreated: (chat: Conversation) => void; onPrepared: (id: string) => void; onFailed: (id: string) => void; onSelect: (chat: Conversation) => void; onMenu: () => void; leftOpen: boolean; projectMode?: boolean; selectedProjectId?: string; projectControls?: ReactNode; onSent: (id: string, model: string, effort: string) => void }) {
  const [draft, setDraft] = useState('')
  const draftRef = useRef('')
  const input = useRef<HTMLTextAreaElement>(null)
  useEffect(() => { if (visible) input.current?.focus() }, [visible])
  const [projectId, setProjectId] = useState('')
  const [jobs, setJobs] = useState<LaunchJob[]>([])
  const pending = useRef(0)
  const editDraft = (value: string) => { draftRef.current = value; setDraft(value) }
  const patch = (id: string, values: Partial<LaunchJob>) => setJobs(current => current.map(job => job.id === id ? { ...job, ...values } : job))
  const launch = (event: FormEvent) => {
    event.preventDefault()
    const prompt = draftRef.current
    if (!prompt.trim() || pending.current >= 10 || (projectMode && !selectedProjectId)) return
    const id = crypto.randomUUID(), title = deriveConversationTitle(prompt)
    const project = projects.find(item => item.id === (projectMode ? selectedProjectId : projectId))
    pending.current++
    editDraft('')
    setJobs(current => [{ id, prompt, title, projectId: project?.id ?? '', stage: 'Creating chat' }, ...current])
    input.current?.focus()
    void (async () => {
      let chat: Conversation | undefined
      try {
        chat = await createConversation({ projectId: project?.id, cwd: project?.path ?? '.' })
        onCreated({ ...chat, title, status: 'running', preview: prompt, updatedAtEpoch: Date.now(), updatedAt: 'Now' })
        patch(id, { threadId: chat.id, stage: 'Choosing model' })
        // A failed optional name update must not duplicate or block submission.
        void renameConversation(chat.id, title).catch(() => undefined)
        const result = await sendPrompt(chat.id, prompt, stage => patch(id, { stage: stage === 'routing' ? 'Choosing model' : stage === 'switching' ? 'Changing model' : 'Sending' }))
        onSent(chat.id, result.decision.model, result.decision.effort)
        onPrepared(chat.id)
        setJobs(current => current.filter(job => job.id !== id))
      } catch (error) {
        if (chat) { onFailed(chat.id); onPrepared(chat.id) }
        patch(id, { stage: 'Needs attention', error: turnStartFailureMessage(error).replaceAll('Your prompt is preserved above', 'Your prompt can be restored below') })
      } finally { pending.current-- }
    })()
  }
  const recent = chats.filter(chat => !projectMode || chat.projectId === selectedProjectId).sort((a, b) => (b.updatedAtEpoch ?? 0) - (a.updatedAtEpoch ?? 0)).slice(0, 10)
  const lastUsed = recent.find(chat => chat.lastTurnModel)
  const unseenJobs = jobs.filter(job => (!projectMode || job.projectId === selectedProjectId) && (!job.threadId || (job.error && !recent.some(chat => chat.id === job.threadId))))
  const selectedProject = projects.find(project => project.id === selectedProjectId)
  return <main className="launch-pad" hidden={!visible}>
    <header className="launch-header">{!leftOpen && <button type="button" className="icon-button" aria-label="Expand conversations" onClick={onMenu}><Menu size={20} /></button>}<span>Codex</span></header>
    <div className="launch-content">{projectControls}<section className="launch-prompt"><h1>{projectMode ? selectedProject?.name ?? 'Your projects' : 'Start something new'}</h1><p>{projectMode ? 'Start a chat in this project. Keep going while Codex works.' : 'Send a prompt. Keep moving while Codex works.'}</p><form className="composer launch-composer" onSubmit={launch}>
      <textarea ref={input} value={draft} onChange={event => editDraft(event.target.value)} aria-label="New chat prompt" placeholder="What would you like Codex to work on?" rows={3} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} />
      <div className="composer-tools"><label className="launch-project"><span>Workspace</span><select aria-label="New chat workspace" value={projectMode ? selectedProjectId ?? '' : projectId} disabled={projectMode} onChange={event => setProjectId(event.target.value)}><option value="">No project</option>{projects.map(project => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label><div className="send-cluster"><span className="launch-auto">Auto · Jev{lastUsed?.lastTurnModel && <small title={`Last turn model: ${lastUsed.lastTurnModel}`}>Last: {lastUsed.lastTurnModel.replace('gpt-', '')} · {lastUsed.lastTurnEffort ?? 'unknown'}</small>}</span><button type="submit" className="send-button" aria-label="Launch new chat" disabled={!draft.trim() || pending.current >= 10 || (projectMode && !selectedProject)}><ArrowUp size={20} /></button></div></div>
    </form></section>
    <section className="launch-recents" aria-label="Last 10 chats"><header><h2>Recent chats</h2><span>Last 10</span></header>
      {unseenJobs.map(job => <div className="launch-job" key={job.id}><div className="launch-row"><strong>{job.title}</strong><span className="launch-row-mark"><ChatActivityMark chat={{ status: job.error ? 'failed' : 'running' }} /></span><small>{job.stage}</small></div>{job.error && <p role="alert">{job.error}<button type="button" onClick={() => { editDraft(job.prompt); input.current?.focus() }}>Restore prompt</button><button type="button" onClick={() => setJobs(current => current.filter(item => item.id !== job.id))}>Dismiss</button></p>}</div>)}
      {recent.map(chat => { const job = jobs.find(item => item.threadId === chat.id); return <div key={chat.id} className="launch-job"><button type="button" className="launch-row" onClick={() => onSelect(chat)}><strong>{chat.title}</strong><span className="launch-row-mark"><ChatActivityMark chat={chat} /></span><small>{chat.lastTurnModel && <span className="recent-model" title={`Last turn: ${chat.lastTurnModel} · ${chat.lastTurnEffort ?? 'effort unknown'}`}>{chat.lastTurnModel.replace('gpt-', '')} · {chat.lastTurnEffort ?? 'unknown'}</span>}{job?.stage ?? (chat.status === 'running' ? 'Working' : chat.unread ? 'Finished' : chat.updatedAt)}</small></button>{job?.error && <p role="alert">{job.error}<button type="button" onClick={() => { editDraft(job.prompt); input.current?.focus() }}>Restore prompt</button><button type="button" onClick={() => setJobs(current => current.filter(item => item.id !== job.id))}>Dismiss</button></p>}</div> })}
      {!recent.length && !unseenJobs.length && <p className="launch-empty"><Plus size={16} />Your new chats will appear here.</p>}
    </section></div>
  </main>
}
