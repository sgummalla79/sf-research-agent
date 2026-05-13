<template>
  <div class="ap-root" :class="{ 'no-sidebar': !!selectedKey }">

    <!-- ── Left: agent list (hidden when a key is pre-selected by parent) ── -->
    <aside v-if="!selectedKey" class="ap-list">
      <div class="ap-list-heading">Agents</div>
      <button v-for="agent in agents" :key="agent.agent_key"
        class="ap-agent-row" :class="{ active: selected?.agent_key === agent.agent_key }"
        @click="selectAgent(agent)">
        <span class="ap-agent-label">{{ agent.label }}</span>
        <span class="ap-agent-badge" :class="badgeClass(agent)">{{ badgeText(agent) }}</span>
      </button>
    </aside>

    <!-- ── Editor + History ──────────────────────────────────────────── -->
    <div class="ap-editor-wrap" v-if="selected">

      <!-- ── Main: title + model at top, then textarea ── -->
      <div class="ap-main">

        <!-- Agent name + status -->
        <div class="ap-top">
          <div class="ap-top-left">
            <div class="ap-editor-title">{{ selected.label }}</div>
            <div class="ap-editor-meta" :class="metaClass">{{ metaText }}</div>
          </div>

          <!-- Model picker — top right -->
          <div class="ap-model-top">
            <select class="ap-model-select" v-model="selectedModelKey" @change="onModelChange">
              <option value="__global__">Smart default</option>
              <optgroup v-for="grp in PROVIDER_GROUPS" :key="grp.id" :label="grp.label">
                <option v-for="m in grp.models" :key="`${grp.id}/${m.model}`"
                  :value="`${grp.id}/${m.model}`">
                  {{ m.label }}
                </option>
              </optgroup>
            </select>
            <button class="ap-suggest-btn" @click="suggestModel" title="Auto-suggest best model for this agent role">
              ✦ Suggest
            </button>
          </div>
        </div>

        <!-- Action buttons -->
        <div class="ap-actions">
          <button v-if="dirty && currentPublishedContent"
            class="ap-btn ap-btn-ghost" @click="revertToPublished" :disabled="saving">
            ↩ Revert
          </button>
          <button v-if="hasDraft" class="ap-btn ap-btn-ghost ap-btn-danger"
            @click="discardDraft" :disabled="saving">
            Discard draft
          </button>
          <button class="ap-btn ap-btn-secondary" @click="saveDraft" :disabled="saving || !dirty">
            {{ saving ? 'Saving…' : hasDraft ? 'Update Draft' : 'Save as Draft' }}
          </button>
        </div>

        <div v-if="saveMsg" class="ap-save-msg" :class="saveMsg.type">{{ saveMsg.text }}</div>
        <div v-if="suggestNote" class="ap-suggest-note">{{ suggestNote }}</div>

        <!-- Prompt textarea -->
        <textarea class="ap-textarea" v-model="editorContent" spellcheck="false"
          placeholder="Enter the system prompt for this agent…"
          @input="dirty = true" />
      </div>


    </div>

    <div v-else class="ap-empty">
      <p>Select an agent to view and edit its prompt.</p>
    </div>

  </div>
</template>

<script setup>
import { apiFetch } from '../../composables/useFetch.js'
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  flowId:      { type: String, default: 'architect' },
  selectedKey: { type: String, default: null },
})

const agents   = ref([])
const selected = ref(null)

const editorContent    = ref('')
const dirty            = ref(false)
const saving           = ref(false)
const saveMsg          = ref(null)

// Model picker
const selectedModelKey = ref('__global__')   // '__global__' | 'provider/model'
const suggestNote      = ref('')

