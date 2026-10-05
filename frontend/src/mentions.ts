import type { Mention } from './types'

export function mentionQuery(value: string, caret: number): { query: string; start: number; end: number } | null {
  const match = /(?:^|[\s([{])[@$]([\p{L}\p{N}._:/-]*)$/u.exec(value.slice(0, caret))
  if (!match) return null
  const tail = /^[\p{L}\p{N}._:/-]*/u.exec(value.slice(caret))?.[0].length ?? 0
  return { query: match[1], start: caret - match[1].length - 1, end: caret + tail }
}

export function retainedMentions(value: string, selected: Mention[]): Mention[] {
  return selected.filter(entry => {
    const end = entry.insertText.endsWith('"') ? '(?![\\p{L}\\p{N}_])' : '(?![\\p{L}\\p{N}_.\\-/])'
    return new RegExp(`(^|[^\\p{L}\\p{N}_@$])${entry.insertText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}${end}`, 'u').test(value)
  })
}

export function mentionSuggestions(entries: Mention[], query: string): Mention[] {
  const groups: Mention['kind'][] = ['skill', 'plugin', 'app', 'file']
  const matches = entries.filter(entry => `${entry.name} ${entry.displayName} ${entry.description}`.toLowerCase().includes(query.toLowerCase()))
  // Give each category room in the initial menu; matching files follow native
  // fuzzy ordering, which need not contain a literal substring.
  const ranked = matches.filter(entry => entry.kind !== 'file')
  const files = entries.filter(entry => entry.kind === 'file')
  const result: Mention[] = []
  for (let index = 0; result.length < 12; index++) {
    let added = false
    for (const kind of groups) {
      const entry = (kind === 'file' ? files : ranked.filter(item => item.kind === kind))[index]
      if (entry) { result.push(entry); added = true }
      if (result.length === 12) break
    }
    if (!added) break
  }
  return result
}
