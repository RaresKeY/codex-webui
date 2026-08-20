import { demoBootstrap, demoEvents, demoFileContents } from './demo'
import type { RealtimeVoice, RealtimeVoicesList, WebRtcRealtimeVersion } from './app-server-protocol'
import type { BackgroundTerminals, BootstrapPayload, ConnectionState, Conversation, ConversationSnapshot, FileReadResult, ImageAsset, LiveUpdate, Project, RealtimeCapability, Schedule, StreamEvent, TurnLifecycle, Usage, WorkspaceChanges, WorkspaceFile } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'
type JsonObject = Record<string, unknown>

export class ApiError extends Error {
  constructor(readonly status: number, message: string, readonly payload?: unknown) {
    super(message)
    this.name = 'ApiError'
  }
}

export function turnStartFailureMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 503) {
    return 'The local Codex service is offline. Your prompt is preserved above; reconnect, then retry.'
  }
  const message = error instanceof Error ? error.message.toLowerCase() : ''
  if (message.includes('not materialized') || message.includes('no rollout found')) {
    return 'This new conversation was not ready for its first turn. Your prompt is preserved above; retry after reconnecting the local service.'
  }
  if (error instanceof ApiError && error.status === 409 && !message.includes('rpc_error')) {
    return `${error.message} Your prompt is preserved above for retry.`
  }
  return 'The local service could not start this Codex turn. Your prompt is preserved above; reconnect and retry.'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let payload: unknown
    try { payload = await response.json() } catch { payload = undefined }
    const detail = text(object(payload).detail, `${response.status} ${response.statusText}`)
    throw new ApiError(response.status, detail, payload)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function object(value: unknown): JsonObject { return value && typeof value === 'object' ? value as JsonObject : {} }
