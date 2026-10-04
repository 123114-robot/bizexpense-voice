import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { AuthPage } from '../pages/AuthPage'

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear() })

test('sign in stores the JWT and enters the app', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ access_token: 'demo-jwt' }) }))
  render(<MemoryRouter initialEntries={['/login']}><Routes><Route path="/login" element={<AuthPage />} /><Route path="/" element={<p>Dashboard ready</p>} /></Routes></MemoryRouter>)
  await userEvent.type(screen.getByLabelText('Email'), 'demo@example.com')
  await userEvent.type(screen.getByLabelText('Password'), 'demo-password-123')
  await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
  expect(await screen.findByText('Dashboard ready')).toBeInTheDocument()
  expect(localStorage.getItem('bizexpense_token')).toBe('demo-jwt')
})
