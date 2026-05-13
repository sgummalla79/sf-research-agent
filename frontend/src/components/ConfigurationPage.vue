<template>
  <div class="cp-root">
    <aside class="cp-sidebar">
      <div class="cp-back" @click="$emit('back')">
        <span class="cp-back-arrow">←</span>
        <span>Back to Chat</span>
      </div>
      <div class="cp-title">Configuration</div>
    </aside>

    <main class="cp-content">
      <AgentConfigSettings />
    </main>
  </div>
</template>

<script setup>
import AgentConfigSettings from './settings/AgentConfigSettings.vue'
defineEmits(['back'])
</script>

<style scoped>
.cp-root {
  display: flex; height: 100%; background: var(--bg);
  color: var(--tx); overflow: hidden;
}

.cp-sidebar {
  width: 220px; flex-shrink: 0;
  background: var(--sidebar);
  border-right: 1px solid var(--bdr);
  display: flex; flex-direction: column;
  padding: 20px 12px; gap: 16px;
}

.cp-back {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 8px;
  font-size: 13px; font-weight: 500; color: var(--muted);
  cursor: pointer; transition: background .15s, color .15s;
  user-select: none;
}
.cp-back:hover { background: var(--hover); color: var(--tx); }
.cp-back-arrow { font-size: 16px; line-height: 1; }

.cp-title {
  padding: 4px 10px;
  font-size: 12px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--muted);
}

.cp-content {
  flex: 1; min-width: 0; overflow-y: auto;
  padding: 40px 48px;
}
</style>