function array(value: unknown): unknown[] { return Array.isArray(value) ? value : [] }
function text(value: unknown, fallback = ''): string { return typeof value === 'string' ? value : fallback }
function optionalText(value: unknown): string | undefined { return typeof value === 'string' && value ? value : undefined }
function number(value: unknown, fallback = 0): number { return typeof value === 'number' && Number.isFinite(value) ? value : fallback }
function optionalNumber(value: unknown): number | undefined { return typeof value === 'number' && Number.isFinite(value) ? value : undefined }
function timeLabel(value: unknown): string {
  if (!value) return 'Recently'
  const parsed = new Date(typeof value === 'number' && value < 1e12 ? value * 1000 : String(value))
  if (Number.isNaN(parsed.getTime())) return 'Recently'
  const minutes = Math.floor((Date.now() - parsed.getTime()) / 60000)
  if (minutes < 1) return 'Now'
  if (minutes < 60) return `${minutes}m`
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h`
  return parsed.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function normalizeProject(value: unknown): Project {
  const item = object(value)
  return {
    id: String(item.id ?? crypto.randomUUID()),
    name: text(item.name, 'Untitled project'),
    path: text(item.path ?? item.workspace, '.'),
    color: text(item.color, '#87d4a6'),
    chatCount: 0,
    updatedAt: timeLabel(item.updated_at ?? item.updatedAt),
  }
}

export function normalizeConversation(value: unknown, fallbackProject = ''): Conversation {
  const outer = object(value)
  const item = object(outer.thread ?? outer)
  const webui = object(item.webui)
  const turns = array(item.turns)
  const lastTurn = object(turns.at(-1))
  const rawStatus = typeof item.status === 'string' ? item.status : text(object(item.status).type)
  const status: Conversation['status'] = rawStatus === 'active' || rawStatus === 'running' ? 'running' : rawStatus === 'paused' || rawStatus === 'interrupted' ? 'paused' : rawStatus === 'failed' || rawStatus === 'error' || rawStatus === 'systemError' ? 'failed' : 'ready'
  return {
    id: String(item.id ?? item.threadId ?? crypto.randomUUID()),
    projectId: String(webui.project_id ?? item.projectId ?? fallbackProject),
    title: text(item.name ?? item.title, 'Untitled conversation'),
    preview: text(item.preview ?? lastTurn.preview ?? item.lastMessage, 'Resumable local Codex session'),
    updatedAt: timeLabel(item.updatedAt ?? item.updated_at ?? item.createdAt ?? item.created_at),
    status,
    cwd: text(item.cwd, '.'),
    model: text(item.model, 'gpt-5.6-sol'),
    contextPercent: Math.round(number(item.contextPercent ?? item.context_percent)),
  }
}

function languageFor(name: string, mime: string): string | undefined {
  const extension = name.split('.').pop()?.toLowerCase()
  return ({ ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript', py: 'python', css: 'css', json: 'json', md: 'markdown', yaml: 'yaml', yml: 'yaml' } as Record<string, string>)[extension ?? ''] ?? (mime.startsWith('text/') ? 'text' : undefined)
}

function normalizeWorkspace(value: unknown): WorkspaceFile[] {
  const item = object(value)
  const convert = (raw: unknown): WorkspaceFile => {
    const entry = object(raw)
    const path = text(entry.path, text(entry.name))
    const isFolder = entry.type === 'directory' || entry.type === 'folder'
    return { id: path || crypto.randomUUID(), name: text(entry.name, path), path, type: isFolder ? 'folder' : 'file', language: isFolder ? undefined : languageFor(path, text(entry.mime)), children: isFolder ? array(entry.children).map(convert) : undefined }
  }
  if (item.type === 'directory' || item.type === 'folder') return array(item.children).map(convert)
  return array(value).map(convert)
}

export function normalizeBackgroundTerminals(value: unknown): BackgroundTerminals {
  const response = object(value)
  const items = array(response.data ?? value).map(raw => {
    const item = object(raw)
    return {
      itemId: text(item.itemId ?? item.item_id),
      processId: text(item.processId ?? item.process_id),
      command: text(item.command),
      cwd: text(item.cwd),
      osPid: optionalNumber(item.osPid ?? item.os_pid),
      cpuPercent: optionalNumber(item.cpuPercent ?? item.cpu_percent),
      rssKb: optionalNumber(item.rssKb ?? item.rss_kb),
    }
  }).filter(item => item.processId)
  return { items, unavailableReason: optionalText(response.unavailableReason ?? response.unavailable_reason) }
}

export function normalizeWorkspaceChanges(value: unknown): WorkspaceChanges {
  const root = object(value)
  const files = array(root.data).map(raw => {
    const item = object(raw)
    const path = text(item.path)
    const rawStatus = text(item.status)
    const status: WorkspaceFile['status'] = rawStatus === 'added' || rawStatus === 'deleted' ? rawStatus : 'modified'
    return {
      id: path || crypto.randomUUID(),
      name: text(item.name, path.split('/').at(-1) ?? path),
      path,
      type: 'file' as const,
      language: languageFor(path, ''),
      status,
    }
  }).filter(file => file.path)
  return { files, repoRoot: text(root.repoRoot) || undefined, truncated: root.truncated === true }
}

function normalizeSchedule(value: unknown): Schedule {
  const item = object(value)
  const schedule = text(item.schedule)
  const type = text(item.schedule_type)
  return {
    id: String(item.id ?? crypto.randomUUID()),
    name: text(item.name, 'Untitled task'),
    prompt: text(item.prompt),
    cadence: type === 'cron' ? `Cron · ${schedule}` : `Every ${schedule}`,
    nextRun: text(item.next_run_at ?? item.nextRun, item.last_status ? `Last: ${String(item.last_status)}` : 'Pending scheduler'),
    enabled: Boolean(item.enabled),
  }
}

function pickNumber(root: JsonObject, paths: string[][]): number {
  for (const path of paths) {
    let value: unknown = root
    for (const key of path) value = object(value)[key]
    if (typeof value === 'number') return value
  }
  return 0
}

function pickOptionalNumber(root: JsonObject, paths: string[][]): number | null {
  for (const path of paths) {
    let value: unknown = root
    for (const key of path) value = object(value)[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value
  }
  return null
}

export function normalizeUsage(value: unknown, sessionCount: number): Usage {
  const item = object(value)
  const limitsEnvelope = object(item.rateLimits)
  const limits = object(limitsEnvelope.rateLimits)
  const summary = object(object(item.usage).summary)
  const primary = object(limits.primary)
  const secondary = object(limits.secondary)
  const resetValue = primary.resetsAt ?? primary.resets_at
  const resetDate = typeof resetValue === 'number' ? new Date(resetValue * 1000) : null
  const resetMinutes = resetDate ? Math.max(0, Math.round((resetDate.getTime() - Date.now()) / 60000)) : null
  const resetsAt = resetMinutes !== null ? resetMinutes < 60 ? `in ${resetMinutes}m` : `in ${Math.floor(resetMinutes / 60)}h ${resetMinutes % 60}m` : text(resetValue, sessionCount ? 'Unavailable' : 'No usage data')
  return {
    fiveHourPercent: Object.keys(primary).length ? Math.round(pickNumber(limits, [['primary', 'usedPercent'], ['primary', 'used_percent']])) : null,
    weeklyPercent: Object.keys(secondary).length ? Math.round(pickNumber(limits, [['secondary', 'usedPercent'], ['secondary', 'used_percent']])) : null,
    lifetimeTokens: pickOptionalNumber(summary, [['lifetimeTokens'], ['lifetime_tokens']]),
    peakDailyTokens: pickOptionalNumber(summary, [['peakDailyTokens'], ['peak_daily_tokens']]),
    currentStreakDays: pickOptionalNumber(summary, [['currentStreakDays'], ['current_streak_days']]),
    resetsAt,
  }
}

function normalizeImage(value: unknown): ImageAsset {
  const item = object(value)
  return { id: String(item.id ?? crypto.randomUUID()), name: text(item.name, 'Image'), url: text(item.url), mime: text(item.mime, 'image/*'), size: number(item.size), modifiedAt: timeLabel(item.modified_at ?? item.modifiedAt) }
}

function normalizeBootstrap(raw: unknown): BootstrapPayload {
  const item = object(raw)
  const projects = array(item.projects).map(normalizeProject)
  const rawThreads = object(item.threads).data ?? item.threads
  const conversations = array(rawThreads).map(thread => normalizeConversation(thread, projects[0]?.id))
  const counts = new Map<string, number>()
  conversations.forEach(chat => counts.set(chat.projectId, (counts.get(chat.projectId) ?? 0) + 1))
  projects.forEach(project => { project.chatCount = counts.get(project.id) ?? 0 })
  const modelData = array(object(item.models).data ?? item.models)
  const models = modelData.map(model => text(object(model).id ?? object(model).model ?? object(model).slug ?? model)).filter(Boolean)
  const images = array(object(item.images).data ?? item.images).map(normalizeImage)
  const system = object(item.system)
  const codex = object(system.codex)
  const serverInfo = object(codex.server_info)
  const features = object(item.features)
  return {
    projects,
    conversations,
    files: normalizeWorkspace(item.workspace),
    schedules: array(item.tasks).map(normalizeSchedule),
    usage: normalizeUsage(item.usage, conversations.length),
    models: models.length ? models : ['gpt-5.6-sol', 'gpt-5.6-terra'],
    images,
    demo: false,
    codexVersion: text(codex.cli_version ?? serverInfo.version ?? serverInfo.codexVersion) || undefined,
    updatesEnabled: features.updates === true,
    realtimeVoice: features.realtimeVoice === true,
    realtimeVoiceReason: text(features.realtimeVoiceReason) || undefined,
    runtime: system.runtime === 'localhost-companion' || system.runtime === 'container' ? system.runtime : 'unknown',
  }
}

function contentText(value: unknown): string {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(part => contentText(object(part).text ?? object(part).content ?? part)).filter(Boolean).join('\n')
  const item = object(value)
  return text(item.text ?? item.content ?? item.message ?? item.summary)
}

function fileChangesText(value: unknown): string {
  return array(value).map(raw => {
    const change = object(raw)
    const heading = [text(change.kind), text(change.path)].filter(Boolean).join(' · ')
    const diff = text(change.diff)
    return [heading, diff].filter(Boolean).join('\n')
  }).filter(Boolean).join('\n\n')
}

export function normalizeItem(raw: unknown, index: number): StreamEvent | null {
  const item = object(raw)
  const type = text(item.type ?? item.kind).toLowerCase()
  const id = String(item.id ?? `history-${index}`)
  const timestamp = timeLabel(item.timestamp ?? item.createdAt ?? item.created_at)
  const state = item.status === 'failed' ? 'failed' : item.status === 'inProgress' ? 'running' : item.status ? 'done' : undefined
  if (type.includes('user')) return { id, kind: 'message', role: 'user', content: contentText(item.content ?? item.message ?? item.input), timestamp, state }
  if (type.includes('agent') || type.includes('assistant') || type === 'message') return { id, kind: 'message', role: 'assistant', content: contentText(item.text ?? item.content ?? item.message ?? item.output), timestamp, state }
  if (type === 'plan' || type.includes('plan')) return { id, kind: 'reasoning', title: 'Plan', content: contentText(item.text ?? item.content), timestamp, state: state ?? 'done' }
  if (type.includes('reason')) return { id, kind: 'reasoning', title: 'Reasoning summary', content: contentText(item.summary ?? item.content), timestamp, state: state ?? 'done' }
  if (type.includes('command') || type.includes('exec')) {
    const command = contentText(item.command ?? item.content)
    const output = contentText(item.aggregatedOutput)
    return { id, kind: 'command', title: text(item.name, 'Command'), content: [command, output].filter(Boolean).join('\n'), timestamp, state: item.status === 'failed' ? 'failed' : item.status === 'inProgress' ? 'running' : 'done', meta: { ...(typeof item.exitCode === 'number' ? { exitCode: item.exitCode } : {}), ...(typeof item.durationMs === 'number' ? { durationMs: item.durationMs } : {}) } }
  }
  if (type.includes('file') || type.includes('patch') || type.includes('diff')) return { id, kind: 'file', title: text(item.name, 'Workspace changes'), content: fileChangesText(item.changes) || contentText(item.path ?? item.content), timestamp, state: item.status === 'failed' ? 'failed' : item.status === 'inProgress' ? 'running' : 'done' }
  return null
}

function eventsFromThread(raw: unknown): StreamEvent[] {
  const outer = object(raw)
  const thread = object(outer.thread ?? outer)
  return array(thread.turns).flatMap((turn, turnIndex) => {
    const record = object(turn)
    return array(record.items ?? record.events ?? record.messages).map((item, itemIndex) => normalizeItem(item, turnIndex * 1000 + itemIndex)).filter((event): event is StreamEvent => Boolean(event))
  })
}

function errorText(value: unknown): string | undefined {
  const error = object(value)
  return text(error.message ?? error.additionalDetails) || undefined
}

export function normalizeThreadLifecycle(raw: unknown): TurnLifecycle {
  const outer = object(raw)
  const thread = object(outer.thread ?? outer)
  const turns = array(thread.turns)
  const turn = object(turns.at(-1))
  const turnId = text(turn.id) || undefined
  const status = text(turn.status)
  if (!turnId || !status) return { phase: 'idle' }
  if (status === 'inProgress') {
    const hasAssistantText = array(turn.items).some(item => {
      const record = object(item)
      const type = text(record.type).toLowerCase()
      return (type.includes('agent') || type.includes('assistant')) && Boolean(contentText(record.text ?? record.content ?? record.message))
    })
    return { phase: hasAssistantText ? 'streaming' : 'waiting', turnId }
  }
  if (status === 'failed') return { phase: 'failed', turnId, error: errorText(turn.error) }
  if (status === 'interrupted') return { phase: 'interrupted', turnId }
  if (status === 'completed') return { phase: 'completed', turnId }
  return { phase: 'idle' }
}

function pendingApprovals(raw: unknown, conversationId: string): StreamEvent[] {
  const data = object(raw).data ?? raw
  const entries: Array<[string, unknown]> = Array.isArray(data)
    ? data.map((request, index) => [String(object(request).id ?? object(request).requestId ?? index), request])
    : Object.entries(object(data))
  return entries.flatMap(([requestId, value]) => {
    const request = object(value)
    const params = object(request.params)
    const thread = text(params.threadId ?? params.thread_id ?? object(params.turn).threadId ?? object(params.item).threadId)
    if (thread && thread !== conversationId) return []
    const method = text(request.method, 'Approval request')
    const command = contentText(params.command ?? params.reason ?? params.message)
    const decisionRequest = method === 'item/commandExecution/requestApproval' || method === 'item/fileChange/requestApproval' || method.includes('execCommandApproval') || method.includes('applyPatchApproval')
    const unsupported = !decisionRequest
    return [{ id: requestId, kind: 'approval', title: unsupported ? 'Codex input requested' : 'Approval requested', content: command || method, timestamp: 'Pending', state: 'pending', meta: { method, unsupported } } satisfies StreamEvent]
  })
}

export function notificationUpdate(raw: unknown, realtimeTranscriptId?: string): LiveUpdate | null {
  const envelope = object(raw)
  const method = text(envelope.method)
  const params = object(envelope.params)
  const threadId = text(params.threadId)
  const turn = object(params.turn)
  const turnId = text(params.turnId ?? turn.id) || undefined
  if (method === 'turn/started' && turnId) return { turn: { kind: 'started', turnId } }
  if (method === 'turn/completed' && turnId) {
    const status = text(turn.status)
    if (status === 'completed' || status === 'interrupted' || status === 'failed') {
      return { turn: { kind: 'completed', turnId, status, error: errorText(turn.error) } }
    }
  }
  if (method === 'error' && turnId) {
    return { turn: { kind: 'error', turnId, message: errorText(params.error) ?? 'Codex reported a turn error.', willRetry: params.willRetry === true } }
  }
  if (method === 'thread/realtime/sdp') return { realtime: { kind: 'sdp', threadId, sdp: text(params.sdp) } }
  if (method === 'thread/realtime/started') return { realtime: { kind: 'started', threadId } }
  if (method === 'thread/realtime/error') return { realtime: { kind: 'error', threadId, message: text(params.message, 'Realtime voice failed.') } }
  if (method === 'thread/realtime/closed') return { realtime: { kind: 'closed', threadId, reason: text(params.reason) || undefined } }
  if (method === 'thread/realtime/transcript/delta') {
    const role = text(params.role) === 'user' ? 'user' : 'assistant'
    return { event: { id: realtimeTranscriptId ?? `realtime-${role}`, kind: 'message', role, content: text(params.delta), timestamp: 'Now', state: 'running', append: true, meta: { realtime: true } } }
  }
  if (method === 'thread/realtime/transcript/done') {
    const role = text(params.role) === 'user' ? 'user' : 'assistant'
    return { event: { id: realtimeTranscriptId ?? `realtime-${role}`, kind: 'message', role, content: text(params.text), timestamp: 'Now', state: 'done', meta: { realtime: true } } }
  }
  if (method === 'webui/status') return { event: { id: `status-${Date.now()}`, kind: 'status', title: 'Local service', content: params.codexAvailable ? 'Codex CLI connected.' : text(params.error, 'Codex CLI is unavailable.'), timestamp: 'Now', state: params.codexAvailable ? 'done' : 'failed' } }
  if (method === 'webui/serverRequestResolved') return { event: { id: String(params.id), kind: 'approval', title: 'Request resolved', content: params.automatic ? 'Resolved automatically by the local service.' : 'Response sent to Codex.', timestamp: 'Now', state: 'done' } }
  if (method === 'item/agentMessage/delta') return { event: { id: String(params.itemId), kind: 'message', role: 'assistant', content: text(params.delta), timestamp: 'Now', state: 'running', append: true }, turn: { kind: 'delta', turnId } }
  if (method === 'item/plan/delta') return { event: { id: String(params.itemId), kind: 'reasoning', title: 'Plan', content: text(params.delta), timestamp: 'Now', state: 'running', append: true }, turn: { kind: 'activity', turnId } }
  if (method === 'item/reasoning/summaryTextDelta') return { event: { id: String(params.itemId), kind: 'reasoning', title: 'Reasoning summary', content: text(params.delta), timestamp: 'Now', state: 'running', append: true }, turn: { kind: 'activity', turnId } }
  if (method === 'item/reasoning/textDelta') return { event: { id: String(params.itemId), kind: 'reasoning', title: 'Reasoning', content: text(params.delta), timestamp: 'Now', state: 'running', append: true }, turn: { kind: 'activity', turnId } }
  if (method === 'item/commandExecution/outputDelta') return { event: { id: String(params.itemId), kind: 'command', title: 'Command output', content: text(params.delta), timestamp: 'Now', state: 'running', append: true }, turn: { kind: 'activity', turnId } }
  if (method === 'item/fileChange/outputDelta') return { event: { id: String(params.itemId), kind: 'file', title: 'Workspace changes', content: text(params.delta), timestamp: 'Now', state: 'running', append: true }, turn: { kind: 'activity', turnId } }
  if (method === 'thread/tokenUsage/updated') {
    const tokenUsage = object(params.tokenUsage ?? params.usage)
    const total = object(tokenUsage.total ?? tokenUsage.totalUsage)
    const used = number(total.totalTokens ?? total.total_tokens ?? tokenUsage.totalTokens)
    const contextWindow = number(tokenUsage.modelContextWindow ?? tokenUsage.model_context_window ?? params.modelContextWindow)
    return contextWindow > 0 ? { contextPercent: Math.min(100, Math.round((used / contextWindow) * 100)) } : null
  }
  if (method.toLowerCase().includes('approval')) {
    const decisionRequest = method === 'item/commandExecution/requestApproval' || method === 'item/fileChange/requestApproval' || method.includes('execCommandApproval') || method.includes('applyPatchApproval')
    return { event: { id: String(envelope.id ?? params.id ?? params.requestId ?? crypto.randomUUID()), kind: 'approval', title: decisionRequest ? 'Approval requested' : 'Codex input requested', content: contentText(params.reason ?? params.command ?? params) || method, timestamp: 'Now', state: 'pending', meta: { method, unsupported: !decisionRequest } } }
  }
  if (envelope.id !== undefined && method) return { event: { id: String(envelope.id), kind: 'approval', title: 'Codex input requested', content: contentText(params.prompt ?? params.message ?? params) || `${method} is not interactively supported by this UI yet.`, timestamp: 'Now', state: 'pending', meta: { method, unsupported: true } } }
  const candidate = params.item ?? params.message ?? params.event ?? params
  const normalized = normalizeItem(candidate, Date.now())
  if (!normalized) return null
  const item = object(candidate)
  const state = method === 'item/started' ? 'running' : method === 'item/completed' ? (item.status === 'failed' ? 'failed' : 'done') : normalized.state
  return { event: { ...normalized, state }, ...(method === 'item/started' || method === 'item/completed' ? { turn: { kind: 'activity' as const, turnId } } : {}) }
}

export async function loadBootstrap(): Promise<{ data: BootstrapPayload; connection: ConnectionState }> {
  try { return { data: normalizeBootstrap(await request<unknown>('/bootstrap')), connection: 'online' } }
  catch { return { data: demoBootstrap, connection: 'demo' } }
}

export async function loadEvents(conversationId: string, demoMode = false): Promise<StreamEvent[]> {
  return (await loadConversationSnapshot(conversationId, demoMode)).events
}

export async function loadConversationSnapshot(conversationId: string, demoMode = false): Promise<ConversationSnapshot> {
  try {
    const thread = await request<unknown>(`/threads/${encodeURIComponent(conversationId)}`)
    let approvals: StreamEvent[] = []
    try { approvals = pendingApprovals(await request<unknown>('/approvals'), conversationId) } catch { /* History remains authoritative if approval hydration fails. */ }
    return { events: [...eventsFromThread(thread), ...approvals], turn: normalizeThreadLifecycle(thread) }
  }
  catch {
    return {
      events: demoMode ? demoEvents : [{ id: `history-error-${conversationId}`, kind: 'status', title: 'History unavailable', content: 'The local service could not read this conversation. Retry after checking the Codex connection.', timestamp: 'Now', state: 'failed' }],
      turn: { phase: 'idle' },
    }
  }
}

export async function loadFile(path: string, demoMode = false): Promise<FileReadResult> {
  try { return { content: (await request<{ content: string }>(`/workspace/file?path=${encodeURIComponent(path)}`)).content } }
  catch (error) {
    if (demoMode) return { content: demoFileContents[path] ?? `// ${path}\n// Demo preview while the local service is offline.\n`, demo: true }
    return { content: '', error: error instanceof Error ? error.message : 'File preview unavailable' }
  }
}

