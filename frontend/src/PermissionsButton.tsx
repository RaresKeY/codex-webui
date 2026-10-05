import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Check, ChevronDown, ShieldCheck, ShieldOff } from 'lucide-react'
import { loadChatPermissions, setChatPermissions } from './api'
import type { PermissionMode } from './types'

const options: { mode: PermissionMode; short: string; label: string; description: string }[] = [
  { mode: 'default', short: 'Default', label: 'Default permissions', description: 'Use the workspace permissions and ask you when approval is needed.' },
  { mode: 'full-auto', short: 'Auto approve', label: 'Full access · Auto approve', description: 'Access files and network. Codex automatically reviews approval requests.' },
  { mode: 'yolo', short: 'YOLO', label: 'Full access · YOLO', description: 'Access files and network without approval prompts.' },
]

export function PermissionsButton({ threadId, disabled, onChanging }: { threadId: string; disabled: boolean; onChanging: (changing: boolean) => void }) {
  const [mode, setMode] = useState<PermissionMode | null>(null)
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const root = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const changing = useRef(false)
  const mounted = useRef(true)
  const menuId = `permissions-${threadId}`
  useEffect(() => {
    mounted.current = true
    const controller = new AbortController()
    void loadChatPermissions(threadId, controller.signal).then(value => {
      if (!controller.signal.aborted) { setMode(value); setError(''); setLoading(false) }
    }).catch(() => {
      if (!controller.signal.aborted) { setError('Permissions could not be loaded. Retry or choose a mode.'); setLoading(false) }
    })
    return () => { mounted.current = false; controller.abort() }
  }, [threadId, attempt])
  useLayoutEffect(() => {
    if (open) (root.current?.querySelector<HTMLButtonElement>('[aria-checked="true"]') ?? root.current?.querySelector<HTMLButtonElement>('[role="menuitemradio"]'))?.focus()
  }, [open, loading])
  useEffect(() => {
    if (!open) return
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false) }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open])
  const close = () => { setOpen(false); trigger.current?.focus() }
  const choose = async (next: PermissionMode) => {
    if (changing.current || disabled || loading) return
    changing.current = true
    setSaving(true); setError(''); onChanging(true)
    try {
      const acknowledged = await setChatPermissions(threadId, next)
      if (mounted.current) { setMode(acknowledged); close() }
    } catch (failure) {
      if (mounted.current) setError(failure instanceof Error ? failure.message : 'The permission change could not be confirmed.')
    } finally {
      changing.current = false
      if (mounted.current) { setSaving(false); onChanging(false) }
    }
  }
  const current = options.find(option => option.mode === mode)
  const Icon = mode === 'yolo' ? ShieldOff : ShieldCheck
  return <div className={`permissions-control mode-${mode ?? 'unknown'}`} ref={root} onBlur={event => {
    if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget as Node)) setOpen(false)
  }}>
    <button type="button" className="permissions-trigger" ref={trigger} aria-label={`Change permissions: ${current?.short ?? 'Permissions'}`} aria-haspopup="menu" aria-expanded={open} aria-controls={menuId} disabled={disabled || saving} title={disabled ? 'Wait for the current operation to finish before changing permissions' : 'Change permissions for this chat'} onClick={() => setOpen(value => !value)} onKeyDown={event => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); setOpen(true) }
    }}><Icon size={21} /><span className="composer-control-label">{saving ? 'Applying…' : current?.short ?? 'Permissions'}</span><ChevronDown className="composer-control-chevron" size={12} /></button>
    {open && <div className="permissions-menu" id={menuId} role="menu" aria-label="Chat permissions" aria-busy={saving || loading} onKeyDown={event => {
      if (event.key === 'Escape') { event.preventDefault(); close(); return }
      if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
        event.preventDefault()
        const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="menuitemradio"]:not(:disabled)'))
        if (!buttons.length) return
        const index = buttons.indexOf(document.activeElement as HTMLButtonElement)
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowUp' ? -1 : 1) + buttons.length) % buttons.length
        buttons[next].focus()
      }
    }}><div className="permissions-menu-heading">Permissions for this chat</div>
      {loading && <p role="status">Loading permissions…</p>}
      {options.map(option => <button type="button" role="menuitemradio" aria-checked={mode === option.mode} disabled={disabled || loading || saving} key={option.mode} onClick={() => void choose(option.mode)}><span><strong>{option.label}</strong><small>{option.description}</small></span><Check size={16} className={mode === option.mode ? '' : 'permission-check-hidden'} /></button>)}
      {saving && <p role="status">Applying permissions…</p>}
      {error && <p className="permissions-error" role="alert">{error} <button type="button" disabled={saving} onClick={() => { setLoading(true); setAttempt(value => value + 1) }}>Refresh</button></p>}
    </div>}
  </div>
}
