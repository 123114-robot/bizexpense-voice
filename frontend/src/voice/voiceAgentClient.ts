export type VoiceStatus = 'idle' | 'connecting' | 'ready' | 'listening' | 'processing' | 'confirmation_required' | 'success' | 'error'

import { type PendingVoiceAction, voiceToolAdapter } from './voiceToolAdapter'
import { api } from '../services/api'

export type { PendingVoiceAction } from './voiceToolAdapter'

type VoiceAgentOptions = {
  onStatus: (status: VoiceStatus) => void
  onUserTranscript: (text: string, partial: boolean) => void
  onAgentTranscript: (text: string) => void
  onPendingAction: (action: PendingVoiceAction) => void
  onError: (message: string) => void
}

type ToolCall = {
  type: 'tool.call'
  call_id: string
  name: string
  arguments: Record<string, unknown>
}

type ToolResult = { callId: string; result: unknown }

function messageFromUnknown(error: unknown) {
  return error instanceof Error ? error.message : 'Voice assistant failed'
}

function bytesToBase64(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let index = 0; index < bytes.length; index += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000))
  }
  return btoa(binary)
}

export class VoiceAgentClient {
  private options: VoiceAgentOptions
  private socket?: WebSocket
  private audioContext?: AudioContext
  private stream?: MediaStream
  private playbackTime = 0
  private playbackSources = new Set<AudioBufferSourceNode>()
  private pendingToolResults: ToolResult[] = []
  private ready = false

  constructor(options: VoiceAgentOptions) {
    this.options = options
  }

  async connect() {
    this.options.onStatus('connecting')
    const { token, agent_id: agentId } = await api<{ token: string; agent_id: string | null }>('/voice/token')
    if (!agentId) throw new Error('ASSEMBLYAI_AGENT_ID is not configured')

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      })
    } catch (error) {
      throw new Error('Microphone permission denied', { cause: error })
    }

    this.audioContext = new AudioContext({ sampleRate: 24000 })
    await this.audioContext.audioWorklet.addModule('/pcm-processor.js')
    const source = this.audioContext.createMediaStreamSource(this.stream)
    const worklet = new AudioWorkletNode(this.audioContext, 'pcm-processor')
    const silentOutput = this.audioContext.createGain()
    silentOutput.gain.value = 0
    source.connect(worklet).connect(silentOutput).connect(this.audioContext.destination)

    const url = new URL('wss://agents.assemblyai.com/v1/ws')
    url.searchParams.set('token', token)
    this.socket = new WebSocket(url)
    worklet.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
      if (this.ready && this.socket?.readyState === WebSocket.OPEN) {
        this.send({ type: 'input.audio', audio: bytesToBase64(event.data) })
      }
    }
    this.socket.addEventListener('open', () => {
      this.send({ type: 'session.update', session: { agent_id: agentId } })
    })
    this.socket.addEventListener('message', (event) => {
      void this.handleEvent(JSON.parse(String(event.data)) as Record<string, unknown>)
    })
    this.socket.addEventListener('error', () => this.options.onError('AssemblyAI WebSocket connection failed'))
    this.socket.addEventListener('close', () => {
      if (this.ready) this.options.onError('AssemblyAI voice session disconnected')
      this.ready = false
    })
  }

  disconnect() {
    this.ready = false
    this.socket?.close()
    this.stream?.getTracks().forEach(track => track.stop())
    void this.audioContext?.close()
    this.flushPlayback()
    this.options.onStatus('idle')
  }

  private send(payload: unknown) {
    this.socket?.send(JSON.stringify(payload))
  }

  private async handleEvent(event: Record<string, unknown>) {
    switch (event.type) {
      case 'session.ready':
        this.ready = true
        this.options.onStatus('ready')
        break
      case 'input.speech.started':
        this.flushPlayback()
        this.options.onStatus('listening')
        break
      case 'input.speech.stopped':
      case 'reply.started':
        this.options.onStatus('processing')
        break
      case 'transcript.user.delta':
        this.options.onUserTranscript(String(event.text || ''), true)
        break
      case 'transcript.user':
        this.options.onUserTranscript(String(event.text || ''), false)
        break
      case 'transcript.agent':
        this.options.onAgentTranscript(String(event.text || ''))
        break
      case 'reply.audio':
        this.playAudio(String(event.data || ''))
        break
      case 'tool.call':
        await this.runTool(event as ToolCall)
        break
      case 'reply.done':
        if (event.status === 'interrupted') {
          this.pendingToolResults = []
          this.flushPlayback()
        } else {
          this.flushToolResults()
          this.options.onStatus('ready')
        }
        break
      case 'session.error':
        this.options.onError(String(event.message || 'AssemblyAI session error'))
        break
    }
  }

  private async runTool(call: ToolCall) {
    let result: unknown
    try {
      result = await voiceToolAdapter.callTool(call.name, call.arguments)
      if ((result as PendingVoiceAction).status === 'confirmation_required') {
        this.options.onPendingAction(result as PendingVoiceAction)
        this.options.onStatus('confirmation_required')
      }
    } catch (error) {
      result = { error: messageFromUnknown(error) }
    }
    this.pendingToolResults.push({ callId: call.call_id, result })
  }

  private flushToolResults() {
    for (const item of this.pendingToolResults.splice(0)) {
      this.send({ type: 'tool.result', call_id: item.callId, result: JSON.stringify(item.result) })
    }
  }

  private playAudio(base64: string) {
    if (!this.audioContext || !base64) return
    const binary = atob(base64)
    const samples = new Int16Array(binary.length / 2)
    for (let index = 0; index < samples.length; index++) {
      samples[index] = binary.charCodeAt(index * 2) | (binary.charCodeAt(index * 2 + 1) << 8)
    }
    const buffer = this.audioContext.createBuffer(1, samples.length, 24000)
    const channel = buffer.getChannelData(0)
    for (let index = 0; index < samples.length; index++) channel[index] = samples[index] / 32768
    const source = this.audioContext.createBufferSource()
    source.buffer = buffer
    source.connect(this.audioContext.destination)
    this.playbackTime = Math.max(this.playbackTime, this.audioContext.currentTime)
    source.start(this.playbackTime)
    this.playbackTime += buffer.duration
    this.playbackSources.add(source)
    source.onended = () => this.playbackSources.delete(source)
  }

  private flushPlayback() {
    this.playbackSources.forEach(source => {
      try { source.stop() } catch { /* already stopped */ }
    })
    this.playbackSources.clear()
    this.playbackTime = this.audioContext?.currentTime || 0
  }
}
