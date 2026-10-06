import { useCallback, useLayoutEffect, useRef, useState } from 'react'

const WIDTH_KEY = 'codex-webui.context-width'
function savedWidth(): number {
  try { const value = Number(localStorage.getItem(WIDTH_KEY)); if (Number.isFinite(value) && value >= 280 && value <= 5000) return value } catch { /* Storage can be unavailable. */ }
  return 440
}

export function ContextResizeHandle() {
  const handle = useRef<HTMLDivElement>(null)
  const drag = useRef<{ x: number; width: number } | null>(null)
  const preferred = useRef(savedWidth())
  const [width, setWidth] = useState(440)
  const [bounds, setBounds] = useState({ min: 280, max: 940 })
  const limits = useCallback(() => {
    const shell = handle.current?.closest<HTMLElement>('.app-shell')
    const sidebar = shell?.querySelector('.chat-sidebar')?.getBoundingClientRect().width ?? 0
    return { min: Math.min(280, innerWidth), max: innerWidth <= 1000 ? innerWidth : Math.max(280, innerWidth - sidebar - 360) }
  }, [])
  const apply = useCallback((next: number) => {
    const shell = handle.current?.closest<HTMLElement>('.app-shell')
    const { min, max } = limits()
    const bounded = Math.round(Math.min(max, Math.max(min, next)))
    shell?.style.setProperty('--context-width', `${bounded}px`)
    shell?.style.setProperty('--context-user-width', `${bounded}px`)
    setWidth(bounded); setBounds({ min, max })
    return bounded
  }, [limits])
  const resize = (next: number) => {
    preferred.current = apply(next)
    try { localStorage.setItem(WIDTH_KEY, String(preferred.current)) } catch { /* Retain session behavior. */ }
  }
  useLayoutEffect(() => {
    const sync = () => { apply(preferred.current) }
    const storage = (event: StorageEvent) => { if (event.key === WIDTH_KEY) { preferred.current = savedWidth(); sync() } }
    sync(); window.addEventListener('resize', sync); window.addEventListener('storage', storage)
    const shell = handle.current?.closest<HTMLElement>('.app-shell')
    const observer = new MutationObserver(sync)
    if (shell) observer.observe(shell, { attributes: true, attributeFilter: ['class'] })
    return () => { observer.disconnect(); window.removeEventListener('resize', sync); window.removeEventListener('storage', storage); document.body.classList.remove('context-resizing') }
  }, [apply])
  return <div ref={handle} className="context-resize-handle" role="separator" aria-label="Resize context sidebar" aria-orientation="vertical" aria-valuemin={bounds.min} aria-valuemax={bounds.max} aria-valuenow={width} tabIndex={0}
    onPointerDown={event => { if (event.button !== 0) return; event.preventDefault(); drag.current = { x: event.clientX, width: event.currentTarget.parentElement!.getBoundingClientRect().width }; event.currentTarget.setPointerCapture(event.pointerId); document.body.classList.add('context-resizing') }}
    onPointerMove={event => { if (drag.current) resize(drag.current.width + drag.current.x - event.clientX) }}
    onPointerUp={event => { drag.current = null; if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId); document.body.classList.remove('context-resizing') }}
    onLostPointerCapture={() => { drag.current = null; document.body.classList.remove('context-resizing') }}
    onDoubleClick={() => { preferred.current = 440; try { localStorage.removeItem(WIDTH_KEY) } catch { /* Storage can be unavailable. */ } apply(440) }}
    onKeyDown={event => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) { event.preventDefault(); event.stopPropagation(); resize(event.key === 'Home' ? limits().min : event.key === 'End' ? limits().max : width + (event.key === 'ArrowLeft' ? 1 : -1) * (event.shiftKey ? 64 : 16)) } }} />
}