export async function loadWorkspaceTree(path: string): Promise<WorkspaceFile[]> {
  return normalizeWorkspace(await request<unknown>(`/workspace/tree?path=${encodeURIComponent(path)}&depth=1`))
}

export async function loadWorkspaceChanges(path: string): Promise<WorkspaceChanges> {
  return normalizeWorkspaceChanges(await request<unknown>(`/workspace/changes?path=${encodeURIComponent(path)}`))
}

export async function loadBackgroundTerminals(conversationId: string): Promise<BackgroundTerminals> {
  return normalizeBackgroundTerminals(await request<unknown>(`/threads/${encodeURIComponent(conversationId)}/background-terminals`))
}

export async function saveFile(path: string, content: string): Promise<void> {
  await request(`/workspace/file?path=${encodeURIComponent(path)}`, { method: 'PUT', body: JSON.stringify({ content }) })
}

export async function sendPrompt(conversationId: string, prompt: string, model: string, effort: string): Promise<{ turnId?: string }> {
  await request(`/threads/${encodeURIComponent(conversationId)}/resume`, { method: 'POST', body: JSON.stringify({ model }) })
  const result = object(await request<unknown>(`/threads/${encodeURIComponent(conversationId)}/turns`, { method: 'POST', body: JSON.stringify({ input: prompt, model, effort }) }))
  const turn = object(result.turn ?? result)
  return { turnId: text(turn.id) || undefined }
}

