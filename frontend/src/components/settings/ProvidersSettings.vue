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
            <span class="ps-name">{{ p.name }}</span>
            <span class="ps-desc">{{ p.description }}</span>
          </div>
          <span class="ps-badge" :class="p.connected ? 'ok' : 'off'">
            {{ p.connected ? 'Connected ✓' : 'Not connected' }}
          </span>
        </div>

        <!-- Key input row -->
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
        <p v-if="errors[p.id]" class="ps-err">{{ errors[p.id] }}</p>

        <!-- Model chips -->
        <div v-if="p.connected && p.models.length" class="ps-models">
          <span v-for="m in p.models" :key="m" class="ps-model-chip">{{ m }}</span>
        </div>
        <p v-if="p.connected && !p.models.length" class="ps-no-models">
          No models fetched yet —
          <button class="ps-link" @click="refresh(p.id)">fetch now</button>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'

const providers   = ref([])
const loading     = ref(true)
const keyInputs   = reactive({})
const errors      = reactive({})
const connecting  = reactive({})
const refreshing  = reactive({})
const disconnecting = reactive({})

async function load() {
  loading.value = true
  try {
    const res = await fetch('/api/providers')
    if (res.ok) {
      const data = await res.json()
      providers.value = data.providers || []
      for (const p of providers.value) {
        keyInputs[p.id]    = keyInputs[p.id] ?? ''
        errors[p.id]       = ''
        connecting[p.id]   = false
        refreshing[p.id]   = false
        disconnecting[p.id] = false
      }
    }
  } finally {
    loading.value = false
  }
}

async function connect(pid) {
  const key = (keyInputs[pid] || '').trim()
  if (!key) return
  errors[pid]     = ''
  connecting[pid] = true
  try {
    const res  = await fetch(`/api/providers/${pid}/connect`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ api_key: key }),
    })
    const data = await res.json()
    if (res.ok) {
      keyInputs[pid] = ''
      await load()
    } else {
      errors[pid] = data.detail || 'Connection failed.'
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
    const res  = await fetch(`/api/providers/${pid}/refresh`, { method: 'POST' })
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
    const res = await fetch(`/api/providers/${pid}`, { method: 'DELETE' })
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
.ps-card.connected { border-color: #22c55e44; }

.ps-card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.ps-card-info { display: flex; flex-direction: column; gap: 3px; }
.ps-name { font-size: 15px; font-weight: 700; color: var(--tx); }
.ps-desc { font-size: 12px; color: var(--muted); }
.ps-badge { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 99px; flex-shrink: 0; white-space: nowrap; }
.ps-badge.ok  { background: #22c55e22; color: #4ade80; }
.ps-badge.off { background: #6b728022; color: var(--muted); }

.ps-key-row { display: flex; gap: 8px; align-items: center; }
.ps-input {
  flex: 1; min-width: 0; padding: 9px 12px; border-radius: 8px;
  border: 1.5px solid var(--bdr); background: var(--surf); font-size: 13px;
  color: var(--tx); outline: none; transition: border-color .15s;
}
.ps-input:focus   { border-color: var(--ifocus); }
.ps-input-err     { border-color: #ef4444 !important; }
.ps-input::placeholder { color: var(--muted); }
.ps-err { font-size: 12px; color: #ef4444; margin: -6px 0 0; }

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
.ps-btn-disconnect:hover:not(:disabled) { color: #ef4444; background: #ef444418; }
.ps-btn-refresh:disabled, .ps-btn-disconnect:disabled { opacity: .4; cursor: not-allowed; }

.ps-models { display: flex; flex-wrap: wrap; gap: 6px; }
.ps-model-chip {
  font-size: 11px; font-family: monospace; padding: 3px 10px;
  background: var(--surf); border: 1px solid var(--bdr);
  border-radius: 6px; color: var(--muted);
}
.ps-no-models { font-size: 12px; color: var(--muted); margin: 0; }
.ps-link {
  background: none; border: none; color: var(--pri); font-size: 12px;
  cursor: pointer; padding: 0; text-decoration: underline;
}
</style>
