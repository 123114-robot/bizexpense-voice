import { api } from '../services/api'

export type PendingVoiceAction = {
  status: 'confirmation_required'
  pending_action_id: string
  action: 'create_expense' | 'update_expense'
  preview: Record<string, string | number>
}

export type VoiceSummary = {
  total_expenses: string
  expenses_this_month: string
  gst_paid: string
  category_breakdown: { category: string; total: string }[]
}

export type VoiceSearchResult = {
  count: number
  expenses: {
    id: number
    supplier_name: string
    category_name: string
    invoice_date: string
    total_amount: string
    currency: string
  }[]
}

export type VoiceCategories = { categories: string[] }

const endpoints: Record<string, string> = {
  prepare_expense: '/voice/tools/prepare-expense',
  get_expense_summary: '/voice/tools/summary',
  list_expense_categories: '/voice/tools/categories',
  search_expenses: '/voice/tools/search-expenses',
  prepare_expense_update: '/voice/tools/prepare-update',
}

async function jsonRequest<T>(url: string, options: RequestInit): Promise<T> {
  return api<T>(url, options)
}

export const voiceToolAdapter = {
  async callTool(name: string, args: Record<string, unknown>) {
    const endpoint = endpoints[name]
    if (!endpoint) throw new Error(`Unknown voice tool: ${name}`)
    return jsonRequest<PendingVoiceAction | VoiceSummary | VoiceSearchResult | VoiceCategories>(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(args),
    })
  },
  confirm: (actionId: string) => jsonRequest(`/voice/actions/${actionId}/confirm`, { method: 'POST' }),
  async cancel(actionId: string) {
    await api<void>(`/voice/actions/${actionId}`, { method: 'DELETE' })
  },
}
