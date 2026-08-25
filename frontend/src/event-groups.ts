import type { StreamEvent } from './types'

export type EventFeedEntry =
  | { type: 'event'; event: StreamEvent }
  | { type: 'commands'; id: string; commands: StreamEvent[] }

export function groupEventFeed(events: StreamEvent[]): EventFeedEntry[] {
  const entries: EventFeedEntry[] = []
  for (const event of events) {
    if (event.kind !== 'command') {
      entries.push({ type: 'event', event })
      continue
    }
    const previous = entries.at(-1)
    if (previous?.type === 'commands') previous.commands.push(event)
    else entries.push({ type: 'commands', id: `commands-${event.id}`, commands: [event] })
  }
  return entries
}