export async function loadRealtimeCapability(conversationId: string): Promise<RealtimeCapability> {
  return request<RealtimeCapability>(`/threads/${encodeURIComponent(conversationId)}/realtime/capability`)
}

export async function createConversation(options: { projectId?: string; cwd?: string; model?: string } = {}): Promise<Conversation> {
  const raw = await request<unknown>('/threads', { method: 'POST', body: JSON.stringify({ cwd: options.cwd ?? '.', model: options.model }) })
  const conversation = normalizeConversation(raw, options.projectId)
  if (options.projectId && conversation.id) await request(`/threads/${encodeURIComponent(conversation.id)}/metadata`, { method: 'PATCH', body: JSON.stringify({ project_id: Number(options.projectId) }) })
  return conversation
}

export async function searchConversations(query: string): Promise<Conversation[]> {
  const result = await request<unknown>(`/threads?q=${encodeURIComponent(query)}&limit=100`)
  return array(object(result).data ?? result).map(thread => normalizeConversation(thread))
}

export async function assignConversationProject(conversationId: string, projectId: string): Promise<void> {
  await request(`/threads/${encodeURIComponent(conversationId)}/metadata`, { method: 'PATCH', body: JSON.stringify({ project_id: Number(projectId) }) })
}

export async function createProject(input: { name: string; description?: string; color?: string; workspace?: string }): Promise<Project> {
  return normalizeProject(await request<unknown>('/projects', { method: 'POST', body: JSON.stringify(input) }))
}

