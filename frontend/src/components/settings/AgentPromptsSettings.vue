<!--
  AgentPromptsSettings — prompt editor per skill agent.

  Fetches agents via GET /api/skills/{skillKey}/agents.
  Draft: PUT /api/skills/{skillKey}/agents/{agentKey}/draft  {content}
  Discard: DELETE /api/skills/{skillKey}/agents/{agentKey}/draft
  Model: PATCH /api/skills/{skillKey}/agents/{agentKey}/model  {provider, model}
-->
<template>
  <div class="ap-root">

    <!-- ── Left: agent list ────────────────────────────────────────────────── -->
    <aside class="ap-list">
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

        <div class="ap-top">
          <div class="ap-top-left">
            <div class="ap-editor-title">{{ selected.label || selected.agent_key }}</div>
            <div class="ap-editor-meta" :class="metaClass">{{ metaText }}</div>
          </div>

          <!-- Model picker -->
          <div class="ap-model-top">
            <select class="ap-model-select" v-model="selectedModelKey" @change="onModelChange">
              <option value="__global__">Smart default</option>
              <optgroup v-for="grp in filteredProviderGroups" :key="grp.id" :label="grp.label">
                <option v-for="m in grp.models" :key="`${grp.id}::${m.model}`"
                  :value="`${grp.id}::${m.model}`">
                  {{ m.label }}
                </option>
              </optgroup>
            </select>
            <button class="ap-suggest-btn" @click="suggestModel" title="Auto-suggest best model">
              ✦ Suggest
            </button>
          </div>
        </div>

        <!-- Action bar -->
        <div class="ap-actions">
          <button v-if="dirty && selected.published"
            class="ap-btn ap-btn-ghost" @click="revertToPublished" :disabled="saving">
            ↩ Revert
          </button>
          <button v-if="selected.has_draft" class="ap-btn ap-btn-ghost ap-btn-danger"
            @click="discardDraft" :disabled="saving">
            Discard draft
          </button>
          <button class="ap-btn ap-btn-secondary" @click="saveDraft" :disabled="saving || !dirty">
            {{ saving ? 'Saving…' : selected.has_draft ? 'Update Draft' : 'Save as Draft' }}
          </button>
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
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch } from '../../composables/useFetch.js'

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

const SLOT_SUGGESTIONS = {
  researcher_search:    'perplexity::sonar-pro',
  researcher_reasoning: 'google::gemini-2.5-pro',
  approver:             'anthropic::claude-opus-4-7',
}

// ── State ─────────────────────────────────────────────────────────────────────
const allSkills      = ref([])
const loadingSkills  = ref(true)
const connectedIds   = ref(new Set())   // provider ids that are connected

const activeSkillKey   = ref(null)
const selected         = ref(null)
const editorContent    = ref('')
const dirty            = ref(false)
const saving           = ref(false)
const saveMsg          = ref(null)
const selectedModelKey = ref('__global__')

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

function suggestModel() {
  const slot = selected.value?.slot
  const candidates = slot ? [SLOT_SUGGESTIONS[slot], 'anthropic::claude-sonnet-4-6'] : ['anthropic::claude-sonnet-4-6']
  // Pick first suggestion whose provider is connected
  const pick = candidates.find(c => {
    const pid = c?.split('::')[0]
    return pid && connectedIds.value.has(pid)
  })
  if (pick) {
    selectedModelKey.value = pick
    dirty.value = true
  }
}

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
  } finally {
    loadingSkills.value = false
  }
}

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
  selectedModelKey.value = keyFromModelConfig(agent.provider_to_use, agent.model_to_use)
  dirty.value   = false
  saveMsg.value = null
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

    // Save prompt draft
    const draftRes = await apiFetch(`/api/skills/${sk}/agents/${ak}/draft`, {
      method: 'PUT',
      body:   JSON.stringify({ content: editorContent.value }),
    })
    if (!draftRes.ok) {
      saveMsg.value = { type: 'err', text: 'Draft save failed.' }
      return
    }

    // Save model override if changed from global default
    if (selectedModelKey.value !== '__global__') {
      const [provider, model] = selectedModelKey.value.split('::')
      await apiFetch(`/api/skills/${sk}/agents/${ak}/model`, {
        method: 'PATCH',
        body:   JSON.stringify({ provider, model }),
      })
    }

    dirty.value   = false
    saveMsg.value = { type: 'ok', text: 'Draft saved.' }
    await refreshCurrentSkill()
  } catch (_) {
    saveMsg.value = { type: 'err', text: 'Network error.' }
  } finally {
    saving.value = false
  }
}

async function discardDraft() {
  if (!selected.value?.has_draft) return
  if (!confirm('Discard this draft? The unpublished changes will be lost.')) return
  saving.value = true
  try {
    await apiFetch(
      `/api/skills/${activeSkillKey.value}/agents/${selected.value.agent_key}/draft`,
      { method: 'DELETE' }
    )
    await refreshCurrentSkill()
  } finally {
    saving.value = false
  }
}

function revertToPublished() {
  if (!selected.value?.published?.content) return
  editorContent.value = selected.value.published.content
  dirty.value         = false
  saveMsg.value       = { type: 'ok', text: 'Reverted to published version.' }
}

onMounted(loadAll)
</script>

<style scoped>
.ap-root {
  display: flex; height: 100%; overflow: hidden;
  color: var(--text); font-family: inherit;
}

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

.ap-top {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
}
.ap-top-left { display: flex; flex-direction: column; gap: 3px; }
.ap-editor-title { font-size: 15px; font-weight: 700; color: var(--text); }
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
.ap-suggest-btn {
  padding: 6px 12px; border-radius: 8px; white-space: nowrap;
  border: 1px solid var(--border); background: var(--surface); color: var(--text);
  font-size: 13px; font-weight: 500; cursor: pointer; transition: background .13s;
}
.ap-suggest-btn:hover { background: var(--surface-2); border-color: var(--pri); color: var(--pri); }

.ap-actions { display: flex; align-items: center; gap: 8px; }

.ap-btn {
  padding: 7px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: 1px solid var(--border); transition: background .13s, opacity .13s;
}
.ap-btn:disabled { opacity: .45; cursor: not-allowed; }
.ap-btn-secondary { background: var(--surface); color: var(--text); }
.ap-btn-secondary:hover:not(:disabled) { background: var(--surface-2); }
.ap-btn-ghost { background: none; color: var(--muted); border-color: transparent; }
.ap-btn-ghost:hover:not(:disabled) { color: var(--text); background: var(--surface-2); }
.ap-btn-ghost.ap-btn-danger:hover:not(:disabled) { color: #991b1b; }

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
