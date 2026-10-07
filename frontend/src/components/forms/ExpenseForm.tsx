import { useEffect, useState, type FormEvent } from 'react'
import type { Category, ExpenseInput } from '../../types/expense'
import { expenseService } from '../../services/expenseService'

const empty: ExpenseInput = { supplier_name: '', category_id: 1, document_id: null, invoice_number: '', invoice_date: new Date().toISOString().slice(0,10), due_date: null, subtotal: '', gst_amount: '', total_amount: '', currency: 'AUD', description: '', ocr_confidence: null, ocr_confirmed: true }

export function ExpenseForm({ initial, onSubmit, submitLabel = 'Save expense', requireConfirmation = false }: { initial?: Partial<ExpenseInput>, onSubmit: (data: ExpenseInput) => Promise<void>, submitLabel?: string, requireConfirmation?: boolean }) {
  const [data, setData] = useState<ExpenseInput>({...empty, ...initial})
  const [categories, setCategories] = useState<Category[]>([])
  const [error, setError] = useState('')
  const amountError = error === 'GST cannot exceed total amount'
  useEffect(() => { expenseService.categories().then(setCategories).catch(e => setError(e.message)) }, [])
  const set = (name: keyof ExpenseInput, value: string | number | boolean) => setData(current => ({...current, [name]: value}))
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(''); if (Number(data.gst_amount) > Number(data.total_amount)) { setError('GST cannot exceed total amount'); return } if (requireConfirmation && !data.ocr_confirmed) { setError('Confirm the extracted information before saving'); return } try { await onSubmit(data) } catch (e) { setError(e instanceof Error ? e.message : 'Unable to save') } }
  return <form onSubmit={submit} className="card grid gap-4 md:grid-cols-2">
    {error && <div id="expense-form-error" role="alert" aria-live="assertive" className="md:col-span-2 rounded-lg bg-red-50 p-3 text-red-700">{error}</div>}
    <label>Supplier<input required className="field" value={data.supplier_name} onChange={e=>set('supplier_name',e.target.value)} /></label>
    <label>Category<select className="field" value={data.category_id} onChange={e=>set('category_id',Number(e.target.value))}>{categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
    <label>Invoice number<input className="field" value={data.invoice_number || ''} onChange={e=>set('invoice_number',e.target.value)} /></label>
    <label>Invoice date<input required type="date" className="field" value={data.invoice_date} onChange={e=>set('invoice_date',e.target.value)} /></label>
    <label>Subtotal<input required min="0" step="0.01" type="number" className="field" value={data.subtotal} onChange={e=>set('subtotal',e.target.value)} /></label>
    <label>GST amount<input required min="0" step="0.01" type="number" className="field" aria-invalid={amountError} aria-describedby={amountError?'expense-form-error':undefined} value={data.gst_amount} onChange={e=>set('gst_amount',e.target.value)} /></label>
    <label>Total amount<input required min="0" step="0.01" type="number" className="field" aria-invalid={amountError} aria-describedby={amountError?'expense-form-error':undefined} value={data.total_amount} onChange={e=>set('total_amount',e.target.value)} /></label>
    <label>Currency<input required maxLength={3} className="field" value={data.currency} onChange={e=>set('currency',e.target.value.toUpperCase())} /></label>
    <label className="md:col-span-2">Description<textarea required className="field" value={data.description} onChange={e=>set('description',e.target.value)} /></label>
    {requireConfirmation && <label className="md:col-span-2 flex grid-cols-none flex-row items-center gap-2"><input type="checkbox" checked={data.ocr_confirmed} onChange={e=>set('ocr_confirmed',e.target.checked)} />I have reviewed and confirm this information</label>}
    <div className="md:col-span-2"><button className="btn" type="submit">{submitLabel}</button></div>
  </form>
}
