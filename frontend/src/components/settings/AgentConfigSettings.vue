<template>
  <div class="ac-wrap">
    <div class="ac-heading">
      <h2 class="ac-title">Agent Configuration</h2>
      <p class="ac-subtitle">
        Choose the model for each agent step. Only models from connected providers are shown.
        This configuration is snapshotted when a new session starts — changing it here
        does not affect sessions already in progress.
      </p>
    </div>

    <div v-if="loading" class="ac-loading">Loading…</div>

    <template v-else>
      <!-- Legend -->
      <div class="ac-legend">
        <div class="ac-legend-row">
          <span class="ac-legend-icon">i</span>
          <span>
            <strong>200K ctx</strong> — context window: max text the model can read in one call (your prompt + its reply combined, ~150,000 words)
            &nbsp;·&nbsp;
            <strong>64K out</strong> — max tokens the model can write back per response (~48,000 words)
            &nbsp;·&nbsp;
            <strong>$3.00 / $15.00 per 1M</strong> — you pay $3.00 for every million tokens you send in, $15.00 for every million tokens it generates back.
            A typical session (10 messages, ~5,000 tokens) costs roughly $0.09.
          </span>
        </div>
      </div>

      <div v-if="!hasAnyModels" class="ac-empty">
        No providers connected yet. Go to <strong>Providers</strong> to add your API keys first.
      </div>

      <div v-else class="ac-table">
        <div v-for="slot in slots" :key="slot" class="ac-row">
          <div class="ac-slot-info">
            <span class="ac-slot-label">{{ labels[slot] }}</span>
            <span v-if="currentConfig[slot]" class="ac-current-badge">
              {{ currentConfig[slot].provider }} / {{ currentConfig[slot].model }}
            </span>
          </div>
          <div class="ac-select-wrap">
            <select v-model="selections[slot]" class="ac-select" :class="{ 'ac-select-empty': !selections[slot] }" @change="onSelectChange(slot)">
              <option value="" disabled>— select model —</option>
              <template v-for="pid in connectedProviderIds" :key="pid">
                <optgroup :label="providerNames[pid]">
                  <option
                    v-for="m in availableModels[pid]"
                    :key="`${pid}::${m}`"
                    :value="`${pid}::${m}`"
                  >{{ m }}</option>
                </optgroup>
              </template>
            </select>
            <!-- Model metadata strip -->
            <div v-if="selections[slot]" class="ac-meta">
              <span v-if="modelInfo[slot] === undefined" class="ac-meta-dim">···</span>
              <span v-else-if="modelInfo[slot]" class="ac-meta-line">
                {{ fmtCtx(modelInfo[slot].context_window) }} ctx
                · {{ fmtCtx(modelInfo[slot].max_output_tokens) }} out
                · <span class="ac-meta-cost">${{ fmt$(modelInfo[slot].input_cost_per_million) }} / ${{ fmt$(modelInfo[slot].output_cost_per_million) }} per 1M</span>
              </span>
              <span v-else class="ac-meta-dim">No pricing info available</span>
            </div>
          </div>
        </div>
      </div>

      <div class="ac-footer">
        <div class="ac-footer-left">
          <button class="ac-btn-clear" :disabled="!hasAnyModels" @click="clear">
            Clear
          </button>
          <button class="ac-btn-suggest" :disabled="!hasAnyModels" @click="suggest">
            ✦ Suggest
          </button>
        </div>
        <div class="ac-footer-right">
          <span v-if="saveMsg" class="ac-msg" :class="saveMsg.type">{{ saveMsg.text }}</span>
          <button class="ac-save-btn" :disabled="saving || !hasAnyModels" @click="save">
            {{ saving ? 'Saving…' : 'Save Configuration' }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'

// ── Priority rules per agent slot ─────────────────────────────────────────────
const SLOT_PRIORITY = {
  intake: [
    { provider: 'anthropic', prefer: ['claude-sonnet', 'claude-haiku', 'claude'] },
    { provider: 'openai',    prefer: ['gpt-4o', 'o4', 'o3', 'gpt-4'] },
    { provider: 'google',    prefer: ['gemini-2.5-pro', 'gemini-2.5', 'gemini-2.0-flash', 'gemini'] },
    { provider: 'groq',      prefer: ['llama-3.3', 'llama-3.1', 'llama'] },
    { provider: 'mistral',   prefer: ['mistral-large', 'mistral-medium', 'mistral-small', 'mistral'] },
  ],
  discovery: [
    { provider: 'anthropic', prefer: ['claude-sonnet', 'claude-haiku', 'claude'] },
    { provider: 'openai',    prefer: ['gpt-4o', 'o4', 'o3', 'gpt-4'] },
    { provider: 'google',    prefer: ['gemini-2.5-pro', 'gemini-2.5', 'gemini-2.0-flash', 'gemini'] },
    { provider: 'groq',      prefer: ['llama-3.3', 'llama-3.1', 'llama'] },
    { provider: 'mistral',   prefer: ['mistral-large', 'mistral-medium', 'mistral-small', 'mistral'] },
  ],
  researcher_search: [
    { provider: 'perplexity', prefer: ['sonar-pro', 'sonar-reasoning-pro', 'sonar-deep-research', 'sonar'] },
    { provider: 'openai',     prefer: ['gpt-4o', 'o4', 'o3', 'gpt-4'] },
    { provider: 'anthropic',  prefer: ['claude-sonnet', 'claude'] },
    { provider: 'google',     prefer: ['gemini-2.5-pro', 'gemini'] },
  ],
  researcher_reasoning: [
    { provider: 'google',    prefer: ['gemini-2.5-pro', 'gemini-2.5', 'gemini-2.0-flash', 'gemini'] },
    { provider: 'anthropic', prefer: ['claude-opus', 'claude-sonnet', 'claude'] },
    { provider: 'openai',    prefer: ['gpt-4o', 'o3', 'o4', 'gpt-4'] },
    { provider: 'groq',      prefer: ['llama-3.3', 'llama-3.1', 'llama'] },
  ],
  researcher_writer: [
    { provider: 'anthropic', prefer: ['claude-sonnet', 'claude-haiku', 'claude'] },
    { provider: 'openai',    prefer: ['gpt-4o', 'o4', 'o3', 'gpt-4'] },
    { provider: 'google',    prefer: ['gemini-2.5-pro', 'gemini-2.5', 'gemini-2.0-flash', 'gemini'] },
    { provider: 'groq',      prefer: ['llama-3.3', 'llama-3.1', 'llama'] },
    { provider: 'mistral',   prefer: ['mistral-large', 'mistral-medium', 'mistral-small', 'mistral'] },
  ],
  reviewer: [
    { provider: 'anthropic', prefer: ['claude-opus', 'claude-sonnet', 'claude'] },
    { provider: 'openai',    prefer: ['o3', 'o4', 'gpt-4o', 'gpt-4'] },
    { provider: 'google',    prefer: ['gemini-2.5-pro', 'gemini-2.5', 'gemini'] },
    { provider: 'groq',      prefer: ['llama-3.3', 'llama-3.1', 'llama'] },
  ],
  approver: [
    { provider: 'anthropic', prefer: ['claude-opus', 'claude-sonnet', 'claude'] },
    { provider: 'openai',    prefer: ['o3', 'o4', 'gpt-4o', 'gpt-4'] },
    { provider: 'google',    prefer: ['gemini-2.5-pro', 'gemini-2.5', 'gemini'] },
    { provider: 'groq',      prefer: ['llama-3.3', 'llama-3.1', 'llama'] },
  ],
}

// ── State ─────────────────────────────────────────────────────────────────────
const slots           = ref([])
const labels          = ref({})
const currentConfig   = ref({})
const availableModels = ref({})
const providerNames   = ref({})
const selections      = reactive({})
const modelInfo       = reactive({})   // slot → metadata object | null | undefined (loading)
const loading         = ref(true)
const saving          = ref(false)
const saveMsg         = ref(null)

const connectedProviderIds = computed(() =>
  Object.keys(availableModels.value).filter(pid => (availableModels.value[pid] || []).length > 0)
)
const hasAnyModels = computed(() => connectedProviderIds.value.length > 0)

// ── Formatters ────────────────────────────────────────────────────────────────
function fmtCtx(n) {
  if (!n) return '?'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1) + 'M'
  if (n >= 1_000)     return Math.round(n / 1_000) + 'K'
  return String(n)
}
function fmt$(n) {
  if (n == null) return '?'
  return n < 1 ? n.toFixed(n < 0.1 ? 3 : 2) : n.toFixed(2).replace(/\.00$/, '')
}

