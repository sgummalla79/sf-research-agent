<template>
  <div class="cp-root">

    <!-- ══════════ LEFT — file tree ══════════ -->
    <aside class="cp-sidebar">

      <div class="cp-back" @click="$emit('back')">
        <span class="cp-back-arrow">←</span>
        <span>Back to Chat</span>
      </div>

      <!-- Skills header with + button -->
      <div class="cp-tree-header">
        <span class="cp-tree-label">Skills</span>
        <button class="cp-add-btn" title="Browse & install skills" @click="directoryOpen = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="13" height="13"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>
      </div>

      <div class="cp-tree">

        <!-- ── Skills ── -->
        <div v-for="skill in skills" :key="skill.id" class="cp-skill-block">

          <!-- Skill row -->
          <div class="cp-skill-row-wrap">
            <button class="cp-skill-row" @click="toggleSkill(skill.id)">
              <span class="cp-chevron">{{ expanded[skill.id] ? '▾' : '▸' }}</span>
              <span class="cp-skill-icon">{{ skill.icon }}</span>
              <span class="cp-skill-name">{{ skill.name }}</span>
            </button>
            <button class="cp-skill-uninstall" title="Uninstall skill"
              @click.stop="confirmUninstall(skill)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="12" height="12"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
            </button>
          </div>

          <!-- File tree (expanded) -->
          <div v-if="expanded[skill.id]" class="cp-subtree">

            <!-- SKILL.md -->
            <button class="cp-tree-file"
              :class="{ active: sel?.type === 'manifest' && sel?.skillId === skill.id }"
              @click="select({ type: 'manifest', skillId: skill.id })">
              <span class="cp-file-icon">📄</span> SKILL.md
            </button>

            <!-- agents/ -->
            <button class="cp-tree-folder-row"
              @click="toggleFolder(skill.id, 'agents')">
              <span class="cp-chevron sm">{{ folderOpen(skill.id, 'agents') ? '▾' : '▸' }}</span>
              <span class="cp-file-icon">📁</span> agents
            </button>
            <div v-if="folderOpen(skill.id, 'agents')" class="cp-folder-items">
              <div v-if="!skillAgents[skill.id]" class="cp-loading-hint">Loading…</div>
              <button v-for="agent in skillAgents[skill.id]" :key="agent.agent_key"
                class="cp-tree-file indent"
                :class="{ active: sel?.type === 'agent' && sel?.skillId === skill.id && sel?.agentKey === agent.agent_key }"
                @click="select({ type: 'agent', skillId: skill.id, agentKey: agent.agent_key, label: agent.label })">
                <span class="cp-file-icon">📝</span>
                {{ agent.label }}
                <span v-if="agent.draft" class="cp-draft-dot" title="Unpublished draft" />
              </button>
            </div>

            <!-- other folders -->
            <button v-for="folder in otherFolders" :key="folder.id"
              class="cp-tree-file"
              :class="{ active: sel?.type === 'folder' && sel?.skillId === skill.id && sel?.folder === folder.id }"
              @click="select({ type: 'folder', skillId: skill.id, folder: folder.id })">
              <span class="cp-file-icon">📁</span> {{ folder.id }}
            </button>

          </div>
        </div>


      </div>
    </aside>

    <!-- ══════════ RIGHT — content panel ══════════ -->
    <main class="cp-content">

      <!-- Skill overview (SKILL.md) -->
      <div v-if="sel?.type === 'manifest' && activeSkill" class="cp-manifest">
        <div class="cp-manifest-header">
          <span class="cp-manifest-icon">{{ activeSkill.icon }}</span>
          <div>
            <div class="cp-manifest-name">{{ activeSkill.name }}</div>
            <div class="cp-manifest-desc">{{ activeSkill.description }}</div>
          </div>
        </div>
        <div class="cp-manifest-section">
          <div class="cp-manifest-label">Pipeline</div>
          <div class="cp-pipeline">
            <template v-for="(stage, i) in (activeSkill.pipeline || [])" :key="stage">
              <span class="cp-stage-chip">{{ stage }}</span>
              <span v-if="i < activeSkill.pipeline.length - 1" class="cp-arrow">→</span>
            </template>
          </div>
        </div>
        <div class="cp-manifest-section">
          <div class="cp-manifest-label">Agents</div>
          <div class="cp-agent-list">
            <div v-for="agent in (skillAgents[activeSkill.id] || [])" :key="agent.agent_key"
              class="cp-agent-chip"
              @click="select({ type: 'agent', skillId: activeSkill.id, agentKey: agent.agent_key, label: agent.label })">
              {{ agent.label }}
              <span v-if="agent.draft" class="cp-draft-dot" />
            </div>
          </div>
        </div>
      </div>

      <!-- Agent prompt editor -->
      <AgentPromptsSettings
        v-else-if="sel?.type === 'agent'"
        :flow-id="sel.skillId"
        :selected-key="sel.agentKey"
        :key="`${sel.skillId}/${sel.agentKey}`"
      />

      <!-- Folder placeholder -->
      <div v-else-if="sel?.type === 'folder'" class="cp-folder-placeholder">
        <div class="cp-ph-icon">{{ folderMeta[sel.folder]?.icon ?? '📁' }}</div>
        <div class="cp-ph-name">{{ sel.folder }}/</div>
        <div class="cp-ph-desc">{{ folderMeta[sel.folder]?.desc ?? '' }}</div>
      </div>


      <!-- Nothing selected -->
      <div v-else class="cp-empty-state">
        <p>Select a file from the tree to get started.</p>
      </div>

    </main>
  </div>

  <!-- ── Skill Directory modal ── -->
  <SkillDirectory v-if="directoryOpen" @close="directoryOpen = false" @installed="onSkillInstalled" />

  <!-- ── Uninstall confirm ── -->
  <transition name="fade">
    <div v-if="uninstallConfirm.show" class="del-overlay" @click.self="uninstallConfirm.show = false">
      <div class="del-dialog">
        <p class="del-title">Uninstall {{ uninstallConfirm.skill?.name }}?</p>
        <p class="del-body">It will be removed from the chat menu. The skill files stay on disk — you can reinstall it anytime from the skill directory.</p>
        <div class="del-btns">
          <button class="del-cancel" @click="uninstallConfirm.show = false">Cancel</button>
          <button class="del-confirm" @click="executeUninstall">Uninstall</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import AgentPromptsSettings from './settings/AgentPromptsSettings.vue'
