import { startRealtimeVoice, stopRealtimeVoice } from './api'
import type { RealtimeSignal, VoiceState } from './types'

type StateListener = (state: VoiceState, message?: string) => void

export function realtimeFailureMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error ?? '')
  const normalized = message.toLowerCase()
  if (normalized.includes('does not support realtime conversation') || normalized.includes('not enabled for this codex conversation')) {
    return 'Realtime voice is not enabled for this Codex conversation.'
  }
  if (normalized.includes('api key auth') || normalized.includes('api-key-backed')) {
    return 'Codex rejected realtime authentication for this conversation. The browser never receives account credentials.'
  }
  if (normalized.includes('permission denied') || normalized.includes('notallowederror')) {
    return 'Microphone access was denied. Allow microphone access for this localhost client and try again.'
  }
  if (normalized.includes('502') || normalized.includes('bad gateway')) {
    return 'Codex App Server rejected the realtime voice session. Check this conversation’s voice availability and try again.'
  }
  return message || 'Realtime voice could not start.'
}

/** Browser-owned WebRTC leg for the public thread/realtime App Server API. */
export class RealtimeVoiceSession {
  private peer: RTCPeerConnection | null = null
  private microphone: MediaStream | null = null
  private audio: HTMLAudioElement | null = null
  private threadId: string | null = null

  constructor(private readonly onState: StateListener) {}

  get supported(): boolean {
    return typeof RTCPeerConnection !== 'undefined'
      && typeof navigator !== 'undefined'
      && Boolean(navigator.mediaDevices?.getUserMedia)
  }

  async start(threadId: string): Promise<void> {
    if (!this.supported) {
      this.onState('unsupported', 'This browser cannot open a WebRTC microphone session.')
      return
    }
    this.closeLocal()
    this.threadId = threadId
    this.onState('connecting')
    try {
      const peer = new RTCPeerConnection()
      const audio = new Audio()
      audio.autoplay = true
      peer.ontrack = event => {
        audio.srcObject = event.streams[0]
        void audio.play().catch(() => undefined)
      }
      peer.onconnectionstatechange = () => {
        if (peer.connectionState === 'connected') this.onState('live')
        if (peer.connectionState === 'failed') {
          this.onState('error', 'The realtime WebRTC connection failed.')
          this.closeLocal()
        }
      }

      const microphone = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      })
      const track = microphone.getAudioTracks()[0]
      if (!track) throw new Error('No microphone audio track was returned.')
      peer.addTrack(track, microphone)
      peer.createDataChannel('oai-events')

      this.peer = peer
      this.microphone = microphone
      this.audio = audio
      const offer = await peer.createOffer()
      await peer.setLocalDescription(offer)
      const sdp = offer.sdp
      if (!sdp) throw new Error('The browser did not produce an SDP offer.')
      // v3 is the documented WebRTC-capable Frameless Bidi protocol. v2 is
      // intentionally excluded because App Server rejects it for WebRTC.
      await startRealtimeVoice(threadId, sdp, { version: 'v3' })
    } catch (error) {
      this.closeLocal()
      this.onState('error', realtimeFailureMessage(error))
      throw error
    }
  }

  async handle(signal: RealtimeSignal): Promise<void> {
    if (!this.threadId || signal.threadId !== this.threadId) return
    if (signal.kind === 'sdp') {
      if (!signal.sdp || !this.peer) return
      await this.peer.setRemoteDescription({ type: 'answer', sdp: signal.sdp })
      return
    }
    if (signal.kind === 'error') {
      this.onState('error', realtimeFailureMessage(new Error(signal.message)))
      this.closeLocal()
      return
    }
    if (signal.kind === 'closed') {
      this.closeLocal()
      this.onState('idle', signal.reason)
    }
  }

  async stop(notifyServer = true): Promise<void> {
    const threadId = this.threadId
    if (!threadId) {
      this.closeLocal()
      this.onState('idle')
      return
    }
    this.onState('stopping')
    try {
      if (notifyServer) await stopRealtimeVoice(threadId)
    } finally {
      this.closeLocal()
      this.onState('idle')
    }
  }

  private closeLocal(): void {
    this.microphone?.getTracks().forEach(track => track.stop())
    this.peer?.close()
    if (this.audio) this.audio.srcObject = null
    this.microphone = null
    this.peer = null
    this.audio = null
    this.threadId = null
  }
}
