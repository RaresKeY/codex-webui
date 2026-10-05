import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Check, Gauge } from 'lucide-react'
import { loadChatExecution, setChatExecution, type ChatExecution } from './api'

const models = [
  { model: 'auto', label: 'Auto · Jev', description: 'Choose model and effort for each message.' },
  { model: 'gpt-6-luna', label: 'GPT-6 Luna', description: 'Fast, everyday work.' },
  { model: 'gpt-6.1-sol', label: 'GPT-6.1 Sol', description: 'Complex work and deeper reasoning.' },
] as const
const efforts = ['low', 'medium', 'high', 'xhigh', 'max'] as const

export function ExecutionButton({ threadId, disabled, onChanging, onSelection }: { threadId: string; disabled: boolean; onChanging: (busy: boolean) => void; onSelection: (choice: ChatExecution) => void }) {
  const [choice, setChoice] = useState<ChatExecution | null>(null)
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const root = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const mounted = useRef(true)
  const changing = useRef(false)
  useEffect(() => {
    mounted.current = true
    const controller = new AbortController()
    void loadChatExecution(threadId, controller.signal).then(value => {
      if (!controller.signal.aborted) { setChoice(value); onSelection(value); setError('') }
    }).catch(() => { if (!controller.signal.aborted) setError('Model settings could not be loaded.') })
    return () => { mounted.current = false; controller.abort() }
  }, [threadId, attempt, onSelection])
  useLayoutEffect(() => {
    if (open && !saving && !disabled) root.current?.querySelector<HTMLButtonElement>('[aria-checked="true"]')?.focus()
  }, [open, saving, disabled])
  useEffect(() => {
    if (!open) return
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false) }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open])
  const close = () => { setOpen(false); trigger.current?.focus() }
  const choose = async (next: ChatExecution) => {
    if (disabled || changing.current) return
    changing.current = true; setSaving(true); setError(''); onChanging(true)
    try {
      const value = await setChatExecution(threadId, next)
      if (mounted.current) { setChoice(value); onSelection(value) }
    } catch (failure) {
      if (mounted.current) setError(failure instanceof Error ? failure.message : 'Model settings could not be applied.')
    } finally {
      changing.current = false
      if (mounted.current) { setSaving(false); onChanging(false) }
    }
  }
  const blocked = disabled || saving || !choice
  return <div className="execution-control" ref={root} onBlur={event => {
    if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget as Node)) setOpen(false)
  }}>
    <button type="button" className="permissions-trigger execution-trigger" ref={trigger} disabled={disabled || saving} aria-label={`Choose model and effort: ${choice?.model ?? 'Loading'}, ${choice?.effort ?? ''}`} aria-haspopup="menu" aria-expanded={open} aria-controls={`execution-${threadId}`} title="Choose model and reasoning effort for this chat" onClick={() => setOpen(value => !value)} onKeyDown={event => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); setOpen(true) }
    }}><Gauge size={21} /><span className="composer-control-label">{saving ? 'Applying…' : choice?.model === 'auto' ? 'Auto' : `${choice?.model === 'gpt-6-luna' ? 'Luna' : 'Sol'} · ${choice?.effort ?? ''}`}</span></button>
    {open && <div className="permissions-menu execution-menu" id={`execution-${threadId}`} role="menu" aria-label="Model and reasoning effort" aria-busy={saving} onKeyDown={event => {
      if (event.key === 'Escape') { event.preventDefault(); close(); return }
      if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
        event.preventDefault()
        const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="menuitemradio"]:not(:disabled)'))
        if (!buttons.length) return
        const index = buttons.indexOf(document.activeElement as HTMLButtonElement)
        buttons[event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowUp' ? -1 : 1) + buttons.length) % buttons.length].focus()
      }
    }}><div className="permissions-menu-heading">Model for this chat</div>
      {models.map(option => <button type="button" role="menuitemradio" aria-checked={choice?.model === option.model} disabled={blocked} key={option.model} onClick={() => void choose({ model: option.model, effort: choice?.effort ?? 'medium' })}><span><strong>{option.label}</strong><small>{option.description}</small></span><Check size={16} className={choice?.model === option.model ? '' : 'permission-check-hidden'} /></button>)}
      <div className="permissions-menu-heading">Reasoning effort {choice?.model === 'auto' && '· chosen automatically'}</div>
      <div className="effort-options" role="group" aria-label="Reasoning effort">{efforts.map(effort => <button type="button" role="menuitemradio" aria-checked={choice?.effort === effort && choice.model !== 'auto'} disabled={blocked || choice?.model === 'auto'} key={effort} onClick={() => choice && void choose({ ...choice, effort })}>{effort}</button>)}</div>
      {saving && <p role="status">Applying selection…</p>}
      {error && <p className="permissions-error" role="alert">{error} <button type="button" disabled={saving} onClick={() => setAttempt(value => value + 1)}>Refresh</button></p>}
    </div>}
  </div>
}
