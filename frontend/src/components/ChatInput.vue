<template>
  <div class="ci-outer">
    <div class="chat-box" :class="{ 'drop-over': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop">

      <!-- No providers banner — attached to top of chat box -->
      <div v-if="noProviders" class="cb-no-providers">
        No LLM providers connected. Go to
        <button class="cb-np-link" @click="$emit('open-settings')">Settings → Providers</button>
        to connect your API keys.
      </div>

      <!-- File chip -->
      <div v-if="selectedFile" class="cb-file-row">
        <div class="cb-file-chip">
          <svg class="cb-file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
          </svg>
          <span>{{ selectedFile.name }}</span>
          <button class="cb-file-rm" @click="clearFile">✕</button>
        </div>
      </div>

      <!-- Slash command skill picker (floats above textarea) -->
      <transition name="fade">
        <div v-if="showSlashMenu" class="cb-slash-menu" @click.stop>
          <div class="cb-slash-header">Skills — type to filter</div>
          <button v-for="flow in slashFilteredFlows" :key="flow.id"
            class="cb-slash-item" @click="selectFromSlash(flow)">
            <span class="cb-slash-icon">{{ flow.icon }}</span>
            <div>
              <div class="cb-slash-name">{{ flow.name }}</div>
              <div class="cb-slash-desc">{{ flow.description }}</div>
            </div>
          </button>
          <div v-if="!slashFilteredFlows.length" class="cb-slash-empty">No matching skills</div>
        </div>
      </transition>

      <!-- Textarea -->
      <textarea v-model="text" class="cb-ta"
        :placeholder="noProviders ? '' : (pendingFlow ? `Describe your project for ${pendingFlow.name}…` : (hint || 'How can I help you today?'))"
        :disabled="noProviders"
        rows="2"
        @input="handleInput"
        @keydown.enter.exact.prevent="!streaming && handleSend()"
        @keydown.meta.enter.prevent="!streaming && handleSend()"
        @keydown.ctrl.enter.prevent="!streaming && handleSend()"
        @keydown.esc="showSlashMenu = false"
        @keydown.arrow-down.prevent="slashMenuFocusNext"
        @keydown.arrow-up.prevent="slashMenuFocusPrev" />

      <!-- Bottom bar -->
      <div class="cb-bar">

        <!-- + button and popup -->
        <div class="cb-plus-wrap">
          <button class="cb-plus" :class="{ active: plusMenuOpen }"
            @click.stop="plusMenuOpen = !plusMenuOpen" title="Add files or agent flows">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="16" height="16">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </button>

          <div v-if="plusMenuOpen" class="cb-plus-menu" @click.stop>
            <button class="cpm-item" @click="fileInputEl.click(); plusMenuOpen = false">
              <svg class="cpm-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
              </svg>
              Add files or photos
            </button>
            <input ref="fileInputEl" type="file" style="display:none"
              accept=".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg,.gif,.webp"
              @change="onFileChange" />

            <!-- Skills → submenu -->
            <template v-if="flows.length">
              <div class="cpm-divider" />
              <div class="cpm-skills-row"
                @mouseenter="skillsOpen = true"
                @mouseleave="skillsOpen = false"
                @click.stop="skillsOpen = !skillsOpen">
                <svg class="cpm-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
                  <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>
                </svg>
                <span>Skills</span>
                <svg class="cpm-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="12" height="12">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>

                <!-- Submenu -->
                <div v-if="skillsOpen" class="cpm-skills-submenu" @click.stop>
                  <button v-for="flow in flows" :key="flow.id"
                    class="cpm-item"
                    @click="onFlowSelect(flow); plusMenuOpen = false; skillsOpen = false">
                    <span class="cpm-flow-icon">{{ flow.icon }}</span>
                    {{ flow.name }}
                  </button>
                  <div class="cpm-divider" />
                  <button class="cpm-item" @click="emit('manage-skills'); plusMenuOpen = false; skillsOpen = false">
                    <svg class="cpm-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="16" height="16">
                      <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                    </svg>
                    Manage skills
                  </button>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- Pending flow pill — inline next to + button -->
        <div v-if="pendingFlow" class="cb-flow-pill">
          <span class="cb-flow-pill-icon">{{ pendingFlow.icon }}</span>
          <span>{{ pendingFlow.name }}</span>
          <button class="cb-flow-pill-rm" @click.stop="$emit('cancel-flow')" title="Back to normal chat">✕</button>
        </div>

        <div v-if="uploadError" class="cb-upload-err">{{ uploadError }}</div>

        <!-- Right controls -->
        <div class="cb-controls">

          <!-- Model picker (hidden when no models or an agent flow is armed) -->
          <div v-if="!pendingFlow && chatModels.length" class="cb-model-wrap">
            <button class="cb-model-btn"
              :class="{ 'cb-model-locked': modelLocked }"
              :disabled="modelLocked"
              @click.stop="modelPickerOpen = !modelPickerOpen">
              {{ selectedModel.display }}
              <svg v-if="!modelLocked" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="10" height="10">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </button>
            <div v-if="modelPickerOpen && !modelLocked" class="cb-model-dropdown" @click.stop>
              <div v-for="m in chatModels" :key="m.model"
                class="cbd-option" :class="{ selected: selectedModel.model === m.model }"
                @click="selectedModel = m; modelPickerOpen = false">
                <div class="cbd-name">{{ m.display }}</div>
                <div class="cbd-desc">{{ m.description }}</div>
                <span v-if="selectedModel.model === m.model" class="cbd-check">✓</span>
              </div>
            </div>
          </div>

          <!-- Adaptive Thinking — always visible, disabled for non-Anthropic -->
          <button v-if="chatModels.length"
            class="cb-adaptive-btn"
            :class="{ on: extendedThinking, 'cb-adaptive-off': selectedModel.provider !== 'anthropic' }"
            :disabled="selectedModel.provider !== 'anthropic'"
            :title="selectedModel.provider === 'anthropic'
              ? 'Adaptive Thinking — Claude thinks deeper before responding'
              : 'Adaptive Thinking is only available for Anthropic Claude models'"
            @click.stop="extendedThinking = !extendedThinking">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="15" height="15">
              <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
            <span>Adaptive</span>
          </button>

          <!-- Send button — disabled while LLM is responding -->
          <button class="cb-send"
            :disabled="streaming || (!selectedFile && !text.trim())"
            @click="handleSend">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
              <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  chatModels:   { type: Array,   default: () => [] },
  flows:        { type: Array,   default: () => [] },
  pendingFlow:  { type: Object,  default: null },
  hint:         { type: String,  default: null },
  modelLocked:  { type: Boolean, default: false },
  noProviders:  { type: Boolean, default: false },
  streaming:    { type: Boolean, default: false },  // LLM responding — block send, allow typing
})

