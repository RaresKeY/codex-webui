import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowLeft, Globe, MousePointer2, RefreshCw, X } from 'lucide-react'

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
  const generation = useRef(0)
  const actionController = useRef<AbortController | null>(null)
  const actionBusy = useRef(false)
  useEffect(() => () => { actionController.current?.abort() }, [])
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
  const navigate = (event: FormEvent) => { event.preventDefault(); if (url?.trim()) void act('open', url.trim()) }
  const currentSignal = signal?.threadId === threadId ? signal : null
  const cursor = currentSignal && currentSignal.revision >= (state?.revision ?? 0) ? currentSignal.cursor : state?.cursor
  const title = state?.title || 'New tab'
  return <section className="browser-context" id="context-tool-browser" role="tabpanel" aria-label="Browser">
    <div className="browser-tab"><Globe size={14} /><span>{title}</span><small>Experimental</small><button aria-label="Close browser session" disabled={!state?.open || busy} onClick={() => { void act('close') }}><X size={15} /></button></div>
    <form className="browser-toolbar" onSubmit={navigate}>
      <button type="button" aria-label="Browser back" disabled={!state?.open || busy} onClick={() => { void act('back') }}><ArrowLeft size={16} /></button>
      <button type="button" aria-label="Reload browser page" disabled={!state?.open || busy} onClick={() => { void act('reload') }}><RefreshCw size={16} className={busy ? 'spin' : ''} /></button>
      <input aria-label="Browser address" type="url" placeholder="Enter an HTTPS address" value={url ?? state?.url ?? ''} onChange={event => setUrl(event.target.value)} disabled={state?.available === false || busy} />
      <button type="submit" disabled={!url?.trim() || busy || !state?.available}>Go</button>
    </form>
    {(error || frameError) && <div className="browser-error" role="alert">{error || frameError}</div>}
    <div className="browser-page">
      {state?.open && state.frame ? <div className="browser-viewport" style={{ aspectRatio: `${state.width}/${state.height}` }}>
        <img src={`data:image/jpeg;base64,${state.frame}`} alt={`Live browser page: ${title}`} draggable={false} />
        {cursor && <div className={`browser-cursor ${cursor.click ? 'clicking' : ''}`} style={{ left: `${cursor.x / (state.width || 1280) * 100}%`, top: `${cursor.y / (state.height || 900) * 100}%` }} aria-label={cursor.click ? 'Agent clicking' : 'Agent cursor'}><MousePointer2 size={23} fill="currentColor" /><span>Codex</span></div>}
      </div> : <div className="context-empty"><Globe size={28} /><strong>{state?.open ? 'Loading browser page…' : 'Browse alongside your chat'}</strong><span>{state?.available === false ? state.reason : state?.agentAvailable ? 'Enter an HTTPS address, or ask the agent to browse in a new chat. The browser opens here automatically.' : 'Enter an HTTPS address. Agent tools require the verified Codex CLI 0.160.1 runtime and a new chat.'}</span></div>}
    </div>
    <footer className="browser-status"><span className={state?.open ? 'live' : ''} />{state?.open ? 'Live page · agent-controlled' : 'Jev browser'}<small>{state?.agentAvailable ? 'View only · agent tools in new chats' : 'View only · manual navigation'}</small></footer>
  </section>
}