export async function createSchedule(input: { name: string; prompt: string; schedule_type: 'interval' | 'cron'; schedule: string; workspace: string; enabled: boolean }): Promise<Schedule> {
  return normalizeSchedule(await request<unknown>('/tasks', { method: 'POST', body: JSON.stringify(input) }))
}

export async function updateSchedule(scheduleId: string, input: { enabled?: boolean }): Promise<Schedule> {
  return normalizeSchedule(await request<unknown>(`/tasks/${encodeURIComponent(scheduleId)}`, { method: 'PATCH', body: JSON.stringify(input) }))
}

export async function runSchedule(scheduleId: string): Promise<void> { await request(`/tasks/${encodeURIComponent(scheduleId)}/run`, { method: 'POST' }) }

export async function importImages(files: File[]): Promise<ImageAsset[]> {
  return Promise.all(files.map(async file => {
    const body = new FormData(); body.append('file', file)
    const response = await fetch(`${API_BASE}/images`, { method: 'POST', body })
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
    return normalizeImage(await response.json())
  }))
}

export async function deleteImage(imageId: string): Promise<void> {
  await request(`/images/${encodeURIComponent(imageId)}`, { method: 'DELETE' })
}

export async function listImages(): Promise<ImageAsset[]> {
  const result = await request<unknown>('/images')
  return array(object(result).data ?? result).map(normalizeImage)
}

