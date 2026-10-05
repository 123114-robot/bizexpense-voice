import { useEffect, useRef, useState } from 'react'

import { VoiceAgentClient, type PendingVoiceAction, type VoiceStatus } from './voiceAgentClient'
import { type VoiceCategories, type VoiceSearchResult, type VoiceSummary, voiceToolAdapter } from './voiceToolAdapter'

type Props = { onMutation: () => void }

const statusLabels: Record<VoiceStatus | 'executing', string> = {
  idle: 'Idle',
  connecting: 'Connecting',
  ready: 'Ready',
  listening: 'Listening',
  processing: 'Processing',
  confirmation_required: 'Needs confirmation',
  executing: 'Saving',
  success: 'Success',
  error: 'Error',
}

export function VoiceAssistant({ onMutation }: Props) {
  const client = useRef<VoiceAgentClient | undefined>(undefined)
  const executing = useRef(false)
  const [status, setStatus] = useState<VoiceStatus | 'executing'>('idle')
  const [userTranscript, setUserTranscript] = useState('')
  const [agentTranscript, setAgentTranscript] = useState('')
  const [pending, setPending] = useState<PendingVoiceAction>()
  const [error, setError] = useState('')
  const [mockMode, setMockMode] = useState(false)

  useEffect(() => () => client.current?.disconnect(), [])

  const start = async () => {
    setMockMode(false)
    setError('')
    client.current?.disconnect()
    const next = new VoiceAgentClient({
      onStatus: setStatus,
      onUserTranscript: (text) => setUserTranscript(text),
      onAgentTranscript: setAgentTranscript,
      onPendingAction: setPending,
      onError: (message) => { setError(message); setStatus('error') },
    })
    client.current = next
    try {
      await next.connect()
    } catch (caught) {
      next.disconnect()
      setError(caught instanceof Error ? caught.message : 'Unable to start voice assistant')
      setStatus('error')
    }
  }

  const stop = () => {
    client.current?.disconnect()
    client.current = undefined
    setMockMode(false)
    setError('')
    setStatus('idle')
    setAgentTranscript('Voice session stopped.')
  }

  const runPrototype = async (action: 'create' | 'summary' | 'search' | 'categories' | 'update') => {
    client.current?.disconnect()
    setMockMode(true)
    setError('')
    setPending(undefined)
    setStatus('processing')
    const examples = {
      create: 'I spent $38.50 at Woolworths today.',
      summary: 'How much did I spend this month?',
      search: 'Show my Woolworths expenses.',
      categories: 'What expense categories can I use?',
      update: 'Classify my Woolworths expense as office supplies.',
    }
    setUserTranscript(examples[action])
    try {
      if (action === 'summary') {
        const summary = await voiceToolAdapter.callTool('get_expense_summary', {}) as VoiceSummary
        setAgentTranscript(`You have recorded $${summary.expenses_this_month} in confirmed expenses this month.`)
        setStatus('success')
        return
      }
      if (action === 'search') {
        const result = await voiceToolAdapter.callTool(
          'search_expenses',
          { search: 'Woolworths' },
        ) as VoiceSearchResult
        const first = result.expenses[0]
        setAgentTranscript(first
          ? `I found ${first.supplier_name} expense for $${first.total_amount} on ${first.invoice_date}.`
          : 'I found no confirmed Woolworths expenses.')
        setStatus('success')
        return
      }
      if (action === 'categories') {
        const result = await voiceToolAdapter.callTool(
          'list_expense_categories',
          {},
        ) as VoiceCategories
        const last = result.categories.at(-1)
        const leading = result.categories.slice(0, -1).join(', ')
        setAgentTranscript(`Available categories are ${leading}${leading ? ', and ' : ''}${last ?? 'none'}.`)
        setStatus('success')
        return
      }
      const result = await voiceToolAdapter.callTool(
        action === 'create' ? 'prepare_expense' : 'prepare_expense_update',
        action === 'create'
          ? { supplier_name: 'Woolworths', amount: 38.5, invoice_date: 'today' }
          : { category_name: 'Office Supplies', search: 'Woolworths' },
      ) as PendingVoiceAction
      setPending(result)
      setAgentTranscript(action === 'create'
        ? 'I found $38.50 at Woolworths for today. Please confirm.'
        : 'I prepared the Woolworths category change. Please confirm.')
      setStatus('confirmation_required')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Prototype action failed')
      setStatus('error')
    }
  }

  const confirm = async () => {
    if (!pending || executing.current) return
    executing.current = true
    setStatus('executing')
    setError('')
    try {
      await voiceToolAdapter.confirm(pending.pending_action_id)
      setPending(undefined)
      setStatus('success')
      setAgentTranscript('Expense saved. Your dashboard is up to date.')
      onMutation()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to save expense')
      setStatus('error')
    } finally {
      executing.current = false
    }
  }

  const cancel = async () => {
    if (!pending) return
    setError('')
    try {
      await voiceToolAdapter.cancel(pending.pending_action_id)
      setPending(undefined)
      setStatus('ready')
      setAgentTranscript('Cancelled. Nothing was saved.')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to cancel pending action')
      setStatus('error')
    }
  }

  const preview = pending?.preview
  return <section className="card mb-6" aria-labelledby="voice-assistant-title">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 id="voice-assistant-title" className="text-xl font-semibold">BizExpense Voice</h2>
        <p className="text-sm text-slate-500">AssemblyAI-powered voice expense assistant</p>
      </div>
      <div className="flex gap-2">
        <button className="btn-primary" onClick={start} disabled={status === 'connecting'}>
          {status === 'error' ? 'Retry' : status === 'idle' || mockMode ? 'Start voice assistant' : 'Reconnect microphone'}
        </button>
        {!mockMode && status !== 'idle' && status !== 'error' && <button className="btn-secondary" onClick={stop}>Stop voice assistant</button>}
      </div>
    </div>
    <p className="mt-4 text-sm"><strong>Status:</strong> {statusLabels[status]}</p>
    <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3">
      <p className="text-sm font-semibold text-blue-950">Prototype demo — mock voice input</p>
      <p className="mt-1 text-xs text-blue-800">Transcript, intent, and tool selection are simulated. Confirmed actions still call the configured BizExpense API.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="btn-secondary" onClick={() => runPrototype('create')}>Demo create</button>
        <button className="btn-secondary" onClick={() => runPrototype('summary')}>Demo query</button>
        <button className="btn-secondary" onClick={() => runPrototype('search')}>Demo search</button>
        <button className="btn-secondary" onClick={() => runPrototype('categories')}>Demo categories</button>
        <button className="btn-secondary" onClick={() => runPrototype('update')}>Demo category update</button>
      </div>
    </div>
    {mockMode && <p className="mt-3 text-xs font-semibold uppercase text-blue-700">Mock voice mode</p>}
    {userTranscript && <p className="mt-3 rounded-lg bg-slate-50 p-3"><strong>You:</strong> “{userTranscript}”</p>}
    {agentTranscript && <p className="mt-3 rounded-lg bg-teal-50 p-3 text-teal-950"><strong>Agent:</strong> “{agentTranscript}”</p>}
    {error && <p role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>}
    {pending && preview && <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-4">
      <h3 className="font-semibold">{pending.action === 'create_expense' ? 'New expense' : 'Classify expense'}</h3>
      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
        {Object.entries(preview).filter(([key]) => key !== 'expense_id').map(([key, value]) => <div key={key}>
          <dt className="text-xs uppercase text-slate-500">{key.replaceAll('_', ' ')}</dt>
          <dd className="font-medium">{String(value)}</dd>
        </div>)}
      </dl>
      <p className="mt-3 text-sm font-medium text-amber-900">Confirmation required. No database change has been made.</p>
      <div className="mt-3 flex gap-2">
        <button className="btn-primary" onClick={confirm} disabled={status === 'executing'}>Confirm</button>
        <button className="btn-secondary" onClick={cancel} disabled={status === 'executing'}>Cancel</button>
      </div>
    </div>}
  </section>
}
