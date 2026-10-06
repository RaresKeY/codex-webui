import { useEffect, useRef, useState } from 'react'
import { Activity, ChevronRight, RefreshCw } from 'lucide-react'
import { loadJevTurn } from './api'
import { activityStatus, type JevActivity, type JevTurn, type JevChatState } from './jev-activity'
import './jev-activity.css'

function percentage(value: number | undefined) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1 ? `${(value * 100).toFixed(1)}%` : 'Unavailable'
}

function Probabilities({ title, values }: { title: string; values?: Record<string, number> }) {
  if (!values) return null
  return <section className="jev-probabilities"><h4>{title}</h4>{Object.entries(values).map(([label, value]) => <div key={label}><span>{label.replace('gpt-', '')}</span><progress max="1" value={value} aria-label={`${label} probability`} /><strong>{percentage(value)}</strong></div>)}</section>
}

function ActivityRecord({ item, selected }: { item: JevActivity; selected: boolean }) {
  const details = useRef<HTMLDetailsElement>(null)
  useEffect(() => { if (selected && details.current) { details.current.open = true; details.current.scrollIntoView({ block: 'nearest' }) } }, [selected])
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
  return <details ref={details} className="jev-record"><summary><span className="jev-record-copy"><strong>{decision?.model?.replace('gpt-', '') ?? 'Awaiting selection'}{decision?.effort && ` · ${decision.effort}`}</strong><span>{source}</span></span><span className={`jev-status ${item.status}`}>{activityStatus(item)}</span></summary>
    <div className="jev-record-details"><ol className="jev-process-flow" aria-label="Preparation stages">{(['routing', 'switching', 'sending'] as const).map((stage, index) => {
      const current = ['routing', 'switching', 'sending'].indexOf(item.stage)
      const status = index < current || item.status === 'submitted' ? 'complete' : index === current ? item.status === 'pending' ? 'active' : 'stopped' : 'waiting'
      return <li key={stage} data-state={status}><span>{index + 1}</span>{{ routing: item.source === 'manual' ? 'Manual selection' : 'Jev routing', switching: 'Apply model', sending: 'Submit turn' }[stage]}<small>{status}</small></li>
    })}</ol><dl><div><dt>Started</dt><dd>{new Date(item.started_at).toLocaleString()}</dd></div><div><dt>Preparation time</dt><dd>{item.duration_ms === null ? 'Pending' : `${(item.duration_ms / 1000).toFixed(2)} s`}</dd></div><div><dt>Policy</dt><dd>{decision?.policy ?? 'Unavailable'}</dd></div><div><dt>Last stage</dt><dd>{{ routing: 'Model selection', switching: 'Model acknowledgement', sending: 'Turn submission' }[item.stage]}</dd></div>
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
      <footer>{item.turn_id && <button type="button" className="button" disabled={busy} onClick={() => void checkTurn()}>{busy ? 'Checking…' : 'Check actual turn'}</button>}</footer>
    </div>
  </details>
}

export function JevContext({ threadId, state, selectedId, onLoad }: { threadId?: string; state: JevChatState; selectedId?: number; onLoad: (before?: number) => void }) {
  return <section className="jev-context" id="context-tool-jev" role="tabpanel" aria-label="Jev process">
    <div className="jev-context-heading"><h3>This chat’s Jev process</h3><button type="button" className="icon-button" aria-label="Reload Jev history" disabled={!threadId || state.loading} onClick={() => onLoad()}><RefreshCw size={15} /></button></div>
    <p className="jev-hint">Each run belongs to a turn. Updates arrive when Jev runs. Earlier turns have no reconstructed routing record; manual selections skip Jev.</p>
    {state.error && <p className="notice" role="alert">{state.error}</p>}
    {!state.items.length && !state.error && <p className="jev-empty" role="status"><Activity size={24} />{!threadId ? 'Open a chat to see its Jev process.' : state.loading ? 'Loading this chat’s Jev history…' : 'No Jev runs in this chat yet.'}</p>}
    <div className="jev-list">{state.items.map(item => <ActivityRecord key={item.id} item={item} selected={item.id === selectedId} />)}</div>
    {state.cursor !== null && <button type="button" className="button jev-more" disabled={state.loading} onClick={() => onLoad(state.cursor!)}>Load older runs</button>}
  </section>
}

export function JevTurnStep({ item, onOpen }: { item: JevActivity; onOpen: () => void }) {
  return <button type="button" className="jev-turn-step" onClick={onOpen} aria-label="Open this turn’s Jev process"><Activity size={14} /><strong>Jev</strong><span>{activityStatus(item)}{item.decision?.model && ` · ${item.decision.model.replace('gpt-', '')} · ${item.decision.effort}`}</span><span className="jev-step-details">Process <ChevronRight size={13} /></span></button>
}
