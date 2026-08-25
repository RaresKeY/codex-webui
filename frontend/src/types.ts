export type View = 'chat' | 'projects' | 'schedules' | 'images' | 'settings'
export type ConnectionState = 'connecting' | 'online' | 'demo' | 'offline'
export type EventKind = 'message' | 'reasoning' | 'command' | 'file' | 'approval' | 'status'
export type VoiceState = 'idle' | 'connecting' | 'live' | 'stopping' | 'error' | 'unsupported'
export type TurnPhase = 'idle' | 'waiting' | 'streaming' | 'completed' | 'interrupted' | 'failed'

export interface TurnLifecycle {
  phase: TurnPhase
  turnId?: string
  requestId?: string
  error?: string
}

export type TurnSignal =
  | { kind: 'started'; turnId: string }
  | { kind: 'activity'; turnId?: string }
  | { kind: 'delta'; turnId?: string }
  | { kind: 'error'; turnId?: string; message: string; willRetry: boolean }
  | { kind: 'completed'; turnId: string; status: 'completed' | 'interrupted' | 'failed'; error?: string }

export interface RealtimeCapability {
  available: boolean
  reason?: string
}

export type RealtimeSignal =
  | { kind: 'sdp'; threadId: string; sdp: string }
  | { kind: 'started'; threadId: string }
  | { kind: 'closed'; threadId: string; reason?: string }
  | { kind: 'error'; threadId: string; message: string }

export interface Project {
  id: string
  name: string
  path: string
  color: string
  chatCount: number
  updatedAt: string
}

export interface Conversation {
  id: string
  projectId: string
  title: string
  preview: string
  updatedAt: string
  status: 'ready' | 'running' | 'paused' | 'failed'
  cwd: string
  model: string
  contextPercent: number
}

export interface StreamEvent {
  id: string
  kind: EventKind
  role?: 'user' | 'assistant' | 'system'
  title?: string
  content: string
  timestamp: string
  state?: 'pending' | 'running' | 'done' | 'failed'
  meta?: Record<string, string | number | boolean>
  append?: boolean
}

export interface WorkspaceFile {
  id: string
  name: string
  path: string
  type: 'file' | 'folder'
  language?: string
  status?: 'modified' | 'added' | 'deleted'
  children?: WorkspaceFile[]
}

export interface BackgroundTerminal {
  itemId: string
  processId: string
  command: string
  cwd: string
  osPid?: number
  cpuPercent?: number
  rssKb?: number
}

export interface BackgroundTerminals {
  items: BackgroundTerminal[]
  unavailableReason?: string
}

export interface WorkspaceChanges {
  files: WorkspaceFile[]
  repoRoot?: string
  truncated?: boolean
}

export interface Schedule {
  id: string
  name: string
  prompt: string
  cadence: string
  nextRun: string
  enabled: boolean
}

export interface Usage {
  fiveHourPercent: number | null
  weeklyPercent: number | null
  lifetimeTokens: number | null
  peakDailyTokens: number | null
  currentStreakDays: number | null
  resetsAt: string
}

export interface ImageAsset {
  id: string
  name: string
  url: string
  mime: string
  size: number
  modifiedAt: string
}

export interface BootstrapPayload {
  projects: Project[]
  conversations: Conversation[]
  files: WorkspaceFile[]
  schedules: Schedule[]
  usage: Usage
  models: string[]
  images: ImageAsset[]
  demo: boolean
  codexVersion?: string
  updatesEnabled: boolean
  realtimeVoice: boolean
  realtimeVoiceReason?: string
  runtime: 'localhost-companion' | 'container' | 'unknown'
}

export interface LiveUpdate {
  event?: StreamEvent
  turn?: TurnSignal
  contextPercent?: number
  conversationTitle?: string
  realtime?: RealtimeSignal
}

export interface ConversationSnapshot {
  events: StreamEvent[]
  turn: TurnLifecycle
}

export interface FileReadResult {
  content: string
  error?: string
  demo?: boolean
}
