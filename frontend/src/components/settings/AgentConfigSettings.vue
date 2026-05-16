<!--
  AgentConfigSettings — model selection per skill agent.

  Fetches agents from GET /api/skills/{skillKey}/agents.
  Saves via PATCH /api/skills/{skillKey}/agents/{agent_key}/model.
-->
<template>
  <div class="ac-wrap">
    <div class="ac-heading">
      <h2 class="ac-title">Agent Configuration</h2>
      <p class="ac-subtitle">
        Choose the default model for each agent step. Only models from connected providers are shown.
        This configuration is snapshotted when a new skill execution starts — changing it here does
        not affect executions already in progress.
      </p>
    </div>

    <div v-if="loading" class="ac-loading">Loading…</div>

    <template v-else>
      <div v-if="!hasAnyModels" class="ac-empty">
        No providers connected yet. Go to <strong>Providers</strong> to add your API keys first.
      </div>

      <template v-else>
        <!-- Per-skill section -->
        <div v-for="sk in skillAgents" :key="sk.skillKey" class="ac-skill-section">
          <div class="ac-skill-hdr">
            <span class="ac-skill-icon">{{ sk.icon }}</span>
            <span class="ac-skill-name">{{ sk.name }}</span>
          </div>

          <div class="ac-table">
            <div v-for="agent in sk.agents" :key="agent.agent_key" class="ac-row">
              <div class="ac-agent-info">
                <span class="ac-agent-label">{{ agent.label || agent.agent_key }}</span>
                <span v-if="agent.provider_to_use" class="ac-current-badge">
                  {{ agent.provider_to_use }} / {{ agent.model_to_use }}
                </span>
              </div>

              <div class="ac-select-wrap">
                <select
                  v-model="selections[sk.skillKey + '::' + agent.agent_key]"
                  class="ac-select"
                  :class="{ 'ac-select-empty': !selections[sk.skillKey + '::' + agent.agent_key] }"
                  @change="onSelectChange(sk.skillKey, agent.agent_key)">
                  <option value="" disabled>— select model —</option>
                  <template v-for="pid in connectedProviderIds" :key="pid">
                    <optgroup :label="providerNames[pid]">
                      <option
                        v-for="m in availableModels[pid]"
                        :key="`${pid}::${m}`"
                        :value="`${pid}::${m}`">{{ m }}</option>
                    </optgroup>
                  </template>
                </select>
              </div>
            </div>
          </div>

          <div class="ac-skill-footer">
            <div class="ac-footer-left">
              <button class="ac-btn-clear" @click="clearSkill(sk.skillKey)">Clear</button>
              <button class="ac-btn-suggest" @click="suggestSkill(sk.skillKey, sk.agents)">✦ Suggest</button>
            </div>
            <div class="ac-footer-right">
              <span v-if="saveMsgs[sk.skillKey]" class="ac-msg" :class="saveMsgs[sk.skillKey].type">
                {{ saveMsgs[sk.skillKey].text }}
              </span>
              <button class="ac-save-btn" :disabled="saving[sk.skillKey]" @click="saveSkill(sk)">
                {{ saving[sk.skillKey] ? 'Saving…' : 'Save' }}
              </button>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { apiFetch } from '../../composables/useFetch'

