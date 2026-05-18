/**
 * Unit tests for useDocumentPanel composable.
 * Covers: open/close state, loading, fetch errors, version resolution,
 *         downloadMD, downloadPDF.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useDocumentPanel } from '../../../composables/useDocumentPanel'

vi.mock('../../../api/service.js', () => ({
  Api: { getArtifact: vi.fn() },
}))

import { Api } from '../../../api/service.js'

beforeEach(() => vi.clearAllMocks())

// ── initial state ─────────────────────────────────────────────────────────────

describe('initial state', () => {
  it('starts closed with empty content', () => {
    const { panel } = useDocumentPanel()
    expect(panel.open).toBe(false)
    expect(panel.content).toBe('')
    expect(panel.loading).toBe(false)
    expect(panel.version).toBe(0)
    expect(panel.artifactId).toBeNull()
  })
})

// ── open() ────────────────────────────────────────────────────────────────────

describe('open()', () => {
  it('sets open=true and fetches artifact content', async () => {
    Api.getArtifact.mockResolvedValue({ content: '# Doc', version: 2 })
    const { panel, open } = useDocumentPanel()
    await open('art-1')

    expect(panel.open).toBe(true)
    expect(panel.content).toBe('# Doc')
    expect(panel.version).toBe(2)
    expect(panel.loading).toBe(false)
    expect(panel.artifactId).toBe('art-1')
    expect(Api.getArtifact).toHaveBeenCalledWith('art-1')
  })

  it('shows loading=true while fetching', async () => {
    let resolve
    Api.getArtifact.mockReturnValue(new Promise(r => { resolve = r }))
    const { panel, open } = useDocumentPanel()
    const p = open('art-1')
    expect(panel.loading).toBe(true)
    resolve({ content: 'doc', version: 1 })
    await p
    expect(panel.loading).toBe(false)
  })

  it('shows error message when fetch fails', async () => {
    Api.getArtifact.mockRejectedValue(new Error('network'))
    const { panel, open } = useDocumentPanel()
    await open('bad-id')
    expect(panel.open).toBe(true)
    expect(panel.content).toContain('⚠️')
    expect(panel.loading).toBe(false)
  })

  it('uses version from API response when present', async () => {
    Api.getArtifact.mockResolvedValue({ content: 'doc', version: 5 })
    const { panel, open } = useDocumentPanel()
    await open('art-v5', 1)
    expect(panel.version).toBe(5)
  })

  it('falls back to passed version when response omits it', async () => {
    Api.getArtifact.mockResolvedValue({ content: 'doc' })
    const { panel, open } = useDocumentPanel()
    await open('art-fallback', 3)
    expect(panel.version).toBe(3)
  })
})

// ── close() ───────────────────────────────────────────────────────────────────

describe('close()', () => {
  it('sets open=false', async () => {
    Api.getArtifact.mockResolvedValue({ content: '# Doc', version: 1 })
    const { panel, open, close } = useDocumentPanel()
    await open('art-1')
    expect(panel.open).toBe(true)
    close()
    expect(panel.open).toBe(false)
  })
})

// ── downloadMD() ──────────────────────────────────────────────────────────────

describe('downloadMD()', () => {
  it('does nothing when content is empty', () => {
    const { downloadMD } = useDocumentPanel()
    expect(() => downloadMD()).not.toThrow()
  })

  it('creates blob URL, clicks anchor, and revokes URL', async () => {
    Api.getArtifact.mockResolvedValue({ content: '# Doc', version: 1 })
    const { open, downloadMD } = useDocumentPanel()
    await open('art-dl', 1)

    const anchor = { href: '', download: '', click: vi.fn() }
    vi.spyOn(document, 'createElement').mockReturnValue(anchor)
    global.URL.createObjectURL = vi.fn().mockReturnValue('blob:test')
    global.URL.revokeObjectURL = vi.fn()

    downloadMD()

    expect(global.URL.createObjectURL).toHaveBeenCalled()
    expect(anchor.click).toHaveBeenCalled()
    expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('blob:test')
  })
})

// ── downloadPDF() ─────────────────────────────────────────────────────────────

describe('downloadPDF()', () => {
  it('does nothing when content is empty', () => {
    const { downloadPDF } = useDocumentPanel()
    const openSpy = vi.spyOn(window, 'open').mockReturnValue(null)
    downloadPDF(t => t)
    expect(openSpy).not.toHaveBeenCalled()
  })

  it('does nothing when renderFn is null', async () => {
    Api.getArtifact.mockResolvedValue({ content: 'doc', version: 1 })
    const { open, downloadPDF } = useDocumentPanel()
    await open('art-1', 1)
    const openSpy = vi.spyOn(window, 'open').mockReturnValue(null)
    downloadPDF(null)
    expect(openSpy).not.toHaveBeenCalled()
  })

  it('opens window, writes HTML, and calls print', async () => {
    Api.getArtifact.mockResolvedValue({ content: '# Doc', version: 1 })
    const { open, downloadPDF } = useDocumentPanel()
    await open('art-pdf', 1)

    const mockWin = { document: { write: vi.fn(), close: vi.fn() }, print: vi.fn() }
    vi.spyOn(window, 'open').mockReturnValue(mockWin)

    downloadPDF(text => `<html><body>${text}</body></html>`)

    expect(mockWin.document.write).toHaveBeenCalled()
    expect(mockWin.print).toHaveBeenCalled()
  })
})
