<!--
  DocumentPanel — slide-in panel on the right for viewing the artifact.

  Uses useDocumentPanel composable for open/close/download logic.
  Receives the composable's panel reactive object as a prop.
-->
<template>
  <div class="doc-panel" :class="{ open: panel.open }">
    <div class="doc-panel-header">
      <span class="doc-panel-title">📄 Architecture Document<span v-if="panel.version"> v{{ panel.version }}</span></span>
      <div class="doc-panel-actions">
        <button class="ol-btn" @click="downloadMD">⬇ Markdown</button>
        <button class="ol-btn accent" @click="downloadPDF(renderContent)">⬇ PDF</button>
        <button class="ol-btn close" @click="close">✕</button>
      </div>
    </div>

    <div class="doc-panel-body">
      <div v-if="panel.loading" class="doc-loading">
        <AppSpinner size="lg" /> Loading…
      </div>
      <div v-else class="doc-content" v-html="renderContent(panel.content)" />
    </div>
  </div>
</template>

<script setup>
import { marked } from 'marked'
import AppSpinner from '../ui/AppSpinner.vue'

const props = defineProps({
  panel:       { type: Object,   required: true },
  close:       { type: Function, required: true },
  downloadMD:  { type: Function, required: true },
  downloadPDF: { type: Function, required: true },
})

function renderContent(text) {
  if (!text) return ''
  try { return marked.parse(text) } catch { return text }
}
</script>

<style scoped>
.doc-panel { position: fixed; top: 0; right: 0; width: 560px; height: 100vh; background: var(--surface); border-left: 1px solid var(--border); display: flex; flex-direction: column; transform: translateX(100%); transition: transform .25s ease; z-index: 50; }
.doc-panel.open { transform: translateX(0); }

.doc-panel-header { display: flex; align-items: center; padding: 14px 16px; border-bottom: 1px solid var(--border); gap: 8px; }
.doc-panel-title  { flex: 1; font-size: 14px; font-weight: 600; color: var(--text); }
.doc-panel-actions { display: flex; gap: 6px; }

.ol-btn { padding: 5px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface-2); color: var(--text); font-size: 12px; cursor: pointer; }
.ol-btn:hover { background: var(--surface); }
.ol-btn.accent { background: var(--pri); color: var(--pri-fg); border-color: var(--pri); }
.ol-btn.close  { color: var(--muted); }

.doc-panel-body { flex: 1; overflow-y: auto; padding: 24px; }
.doc-loading    { display: flex; align-items: center; gap: 12px; padding: 40px; justify-content: center; color: var(--muted); }
.doc-content    { font-size: 14px; line-height: 1.7; color: var(--text); }
.doc-content :deep(h1) { font-size: 20px; margin: 0 0 16px; }
.doc-content :deep(h2) { font-size: 16px; margin: 24px 0 10px; }
.doc-content :deep(h3) { font-size: 14px; margin: 16px 0 8px; }
.doc-content :deep(p)  { margin: 0 0 12px; }
.doc-content :deep(pre) { background: var(--surface-2); padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 13px; }
.doc-content :deep(ul), .doc-content :deep(ol) { padding-left: 20px; margin: 0 0 12px; }
.doc-content :deep(code) { background: var(--surface-2); padding: 1px 5px; border-radius: 4px; font-size: 13px; }
</style>
