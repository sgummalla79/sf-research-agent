<template>
  <div class="cp-root">

    <!-- ══════════ LEFT — file tree ══════════ -->
    <aside class="cp-sidebar">

      <div class="cp-back" @click="$emit('back')">
        <span class="cp-back-arrow">←</span>
        <span>Back to Chat</span>
      </div>

      <div class="cp-tree">

        <!-- ── Skills ── -->
        <div v-for="skill in skills" :key="skill.id" class="cp-skill-block">

          <!-- Skill row -->
          <button class="cp-skill-row" @click="toggleSkill(skill.id)">
            <span class="cp-chevron">{{ expanded[skill.id] ? '▾' : '▸' }}</span>
            <span class="cp-skill-icon">{{ skill.icon }}</span>
            <span class="cp-skill-name">{{ skill.name }}</span>
          </button>

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

        <div class="cp-divider" />

        <!-- Agent Models (separate from skills) -->
        <button class="cp-tree-file"
          :class="{ active: sel?.type === 'models' }"
          @click="select({ type: 'models' })">
          <span class="cp-file-icon">⚙</span> Agent Models
        </button>

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

      <!-- Agent models -->
      <AgentConfigSettings v-else-if="sel?.type === 'models'" />

      <!-- Nothing selected -->
      <div v-else class="cp-empty-state">
        <p>Select a file from the tree to get started.</p>
      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import AgentConfigSettings  from './settings/AgentConfigSettings.vue'
import AgentPromptsSettings from './settings/AgentPromptsSettings.vue'

defineEmits(['back'])

// ── State ─────────────────────────────────────────────────────────────────────

const skills     = ref([])            // from /api/flows
const skillAgents = reactive({})      // skillId → agents[]
const expanded   = reactive({})       // skillId → bool
const openFolders = reactive({})      // `${skillId}/${folder}` → bool
const sel        = ref(null)          // current selection

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

.cp-tree { display: flex; flex-direction: column; padding: 4px 6px 16px; flex: 1; }

/* Skill block */
.cp-skill-block { margin-bottom: 2px; }

.cp-skill-row {
  display: flex; align-items: center; gap: 7px; width: 100%;
  padding: 7px 8px; border-radius: 7px; border: none;
  background: none; cursor: pointer; text-align: left;
  font-size: 13px; font-weight: 600; color: var(--tx);
  transition: background .13s;
}
.cp-skill-row:hover { background: var(--hover); }
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
</style>