// ── Model info fetch ──────────────────────────────────────────────────────────
async function fetchModelInfo(slot) {
  const val = selections[slot]
  if (!val || !val.includes('::')) { modelInfo[slot] = null; return }
  const [provider, model] = val.split('::')
  modelInfo[slot] = undefined   // mark as loading
  try {
    const res = await fetch(`/api/providers/model-info?provider=${encodeURIComponent(provider)}&model=${encodeURIComponent(model)}`)
    if (!res.ok) { modelInfo[slot] = null; return }
    const data = await res.json()
    modelInfo[slot] = data.found ? data : null
  } catch (_) {
    modelInfo[slot] = null
  }
}

function onSelectChange(slot) {
  fetchModelInfo(slot)
}

// ── Data loading ──────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    const [cfgRes, pvdRes] = await Promise.all([
      fetch('/api/settings/agent-config'),
      fetch('/api/providers'),
    ])
    if (cfgRes.ok) {
      const data = await cfgRes.json()
      slots.value         = data.slots  || []
      labels.value        = data.labels || {}
      currentConfig.value = data.config || {}
      for (const slot of slots.value) {
        const cfg = (data.config || {})[slot]
        selections[slot] = cfg ? `${cfg.provider}::${cfg.model}` : ''
      }
    }
    if (pvdRes.ok) {
      const data   = await pvdRes.json()
      const models = {}
      const names  = {}
      for (const p of (data.providers || [])) {
        if (p.connected && p.models.length) {
          models[p.id] = p.models
          names[p.id]  = p.name
        }
      }
      availableModels.value = models
      providerNames.value   = names
    }
    // Fetch metadata for all pre-filled selections in parallel
    await Promise.all(slots.value.map(slot => fetchModelInfo(slot)))
  } finally {
    loading.value = false
  }
}

