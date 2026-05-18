<!-- Skills settings tab — installed skills + browse/install -->
<template>
  <div class="ss-wrap">
    <div class="ss-heading">
      <div class="ss-title-row">
        <h2 class="ss-title">Skills</h2>
        <button class="ss-browse-btn" @click="directoryOpen = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="14" height="14">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Browse &amp; Install
        </button>
      </div>
      <p class="ss-subtitle">Skills are agent pipelines that run structured research tasks. Install skills to make them available in your chats via the <kbd>/</kbd> command.</p>
    </div>

    <div v-if="loading" class="ss-loading">Loading…</div>

    <div v-else-if="!installedSkills.length" class="ss-empty">
      No skills installed yet.
      <button class="ss-link" @click="directoryOpen = true">Browse the skill directory →</button>
    </div>

    <div v-else class="ss-list">
      <div v-for="skill in installedSkills" :key="skill.id" class="ss-card">
        <div class="ss-card-left">
          <img v-if="skillIconUrl(skill.skill_key)" :src="skillIconUrl(skill.skill_key)" class="ss-card-icon-svg" :alt="skill.name" />
          <span v-else class="ss-card-icon">{{ skill.icon || '⚡' }}</span>
          <div class="ss-card-body">
            <span class="ss-card-name">{{ skill.name }}</span>
            <span class="ss-card-desc">{{ skill.description }}</span>
          </div>
        </div>
        <button class="ss-uninstall-btn" :disabled="busy[skill.id]" @click="uninstall(skill)">
          {{ busy[skill.id] ? '…' : 'Uninstall' }}
        </button>
      </div>
    </div>

    <!-- Skill Directory modal -->
    <SkillDirectory
      v-if="directoryOpen"
      @close="directoryOpen = false"
      @changed="load"
    />
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { Api } from '../../api/service.js'
import SkillDirectory   from '../SkillDirectory.vue'
import { useSkillIcon } from '../../composables/useSkillIcon.js'

const { skillIconUrl } = useSkillIcon()

const skills   = ref([])
const loading  = ref(true)
const busy     = reactive({})
const directoryOpen = ref(false)

const installedSkills = computed(() => skills.value.filter(s => s.installed))

async function load() {
  loading.value = true
  try {
    const data = await Api.getSkills()
    skills.value = data.skills || []
  } catch (_) {
  } finally {
    loading.value = false
  }
}

async function uninstall(skill) {
  busy[skill.id] = true
  try {
    await Api.uninstallSkill(skill.skill_key)
    skill.installed = false
  } catch (_) {
  } finally {
    busy[skill.id] = false
  }
}

onMounted(load)
</script>

<style scoped>
.ss-wrap    { display: flex; flex-direction: column; gap: 24px; }
.ss-heading { display: flex; flex-direction: column; gap: 8px; }

.ss-title-row { display: flex; align-items: center; justify-content: space-between; }
.ss-title     { font-size: 15px; font-weight: 700; color: var(--text); margin: 0; }

.ss-browse-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 14px; border-radius: 8px;
  border: 1px solid var(--border); background: none;
  color: var(--text); font-size: 13px; font-weight: 600;
  cursor: pointer; transition: border-color .13s, background .13s;
}
.ss-browse-btn:hover { border-color: var(--pri); color: var(--pri); }

.ss-subtitle { font-size: 13px; color: var(--muted); margin: 0; line-height: 1.6; }
.ss-subtitle kbd {
  display: inline-block; padding: 1px 6px;
  border: 1px solid var(--border); border-radius: 4px;
  font-family: monospace; background: var(--surface-2);
}

.ss-loading { font-size: 13px; color: var(--muted); }
.ss-empty   { font-size: 13px; color: var(--muted); display: flex; align-items: center; gap: 8px; }
.ss-link    { background: none; border: none; cursor: pointer; font-size: 13px; color: var(--pri); text-decoration: underline; padding: 0; }

.ss-list { display: flex; flex-direction: column; gap: 10px; }

.ss-card {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 14px 16px; border-radius: 10px;
  background: var(--surface-2); border: 1px solid var(--border);
}
.ss-card-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
.ss-card-icon     { font-size: 20px; flex-shrink: 0; }
.ss-card-icon-svg { width: 28px; height: 28px; flex-shrink: 0; object-fit: contain; }
.ss-card-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ss-card-name { font-size: 14px; font-weight: 600; color: var(--text); }
.ss-card-desc { font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.ss-uninstall-btn {
  flex-shrink: 0; padding: 6px 14px; border-radius: 8px;
  border: 1px solid var(--border); background: none;
  color: var(--muted); font-size: 12.5px; font-weight: 600;
  cursor: pointer; transition: border-color .13s, color .13s;
}
.ss-uninstall-btn:hover:not(:disabled) { border-color: var(--danger); color: var(--danger); }
.ss-uninstall-btn:disabled { opacity: .45; cursor: not-allowed; }
</style>
