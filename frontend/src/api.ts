import { demoBootstrap, demoEvents, demoFileContents } from './demo'
import type { BootstrapPayload, ConnectionState, Conversation, FileReadResult, ImageAsset, LiveUpdate, Project, Schedule, StreamEvent, Usage, WorkspaceFile } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'
type JsonObject = Record<string, unknown>

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function object(value: unknown): JsonObject { return value && typeof value === 'object' ? value as JsonObject : {} }
function array(value: unknown): unknown[] { return Array.isArray(value) ? value : [] }
function text(value: unknown, fallback = ''): string { return typeof value === 'string' ? value : fallback }
function number(value: unknown, fallback = 0): number { return typeof value === 'number' && Number.isFinite(value) ? value : fallback }
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
  const serverInfo = object(object(object(item.system).codex).server_info)
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
    codexVersion: text(serverInfo.version ?? serverInfo.codexVersion) || undefined,
    updatesEnabled: features.updates === true,
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
  if (type.includes('user')) return { id, kind: 'message', role: 'user', content: contentText(item.content ?? item.message ?? item.input), timestamp }
  if (type.includes('agent') || type.includes('assistant') || type === 'message') return { id, kind: 'message', role: 'assistant', content: contentText(item.text ?? item.content ?? item.message ?? item.output), timestamp }
  if (type === 'plan' || type.includes('plan')) return { id, kind: 'reasoning', title: 'Plan', content: contentText(item.text ?? item.content), timestamp, state: 'done' }
  if (type.includes('reason')) return { id, kind: 'reasoning', title: 'Reasoning summary', content: contentText(item.summary ?? item.content), timestamp, state: 'done' }
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

export function notificationUpdate(raw: unknown): LiveUpdate | null {
  const envelope = object(raw)
  const method = text(envelope.method)
  const params = object(envelope.params)
  if (method === 'webui/status') return { event: { id: `status-${Date.now()}`, kind: 'status', title: 'Local service', content: params.codexAvailable ? 'Codex CLI connected.' : text(params.error, 'Codex CLI is unavailable.'), timestamp: 'Now', state: params.codexAvailable ? 'done' : 'failed' } }
  if (method === 'webui/serverRequestResolved') return { event: { id: String(params.id), kind: 'approval', title: 'Request resolved', content: params.automatic ? 'Resolved automatically by the local service.' : 'Response sent to Codex.', timestamp: 'Now', state: 'done' } }
  if (method === 'item/agentMessage/delta') return { event: { id: String(params.itemId), kind: 'message', role: 'assistant', content: text(params.delta), timestamp: 'Now', state: 'running', append: true } }
  if (method === 'item/plan/delta') return { event: { id: String(params.itemId), kind: 'reasoning', title: 'Plan', content: text(params.delta), timestamp: 'Now', state: 'running', append: true } }
  if (method === 'item/reasoning/summaryTextDelta') return { event: { id: String(params.itemId), kind: 'reasoning', title: 'Reasoning summary', content: text(params.delta), timestamp: 'Now', state: 'running', append: true } }
  if (method === 'item/reasoning/textDelta') return { event: { id: String(params.itemId), kind: 'reasoning', title: 'Reasoning', content: text(params.delta), timestamp: 'Now', state: 'running', append: true } }
  if (method === 'item/commandExecution/outputDelta') return { event: { id: String(params.itemId), kind: 'command', title: 'Command output', content: text(params.delta), timestamp: 'Now', state: 'running', append: true } }
  if (method === 'item/fileChange/outputDelta') return { event: { id: String(params.itemId), kind: 'file', title: 'Workspace changes', content: text(params.delta), timestamp: 'Now', state: 'running', append: true } }
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
  return { event: { ...normalized, state } }
}

export async function loadBootstrap(): Promise<{ data: BootstrapPayload; connection: ConnectionState }> {
  try { return { data: normalizeBootstrap(await request<unknown>('/bootstrap')), connection: 'online' } }
  catch { return { data: demoBootstrap, connection: 'demo' } }
}

export async function loadEvents(conversationId: string, demoMode = false): Promise<StreamEvent[]> {
  try {
    const thread = await request<unknown>(`/threads/${encodeURIComponent(conversationId)}`)
    let approvals: StreamEvent[] = []
    try { approvals = pendingApprovals(await request<unknown>('/approvals'), conversationId) } catch { /* History remains authoritative if approval hydration fails. */ }
    return [...eventsFromThread(thread), ...approvals]
  }
  catch { return demoMode ? demoEvents : [{ id: `history-error-${conversationId}`, kind: 'status', title: 'History unavailable', content: 'The local service could not read this conversation. Retry after checking the Codex connection.', timestamp: 'Now', state: 'failed' }] }
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

export async function saveFile(path: string, content: string): Promise<void> {
  await request(`/workspace/file?path=${encodeURIComponent(path)}`, { method: 'PUT', body: JSON.stringify({ content }) })
}

export async function sendPrompt(conversationId: string, prompt: string, model: string, effort: string): Promise<void> {
  await request(`/threads/${encodeURIComponent(conversationId)}/resume`, { method: 'POST', body: JSON.stringify({ model }) })
  await request(`/threads/${encodeURIComponent(conversationId)}/turns`, { method: 'POST', body: JSON.stringify({ input: prompt, model, effort }) })
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
  else if (requestMethod === 'item/permissions/requestApproval') response = { permissions: {}, scope: 'turn' }
  else if (requestMethod.includes('requestUserInput')) response = { answers: {} }
  else if (requestMethod.includes('elicitation')) response = { action: 'cancel' }
  else if (requestMethod === 'item/tool/call' || requestMethod.includes('dynamicTool')) response = { success: false, contentItems: [{ type: 'inputText', text: 'Declined in Web UI' }] }
  else if (requestMethod === 'item/commandExecution/requestApproval' || requestMethod === 'item/fileChange/requestApproval') response = { decision: approved ? 'accept' : 'decline' }
  else { await request(`/approvals/${encodeURIComponent(eventId)}/reject`, { method: 'POST' }); return }
  await request(`/approvals/${encodeURIComponent(eventId)}`, { method: 'POST', body: JSON.stringify({ response }) })
}

export async function requestUpdate(): Promise<void> { await request('/update', { method: 'POST' }) }

export function connectConversation(conversationId: string, onUpdate: (update: LiveUpdate) => void, onState: (state: ConnectionState) => void): () => void {
  const base = import.meta.env.VITE_WS_BASE ?? `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
  try {
    const socket = new WebSocket(`${base}/conversations/${encodeURIComponent(conversationId)}`)
    socket.onopen = () => onState('online')
    socket.onmessage = message => { const update = notificationUpdate(JSON.parse(message.data)); if (update) onUpdate(update) }
    socket.onerror = () => onState('offline')
    socket.onclose = () => onState('offline')
    return () => socket.close()
  } catch { onState('offline'); return () => undefined }
}
