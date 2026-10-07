import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { logout } from '../../services/api'

export function AppLayout() {
  const navigate = useNavigate()
  const nav = ({ isActive }: { isActive: boolean }) => `rounded-lg px-3 py-2 ${isActive ? 'bg-teal-50 text-teal-800' : 'text-slate-600 hover:bg-slate-50'}`
  const signOut = async () => {
    await logout()
    navigate('/login')
  }

  return <div className="min-h-screen">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <header className="border-b bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <NavLink to="/" className="text-xl font-bold text-teal-800">BizExpense</NavLink>
        <nav aria-label="Primary navigation" className="flex gap-2">
          <NavLink className={nav} to="/">Dashboard</NavLink>
          <NavLink className={nav} to="/expenses">Expenses</NavLink>
          <NavLink className={nav} to="/expenses/new">Add expense</NavLink>
          <NavLink className={nav} to="/upload">Upload invoice</NavLink>
          <button className="px-3 py-2 text-slate-600" onClick={signOut}>Sign out</button>
        </nav>
      </div>
    </header>
    <main id="main-content" tabIndex={-1} className="mx-auto max-w-6xl p-5"><Outlet /></main>
  </div>
}
