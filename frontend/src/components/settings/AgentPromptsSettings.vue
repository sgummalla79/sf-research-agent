<!--
  AgentPromptsSettings — prompt editor per skill agent.

  Fetches agents via GET /api/skills/{skillKey}/agents.
  Draft: PUT /api/skills/{skillKey}/agents/{agentKey}/draft  {content}
  Discard: DELETE /api/skills/{skillKey}/agents/{agentKey}/draft
  Model: PATCH /api/skills/{skillKey}/agents/{agentKey}/model  {provider, model}
-->
<template>
  <div class="ap-root" :class="{ 'ap-no-sidebar': embedded }">

    <!-- ── Left: agent list — hidden when embedded in ConfigurationPage ──── -->
    <aside v-if="!embedded" class="ap-list">
      <div class="ap-list-heading">Agents</div>

      <div v-if="loadingSkills" class="ap-list-loading">Loading…</div>

      <template v-else>
        <div v-for="sk in allSkills" :key="sk.skillKey">
          <div class="ap-skill-hdr">{{ sk.icon }} {{ sk.name }}</div>
          <button v-for="agent in sk.agents" :key="agent.agent_key"
            class="ap-agent-row"
            :class="{ active: selected?.agent_key === agent.agent_key && activeSkillKey === sk.skillKey }"
            @click="selectAgent(sk.skillKey, agent)">
            <span class="ap-agent-label">{{ agent.label || agent.agent_key }}</span>
            <span class="ap-agent-badge" :class="badgeClass(agent)">{{ badgeText(agent) }}</span>
          </button>
        </div>
      </template>
    </aside>

    <!-- ── Editor ──────────────────────────────────────────────────────────── -->
    <div class="ap-editor-wrap" v-if="selected">
      <div class="ap-main">

        <!-- Agent name + meta + model picker inline -->
        <div class="ap-top">
          <div class="ap-top-left">
            <div class="ap-name-row">
              <span class="ap-editor-title">{{ selected.label || selected.agent_key }}</span>
              <!-- Model picker inline next to name -->
              <select class="ap-model-select" v-model="selectedModelKey" @change="onModelChange"
                :title="filteredProviderGroups.length ? '' : 'Connect a provider in Settings → Providers'">
                <option value="__global__">Smart default</option>
                <template v-if="filteredProviderGroups.length">
                  <optgroup v-for="grp in filteredProviderGroups" :key="grp.id" :label="grp.label">
                    <option v-for="m in grp.models" :key="`${grp.id}::${m.model}`"
                      :value="`${grp.id}::${m.model}`">
                      {{ m.label }}
                    </option>
                  </optgroup>
                </template>
                <option v-else disabled>— connect a provider first —</option>
              </select>
            </div>
            <div class="ap-editor-meta" :class="metaClass">{{ metaText }}</div>
          </div>
        </div>

        <!-- Action bar: [Discard Draft] ···· [Cancel Changes] [Save Draft] [Publish] -->
        <div class="ap-actions">
          <!-- Discard Draft — opens confirmation modal -->
          <button v-if="selected.has_draft"
            class="ap-btn ap-btn-secondary"
            :disabled="saving"
            @click="discardPending = true">
            Discard Draft
          </button>

          <div class="ap-actions-right">
            <!-- Cancel Changes — secondary, visible border -->
            <button v-if="dirty"
              class="ap-btn ap-btn-secondary"
              :disabled="saving"
              @click="cancelChanges">
              Cancel Changes
            </button>
            <!-- Save Draft — primary (most common action) -->
            <button class="ap-btn ap-btn-primary"
              :disabled="saving || !dirty"
              @click="saveDraft">
              {{ saving ? 'Saving…' : 'Save Draft' }}
            </button>
            <!-- Publish — primary, enabled when draft or model changed -->
            <button class="ap-btn ap-btn-primary"
              :disabled="publishing || (!selected.has_draft && !modelChanged)"
              @click="publishAgent">
              {{ publishing ? 'Publishing…' : 'Publish' }}
            </button>
          </div>
        </div>

        <div v-if="saveMsg" class="ap-save-msg" :class="saveMsg.type">{{ saveMsg.text }}</div>

        <textarea class="ap-textarea" v-model="editorContent" spellcheck="false"
          placeholder="Enter the system prompt for this agent…"
          @input="dirty = true" />
      </div>
    </div>

    <div v-else class="ap-empty">
      <p>Select an agent to view and edit its prompt.</p>
    </div>

  </div>

  <ConfirmDialog
    :open="discardPending"
    title="Discard draft?"
    body="The unpublished changes will be permanently lost."
    confirm-label="Discard"
    @confirm="doDiscardDraft"
    @cancel="discardPending = false"
  />
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { apiFetch }     from '../../composables/useFetch.js'
import ConfirmDialog    from '../ui/ConfirmDialog.vue'

