<!--
  ChatInput — molecule.

  Props:  chatModels, skills, isPipelineRunning, isStreaming, noProviders, placeholder
  Emits:  submit(text, opts), upload(file, opts), show-palette(query), hide-palette,
          open-settings, skill-select(skillId), manage-skills
  Exposes: clear()
-->
<template>
  <div class="ci-outer">
    <div class="chat-box" :class="{ 'drop-over': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop">

      <!-- No providers banner -->
      <div v-if="props.noProviders" class="cb-no-providers">
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

      <!-- Textarea -->
      <textarea ref="taEl" v-model="text" class="cb-ta"
        :placeholder="effectivePlaceholder"
        :disabled="props.noProviders || props.isPipelineRunning"
        rows="2"
        @input="handleInput"
        @keydown.enter.exact.prevent="canSend && handleSend()"
        @keydown.meta.enter.prevent="canSend && handleSend()"
        @keydown.ctrl.enter.prevent="canSend && handleSend()"
        @keydown.esc="$emit('hide-palette')" />

      <!-- Bottom bar -->
      <div class="cb-bar">

        <!-- + button -->
        <div class="cb-plus-wrap">
          <button class="cb-plus" :class="{ active: plusMenuOpen }"
            :disabled="props.isPipelineRunning"
            @click.stop="plusMenuOpen = !plusMenuOpen" title="Attach file">
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

            <!-- Skills — hover to open flyout submenu to the right -->
            <template v-if="props.skills.length">
              <div class="cpm-divider" />
              <div class="cpm-skills-wrap"
                @mouseenter="skillsOpen = true"
                @mouseleave="skillsOpen = false">
                <button class="cpm-item">
                  <svg class="cpm-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="16" height="16">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
                  </svg>
                  <span style="flex:1; text-align:left">Skills</span>
                  <svg class="cpm-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="11" height="11">
                    <polyline points="9 18 15 12 9 6"/>
                  </svg>
                </button>

                <!-- Flyout submenu — appears to the right -->
                <div v-if="skillsOpen" class="cpm-flyout">
                  <button v-for="skill in props.skills" :key="skill.id"
                    class="cpm-item"
                    @click="$emit('skill-select', skill.id); plusMenuOpen = false; skillsOpen = false">
                    <span class="cpm-skill-icon">{{ skill.icon || '⚡' }}</span>
                    {{ skill.name }}
                  </button>
                  <div class="cpm-divider" />
                  <button class="cpm-item cpm-manage"
                    @click="app.openConfiguration(); plusMenuOpen = false; skillsOpen = false">
                    <svg class="cpm-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="16" height="16">
                      <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>
                    </svg>
                    Manage skills
                  </button>
                </div>
              </div>
            </template>
          </div>
        </div>

        <div v-if="uploadError" class="cb-upload-err">{{ uploadError }}</div>

        <!-- Right controls -->
        <div class="cb-controls">

          <!-- Model picker -->
          <div v-if="!props.isPipelineRunning && props.chatModels.length" class="cb-model-wrap">
            <button class="cb-model-btn" @click.stop="modelPickerOpen = !modelPickerOpen">
              {{ selectedModel.display }}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="10" height="10">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </button>
            <FlyoutMenu
              :groups="modelGroups"
              :open="modelPickerOpen"
              :direction="props.isEmptyChat ? 'below' : 'above'"
              @select="m => { selectedModel = m }"
              @close="modelPickerOpen = false"
            />
          </div>

          <!-- Adaptive Thinking — hidden while pipeline is running -->
          <button v-if="!props.isPipelineRunning && props.chatModels.length"
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

          <!-- Send -->
          <button class="cb-send" :disabled="!canSend" @click="handleSend">
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
import { useAppStore }  from '../../stores/app'
import FlyoutMenu       from '../ui/FlyoutMenu.vue'

const props = defineProps({
  chatModels:        { type: Array,   default: () => [] },
  skills:            { type: Array,   default: () => [] },
  isPipelineRunning: { type: Boolean, default: false },
  isStreaming:       { type: Boolean, default: false },
  noProviders:       { type: Boolean, default: false },
  isEmptyChat:       { type: Boolean, default: false },
  placeholder:       { type: String,  default: 'Message or type / to use a skill…' },
})

