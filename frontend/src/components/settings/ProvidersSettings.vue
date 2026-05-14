<template>
  <div class="ps-wrap">
    <div class="ps-heading">
      <h2 class="ps-title">Providers</h2>
      <p class="ps-subtitle">Connect your LLM providers. After connecting, the available models for that provider will be fetched automatically.</p>
    </div>

    <div v-if="loading" class="ps-loading">Loading providers…</div>

    <div v-else class="ps-list">
      <div v-for="p in providers" :key="p.id" class="ps-card" :class="{ connected: p.connected }">
        <!-- Card header -->
        <div class="ps-card-header">
          <div class="ps-card-info">
            <div class="ps-name-row">
              <span class="ps-name">{{ p.name }}</span>
              <span class="ps-badge" :class="p.connected ? 'ok' : 'off'">
                {{ p.connected ? 'Connected ✓' : 'Not connected' }}
              </span>
            </div>
            <span class="ps-desc">{{ p.description }}</span>
          </div>
        </div>

        <!-- Mode toggle (Anthropic only) -->
        <div v-if="p.auth_modes" class="ps-mode-toggle">
          <button
            v-for="m in p.auth_modes"
            :key="m.id"
            class="ps-mode-btn"
            :class="{ active: selectedMode[p.id] === m.id }"
            @click="selectedMode[p.id] = m.id"
          >{{ m.label }}</button>
        </div>

        <!-- Key input row(s) -->
        <template v-if="p.auth_modes">
          <div
            v-for="field in p.auth_modes.find(m => m.id === selectedMode[p.id])?.fields ?? []"
            :key="field.key"
            class="ps-field-group"
          >
            <span class="ps-field-label">{{ field.label }}</span>
            <input
              v-model="keyInputs[field.key]"
              class="ps-input"
              :class="{ 'ps-input-err': errors[p.id] }"
              type="password"
              :placeholder="field.placeholder"
              :aria-label="field.label"
              autocomplete="off"
              @keydown.enter="connect(p.id)"
            />
          </div>
          <div class="ps-key-row ps-key-row-actions">
            <button
              class="ps-btn-connect"
              :disabled="connecting[p.id] || !modeFieldsFilled(p)"
              @click="connect(p.id)"
            >
              {{ connecting[p.id] ? 'Connecting…' : (p.connected ? 'Update' : 'Connect') }}
            </button>
            <button
              v-if="p.connected"
              class="ps-btn-refresh"
              :disabled="refreshing[p.id]"
              @click="refresh(p.id)"
              title="Re-fetch model list"
            >↻</button>
            <button
              v-if="p.connected"
              class="ps-btn-disconnect"
              :disabled="disconnecting[p.id]"
              @click="disconnect(p.id)"
              title="Disconnect"
            >✕</button>
          </div>
        </template>
        <template v-else>
          <div class="ps-key-row">
            <input
              v-model="keyInputs[p.id]"
              class="ps-input"
              :class="{ 'ps-input-err': errors[p.id] }"
              type="password"
              :placeholder="p.connected ? 'Enter new key to update…' : p.placeholder"
              autocomplete="off"
              @keydown.enter="connect(p.id)"
            />
            <button
              class="ps-btn-connect"
              :disabled="connecting[p.id] || !keyInputs[p.id]"
              @click="connect(p.id)"
            >
              {{ connecting[p.id] ? 'Connecting…' : (p.connected ? 'Update' : 'Connect') }}
            </button>
            <button
              v-if="p.connected"
              class="ps-btn-refresh"
              :disabled="refreshing[p.id]"
              @click="refresh(p.id)"
              title="Re-fetch model list"
            >↻</button>
            <button
              v-if="p.connected"
              class="ps-btn-disconnect"
              :disabled="disconnecting[p.id]"
              @click="disconnect(p.id)"
              title="Disconnect"
            >✕</button>
          </div>
        </template>
        <p v-if="errors[p.id]" class="ps-err">{{ errors[p.id] }}</p>

      </div>
    </div>
  </div>
</template>

<script setup>
import { apiFetch } from '../../composables/useFetch.js'
import { ref, reactive, onMounted } from 'vue'

const providers     = ref([])
const loading       = ref(true)
const keyInputs     = reactive({})
const selectedMode  = reactive({})
const errors        = reactive({})
const connecting    = reactive({})
const refreshing    = reactive({})
const disconnecting = reactive({})

async function load() {
  loading.value = true
  try {
    const res = await apiFetch('/api/providers')
    if (res.ok) {
      const data = await res.json()
      providers.value = data.providers || []
      for (const p of providers.value) {
        errors[p.id]        = ''
        connecting[p.id]    = false
        refreshing[p.id]    = false
        disconnecting[p.id] = false

        if (p.auth_modes) {
          // Initialize mode from backend active_mode
          selectedMode[p.id] = p.active_mode || p.auth_modes[0].id
          // Initialize a keyInput slot for every possible field across all modes
          for (const m of p.auth_modes) {
            for (const f of m.fields) {
              keyInputs[f.key] = keyInputs[f.key] ?? ''
            }
          }
        } else {
          keyInputs[p.id] = keyInputs[p.id] ?? ''
        }
      }
    }
  } finally {
    loading.value = false
  }
}

function modeFieldsFilled(p) {
  const mode = p.auth_modes.find(m => m.id === selectedMode[p.id])
  if (!mode) return false
  return mode.fields.every(f => (keyInputs[f.key] || '').trim())
}