const emit = defineEmits(['submit', 'upload', 'flow-select', 'cancel-flow', 'manage-skills', 'open-settings'])

// ── Internal state ────────────────────────────────────────────────────────────
const text             = ref('')
const selectedModel    = ref({ model: 'claude-sonnet-4-6', display: 'Sonnet 4.6', description: 'Responsive everyday work' })
const extendedThinking = ref(false)
const plusMenuOpen     = ref(false)
const skillsOpen       = ref(false)
const modelPickerOpen  = ref(false)
const selectedFile     = ref(null)
const imagePreviewUrl  = ref(null)
const isDragging       = ref(false)
const uploadError      = ref(null)
const fileInputEl      = ref(null)

// Slash command
const showSlashMenu       = ref(false)
const slashQuery          = ref('')
const slashFilteredFlows  = computed(() => {
  const q = slashQuery.value.toLowerCase()
  return q
    ? props.flows.filter(f => f.id.includes(q) || f.name.toLowerCase().includes(q))
    : props.flows
})

function handleInput() {
  const val = text.value
  if (val.startsWith('/') && props.flows.length) {
    slashQuery.value    = val.slice(1)
    showSlashMenu.value = true
  } else {
    showSlashMenu.value = false
    slashQuery.value    = ''
  }
}

function selectFromSlash(flow) {
  text.value          = ''
  showSlashMenu.value = false
  slashQuery.value    = ''
  onFlowSelect(flow)
}

