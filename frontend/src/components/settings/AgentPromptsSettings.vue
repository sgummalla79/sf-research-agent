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

    <!-- ── Right: editor ─────────────────────────────────────────────── -->
    <div class="ap-editor" v-if="selected">

      <!-- Header -->
      <div class="ap-editor-header">
        <div>
          <div class="ap-title-row">
            <span class="ap-editor-title">{{ selected.label }}</span>
            <span v-if="activeModelLabel" class="ap-model-badge">{{ activeModelLabel }}</span>
          </div>
          <div class="ap-editor-meta" :class="metaClass">{{ metaText }}</div>
        </div>
        <div class="ap-editor-actions">
          <!-- Revert: reset editor to current published content, no API call -->
          <button v-if="dirty && currentPublishedContent"
            class="ap-btn ap-btn-ghost" @click="revertToPublished" :disabled="saving"
            title="Discard unsaved edits and restore the current published prompt">
            ↩ Revert to published
          </button>

          <template v-if="hasDraft">
            <button class="ap-btn ap-btn-secondary" @click="saveDraft" :disabled="saving || !dirty">
              {{ saving ? 'Saving…' : 'Update Draft' }}
            </button>
            <button class="ap-btn ap-btn-ghost ap-btn-danger" @click="discardDraft" :disabled="saving">
              Discard draft
            </button>
            <button class="ap-btn ap-btn-primary" @click="publishDraft" :disabled="saving">
              {{ saving ? 'Publishing…' : `Publish v${draftVersion}` }}
            </button>
          </template>

          <button v-else class="ap-btn ap-btn-secondary" @click="saveDraft" :disabled="saving || !dirty">
            {{ saving ? 'Saving…' : 'Save as Draft' }}
          </button>
        </div>
      </div>

      <div v-if="saveMsg" class="ap-save-msg" :class="saveMsg.type">{{ saveMsg.text }}</div>

      <!-- Textarea -->
      <textarea class="ap-textarea" v-model="editorContent" spellcheck="false"
        placeholder="Enter the system prompt for this agent…"
        @input="dirty = true" />

      <div class="ap-separator" />

      <!-- Model picker -->
      <div class="ap-model-section">
        <div class="ap-model-label">
          Model
          <span class="ap-model-hint">Overrides the global default for this agent only</span>
        </div>
        <div class="ap-model-row">
          <select class="ap-model-select" v-model="selectedModelKey" @change="onModelChange">
            <option value="__global__">Global default{{ globalDefaultLabel ? ` — ${globalDefaultLabel}` : '' }}</option>
            <optgroup v-for="prov in providerModels" :key="prov.id" :label="prov.name">
              <option v-for="m in prov.models" :key="m" :value="`${prov.id}/${m}`">
                {{ m }}
              </option>
            </optgroup>
          </select>
          <button class="ap-suggest-btn" @click="suggestModel" title="Auto-suggest best model for this agent role">
            ✦ Suggest
          </button>
        </div>
        <div v-if="suggestNote" class="ap-suggest-note">{{ suggestNote }}</div>
      </div>

      <!-- Version history -->
      <div class="ap-history">
        <button class="ap-history-toggle" @click="historyOpen = !historyOpen">
          {{ historyOpen ? '▾' : '▸' }} Version History
        </button>
        <div v-if="historyOpen" class="ap-history-list">
          <div v-if="!history.length" class="ap-history-empty">No published versions yet.</div>
          <div v-for="v in history" :key="v.id" class="ap-history-row"
            :class="{ current: v.version === currentPublishedVersion }">
            <span class="ap-hv-num">v{{ v.version }}</span>
            <span class="ap-hv-date">{{ fmtDate(v.published_at || v.created_at) }}</span>
            <span v-if="v.model_config" class="ap-hv-model">{{ v.model_config.model }}</span>
            <span class="ap-hv-badge" :class="v.status">{{ v.status }}</span>
            <button v-if="v.status === 'published' && v.version !== currentPublishedVersion"
              class="ap-hv-restore" @click="restoreVersion(v)">Restore</button>
            <span v-if="v.version === currentPublishedVersion && v.status === 'published'"
              class="ap-hv-current">● current</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="ap-empty">
      <p>Select an agent to view and edit its prompt.</p>
    </div>

  </div>
</template>

<script setup>
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
const history          = ref([])
const historyOpen      = ref(false)

// Model picker
const selectedModelKey  = ref('__global__')  // '__global__' | 'provider/model'
const providerModels    = ref([])             // [{id, name, models:[]}]
const globalDefaultLabel = ref('')           // e.g. "Sonnet 4.6"