// Curated model list shown for every agent, grouped by provider.
// Each provider shows only its most relevant models — not the full API catalogue.
const PROVIDER_GROUPS = [
  {
    id: 'anthropic', label: 'Anthropic',
    models: [
      { model: 'claude-opus-4-7',           label: 'Claude Opus 4.7' },
      { model: 'claude-sonnet-4-6',         label: 'Claude Sonnet 4.6' },
      { model: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
    ],
  },
  {
    id: 'google', label: 'Google',
    models: [
      { model: 'gemini-2.5-pro',   label: 'Gemini 2.5 Pro' },
      { model: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
    ],
  },
  {
    id: 'perplexity', label: 'Perplexity',
    models: [
      { model: 'sonar-pro', label: 'Sonar Pro' },
      { model: 'sonar',     label: 'Sonar' },
    ],
  },
]

// Slot → best-model key for the Suggest button (mirrors SMART_SLOT_DEFAULTS)
const SLOT_SUGGESTIONS = {
  researcher_search:    'perplexity/sonar-pro',
  researcher_reasoning: 'google/gemini-2.5-pro',
  approver:             'anthropic/claude-opus-4-7',
}

// Compact label shown next to the agent name in the header
const activeModelLabel = computed(() => {
  if (!selectedModelKey.value || selectedModelKey.value === '__global__') return ''
  const parts = selectedModelKey.value.split('/')
  return parts[parts.length - 1]
})

function modelConfigFromKey(key) {
  if (!key || key === '__global__') return null
  const [provider, ...rest] = key.split('/')
  return { provider, model: rest.join('/') }
}
function keyFromModelConfig(cfg) {
  if (!cfg) return '__global__'
  return `${cfg.provider}/${cfg.model}`
}
function onModelChange() { dirty.value = true; suggestNote.value = '' }

function suggestModel() {
  const slot      = selected.value?.llm_slot
  const suggested = slot ? (SLOT_SUGGESTIONS[slot] ?? 'anthropic/claude-sonnet-4-6') : 'anthropic/claude-sonnet-4-6'
  const model     = suggested.split('/').pop()
  selectedModelKey.value = suggested
  dirty.value            = true
  suggestNote.value      = `✓ ${model} suggested for this agent's role.`
}

// ── Computed helpers ──────────────────────────────────────────────────────────

const hasDraft = computed(() => !!selected.value?.draft)

const currentPublishedContent = computed(() =>
  selected.value?.latest_published?.content ?? null
)

const metaText = computed(() => {
  if (!selected.value) return ''
  const d = selected.value.draft
  const p = selected.value.latest_published
  if (d) return `Draft v${d.version} — unpublished changes`
  if (p) return `Published v${p.version}`
  return 'No versions yet'
})

const metaClass = computed(() => {
  if (selected.value?.draft)             return 'meta-draft'
  if (selected.value?.latest_published)  return 'meta-published'
  return ''
})

function badgeText(agent) {
  if (agent.draft)             return `Draft v${agent.draft.version}`
  if (agent.latest_published)  return `v${agent.latest_published.version}`
  return '—'
}

function badgeClass(agent) {
  if (agent.draft)            return 'badge-draft'
  if (agent.latest_published) return 'badge-published'
  return 'badge-none'
}

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadAgents() {
  try {
    const res  = await apiFetch(`/api/prompts/${props.flowId}`)
    const data = await res.json()
    agents.value = data.agents || []
    // Re-sync selected agent data if one is active
    if (selected.value) {
      const fresh = agents.value.find(a => a.agent_key === selected.value.agent_key)
      if (fresh) syncSelected(fresh)
    }
  } catch (_) {}
}


function syncSelected(agent) {
  selected.value      = agent
  const source        = agent.draft ?? agent.latest_published
  editorContent.value = source?.content ?? ''
  const mc = (agent.draft ?? agent.latest_published)?.model_config ?? null
  selectedModelKey.value = keyFromModelConfig(mc)
  dirty.value   = false
  saveMsg.value = null
}

function selectAgent(agent) {
  syncSelected(agent)
}

// ── Actions ───────────────────────────────────────────────────────────────────


async function saveDraft() {
  if (!selected.value) return
  saving.value = true
  saveMsg.value = null
  try {
    const res = await apiFetch(`/api/prompts/${props.flowId}/${selected.value.agent_key}/draft`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        content:      editorContent.value,
        agent_model: modelConfigFromKey(selectedModelKey.value),
      }),
    })
    if (res.ok) {
      dirty.value   = false
      saveMsg.value = { type: 'ok', text: 'Draft saved.' }
      await loadAgents()
    } else {
      saveMsg.value = { type: 'err', text: 'Save failed.' }
    }
  } catch (_) {
    saveMsg.value = { type: 'err', text: 'Network error.' }
  } finally {
    saving.value = false
  }
}