const props = defineProps({
  embedded:  { type: Boolean, default: false },
  skillKey:  { type: String,  default: null },
  agentKey:  { type: String,  default: null },
})

const emit = defineEmits(['draft-saved'])

// ── Curated model list ────────────────────────────────────────────────────────
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
    id: 'openai', label: 'OpenAI',
    models: [
      { model: 'gpt-4o',      label: 'GPT-4o' },
      { model: 'gpt-4o-mini', label: 'GPT-4o Mini' },
      { model: 'o3',          label: 'o3' },
      { model: 'o4-mini',     label: 'o4 mini' },
    ],
  },
  {
    id: 'google', label: 'Google',
    models: [
      { model: 'gemini-2.5-pro',       label: 'Gemini 2.5 Pro' },
      { model: 'gemini-2.0-flash-001', label: 'Gemini 2.0 Flash' },
    ],
  },
  {
    id: 'perplexity', label: 'Perplexity',
    models: [
      { model: 'sonar-pro', label: 'Sonar Pro' },
      { model: 'sonar',     label: 'Sonar' },
    ],
  },
  {
    id: 'groq', label: 'Groq',
    models: [
      { model: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B' },
    ],
  },
  {
    id: 'mistral', label: 'Mistral',
    models: [
      { model: 'mistral-large-latest',  label: 'Mistral Large' },
      { model: 'mistral-medium-latest', label: 'Mistral Medium' },
    ],
  },
]

// ── State ─────────────────────────────────────────────────────────────────────
const allSkills      = ref([])
const loadingSkills  = ref(true)
const connectedIds   = ref(new Set())   // provider ids that are connected

const activeSkillKey      = ref(null)
const selected            = ref(null)
const editorContent       = ref('')
const dirty               = ref(false)
const saving              = ref(false)
const publishing          = ref(false)
const saveMsg             = ref(null)
const selectedModelKey    = ref('__global__')
const savedModelKey       = ref('__global__')   // what's currently in DB
const discardPending      = ref(false)

const modelChanged = computed(() => selectedModelKey.value !== savedModelKey.value)

// Only show model groups for connected providers
const filteredProviderGroups = computed(() =>
  PROVIDER_GROUPS.filter(g => connectedIds.value.has(g.id))
)

// ── Computed helpers ──────────────────────────────────────────────────────────
const hasDraft = computed(() => !!selected.value?.has_draft)

const metaText = computed(() => {
  if (!selected.value) return ''
  const d = selected.value.draft
  const p = selected.value.published
  if (d) return `Draft v${d.version} — unpublished changes`
  if (p) return `Published v${p.version}`
  return 'No versions yet'
})

const metaClass = computed(() => {
  if (selected.value?.has_draft)   return 'meta-draft'
  if (selected.value?.published)   return 'meta-published'
  return ''
})

function badgeText(agent) {
  if (agent.has_draft)  return `Draft v${agent.draft?.version}`
  if (agent.published)  return `v${agent.published.version}`
  return '—'
}

function badgeClass(agent) {
  if (agent.has_draft)  return 'badge-draft'
  if (agent.published)  return 'badge-published'
  return 'badge-none'
}

function keyFromModelConfig(provider, model) {
  if (!provider || !model) return '__global__'
  return `${provider}::${model}`
}

function onModelChange() { dirty.value = true }

// ── Data loading ──────────────────────────────────────────────────────────────
async function loadAll() {
  loadingSkills.value = true
  try {
    // Fetch connected providers first so the model picker is filtered
    const pvdRes = await apiFetch('/api/providers')
    if (pvdRes.ok) {
      const pvd = await pvdRes.json()
      connectedIds.value = new Set((pvd.providers || []).filter(p => p.connected).map(p => p.id))
    }

    const skillsRes = await apiFetch('/api/skills')
    if (!skillsRes.ok) return
    const skillsData = await skillsRes.json()

    const result = []
    for (const sk of (skillsData.skills || [])) {
      if (!sk.installed) continue
      const agentsRes = await apiFetch(`/api/skills/${sk.skill_key}/agents`)
      if (!agentsRes.ok) continue
      const agentsData = await agentsRes.json()
      result.push({
        skillKey: sk.skill_key,
        name:     sk.name,
        icon:     sk.icon || '⚡',
        agents:   agentsData.agents || [],
      })
    }
    allSkills.value = result

    // When embedded, auto-select the agent passed via props
    if (props.embedded && props.skillKey && props.agentKey) {
      const sk = result.find(s => s.skillKey === props.skillKey)
      if (sk) {
        const agent = sk.agents.find(a => a.agent_key === props.agentKey)
        if (agent) selectAgent(props.skillKey, agent)
      }
    }
  } finally {
    loadingSkills.value = false
  }
}

