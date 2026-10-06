import { useState, type ReactNode } from 'react'
import { ChevronRight, FileCode2, Globe, Sparkles, Terminal } from 'lucide-react'
import { MarkdownContent } from './MarkdownContent'
import type { StreamEvent } from './types'
import './work-activity.css'

// Native details provides keyboard semantics; stable component keys preserve
// manual expansion while streamed events update the label and body.
export function ActivityDisclosure({ className, icon, label, labelClass = '', title, status, children }: { className: string; icon?: ReactNode; label: ReactNode; labelClass?: string; title?: string; status?: string; children: ReactNode }) {
  const [expanded, setExpanded] = useState(false)
  return <details className={`activity-disclosure ${className}`} open={expanded} onToggle={event => setExpanded(event.currentTarget.open)}>
    <summary title={title}>{icon}<span className={`activity-label ${labelClass}`}>{label}</span><ChevronRight size={14} className="disclosure-chevron" aria-hidden="true" />{status && <span className="command-failure">{status}</span>}</summary>{children}
  </details>
}

function ActivitySurface({ title, duration, status, children }: { title: string; duration?: string; status?: string; children: ReactNode }) {
  return <div className="command-card-body"><header>{title}</header><pre><code>{children}</code></pre>{(duration || status) && <footer><span>{duration}</span><span>{status}</span></footer>}</div>
}

export function CommandCard({ event }: { event: StreamEvent }) {
  const command = event.command ?? event.content.split('\n').find(line => line.trim())?.trim() ?? event.title ?? 'Command'
  const commandLine = command.replace(/\s+/g, ' ').trim() || 'Command'
  const output = event.state !== 'running' && event.commandOutput !== undefined ? event.commandOutput : event.content.startsWith(command) ? event.content.slice(command.length).replace(/^\n/, '') : event.content
  const exitCode = typeof event.meta?.exitCode === 'number' ? event.meta.exitCode : undefined
  const failed = event.state === 'failed' || exitCode !== undefined && exitCode !== 0
  const status = event.state === 'running' ? 'Running' : failed ? exitCode !== undefined ? `Exit ${exitCode}` : 'Failed' : exitCode === 0 ? 'Success' : 'Completed'
  return <ActivityDisclosure className={`command-card ${event.state ?? ''} ${failed ? 'failed' : ''}`} icon={<Terminal size={15} />} label={`${event.state === 'running' ? 'Running' : 'Ran'} ${commandLine}`} labelClass="command-line" title={`${commandLine} · ${status}`} status={failed ? 'Failed' : undefined}>
    <ActivitySurface title="Shell" duration={typeof event.meta?.durationMs === 'number' ? `${(event.meta.durationMs / 1000).toFixed(1)}s` : undefined} status={status}><span className="prompt">$</span> {command}{output ? `\n\n${output}` : ''}</ActivitySurface>
  </ActivityDisclosure>
}

export function CommandGroup({ commands }: { commands: StreamEvent[] }) {
  const running = commands.some(command => command.state === 'running')
  const failures = commands.filter(command => command.state === 'failed' || typeof command.meta?.exitCode === 'number' && command.meta.exitCode !== 0).length
  return <ActivityDisclosure className={`command-group ${running ? 'running' : failures ? 'failed' : 'done'}`} icon={<Terminal size={15} />} label={`${running ? 'Running' : 'Ran'} ${commands.length} ${commands.length === 1 ? 'command' : 'commands'}`} labelClass="command-group-label" status={failures ? `${failures} failed` : undefined}>
    <div className="command-group-items">{commands.map(command => <CommandCard event={command} key={command.id} />)}</div>
  </ActivityDisclosure>
}


export function FileChangeActivity({ event }: { event: StreamEvent }) {
  const verb = event.state === 'running' ? 'Changing' : event.state === 'failed' ? 'Failed changes to' : 'Changed'
  const target = event.outputPaths?.length ? `${event.outputPaths.length} ${event.outputPaths.length === 1 ? 'file' : 'files'}` : 'workspace files'
  return <ActivityDisclosure className={`file-change-disclosure ${event.state ?? ''}`} icon={<FileCode2 size={15} />} label={`${verb} ${target}`} status={event.state === 'failed' ? 'Failed' : undefined}><ActivitySurface title="Changes">{event.content}</ActivitySurface></ActivityDisclosure>
}

export function ReasoningActivity({ event, cwd }: { event: StreamEvent; cwd: string }) {
  return <ActivityDisclosure className="reasoning-disclosure" icon={<Sparkles size={15} />} label="Thought summary"><div className="activity-reasoning"><MarkdownContent source={event.content} compact cwd={cwd} /></div></ActivityDisclosure>
}

export function SearchActivity({ event }: { event: StreamEvent }) {
  return <div className="search-step"><Globe size={15} /><span>{event.title ?? 'Searched the web'}</span>{event.content && <small>{event.content}</small>}</div>
}
