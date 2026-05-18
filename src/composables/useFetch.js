/**
 * Authenticated fetch — credentials:'include' sends the httpOnly session
 * cookie automatically. No Authorization header needed.
 * On 401, redirect to /login.
 */

import { API_BASE } from '../api/config.js'

export async function apiFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) }

  if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`

  const res = await fetch(fullUrl, { ...options, headers, credentials: 'include' })

  if (res.status === 401) {
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  return res
}