// ── Clear ─────────────────────────────────────────────────────────────────────
function clear() {
  for (const slot of slots.value) {
    selections[slot] = ''
    modelInfo[slot]  = null
  }
  saveMsg.value = null
}

// ── Suggest ───────────────────────────────────────────────────────────────────
function suggest() {
  let suggested = 0
  for (const slot of slots.value) {
    const priority = SLOT_PRIORITY[slot] || []
    let picked = null
    for (const { provider, prefer } of priority) {
      const models = availableModels.value[provider] || []
      if (!models.length) continue
      for (const pref of prefer) {
        const match = models.find(m => m.toLowerCase().includes(pref.toLowerCase()))
        if (match) { picked = `${provider}::${match}`; break }
      }
      if (!picked) picked = `${provider}::${models[0]}`
      if (picked) break
    }
    if (picked) {
      selections[slot] = picked
      fetchModelInfo(slot)
      suggested++
    }
  }
  saveMsg.value = suggested > 0
    ? { type: 'ok',  text: `Suggested models for ${suggested} agent${suggested > 1 ? 's' : ''}. Review and save when ready.` }
    : { type: 'err', text: 'No connected providers found. Go to Providers to add API keys first.' }
}

// ── Save ──────────────────────────────────────────────────────────────────────
async function save() {
  saving.value  = true
  saveMsg.value = null
  try {
    const config = {}
    for (const slot of slots.value) {
      const val = selections[slot]
      if (val && val.includes('::')) {
        const [provider, model] = val.split('::')
        config[slot] = { provider, model }
      }
    }
    const res  = await fetch('/api/settings/agent-config', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ config }),
    })
    const data = await res.json()
    if (res.ok) {
      currentConfig.value = data.config || {}
      saveMsg.value = { type: 'ok', text: 'Configuration saved. New sessions will use these models.' }
    } else {
      const errs = data.detail?.config_errors
      saveMsg.value = { type: 'err', text: errs ? Object.values(errs).join(' ') : (data.detail || 'Save failed.') }
    }
  } catch (_) {
    saveMsg.value = { type: 'err', text: 'Network error.' }
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ac-wrap { display: flex; flex-direction: column; gap: 28px; }
.ac-heading { display: flex; flex-direction: column; gap: 6px; }
.ac-title { font-size: 22px; font-weight: 700; color: var(--tx); margin: 0; }
.ac-subtitle { font-size: 13px; color: var(--muted); margin: 0; line-height: 1.6; }
.ac-loading { font-size: 13px; color: var(--muted); }

.ac-legend {
  font-size: 12px; color: var(--muted); line-height: 1.7;
  padding: 12px 16px; border-radius: 8px;
  background: var(--surf); border: 1px solid var(--bdr);
}
.ac-legend-row { display: flex; gap: 10px; align-items: flex-start; }
.ac-legend-icon {
  flex-shrink: 0; margin-top: 1px;
  width: 18px; height: 18px; border-radius: 50%;
  background: #f97316; color: #fff;
  font-size: 11px; font-weight: 700; font-style: italic;
  display: flex; align-items: center; justify-content: center;
}
.ac-legend strong { color: var(--tx); font-weight: 600; font-family: monospace; font-size: 11px; }

.ac-empty {
  background: var(--inp); border: 1.5px solid var(--bdr); border-radius: 10px;
  padding: 20px; font-size: 13px; color: var(--muted); text-align: center;
}

.ac-table { display: flex; flex-direction: column; gap: 10px; }

.ac-row {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 20px;
  background: var(--inp); border: 1.5px solid var(--bdr);
  border-radius: 10px; padding: 14px 18px;
  transition: border-color .15s;
}

.ac-slot-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; padding-top: 8px; }
.ac-slot-label { font-size: 14px; font-weight: 600; color: var(--tx); }
.ac-current-badge { font-size: 11px; font-family: monospace; color: var(--muted); }

