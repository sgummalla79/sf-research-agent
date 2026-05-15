<!-- Artifact card — shown when a document version is ready -->
<template>
  <div class="doc-card">
    <span class="doc-card-icon">📄</span>
    <div class="doc-card-body">
      <p class="doc-card-title">Architecture Document<span v-if="docVersion"> v{{ docVersion }}</span></p>
      <p class="doc-card-sub">Ready for review</p>
    </div>
    <button class="doc-card-btn" @click="$emit('view', artifactId)">View →</button>
  </div>
</template>

<script setup>
defineProps({
  artifactId: { type: String, default: null },
  docVersion: { type: Number, default: null },
})
defineEmits(['view'])
</script>

<style scoped>
.doc-card { display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 10px; background: var(--surface-2); border: 1px solid var(--border); }
.doc-card-icon { font-size: 24px; }
.doc-card-body { flex: 1; }
.doc-card-title { font-size: 14px; font-weight: 600; color: var(--text); margin: 0 0 2px; }
.doc-card-sub   { font-size: 12px; color: var(--muted); margin: 0; }
.doc-card-btn   { padding: 6px 14px; border-radius: 6px; background: var(--pri); color: #fff; border: none; cursor: pointer; font-size: 13px; font-weight: 500; white-space: nowrap; }
.doc-card-btn:hover { opacity: .85; }
</style>
