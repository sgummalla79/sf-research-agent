/**
 * Authenticated fetch wrapper.
 *
 * Attaches Authorization: Bearer {token} to every request.
 * On 401, clears auth and redirects to /login.
 *
 * Usage:
 *   import { apiFetch } from '@/composables/useFetch.js'
 *   const res = await apiFetch('/api/chat/sessions')
 *   const res = await apiFetch('/api/chat/start', { method: 'POST', body: JSON.stringify(payload) })
 */

import { useAuth } from './useAuth.js'

export async function apiFetch(url, options = {}) {
  const { accessToken, logout } = useAuth()

  const headers = {
    ...(options.headers || {}),
    Authorization: `Bearer ${accessToken.value}`,
  }

  // Only auto-set Content-Type for JSON bodies (don't override FormData)
  if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(url, { ...options, headers })

  if (res.status === 401) {
    logout()
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  return res
}
