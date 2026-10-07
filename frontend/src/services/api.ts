const ACCESS_TOKEN_KEY = 'bizexpense_token'
const REFRESH_TOKEN_KEY = 'bizexpense_refresh_token'

export type TokenPair = {
  access_token: string
  refresh_token: string
}

export function storeSession(tokens: TokenPair) {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
}

export function clearSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

function expireSession() {
  clearSession()
  window.dispatchEvent(new Event('bizexpense:unauthorized'))
}

let refreshRequest: Promise<boolean> | null = null

async function refreshSession(): Promise<boolean> {
  if (refreshRequest) return refreshRequest
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) return false

  refreshRequest = (async () => {
    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) {
      expireSession()
      return false
    }
    storeSession(await response.json() as TokenPair)
    return true
  })().catch(() => {
    expireSession()
    return false
  }).finally(() => {
    refreshRequest = null
  })

  return refreshRequest
}

async function authenticatedFetch(path: string, options?: RequestInit, retry = true) {
  const headers = new Headers(options?.headers)
  const token = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`/api${path}`, { ...options, headers })
  if (response.status === 401 && retry && await refreshSession()) {
    return authenticatedFetch(path, options, false)
  }
  return response
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(path, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    if (response.status === 401 && localStorage.getItem(ACCESS_TOKEN_KEY)) expireSession()
    throw new Error(response.status === 401 ? 'Authentication expired' : body.detail || 'Something went wrong')
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export async function download(path: string): Promise<Blob> {
  const response = await authenticatedFetch(path)
  if (!response.ok) {
    if (response.status === 401 && localStorage.getItem(ACCESS_TOKEN_KEY)) expireSession()
    throw new Error('Export failed')
  }
  return response.blob()
}

export async function logout(): Promise<void> {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  try {
    if (refreshToken) {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
    }
  } finally {
    clearSession()
  }
}
