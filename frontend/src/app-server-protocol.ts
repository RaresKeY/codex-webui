// Curated from `codex app-server generate-ts --experimental` using
// codex-cli 0.147.0. Keep this subset aligned with the generated
// schema; `tools/generate-app-server-schema.sh` regenerates the source bundle.

export const APP_SERVER_SCHEMA_VERSION = 'codex-cli 0.147.0'

export type RealtimeVoice =
  | 'alloy' | 'arbor' | 'ash' | 'ballad' | 'breeze' | 'cedar' | 'coral' | 'cove'
  | 'echo' | 'ember' | 'juniper' | 'maple' | 'marin' | 'sage' | 'shimmer' | 'sol'
  | 'spruce' | 'vale' | 'verse'

export type WebRtcRealtimeVersion = 'v1' | 'v3'

export interface ThreadRealtimeStartTransport {
  type: 'webrtc'
  sdp: string
}

export interface ThreadRealtimeStartParams {
  threadId: string
  outputModality: 'audio'
  transport: ThreadRealtimeStartTransport
  voice?: RealtimeVoice
  version?: WebRtcRealtimeVersion
  model?: string
  includeStartupContext?: boolean
}

export interface ThreadRealtimeSdpNotification {
  threadId: string
  sdp: string
}

export interface RealtimeVoicesList {
  v1: RealtimeVoice[]
  v2: RealtimeVoice[]
  defaultV1: RealtimeVoice
  defaultV2: RealtimeVoice
}

export type TurnStatus = 'completed' | 'interrupted' | 'failed' | 'inProgress'

export interface TurnError {
  message: string
  additionalDetails: string | null
}

export interface TurnLifecycleRecord {
  id: string
  status: TurnStatus
  error: TurnError | null
}

export interface TurnStartedNotification {
  threadId: string
  turn: TurnLifecycleRecord
}

export interface TurnCompletedNotification {
  threadId: string
  turn: TurnLifecycleRecord
}

export interface AgentMessageDeltaNotification {
  threadId: string
  turnId: string
  itemId: string
  delta: string
}

export interface ExperimentalFeature {
  name: string
  enabled: boolean
  defaultEnabled: boolean
}

export interface ExperimentalFeatureListResponse {
  data: ExperimentalFeature[]
  nextCursor: string | null
}

export interface ThreadBackgroundTerminalsListParams {
  threadId: string
  cursor?: string | null
  limit?: number | null
}

export interface ThreadBackgroundTerminal {
  itemId: string
  processId: string
  command: string
  cwd: string
  osPid: number | null
  cpuPercent: number | null
  rssKb: bigint | null
}

export interface ThreadBackgroundTerminalsListResponse {
  data: ThreadBackgroundTerminal[]
  nextCursor: string | null
}

export type CurrentApprovalMethod =
  | 'item/commandExecution/requestApproval'
  | 'item/fileChange/requestApproval'

export type SingleUseApprovalDecision = 'accept' | 'decline' | 'cancel'