// Best-model suggestions per llm_slot — mirrors SMART_SLOT_DEFAULTS in the backend
const SLOT_SUGGESTIONS = {
  researcher_search:    'perplexity/sonar-pro',
  researcher_reasoning: 'google/gemini-2.5-pro',
  approver:             'anthropic/claude-opus-4-7',
  intake:               'anthropic/claude-sonnet-4-6',
  discovery:            'anthropic/claude-sonnet-4-6',
  reviewer:             'anthropic/claude-sonnet-4-6',
  researcher_writer:    'anthropic/claude-sonnet-4-6',
}

const suggestNote = ref('')

// Compact label shown next to the agent name in the header
const activeModelLabel = computed(() => {
  if (!selectedModelKey.value || selectedModelKey.value === '__global__') {
    return globalDefaultLabel.value ? globalDefaultLabel.value : ''
  }
  const parts = selectedModelKey.value.split('/')
  return parts[parts.length - 1]   // just the model name, no provider prefix
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
  const slot       = selected.value?.llm_slot
  const suggested  = slot ? (SLOT_SUGGESTIONS[slot] ?? 'anthropic/claude-sonnet-4-6') : 'anthropic/claude-sonnet-4-6'
  const [provider, model] = suggested.split('/')
  const available  = providerModels.value.some(p => p.id === provider && p.models.includes(model))

  if (available) {
    selectedModelKey.value = suggested
    dirty.value            = true
    suggestNote.value      = `✓ Suggested ${model} for this agent's role.`
  } else {
    // Fall back to any available model from that provider, or just set the key anyway
    selectedModelKey.value = suggested
    dirty.value            = true
    suggestNote.value      = `${model} suggested — connect ${provider} in Settings to use it.`
  }
}

// ── Computed helpers ──────────────────────────────────────────────────────────

const hasDraft = computed(() => !!selected.value?.draft)

const draftVersion = computed(() => selected.value?.draft?.version ?? null)

const currentPublishedVersion = computed(() =>
  selected.value?.latest_published?.version ?? null
)

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
    const res  = await fetch(`/api/prompts/${props.flowId}`)
    const data = await res.json()
    agents.value = data.agents || []
    // Re-sync selected agent data if one is active
    if (selected.value) {
      const fresh = agents.value.find(a => a.agent_key === selected.value.agent_key)
      if (fresh) syncSelected(fresh)
    }
  } catch (_) {}
}

async function loadHistory() {
  if (!selected.value) return
  try {
    const res  = await fetch(`/api/prompts/${props.flowId}/${selected.value.agent_key}/history`)
    const data = await res.json()
    history.value = data.history || []
  } catch (_) {}
}

function syncSelected(agent) {
  selected.value      = agent
  const source        = agent.draft ?? agent.latest_published
  editorContent.value = source?.content ?? ''
  // Sync model picker: draft model_config takes priority over published
  const mc = (agent.draft ?? agent.latest_published)?.model_config ?? null
  selectedModelKey.value = keyFromModelConfig(mc)
  dirty.value   = false
  saveMsg.value = null
  // Update global default label for this agent's slot
  updateGlobalDefaultLabel(agent.llm_slot)
}

function selectAgent(agent) {
  syncSelected(agent)
  historyOpen.value = false
  history.value     = []
  loadHistory()
}

// ── Actions ───────────────────────────────────────────────────────────────────

async function loadProviderModels() {
  try {
    const res  = await fetch('/api/providers')
    const data = await res.json()
    providerModels.value = (data.providers || [])
      .filter(p => p.connected && p.models?.length)
      .map(p => ({ id: p.id, name: p.name || p.id, models: p.models }))
  } catch (_) {}
}

async function updateGlobalDefaultLabel(slot) {
  if (!slot) return
  try {
    const res  = await fetch('/api/settings/agent-config')
    const data = await res.json()
    const cfg  = data.config?.[slot]
    globalDefaultLabel.value = cfg?.model ? cfg.model.replace('claude-', '').replace(/-\d{8}.*$/, '') : ''
  } catch (_) {}
}