async function discardDraft() {
  if (!selected.value?.draft) return
  if (!confirm('Discard this draft? The unpublished changes will be lost.')) return
  saving.value = true
  try {
    await apiFetch(`/api/prompts/${props.flowId}/${selected.value.agent_key}/draft`, { method: 'DELETE' })
    await loadAgents()
  } finally {
    saving.value = false
  }
}

function revertToPublished() {
  if (!currentPublishedContent.value) return
  editorContent.value = currentPublishedContent.value
  dirty.value         = false
  saveMsg.value       = { type: 'ok', text: 'Reverted to published version.' }
}

onMounted(async () => {
  await loadAgents()
  if (props.selectedKey) {
    const agent = agents.value.find(a => a.agent_key === props.selectedKey)
    if (agent) selectAgent(agent)
  }
})
</script>

<style scoped>
.ap-root {
  display: flex; height: 100%; gap: 0;
  font-family: inherit; color: var(--tx);
}
/* When the file tree (parent) handles agent navigation, hide the internal list */


/* ── Agent list ── */
.ap-list {
  width: 210px; flex-shrink: 0;
  border-right: 1px solid var(--bdr);
  display: flex; flex-direction: column;
  padding: 8px 8px;
  overflow-y: auto;
}
.ap-list-heading {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--muted);
  padding: 6px 8px 10px;
}
.ap-agent-row {
  display: flex; flex-direction: row; align-items: center; gap: 6px;
  padding: 8px 10px; border-radius: 8px;
  background: none; border: none; cursor: pointer; text-align: left; width: 100%;
  transition: background .13s;
}
.ap-agent-row:hover  { background: var(--hover); }
.ap-agent-row.active { background: var(--active-nav); }
.ap-agent-label {
  font-size: 13px; font-weight: 500; color: var(--tx);
  flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ap-agent-badge {
  font-size: 10.5px; font-weight: 600; flex-shrink: 0;
  padding: 1px 6px; border-radius: 10px;
}
.badge-published { background: var(--sbg); color: var(--stx); }
.badge-draft     { background: #fef3c7;    color: #92400e; }
.badge-none      { color: var(--muted); }
.dark .badge-draft { background: #1c1400; color: #fcd34d; }

/* ── Editor + History two-column wrap ── */
.ap-editor-wrap {
  flex: 1; min-width: 0; display: flex; flex-direction: row; overflow: hidden;
}


/* ── Main content (left) ── */
.ap-main {
  flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px;
  padding: 24px 28px; overflow-y: auto;
}

/* Top bar: agent name (left) + model picker (right) */
.ap-top {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px; flex-wrap: wrap;
}
.ap-top-left { display: flex; flex-direction: column; gap: 3px; }
.ap-editor-title { font-size: 18px; font-weight: 700; color: var(--tx); }
.ap-editor-meta  { font-size: 13px; }
.meta-draft      { color: #d97706; }
.meta-published  { color: var(--stx); }

/* Model picker inline at top-right */
.ap-model-top { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

/* Action buttons row */
.ap-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.ap-btn {
  padding: 7px 16px; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: 1.5px solid transparent; transition: background .13s, opacity .13s;
  white-space: nowrap;
}
.ap-btn:disabled { opacity: .45; cursor: not-allowed; }
.ap-btn-primary  { background: var(--pri); color: #fff; border-color: var(--pri); }
.ap-btn-primary:hover:not(:disabled) { background: var(--pri-h); }
.ap-btn-secondary { background: var(--surf); color: var(--tx); border-color: var(--bdr); }
.ap-btn-secondary:hover:not(:disabled) { background: var(--hover); }
.ap-btn-ghost { background: none; color: var(--muted); border-color: transparent; }
.ap-btn-ghost:hover:not(:disabled) { color: var(--tx); background: var(--hover); }
.ap-btn-ghost.ap-btn-danger { color: var(--muted); }
.ap-btn-ghost.ap-btn-danger:hover:not(:disabled) { color: #dc2626; background: #fef2f2; }
.dark .ap-btn-ghost.ap-btn-danger:hover:not(:disabled) { color: #fca5a5; background: #1f0000; }

.ap-save-msg { font-size: 13px; padding: 8px 12px; border-radius: 8px; }
.ap-save-msg.ok  { background: var(--pass-bg); color: var(--pass-tx); }
.ap-save-msg.err { background: var(--fail-bg); color: var(--fail-tx); }

.ap-textarea {
  flex: 1; min-height: 360px;
  background: var(--surf2); color: var(--tx);
  border: 1px solid var(--bdr); border-radius: 10px;
  padding: 14px 16px; font-size: 13px; font-family: 'Courier New', monospace;
  line-height: 1.65; resize: vertical; outline: none;
  transition: border-color .15s;
}
.ap-textarea:focus { border-color: var(--ifocus); }

/* ── Shared model select + suggest ── */
.ap-model-select {
  padding: 6px 10px; border-radius: 8px;
  border: 1px solid var(--bdr); background: var(--surf2); color: var(--tx);
  font-size: 13px; font-family: inherit; cursor: pointer; outline: none;
  transition: border-color .15s;
}
.ap-model-select:focus { border-color: var(--ifocus); }
.ap-suggest-btn {
  padding: 6px 12px; border-radius: 8px; white-space: nowrap;
  border: 1.5px solid var(--bdr); background: var(--surf); color: var(--tx);
  font-size: 13px; font-weight: 500; cursor: pointer;
  transition: background .13s, border-color .13s;
}
.ap-suggest-btn:hover { background: var(--sbg); border-color: var(--pri); color: var(--pri); }
.ap-suggest-note { font-size: 12px; color: var(--muted); }

/* ── Version history panel (right column) ── */
.ap-history-panel {
  width: 220px; flex-shrink: 0;
  border-left: 1px solid var(--bdr);
  background: var(--sidebar);
  display: flex; flex-direction: column;
  padding: 20px 14px; gap: 8px; overflow-y: auto;
}
.ap-history-heading {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--muted); margin-bottom: 4px;
}
.ap-history-empty { font-size: 12px; color: var(--muted); padding: 4px 0; }
.ap-hv-row {
  display: flex; flex-direction: column; gap: 3px;
  padding: 8px 10px; border-radius: 8px; font-size: 12px;
  background: var(--surf2); border: 1px solid transparent;
  transition: border-color .13s;
}
.ap-hv-row.current { border-color: var(--pri); }
.ap-hv-top    { display: flex; align-items: center; gap: 6px; }
.ap-hv-num    { font-weight: 700; color: var(--tx); font-size: 13px; }
.ap-hv-date   { font-size: 11px; color: var(--muted); }
.ap-hv-model  { font-size: 11px; color: var(--muted); font-family: monospace; }
.ap-hv-badge  { font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 6px; }
.ap-hv-badge.published { background: var(--sbg); color: var(--stx); }
.ap-hv-badge.draft     { background: #fef3c7; color: #92400e; }
.dark .ap-hv-badge.draft { background: #1c1400; color: #fcd34d; }
.ap-hv-current { font-size: 10px; color: var(--pri); font-weight: 600; }
.ap-hv-restore {
  background: none; border: 1px solid var(--bdr); border-radius: 5px;
  padding: 2px 7px; font-size: 11px; cursor: pointer; color: var(--muted);
  margin-top: 2px; align-self: flex-start;
}
.ap-hv-restore:hover { color: var(--tx); border-color: var(--tx); }

/* ── Empty state ── */
.ap-empty {
  flex: 1; display: flex; align-items: center; justify-content: center;
  color: var(--muted); font-size: 14px;
}
</style>
