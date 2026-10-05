import type { Plugin } from './types'

export interface PluginQuery { query: string; start: number; end: number }

export function pluginQuery(value: string, caret: number): PluginQuery | null {
  const match = /(?:^|[\s([{])@([A-Za-z0-9._-]*)$/.exec(value.slice(0, caret))
  if (!match) return null
  const tail = /^[A-Za-z0-9._-]*/.exec(value.slice(caret))?.[0].length ?? 0
  return { query: match[1], start: caret - match[1].length - 1, end: caret + tail }
}

export function mentionedPluginIds(value: string, plugins: Plugin[], selected: string[]): string[] {
  return plugins.filter(plugin => selected.includes(plugin.id) && new RegExp(`(^|[^\\w@])@${plugin.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![\\w.-])`).test(value)).map(plugin => plugin.id)
}