import SkillDirectory from './SkillDirectory.vue'

defineEmits(['back'])

// ── State ─────────────────────────────────────────────────────────────────────

const skills      = ref([])           // installed skills from /api/flows
const skillAgents = reactive({})      // skillId → agents[]
const expanded    = reactive({})      // skillId → bool
const openFolders = reactive({})      // `${skillId}/${folder}` → bool
const sel         = ref(null)         // current selection
const directoryOpen     = ref(false)
const uninstallConfirm  = reactive({ show: false, skill: null })

const otherFolders = [
  { id: 'assets' },
  { id: 'references' },
  { id: 'eval-viewer' },
  { id: 'scripts' },
]

const folderMeta = {
  assets:        { icon: '🎨', desc: 'Document templates, CSS, and output format files.' },
  references:    { icon: '📚', desc: 'Curated official documentation — research agents consult these for accurate platform-specific guidance.' },
  'eval-viewer': { icon: '🔬', desc: 'Test cases and evaluation config. Run evaluations before publishing new prompt versions.' },
  scripts:       { icon: '⚙',  desc: 'Validation and evaluation scripts. validate_prompt.py runs before each publish.' },
}

const activeSkill = computed(() =>
  skills.value.find(s => s.id === sel.value?.skillId) ?? null
)

// ── Data fetching ─────────────────────────────────────────────────────────────

async function fetchSkills() {
  try {
    const res  = await fetch('/api/flows')
    const data = await res.json()
    skills.value = data.flows || []
    if (skills.value.length) {
      const first = skills.value[0]
      expanded[first.id] = true
      await loadAgents(first.id)
      openFolders[`${first.id}/agents`] = true
      // Fetch pipeline info
      await fetchSkillPipeline(first.id)
      sel.value = { type: 'manifest', skillId: first.id }
    }
  } catch (_) {}
}

