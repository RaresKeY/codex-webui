import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowUp, Mic, MicOff, Puzzle, Sparkles } from 'lucide-react'
import { loadPlugins } from './api'
import { mentionedPluginIds, pluginQuery } from './plugin-mentions'
import type { Plugin, VoiceState } from './types'

interface ComposerProps {
  cwd: string
  onSend: (prompt: string, plugins: string[]) => Promise<boolean>
  busy: boolean
  voiceEnabled: boolean
  voiceState: VoiceState
  voiceMessage: string
  onVoiceToggle: () => void
}

export function Composer({ cwd, onSend, busy, voiceEnabled, voiceState, voiceMessage, onVoiceToggle }: ComposerProps) {
  const [value, setValue] = useState('')
  const [caret, setCaret] = useState(0)
  const [plugins, setPlugins] = useState<Plugin[]>([])
  const [pluginState, setPluginState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [attempt, setAttempt] = useState(0)
  const [selected, setSelected] = useState<string[]>([])
  const [option, setOption] = useState(0)
  const [dismissed, setDismissed] = useState(false)
  const sending = useRef(false)
  const draft = useRef(value)
  useLayoutEffect(() => { draft.current = value }, [value])
  const textarea = useRef<HTMLTextAreaElement>(null)
  const mention = dismissed ? null : pluginQuery(value, caret)
  const suggestions = mention ? plugins.filter(plugin => `${plugin.name} ${plugin.displayName}`.toLowerCase().includes(mention.query.toLowerCase())).slice(0, 8) : []
  const retainedIds = mentionedPluginIds(value, plugins, selected)
  const activeOption = Math.min(option, Math.max(0, suggestions.length - 1))

  useEffect(() => {
    const controller = new AbortController()
    void loadPlugins(cwd, controller.signal).then(result => {
      if (controller.signal.aborted) return
      setPlugins(result); setPluginState('ready')
    }).catch(() => { if (!controller.signal.aborted) setPluginState('error') })
    return () => controller.abort()
  }, [cwd, attempt])
  useLayoutEffect(() => {
    const element = textarea.current
    if (element) { element.style.height = 'auto'; element.style.height = `${Math.min(180, element.scrollHeight)}px` }
  }, [value])

  const choose = (plugin: Plugin) => {
    if (!mention) return
    const retained = mentionedPluginIds(value, plugins, selected)
    if (!retained.includes(plugin.id) && retained.length >= 8) return
    const inserted = `@${plugin.name} `
    const next = value.slice(0, mention.start) + inserted + value.slice(mention.end)
    const nextCaret = mention.start + inserted.length
    setValue(next); setCaret(nextCaret); setDismissed(true)
    setSelected(retained.includes(plugin.id) ? retained : [...retained, plugin.id])
    requestAnimationFrame(() => { textarea.current?.focus(); textarea.current?.setSelectionRange(nextCaret, nextCaret) })
  }
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!value.trim() || busy || sending.current) return
    sending.current = true
    const submitted = value
    try {
      if (await onSend(submitted, mentionedPluginIds(submitted, plugins, selected))) {
        if (draft.current === submitted) { setValue(''); setSelected([]) }
      }
    } finally { sending.current = false }
  }
  const voiceActive = voiceState === 'live' || voiceState === 'connecting'
  const voiceLabel = voiceActive ? 'Stop realtime voice' : voiceEnabled ? 'Start realtime voice' : voiceMessage || 'Realtime voice unavailable'
  return <div className="composer-wrap">
    <form className="composer" onSubmit={event => void submit(event)}>
      {mention && <div className="plugin-suggestions" >
        <div className="plugin-menu-title"><Puzzle size={14} />Plugins{retainedIds.length >= 8 && <span> · 8 selected (maximum)</span>}</div>
        {pluginState === 'loading' && <p>Loading installed plugins…</p>}
        {pluginState === 'error' && <p>Plugins could not be loaded. <button type="button" onClick={() => { setPluginState('loading'); setAttempt(current => current + 1) }}>Retry</button></p>}
        {pluginState === 'ready' && !suggestions.length && <p>No matching installed plugins.</p>}
        <div className="plugin-options" id="plugin-suggestions" role="listbox" aria-label="Installed plugins">{suggestions.map((plugin, index) => <button type="button" tabIndex={-1} role="option" id={`plugin-option-${index}`} aria-selected={index === activeOption} disabled={retainedIds.length >= 8 && !retainedIds.includes(plugin.id)} key={plugin.id} onPointerDown={event => event.preventDefault()} onClick={() => choose(plugin)}><Puzzle size={18} /><span><strong>{plugin.displayName}</strong><small>@{plugin.name}{plugin.description ? ` · ${plugin.description}` : ''}</small></span></button>)}</div>
      </div>}
      <textarea ref={textarea} value={value} role="combobox" aria-autocomplete="list" aria-expanded={Boolean(mention)} aria-controls="plugin-suggestions" aria-activedescendant={mention && suggestions.length ? `plugin-option-${activeOption}` : undefined} onChange={event => { setValue(event.target.value); setCaret(event.target.selectionStart); setOption(0); setDismissed(false) }} onSelect={event => setCaret(event.currentTarget.selectionStart)} onBlur={event => { if (!(event.relatedTarget instanceof Element) || !event.relatedTarget.closest('.plugin-suggestions')) setDismissed(true) }} onFocus={() => setDismissed(false)} onKeyDown={event => {
        if (event.nativeEvent.isComposing) return
        if (mention && event.key === 'Escape') { event.preventDefault(); setDismissed(true); return }
        if (mention && suggestions.length && !event.shiftKey && ['ArrowDown', 'ArrowUp', 'Enter', 'Tab'].includes(event.key)) {
          event.preventDefault()
          if (event.key === 'ArrowDown') setOption((activeOption + 1) % suggestions.length)
          else if (event.key === 'ArrowUp') setOption((activeOption + suggestions.length - 1) % suggestions.length)
          else choose(suggestions[activeOption])
          return
        }
        if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() }
      }} placeholder="Ask anything · @ for plugins" aria-label="Message Codex" rows={1} />
      <div className="composer-tools"><span className="auto-route-label"><Sparkles size={15} />Auto · Jev</span><div className="send-cluster"><button type="button" className={`icon-button ${voiceActive ? 'active' : ''}`} aria-label={voiceLabel} title={voiceLabel} disabled={voiceState === 'stopping' || (!voiceActive && (!voiceEnabled || busy))} onClick={onVoiceToggle}>{voiceActive ? <MicOff size={18} /> : <Mic size={18} />}</button><button type="submit" className="send-button" disabled={!value.trim() || busy} aria-label="Send message"><ArrowUp size={20} /></button></div></div>
    </form>
    <p className={`composer-note voice-${voiceState}`} role={voiceState === 'error' ? 'alert' : undefined}>{voiceState === 'connecting' ? 'Connecting voice…' : voiceState === 'live' ? 'Voice is live' : voiceState === 'error' ? voiceMessage : 'Jev chooses the model and reasoning for each message.'}</p>
  </div>
}
