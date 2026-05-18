/**
 * useFetch — internal HTTP utility. Do NOT import this outside of api/service.js.
 * All API calls must go through Api (src/api/service.js).
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

export async function* _readSSEStream(body) {
  const reader  = body.getReader()
  const decoder = new TextDecoder()
  let   buffer  = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try { yield JSON.parse(line.slice(6)) } catch { /* skip malformed */ }
    }
  }
}
