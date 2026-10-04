export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers)
  const token = localStorage.getItem('bizexpense_token')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`/api${path}`, { ...options, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    if (response.status === 401) { localStorage.removeItem('bizexpense_token'); window.dispatchEvent(new Event('bizexpense:unauthorized')) }
    throw new Error(body.detail || 'Something went wrong')
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export async function download(path: string): Promise<Blob> {
  const token = localStorage.getItem('bizexpense_token')
  const response = await fetch(`/api${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!response.ok) throw new Error('Export failed')
  return response.blob()
}