// Re-select when the target agent changes (user clicks a different agent in the tree)
watch(() => [props.skillKey, props.agentKey], ([sk, ak]) => {
  if (!props.embedded || !sk || !ak) return
  const skill = allSkills.value.find(s => s.skillKey === sk)
  if (!skill) return
  const agent = skill.agents.find(a => a.agent_key === ak)
  if (agent) selectAgent(sk, agent)
})

async function refreshCurrentSkill() {
  if (!activeSkillKey.value) return
  const sk = allSkills.value.find(s => s.skillKey === activeSkillKey.value)
  if (!sk) return
  const res  = await apiFetch(`/api/skills/${activeSkillKey.value}/agents`)
  if (!res.ok) return
  const data = await res.json()
  sk.agents  = data.agents || []

  // Re-sync selected agent
  if (selected.value) {
    const fresh = sk.agents.find(a => a.agent_key === selected.value.agent_key)
    if (fresh) syncSelected(activeSkillKey.value, fresh)
  }
}

function syncSelected(skillKey, agent) {
  activeSkillKey.value = skillKey
  selected.value       = agent
  const source         = agent.draft ?? agent.published
  editorContent.value  = source?.content ?? ''
  // Model comes from the version record currently being displayed
  const mk = keyFromModelConfig(source?.provider_to_use, source?.model_to_use)
  selectedModelKey.value = mk
  savedModelKey.value    = mk
  dirty.value            = false
  saveMsg.value          = null
}

function selectAgent(skillKey, agent) {
  syncSelected(skillKey, agent)
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function saveDraft() {
  if (!selected.value) return
  saving.value  = true
  saveMsg.value = null

  try {
    const sk = activeSkillKey.value
    const ak = selected.value.agent_key

    // Save prompt draft (model stored alongside content)
    const val    = selectedModelKey.value
    const body   = { content: editorContent.value }
    if (val === '__global__') { body.provider = null; body.model = null }
    else { [body.provider, body.model] = val.split('::') }

    const draftRes = await apiFetch(`/api/skills/${sk}/agents/${ak}/draft`, {
      method: 'PUT',
      body:   JSON.stringify(body),
    })
    if (!draftRes.ok) {
      saveMsg.value = { type: 'err', text: 'Draft save failed.' }
      return
    }

    savedModelKey.value = selectedModelKey.value
    dirty.value         = false
    saveMsg.value       = { type: 'ok', text: 'Draft saved.' }
    emit('draft-saved')
    await refreshCurrentSkill()
  } catch (_) {
    saveMsg.value = { type: 'err', text: 'Network error.' }
  } finally {
    saving.value = false
  }
}

async function doDiscardDraft() {
  discardPending.value = false
  if (!selected.value?.has_draft) return
  saving.value = true
  try {
    await apiFetch(
      `/api/skills/${activeSkillKey.value}/agents/${selected.value.agent_key}/draft`,
      { method: 'DELETE' }
    )
    emit('draft-saved')
    await refreshCurrentSkill()
  } finally {
    saving.value = false
  }
}

async function publishAgent() {
  if (!selected.value) return
  publishing.value = true
  saveMsg.value    = null
  const sk = activeSkillKey.value
  const ak = selected.value.agent_key
  try {
    // If there's a pending model change but no draft yet, save a draft first so the
    // model is captured in user_agents_versions before publishing.
    if (modelChanged.value && !selected.value.draft) {
      const val  = selectedModelKey.value
      const body = { content: editorContent.value }
      if (val === '__global__') { body.provider = null; body.model = null }
      else { [body.provider, body.model] = val.split('::') }
      await apiFetch(`/api/skills/${sk}/agents/${ak}/draft`, {
        method: 'PUT', body: JSON.stringify(body),
      })
      savedModelKey.value = selectedModelKey.value
    }

    // Publish — backend copies provider/model from the draft into user_agents
    if (selected.value.draft || modelChanged.value) {
      const res  = await apiFetch(`/api/skills/${sk}/agents/${ak}/publish`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) { saveMsg.value = { type: 'err', text: data.detail || 'Publish failed.' }; return }
    }

    saveMsg.value = { type: 'ok', text: 'Published successfully.' }
    emit('draft-saved')
    await refreshCurrentSkill()
  } catch (_) {
    saveMsg.value = { type: 'err', text: 'Network error.' }
  } finally {
    publishing.value = false
  }
}

function cancelChanges() {
  // Revert to last *saved* state: draft content if a draft exists, otherwise published
  const source = selected.value?.draft ?? selected.value?.published
  if (!source?.content) return
  editorContent.value = source.content
  dirty.value         = false
  saveMsg.value       = null
}

onMounted(loadAll)
</script>

<style scoped>
.ap-root {
  display: flex; height: 100%; overflow: hidden;
  color: var(--text); font-family: inherit;
}
/* When embedded in ConfigurationPage — no inner nav, editor fills full width */
.ap-no-sidebar .ap-editor-wrap { flex: 1; }

/* ── Agent list ── */
.ap-list {
  width: 200px; flex-shrink: 0;
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  padding: 8px; overflow-y: auto;
}
.ap-list-heading {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--muted); padding: 6px 8px 10px;
}
.ap-list-loading { font-size: 13px; color: var(--muted); padding: 8px 8px; }

