import './browser-chrome.css'
import { browserAddress } from './browser-address'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowLeft, ArrowUpRight, Globe, MousePointer2, RefreshCw, X } from 'lucide-react'

export interface BrowserState {
  available: boolean
  agentAvailable?: boolean
  open: boolean
  reason?: string
  url: string
  title: string
  frame?: string | null
  revision: number
  width: number
  height: number
  cursor?: { x: number; y: number; click: boolean } | null
}
export interface BrowserSignal extends BrowserState { threadId: string; action: string }

export function BrowserContext({ threadId, signal }: { threadId?: string; signal: BrowserSignal | null }) {
  const pageViewport = useRef<HTMLDivElement>(null)
  const receiveInput = useRef<(packet: Record<string, unknown>) => void>(() => undefined)
  const inputQueue = useRef<Record<string, unknown>[]>([])
  const inputRunning = useRef(false)
  const alive = useRef(true)
  const [control, setControl] = useState(true)
  const [typing, setTyping] = useState('')
  const generation = useRef(0)
  const actionController = useRef<AbortController | null>(null)
  const actionBusy = useRef(false)
  useEffect(() => { alive.current = true; return () => { alive.current = false; inputQueue.current = []; actionController.current?.abort() } }, [])
  const [state, setState] = useState<BrowserState | null>(null)
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [frameError, setFrameError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (!threadId) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    const refresh = async () => {
      const requestedGeneration = generation.current
      try {
        const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/browser`, { signal: controller.signal, cache: 'no-store' })
        if (!response.ok) throw new Error('Browser view unavailable. Try reopening the browser.')
        const next = await response.json() as BrowserState
        if (!controller.signal.aborted && requestedGeneration === generation.current) { setState(next); setFrameError('') }
      } catch (reason) {
        if (!controller.signal.aborted && requestedGeneration === generation.current) setFrameError(reason instanceof Error ? reason.message : 'Browser unavailable')
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(() => { void refresh() }, 650)
      }
    }
    void refresh()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [threadId])
  const act = async (action: string, targetUrl?: string) => {
    if (!threadId || actionBusy.current) return
    actionBusy.current = true; generation.current++
    const controller = new AbortController(); actionController.current = controller
    setBusy(true); setError('')
    try {
      const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/browser`, {
        signal: controller.signal, method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, ...(targetUrl ? { url: targetUrl } : {}) }),
      })
      if (!response.ok) throw new Error('Could not complete browser action. Check the HTTPS URL and local browser runtime.')
      const next = await response.json() as BrowserState
      if (!controller.signal.aborted) { generation.current++; setState(next); setUrl(null) }
    } catch (reason) { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Browser action failed') }
    finally { actionBusy.current = false; if (!controller.signal.aborted) setBusy(false) }
  }
  const input = (packet: Record<string, unknown>) => {
    if (!threadId || !state?.open || !control || (actionBusy.current && !inputRunning.current)) return
    if (inputQueue.current.length >= 100) { setError('Input is still catching up. Wait before typing more.'); return }
    inputQueue.current.push(packet)
    if (inputRunning.current) return
    inputRunning.current = true; actionBusy.current = true; setBusy(true); setError('')
    const controller = new AbortController(); actionController.current = controller
    void (async () => {
      try {
        while (inputQueue.current.length && alive.current && !controller.signal.aborted) {
          const nextInput = inputQueue.current.shift()!
          while (nextInput.action === 'text' && inputQueue.current[0]?.action === 'text' && String(nextInput.text).length + String(inputQueue.current[0].text).length <= 2000) nextInput.text = String(nextInput.text) + String(inputQueue.current.shift()!.text)
          generation.current++
          const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/browser/input`, { signal: controller.signal, method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(nextInput) })
          if (!response.ok) throw new Error('Browser input failed. Click the page again after refreshing.')
          const next = await response.json() as BrowserState
          if (!controller.signal.aborted) { generation.current++; setState(next) }
        }
      } catch (reason) {
        inputQueue.current = []
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Browser input failed')
      } finally { inputRunning.current = false; actionBusy.current = false; if (alive.current) setBusy(false) }
    })()
  }
  const coordinates = (element: HTMLElement, clientX: number, clientY: number) => {
    const rect = element.getBoundingClientRect()
    return { x: Math.max(0, Math.min(1279, (clientX - rect.left) / rect.width * 1280)), y: Math.max(0, Math.min(899, (clientY - rect.top) / rect.height * 900)) }
  }
  receiveInput.current = input
  const hasFrame = Boolean(state?.open && state.frame)
  useEffect(() => {
    const page = pageViewport.current
    if (!page || !control || !hasFrame) return
    const wheel = (event: WheelEvent) => {
      event.preventDefault()
      const rect = page.getBoundingClientRect()
      receiveInput.current({ action: 'scroll', x: Math.max(0, Math.min(1279, (event.clientX - rect.left) / rect.width * 1280)), y: Math.max(0, Math.min(899, (event.clientY - rect.top) / rect.height * 900)), delta: Math.max(-1800, Math.min(1800, event.deltaY)) })
    }
    page.addEventListener('wheel', wheel, { passive: false })
    return () => page.removeEventListener('wheel', wheel)
  }, [control, hasFrame])
  const navigate = (event: FormEvent) => { event.preventDefault(); const address = browserAddress(url ?? ''); if (address) void act('open', address); else setError('Enter a valid website address.') }
  const currentSignal = signal?.threadId === threadId ? signal : null
  const cursor = currentSignal && currentSignal.revision >= (state?.revision ?? 0) ? currentSignal.cursor : state?.cursor
  const title = state?.title || 'New tab'
  return <section className="browser-context" id="context-tool-browser" role="tabpanel" aria-label="Browser">
    <div className="browser-tab-strip"><div className="browser-tab"><Globe size={13} /><span title={title}>{title}</span><button type="button" aria-label="Close browser session" disabled={!state?.open || busy} onClick={() => { void act('close') }}><X size={13} /></button></div><button type="button" className="browser-control-toggle" aria-pressed={control} title="Enable direct page control" onClick={() => { setControl(value => !value); inputQueue.current = [] }}>{control ? 'Control on' : 'View only'}</button></div>
    <form className="browser-toolbar" onSubmit={navigate}>
      <div className="browser-navigation"><button type="button" aria-label="Browser back" disabled={!state?.open || busy} onClick={() => { void act('back') }}><ArrowLeft size={16} /></button>
      <button type="button" aria-label="Reload browser page" disabled={!state?.open || busy} onClick={() => { void act('reload') }}><RefreshCw size={16} className={busy ? 'spin' : ''} /></button></div>
      <div className="browser-address-bar"><input aria-label="Browser address" type="text" inputMode="url" autoCapitalize="none" autoCorrect="off" spellCheck={false} placeholder="Enter a website or URL" value={url ?? state?.url ?? ''} onChange={event => setUrl(event.target.value)} disabled={state?.available === false || busy} />
      <button type="submit" aria-label="Open website" title="Open website" disabled={!url?.trim() || busy || !state?.available}><ArrowUpRight size={16} /></button></div>
    </form>
    {(error || frameError) && <div className="browser-error" role="alert">{error || frameError}</div>}
    <div className="browser-page">
      {state?.open && state.frame ? <div ref={pageViewport} className={`browser-viewport ${control ? 'interactive' : ''}`} tabIndex={control ? 0 : undefined} role={control ? 'application' : undefined} aria-label="Browser page control" title="Click to control the page; type, paste or scroll. Escape releases keyboard focus." onClick={event => { if (control) { event.currentTarget.focus(); input({ action: 'click', ...coordinates(event.currentTarget, event.clientX, event.clientY) }) } }} onPaste={event => { if (control) { event.preventDefault(); input({ action: 'text', text: event.clipboardData.getData('text').slice(0, 2000) }) } }} onKeyDown={event => {
          if (!control || event.nativeEvent.isComposing) return
          const keys = ['Enter','Tab','Backspace','Delete','Escape','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End']
          if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') { event.preventDefault(); event.stopPropagation(); input({ action: 'key', key: 'A', modifiers: event.metaKey ? 4 : 2 }) }
          else if (keys.includes(event.key)) { event.preventDefault(); event.stopPropagation(); input({ action: 'key', key: event.key, modifiers: (event.altKey ? 1 : 0) + (event.ctrlKey ? 2 : 0) + (event.metaKey ? 4 : 0) + (event.shiftKey ? 8 : 0) }); if (event.key === 'Escape') event.currentTarget.blur() }
          else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) { event.preventDefault(); event.stopPropagation(); input({ action: 'text', text: event.key }) }
        }} style={{ aspectRatio: `${state.width}/${state.height}` }}>
        <img src={`data:image/jpeg;base64,${state.frame}`} alt={`Live browser page: ${title}`} draggable={false} />
        {cursor && <div className={`browser-cursor ${cursor.click ? 'clicking' : ''}`} style={{ left: `${cursor.x / (state.width || 1280) * 100}%`, top: `${cursor.y / (state.height || 900) * 100}%` }} aria-label={cursor.click ? 'Agent clicking' : 'Agent cursor'}><MousePointer2 size={23} fill="currentColor" /><span>Codex</span></div>}
      </div> : <div className="context-empty"><Globe size={28} /><strong>{state?.open ? 'Loading browser page…' : 'New tab'}</strong><span>{state?.available === false ? state.reason : state?.agentAvailable ? 'Enter a website above or ask the agent to browse.' : 'Enter a website above to start browsing.'}</span></div>}
    </div>
    {state?.open && control && <form className="browser-typing" onSubmit={event => { event.preventDefault(); if (typing) { input({ action: 'text', text: typing }); setTyping('') } }}><input aria-label="Type in browser" placeholder="Click a field, then type here…" maxLength={2000} value={typing} onChange={event => setTyping(event.target.value)} /><button type="submit" disabled={!typing || busy}>Send text</button></form>}
    <footer className="browser-status"><span className={state?.open ? 'live' : ''} />{state?.open ? 'Live page · click to control' : 'Jev browser'}<small title="Site cookies and storage stay in the dedicated local browser profile. Sites control cookie expiry.">Cookies saved locally</small></footer>
  </section>
}
