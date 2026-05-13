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

        <!-- Header row: icon + name + version badge + publish button -->
        <div class="cp-manifest-header">
          <span class="cp-manifest-icon">{{ activeSkill.icon }}</span>
          <div class="cp-manifest-header-body">
            <div class="cp-manifest-name-row">
              <span class="cp-manifest-name">{{ activeSkill.name }}</span>
              <span v-if="skillVersion[activeSkill.id]" class="cp-version-badge">
                v{{ skillVersion[activeSkill.id] }}
              </span>
              <span v-if="skillHasDraft[activeSkill.id]" class="cp-draft-badge">draft pending</span>
            </div>
            <div class="cp-manifest-desc">{{ activeSkill.description }}</div>
          </div>
          <button class="cp-publish-btn"
            :disabled="!skillHasDraft[activeSkill.id] || publishing"
            @click="publishSkill(activeSkill.id)">
            {{ publishing ? 'Publishing…' : 'Publish Skill' }}
          </button>
        </div>

        <div v-if="publishMsg" class="cp-publish-msg" :class="publishMsg.type">{{ publishMsg.text }}</div>

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
              <span v-if="agent.draft" class="cp-draft-dot" title="Unpublished draft" />
            </div>
          </div>
        </div>

        <!-- Version history -->
        <div class="cp-manifest-section">
          <div class="cp-manifest-label">Version History</div>
          <div v-if="!skillSnapshots[activeSkill.id]?.length" class="cp-vh-empty">No published versions yet.</div>
          <div v-for="snap in (skillSnapshots[activeSkill.id] || [])" :key="snap.id" class="cp-vh-row">
            <span class="cp-vh-ver">v{{ snap.snapshot_version }}</span>
            <span class="cp-vh-date">{{ fmtDate(snap.created_at) }}</span>
            <span v-if="snap.snapshot_version === skillVersion[activeSkill.id]" class="cp-vh-current">● current</span>
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

const skills         = ref([])          // installed skills from /api/flows
const skillAgents    = reactive({})     // skillId → agents[]
const skillHasDraft  = reactive({})     // skillId → bool
const skillVersion   = reactive({})     // skillId → latest snapshot_version
const skillSnapshots = reactive({})     // skillId → snapshots[]
const expanded       = reactive({})     // skillId → bool
const openFolders    = reactive({})     // `${skillId}/${folder}` → bool
const sel            = ref(null)        // current selection
const directoryOpen     = ref(false)
const uninstallConfirm  = reactive({ show: false, skill: null })
const publishing        = ref(false)
const publishMsg        = ref(null)

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
      await Promise.all([loadAgents(first.id), loadSnapshots(first.id)])
      openFolders[`${first.id}/agents`] = true
      sel.value = { type: 'manifest', skillId: first.id }
    }
  } catch (_) {}
}

async function loadAgents(skillId) {
  try {
    const res  = await fetch(`/api/prompts/${skillId}`)
    const data = await res.json()
    skillAgents[skillId]   = data.agents   || []
    skillHasDraft[skillId] = !!data.has_draft
  } catch (_) {
    skillAgents[skillId]   = []
    skillHasDraft[skillId] = false
  }
}

async function loadSnapshots(skillId) {
  try {
    const res  = await fetch(`/api/prompts/${skillId}/snapshots`)
    const data = await res.json()
    const snaps = data.snapshots || []
    skillSnapshots[skillId] = snaps
    skillVersion[skillId]   = snaps[0]?.snapshot_version ?? null
  } catch (_) {}
}

async function publishSkill(skillId) {
  publishing.value = true
  publishMsg.value = null
  try {
    const res  = await fetch(`/api/prompts/${skillId}/publish`, { method: 'POST' })
    const data = await res.json()
    if (res.ok) {
      publishMsg.value = { type: 'ok', text: `Published — skill is now v${data.snapshot_version}.` }
      await loadAgents(skillId)
      await loadSnapshots(skillId)
    } else {
      publishMsg.value = { type: 'err', text: data.detail || 'Publish failed.' }
    }
  } catch (_) {
    publishMsg.value = { type: 'err', text: 'Network error.' }
  } finally {
    publishing.value = false
  }
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}


// ── Tree interactions ─────────────────────────────────────────────────────────

async function toggleSkill(skillId) {
  expanded[skillId] = !expanded[skillId]
  if (expanded[skillId]) {
    await loadAgents(skillId)
    await loadSnapshots(skillId)
  }
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

/* Skill manifest — publish row */
.cp-manifest-header { display: flex; align-items: flex-start; gap: 14px; }
.cp-manifest-header-body { flex: 1; min-width: 0; }
.cp-manifest-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cp-version-badge {
  font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 99px;
  background: var(--sbg); color: var(--stx); flex-shrink: 0;
}
.cp-draft-badge {
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 99px;
  background: #fef3c7; color: #92400e; flex-shrink: 0;
}
.cp-publish-btn {
  flex-shrink: 0; padding: 8px 18px; border-radius: 8px;
  background: var(--pri); color: #fff; border: none; font-size: 13px;
  font-weight: 600; cursor: pointer;
}
.cp-publish-btn:hover:not(:disabled) { background: var(--pri-h); }
.cp-publish-btn:disabled { opacity: .4; cursor: not-allowed; }

.cp-publish-msg {
  font-size: 12.5px; padding: 8px 12px; border-radius: 7px; margin-top: -4px;
}
.cp-publish-msg.ok  { background: #f0fdf4; color: #15803d; }
.cp-publish-msg.err { background: #fef2f2; color: #b91c1c; }

/* Version history in manifest */
.cp-vh-empty { font-size: 13px; color: var(--muted); }
.cp-vh-row {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 0; border-bottom: 1px solid var(--bdr); font-size: 13px;
}
.cp-vh-row:last-child { border-bottom: none; }
.cp-vh-ver  { font-weight: 700; color: var(--tx); min-width: 28px; }
.cp-vh-date { color: var(--muted); flex: 1; }
.cp-vh-current { font-size: 11px; font-weight: 600; color: var(--pri); }

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