.ap-skill-hdr {
  font-size: 11px; font-weight: 700; color: var(--muted);
  padding: 6px 8px 2px; text-transform: uppercase; letter-spacing: .04em;
}

.ap-agent-row {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 10px; border-radius: 8px;
  background: none; border: none; cursor: pointer;
  text-align: left; width: 100%; transition: background .13s;
}
.ap-agent-row:hover  { background: var(--surface-2); }
.ap-agent-row.active { background: var(--surface-2); border-left: 2px solid var(--pri); }
.ap-agent-label {
  font-size: 13px; font-weight: 500; color: var(--text);
  flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ap-agent-badge {
  font-size: 10.5px; font-weight: 600;
  padding: 1px 6px; border-radius: 10px; flex-shrink: 0;
}
.badge-published { background: var(--surface-2); color: var(--pri); }
.badge-draft     { background: #fef3c7; color: #92400e; }
.badge-none      { color: var(--muted); }

/* ── Editor ── */
.ap-editor-wrap {
  flex: 1; min-width: 0; overflow: hidden;
}
.ap-main {
  flex: 1; display: flex; flex-direction: column; gap: 12px;
  padding: 20px 24px; height: 100%; overflow-y: auto;
}

.ap-top      { display: flex; flex-direction: column; gap: 6px; }
.ap-top-left { display: flex; flex-direction: column; gap: 6px; }

/* Agent name + model picker on the same row */
.ap-name-row {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.ap-editor-title { font-size: 15px; font-weight: 700; color: var(--text); flex-shrink: 0; }
.ap-editor-meta  { font-size: 13px; }
.meta-draft     { color: #92400e; }
.meta-published { color: var(--pri); }

.ap-model-top { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.ap-model-select {
  padding: 6px 10px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--surface-2); color: var(--text);
  font-size: 13px; cursor: pointer; outline: none; transition: border-color .15s;
}
.ap-model-select:focus { border-color: var(--pri); }

.ap-actions       { display: flex; align-items: center; gap: 8px; }
.ap-actions-right { display: flex; align-items: center; gap: 8px; margin-left: auto; }

/* ── Button system ───────────────────────────────────────────────────────── */
.ap-btn {
  padding: 7px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: 1.5px solid transparent;
  transition: background .13s, opacity .13s, border-color .13s;
  white-space: nowrap;
}
.ap-btn:disabled { opacity: .4; cursor: not-allowed; }

/* Primary — filled brand colour: Save Draft, Publish */
.ap-btn-primary {
  background: var(--pri); color: var(--pri-fg); border-color: transparent;
}
.ap-btn-primary:hover:not(:disabled) { opacity: .88; }

/* Secondary — visible border, surface bg: Cancel Changes */
.ap-btn-secondary {
  background: var(--surface); color: var(--text);
  border-color: var(--border);
}
.ap-btn-secondary:hover:not(:disabled) { background: var(--surface-2); }


.ap-save-msg { font-size: 13px; padding: 8px 12px; border-radius: 8px; }
.ap-save-msg.ok  { background: #dcfce7; color: #166534; }
.ap-save-msg.err { background: #fee2e2; color: #991b1b; }

.ap-textarea {
  flex: 1; min-height: 360px;
  background: var(--surface-2); color: var(--text);
  border: 1px solid var(--border); border-radius: 10px;
  padding: 14px 16px; font-size: 13px; font-family: 'Courier New', monospace;
  line-height: 1.65; resize: vertical; outline: none; transition: border-color .15s;
}
.ap-textarea:focus { border-color: var(--pri); }

.ap-empty {
  flex: 1; display: flex; align-items: center; justify-content: center;
  color: var(--muted); font-size: 14px;
}
</style>
