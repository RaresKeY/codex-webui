import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('./api', () => ({
  startRealtimeVoice: vi.fn().mockResolvedValue(undefined),
  stopRealtimeVoice: vi.fn().mockResolvedValue(undefined),
}))

import { startRealtimeVoice, stopRealtimeVoice } from './api'
import { RealtimeVoiceSession, realtimeFailureMessage } from './realtime'

class FakePeerConnection {
  connectionState: RTCPeerConnectionState = 'new'
  localDescription: RTCSessionDescription | null = null
  onconnectionstatechange: (() => void) | null = null
  ontrack: ((event: RTCTrackEvent) => void) | null = null
  dataChannel = ''
  remoteDescription: RTCSessionDescriptionInit | null = null

  addTrack(): RTCRtpSender { return {} as RTCRtpSender }
  close(): void { this.connectionState = 'closed' }
  createDataChannel(label: string): RTCDataChannel { this.dataChannel = label; return {} as RTCDataChannel }
  async createOffer(): Promise<RTCSessionDescriptionInit> { return { type: 'offer', sdp: 'v=0\r\no=browser-offer' } }
  async setLocalDescription(description: RTCSessionDescriptionInit): Promise<void> { this.localDescription = description as RTCSessionDescription }
  async setRemoteDescription(description: RTCSessionDescriptionInit): Promise<void> { this.remoteDescription = description }
}

describe('RealtimeVoiceSession', () => {
  afterEach(() => vi.clearAllMocks())

  it('uses the documented WebRTC offer, oai-events channel, and v3 App Server start', async () => {
    const track = { stop: vi.fn() } as unknown as MediaStreamTrack
    const stream = { getAudioTracks: () => [track], getTracks: () => [track] } as unknown as MediaStream
    const peers: FakePeerConnection[] = []
    Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: { getUserMedia: vi.fn().mockResolvedValue(stream) } } })
    Object.defineProperty(globalThis, 'RTCPeerConnection', { configurable: true, value: class extends FakePeerConnection { constructor() { super(); peers.push(this) } } })
    Object.defineProperty(globalThis, 'Audio', { configurable: true, value: class { autoplay = false; srcObject: MediaStream | null = null; play = vi.fn().mockResolvedValue(undefined) } })
    const states: string[] = []
    const session = new RealtimeVoiceSession(state => states.push(state))

    await session.start('thread-voice')

    const peer = peers[0]
    expect(peer.dataChannel).toBe('oai-events')
    expect(startRealtimeVoice).toHaveBeenCalledWith(
      'thread-voice',
      'v=0\r\no=browser-offer',
      { version: 'v3' },
    )
    await session.handle({ kind: 'sdp', threadId: 'thread-voice', sdp: 'v=0\r\no=server-answer' })
    expect(peer.remoteDescription).toEqual({ type: 'answer', sdp: 'v=0\r\no=server-answer' })
    await session.stop()
    expect(stopRealtimeVoice).toHaveBeenCalledWith('thread-voice')
    expect(track.stop).toHaveBeenCalled()
    expect(states).toContain('connecting')
  })

  it('turns protocol and permission failures into actionable voice messages', () => {
    expect(realtimeFailureMessage(new Error('thread abc does not support realtime conversation'))).toBe(
      'Realtime voice is not enabled for this Codex conversation.',
    )
    expect(realtimeFailureMessage(new Error('realtime conversation requires API key auth'))).toBe(
      'Codex rejected realtime authentication for this conversation. The browser never receives account credentials.',
    )
    expect(realtimeFailureMessage(new Error('Permission denied'))).toContain('Allow microphone access')
  })

  it('releases the microphone and reports a friendly state when App Server rejects startup', async () => {
    const track = { stop: vi.fn() } as unknown as MediaStreamTrack
    const stream = { getAudioTracks: () => [track], getTracks: () => [track] } as unknown as MediaStream
    Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: { getUserMedia: vi.fn().mockResolvedValue(stream) } } })
    Object.defineProperty(globalThis, 'RTCPeerConnection', { configurable: true, value: FakePeerConnection })
    Object.defineProperty(globalThis, 'Audio', { configurable: true, value: class { autoplay = false; srcObject: MediaStream | null = null; play = vi.fn().mockResolvedValue(undefined) } })
    vi.mocked(startRealtimeVoice).mockRejectedValueOnce(new Error('thread abc does not support realtime conversation'))
    const states: Array<[string, string | undefined]> = []
    const session = new RealtimeVoiceSession((state, message) => states.push([state, message]))

    await expect(session.start('thread-voice')).rejects.toThrow()

    expect(track.stop).toHaveBeenCalled()
    expect(states.at(-1)).toEqual(['error', 'Realtime voice is not enabled for this Codex conversation.'])
  })
})
