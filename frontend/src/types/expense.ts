export type Expense = {
  id: number; supplier_name: string; category_id: number; category_name: string;
  document_id: number | null; invoice_number: string | null; invoice_date: string; due_date: string | null;
  subtotal: string; gst_amount: string; total_amount: string; currency: string; description: string;
  ocr_confidence: number | null; ocr_confirmed: boolean;
  duplicate_warning: boolean; duplicate_expense_id: number | null;
}
export type ExpenseInput = Omit<Expense, 'id' | 'category_name' | 'duplicate_warning' | 'duplicate_expense_id'>
export type Category = { id: number; name: string }
export type ExpenseFilters = {
  search?: string
  category_id?: string
  date_from?: string
  date_to?: string
  ocr_confirmed?: string
}
export type Dashboard = {
  total_expenses: string
  expenses_this_month: string
  gst_paid: string
  expense_count: number
  average_expense: string
  top_suppliers: { supplier: string; total: string; expense_count: number }[]
  category_breakdown: { category: string; total: string; expense_count: number }[]
  monthly_trend: { month: string; total: string }[]
}
export type OCRResult = { supplier_name: string; abn: string | null; invoice_number: string | null; invoice_date: string; due_date: string | null; subtotal: string; gst: string; total: string; currency: string; confidence: number; confirmed: boolean }