// ── Hardcoded model lists per provider (no caching needed) ───────────────────
const PROVIDER_MODEL_DEFAULTS = {
  anthropic:  ['claude-opus-4-7', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
  openai:     ['gpt-4o', 'gpt-4o-mini', 'o3', 'o4-mini'],
  google:     ['gemini-2.5-pro', 'gemini-2.0-flash-001', 'gemini-1.5-pro'],
  perplexity: ['sonar-pro', 'sonar-reasoning-pro', 'sonar'],
  groq:       ['llama-3.3-70b-versatile', 'llama-3.1-70b-versatile'],
}

// ── Slot-priority hints for Suggest ──────────────────────────────────────────
const SLOT_PRIORITY = {
  intake:               ['anthropic:claude-sonnet', 'openai:gpt-4o', 'google:gemini-2.0-flash'],
  discovery:            ['anthropic:claude-sonnet', 'openai:gpt-4o', 'google:gemini-2.0-flash'],
  researcher_search:    ['perplexity:sonar-pro', 'openai:gpt-4o', 'anthropic:claude-sonnet'],
  researcher_reasoning: ['google:gemini-2.5-pro', 'anthropic:claude-opus', 'openai:o3'],
  researcher_writer:    ['anthropic:claude-sonnet', 'openai:gpt-4o', 'google:gemini-2.0-flash'],
  reviewer:             ['anthropic:claude-opus', 'openai:o3', 'google:gemini-2.5-pro'],
  approver:             ['anthropic:claude-opus', 'openai:o3', 'google:gemini-2.5-pro'],
}

// ── State ─────────────────────────────────────────────────────────────────────
const skillAgents      = ref([])     // [{skillKey, name, icon, agents: [...]}]
const availableModels  = ref({})     // { providerId: [modelStr] }
const providerNames    = ref({})     // { providerId: displayName }
const selections       = reactive({})  // "skillKey::agentKey" → "provider::model"
const saving           = reactive({})  // skillKey → bool
const saveMsgs         = reactive({})  // skillKey → {type, text}
const loading          = ref(true)

const connectedProviderIds = computed(() =>
  Object.keys(availableModels.value).filter(pid => (availableModels.value[pid] || []).length > 0)
)
const hasAnyModels = computed(() => connectedProviderIds.value.length > 0)

// ── Load ──────────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    const [skillsRes, pvdRes] = await Promise.all([
      apiFetch('/api/skills'),
      apiFetch('/api/providers'),
    ])

    // Build provider model maps from hardcoded defaults (no cache needed)
    if (pvdRes.ok) {
      const data   = await pvdRes.json()
      const models = {}
      const names  = {}
      for (const p of (data.providers || [])) {
        if (!p.connected) continue
        models[p.id] = PROVIDER_MODEL_DEFAULTS[p.id] || []
        names[p.id]  = p.name
      }
      availableModels.value = models
      providerNames.value   = names
    }

    // Fetch agents for each installed skill
    if (skillsRes.ok) {
      const data    = await skillsRes.json()
      const result  = []

      for (const sk of (data.skills || [])) {
        if (!sk.installed) continue
        const agentsRes  = await apiFetch(`/api/skills/${sk.skill_key}/agents`)
        if (!agentsRes.ok) continue
        const agentsData = await agentsRes.json()

        // Populate selections from current user config
        for (const agent of (agentsData.agents || [])) {
          const selKey = `${sk.skill_key}::${agent.agent_key}`
          if (agent.provider_to_use && agent.model_to_use) {
            selections[selKey] = `${agent.provider_to_use}::${agent.model_to_use}`
          } else {
            selections[selKey] = ''
          }
        }

        result.push({
          skillKey: sk.skill_key,
          name:     sk.name,
          icon:     sk.icon || '⚡',
          agents:   agentsData.agents || [],
        })
      }

      skillAgents.value = result
    }
  } finally {
    loading.value = false
  }
}

// ── Change handler ─────────────────────────────────────────────────────────────
function onSelectChange(skillKey, agentKey) {
  // Clear any save message when selection changes
  saveMsgs[skillKey] = null
}

// ── Clear ──────────────────────────────────────────────────────────────────────
function clearSkill(skillKey) {
  const sk = skillAgents.value.find(s => s.skillKey === skillKey)
  if (!sk) return
  for (const agent of sk.agents) {
    selections[`${skillKey}::${agent.agent_key}`] = ''
  }
  saveMsgs[skillKey] = null
}

// ── Suggest ────────────────────────────────────────────────────────────────────
function suggestSkill(skillKey, agents) {
  let suggested = 0
  for (const agent of agents) {
    const slot     = agent.slot || agent.agent_key
    const priority = SLOT_PRIORITY[slot] || []
    let   picked   = null

    for (const hint of priority) {
      const [preferPid, preferModel] = hint.split(':')
      const models = availableModels.value[preferPid] || []
      if (!models.length) continue
      const match = models.find(m => m.toLowerCase().includes(preferModel.toLowerCase()))
      if (match) { picked = `${preferPid}::${match}`; break }
      picked = `${preferPid}::${models[0]}`; break
    }

    if (!picked) {
      // fallback: first available model from any connected provider
      for (const pid of connectedProviderIds.value) {
        const models = availableModels.value[pid] || []
        if (models.length) { picked = `${pid}::${models[0]}`; break }
      }
    }

    if (picked) {
      selections[`${skillKey}::${agent.agent_key}`] = picked
      suggested++
    }
  }
  saveMsgs[skillKey] = suggested > 0
    ? { type: 'ok',  text: `Suggested models for ${suggested} agent${suggested !== 1 ? 's' : ''}. Review and save.` }
    : { type: 'err', text: 'No connected providers. Add API keys in Providers first.' }
}

