import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowUp, BookOpen, Box, FileText, Mic, MicOff, Puzzle, Sparkles } from 'lucide-react'
import { loadMentionFiles, loadMentions, type ChatExecution } from './api'
import { mentionQuery, mentionSuggestions, retainedMentions } from './mentions'
import { ContextIndicator } from './ContextIndicator'
import type { Conversation, Mention, VoiceState } from './types'
import { PermissionsButton } from './PermissionsButton'
import { ExecutionButton } from './ExecutionButton'

interface ComposerProps {
  conversation: Conversation
  cwd: string
  threadId: string
  onSend: (prompt: string, mentions: string[]) => Promise<boolean>
  busy: boolean
  voiceEnabled: boolean
  voiceState: VoiceState
  voiceMessage: string
  onVoiceToggle: () => void
  onPermissionsChanging: (changing: boolean) => void
  lastModel?: string
  lastEffort?: string
  manualExecution: boolean
  permissionsBusy: boolean
  onExecutionSelection: (choice: ChatExecution) => void
}

export function Composer({ conversation, cwd, threadId, onSend, busy, voiceEnabled, voiceState, voiceMessage, onVoiceToggle, onPermissionsChanging, permissionsBusy, onExecutionSelection, manualExecution, lastModel, lastEffort }: ComposerProps) {
  const [value, setValue] = useState('')
  const [caret, setCaret] = useState(0)
  const [entries, setEntries] = useState<Mention[]>([])
  const [catalogErrors, setCatalogErrors] = useState<string[]>([])
  const [fileSearch, setFileSearch] = useState<{ query: string; entries: Mention[]; error?: string; loading?: boolean }>({ query: '', entries: [] })
  const [catalogState, setCatalogState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [attempt, setAttempt] = useState(0)
  const [selected, setSelected] = useState<Mention[]>([])
  const [option, setOption] = useState(0)
  const [dismissed, setDismissed] = useState(false)
  const sending = useRef(false)
  const draft = useRef(value)
  useLayoutEffect(() => { draft.current = value }, [value])
  const textarea = useRef<HTMLTextAreaElement>(null)
  const insertionCaret = useRef<number | null>(null)
  const menu = useRef<HTMLDivElement>(null)
  const mention = dismissed ? null : mentionQuery(value, caret)
  const query = mention?.query ?? ''
  const fileEntries = fileSearch.query === query ? fileSearch.entries : []
  const suggestions = mention ? mentionSuggestions([...entries, ...fileEntries], query) : []
  const retained = retainedMentions(value, selected)
  const retainedIds = retained.map(entry => entry.id)
  const activeOption = Math.min(option, Math.max(0, suggestions.length - 1))

  useEffect(() => {
    const controller = new AbortController()
    void loadMentions(cwd, threadId, controller.signal).then(result => {
      if (controller.signal.aborted) return
      setEntries(result.entries); setCatalogErrors(result.errors); setCatalogState('ready')
    }).catch(() => { if (!controller.signal.aborted) setCatalogState('error') })
    return () => controller.abort()
  }, [cwd, threadId, attempt])
  useEffect(() => {
    if (!query || query.length > 200) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setFileSearch({ query, entries: [], loading: true })
      void loadMentionFiles(cwd, query, controller.signal).then(result => {
        if (!controller.signal.aborted) setFileSearch({ query, entries: result })
      }).catch(() => {
        if (!controller.signal.aborted) setFileSearch({ query, entries: [], error: 'Files could not be searched.' })
      })
    }, 200)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [cwd, query, attempt])
  useLayoutEffect(() => {
    const element = textarea.current
    if (element) {
      element.style.height = 'auto'; element.style.height = `${Math.min(180, element.scrollHeight)}px`
      if (insertionCaret.current !== null) {
        element.focus(); element.setSelectionRange(insertionCaret.current, insertionCaret.current)
        insertionCaret.current = null
      }
    }
  }, [value])
  useLayoutEffect(() => {
    if (!mention) return
    const container = menu.current
    const selected = container?.querySelector('[aria-selected="true"]')
    if (!container || !selected) return
    const bounds = container.getBoundingClientRect(), item = selected.getBoundingClientRect()
    if (item.bottom > bounds.bottom) container.scrollTop += item.bottom - bounds.bottom + 6
    else if (item.top < bounds.top) container.scrollTop -= bounds.top - item.top + 6
  }, [activeOption, mention, suggestions.length])

  const choose = (entry: Mention) => {
    if (!mention) return
    const retained = retainedMentions(value, selected)
    if (!retained.some(item => item.id === entry.id) && retained.length >= 8) return
    const inserted = `${entry.insertText} `
    const next = value.slice(0, mention.start) + inserted + value.slice(mention.end)
    const nextCaret = mention.start + inserted.length
    insertionCaret.current = nextCaret
    setValue(next); setCaret(nextCaret); setDismissed(true)
    setSelected(retained.some(item => item.id === entry.id) ? retained : [...retained, entry])
  }
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!value.trim() || busy || permissionsBusy || sending.current) return
    sending.current = true
    const submitted = value
    try {
      if (await onSend(submitted, retainedMentions(submitted, selected).map(entry => entry.id))) {
        if (draft.current === submitted) { setValue(''); setSelected([]) }
      }
    } finally { sending.current = false }
  }
  const voiceActive = voiceState === 'live' || voiceState === 'connecting'
  const voiceLabel = voiceActive ? 'Stop realtime voice' : voiceEnabled ? 'Start realtime voice' : voiceMessage || 'Realtime voice unavailable'
  return <div className="composer-wrap">
    <form className="composer" onSubmit={event => void submit(event)}>
      {mention && <div className="plugin-suggestions" ref={menu}>
        <div className="plugin-menu-title"><Sparkles size={14} />Add to your message{retainedIds.length >= 8 && <span> · 8 selected (maximum)</span>}</div>
        {catalogState === 'loading' && <p>Loading skills, plugins and apps…</p>}
        {catalogState === 'error' && <p>Mentions could not be loaded. <button type="button" onClick={() => { setCatalogState('loading'); setAttempt(current => current + 1) }}>Retry</button></p>}
        {catalogState === 'ready' && !suggestions.length && <p>No matching mentions. Type a name or file path.</p>}
        {catalogState === 'ready' && catalogErrors.length > 0 && <p className="mention-error" role="status">{catalogErrors.join(' ')} <button type="button" onClick={() => setAttempt(current => current + 1)}>Retry</button></p>}
        {fileSearch.query === query && fileSearch.loading && <p>Searching files…</p>}
        {fileSearch.query === query && fileSearch.error && <p>{fileSearch.error} <button type="button" onClick={() => setAttempt(current => current + 1)}>Retry</button></p>}
        <div className="plugin-options" id="plugin-suggestions" role="listbox" aria-label="Skills, plugins, apps and files">{suggestions.map((entry, index) => { const Icon = { skill: BookOpen, plugin: Puzzle, app: Box, file: FileText }[entry.kind]; return <button type="button" tabIndex={-1} role="option" id={`plugin-option-${index}`} aria-selected={index === activeOption} disabled={retainedIds.length >= 8 && !retainedIds.includes(entry.id)} key={entry.id} onPointerDown={event => event.preventDefault()} onClick={() => choose(entry)}><Icon size={18} /><span><strong>{entry.displayName}</strong><small>{entry.kind} · {entry.insertText}{entry.description ? ` · ${entry.description}` : ''}</small></span></button> })}</div>
      </div>}
      <textarea ref={textarea} value={value} role="combobox" aria-autocomplete="list" aria-expanded={Boolean(mention)} aria-controls="plugin-suggestions" aria-activedescendant={mention && suggestions.length ? `plugin-option-${activeOption}` : undefined} onChange={event => { setValue(event.target.value); setSelected(retainedMentions(event.target.value, selected)); setCaret(event.target.selectionStart); setOption(0); setDismissed(false) }} onSelect={event => setCaret(event.currentTarget.selectionStart)} onBlur={event => { if (!(event.relatedTarget instanceof Element) || !event.relatedTarget.closest('.plugin-suggestions')) setDismissed(true) }} onFocus={() => setDismissed(false)} onKeyDown={event => {
        if (event.nativeEvent.isComposing) return
        if (mention && event.key === 'Escape') { event.preventDefault(); setDismissed(true); return }
        if (mention && suggestions.length && !event.shiftKey && ['ArrowDown', 'ArrowUp', 'Enter', 'Tab'].includes(event.key)) {
          if (event.key === 'Tab' && retainedIds.length >= 8 && !retainedIds.includes(suggestions[activeOption].id)) { setDismissed(true); return }
          event.preventDefault()
          if (event.key === 'ArrowDown') setOption((activeOption + 1) % suggestions.length)
          else if (event.key === 'ArrowUp') setOption((activeOption + suggestions.length - 1) % suggestions.length)
          else choose(suggestions[activeOption])
          return
        }
        if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() }
      }} placeholder="Ask anything · @ for skills, apps and files" aria-label="Message Codex" rows={1} />
      <div className="composer-tools"><div className="composer-options"><PermissionsButton threadId={threadId} disabled={busy || permissionsBusy} onChanging={onPermissionsChanging} /></div><div className="send-cluster"><ContextIndicator conversation={conversation} />{lastModel && <span className="composer-last-model" title={`Last turn model: ${lastModel} · Reasoning effort: ${lastEffort ?? 'unknown'}`}><Sparkles size={12} />{lastModel.replace('gpt-', '')}<small>· {lastEffort ?? 'unknown'}</small></span>}<ExecutionButton onSelection={onExecutionSelection} threadId={threadId} disabled={busy || permissionsBusy} onChanging={onPermissionsChanging} /><button type="button" className={`icon-button ${voiceActive ? 'active' : ''}`} aria-label={voiceLabel} title={voiceLabel} disabled={permissionsBusy || voiceState === 'stopping' || (!voiceActive && (!voiceEnabled || busy))} onClick={onVoiceToggle}>{voiceActive ? <MicOff size={18} /> : <Mic size={18} />}</button><button type="submit" className="send-button" disabled={!value.trim() || busy || permissionsBusy} aria-label="Send message"><ArrowUp size={20} /></button></div></div>
    </form>
    <p className={`composer-note voice-${voiceState}`} role={voiceState === 'error' ? 'alert' : undefined}>{voiceState === 'connecting' ? 'Connecting voice…' : voiceState === 'live' ? 'Voice is live' : voiceState === 'error' ? voiceMessage : manualExecution ? 'Using your selected model and reasoning effort for this chat.' : 'Jev chooses the model and reasoning for each message.'}</p>
  </div>
}
