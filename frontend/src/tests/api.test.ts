import { afterEach, expect, test, vi } from 'vitest'

import { api, logout } from '../services/api'

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

test('an expired access token is refreshed once before retrying the request', async () => {
  localStorage.setItem('bizexpense_token', 'expired-access')
  localStorage.setItem('bizexpense_refresh_token', 'valid-refresh')
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ detail: 'expired' }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ access_token: 'new-access', refresh_token: 'new-refresh' }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ status: 'ok' }) })
  vi.stubGlobal('fetch', fetchMock)

  await expect(api<{ status: string }>('/protected')).resolves.toEqual({ status: 'ok' })
  expect(localStorage.getItem('bizexpense_token')).toBe('new-access')
  expect(localStorage.getItem('bizexpense_refresh_token')).toBe('new-refresh')
  expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/auth/refresh', expect.objectContaining({ method: 'POST' }))
})

test('failed refresh clears the session and emits unauthorized', async () => {
  localStorage.setItem('bizexpense_token', 'expired-access')
  localStorage.setItem('bizexpense_refresh_token', 'expired-refresh')
  const unauthorized = vi.fn()
  window.addEventListener('bizexpense:unauthorized', unauthorized)
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
    .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) }))

  await expect(api('/protected')).rejects.toThrow('Authentication expired')
  expect(localStorage.getItem('bizexpense_token')).toBeNull()
  expect(localStorage.getItem('bizexpense_refresh_token')).toBeNull()
  expect(unauthorized).toHaveBeenCalledOnce()
  window.removeEventListener('bizexpense:unauthorized', unauthorized)
})

test('logout revokes the refresh token before clearing local session', async () => {
  localStorage.setItem('bizexpense_token', 'access')
  localStorage.setItem('bizexpense_refresh_token', 'refresh')
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204 })
  vi.stubGlobal('fetch', fetchMock)

  await logout()

  expect(fetchMock).toHaveBeenCalledWith('/api/auth/logout', expect.objectContaining({ method: 'POST' }))
  expect(localStorage.getItem('bizexpense_token')).toBeNull()
  expect(localStorage.getItem('bizexpense_refresh_token')).toBeNull()
})
