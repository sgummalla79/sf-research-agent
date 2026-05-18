<template>
  <div class="ps-wrap">
    <div class="ps-heading">
      <h2 class="ps-title">Providers</h2>
      <p class="ps-subtitle">Connect your LLM providers. Click a tile to add or update credentials.</p>
    </div>

    <div v-if="loading" class="ps-loading">Loading providers…</div>

    <div v-else class="ps-grid">
      <div
        v-for="p in providers"
        :key="p.id"
        class="ps-tile"
        :class="{ 'tile-connected': p.connected }"
        @click="openModal(p)"
      >
        <div class="ps-tile-logo">
          <img v-if="PROVIDER_LOGOS[p.id]" :src="PROVIDER_LOGOS[p.id]" :alt="p.name"
               :class="{ 'logo-mono-black': MONO_BLACK.has(p.id), 'logo-mono-white': MONO_WHITE.has(p.id) }" />
          <span v-else class="ps-logo-fallback"
            :style="{ background: PROVIDER_COLORS[p.id]?.bg, color: PROVIDER_COLORS[p.id]?.fg }">
            {{ p.name[0] }}
          </span>
        </div>

        <div class="ps-tile-body">
          <span class="ps-tile-name">{{ p.name }}</span>
          <span class="ps-tile-desc">{{ p.description }}</span>
        </div>

        <!-- Active/inactive pill — top-right corner, connected only -->
        <button
          v-if="p.connected"
          class="ps-pill-toggle ps-pill-corner"
          :class="p.isactive ? 'pill-active' : 'pill-inactive'"
          :disabled="toggling[p.id]"
          @click.stop="toggle(p.id)"
        >
          {{ p.isactive ? 'Active' : 'Inactive' }}
        </button>

        <div class="ps-tile-footer">
          <span class="ps-badge" :class="p.connected ? 'ok' : 'off'">
            {{ p.connected ? 'Connected ✓' : 'Not connected' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="modal" class="ps-overlay" @click.self="closeModal">
          <div class="ps-modal">
            <div class="ps-modal-hdr">
              <div class="ps-modal-logo">
                <img v-if="PROVIDER_LOGOS[modal.id]" :src="PROVIDER_LOGOS[modal.id]" :alt="modal.name"
                     :class="{ 'logo-mono-black': MONO_BLACK.has(modal.id), 'logo-mono-white': MONO_WHITE.has(modal.id) }" />
                <span v-else class="ps-logo-fallback sm"
                  :style="{ background: PROVIDER_COLORS[modal.id]?.bg, color: PROVIDER_COLORS[modal.id]?.fg }">
                  {{ modal.name[0] }}
                </span>
              </div>
              <div class="ps-modal-hdr-text">
                <h3 class="ps-modal-title">{{ modal.name }}</h3>
                <p class="ps-modal-desc">{{ modal.description }}</p>
              </div>
              <button class="ps-modal-close" @click="closeModal">✕</button>
            </div>

            <div v-for="field in TILE_FIELDS[modal.id]" :key="field.key" class="ps-field-group">
              <label class="ps-field-label">{{ field.label }}</label>
              <input
                v-model="keyInputs[field.key]"
                class="ps-input"
                :class="{ 'ps-input-err': errors[modal.id] }"
                type="password"
                :placeholder="modal.connected ? 'Enter new value to update…' : field.placeholder"
                autocomplete="off"
                @keydown.enter="connect(modal.id)"
              />
            </div>

            <p v-if="errors[modal.id]" class="ps-err">{{ errors[modal.id] }}</p>

            <div class="ps-modal-actions">
              <button
                class="ps-btn-connect"
                :disabled="connecting[modal.id] || !modalFieldsFilled"
                @click="connect(modal.id)"
              >
                {{ connecting[modal.id] ? 'Connecting…' : (modal.connected ? 'Update' : 'Connect') }}
              </button>
              <button
                v-if="modal.connected"
                class="ps-btn-disconnect"
                :disabled="disconnecting[modal.id]"
                @click="disconnect(modal.id)"
              >
                {{ disconnecting[modal.id] ? 'Disconnecting…' : 'Disconnect' }}
              </button>
            </div>

            <!-- Models section — shown when provider is connected -->
            <template v-if="modal.connected">
              <div class="ps-models-hdr">
                <span class="ps-models-title">Models</span>
                <span class="ps-models-hint">Activate the models you want to use</span>
                <button class="ps-models-refresh" :disabled="refreshing[modal.id]" @click="refreshModels(modal.id)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" width="13" height="13">
                    <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                  </svg>
                  {{ refreshing[modal.id] ? 'Refreshing…' : 'Refresh' }}
                </button>
              </div>
              <div v-if="modelsLoading[modal.id]" class="ps-models-loading">Loading models…</div>
              <div v-else-if="!modalModels.length" class="ps-models-empty">
                No models found. Click Refresh to fetch models.
              </div>
              <div v-else class="ps-models-grid">
                <div
                  v-for="m in modalModels"
                  :key="m.model_id"
                  class="ps-model-pill-wrap"
                >
                  <template v-if="editingModel === m.model_id">
                    <input
                      class="ps-model-pill ps-model-pill-input"
                      :value="editingName"
                      @input="editingName = $event.target.value"
                      @keydown.enter="saveModelName(modal.id, m)"
                      @keydown.escape="cancelEdit"
                      @blur="saveModelName(modal.id, m)"
                      ref="editInputEl"
                      autofocus
                    />
                  </template>
                  <template v-else>
                    <button
                      class="ps-model-pill"
                      :class="m.isactive ? 'pill-on' : 'pill-off'"
                      @click="toggleModel(modal.id, m.model_id)"
                    >
                      {{ m.display_name }}
                    </button>
                    <button class="ps-model-edit-btn" @click.stop="startEdit(m)" title="Rename">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="11" height="11">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                    </button>
                  </template>
                </div>
              </div>
            </template>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { apiFetch } from '../../composables/useFetch.js'
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { useProvidersStore } from '../../stores/providers'

const provStore = useProvidersStore()

const logoModules = import.meta.glob('../../assets/logos/*.svg', { eager: true, query: '?url', import: 'default' })
const PROVIDER_LOGOS = Object.fromEntries(
  Object.entries(logoModules).map(([path, url]) => {
    const id = path.split('/').pop().replace('.svg', '')
    return [id, url]
  })
)

// SVGs that are black (or currentColor) and need to be inverted in dark mode
const MONO_BLACK = new Set(['openai', 'groq', 'perplexity'])
// SVGs that are white and need to be inverted in light mode (none currently)
const MONO_WHITE = new Set()

const PROVIDER_COLORS = {
  anthropic:  { bg: '#CC785C', fg: '#fff' },
  openai:     { bg: '#0d0d0d', fg: '#fff' },
  google:     { bg: '#4285F4', fg: '#fff' },
  perplexity: { bg: '#1a1a2e', fg: '#20d9d2' },
  groq:       { bg: '#F55036', fg: '#fff' },
  bedrock:    { bg: '#FF9900', fg: '#fff' },
}

const TILE_FIELDS = {
  anthropic:  [{ key: 'anthropic',     label: 'API Key',           placeholder: 'sk-ant-api03-…' }],
  openai:     [{ key: 'openai',        label: 'API Key',           placeholder: 'sk-proj-…'       }],
  google:     [{ key: 'google',        label: 'API Key',           placeholder: 'AIza…'            }],
  perplexity: [{ key: 'perplexity',    label: 'API Key',           placeholder: 'pplx-…'           }],
  groq:       [{ key: 'groq',          label: 'API Key',           placeholder: 'gsk_…'            }],
  bedrock:    [
    { key: 'bedrock_url',   label: 'Bedrock Base URL', placeholder: 'https://…' },
    { key: 'bedrock_token', label: 'Auth Token',       placeholder: '…'         },
  ],
}

const providers     = ref([])
const loading       = ref(true)
const modal         = ref(null)
const keyInputs     = reactive({})
const errors        = reactive({})
const connecting    = reactive({})
const disconnecting = reactive({})
const toggling      = reactive({})
const refreshing    = reactive({})
const modelsLoading = reactive({})
const modalModels   = ref([])
const editingModel  = ref(null)
const editingName   = ref('')
const editInputEl   = ref(null)

async function load() {
  loading.value = true
  try {
    const res = await apiFetch('/api/providers')
    if (res.ok) {
      const data = await res.json()
      providers.value = data.providers || []
      for (const p of providers.value) {
        errors[p.id]        = errors[p.id]        ?? ''
        connecting[p.id]    = connecting[p.id]    ?? false
        disconnecting[p.id] = disconnecting[p.id] ?? false
        toggling[p.id]      = toggling[p.id]      ?? false
        for (const f of (TILE_FIELDS[p.id] || [])) {
          keyInputs[f.key] = keyInputs[f.key] ?? ''
        }
      }
    }
  } finally {
    loading.value = false
  }
}

const modalFieldsFilled = computed(() => {
  if (!modal.value) return false
  return (TILE_FIELDS[modal.value.id] || []).every(f => (keyInputs[f.key] || '').trim())
})

async function openModal(p) {
  errors[p.id]  = ''
  modal.value   = p
  modalModels.value = []
  if (p.connected) await loadModalModels(p.id)
}
function closeModal() { modal.value = null; modalModels.value = [] }

async function loadModalModels(pid) {
  modelsLoading[pid] = true
  try {
    const res = await apiFetch(`/api/providers/${pid}/models`)
    if (res.ok) modalModels.value = (await res.json()).models || []
  } finally {
    modelsLoading[pid] = false
  }
}

function startEdit(m) {
  editingModel.value = m.model_id
  editingName.value  = m.display_name
  nextTick(() => editInputEl.value?.focus())
}

function cancelEdit() {
  editingModel.value = null
  editingName.value  = ''
}

async function saveModelName(pid, m) {
  const name = editingName.value.trim()
  if (!name || name === m.display_name) { cancelEdit(); return }
  const res = await apiFetch(
    `/api/providers/${pid}/models/${encodeURIComponent(m.model_id)}/display-name`,
    { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_name: name }) }
  )
  if (res.ok) {
    m.display_name = name
    provStore.markUpdated()
  }
  cancelEdit()
}

