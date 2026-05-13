<template>
  <div class="cp-root">
    <aside class="cp-sidebar">
      <div class="cp-back" @click="$emit('back')">
        <span class="cp-back-arrow">←</span>
        <span>Back to Chat</span>
      </div>

      <div class="cp-nav">
        <button v-for="item in navItems" :key="item.id"
          class="cp-nav-item" :class="{ active: section === item.id }"
          @click="section = item.id">
          <span class="cp-nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </button>
      </div>
    </aside>

    <main class="cp-content">
      <AgentConfigSettings v-if="section === 'models'" />
      <AgentPromptsSettings v-else-if="section === 'prompts'" flow-id="architect" />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AgentConfigSettings  from './settings/AgentConfigSettings.vue'
import AgentPromptsSettings from './settings/AgentPromptsSettings.vue'

defineEmits(['back'])

const section  = ref('prompts')
const navItems = [
  { id: 'prompts', label: 'Agent Prompts', icon: '📝' },
  { id: 'models',  label: 'Agent Models',  icon: '⚙'  },
]
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

.cp-nav { display: flex; flex-direction: column; gap: 2px; }
.cp-nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 8px;
  font-size: 13px; font-weight: 500; color: var(--muted);
  background: none; border: none; cursor: pointer; text-align: left; width: 100%;
  transition: background .15s, color .15s;
}
.cp-nav-item:hover  { background: var(--hover); color: var(--tx); }
.cp-nav-item.active { background: var(--active-nav); color: var(--tx); font-weight: 600; }
.cp-nav-icon { font-size: 15px; width: 20px; text-align: center; flex-shrink: 0; }

.cp-content {
  flex: 1; min-width: 0; overflow-y: auto;
  padding: 40px 48px;
}
</style>
