/**
 * useDocumentPanel — document viewer logic.
 *
 * Extracted from the old ChatWindow.vue / useAgentChat.js.
 * Manages: open/close, fetch by artifactId, download MD, trigger PDF.
 */

import { reactive } from 'vue'
import { apiFetch } from './useFetch'

export function useDocumentPanel() {
  const panel = reactive({
    open:       false,
    loading:    false,
    content:    '',
    version:    0,
    artifactId: null,
  })

  async function open(artifactId, version = null) {
    panel.open       = true
    panel.loading    = true
    panel.artifactId = artifactId
    panel.content    = ''
    panel.version    = version ?? 0

    try {
      const res  = await apiFetch(`/api/artifacts/${artifactId}`)
      const data = await res.json()
      panel.content = data.content || ''
      panel.version = data.version ?? version ?? 0
    } catch (_) {
      panel.content = '⚠️ Could not load document.'
    } finally {
      panel.loading = false
    }
  }

  function close() {
    panel.open = false
  }

  function downloadMD() {
    if (!panel.content) return
    const blob = new Blob([panel.content], { type: 'text/markdown' })
    const url  = URL.createObjectURL(blob)
    const a    = Object.assign(document.createElement('a'), {
      href:     url,
      download: `architecture-v${panel.version}.md`,
    })
    a.click()
    URL.revokeObjectURL(url)
  }

  function downloadPDF(renderFn) {
    if (!panel.content || !renderFn) return
    const win = window.open('', '_blank')
    win.document.write(`
      <html><head><title>Architecture v${panel.version}</title>
      <style>body{font-family:sans-serif;max-width:900px;margin:40px auto;padding:0 20px}
      pre{background:#f4f4f4;padding:12px;border-radius:4px;overflow:auto}</style>
      </head><body>${renderFn(panel.content)}</body></html>
    `)
    win.document.close()
    win.print()
  }

  return { panel, open, close, downloadMD, downloadPDF }
}