async function toggleModel(pid, modelId) {
  const res = await apiFetch(`/api/providers/${pid}/models/${encodeURIComponent(modelId)}`, { method: 'PATCH' })
  if (res.ok) {
    const data = await res.json()
    const m = modalModels.value.find(x => x.model_id === modelId)
    if (m) m.isactive = data.isactive
    provStore.markUpdated()
  }
}

async function refreshModels(pid) {
  refreshing[pid] = true
  errors[pid] = ''
  try {
    const res  = await apiFetch(`/api/providers/${pid}/refresh`, { method: 'POST' })
    const data = await res.json()
    if (res.ok) {
      await loadModalModels(pid)
      provStore.markUpdated()
      if (data.fetch_error) {
        errors[pid] = `Could not fetch models: ${_friendlyFetchError(data.fetch_error)}`
      }
    } else {
      errors[pid] = data.detail || 'Refresh failed.'
    }
  } catch (_) {
    errors[pid] = 'Network error.'
  } finally {
    refreshing[pid] = false
  }
}

function _friendlyFetchError(msg) {
  if (!msg) return ''
  const low = msg.toLowerCase()
  if (low.includes('authentication') || low.includes('invalid') && low.includes('key') || low.includes('401'))
    return 'Invalid API key — please check and reconnect.'
  if (low.includes('network') || low.includes('connection') || low.includes('timeout'))
    return 'Network error — check your connection and try again.'
  if (low.includes('permission') || low.includes('forbidden') || low.includes('403'))
    return 'API key does not have permission to list models.'
  return msg.length > 120 ? msg.slice(0, 120) + '…' : msg
}

