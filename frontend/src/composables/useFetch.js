/**
 * Authenticated fetch — credentials:'include' sends the httpOnly session
 * cookie automatically. No Authorization header needed.
 * On 401, redirect to /login.
 */

export async function apiFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) }

  if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(url, { ...options, headers, credentials: 'include' })

  if (res.status === 401) {
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  return res
}