async function loadAgents(skillId) {
  if (skillAgents[skillId]) return
  try {
    const res  = await fetch(`/api/prompts/${skillId}`)
    const data = await res.json()
    skillAgents[skillId] = data.agents || []
  } catch (_) {
    skillAgents[skillId] = []
  }
}

async function fetchSkillPipeline(skillId) {
  // Enrich skill with pipeline info from manifest endpoint (future)
  // For now pipeline is not in /api/flows — show agents list instead
}

// ── Tree interactions ─────────────────────────────────────────────────────────

async function toggleSkill(skillId) {
  expanded[skillId] = !expanded[skillId]
  if (expanded[skillId]) await loadAgents(skillId)
}

function toggleFolder(skillId, folder) {
  const key = `${skillId}/${folder}`
  openFolders[key] = !openFolders[key]
  if (openFolders[key] && folder === 'agents') loadAgents(skillId)
}

function folderOpen(skillId, folder) {
  return !!openFolders[`${skillId}/${folder}`]
}

function select(item) {
  sel.value = item
  if (item.type === 'agent' || item.type === 'manifest') {
    if (!skillAgents[item.skillId]) loadAgents(item.skillId)
  }
}

function confirmUninstall(skill) {
  uninstallConfirm.skill = skill
  uninstallConfirm.show  = true
}

async function executeUninstall() {
  const skill = uninstallConfirm.skill
  uninstallConfirm.show = false
  await fetch(`/api/skills/${skill.id}`, { method: 'DELETE' })
  // Clear selection if we just uninstalled the active skill
  if (sel.value?.skillId === skill.id) sel.value = null
  await fetchSkills()
}

async function onSkillInstalled() {
  await fetchSkills()
}

onMounted(fetchSkills)
</script>

<style scoped>
.cp-root {
  display: flex; height: 100%; background: var(--bg);
  color: var(--tx); overflow: hidden; font-family: inherit;
}

/* ── Sidebar ── */
.cp-sidebar {
  width: 260px; flex-shrink: 0;
  background: var(--sidebar);
  border-right: 1px solid var(--bdr);
  display: flex; flex-direction: column;
  overflow-y: auto;
}

.cp-back {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 14px 10px;
  font-size: 13px; font-weight: 500; color: var(--muted);
  cursor: pointer; transition: color .15s;
  user-select: none; flex-shrink: 0; border: none; background: none;
}
.cp-back:hover { color: var(--tx); }
.cp-back-arrow { font-size: 16px; line-height: 1; }