async function connect(pid) {
  errors[pid]     = ''
  connecting[pid] = true
  try {
    let res
    if (pid === 'bedrock') {
      res = await apiFetch('/api/providers/bedrock/connect', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          bedrock_url:   keyInputs['bedrock_url'].trim(),
          bedrock_token: keyInputs['bedrock_token'].trim(),
        }),
      })
    } else {
      res = await apiFetch(`/api/providers/${pid}/connect`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ api_key: keyInputs[pid].trim() }),
      })
    }
    const data = await res.json()
    if (res.ok) {
      for (const f of (TILE_FIELDS[pid] || [])) keyInputs[f.key] = ''
      await load()
      provStore.markUpdated()
      const updated = providers.value.find(p => p.id === pid)
      if (updated) { modal.value = updated; await loadModalModels(pid) }
      if (data.fetch_error) {
        errors[pid] = `Connected, but could not fetch models: ${_friendlyFetchError(data.fetch_error)}`
      }
    } else {
      errors[pid] = (typeof data.detail === 'string' ? data.detail : null) || 'Connection failed.'
    }
  } catch (_) {
    errors[pid] = 'Network error.'
  } finally {
    connecting[pid] = false
  }
}

async function disconnect(pid) {
  disconnecting[pid] = true
  try {
    const url = pid === 'bedrock' ? '/api/providers/bedrock' : `/api/providers/${pid}`
    const res = await apiFetch(url, { method: 'DELETE' })
    if (res.ok) {
      await load()
      provStore.markUpdated()
      const updated = providers.value.find(p => p.id === pid)
      if (updated) modal.value = updated
    }
  } finally {
    disconnecting[pid] = false
  }
}

