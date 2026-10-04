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

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('VoiceAssistant renders', () => {
  render(<VoiceAssistant onMutation={vi.fn()} />)

  expect(screen.getByRole('heading', { name: 'BizExpense Voice' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Start voice assistant' })).toBeInTheDocument()
  expect(screen.getByText('Prototype demo — mock voice input')).toBeInTheDocument()
})

test('mock query uses the BizExpense voice tool adapter', async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      total_expenses: '120.00',
      expenses_this_month: '38.50',
      gst_paid: '0.00',
      category_breakdown: [],
    }),
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<VoiceAssistant onMutation={vi.fn()} />)

  await userEvent.click(screen.getByRole('button', { name: 'Demo query' }))

  expect(await screen.findByText('Mock voice mode')).toBeInTheDocument()
  expect(screen.getByText(/How much did I spend this month/)).toBeInTheDocument()
  expect(screen.getByText(/\$38.50 in confirmed expenses this month/)).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith('/api/voice/tools/summary', expect.objectContaining({ method: 'POST' }))
})

test('mock search queries confirmed expenses by supplier', async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      count: 1,
      expenses: [{ supplier_name: 'Woolworths', total_amount: '38.50', invoice_date: '2026-09-30' }],
    }),
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<VoiceAssistant onMutation={vi.fn()} />)

  await userEvent.click(screen.getByRole('button', { name: 'Demo search' }))

  expect(await screen.findByText(/Woolworths expense for \$38.50/)).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    '/api/voice/tools/search-expenses',
    expect.objectContaining({ method: 'POST' }),
  )
})

test('mock category update targets the spoken supplier', async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      status: 'confirmation_required',
      pending_action_id: 'pending-category',
      action: 'update_expense',
      preview: {
        supplier_name: 'Woolworths',
        current_category: 'Other',
        proposed_category: 'Office Supplies',
      },
    }),
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<VoiceAssistant onMutation={vi.fn()} />)

  await userEvent.click(screen.getByRole('button', { name: 'Demo category update' }))

  expect(await screen.findByText(/prepared the Woolworths category change/i)).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    '/api/voice/tools/prepare-update',
    expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ category_name: 'Office Supplies', search: 'Woolworths' }),
    }),
  )
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
  expect(fetchMock).toHaveBeenCalledWith(
    '/api/voice/actions/pending-1/confirm',
    expect.objectContaining({ method: 'POST' }),
  )
  expect(onMutation).toHaveBeenCalledTimes(1)
})

test('error state renders', async () => {
  connect.mockRejectedValueOnce(new Error('Microphone permission denied'))
  render(<VoiceAssistant onMutation={vi.fn()} />)

  await userEvent.click(screen.getByRole('button', { name: 'Start voice assistant' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('Microphone permission denied')
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  expect(disconnect).toHaveBeenCalledTimes(1)
})

test('mock demo disconnects a live microphone session', async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      total_expenses: '120.00',
      expenses_this_month: '38.50',
      gst_paid: '0.00',
      category_breakdown: [],
    }),
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<VoiceAssistant onMutation={vi.fn()} />)

  await userEvent.click(screen.getByRole('button', { name: 'Start voice assistant' }))
  await userEvent.click(screen.getByRole('button', { name: 'Demo query' }))

  expect(disconnect).toHaveBeenCalledTimes(1)
  expect(await screen.findByText('Mock voice mode')).toBeInTheDocument()
})
