import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { expenseService } from '../services/expenseService'
import type { Category, Expense, ExpenseFilters } from '../types/expense'

const emptyFilters: ExpenseFilters = {
  search: '',
  category_id: '',
  date_from: '',
  date_to: '',
  ocr_confirmed: '',
}

export function ExpensesPage() {
  const [rows, setRows] = useState<Expense[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [filters, setFilters] = useState<ExpenseFilters>(emptyFilters)

  useEffect(() => { expenseService.categories().then(setCategories) }, [])
  useEffect(() => {
    const timer = setTimeout(() => expenseService.list(filters).then(setRows), 200)
    return () => clearTimeout(timer)
  }, [filters])

  const updateFilter = (name: keyof ExpenseFilters, value: string) => {
    setFilters((current) => ({ ...current, [name]: value }))
  }
  const exportCsv = async () => {
    const blob = await expenseService.exportCsv(filters); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = 'bizexpense-expenses.csv'; link.click(); URL.revokeObjectURL(url)
  }

  return <>
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-3xl font-bold">Expenses</h1><p className="text-slate-600">Review and manage recorded expenses.</p></div>
      <div className="flex gap-2">
        <button className="btn-secondary" type="button" onClick={exportCsv}>Export CSV</button>
        <Link className="btn" to="/expenses/new">Add expense</Link>
      </div>
    </div>
    <div className="card mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
      <label className="text-sm">Search
        <input aria-label="Search expenses" className="field mt-1" placeholder="Supplier or description" value={filters.search} onChange={(event) => updateFilter('search', event.target.value)} />
      </label>
      <label className="text-sm">Category
        <select className="field mt-1" value={filters.category_id} onChange={(event) => updateFilter('category_id', event.target.value)}>
          <option value="">All categories</option>
          {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
        </select>
      </label>
      <label className="text-sm">From date
        <input className="field mt-1" type="date" value={filters.date_from} onChange={(event) => updateFilter('date_from', event.target.value)} />
      </label>
      <label className="text-sm">To date
        <input className="field mt-1" type="date" value={filters.date_to} onChange={(event) => updateFilter('date_to', event.target.value)} />
      </label>
      <label className="text-sm">Status
        <select className="field mt-1" value={filters.ocr_confirmed} onChange={(event) => updateFilter('ocr_confirmed', event.target.value)}>
          <option value="">All statuses</option>
          <option value="true">Confirmed</option>
          <option value="false">Draft</option>
        </select>
      </label>
    </div>
    <button className="mb-4 text-sm text-teal-700 hover:underline" type="button" onClick={() => setFilters(emptyFilters)}>Clear filters</button>
    <div className="card overflow-x-auto p-0">
      <table className="w-full text-left text-sm"><thead className="bg-slate-50"><tr>{['Date', 'Supplier', 'Category', 'Description', 'GST', 'Total', 'Status'].map((heading) => <th className="p-3" key={heading}>{heading}</th>)}</tr></thead>
        <tbody>{rows.map((expense) => <tr className="border-t" key={expense.id}><td className="p-3"><Link className="text-teal-700 hover:underline" to={`/expenses/${expense.id}`}>{expense.invoice_date}</Link></td><td>{expense.supplier_name}</td><td>{expense.category_name}</td><td>{expense.description}</td><td>${expense.gst_amount}</td><td>${expense.total_amount}</td><td>{expense.ocr_confirmed ? 'Confirmed' : 'Draft'}</td></tr>)}</tbody>
      </table>
      {rows.length === 0 && <p className="p-6 text-center text-slate-500">No expenses found.</p>}
    </div>
  </>
}
