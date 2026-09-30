import { useEffect, useRef, useState } from 'react'

import { VoiceAgentClient, type PendingVoiceAction, type VoiceStatus } from './voiceAgentClient'

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

  useEffect(() => () => client.current?.disconnect(), [])

  const start = async () => {
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
      setError(caught instanceof Error ? caught.message : 'Unable to start voice assistant')
      setStatus('error')
    }
  }

  const confirm = async () => {
    if (!pending || executing.current) return
    executing.current = true
    setStatus('executing')
    setError('')
    try {
      const response = await fetch(`/api/voice/actions/${pending.pending_action_id}/confirm`, { method: 'POST' })
      const body = await response.json().catch(() => ({})) as { detail?: string }
      if (!response.ok) throw new Error(body.detail || 'Unable to save expense')
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
    await fetch(`/api/voice/actions/${pending.pending_action_id}`, { method: 'DELETE' })
    setPending(undefined)
    setStatus('ready')
    setAgentTranscript('Cancelled. Nothing was saved.')
  }

  const preview = pending?.preview
  return <section className="card mb-6" aria-labelledby="voice-assistant-title">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 id="voice-assistant-title" className="text-xl font-semibold">BizExpense Voice</h2>
        <p className="text-sm text-slate-500">AssemblyAI-powered voice expense assistant</p>
      </div>
      <button className="btn-primary" onClick={start} disabled={status === 'connecting'}>
        {status === 'error' ? 'Retry' : status === 'idle' ? 'Start voice assistant' : 'Reconnect microphone'}
      </button>
    </div>
    <p className="mt-4 text-sm"><strong>Status:</strong> {statusLabels[status]}</p>
    {userTranscript && <p className="mt-3 rounded-lg bg-slate-50 p-3"><strong>You:</strong> “{userTranscript}”</p>}
    {agentTranscript && <p className="mt-3 rounded-lg bg-teal-50 p-3 text-teal-950"><strong>Agent:</strong> “{agentTranscript}”</p>}
    {error && <p role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>}
    {pending && preview && <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-4">
      <h3 className="font-semibold">{pending.action === 'create_expense' ? 'New expense' : 'Update latest expense'}</h3>
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