export async function respondApproval(_conversationId: string, eventId: string, approved: boolean, requestMethod = ''): Promise<void> {
  let response: unknown
  if (requestMethod.includes('execCommandApproval') || requestMethod.includes('applyPatchApproval')) response = { decision: approved ? 'approved' : { denied: { rejection: 'Denied in Web UI' } } }
  else if (requestMethod === 'item/commandExecution/requestApproval' || requestMethod === 'item/fileChange/requestApproval') response = { decision: approved ? 'accept' : 'decline' }
  else { await request(`/approvals/${encodeURIComponent(eventId)}/reject`, { method: 'POST' }); return }
  await request(`/approvals/${encodeURIComponent(eventId)}`, { method: 'POST', body: JSON.stringify({ response }) })
}

export async function listRealtimeVoices(): Promise<RealtimeVoicesList> {
  const result = object(await request<unknown>('/realtime/voices'))
  return object(result.voices) as unknown as RealtimeVoicesList
}

export async function startRealtimeVoice(
  conversationId: string,
  sdp: string,
  options: { voice?: RealtimeVoice; version?: WebRtcRealtimeVersion } = {},
): Promise<void> {
  await request(`/threads/${encodeURIComponent(conversationId)}/realtime/start`, {
    method: 'POST',
    body: JSON.stringify({ sdp, ...options }),
  })
}