/* Right column: select + meta info stacked */
.ac-select-wrap { flex-shrink: 0; width: 300px; display: flex; flex-direction: column; gap: 6px; }

.ac-select {
  width: 100%; padding: 9px 12px; border-radius: 8px;
  border: 1.5px solid var(--bdr); background: var(--surf); font-size: 13px;
  color: var(--tx); outline: none; cursor: pointer; transition: border-color .15s;
}
.ac-select:focus { border-color: var(--ifocus); }
.ac-select-empty { color: var(--muted); }

/* Metadata strip */
.ac-meta {
  padding: 4px 8px; border-radius: 6px;
  background: var(--surf); border: 1px solid var(--bdr);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ac-meta-line { font-size: 11px; color: var(--muted); }
.ac-meta-cost { color: var(--pri); font-weight: 600; }
.ac-meta-dim  { font-size: 11px; color: var(--muted); }

/* Footer */
.ac-footer {
  display: flex; align-items: center; justify-content: space-between; gap: 14px;
  padding-top: 4px;
}
.ac-footer-left  { display: flex; gap: 8px; }
.ac-footer-right { display: flex; align-items: center; gap: 14px; }

.ac-msg { font-size: 13px; font-weight: 500; }
.ac-msg.ok  { color: var(--success-tx); }
.ac-msg.err { color: var(--danger); }

.ac-btn-clear {
  padding: 9px 18px; background: transparent; color: var(--muted);
  border: 1.5px solid var(--bdr); border-radius: 10px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: color .15s, border-color .15s;
}
.ac-btn-clear:hover:not(:disabled) { color: var(--tx); border-color: var(--tx); }
.ac-btn-clear:disabled { opacity: .4; cursor: not-allowed; }

.ac-btn-suggest {
  padding: 9px 18px; background: rgba(201,112,64,0.08); color: var(--pri);
  border: 1.5px solid rgba(201,112,64,0.3); border-radius: 10px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: background .15s, border-color .15s;
}
.ac-btn-suggest:hover:not(:disabled) { background: rgba(201,112,64,0.12); border-color: var(--pri); }
.ac-btn-suggest:disabled { opacity: .4; cursor: not-allowed; }

.ac-save-btn {
  padding: 10px 22px; background: var(--pri); color: var(--pri-fg);
  border: none; border-radius: 10px; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: opacity .15s;
}
.ac-save-btn:hover:not(:disabled) { opacity: .85; }
.ac-save-btn:disabled { opacity: .45; cursor: not-allowed; }
</style>