async function saveDraft() {
  if (!selected.value) return
  saving.value = true
  saveMsg.value = null
  try {
    const res = await fetch(`/api/prompts/${props.flowId}/${selected.value.agent_key}/draft`, {
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
      await loadHistory()
    } else {
      saveMsg.value = { type: 'err', text: 'Save failed.' }
    }
  } catch (_) {
    saveMsg.value = { type: 'err', text: 'Network error.' }
  } finally {
    saving.value = false
  }
}

async function publishDraft() {
  if (!selected.value) return
  saving.value  = true
  saveMsg.value = null
  try {
    const res = await fetch(`/api/prompts/${props.flowId}/${selected.value.agent_key}/publish`, {
      method: 'POST',
    })
    const data = await res.json()
    if (res.ok) {
      saveMsg.value = { type: 'ok',
        text: `Published v${data.version}. New flow snapshot v${data.snapshot_version} created.` }
      dirty.value = false
      await loadAgents()
      await loadHistory()
    } else {
      saveMsg.value = { type: 'err', text: data.detail || 'Publish failed.' }
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
    await fetch(`/api/prompts/${props.flowId}/${selected.value.agent_key}/draft`, { method: 'DELETE' })
    await loadAgents()
    await loadHistory()
  } finally {
    saving.value = false
  }
}

function revertToPublished() {
  if (!currentPublishedContent.value) return
  editorContent.value = currentPublishedContent.value
  dirty.value         = false
  saveMsg.value       = { type: 'ok', text: `Reverted to published v${currentPublishedVersion.value}.` }
}

async function restoreVersion(v) {
  editorContent.value = v.content
  dirty.value         = true
  saveMsg.value       = { type: 'ok', text: `Loaded v${v.version} into editor — save as draft to keep.` }
}

// ── Utils ─────────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

onMounted(async () => {
  await Promise.all([loadAgents(), loadProviderModels()])
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
.ap-root.no-sidebar .ap-editor { padding: 28px 48px; }

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

/* ── Editor ── */
.ap-editor {
  flex: 1; min-width: 0; display: flex; flex-direction: column;
  padding: 28px 36px; gap: 16px; overflow-y: auto;
}
.ap-editor-header {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
  flex-wrap: wrap;
}
.ap-title-row    { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.ap-editor-title { font-size: 18px; font-weight: 700; color: var(--tx); }
.ap-model-badge  {
  font-size: 11.5px; font-weight: 500; color: var(--muted);
  padding: 2px 8px; border-radius: 6px;
  background: var(--surf2); border: 1px solid var(--bdr);
  font-family: monospace; white-space: nowrap;
}
.ap-editor-meta  { font-size: 13px; }
.ap-separator    { height: 1px; background: var(--bdr); margin: 4px 0; }
.meta-draft      { color: #d97706; }
.meta-published  { color: var(--stx); }

.ap-editor-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

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

/* ── Model picker ── */
.ap-model-section { display: flex; flex-direction: column; gap: 8px; }
.ap-model-label {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; font-weight: 600; color: var(--tx);
}
.ap-model-hint { font-size: 12px; font-weight: 400; color: var(--muted); }
.ap-model-row  { display: flex; align-items: center; gap: 10px; }
.ap-suggest-btn {
  padding: 7px 14px; border-radius: 8px; white-space: nowrap;
  border: 1.5px solid var(--bdr); background: var(--surf); color: var(--tx);
  font-size: 13px; font-weight: 500; cursor: pointer;
  transition: background .13s, border-color .13s;
}
.ap-suggest-btn:hover { background: var(--sbg); border-color: var(--pri); color: var(--pri); }
.ap-suggest-note { font-size: 12px; color: var(--muted); margin-top: 4px; }

.ap-model-select {
  padding: 7px 12px; border-radius: 8px;
  border: 1px solid var(--bdr); background: var(--surf2); color: var(--tx);
  font-size: 13px; font-family: inherit; cursor: pointer; outline: none;
  transition: border-color .15s; min-width: 280px;
}
.ap-model-select:focus { border-color: var(--ifocus); }

/* ── Version history ── */
.ap-history { border-top: 1px solid var(--bdr); padding-top: 14px; }
.ap-history-toggle {
  background: none; border: none; cursor: pointer;
  font-size: 13px; font-weight: 600; color: var(--muted);
  padding: 0; transition: color .13s;
}
.ap-history-toggle:hover { color: var(--tx); }
.ap-history-list  { display: flex; flex-direction: column; gap: 4px; margin-top: 10px; }
.ap-history-empty { font-size: 13px; color: var(--muted); padding: 6px 0; }
.ap-history-row   {
  display: flex; align-items: center; gap: 10px;
  padding: 7px 10px; border-radius: 8px; font-size: 13px;
  background: var(--surf2);
}
.ap-history-row.current { border-left: 3px solid var(--pri); padding-left: 7px; }
.ap-hv-num    { font-weight: 700; color: var(--tx); min-width: 28px; }
.ap-hv-date   { color: var(--muted); flex: 1; }
.ap-hv-badge  { font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 8px; }
.ap-hv-badge.published { background: var(--sbg); color: var(--stx); }
.ap-hv-badge.draft     { background: #fef3c7; color: #92400e; }
.dark .ap-hv-badge.draft { background: #1c1400; color: #fcd34d; }
.ap-hv-model   { font-size: 11px; color: var(--muted); font-family: monospace; }
.ap-hv-restore { background: none; border: 1px solid var(--bdr); border-radius: 6px; padding: 2px 8px; font-size: 11px; cursor: pointer; color: var(--muted); }
.ap-hv-restore:hover { color: var(--tx); border-color: var(--tx); }
.ap-hv-current { font-size: 11px; color: var(--pri); font-weight: 600; }

/* ── Empty state ── */
.ap-empty {
  flex: 1; display: flex; align-items: center; justify-content: center;
  color: var(--muted); font-size: 14px;
}
</style>
