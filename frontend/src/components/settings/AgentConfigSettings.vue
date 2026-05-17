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

              <div class="ac-picker-wrap">
                <button class="ac-picker-btn"
                  :class="{ 'ac-picker-empty': !selections[sk.skillKey + '::' + agent.agent_key] }"
                  @click.stop="togglePicker(sk.skillKey + '::' + agent.agent_key)">
                  {{ getSelectedLabel(sk.skillKey + '::' + agent.agent_key) }}
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
                    stroke-linecap="round" width="10" height="10">
                    <polyline points="6 9 12 15 18 9"/>
                  </svg>
                </button>
                <ModelMenu
                  :groups="getModelGroups(sk.skillKey + '::' + agent.agent_key)"
                  :open="openPickerKey === sk.skillKey + '::' + agent.agent_key"
                  direction="below"
                  @select="v => onModelPick(sk.skillKey, agent.agent_key, v)"
                  @close="openPickerKey = null"
                />
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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { apiFetch } from '../../composables/useFetch'
import { useProvidersStore } from '../../stores/providers'
import ModelMenu from '../ui/ModelMenu.vue'


// ── State ─────────────────────────────────────────────────────────────────────
const skillAgents      = ref([])       // [{skillKey, name, icon, agents: [...]}]
const activeModels     = ref([])       // [{provider, model_id, display_name}] from /api/models/active
const selections       = reactive({})  // "skillKey::agentKey" → "provider::model_id"
const saving           = reactive({})  // skillKey → bool
const saveMsgs         = reactive({})  // skillKey → {type, text}
const loading          = ref(true)
const openPickerKey    = ref(null)     // which row's picker is open

const hasAnyModels = computed(() => activeModels.value.length > 0)

// Group active models by provider
const modelsByProvider = computed(() => {
  const map = {}
  for (const m of activeModels.value) {
    if (!map[m.provider]) map[m.provider] = { name: m.provider_name || m.provider, models: [] }
    map[m.provider].models.push(m)
  }
  return map
})

function getModelGroups(selKey) {
  return Object.entries(modelsByProvider.value).map(([pid, { name, models }]) => ({
    key:   pid,
    label: name,
    items: models.map(m => ({
      label:    m.display_name,
      value:    `${pid}::${m.model_id}`,
      selected: selections[selKey] === `${pid}::${m.model_id}`,
    })),
  }))
}

function getSelectedLabel(selKey) {
  const val = selections[selKey]
  if (!val) return '— select model —'
  const [pid, mid] = val.split('::')
  const entry = modelsByProvider.value[pid]
  const m = (entry?.models || []).find(m => m.model_id === mid)
  return m ? m.display_name : mid
}

function togglePicker(key) {
  openPickerKey.value = openPickerKey.value === key ? null : key
}

function onModelPick(skillKey, agentKey, val) {
  selections[`${skillKey}::${agentKey}`] = val
  openPickerKey.value = null
  saveMsgs[skillKey] = null
}

// ── Load ──────────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    const [skillsRes, modelsRes] = await Promise.all([
      apiFetch('/api/skills'),
      apiFetch('/api/models/active'),
    ])

    if (modelsRes.ok) {
      const data = await modelsRes.json()
      activeModels.value = (data.models || []).map(m => ({
        ...m,
        provider_name: m.provider_name || m.provider,
      }))
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
async function suggestSkill(skillKey, agents) {
  try {
    const res = await apiFetch(`/api/skills/${skillKey}/suggest-config`)
    if (!res.ok) {
      saveMsgs[skillKey] = { type: 'err', text: 'No connected providers. Add API keys in Providers first.' }
      return
    }
    const { suggestions } = await res.json()
    let suggested = 0
    for (const agent of agents) {
      const pick = suggestions[agent.agent_key]
      if (pick) {
        selections[`${skillKey}::${agent.agent_key}`] = `${pick.provider}::${pick.model}`
        suggested++
      }
    }
    saveMsgs[skillKey] = suggested > 0
      ? { type: 'ok',  text: `Suggested models for ${suggested} agent${suggested !== 1 ? 's' : ''}. Review and save.` }
      : { type: 'err', text: 'No connected providers. Add API keys in Providers first.' }
  } catch (_) {
    saveMsgs[skillKey] = { type: 'err', text: 'Failed to fetch suggestions.' }
  }
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

const provStore = useProvidersStore()
watch(() => provStore.version, load)

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

.ac-picker-wrap { position: relative; flex-shrink: 0; }
.ac-picker-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; border-radius: 8px; white-space: nowrap;
  border: 1px solid var(--border); background: var(--surface); font-size: 13px;
  color: var(--text); cursor: pointer; transition: border-color .15s;
  min-width: 220px; justify-content: space-between;
}
.ac-picker-btn:hover   { border-color: var(--pri); }
.ac-picker-empty       { color: var(--muted); }
.ac-picker-btn svg     { color: var(--muted); flex-shrink: 0; }

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
