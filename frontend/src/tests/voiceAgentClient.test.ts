import { afterEach, expect, test, vi } from 'vitest'

import { VoiceAgentClient } from '../voice/voiceAgentClient'

const options = {
  onStatus: vi.fn(),
  onUserTranscript: vi.fn(),
  onAgentTranscript: vi.fn(),
  onPendingAction: vi.fn(),
  onError: vi.fn(),
}

function tokenResponse() {
  return Promise.resolve({
    ok: true,
    json: async () => ({ token: 'test-token', agent_id: 'test-agent' }),
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test('reports unsupported microphone capture', async () => {
  vi.stubGlobal('fetch', vi.fn(tokenResponse))
  vi.stubGlobal('navigator', {})

  await expect(new VoiceAgentClient(options).connect()).rejects.toThrow(
    'Microphone capture is not supported in this browser',
  )
})

test('reports when no microphone input device exists', async () => {
  vi.stubGlobal('fetch', vi.fn(tokenResponse))
  vi.stubGlobal('navigator', {
    mediaDevices: {
      getUserMedia: vi.fn().mockRejectedValue(new DOMException('Missing', 'NotFoundError')),
    },
  })

  await expect(new VoiceAgentClient(options).connect()).rejects.toThrow(
    'No microphone input device was found',
  )
})
