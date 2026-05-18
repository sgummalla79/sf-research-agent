/**
 * Unit tests for the sidebar Pinia store.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia }           from 'pinia'
import { useSidebarStore }                       from '../../../stores/sidebar'

vi.mock('../../../composables/useFetch', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../../composables/useFetch'

function makeJsonResponse(data) {
  return { ok: true, json: vi.fn().mockResolvedValue(data) }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('toggle()', () => {
  it('flips open from true to false', () => {
    const store = useSidebarStore()
    expect(store.open).toBe(true)
    store.toggle()
    expect(store.open).toBe(false)
  })

  it('flips open from false to true', () => {
    const store = useSidebarStore()
    store.open = false
    store.toggle()
    expect(store.open).toBe(true)
  })
})

describe('load()', () => {
  it('populates pinned and recent from API', async () => {
    const store = useSidebarStore()
    apiFetch.mockResolvedValue(makeJsonResponse({
      pinned: [{ id: '1', title: 'Pinned' }],
      recent: [{ id: '2', title: 'Recent' }],
    }))

    await store.load()

    expect(store.pinned).toHaveLength(1)
    expect(store.recent).toHaveLength(1)
    expect(store.pinned[0].title).toBe('Pinned')
    expect(store.recent[0].title).toBe('Recent')
  })

  it('handles missing keys gracefully', async () => {
    const store = useSidebarStore()
    apiFetch.mockResolvedValue(makeJsonResponse({}))

    await store.load()

    expect(store.pinned).toEqual([])
    expect(store.recent).toEqual([])
  })

  it('does not throw on network error', async () => {
    const store = useSidebarStore()
    apiFetch.mockRejectedValue(new Error('network'))

    await expect(store.load()).resolves.not.toThrow()
  })
})

describe('pin() / unpin()', () => {
  it('calls POST pin endpoint then reloads', async () => {
    const store = useSidebarStore()
    apiFetch
      .mockResolvedValueOnce({ ok: true, json: vi.fn().mockResolvedValue({}) })  // pin
      .mockResolvedValueOnce(makeJsonResponse({ pinned: [], recent: [] }))        // reload

    await store.pin('conv-1')

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/conversations/conv-1/pin',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('calls DELETE pin endpoint then reloads', async () => {
    const store = useSidebarStore()
    apiFetch
      .mockResolvedValueOnce({ ok: true, json: vi.fn().mockResolvedValue({}) })  // unpin
      .mockResolvedValueOnce(makeJsonResponse({ pinned: [], recent: [] }))        // reload

    await store.unpin('conv-1')

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/conversations/conv-1/pin',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })
})

describe('remove()', () => {
  it('calls DELETE and reloads', async () => {
    const store = useSidebarStore()
    apiFetch
      .mockResolvedValueOnce({ ok: true, json: vi.fn().mockResolvedValue({}) })
      .mockResolvedValueOnce(makeJsonResponse({ pinned: [], recent: [] }))

    await store.remove('conv-99')

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/conversations/conv-99',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })
})

describe('rename()', () => {
  it('calls PATCH with trimmed title and reloads', async () => {
    const store = useSidebarStore()
    apiFetch
      .mockResolvedValueOnce({ ok: true, json: vi.fn().mockResolvedValue({}) })
      .mockResolvedValueOnce(makeJsonResponse({ pinned: [], recent: [] }))

    await store.rename('conv-5', '  My New Title  ')

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/conversations/conv-5',
      expect.objectContaining({
        method: 'PATCH',
        body:   JSON.stringify({ title: 'My New Title' }),
      }),
    )
  })

  it('does nothing when title is empty/whitespace', async () => {
    const store = useSidebarStore()

    await store.rename('conv-5', '   ')

    expect(apiFetch).not.toHaveBeenCalled()
  })
})