function slashMenuFocusNext() { /* keyboard nav stub — extend later */ }
function slashMenuFocusPrev() { /* keyboard nav stub — extend later */ }

// Sync default model when chatModels prop arrives (fetched async by parent)
watch(() => props.chatModels, (models) => {
  if (!models.length) return
  const def = models.find(m => m.default) || models[0]
  if (def) selectedModel.value = def
}, { immediate: true })

// Sync Adaptive Thinking with provider — on for Anthropic, off + disabled for others
watch(() => selectedModel.value.provider, (provider) => {
  extendedThinking.value = provider === 'anthropic'
}, { immediate: true })

// ── File handling ─────────────────────────────────────────────────────────────
const MAX_MB   = 10
const IMG_EXTS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp'])
const ALL_EXTS = ['.pdf', '.docx', '.doc', '.txt', '.md', ...IMG_EXTS]

function clearFile() {
  if (imagePreviewUrl.value) URL.revokeObjectURL(imagePreviewUrl.value)
  selectedFile.value    = null
  imagePreviewUrl.value = null
  uploadError.value     = null
}

function setFile(file) {
  uploadError.value = null
  imagePreviewUrl.value = null
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!ALL_EXTS.includes(ext)) { uploadError.value = 'Unsupported file type.'; return }
  if (file.size > MAX_MB * 1048576) { uploadError.value = `Max ${MAX_MB} MB.`; return }
  selectedFile.value = file
  if (IMG_EXTS.has(ext)) imagePreviewUrl.value = URL.createObjectURL(file)
}

function onFileChange(e) { const f = e.target.files?.[0]; if (f) setFile(f) }
function onDrop(e) { isDragging.value = false; const f = e.dataTransfer?.files?.[0]; if (f) setFile(f) }

// ── Actions ───────────────────────────────────────────────────────────────────
const opts = () => ({ model: selectedModel.value.model, provider: selectedModel.value.provider || 'anthropic', extendedThinking: extendedThinking.value })

function handleSend() {
  if (selectedFile.value) {
    emit('upload', selectedFile.value, opts())
    clearFile()
    return
  }
  if (!text.value.trim()) return
  emit('submit', text.value.trim(), opts())
  text.value = ''
}

function onFlowSelect(flow) {
  plusMenuOpen.value = false
  emit('flow-select', flow)
}

// ── Close popups on outside click ─────────────────────────────────────────────
function closeMenus() {
  plusMenuOpen.value  = false
  skillsOpen.value    = false
  modelPickerOpen.value = false
  showSlashMenu.value = false
}
onMounted(() => document.addEventListener('click', closeMenus))
onUnmounted(() => document.removeEventListener('click', closeMenus))
</script>

<style scoped>
/* Outer wrapper — matches .input-panel spacing */
.ci-outer { flex-shrink: 0; padding: 10px 20px 16px; background: var(--bg); }

/* Chat box */
.chat-box {
  position: relative;
  background: var(--surf);
  border: 1px solid var(--bdr);
  border-radius: 18px;
  padding: 12px 14px 10px;
  display: flex; flex-direction: column; gap: 6px;
  box-shadow: 0 1px 6px rgba(0,0,0,.06);
  transition: border-color .15s;
}
.chat-box:focus-within { border-color: var(--ifocus); }
.chat-box.drop-over    { border-color: var(--pri); background: var(--sbg); }

/* Pending flow pill (inline in bottom bar) */
.cb-flow-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 8px 4px 10px; border-radius: 20px;
  background: var(--sbg); border: 1px solid var(--sbdr);
  color: var(--stx); font-size: 12.5px; font-weight: 600;
}
.cb-flow-pill-icon { font-size: 14px; }
.cb-flow-pill-rm {
  background: none; border: none; cursor: pointer;
  color: var(--stx); opacity: 0.6; padding: 0 0 0 2px;
  font-size: 12px; line-height: 1; border-radius: 50%;
  transition: opacity .13s;
}
.cb-flow-pill-rm:hover { opacity: 1; }

