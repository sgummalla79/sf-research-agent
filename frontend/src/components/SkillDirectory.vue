<template>
  <div class="sd-overlay" @click.self="$emit('close')">
    <div class="sd-modal">

      <!-- Header -->
      <div class="sd-header">
        <div class="sd-header-left">
          <span class="sd-title">Skill Directory</span>
          <span class="sd-subtitle">{{ available.length }} skill{{ available.length !== 1 ? 's' : '' }} available</span>
        </div>
        <button class="sd-close" @click="$emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="16" height="16"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <!-- Search -->
      <div class="sd-search-wrap">
        <svg class="sd-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input v-model="query" class="sd-search" placeholder="Search skills…" autofocus />
      </div>

      <!-- Grid -->
      <div class="sd-grid">
        <div v-if="!filtered.length" class="sd-empty">No skills match your search.</div>

        <div v-for="skill in filtered" :key="skill.id" class="sd-card" :class="{ installed: skill.installed }">
          <div class="sd-card-top">
            <span class="sd-card-icon">{{ skill.icon }}</span>
            <button v-if="skill.installed" class="sd-uninstall-btn" :disabled="busy[skill.id]"
              @click="toggle(skill)">
              {{ busy[skill.id] ? '…' : 'Uninstall' }}
            </button>
            <button v-else class="sd-install-btn" :disabled="busy[skill.id]"
              @click="toggle(skill)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="13" height="13"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              {{ busy[skill.id] ? '…' : 'Install' }}
            </button>
          </div>
          <div class="sd-card-name">{{ skill.name }}</div>
          <div class="sd-card-desc">{{ skill.description }}</div>
          <div v-if="skill.installed" class="sd-installed-badge">Installed ✓</div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { apiFetch } from '../composables/useFetch.js'
import { ref, computed, reactive, onMounted } from 'vue'

const emit = defineEmits(['close', 'installed'])

const skills = ref([])
const query  = ref('')
const busy   = reactive({})

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q
    ? skills.value.filter(s => s.name.toLowerCase().includes(q) || s.description?.toLowerCase().includes(q))
    : skills.value
})

const available = computed(() => skills.value)

async function load() {
  try {
    const res  = await apiFetch('/api/skills')
    const data = await res.json()
    skills.value = data.skills || []
  } catch (_) {}
}

async function toggle(skill) {
  busy[skill.id] = true
  try {
    if (skill.installed) {
      await apiFetch(`/api/skills/${skill.id}`, { method: 'DELETE' })
      skill.installed = false
    } else {
      await apiFetch(`/api/skills/${skill.id}`, { method: 'POST' })
      skill.installed = true
      emit('installed', skill.id)
    }
  } catch (_) {} finally {
    busy[skill.id] = false
  }
}

onMounted(load)
</script>

<style scoped>
.sd-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.5);
  display: flex; align-items: center; justify-content: center; z-index: 800;
}

.sd-modal {
  width: 680px; max-width: 94vw; max-height: 80vh;
  background: var(--surf); border: 1px solid var(--bdr); border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,.3);
  display: flex; flex-direction: column; overflow: hidden;
}

/* Header */
.sd-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 22px 24px 0; flex-shrink: 0;
}
.sd-header-left { display: flex; flex-direction: column; gap: 3px; }
.sd-title    { font-size: 18px; font-weight: 700; color: var(--tx); }
.sd-subtitle { font-size: 12px; color: var(--muted); }
.sd-close {
  width: 30px; height: 30px; border-radius: 7px; border: none;
  background: transparent; color: var(--muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.sd-close:hover { background: rgba(100,116,139,.13); color: var(--tx); }

/* Search */
.sd-search-wrap {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 24px 10px; flex-shrink: 0;
}
.sd-search-icon { color: var(--muted); flex-shrink: 0; }
.sd-search {
  flex: 1; background: var(--inp); border: 1.5px solid var(--bdr); border-radius: 8px;
  padding: 8px 12px; font-size: 14px; color: var(--tx); outline: none;
}
.sd-search:focus { border-color: var(--ifocus); }
.sd-search::placeholder { color: var(--muted); }

/* Grid */
.sd-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px; padding: 10px 24px 24px; overflow-y: auto; flex: 1;
}
.sd-empty { grid-column: 1 / -1; text-align: center; color: var(--muted); font-size: 14px; padding: 32px; }

.sd-card {
  background: var(--surf2); border: 1.5px solid var(--bdr); border-radius: 12px;
  padding: 16px; display: flex; flex-direction: column; gap: 6px;
}
.sd-card.installed { border-color: #22c55e55; }

.sd-card-top {
  display: flex; align-items: center; justify-content: space-between;
}
.sd-card-icon { font-size: 20px; }

.sd-install-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 12px; border-radius: 7px; border: 1.5px solid var(--bdr);
  background: transparent; color: var(--tx); font-size: 12px; font-weight: 600;
  cursor: pointer;
}
.sd-install-btn:hover:not(:disabled) { border-color: var(--pri); color: var(--pri); }
.sd-install-btn:disabled { opacity: .5; cursor: not-allowed; }

.sd-uninstall-btn {
  padding: 5px 12px; border-radius: 7px; border: 1.5px solid var(--bdr);
  background: transparent; color: var(--muted); font-size: 12px; font-weight: 600;
  cursor: pointer;
}
.sd-uninstall-btn:hover:not(:disabled) { border-color: #ef4444; color: #ef4444; }
.sd-uninstall-btn:disabled { opacity: .5; cursor: not-allowed; }

.sd-card-name { font-size: 14px; font-weight: 700; color: var(--tx); }
.sd-card-desc { font-size: 12px; color: var(--muted); line-height: 1.5; flex: 1; }

.sd-installed-badge {
  font-size: 11px; font-weight: 600; color: #22c55e;
  margin-top: 4px;
}
</style>