async function connect(pid) {
  errors[pid]     = ''
  connecting[pid] = true
  try {
    const p = providers.value.find(x => x.id === pid)
    let body

    if (p?.auth_modes) {
      const mode = selectedMode[pid]
      const modeFields = p.auth_modes.find(m => m.id === mode)?.fields ?? []
      if (mode === 'bedrock') {
        body = {
          mode,
          bedrock_url:   (keyInputs['anthropic_bedrock_url']   || '').trim(),
          bedrock_token: (keyInputs['anthropic_bedrock_token'] || '').trim(),
        }
      } else {
        body = { mode, api_key: (keyInputs[modeFields[0]?.key] || '').trim() }
      }
    } else {
      body = { api_key: (keyInputs[pid] || '').trim() }
    }

    const res  = await apiFetch(`/api/providers/${pid}/connect`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    })
    const data = await res.json()
    if (res.ok) {
      // Clear inputs for all fields of this provider
      if (p?.auth_modes) {
        for (const m of p.auth_modes) {
          for (const f of m.fields) keyInputs[f.key] = ''
        }
      } else {
        keyInputs[pid] = ''
      }
      await load()
    } else {
      errors[pid] = (typeof data.detail === 'string' ? data.detail : null) || 'Connection failed.'
    }
  } catch (_) {
    errors[pid] = 'Network error.'
  } finally {
    connecting[pid] = false
  }
}

async function refresh(pid) {
  refreshing[pid] = true
  try {
    const res  = await apiFetch(`/api/providers/${pid}/refresh`, { method: 'POST' })
    const data = await res.json()
    if (res.ok) {
      const p = providers.value.find(x => x.id === pid)
      if (p) p.models = data.models || []
    }
  } finally {
    refreshing[pid] = false
  }
}

async function disconnect(pid) {
  disconnecting[pid] = true
  try {
    const res = await apiFetch(`/api/providers/${pid}`, { method: 'DELETE' })
    if (res.ok) await load()
  } finally {
    disconnecting[pid] = false
  }
}

onMounted(load)
</script>

<style scoped>
.ps-wrap { display: flex; flex-direction: column; gap: 32px; }
.ps-heading { display: flex; flex-direction: column; gap: 6px; }
.ps-title { font-size: 22px; font-weight: 700; color: var(--tx); margin: 0; }
.ps-subtitle { font-size: 13px; color: var(--muted); margin: 0; }
.ps-loading { font-size: 13px; color: var(--muted); }

.ps-list { display: flex; flex-direction: column; gap: 14px; }

.ps-card {
  background: var(--inp); border: 1.5px solid var(--bdr);
  border-radius: 12px; padding: 18px 20px;
  display: flex; flex-direction: column; gap: 12px;
  transition: border-color .2s;
}
.ps-card.connected { border-color: var(--success-bdr); }

.ps-card-header { display: flex; align-items: flex-start; gap: 12px; }
.ps-card-info { display: flex; flex-direction: column; gap: 4px; }
.ps-name-row { display: flex; align-items: center; gap: 8px; }
.ps-name { font-size: 15px; font-weight: 700; color: var(--tx); }
.ps-desc { font-size: 12px; color: var(--muted); }
.ps-badge { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 99px; flex-shrink: 0; white-space: nowrap; }
.ps-badge.ok  { background: rgba(34,197,94,0.12); color: var(--success-tx); }
.ps-badge.off { background: rgba(239,68,68,0.12); color: #f87171; }

.ps-mode-toggle { display: flex; gap: 6px; }
.ps-mode-btn {
  padding: 5px 14px; border-radius: 6px; font-size: 12px; font-weight: 600;
  border: 1.5px solid var(--bdr); background: var(--surf); color: var(--muted);
  cursor: pointer; transition: all .15s;
}
.ps-mode-btn:hover  { color: var(--tx); background: var(--inp); }
.ps-mode-btn.active { border-color: var(--pri); color: var(--pri); background: var(--inp); }

.ps-field-group { display: flex; flex-direction: column; gap: 5px; }
.ps-field-label { font-size: 12px; font-weight: 600; color: var(--muted); }
.ps-key-row-actions { margin-top: 2px; }
.ps-key-row { display: flex; gap: 8px; align-items: center; }
.ps-input {
  flex: 1; min-width: 0; padding: 9px 12px; border-radius: 8px;
  border: 1.5px solid var(--bdr); background: var(--surf); font-size: 13px;
  color: var(--tx); outline: none; transition: border-color .15s;
}
.ps-input:focus   { border-color: var(--ifocus); }
.ps-input-err     { border-color: var(--danger) !important; }
.ps-input::placeholder { color: var(--muted); }
.ps-err { font-size: 12px; color: var(--danger); margin: -6px 0 0; }

.ps-btn-connect {
  padding: 9px 16px; background: var(--pri); color: var(--pri-fg);
  border: none; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; white-space: nowrap; transition: opacity .15s;
}
.ps-btn-connect:hover:not(:disabled) { opacity: .85; }
.ps-btn-connect:disabled { opacity: .45; cursor: not-allowed; }

.ps-btn-refresh, .ps-btn-disconnect {
  width: 34px; height: 34px; border-radius: 8px; border: 1.5px solid var(--bdr);
  background: var(--surf); color: var(--muted); font-size: 14px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: color .15s, background .15s; flex-shrink: 0;
}
.ps-btn-refresh:hover:not(:disabled)    { color: var(--tx); background: var(--inp); }
.ps-btn-disconnect:hover:not(:disabled) { color: var(--danger); background: var(--danger-h); }
.ps-btn-refresh:disabled, .ps-btn-disconnect:disabled { opacity: .4; cursor: not-allowed; }

</style>