const emit = defineEmits(['submit', 'upload', 'show-palette', 'hide-palette', 'open-settings', 'skill-select'])
const app  = useAppStore()

// ── State ─────────────────────────────────────────────────────────────────────
const text                  = ref('')
const selectedModel         = ref({ model: 'claude-sonnet-4-6', display: 'Sonnet 4.6', description: 'Responsive everyday work', provider: 'anthropic' })
const extendedThinking      = ref(true)
const plusMenuOpen          = ref(false)
const skillsOpen            = ref(false)
const modelPickerOpen       = ref(false)
const PROVIDER_LABELS = { anthropic: 'Anthropic', openai: 'OpenAI', google: 'Google', perplexity: 'Perplexity', groq: 'Groq', mistral: 'Mistral' }

const modelGroups = computed(() => {
  const map = {}
  for (const m of props.chatModels) {
    const p = m.provider || 'other'
    if (!map[p]) map[p] = { key: p, label: PROVIDER_LABELS[p] || p, items: [] }
    map[p].items.push({ label: m.display, value: m, selected: selectedModel.value.model === m.model })
  }
  return Object.values(map)
})
const selectedFile     = ref(null)
const imagePreviewUrl  = ref(null)
const isDragging       = ref(false)
const uploadError      = ref(null)
const fileInputEl      = ref(null)
const taEl             = ref(null)

const effectivePlaceholder = computed(() => {
  if (props.noProviders)       return ''
  if (props.isPipelineRunning) return 'Skill running…'
  return props.placeholder
})

const canSend = computed(() =>
  !props.isPipelineRunning &&
  !props.isStreaming &&
  !props.noProviders &&
  (!!selectedFile.value || !!text.value.trim())
)

// Sync default model when chatModels arrive (async from parent)
watch(() => props.chatModels, (models) => {
  if (!models.length) return
  const def = models.find(m => m.default) || models[0]
  if (def) selectedModel.value = def
}, { immediate: true })

// Keep Adaptive Thinking in sync with chosen provider
watch(() => selectedModel.value.provider, (provider) => {
  extendedThinking.value = provider === 'anthropic'
}, { immediate: true })

// ── Slash command — delegate palette to parent ────────────────────────────────
function handleInput() {
  if (text.value.startsWith('/')) {
    emit('show-palette', text.value.slice(1))
  } else {
    emit('hide-palette')
  }
}

// Parent calls this after a skill is selected from the palette
function clear() {
  text.value         = ''
  selectedFile.value = null
  if (imagePreviewUrl.value) URL.revokeObjectURL(imagePreviewUrl.value)
  imagePreviewUrl.value = null
  uploadError.value     = null
  emit('hide-palette')
  taEl.value?.focus()
}

defineExpose({ clear })

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
  uploadError.value     = null
  imagePreviewUrl.value = null
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!ALL_EXTS.includes(ext)) { uploadError.value = 'Unsupported file type.'; return }
  if (file.size > MAX_MB * 1048576) { uploadError.value = `Max ${MAX_MB} MB.`; return }
  selectedFile.value = file
  if (IMG_EXTS.has(ext)) imagePreviewUrl.value = URL.createObjectURL(file)
}

function onFileChange(e) { const f = e.target.files?.[0]; if (f) setFile(f) }
function onDrop(e)       { isDragging.value = false; const f = e.dataTransfer?.files?.[0]; if (f) setFile(f) }

// ── Submit ────────────────────────────────────────────────────────────────────
const opts = () => ({
  model:            selectedModel.value.model,
  provider:         selectedModel.value.provider || 'anthropic',
  extendedThinking: extendedThinking.value,
})

function handleSend() {
  if (!canSend.value) return
  if (selectedFile.value) {
    emit('upload', selectedFile.value, opts())
    clearFile()
    return
  }
  const msg = text.value.trim()
  if (!msg) return
  emit('submit', msg, opts())
  text.value = ''
}

// ── Close popups on outside click ─────────────────────────────────────────────
function closeMenus() { plusMenuOpen.value = false; skillsOpen.value = false; modelPickerOpen.value = false }
onMounted(()   => document.addEventListener('click', closeMenus))
onUnmounted(() => document.removeEventListener('click', closeMenus))
</script>

