<!-- ConfigurationPage — file-tree + prompt editor, adapted for new backend -->
<template>
  <div class="cp-root">

    <!-- ══ LEFT — file tree ══ -->
    <aside class="cp-sidebar">
      <button class="cp-back" @click="$emit('back')">
        <span class="cp-back-arrow">←</span>
        <span>Back to Chat</span>
      </button>

      <div class="cp-tree-header">
        <span class="cp-tree-label">Skills</span>
        <button class="cp-add-btn" title="Browse & install skills" @click="directoryOpen = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="13" height="13">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
      </div>

      <div class="cp-tree">
        <div v-if="loading" class="cp-loading-hint">Loading…</div>
        <div v-else-if="!skills.length" class="cp-loading-hint">No skills installed. Click + to browse.</div>

        <div v-for="skill in skills" :key="skill.id" class="cp-skill-block">
          <div class="cp-skill-row-wrap">
            <button class="cp-skill-row" @click="toggleSkill(skill)">
              <span class="cp-chevron">{{ expanded[skill.id] ? '▾' : '▸' }}</span>
              <span class="cp-skill-icon">{{ skill.icon || '⚡' }}</span>
              <span class="cp-skill-name">{{ skill.name }}</span>
            </button>
            <button class="cp-skill-uninstall" title="Uninstall" @click.stop="confirmUninstall(skill)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="12" height="12">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                <path d="M10 11v6M14 11v6M9 6V4h6v2"/>
              </svg>
            </button>
          </div>

          <div v-if="expanded[skill.id]" class="cp-subtree">
            <button class="cp-tree-file"
              :class="{ active: sel?.type === 'manifest' && sel?.skillId === skill.id }"
              @click="select({ type: 'manifest', skillId: skill.id })">
              <span class="cp-file-icon">📄</span> SKILL.md
            </button>

            <button class="cp-tree-folder-row" @click="toggleFolder(skill.id, 'agents')">
              <span class="cp-chevron sm">{{ folderOpen(skill.id, 'agents') ? '▾' : '▸' }}</span>
              <span class="cp-file-icon">📁</span> agents
            </button>
            <div v-if="folderOpen(skill.id, 'agents')" class="cp-folder-items">
              <div v-if="!skillAgents[skill.id]" class="cp-loading-hint">Loading…</div>
              <button v-for="agent in (skillAgents[skill.id] || [])" :key="agent.agent_key"
                class="cp-tree-file indent"
                :class="{ active: sel?.type === 'agent' && sel?.skillId === skill.id && sel?.agentKey === agent.agent_key }"
                @click="select({ type: 'agent', skillId: skill.id, skillKey: skill.skill_key, agentKey: agent.agent_key, label: agent.label || agent.agent_key })">
                <span class="cp-file-icon">📝</span>
                {{ agent.label || agent.agent_key }}
                <span v-if="agent.has_draft" class="cp-draft-dot" title="Unpublished draft" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- ══ RIGHT — content panel ══ -->
    <main class="cp-content">

      <!-- Skill overview -->
      <div v-if="sel?.type === 'manifest' && activeSkill" class="cp-manifest">
        <div class="cp-manifest-header">
          <span class="cp-manifest-icon">{{ activeSkill.icon || '⚡' }}</span>
          <div class="cp-manifest-header-body">
            <div class="cp-manifest-name-row">
              <span class="cp-manifest-name">{{ activeSkill.name }}</span>
              <span v-if="skillHasDraft[activeSkill.id]" class="cp-draft-badge">draft pending</span>
            </div>
            <div class="cp-manifest-desc">{{ activeSkill.description }}</div>
          </div>
          <button class="cp-publish-btn"
            :disabled="!skillHasDraft[activeSkill.id] || publishing"
            @click="publishSkill(activeSkill.skill_key)">
            {{ publishing ? 'Publishing…' : 'Publish All Drafts' }}
          </button>
        </div>

        <div v-if="publishMsg" class="cp-publish-msg" :class="publishMsg.type">{{ publishMsg.text }}</div>

        <div class="cp-manifest-section">
          <div class="cp-manifest-label">Agents</div>
          <div class="cp-agent-list">
            <div v-for="agent in (skillAgents[activeSkill.id] || [])" :key="agent.agent_key"
              class="cp-agent-chip"
              @click="select({ type: 'agent', skillId: activeSkill.id, skillKey: activeSkill.skill_key, agentKey: agent.agent_key, label: agent.label || agent.agent_key })">
              {{ agent.label || agent.agent_key }}
              <span v-if="agent.has_draft" class="cp-draft-dot" />
            </div>
          </div>
        </div>
      </div>

      <!-- Agent prompt editor -->
      <AgentPromptsSettings
        v-else-if="sel?.type === 'agent'"
        :key="`${sel.skillKey}/${sel.agentKey}`"
      />

      <div v-else class="cp-empty-state">
        <p>Select a skill or agent from the tree.</p>
      </div>

    </main>
  </div>

  <SkillDirectory v-if="directoryOpen" @close="directoryOpen = false" @changed="fetchSkills" />

  <Transition name="fade">
    <div v-if="uninstallTarget" class="del-overlay" @click.self="uninstallTarget = null">
      <div class="del-dialog">
        <p class="del-title">Uninstall {{ uninstallTarget.name }}?</p>
        <p class="del-body">Removed from chat menu. You can reinstall anytime from the skill directory.</p>
        <div class="del-btns">
          <button class="del-cancel" @click="uninstallTarget = null">Cancel</button>
          <button class="del-confirm" @click="executeUninstall">Uninstall</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { apiFetch }         from '../composables/useFetch.js'
