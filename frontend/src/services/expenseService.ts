import { api, download } from './api'
import type { Category, Dashboard, Expense, ExpenseFilters, ExpenseInput } from '../types/expense'

function expenseQuery(filters: ExpenseFilters) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value)
  })
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const expenseService = {
  list: (filters: ExpenseFilters = {}) => api<Expense[]>(`/expenses${expenseQuery(filters)}`),
  exportCsv: (filters: ExpenseFilters = {}) => download(`/expenses/export.csv${expenseQuery(filters)}`),
  get: (id: string) => api<Expense>(`/expenses/${id}`),
  create: (data: ExpenseInput) => api<Expense>('/expenses', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  update: (id: string, data: ExpenseInput) => api<Expense>(`/expenses/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  remove: (id: string) => api<void>(`/expenses/${id}`, { method: 'DELETE' }),
  categories: () => api<Category[]>('/categories'),
  dashboard: () => api<Dashboard>('/dashboard/summary'),
}
