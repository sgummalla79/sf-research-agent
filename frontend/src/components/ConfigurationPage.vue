<template>
  <div class="cp-root">

    <!-- ── Sidebar ──────────────────────────────────────── -->
    <aside class="cp-sidebar">
      <div class="cp-back" @click="$emit('back')">
        <span class="cp-back-arrow">←</span>
        <span>Back to Chat</span>
      </div>

      <!-- Skills section -->
      <div class="cp-nav">
        <div class="cp-section-label">Skills</div>

        <div v-if="loadingSkills" class="cp-loading">Loading…</div>

        <button v-for="skill in skills" :key="skill.id"
          class="cp-nav-item" :class="{ active: section === skill.id }"
          @click="section = skill.id">
          <span class="cp-nav-icon">{{ skill.icon }}</span>
          <span>{{ skill.name }}</span>
        </button>

        <div v-if="!loadingSkills && !skills.length" class="cp-empty">
          No skills found
        </div>
      </div>

      <!-- Divider -->
      <div class="cp-divider" />

      <!-- Agent Models -->
      <div class="cp-nav">
        <button class="cp-nav-item" :class="{ active: section === 'models' }"
          @click="section = 'models'">
          <span class="cp-nav-icon">⚙</span>
          <span>Agent Models</span>
        </button>
      </div>
    </aside>

    <!-- ── Content ──────────────────────────────────────── -->
    <main class="cp-content">
      <AgentConfigSettings v-if="section === 'models'" />

      <template v-else-if="activeSkill">
        <AgentPromptsSettings :flow-id="activeSkill.id" :key="activeSkill.id" />
      </template>

      <div v-else class="cp-placeholder">
        <p>Select a skill to view and edit its agent prompts.</p>
      </div>
    </main>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import AgentConfigSettings  from './settings/AgentConfigSettings.vue'
import AgentPromptsSettings from './settings/AgentPromptsSettings.vue'

defineEmits(['back'])

const skills       = ref([])
const loadingSkills = ref(true)
const section       = ref(null)   // null | '<skill_id>' | 'models'

const activeSkill = computed(() =>
  skills.value.find(s => s.id === section.value) ?? null
)

async function fetchSkills() {
  try {
    const res  = await fetch('/api/flows')
    const data = await res.json()
    skills.value = data.flows || []
    // Auto-select first skill
    if (skills.value.length) section.value = skills.value[0].id
  } catch (_) {
    skills.value = []
  } finally {
    loadingSkills.value = false
  }
}

onMounted(fetchSkills)
</script>

<style scoped>
.cp-root {
  display: flex; height: 100%; background: var(--bg);
  color: var(--tx); overflow: hidden;
}

/* ── Sidebar ── */
.cp-sidebar {
  width: 220px; flex-shrink: 0;
  background: var(--sidebar);
  border-right: 1px solid var(--bdr);
  display: flex; flex-direction: column;
  padding: 16px 10px; gap: 8px;
  overflow-y: auto;
}

.cp-back {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 8px;
  font-size: 13px; font-weight: 500; color: var(--muted);
  cursor: pointer; transition: background .15s, color .15s;
  user-select: none; flex-shrink: 0;
}
.cp-back:hover { background: var(--hover); color: var(--tx); }
.cp-back-arrow { font-size: 16px; line-height: 1; }

.cp-section-label {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--muted);
  padding: 4px 10px 6px;
}

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

.cp-divider { height: 1px; background: var(--bdr); margin: 4px 2px; }

.cp-loading, .cp-empty {
  font-size: 12px; color: var(--muted); padding: 6px 12px;
}

/* ── Content ── */
.cp-content {
  flex: 1; min-width: 0; overflow-y: auto;
  padding: 40px 48px;
}

.cp-placeholder {
  display: flex; align-items: center; justify-content: center;
  height: 100%; color: var(--muted); font-size: 14px;
}
</style>
