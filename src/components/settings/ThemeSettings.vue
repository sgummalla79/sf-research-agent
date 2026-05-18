<!-- Theme picker — uses useTheme composable -->
<template>
  <div class="ts-wrap">
    <div class="ts-heading">
      <h2 class="ts-title">Theme</h2>
      <p class="ts-subtitle">Choose an accent colour. Dark mode follows your system preference.</p>
    </div>

    <div class="ts-grid">
      <button
        v-for="t in THEMES"
        :key="t.id"
        class="ts-swatch"
        :class="{ active: activeThemeId === t.id }"
        @click="pick(t.id)">
        <span class="ts-dot" :style="{ background: isDark ? t.dark : t.light }" />
        <span class="ts-label">{{ t.label }}</span>
        <svg v-if="activeThemeId === t.id" class="ts-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { THEMES, useTheme } from '../../composables/useTheme'

const { activeThemeId, saveTheme } = useTheme()
const isDark = computed(() => window.matchMedia('(prefers-color-scheme: dark)').matches)

function pick(id) {
  saveTheme(id, isDark.value)
}
</script>

<style scoped>
.ts-wrap    { padding: 20px 20px 32px; }
.ts-heading { margin-bottom: 20px; }
.ts-title   { font-size: 15px; font-weight: 700; color: var(--text); margin: 0 0 4px; }
.ts-subtitle { font-size: 13px; color: var(--muted); margin: 0; line-height: 1.5; }

.ts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 10px;
}

.ts-swatch {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 10px;
  background: var(--surface-2); border: 1.5px solid var(--border);
  cursor: pointer; transition: border-color .13s, background .13s;
}
.ts-swatch:hover  { border-color: var(--pri); }
.ts-swatch.active { border-color: var(--pri); background: var(--hover); }

.ts-dot   { width: 16px; height: 16px; border-radius: 50%; flex-shrink: 0; }
.ts-label { flex: 1; font-size: 13px; font-weight: 500; color: var(--text); text-align: left; }
.ts-check { color: var(--pri); flex-shrink: 0; }
</style>
