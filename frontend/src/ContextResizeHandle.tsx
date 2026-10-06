import { useCallback, useEffect, useRef, useState } from 'react'

export function ContextResizeHandle() {
  const handle = useRef<HTMLDivElement>(null)
  const drag = useRef<{ x: number; width: number } | null>(null)
  const [width, setWidth] = useState(440)
  const [bounds, setBounds] = useState({ min: 280, max: 940 })
  const limits = useCallback(() => {
    const shell = handle.current?.closest<HTMLElement>('.app-shell')
    const sidebar = shell?.querySelector('.chat-sidebar')?.getBoundingClientRect().width ?? 0
    return { min: Math.min(280, innerWidth), max: innerWidth <= 1000 ? innerWidth : Math.max(280, innerWidth - sidebar - 360) }
  }, [])
  const resize = useCallback((next: number) => {
    const shell = handle.current?.closest<HTMLElement>('.app-shell')
    const { min, max } = limits()
    const bounded = Math.round(Math.min(max, Math.max(min, next)))
    shell?.style.setProperty('--context-width', `${bounded}px`)
    shell?.style.setProperty('--context-user-width', `${bounded}px`)
    setWidth(bounded); setBounds({ min, max })
  }, [limits])
  useEffect(() => {
    const sync = () => {
      setBounds(limits())
      const current = handle.current?.parentElement?.getBoundingClientRect().width
      if (current) {
        if (handle.current?.closest<HTMLElement>('.app-shell')?.style.getPropertyValue('--context-user-width')) resize(current)
        else setWidth(Math.round(current))
      }
    }
    sync(); window.addEventListener('resize', sync)
    const observer = new ResizeObserver(sync)
    if (handle.current?.parentElement) observer.observe(handle.current.parentElement)
    return () => { observer.disconnect(); window.removeEventListener('resize', sync); document.body.classList.remove('context-resizing') }
  }, [limits, resize])
  return <div ref={handle} className="context-resize-handle" role="separator" aria-label="Resize context sidebar" aria-orientation="vertical" aria-valuemin={bounds.min} aria-valuemax={bounds.max} aria-valuenow={width} tabIndex={0}
    onPointerDown={event => { if (event.button !== 0) return; event.preventDefault(); drag.current = { x: event.clientX, width: event.currentTarget.parentElement!.getBoundingClientRect().width }; event.currentTarget.setPointerCapture(event.pointerId); document.body.classList.add('context-resizing') }}
    onPointerMove={event => { if (drag.current) resize(drag.current.width + drag.current.x - event.clientX) }}
    onPointerUp={event => { drag.current = null; if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId); document.body.classList.remove('context-resizing') }}
    onLostPointerCapture={() => { drag.current = null; document.body.classList.remove('context-resizing') }}
    onDoubleClick={() => { const shell = handle.current?.closest<HTMLElement>('.app-shell'); shell?.style.removeProperty('--context-width'); shell?.style.removeProperty('--context-user-width'); setWidth(Math.round(handle.current?.parentElement?.getBoundingClientRect().width ?? 440)) }}
    onKeyDown={event => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) { event.preventDefault(); event.stopPropagation(); resize(event.key === 'Home' ? limits().min : event.key === 'End' ? limits().max : width + (event.key === 'ArrowLeft' ? 1 : -1) * (event.shiftKey ? 64 : 16)) } }} />
}