import AgentPromptsSettings from './settings/AgentPromptsSettings.vue'
import SkillDirectory       from './SkillDirectory.vue'

defineEmits(['back'])

const skills        = ref([])
const loading       = ref(true)
const skillAgents   = reactive({})
const skillHasDraft = reactive({})
const expanded      = reactive({})
const openFolders   = reactive({})
const sel           = ref(null)
const directoryOpen  = ref(false)
const uninstallTarget = ref(null)
const publishing    = ref(false)
const publishMsg    = ref(null)

const activeSkill = computed(() => skills.value.find(s => s.id === sel.value?.skillId) ?? null)

async function fetchSkills() {
  loading.value = true
  try {
    const res  = await apiFetch('/api/skills')
    const data = await res.json()
    skills.value = (data.skills || []).filter(s => s.installed)
    if (skills.value.length && !sel.value) {
      const first = skills.value[0]
      expanded[first.id] = true
      await loadAgents(first)
      openFolders[`${first.id}/agents`] = true
      sel.value = { type: 'manifest', skillId: first.id }
    }
  } catch (_) {
  } finally {
    loading.value = false
  }
}

async function loadAgents(skill) {
  try {
    const res  = await apiFetch(`/api/skills/${skill.skill_key}/agents`)
    const data = await res.json()
    skillAgents[skill.id]   = data.agents   || []
    skillHasDraft[skill.id] = data.has_draft || false
  } catch (_) {
    skillAgents[skill.id]   = []
    skillHasDraft[skill.id] = false
  }
}

async function publishSkill(skillKey) {
  publishing.value = true
  publishMsg.value = null
  try {
    const res  = await apiFetch(`/api/skills/${skillKey}/publish`, { method: 'POST' })
    const data = await res.json()
    if (res.ok) {
      publishMsg.value = { type: 'ok', text: `Published ${data.count} agent${data.count !== 1 ? 's' : ''}.` }
      const skill = skills.value.find(s => s.skill_key === skillKey)
      if (skill) await loadAgents(skill)
    } else {
      publishMsg.value = { type: 'err', text: data.detail || 'Publish failed.' }
    }
  } catch (_) {
    publishMsg.value = { type: 'err', text: 'Network error.' }
  } finally {
    publishing.value = false
  }
}

async function toggleSkill(skill) {
  expanded[skill.id] = !expanded[skill.id]
  if (expanded[skill.id]) await loadAgents(skill)
}

function toggleFolder(skillId, folder) {
  openFolders[`${skillId}/${folder}`] = !openFolders[`${skillId}/${folder}`]
}

function folderOpen(skillId, folder) {
  return !!openFolders[`${skillId}/${folder}`]
}

function select(item) {
  publishMsg.value = null
  sel.value = item
  if (item.type === 'manifest') {
    const skill = skills.value.find(s => s.id === item.skillId)
    if (skill && !skillAgents[skill.id]) loadAgents(skill)
  }
}

function confirmUninstall(skill) { uninstallTarget.value = skill }

async function executeUninstall() {
  const skill = uninstallTarget.value
  uninstallTarget.value = null
  await apiFetch(`/api/skills/${skill.skill_key}`, { method: 'DELETE' })
  if (sel.value?.skillId === skill.id) sel.value = null
  await fetchSkills()
}

onMounted(fetchSkills)
</script>

<style scoped>
.cp-root { display: flex; flex: 1; min-width: 0; height: 100%; background: var(--bg); color: var(--text); overflow: hidden; }

/* ── Sidebar ── */
.cp-back {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 14px 8px; width: 100%; border: none; background: none;
  font-size: 13px; font-weight: 500; color: var(--muted);
  cursor: pointer; transition: color .15s; text-align: left;
}
.cp-back:hover { color: var(--text); }
.cp-back-arrow { font-size: 16px; line-height: 1; }