/* File chip */
.cb-file-row { display: flex; }
.cb-file-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px 4px 8px; border-radius: 8px;
  background: var(--sbg); border: 1px solid var(--sbdr);
  color: var(--stx); font-size: 12.5px; font-weight: 500; max-width: 320px;
}
.cb-file-icon { flex-shrink: 0; }
.cb-file-chip span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cb-file-rm {
  background: none; border: none; cursor: pointer;
  color: var(--muted); padding: 0 0 0 4px; font-size: 13px; line-height: 1;
}
.cb-file-rm:hover { color: var(--tx); }

/* Textarea */
/* No-providers banner inside the chat box */
.cb-no-providers {
  padding: 8px 10px;
  font-size: 12.5px; font-weight: 500;
  color: #fff;
  background: #7f1d1d;
  border-radius: 8px;
  margin-bottom: 6px;
}
.cb-np-link {
  background: none; border: none; cursor: pointer;
  font-size: 12.5px; font-weight: 700; color: #fff;
  padding: 0; text-decoration: underline; text-underline-offset: 2px;
}

.cb-ta {
  width: 100%; box-sizing: border-box;
  background: transparent; border: none; outline: none; resize: none;
  font-size: 15px; font-family: inherit; color: var(--tx); line-height: 1.55;
  padding: 2px 2px; min-height: 44px; max-height: 220px;
}
.cb-ta::placeholder { color: var(--muted); }
.cb-ta:disabled { opacity: 0.4; cursor: not-allowed; }

/* Bottom bar */
.cb-bar { display: flex; align-items: center; gap: 6px; }

/* + button */
.cb-plus-wrap { position: relative; flex-shrink: 0; }
.cb-plus {
  width: 32px; height: 32px; border-radius: 8px;
  border: 1px solid var(--bdr); background: transparent;
  color: var(--muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background .13s, color .13s, border-color .13s;
}
.cb-plus:hover, .cb-plus.active {
  background: var(--hover); color: var(--tx); border-color: var(--ifocus);
}

/* + popup menu */
.cb-plus-menu {
  position: absolute; bottom: calc(100% + 8px); left: 0;
  width: 230px; background: var(--surf);
  border: 1px solid var(--bdr); border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,.14);
  z-index: 300; overflow: visible; padding: 4px 0;
}
.cpm-item {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 9px 14px;
  background: none; border: none; cursor: pointer;
  font-size: 14px; color: var(--tx); text-align: left;
  transition: background .1s;
}
.cpm-item:hover { background: var(--hover); }
.cpm-icon { flex-shrink: 0; color: var(--muted); }
.cpm-divider { height: 1px; background: var(--bdr); margin: 4px 0; }
.cpm-section-label {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: .07em; color: var(--muted); padding: 4px 14px 2px;
}
.cpm-flow-item { justify-content: space-between; }
.cpm-flow-icon { font-size: 15px; flex-shrink: 0; }
.cpm-chevron   { flex-shrink: 0; color: var(--muted); margin-left: auto; }

/* Skills → row with nested submenu */
.cpm-skills-row {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 9px 14px; cursor: pointer;
  font-size: 14px; color: var(--tx);
  transition: background .1s; position: relative;
}
.cpm-skills-row:hover { background: var(--hover); }
.cpm-skills-submenu {
  position: absolute; left: 100%; bottom: 0;
  width: 220px; background: var(--surf);
  border: 1px solid var(--bdr); border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,.14);
  z-index: 400; overflow: hidden; padding: 4px 0;
}

