<!--
  SettingsPage — full-page settings overlay, matches main branch pattern.
  Emits: @back — return to chat
-->
<template>
  <div class="sp-root">

    <!-- ── Left nav sidebar ──────────────────────────────────────────────── -->
    <aside class="sp-sidebar">
      <button class="sp-back" @click="$emit('back')">
        <span class="sp-back-arrow">←</span>
        <span>Back to Chat</span>
      </button>

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

    <!-- ── Content area ──────────────────────────────────────────────────── -->
    <!-- Skills section takes full height — no padding -->
    <ConfigurationPage v-if="activeSection === 'skills'" />

    <main class="sp-content" v-else>
      <ProvidersSettings    v-if="activeSection === 'providers'" />
      <AgentConfigSettings  v-else-if="activeSection === 'agents'" />
      <AgentPromptsSettings v-else-if="activeSection === 'prompts'" />
      <UsageSettings        v-else-if="activeSection === 'usage'" />
      <ThemeSettings        v-else-if="activeSection === 'theme'" />
    </main>


  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import ConfigurationPage    from './ConfigurationPage.vue'
import ProvidersSettings    from './settings/ProvidersSettings.vue'
import AgentConfigSettings  from './settings/AgentConfigSettings.vue'
import AgentPromptsSettings from './settings/AgentPromptsSettings.vue'
import UsageSettings        from './settings/UsageSettings.vue'
import ThemeSettings        from './settings/ThemeSettings.vue'

const props = defineProps({
  initialTab: { type: String, default: 'providers' },
})

defineEmits(['back'])

const activeSection = ref(props.initialTab)

// Sync when parent changes the tab (e.g. "Manage skills" while settings already open)
watch(() => props.initialTab, (tab) => { activeSection.value = tab })

const navItems = [
  { id: 'providers', label: 'Providers',    icon: '⚡' },
  { id: 'skills',    label: 'Skills',       icon: '🧩' },
  { id: 'usage',     label: 'Usage & Cost', icon: '📊' },
]
</script>

<style scoped>
.sp-root {
  display: flex; flex: 1; height: 100%;
  background: var(--bg); color: var(--text); overflow: hidden;
}

.sp-sidebar {
  width: 220px; flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  padding: 20px 12px; gap: 24px;
}

.sp-back {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 8px;
  font-size: 13px; font-weight: 500; color: var(--muted);
  cursor: pointer; border: none; background: none;
  transition: background .15s, color .15s; text-align: left; width: 100%;
}
.sp-back:hover { background: var(--hover); color: var(--text); }
.sp-back-arrow { font-size: 16px; line-height: 1; }

.sp-nav-section { display: flex; flex-direction: column; gap: 2px; }

.sp-nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 8px;
  font-size: 13px; font-weight: 500; color: var(--muted);
  background: none; border: none; cursor: pointer;
  text-align: left; width: 100%;
  transition: background .15s, color .15s;
}
.sp-nav-item:hover  { background: var(--hover); color: var(--text); }
.sp-nav-item.active { background: var(--sbg); color: var(--text); font-weight: 600; }
.sp-nav-icon { font-size: 15px; width: 20px; text-align: center; flex-shrink: 0; }

.sp-content {
  flex: 1; min-width: 0; overflow-y: auto;
  padding: 40px 48px;
}
</style>