async function toggle(pid) {
  toggling[pid] = true
  try {
    const url = pid === 'bedrock' ? '/api/providers/bedrock/toggle' : `/api/providers/${pid}/toggle`
    const res = await apiFetch(url, { method: 'PATCH' })
    if (res.ok) {
      const data = await res.json()
      const p = providers.value.find(x => x.id === pid)
      if (p) p.isactive = data.isactive
      provStore.markUpdated()
    }
  } finally {
    toggling[pid] = false
  }
}

onMounted(load)
</script>

<style scoped>
.ps-wrap    { display: flex; flex-direction: column; gap: 28px; }
.ps-heading { display: flex; flex-direction: column; gap: 6px; }
.ps-title   { font-size: 22px; font-weight: 700; color: var(--tx); margin: 0; }
.ps-subtitle { font-size: 13px; color: var(--muted); margin: 0; }
.ps-loading  { font-size: 13px; color: var(--muted); }

/* ── Tile grid ─────────────────────────────────────────────────────────────── */
.ps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 14px;
}

.ps-tile {
  position: relative;
  background: var(--inp);
  border: 1.5px solid var(--bdr);
  border-radius: 16px;
  padding: 20px 16px 14px;
  display: flex; flex-direction: column; gap: 12px;
  cursor: pointer;
  transition: border-color .18s, border-width .18s, box-shadow .18s;
  user-select: none;
}

.ps-pill-corner {
  position: absolute;
  top: 12px; right: 12px;
}
.ps-tile.tile-connected                  { border-color: rgba(34, 197, 94, .4); }
.ps-tile:not(.tile-connected)            { border-color: rgba(239, 68,  68, .4); }
.ps-tile.tile-connected:hover            { border-color: rgba(34, 197, 94, .9); border-width: 2.5px; box-shadow: 0 4px 16px rgba(0,0,0,.1); }
.ps-tile:not(.tile-connected):hover      { border-color: rgba(239, 68,  68, .9); border-width: 2.5px; box-shadow: 0 4px 16px rgba(0,0,0,.1); }