/* Slash command picker */
.cb-slash-menu {
  position: absolute; bottom: calc(100% + 6px); left: 0; right: 0;
  background: var(--surf); border: 1px solid var(--bdr); border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,.14);
  z-index: 300; overflow: hidden;
  max-height: 280px; overflow-y: auto;
}
.cb-slash-header {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--muted);
  padding: 8px 14px 4px;
}
.cb-slash-item {
  display: flex; align-items: flex-start; gap: 12px;
  width: 100%; padding: 10px 14px;
  background: none; border: none; cursor: pointer;
  text-align: left; transition: background .1s;
}
.cb-slash-item:hover { background: var(--hover); }
.cb-slash-icon  { font-size: 18px; flex-shrink: 0; padding-top: 1px; }
.cb-slash-name  { font-size: 14px; font-weight: 600; color: var(--tx); }
.cb-slash-desc  { font-size: 12px; color: var(--muted); margin-top: 2px; line-height: 1.4; }
.cb-slash-empty { padding: 10px 14px; font-size: 13px; color: var(--muted); }

/* Slide-up transition for slash menu */
.fade-enter-active, .fade-leave-active { transition: opacity .12s, transform .12s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(4px); }

/* Upload error */
.cb-upload-err { flex: 1; font-size: 12.5px; color: var(--danger); }

/* Right controls */
.cb-controls { display: flex; align-items: center; gap: 2px; margin-left: auto; }

/* Model button */
.cb-model-wrap { position: relative; }
.cb-model-btn {
  display: flex; align-items: center; gap: 4px;
  background: none; border: none; cursor: pointer;
  font-size: 14px; font-weight: 500; color: var(--tx);
  padding: 5px 8px; border-radius: 8px;
  transition: background .13s; white-space: nowrap;
}
.cb-model-btn:hover { background: var(--hover); }
.cb-model-btn svg { color: var(--muted); flex-shrink: 0; }
.cb-model-locked { cursor: default; opacity: 0.6; }
.cb-model-locked:hover { background: none; }

/* Standalone Adaptive Thinking button */
.cb-adaptive-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 9px; border-radius: 8px; border: 1.5px solid var(--bdr);
  background: transparent; color: var(--muted); cursor: pointer;
  font-size: 12.5px; font-weight: 500;
  transition: all .15s;
}
.cb-adaptive-btn:hover { color: var(--tx); background: var(--hover); border-color: var(--ifocus); }
.cb-adaptive-btn.on      { color: var(--pri); border-color: var(--pri); background: var(--sbg); }
.cb-adaptive-btn.cb-adaptive-off { opacity: 0.35; cursor: not-allowed; }
.cb-adaptive-btn.cb-adaptive-off:hover { color: var(--muted); background: transparent; border-color: var(--bdr); }

/* Model dropdown */
.cb-model-dropdown {
  position: absolute; bottom: calc(100% + 8px); right: 0;
  width: 250px; background: var(--surf);
  border: 1px solid var(--bdr); border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,.12);
  z-index: 300; overflow: hidden;
}
.cbd-option {
  display: flex; flex-direction: column; gap: 2px;
  padding: 10px 14px; cursor: pointer; position: relative;
  transition: background .13s;
}
.cbd-option:hover { background: var(--hover); }
.cbd-option.selected { background: var(--sbg); }
.cbd-name { font-size: 13px; font-weight: 600; color: var(--tx); }
.cbd-desc { font-size: 11.5px; color: var(--muted); }
.cbd-check {
  position: absolute; right: 14px; top: 50%; transform: translateY(-50%);
  color: var(--pri); font-weight: 700; font-size: 14px;
}
.cbd-divider { height: 1px; background: var(--bdr); margin: 2px 0; }

/* Adaptive Thinking toggle row */
.cbd-toggle {
  width: 38px; height: 22px; border-radius: 11px;
  background: var(--bdr); flex-shrink: 0;
  position: relative; transition: background .2s;
}
.cbd-toggle.on { background: var(--pri); }
.cbd-toggle-knob {
  position: absolute; top: 3px; left: 3px;
  width: 16px; height: 16px; border-radius: 50%;
  background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.2);
  transition: transform .2s;
}
.cbd-toggle.on .cbd-toggle-knob { transform: translateX(16px); }

/* Send button */
.cb-send {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--tx); border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background .13s, opacity .13s; flex-shrink: 0;
}
.cb-send svg { stroke: var(--surf); }
.cb-send:hover:not(:disabled) { background: var(--pri); }
.cb-send:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
