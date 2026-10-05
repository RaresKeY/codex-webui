import { useEffect, useId, useRef, useState, type CSSProperties } from 'react'
import { createPortal } from 'react-dom'
import { contextUsageLabel } from './context-usage'
import { formatTokenCount } from './token-format'
import type { Conversation } from './types'

export function ContextIndicator({ conversation }: { conversation: Conversation }) {
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState({ left: 8, bottom: 0 })
  const trigger = useRef<HTMLButtonElement>(null)
  const id = useId()
  const known = conversation.contextUsedTokens !== undefined && conversation.contextWindowTokens !== undefined
  const percent = known ? Math.max(0, Math.min(100, conversation.contextPercent)) : 0
  useEffect(() => {
    if (!open) return
    const place = () => {
      const rect = trigger.current?.getBoundingClientRect()
      if (rect) setPosition({ left: Math.max(8, Math.min(innerWidth - 228, rect.left + rect.width / 2 - 110)), bottom: innerHeight - rect.top + 8 })
    }
    place()
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => { window.removeEventListener('resize', place); window.removeEventListener('scroll', place, true) }
  }, [open])
  return <div className="composer-context" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
    <button ref={trigger} type="button" className="context-button" aria-label={contextUsageLabel(conversation)} aria-describedby={open ? id : undefined} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onClick={() => setOpen(true)} onKeyDown={event => { if (event.key === 'Escape') { setOpen(false); event.stopPropagation() } }}>
      <span className={`context-ring ${known ? '' : 'unknown'}`} aria-hidden="true" style={{ '--context': `${percent * 3.6}deg` } as CSSProperties} />
    </button>
    {open && createPortal(<div id={id} role="tooltip" className="context-tooltip" style={position}><span>Context window:</span>{known ? <><strong>{percent}% used ({100 - percent}% left)</strong><strong title={contextUsageLabel(conversation)}>{formatTokenCount(conversation.contextUsedTokens!).toLowerCase()} / {formatTokenCount(conversation.contextWindowTokens!).toLowerCase()} tokens used</strong></> : <strong>{conversation.contextUsedTokens === undefined ? 'Usage not reported yet' : `${formatTokenCount(conversation.contextUsedTokens).toLowerCase()} tokens used · total unavailable`}</strong>}</div>, document.body)}
  </div>
}
