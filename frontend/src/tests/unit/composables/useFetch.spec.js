/**
 * Unit tests for apiFetch composable.
 * Covers: Content-Type injection, credentials, 401 redirect, passthrough.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiFetch } from '../../../composables/useFetch'

function mockFetch(status, body = {}) {
  return vi.fn().mockResolvedValue({
    status,
    ok: status < 400,
    json: vi.fn().mockResolvedValue(body),
  })
}

beforeEach(() => {
  delete window.location
  window.location = { href: '' }
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('apiFetch()', () => {
  it('passes credentials: include on every request', async () => {
    global.fetch = mockFetch(200)
    await apiFetch('/api/test')
    expect(global.fetch).toHaveBeenCalledWith('/api/test', expect.objectContaining({
      credentials: 'include',
    }))
  })

  it('injects Content-Type: application/json when body is a JSON string', async () => {
    global.fetch = mockFetch(200)
    await apiFetch('/api/test', { method: 'POST', body: JSON.stringify({ a: 1 }) })
    const call = global.fetch.mock.calls[0][1]
    expect(call.headers['Content-Type']).toBe('application/json')
  })

  it('does not override an explicitly set Content-Type', async () => {
    global.fetch = mockFetch(200)
    await apiFetch('/api/test', {
      method:  'POST',
      body:    JSON.stringify({}),
      headers: { 'Content-Type': 'text/plain' },
    })
    const call = global.fetch.mock.calls[0][1]
    expect(call.headers['Content-Type']).toBe('text/plain')
  })

  it('does not inject Content-Type when body is absent', async () => {
    global.fetch = mockFetch(200)
    await apiFetch('/api/test')
    const call = global.fetch.mock.calls[0][1]
    expect(call.headers['Content-Type']).toBeUndefined()
  })

  it('returns the response on 200', async () => {
    global.fetch = mockFetch(200, { ok: true })
    const res = await apiFetch('/api/test')
    expect(res.status).toBe(200)
  })

  it('returns the response on 4xx (non-401)', async () => {
    global.fetch = mockFetch(404)
    const res = await apiFetch('/api/missing')
    expect(res.status).toBe(404)
  })

  it('redirects to /login and throws on 401', async () => {
    global.fetch = mockFetch(401)
    await expect(apiFetch('/api/secure')).rejects.toThrow('Unauthorized')
    expect(window.location.href).toBe('/login')
  })

  it('passes through custom headers alongside injected ones', async () => {
    global.fetch = mockFetch(200)
    await apiFetch('/api/test', { headers: { 'X-Custom': 'value' } })
    const call = global.fetch.mock.calls[0][1]
    expect(call.headers['X-Custom']).toBe('value')
  })
})
