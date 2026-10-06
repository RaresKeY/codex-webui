import { Box, Globe, X } from 'lucide-react'
import { useState } from 'react'
import { chatResources } from './chat-resources'
import type { StreamEvent } from './types'

export function ChatSummary({ events, onClose, onOutputs }: { events: StreamEvent[]; onClose: () => void; onOutputs: () => void }) {
  const { sources, outputs } = chatResources(events)
  const [allSources, setAllSources] = useState(false)
  return <aside id="chat-summary" className="chat-summary" aria-label="Sources and outputs" onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); onClose() } }}>
    <button className="icon-button summary-close" aria-label="Close sources and outputs" onClick={onClose}><X size={15} /></button>
    <section><h3>Outputs</h3>{outputs.length ? <><ul>{outputs.slice(0, 4).map(output => <li key={output.id}><button onClick={onOutputs} title={output.id}><Box size={15} /><span>{output.title}</span></button></li>)}</ul><button className="summary-view-all" onClick={onOutputs}>View outputs</button></> : <p>No outputs yet</p>}</section>
    <section><h3>Sources</h3>{sources.length ? <><ul>{sources.slice(0, allSources ? 100 : 4).map(source => <li key={source.url}><a href={source.url} target="_blank" rel="noopener noreferrer" title={source.url}><Globe size={15} /><span>{source.title}<small>{new URL(source.url).hostname.replace(/^www\./, '')}</small></span></a></li>)}</ul>{sources.length > 4 && <button className="summary-view-all" onClick={() => setAllSources(value => !value)}>{allSources ? 'Show less' : `View all ${sources.length} sources`}</button>}</> : <p>No sources yet</p>}</section>
  </aside>
}