// ── Save ───────────────────────────────────────────────────────────────────────
async function saveSkill(sk) {
  saving[sk.skillKey]   = true
  saveMsgs[sk.skillKey] = null

  const errors = []
  for (const agent of sk.agents) {
    const selKey = `${sk.skillKey}::${agent.agent_key}`
    const val    = selections[selKey]
    if (!val || !val.includes('::')) continue

    const [provider, model] = val.split('::')
    const res = await apiFetch(`/api/skills/${sk.skillKey}/agents/${agent.agent_key}/model`, {
      method: 'PATCH',
      body:   JSON.stringify({ provider, model }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      errors.push(err.detail || `Failed for ${agent.agent_key}`)
    }
  }

  saving[sk.skillKey] = false
  saveMsgs[sk.skillKey] = errors.length
    ? { type: 'err', text: errors.join('; ') }
    : { type: 'ok',  text: 'Saved. New skill executions will use these models.' }

  // Refresh agents to show updated provider_to_use/model_to_use
  await load()
}

onMounted(load)
</script>

<style scoped>
.ac-wrap    { display: flex; flex-direction: column; gap: 28px; padding: 20px; }
.ac-heading { display: flex; flex-direction: column; gap: 6px; }
.ac-title   { font-size: 15px; font-weight: 700; color: var(--text); margin: 0; }
.ac-subtitle { font-size: 13px; color: var(--muted); margin: 0; line-height: 1.6; }
.ac-loading  { font-size: 13px; color: var(--muted); }

.ac-empty {
  background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px;
  padding: 20px; font-size: 13px; color: var(--muted); text-align: center;
}

.ac-skill-section { display: flex; flex-direction: column; gap: 12px; }
.ac-skill-hdr     { display: flex; align-items: center; gap: 8px; }
.ac-skill-icon    { font-size: 16px; }
.ac-skill-name    { font-size: 14px; font-weight: 700; color: var(--text); }

.ac-table  { display: flex; flex-direction: column; gap: 8px; }

.ac-row {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  background: var(--surface-2); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px 16px;
}

.ac-agent-info   { flex: 1; display: flex; flex-direction: column; gap: 3px; }
.ac-agent-label  { font-size: 13px; font-weight: 600; color: var(--text); }
.ac-current-badge { font-size: 11px; font-family: monospace; color: var(--muted); }

.ac-select-wrap { flex-shrink: 0; width: 280px; }
.ac-select {
  width: 100%; padding: 8px 10px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--surface); font-size: 13px;
  color: var(--text); outline: none; cursor: pointer; transition: border-color .15s;
}
.ac-select:focus      { border-color: var(--pri); }
.ac-select-empty      { color: var(--muted); }

.ac-skill-footer {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.ac-footer-left  { display: flex; gap: 8px; }
.ac-footer-right { display: flex; align-items: center; gap: 12px; }

.ac-msg      { font-size: 12.5px; font-weight: 500; }
.ac-msg.ok   { color: #166534; }
.ac-msg.err  { color: #991b1b; }

.ac-btn-clear {
  padding: 7px 14px; background: none; border: 1px solid var(--border);
  border-radius: 8px; font-size: 12.5px; font-weight: 500; color: var(--muted);
  cursor: pointer; transition: color .13s, border-color .13s;
}
.ac-btn-clear:hover { color: var(--text); border-color: var(--text); }

.ac-btn-suggest {
  padding: 7px 14px; background: none; border: 1px solid var(--pri);
  border-radius: 8px; font-size: 12.5px; font-weight: 600; color: var(--pri);
  cursor: pointer; transition: background .13s;
}
.ac-btn-suggest:hover { background: var(--surface-2); }

.ac-save-btn {
  padding: 7px 16px; background: var(--pri); color: var(--pri-fg);
  border: none; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: opacity .13s;
}
.ac-save-btn:hover:not(:disabled) { opacity: .88; }
.ac-save-btn:disabled { opacity: .45; cursor: not-allowed; }
</style>
