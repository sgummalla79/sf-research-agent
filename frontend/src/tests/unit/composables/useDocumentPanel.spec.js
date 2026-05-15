/**
 * Unit tests for useDocumentPanel composable.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useDocumentPanel } from '../../../composables/useDocumentPanel'

vi.mock('../../../composables/useFetch', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../../composables/useFetch'

beforeEach(() => vi.clearAllMocks())

describe('open()', () => {
  it('sets open=true and fetches artifact content', async () => {
    apiFetch.mockResolvedValue({
      json: vi.fn().mockResolvedValue({ content: '# Doc', version: 2 }),
    })

    const { panel, open } = useDocumentPanel()
    await open('art-1')

    expect(panel.open).toBe(true)
    expect(panel.content).toBe('# Doc')
    expect(panel.version).toBe(2)
    expect(panel.loading).toBe(false)
    expect(panel.artifactId).toBe('art-1')
  })

  it('shows error message when fetch fails', async () => {
    apiFetch.mockRejectedValue(new Error('network'))

    const { panel, open } = useDocumentPanel()
    await open('bad-id')

    expect(panel.open).toBe(true)
    expect(panel.content).toContain('⚠️')
    expect(panel.loading).toBe(false)
  })
})

describe('close()', () => {
  it('sets open=false', async () => {
    apiFetch.mockResolvedValue({ json: vi.fn().mockResolvedValue({ content: '' }) })
    const { panel, open, close } = useDocumentPanel()
    await open('art-1')
    expect(panel.open).toBe(true)
    close()
    expect(panel.open).toBe(false)
  })
})

describe('downloadMD()', () => {
  it('does nothing when content is empty', () => {
    const { downloadMD } = useDocumentPanel()
    // Should not throw
    expect(() => downloadMD()).not.toThrow()
  })
})