export async function stopRealtimeVoice(conversationId: string): Promise<void> {
  await request(`/threads/${encodeURIComponent(conversationId)}/realtime/stop`, { method: 'POST' })
}

export async function requestUpdate(): Promise<void> { await request('/update', { method: 'POST' }) }

export function connectConversation(conversationId: string, onUpdate: (update: LiveUpdate) => void, onState: (state: ConnectionState) => void, onReconnect?: () => void): () => void {
  const base = import.meta.env.VITE_WS_BASE ?? `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
  const transcriptIds = new Map<string, string>()
  let socket: WebSocket | null = null
  let retryTimer: number | undefined
  let stopped = false
  let connectedBefore = false
  const open = () => {
    if (stopped) return
    try { socket = new WebSocket(`${base}/conversations/${encodeURIComponent(conversationId)}`) }
    catch { scheduleReconnect(); return }
    socket.onopen = () => {
      const reconnected = connectedBefore
      connectedBefore = true
      onState('online')
      if (reconnected) onReconnect?.()
    }
    socket.onmessage = message => {
      let payload: unknown
      try { payload = JSON.parse(message.data) } catch { return }
      const envelope = object(payload)
      const method = text(envelope.method)
      const role = text(object(envelope.params).role, 'assistant')
      let transcriptId: string | undefined
      if (method === 'thread/realtime/transcript/delta' || method === 'thread/realtime/transcript/done') {
        transcriptId = transcriptIds.get(role) ?? crypto.randomUUID()
        transcriptIds.set(role, transcriptId)
        if (method.endsWith('/done')) transcriptIds.delete(role)
      }
      const update = notificationUpdate(payload, transcriptId)
      if (update) onUpdate(update)
    }
    socket.onerror = () => onState('offline')
    socket.onclose = () => { if (!stopped) { onState('offline'); scheduleReconnect() } }
  }
  const scheduleReconnect = () => {
    if (stopped || retryTimer !== undefined) return
    retryTimer = window.setTimeout(() => { retryTimer = undefined; onState('connecting'); open() }, 1000)
  }
  open()
  return () => {
    stopped = true
    if (retryTimer !== undefined) window.clearTimeout(retryTimer)
    socket?.close()
  }
}
