import { useEffect, useRef, useState } from 'react'
import { Activity, Menu, RefreshCw } from 'lucide-react'
import { loadJevActivity, loadJevTurn } from './api'
import { activityStatus, mergeActivity, type JevActivity, type JevTurn } from './jev-activity'
import type { Conversation } from './types'
import './jev-activity.css'

function percentage(value: number | undefined) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1 ? `${(value * 100).toFixed(1)}%` : 'Unavailable'
}

function Probabilities({ title, values }: { title: string; values?: Record<string, number> }) {
  if (!values) return null
  return <section className="jev-probabilities"><h4>{title}</h4>{Object.entries(values).map(([label, value]) => <div key={label}><span>{label.replace('gpt-', '')}</span><progress max="1" value={value} aria-label={`${label} probability`} /><strong>{percentage(value)}</strong></div>)}</section>
}

function ActivityRecord({ item, chat, onOpen }: { item: JevActivity; chat?: Conversation; onOpen: (id: string) => Promise<void> }) {
  const [turn, setTurn] = useState<JevTurn>()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])
  const checkTurn = async () => {
    if (busy) return
    const abort = new AbortController(); controller.current = abort
    setBusy(true); setError('')
    try { const value = await loadJevTurn(item.id, abort.signal); if (!abort.signal.aborted) setTurn(value) }
    catch { if (!abort.signal.aborted) setError('Turn status is unavailable. Check the chat or try again.') }
    finally { if (!abort.signal.aborted) setBusy(false) }
  }
  const decision = item.decision
  const source = { auto: 'Jev auto', manual: 'Manual selection', preview: 'Routing preview' }[item.source]
  return <details className="jev-record"><summary><span className="jev-record-copy"><strong>{decision?.model?.replace('gpt-', '') ?? 'Awaiting selection'}{decision?.effort && ` · ${decision.effort}`}</strong><span>{chat?.title ?? 'Conversation'} · {source}</span></span><span className={`jev-status ${item.status}`}>{activityStatus(item)}</span></summary>
    <div className="jev-record-details"><dl><div><dt>Started</dt><dd>{new Date(item.started_at).toLocaleString()}</dd></div><div><dt>Preparation time</dt><dd>{item.duration_ms === null ? 'Pending' : `${(item.duration_ms / 1000).toFixed(2)} s`}</dd></div><div><dt>Policy</dt><dd>{decision?.policy ?? 'Unavailable'}</dd></div><div><dt>Last stage</dt><dd>{{ routing: 'Model selection', switching: 'Model acknowledgement', sending: 'Turn submission' }[item.stage]}</dd></div>
      {item.source !== 'manual' && <><div><dt>Model confidence</dt><dd>{percentage(decision?.modelConfidence)}</dd></div><div><dt>Effort confidence</dt><dd>{percentage(decision?.effortConfidence)}</dd></div><div><dt>Jev input tokens</dt><dd>{decision?.usage?.input_tokens.toLocaleString() ?? 'Unavailable'}</dd></div><div><dt>Jev output tokens</dt><dd>{decision?.usage?.output_tokens.toLocaleString() ?? 'Unavailable'}</dd></div></>}
      <div><dt>Chat</dt><dd>{item.thread_id}</dd></div>{item.turn_id && <div><dt>Actual turn</dt><dd>{item.turn_id}</dd></div>}</dl>
      {item.source !== 'manual' && <section className="jev-preparation"><h4>Information needs</h4><dl>{([['online_search', 'Online search'], ['fresh_information', 'Up-to-date information'], ['project_context', 'Project context']] as const).map(([field, label]) => {
        const answer = decision?.preparation?.[field]
        return <div key={field}><dt>{label}</dt><dd>{answer ? { yes: 'Useful', no: 'Not needed', unclear: 'Unclear' }[answer.choice] : 'Unavailable'}{answer && ` · ${percentage(answer.confidence)} confidence`}</dd></div>
      })}</dl><p className="jev-hint">These answers are advisory. Search and project summaries are not prepared automatically yet.</p></section>}
      <div className="jev-distributions"><Probabilities title="Model probabilities" values={decision?.modelProbabilities} /><Probabilities title="Effort probabilities" values={decision?.effortProbabilities} /></div>
      {item.source !== 'manual' && decision && <p className="jev-hint">Confidence and probabilities are classifier estimates, not measured success rates.</p>}
      {turn && <p className="jev-turn-status" role="status">Actual turn: {{ inProgress: 'Running', completed: 'Completed', interrupted: 'Interrupted', failed: 'Failed', unknown: 'Status unavailable' }[turn.status]}</p>}
      {error && <p role="alert">{error}</p>}
      <footer>{item.turn_id && <button type="button" className="button" disabled={busy} onClick={() => void checkTurn()}>{busy ? 'Checking…' : 'Check actual turn'}</button>}<button type="button" className="button" onClick={() => { setError(''); void onOpen(item.thread_id).catch(() => setError('This chat could not be opened. Refresh and try again.')) }}>Open chat</button></footer>
    </div>
  </details>
}

export function JevActivityPage({ chats, onOpen, onMenu, leftOpen }: { chats: Conversation[]; onOpen: (id: string) => Promise<void>; onMenu: () => void; leftOpen: boolean }) {
  const [items, setItems] = useState<JevActivity[]>([])
  const [cursor, setCursor] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const busy = useRef(false)
  const loadedOlder = useRef(false)
  const refresh = useRef<(before?: number) => Promise<void>>(async () => {})
  useEffect(() => {
    const abort = new AbortController()
    refresh.current = async (before?: number) => {
      if (busy.current || abort.signal.aborted) return
      busy.current = true; setLoading(true)
      try {
        const result = await loadJevActivity(before, abort.signal)
        if (abort.signal.aborted) return
        if (before) loadedOlder.current = true
        setItems(current => mergeActivity(current, result.data))
        if (before || !loadedOlder.current) setCursor(result.nextCursor)
        setError('')
      } catch { if (!abort.signal.aborted) setError('Jev activity could not be loaded. Refresh to try again.') }
      finally { busy.current = false; if (!abort.signal.aborted) setLoading(false) }
    }
    void refresh.current()
    const timer = window.setInterval(() => { if (!document.hidden) void refresh.current() }, 5000)
    return () => { abort.abort(); window.clearInterval(timer) }
  }, [])
  return <main className="page jev-page"><header className="page-header"><div>{!leftOpen && <button type="button" className="icon-button" aria-label="Expand conversations" onClick={onMenu}><Menu size={20} /></button>}<span className="eyebrow">Routing</span><h2>Jev activity</h2><p>Model decisions and the Codex turns they started.</p></div><button type="button" className="button" disabled={loading} onClick={() => void refresh.current()}><RefreshCw size={14} className={loading ? 'spin' : ''} />Refresh</button></header>
    <div className="jev-content"><p className="jev-hint">Updates every 5 seconds. Records begin with this update; earlier turns have no routing record. Manual selections skip Jev.</p>
      {error && <p className="notice" role="alert">{error}</p>}
      {!items.length && !error && <p className="jev-empty" role="status"><Activity size={24} />{loading ? 'Loading activity…' : 'No routing activity yet. Send a message to see its decision here.'}</p>}
      <div className="jev-list">{items.map(item => <ActivityRecord key={item.id} item={item} chat={chats.find(chat => chat.id === item.thread_id)} onOpen={onOpen} />)}</div>
      {cursor !== null && <button type="button" className="button jev-more" disabled={loading} onClick={() => void refresh.current(cursor)}>Load older activity</button>}
    </div></main>
}
