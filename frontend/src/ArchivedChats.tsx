import { useEffect, useRef, useState } from 'react'
import { Archive, RefreshCw } from 'lucide-react'
import { loadArchivedConversations } from './api'
import { ConversationListItem } from './ConversationListItem'
import type { Conversation, Project } from './types'

export function ArchivedChats({ refresh, projects, onRestore, onDelete, onOpen }: { refresh: number; projects: Project[]; onRestore: (chat: Conversation) => Promise<Conversation>; onDelete: (chat: Conversation) => void; onOpen: (chat: Conversation) => void }) {
  const [chats, setChats] = useState<Conversation[]>([])
  const [cursor, setCursor] = useState<string>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const busy = useRef(false)
  const generation = useRef(0)
  const controller = useRef<AbortController | null>(null)
  useEffect(() => {
    const abort = new AbortController(); controller.current = abort
    generation.current++; busy.current = true; setLoading(true); setError('')
    void loadArchivedConversations(undefined, abort.signal).then(result => {
      if (abort.signal.aborted) return
      setChats(result.chats); setCursor(result.cursor)
    }).catch(() => { if (!abort.signal.aborted) setError('Archived chats could not be loaded. Reconnect and retry.') }).finally(() => { if (!abort.signal.aborted) { busy.current = false; setLoading(false) } })
    return () => abort.abort()
  }, [refresh, attempt])
  const more = async () => {
    if (!cursor || busy.current) return
    busy.current = true; setLoading(true); setError('')
    const epoch = generation.current
    try {
      const result = await loadArchivedConversations(cursor, controller.current?.signal)
      if (epoch !== generation.current || controller.current?.signal.aborted) return
      setChats(current => [...current, ...result.chats.filter(chat => !current.some(item => item.id === chat.id))]); setCursor(result.cursor)
    } catch { if (epoch === generation.current && !controller.current?.signal.aborted) setError('More archived chats could not be loaded. Retry.') }
    finally { if (epoch === generation.current) { busy.current = false; setLoading(false) } }
  }
  return <main className="page archived-page"><header className="page-header"><div><h2>Archived chats</h2><p>Restore a chat to continue, or permanently delete it.</p></div></header>
    {error && <p className="notice" role="alert">{error}<button type="button" className="button" onClick={() => setAttempt(value => value + 1)}>Retry</button></p>}
    <div className="archived-list">{chats.map(chat => <ConversationListItem key={chat.id} conversation={chat} project={projects.find(project => project.id === chat.projectId)} active={false} onSelect={() => { void onRestore(chat).then(onOpen).catch(() => setError('The chat could not be restored. Refresh and try again.')) }} onRestore={async () => { await onRestore(chat) }} onDelete={() => onDelete(chat)} />)}</div>
    {loading && <p className="archive-loading" role="status"><RefreshCw size={14} className="spin" />Loading archived chats…</p>}
    {!loading && !error && !chats.length && <p className="archive-empty"><Archive size={24} />No archived chats yet.</p>}
    {cursor && <button type="button" className="button" disabled={loading} onClick={() => void more()}>Load more</button>}
  </main>
}
