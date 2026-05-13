<template>
  <div class="sp-root">
    <!-- ── Left sidebar ──────────────────────────────────────────── -->
    <aside class="sp-sidebar">
      <div class="sp-back" @click="$emit('back')">
        <span class="sp-back-arrow">←</span>
        <span>Back to Chat</span>
      </div>

      <div class="sp-nav-section">
        <button
          v-for="item in navItems"
          :key="item.id"
          class="sp-nav-item"
          :class="{ active: activeSection === item.id }"
          @click="activeSection = item.id"
        >
          <span class="sp-nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </button>
      </div>
    </aside>

    <!-- ── Content area ──────────────────────────────────────────── -->
    <main class="sp-content">
      <ProvidersSettings   v-if="activeSection === 'providers'" />
      <div v-else-if="activeSection === 'usage'" class="sp-usage">
        <UsageSection />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ProvidersSettings from './settings/ProvidersSettings.vue'
import UsageSection      from './settings/UsageSettings.vue'

defineEmits(['back'])

const activeSection = ref('providers')

const navItems = [
  { id: 'providers', label: 'Providers',   icon: '⚡' },
  { id: 'usage',     label: 'Usage & Cost', icon: '📊' },
]
</script>

<style scoped>
.sp-root {
  display: flex; height: 100%; background: var(--bg);
  color: var(--tx); overflow: hidden;
}

/* ── Sidebar ── */
.sp-sidebar {
  width: 220px; flex-shrink: 0;
  background: var(--sidebar);
  border-right: 1px solid var(--bdr);
  display: flex; flex-direction: column;
  padding: 20px 12px;
  gap: 24px;
}

.sp-back {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 8px;
  font-size: 13px; font-weight: 500; color: var(--muted);
  cursor: pointer; transition: background .15s, color .15s;
  user-select: none;
}
.sp-back:hover { background: var(--hover); color: var(--tx); }
.sp-back-arrow { font-size: 16px; line-height: 1; }

.sp-nav-section { display: flex; flex-direction: column; gap: 2px; }

.sp-nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 8px;
  font-size: 13px; font-weight: 500; color: var(--muted);
  background: none; border: none; cursor: pointer; text-align: left; width: 100%;
  transition: background .15s, color .15s;
}
.sp-nav-item:hover  { background: var(--hover); color: var(--tx); }
.sp-nav-item.active { background: var(--active-nav); color: var(--tx); font-weight: 600; }
.sp-nav-icon { font-size: 15px; width: 20px; text-align: center; flex-shrink: 0; }

/* ── Content ── */
.sp-content {
  flex: 1; min-width: 0; overflow-y: auto;
  padding: 40px 48px;
}

.sp-usage { /* usage section inherits from inner component */ }
</style>