<style scoped>
.ci-outer { flex-shrink: 0; padding: 10px 20px 16px; background: var(--bg); }

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

.cb-no-providers {
  padding: 8px 10px;
  font-size: 12.5px; font-weight: 500;
  color: #fff; background: #7f1d1d;
  border-radius: 8px; margin-bottom: 6px;
}
.cb-np-link {
  background: none; border: none; cursor: pointer;
  font-size: 12.5px; font-weight: 700; color: #fff;
  padding: 0; text-decoration: underline; text-underline-offset: 2px;
}

.cb-file-row { display: flex; }
.cb-file-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px 4px 8px; border-radius: 8px;
  background: var(--sbg); border: 1px solid var(--sbdr);
  color: var(--stx); font-size: 12.5px; font-weight: 500; max-width: 320px;
}
.cb-file-icon  { flex-shrink: 0; }
.cb-file-chip span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cb-file-rm {
  background: none; border: none; cursor: pointer;
  color: var(--muted); padding: 0 0 0 4px; font-size: 13px; line-height: 1;
}
.cb-file-rm:hover { color: var(--tx); }

.cb-ta {
  width: 100%; box-sizing: border-box;
  background: transparent; border: none; outline: none; resize: none;
  font-size: 15px; font-family: inherit; color: var(--tx); line-height: 1.55;
  padding: 2px; min-height: 44px; max-height: 220px;
}
.cb-ta::placeholder { color: var(--muted); }
.cb-ta:disabled { opacity: 0.4; cursor: not-allowed; }

.cb-bar { display: flex; align-items: center; gap: 6px; }

.cb-plus-wrap { position: relative; flex-shrink: 0; }
.cb-plus {
  width: 32px; height: 32px; border-radius: 8px;
  border: 1px solid var(--bdr); background: transparent;
  color: var(--muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background .13s, color .13s, border-color .13s;
}
.cb-plus:hover, .cb-plus.active { background: var(--hover); color: var(--tx); border-color: var(--ifocus); }
.cb-plus:disabled { opacity: 0.3; cursor: not-allowed; }

.cb-plus-menu {
  position: absolute; bottom: calc(100% + 8px); left: 0;
  width: 220px; background: var(--surf);
  border: 1px solid var(--bdr); border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,.14);
  z-index: 300; padding: 4px 0;
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
.cpm-skill-icon { font-size: 15px; flex-shrink: 0; }
.cpm-manage { color: var(--muted); }
.cpm-divider { height: 1px; background: var(--bdr, var(--border)); margin: 4px 0; }
.cpm-chevron { flex-shrink: 0; color: var(--muted); }

/* Skills flyout */
.cpm-skills-wrap {
  position: relative;
}
.cpm-skills-wrap > .cpm-item {
  width: 100%;
}

/* Flyout panel — sits flush against the right edge, no gap */
.cpm-flyout {
  position: absolute;
  left: 100%;
  top: 0;
  margin-left: -2px;   /* overlap by 2px to remove any gap */
  width: 220px;
  background: var(--surf, var(--surface));
  border: 1px solid var(--bdr, var(--border));
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,.18);
  z-index: 400;
  padding: 4px 0;
}

.cb-upload-err { flex: 1; font-size: 12.5px; color: var(--danger); }

.cb-controls { display: flex; align-items: center; gap: 8px; margin-left: auto; }

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


.cb-adaptive-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 9px; border-radius: 8px; border: 1.5px solid var(--bdr);
  background: transparent; color: var(--muted); cursor: pointer;
  font-size: 12.5px; font-weight: 500; transition: all .15s;
}
.cb-adaptive-btn:hover { color: var(--tx); background: var(--hover); border-color: var(--ifocus); }
.cb-adaptive-btn.on    { color: var(--pri); border-color: var(--pri); background: var(--sbg); }
.cb-adaptive-btn.cb-adaptive-off { opacity: 0.35; cursor: not-allowed; }
.cb-adaptive-btn.cb-adaptive-off:hover { color: var(--muted); background: transparent; border-color: var(--bdr); }

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