.cp-sidebar {
  width: 260px; flex-shrink: 0;
  background: var(--surface); border-right: 1px solid var(--border);
  display: flex; flex-direction: column; overflow-y: auto;
}
.cp-tree-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 10px 6px; flex-shrink: 0;
}
.cp-tree-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.cp-add-btn {
  width: 22px; height: 22px; border-radius: 5px; border: 1px solid var(--border);
  background: transparent; color: var(--muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.cp-add-btn:hover { background: var(--hover); color: var(--text); }
.cp-tree { display: flex; flex-direction: column; padding: 4px 6px 16px; flex: 1; }
.cp-loading-hint { font-size: 12px; color: var(--muted); padding: 8px 10px; }

.cp-skill-block { margin-bottom: 2px; }
.cp-skill-row-wrap { display: flex; align-items: center; border-radius: 7px; }
.cp-skill-row-wrap:hover { background: var(--hover); }
.cp-skill-row-wrap:hover .cp-skill-uninstall { opacity: 1; }

.cp-skill-row {
  display: flex; align-items: center; gap: 7px; flex: 1;
  padding: 7px 8px; border: none; background: none;
  cursor: pointer; text-align: left; font-size: 13px; font-weight: 600; color: var(--text);
}
.cp-skill-uninstall {
  flex-shrink: 0; opacity: 0; margin-right: 4px;
  width: 22px; height: 22px; border: none; border-radius: 4px;
  background: transparent; color: var(--muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: opacity .12s;
}
.cp-skill-uninstall:hover { background: rgba(239,68,68,.1); color: #ef4444; }

.cp-chevron    { font-size: 11px; color: var(--muted); width: 10px; flex-shrink: 0; }
.cp-chevron.sm { font-size: 9px; }
.cp-skill-icon { font-size: 15px; flex-shrink: 0; }
.cp-skill-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.cp-subtree { padding-left: 12px; }
.cp-folder-items { padding-left: 8px; }

.cp-tree-file, .cp-tree-folder-row {
  display: flex; align-items: center; gap: 6px; width: 100%;
  padding: 5px 8px; border-radius: 6px; border: none; background: none;
  cursor: pointer; text-align: left; font-size: 13px; color: var(--muted);
  transition: background .13s, color .13s;
}
.cp-tree-file:hover, .cp-tree-folder-row:hover { background: var(--hover); color: var(--text); }
.cp-tree-file.active { background: var(--sbg); color: var(--text); font-weight: 500; }
.cp-tree-file.indent { padding-left: 22px; }
.cp-file-icon { font-size: 13px; flex-shrink: 0; }
.cp-draft-dot { width: 6px; height: 6px; border-radius: 50%; background: #f59e0b; flex-shrink: 0; margin-left: auto; }

/* ── Content ── */
.cp-content { flex: 1; min-width: 0; overflow-y: auto; }
.cp-manifest { padding: 36px 48px; display: flex; flex-direction: column; gap: 28px; }

.cp-manifest-header      { display: flex; align-items: flex-start; gap: 16px; }
.cp-manifest-icon        { font-size: 40px; line-height: 1; flex-shrink: 0; }
.cp-manifest-header-body { flex: 1; min-width: 0; }
.cp-manifest-name-row    { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.cp-manifest-name        { font-size: 22px; font-weight: 700; color: var(--text); }
.cp-manifest-desc        { font-size: 14px; color: var(--muted); line-height: 1.6; max-width: 580px; }
.cp-draft-badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 99px; background: #fef3c7; color: #92400e; }

.cp-publish-btn {
  flex-shrink: 0; padding: 8px 18px; border-radius: 8px;
  background: var(--pri); color: #fff; border: none; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity .13s;
}
.cp-publish-btn:hover:not(:disabled) { opacity: .88; }
.cp-publish-btn:disabled { opacity: .4; cursor: not-allowed; }

.cp-publish-msg { font-size: 12.5px; padding: 8px 12px; border-radius: 7px; }
.cp-publish-msg.ok  { background: #dcfce7; color: #166534; }
.cp-publish-msg.err { background: #fee2e2; color: #991b1b; }

.cp-manifest-section { display: flex; flex-direction: column; gap: 10px; }
.cp-manifest-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); }

.cp-agent-list { display: flex; gap: 8px; flex-wrap: wrap; }
.cp-agent-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 8px;
  background: var(--surface-2); border: 1px solid var(--border);
  font-size: 13px; color: var(--text); cursor: pointer; transition: border-color .13s;
}
.cp-agent-chip:hover { border-color: var(--pri); color: var(--pri); }

.cp-empty-state { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--muted); font-size: 14px; }

/* ── Delete dialog ── */
.del-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 900; }
.del-dialog { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 24px 28px; width: 360px; display: flex; flex-direction: column; gap: 10px; box-shadow: 0 16px 48px rgba(0,0,0,.25); }
.del-title { font-size: 16px; font-weight: 700; color: var(--text); margin: 0; }
.del-body  { font-size: 13px; color: var(--muted); margin: 0; line-height: 1.55; }
.del-btns  { display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }
.del-cancel { padding: 8px 16px; border-radius: 8px; border: 1px solid var(--border); background: transparent; color: var(--text); font-size: 13px; font-weight: 500; cursor: pointer; }
.del-confirm { padding: 8px 16px; border-radius: 8px; background: #dc2626; color: #fff; border: none; font-size: 13px; font-weight: 600; cursor: pointer; }

.fade-enter-active, .fade-leave-active { transition: opacity .15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
