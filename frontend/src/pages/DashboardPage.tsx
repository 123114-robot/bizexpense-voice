import { useCallback, useEffect, useState } from 'react'

import { expenseService } from '../services/expenseService'
import type { Dashboard } from '../types/expense'
import { VoiceAssistant } from '../voice/VoiceAssistant'

export function DashboardPage() {
  const [data, setData] = useState<Dashboard>()
  const loadDashboard = useCallback(() => { void expenseService.dashboard().then(setData) }, [])
  useEffect(loadDashboard, [loadDashboard])

  const cards = [
    ['Total expenses', data?.total_expenses],
    ['Expenses this month', data?.expenses_this_month],
    ['GST paid', data?.gst_paid],
    ['Number of expenses', data?.expense_count],
  ]
  const trendMaximum = Math.max(...(data?.monthly_trend.map(item => Number(item.total)) ?? [0]), 1)

  return <>
    <h1 className="mb-1 text-3xl font-bold">Dashboard</h1>
    <p className="mb-6 text-slate-600">A clear view of your confirmed business spending.</p>
    <VoiceAssistant onMutation={loadDashboard} />
    <div className="grid gap-4 md:grid-cols-4">
      {cards.map(([label, value]) => <div className="card" key={label}>
        <p className="text-sm text-slate-500">{label}</p>
        <p className="mt-2 text-2xl font-bold">{value ?? '—'}</p>
      </div>)}
    </div>

    <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <section className="card">
        <h2 className="text-lg font-semibold">Spending by category</h2>
        <p className="mb-4 text-sm text-slate-500">Confirmed expenses only</p>
        <div className="grid gap-3">
          {data?.category_breakdown.map(item => <div key={item.category} className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div><p className="font-medium">{item.category}</p><p className="text-xs text-slate-500">{item.expense_count} expense{item.expense_count === 1 ? '' : 's'}</p></div>
            <p className="font-semibold">AUD ${item.total}</p>
          </div>)}
          {data?.category_breakdown.length === 0 && <p className="text-sm text-slate-500">No confirmed expenses yet.</p>}
        </div>
      </section>

      <section className="card">
        <h2 className="text-lg font-semibold">Monthly trend</h2>
        <p className="mb-4 text-sm text-slate-500">Last six months</p>
        <div className="flex h-48 items-end gap-3" aria-label="Monthly expense trend">
          {data?.monthly_trend.map(item => <div key={item.month} className="flex flex-1 flex-col items-center gap-2">
            <span className="text-xs font-medium">${item.total}</span>
            <div className="w-full rounded-t bg-teal-600" style={{ height: `${Math.max(Number(item.total) / trendMaximum * 120, 2)}px` }} />
            <span className="text-xs text-slate-500">{item.month}</span>
          </div>)}
        </div>
      </section>
    </div>
  </>
}