.cp-tree-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 8px 2px; flex-shrink: 0;
}
.cp-tree-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.cp-add-btn {
  width: 22px; height: 22px; border-radius: 5px; border: 1px solid var(--bdr);
  background: transparent; color: var(--muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.cp-add-btn:hover { background: var(--hover); color: var(--tx); }

.cp-tree { display: flex; flex-direction: column; padding: 4px 6px 16px; flex: 1; }

/* Skill block */
.cp-skill-block { margin-bottom: 2px; }

.cp-skill-row-wrap {
  display: flex; align-items: center; border-radius: 7px;
}
.cp-skill-row-wrap:hover { background: var(--hover); }
.cp-skill-row-wrap:hover .cp-skill-uninstall { opacity: 1; }

.cp-skill-row {
  display: flex; align-items: center; gap: 7px; flex: 1;
  padding: 7px 8px; border-radius: 7px; border: none;
  background: none; cursor: pointer; text-align: left;
  font-size: 13px; font-weight: 600; color: var(--tx);
}
.cp-skill-row:hover { background: transparent; }

.cp-skill-uninstall {
  flex-shrink: 0; opacity: 0; margin-right: 4px;
  width: 22px; height: 22px; border: none; border-radius: 4px;
  background: transparent; color: var(--muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.cp-skill-uninstall:hover { background: rgba(239,68,68,.12); color: #ef4444; }
.cp-chevron { font-size: 11px; color: var(--muted); width: 10px; flex-shrink: 0; }
.cp-chevron.sm { font-size: 9px; }
.cp-skill-icon { font-size: 15px; flex-shrink: 0; }
.cp-skill-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Subtree */
.cp-subtree { padding-left: 12px; }

.cp-tree-file, .cp-tree-folder-row {
  display: flex; align-items: center; gap: 6px; width: 100%;
  padding: 5px 8px; border-radius: 6px; border: none;
  background: none; cursor: pointer; text-align: left;
  font-size: 13px; color: var(--muted);
  transition: background .13s, color .13s;
  position: relative;
}
.cp-tree-file:hover, .cp-tree-folder-row:hover { background: var(--hover); color: var(--tx); }
.cp-tree-file.active { background: var(--active-nav); color: var(--tx); font-weight: 500; }
.cp-tree-file.indent { padding-left: 22px; }

.cp-file-icon { font-size: 13px; flex-shrink: 0; }

.cp-folder-items { padding-left: 8px; }

.cp-loading-hint { font-size: 12px; color: var(--muted); padding: 4px 22px; }

.cp-draft-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #f59e0b; flex-shrink: 0; margin-left: auto;
}

.cp-divider { height: 1px; background: var(--bdr); margin: 8px 4px; }

/* ── Content panel ── */
.cp-content { flex: 1; min-width: 0; overflow-y: auto; }

/* Manifest (SKILL.md) view */
.cp-manifest { padding: 36px 48px; display: flex; flex-direction: column; gap: 28px; }

.cp-manifest-header {
  display: flex; align-items: flex-start; gap: 16px;
}
.cp-manifest-icon {
  font-size: 40px; line-height: 1; flex-shrink: 0;
}
.cp-manifest-name { font-size: 22px; font-weight: 700; color: var(--tx); margin-bottom: 6px; }
.cp-manifest-desc { font-size: 14px; color: var(--muted); line-height: 1.6; max-width: 580px; }

.cp-manifest-section { display: flex; flex-direction: column; gap: 10px; }
.cp-manifest-label {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--muted);
}

.cp-pipeline { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.cp-stage-chip {
  padding: 4px 12px; border-radius: 20px;
  background: var(--sbg); color: var(--stx);
  font-size: 13px; font-weight: 500; border: 1px solid var(--sbdr);
}
.cp-arrow { color: var(--muted); font-size: 14px; }

.cp-agent-list { display: flex; gap: 8px; flex-wrap: wrap; }
.cp-agent-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 8px;
  background: var(--surf); border: 1px solid var(--bdr);
  font-size: 13px; color: var(--tx); cursor: pointer;
  transition: border-color .13s, background .13s;
}
.cp-agent-chip:hover { border-color: var(--pri); background: var(--sbg); color: var(--pri); }

/* Folder placeholder */
.cp-folder-placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; gap: 10px; padding: 40px;
  color: var(--muted); text-align: center;
}
.cp-ph-icon { font-size: 40px; }
.cp-ph-name { font-size: 16px; font-weight: 600; color: var(--tx); }
.cp-ph-desc { font-size: 14px; max-width: 380px; line-height: 1.6; }

/* Empty state */
.cp-empty-state {
  display: flex; align-items: center; justify-content: center;
  height: 100%; color: var(--muted); font-size: 14px;
}

/* Uninstall confirm overlay (mirrors ChatWindow del-overlay) */
.del-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center; z-index: 900;
}
.del-dialog {
  background: var(--surf); border: 1px solid var(--bdr); border-radius: 14px;
  padding: 24px 28px; width: 360px; display: flex; flex-direction: column; gap: 10px;
  box-shadow: 0 16px 48px rgba(0,0,0,.25);
}
.del-title { font-size: 16px; font-weight: 700; color: var(--tx); margin: 0; }
.del-body  { font-size: 13px; color: var(--muted); margin: 0; line-height: 1.55; }
.del-btns  { display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }
.del-cancel {
  padding: 8px 16px; border-radius: 8px; border: 1.5px solid var(--bdr);
  background: transparent; color: var(--tx); font-size: 13px; font-weight: 500; cursor: pointer;
}
.del-confirm {
  padding: 8px 16px; border-radius: 8px; border: 1.5px solid #ef4444;
  background: #ef4444; color: #fff; font-size: 13px; font-weight: 600; cursor: pointer;
}
.fade-enter-active, .fade-leave-active { transition: opacity .15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
