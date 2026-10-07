import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import { DashboardPage } from '../pages/DashboardPage'

afterEach(() => vi.unstubAllGlobals())

test('dashboard displays category and monthly analytics', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      total_expenses: '165.00',
      expenses_this_month: '165.00',
      gst_paid: '15.00',
      expense_count: 2,
      average_expense: '82.50',
      top_suppliers: [
        { supplier: 'Acme Office Supplies', total: '110.00', expense_count: 1 },
        { supplier: 'Fuel Station', total: '55.00', expense_count: 1 },
      ],
      category_breakdown: [
        { category: 'Office Supplies', total: '110.00', expense_count: 1 },
        { category: 'Fuel', total: '55.00', expense_count: 1 },
      ],
      monthly_trend: [{ month: '2026-09', total: '165.00' }],
    }),
  }))

  render(<DashboardPage />)

  expect(await screen.findByText('Spending by category')).toBeInTheDocument()
  expect(screen.getByText('Office Supplies')).toBeInTheDocument()
  expect(screen.getByText('Monthly trend')).toBeInTheDocument()
  expect(screen.getByText('2026-09')).toBeInTheDocument()
  expect(screen.getByText('Average expense')).toBeInTheDocument()
  expect(screen.getByText('Top suppliers')).toBeInTheDocument()
  expect(screen.getByText('Acme Office Supplies')).toBeInTheDocument()

})