.ps-tile-logo { width: 44px; height: 44px; }
.ps-tile-logo img { width: 44px; height: 44px; object-fit: contain; border-radius: 10px; }

.ps-tile-body { display: flex; flex-direction: column; gap: 3px; flex: 1; }
.ps-tile-name { font-size: 14px; font-weight: 700; color: var(--tx); }
.ps-tile-desc { font-size: 11.5px; color: var(--muted); line-height: 1.4; }

.ps-tile-footer { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

/* ── Shared: badge, pill, logo fallback ────────────────────────────────────── */
.ps-badge { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 99px; white-space: nowrap; flex-shrink: 0; }
.ps-badge.ok  { background: #22c55e; color: #000; }
.ps-badge.off { background: #ef4444; color: #fff; }

.ps-pill-toggle {
  padding: 3px 12px; border-radius: 99px;
  font-size: 11px; font-weight: 600;
  border: 1.5px solid; cursor: pointer;
  transition: all .18s; flex-shrink: 0;
}
.ps-pill-toggle.pill-active   { background: rgba(34,197,94,.12); border-color: rgba(34,197,94,.4); color: #22c55e; }
.ps-pill-toggle.pill-inactive { background: rgba(148,163,184,.1); border-color: var(--bdr); color: var(--muted); }
.ps-pill-toggle:hover:not(:disabled).pill-active   { background: rgba(34,197,94,.22); }
.ps-pill-toggle:hover:not(:disabled).pill-inactive { background: rgba(148,163,184,.2); color: var(--tx); }
.ps-pill-toggle:disabled { opacity: .5; cursor: not-allowed; }

.ps-logo-fallback {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 700;
}
.ps-logo-fallback.sm { width: 36px; height: 36px; font-size: 16px; border-radius: 8px; }

/* ── Modal overlay ─────────────────────────────────────────────────────────── */
.ps-overlay {
  position: fixed; inset: 0; z-index: 600;
  background: rgba(0,0,0,.5); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
}

.ps-modal {
  background: var(--surf);
  border: 1px solid var(--bdr);
  border-radius: 18px;
  padding: 28px;
  width: 420px; max-width: calc(100vw - 32px);
  display: flex; flex-direction: column; gap: 18px;
  box-shadow: 0 24px 60px rgba(0,0,0,.25);
}

.ps-modal-hdr {
  display: flex; align-items: flex-start; gap: 14px;
}
.ps-modal-logo { width: 36px; height: 36px; flex-shrink: 0; }
.ps-modal-logo img { width: 36px; height: 36px; object-fit: contain; border-radius: 8px; }
.ps-modal-hdr-text { flex: 1; min-width: 0; }
.ps-modal-title { font-size: 16px; font-weight: 700; color: var(--tx); margin: 0 0 4px; }
.ps-modal-desc  { font-size: 12px; color: var(--muted); margin: 0; }
.ps-modal-close {
  background: none; border: none; cursor: pointer;
  color: var(--muted); font-size: 16px; padding: 2px 6px;
  border-radius: 6px; transition: color .15s, background .15s; flex-shrink: 0;
}
.ps-modal-close:hover { color: var(--tx); background: var(--hover); }

.ps-field-group { display: flex; flex-direction: column; gap: 6px; }
.ps-field-label { font-size: 12px; font-weight: 600; color: var(--muted); }
.ps-input {
  width: 100%; box-sizing: border-box;
  padding: 10px 13px; border-radius: 10px;
  border: 1.5px solid var(--bdr); background: var(--inp);
  font-size: 13px; color: var(--tx); outline: none;
  transition: border-color .15s;
}
.ps-input:focus   { border-color: var(--ifocus); }
.ps-input-err     { border-color: var(--danger) !important; }
.ps-input::placeholder { color: var(--muted); }
.ps-err { font-size: 12px; color: var(--danger); margin: -8px 0 0; }

.ps-modal-actions { display: flex; gap: 10px; }
.ps-btn-connect {
  flex: 1; padding: 10px 18px;
  background: var(--pri); color: var(--pri-fg);
  border: none; border-radius: 10px;
  font-size: 14px; font-weight: 600;
  cursor: pointer; transition: opacity .15s;
}
.ps-btn-connect:hover:not(:disabled) { opacity: .85; }
.ps-btn-connect:disabled { opacity: .4; cursor: not-allowed; }
.ps-btn-disconnect {
  padding: 10px 16px; border-radius: 10px;
  border: 1.5px solid var(--bdr); background: transparent;
  color: var(--danger); font-size: 14px; font-weight: 600;
  cursor: pointer; transition: background .15s, border-color .15s;
}
.ps-btn-disconnect:hover:not(:disabled) { background: rgba(239,68,68,.08); border-color: var(--danger); }
.ps-btn-disconnect:disabled { opacity: .4; cursor: not-allowed; }

/* ── Logo colour adaptation ────────────────────────────────────────────────── */
/* Black logos → white in dark mode */
:root.dark .logo-mono-black { filter: invert(1); }
/* White logos → black in light mode */
:root:not(.dark) .logo-mono-white { filter: invert(1); }

/* ── Models section ────────────────────────────────────────────────────────── */
.ps-models-hdr {
  display: flex; align-items: center; gap: 8px;
  padding-top: 4px; border-top: 1px solid var(--bdr);
}
.ps-models-title { font-size: 13px; font-weight: 700; color: var(--tx); }
.ps-models-hint  { font-size: 12px; color: var(--muted); flex: 1; }
.ps-models-refresh {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 7px;
  border: 1px solid var(--bdr); background: none;
  font-size: 12px; color: var(--muted); cursor: pointer;
  transition: color .15s, background .15s;
}
.ps-models-refresh:hover:not(:disabled) { color: var(--tx); background: var(--hover); }
.ps-models-refresh:disabled { opacity: .45; cursor: not-allowed; }

.ps-models-loading { font-size: 13px; color: var(--muted); padding: 8px 0; }
.ps-models-empty   { font-size: 13px; color: var(--muted); padding: 8px 0; }

.ps-models-grid {
  display: flex; flex-wrap: wrap; gap: 8px;
  max-height: 220px; overflow-y: auto;
  scrollbar-width: thin;
}
.ps-model-pill {
  padding: 5px 12px; border-radius: 99px;
  font-size: 12px; font-weight: 500; cursor: pointer;
  border: 1.5px solid; transition: all .15s; white-space: nowrap;
}
.ps-model-pill.pill-on  { background: rgba(34,197,94,.12);  border-color: rgba(34,197,94,.4);  color: #22c55e; }
.ps-model-pill.pill-off { background: rgba(148,163,184,.08); border-color: var(--bdr);          color: var(--muted); }
.ps-model-pill.pill-on:hover  { background: rgba(34,197,94,.22); }
.ps-model-pill.pill-off:hover { background: rgba(148,163,184,.16); color: var(--tx); }

.ps-model-pill-wrap {
  display: flex; align-items: center; gap: 2px;
}
.ps-model-edit-btn {
  display: flex; align-items: center; justify-content: center;
  padding: 3px; border-radius: 5px;
  border: none; background: none;
  color: var(--muted); cursor: pointer; opacity: 0;
  transition: opacity .15s, color .15s;
}
.ps-model-pill-wrap:hover .ps-model-edit-btn { opacity: 1; }
.ps-model-edit-btn:hover { color: var(--tx); }

.ps-model-pill-input {
  padding: 4px 10px; border-radius: 99px;
  font-size: 12px; font-weight: 500;
  border: 1.5px solid var(--pri); background: var(--inp);
  color: var(--tx); outline: none; min-width: 0; width: 140px;
}

/* ── Modal transition ──────────────────────────────────────────────────────── */
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity .2s, transform .2s; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
.modal-fade-enter-from .ps-modal, .modal-fade-leave-to .ps-modal { transform: scale(.96) translateY(8px); }
</style>
