import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import { VoiceAssistant } from '../voice/VoiceAssistant'

const connect = vi.fn()
const disconnect = vi.fn()
let clientOptions: Record<string, (...args: unknown[]) => void>

vi.mock('../voice/voiceAgentClient', () => ({
  VoiceAgentClient: class {
    constructor(options: Record<string, (...args: unknown[]) => void>) {
      clientOptions = options
    }
    connect = connect
    disconnect = disconnect
  },
}))

afterEach(() => {
  vi.clearAllMocks()
  vi.unstubAllGlobals()
})

test('VoiceAssistant renders', () => {
  render(<VoiceAssistant onMutation={vi.fn()} />)

  expect(screen.getByRole('heading', { name: 'BizExpense Voice' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Start voice assistant' })).toBeInTheDocument()
})

test('confirmation button executes a pending action once', async () => {
  connect.mockImplementation(async () => {
    clientOptions.onStatus('ready')
    clientOptions.onPendingAction({
      status: 'confirmation_required',
      pending_action_id: 'pending-1',
      action: 'create_expense',
      preview: {
        supplier_name: 'Woolworths',
        amount: '38.50',
        invoice_date: '2026-09-30',
        category_name: 'Other',
        currency: 'AUD',
      },
    })
  })
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ status: 'executed' }),
  })
  vi.stubGlobal('fetch', fetchMock)
  const onMutation = vi.fn()
  render(<VoiceAssistant onMutation={onMutation} />)

  await userEvent.click(screen.getByRole('button', { name: 'Start voice assistant' }))
  const confirm = await screen.findByRole('button', { name: 'Confirm' })
  await userEvent.dblClick(confirm)

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
  expect(fetchMock).toHaveBeenCalledWith('/api/voice/actions/pending-1/confirm', { method: 'POST' })
  expect(onMutation).toHaveBeenCalledTimes(1)
})

test('error state renders', async () => {
  connect.mockRejectedValueOnce(new Error('Microphone permission denied'))
  render(<VoiceAssistant onMutation={vi.fn()} />)

  await userEvent.click(screen.getByRole('button', { name: 'Start voice assistant' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('Microphone permission denied')
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
})
