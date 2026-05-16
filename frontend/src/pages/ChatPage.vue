<!--
  ChatPage — Container page. Reads both Pinia stores, wires all events.
-->
<template>
  <AppLayout :active-conversation-id="conv.conversationId">

    <div class="chat-page">

      <!-- ── Progress strip (animates while a stage is running) ────────────── -->
      <div class="progress-strip" :class="[conv.currentStage, { visible: !!conv.currentStage }]">
        <span class="p-dot" />
        <span class="p-text">{{ stageLabels[conv.currentStage] }} is working…</span>
      </div>

      <!-- ── Active skill bar ──────────────────────────────────────────────── -->
      <div v-if="conv.isPipelineRunning && activeSkill" class="session-flow-bar">
        <span class="sfb-icon">{{ activeSkill.icon }}</span>
        <span class="sfb-name">{{ activeSkill.name }}</span>
        <span class="sfb-label">active</span>
      </div>

      <!-- ── EMPTY STATE — greeting + input centered together ───────────────── -->
      <div v-if="isEmpty" class="cp-centered">
        <div class="greeting-row">
          <SudarshanChakra :size="48" color="var(--pri)" />
          <h1 class="greeting-text">{{ greeting }}{{ firstName ? ', ' + firstName : '' }}</h1>
        </div>

        <!-- Input group: palette + input flush together -->
        <div class="cp-input-group">
          <Transition name="slide-up">
            <div v-if="paletteVisible" class="cp-palette-wrap">
              <SkillPalette
                ref="skillPaletteRef"
                :skills="skills"
                :query="paletteQuery"
                @select="onSkillSelect"
                @dismiss="hidePalette"
              />
            </div>
          </Transition>

          <ChatInput
            ref="chatInputRef"
            :chat-models="chatModels"
            :skills="skills"
            :is-pipeline-running="false"
            :is-streaming="conv.isStreaming"
            :no-providers="noProviders"
            :is-empty-chat="true"
            :palette-open="paletteVisible"
            placeholder="How can I help you today?"
            @submit="onSubmit"
            @upload="onUpload"
            @show-palette="showPalette"
            @hide-palette="hidePalette"
            @open-settings="openSettings('providers')"
            @skill-select="onSkillSelect"
            @palette-move="onPaletteMove"
            @palette-confirm="onPaletteConfirm"
            @palette-space="onPaletteSpace"
          />
        </div>
      </div>

      <!-- ── ACTIVE STATE — messages + bottom input ────────────────────────── -->
      <template v-else>

        <MessageList
          :messages="conv.messages"
          :is-streaming="conv.isStreaming"
          @open-document="openDoc"
        />

        <!-- Bottom: interrupts + palette + input + inline notices -->
        <div class="cp-bottom">
          <Transition name="slide-up">
            <ConfirmPanel
              v-if="conv.pendingConfirmation"
              :content="conv.pendingConfirmation"
              :is-streaming="conv.isStreaming"
              :error="confirmError"
              class="cp-interrupt"
              @confirm="onConfirmUnderstanding"
            />
          </Transition>

          <Transition name="slide-up">
            <DiscoveryForm
              v-if="conv.pendingQuestions.length && !conv.isInvalidInput"
              :questions="conv.pendingQuestions"
              :is-streaming="conv.isStreaming"
              class="cp-interrupt"
              @submit="conv.sendReply"
            />
          </Transition>

          <Transition name="slide-up">
            <div v-if="paletteVisible" class="cp-palette-wrap">
              <SkillPalette
                ref="skillPaletteRef"
                :skills="skills"
                :query="paletteQuery"
                @select="onSkillSelect"
                @dismiss="hidePalette"
              />
            </div>
          </Transition>

          <!-- Inline notices — sit flush above the input -->
          <div v-if="conv.providerConflict" class="cp-notice cp-notice-warn">
            <svg class="cp-notice-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span>{{ conv.providerConflict.detail }}</span>
            <div class="cp-notice-actions">
              <button class="cp-notice-btn" @click="goToProviders">Configure Providers</button>
              <button v-if="conv.providerConflict.canSmartPick && conv.executionId" class="cp-notice-btn cp-notice-btn-pri"
                :disabled="conv.isStreaming" @click="smartPick">
                {{ conv.isStreaming ? 'Retrying…' : 'Use Smart Config' }}
              </button>
            </div>
          </div>
          <div v-if="conv.isHalted" class="cp-notice cp-notice-warn">
            <svg class="cp-notice-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span>Session halted after maximum revisions.</span>
          </div>
          <div v-if="conv.isInvalidInput" class="cp-notice cp-notice-err">
            <svg class="cp-notice-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
            <span>Input doesn't appear to be architecture-related.</span>
          </div>
          <div v-if="conv.error" class="cp-notice cp-notice-err">
            <svg class="cp-notice-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <span>{{ conv.error }}</span>
            <div v-if="conv.executionId" class="cp-notice-actions">
              <button class="cp-notice-btn" @click="conv.retryExecution">↺ Retry</button>
            </div>
          </div>

          <ChatInput
            v-if="!conv.isPipelineRunning"
            ref="chatInputRef"
            :chat-models="chatModels"
            :skills="skills"
            :is-pipeline-running="false"
            :is-streaming="conv.isStreaming"
            :no-providers="noProviders"
            :palette-open="paletteVisible"
            placeholder="How can I help you today?"
            @submit="onSubmit"
            @upload="onUpload"
            @show-palette="showPalette"
            @hide-palette="hidePalette"
            @open-settings="openSettings('providers')"
            @skill-select="onSkillSelect"
            @palette-move="onPaletteMove"
            @palette-confirm="onPaletteConfirm"
            @palette-space="onPaletteSpace"
            />
        </div>

        <!-- Token usage bar — below input, always visible once messages exist -->
        <StatusBar v-if="conv.messages.length" justify="end">
          <template v-for="row in conv.sessionUsage.breakdown" :key="row.model">
            <div class="ub-cell">
              <span class="ub-name">{{ row.model }}</span>
              <span class="ub-tokens">↑ {{ fmtTokens(row.input_tokens) }} &nbsp;↓ {{ fmtTokens(row.output_tokens) }}</span>
              <span class="ub-cost">{{ fmtCost(row.cost_usd) }}</span>
            </div>
            <div class="ub-sep" />
          </template>
          <div class="ub-cell">
            <span class="ub-name">Session</span>
            <span class="ub-tokens">↑ {{ fmtTokens(conv.sessionUsage.input_tokens) }} &nbsp;↓ {{ fmtTokens(conv.sessionUsage.output_tokens) }}</span>
            <span class="ub-cost">{{ fmtCost(conv.sessionUsage.cost_usd) }}</span>
          </div>
        </StatusBar>

      </template>
    </div>

    <!-- Document panel -->
    <DocumentPanel
      v-if="docPanel.open"
      :panel="docPanel"
      :close="closeDoc"
      :download-m-d="downloadMD"
      :download-p-d-f="downloadPDF"
    />

  </AppLayout>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useProvidersStore } from '../stores/providers'
import { marked } from 'marked'

import { useConversationStore } from '../stores/conversation'
import { useSidebarStore }      from '../stores/sidebar'
import { useDocumentPanel }     from '../composables/useDocumentPanel'
import { useTheme }             from '../composables/useTheme'
import { useDarkMode }          from '../composables/useDarkMode'
import { useAuth }              from '../composables/useAuth'
import { apiFetch }             from '../composables/useFetch'
import { useAppStore }          from '../stores/app'

import AppLayout        from '../components/AppLayout.vue'
import MessageList      from '../components/chat/MessageList.vue'
import ConfirmPanel     from '../components/chat/ConfirmPanel.vue'
import DiscoveryForm    from '../components/chat/DiscoveryForm.vue'
import SkillPalette     from '../components/skill/SkillPalette.vue'
import ChatInput        from '../components/chat/ChatInput.vue'
import DocumentPanel    from '../components/document/DocumentPanel.vue'
import SudarshanChakra  from '../components/SudarshanChakra.vue'
import StatusBar        from '../components/ui/StatusBar.vue'

const conv      = useConversationStore()
const sidebar   = useSidebarStore()
const provStore = useProvidersStore()

watch(() => provStore.version, () => loadChatModels())
const { user } = useAuth()

const { panel: docPanel, open: openDoc, close: closeDoc, downloadMD, downloadPDF } = useDocumentPanel()
const app = useAppStore()
const openSettings      = (tab) => app.openSettings(tab)
const openConfiguration = ()    => app.openConfiguration()

// ── Stage labels ───────────────────────────────────────────────────────────────
const stageLabels = {
  intake:    'Intake Agent',
  discovery: 'Discovery Agent',
  research:  'Research Agent',
  review:    'Review Agent',
  approval:  'Approver Gate',
}

// ── Greeting ───────────────────────────────────────────────────────────────────
const _GREETINGS = {
  morning: [
    'Good morning',
    'Suprabhat',           // Sanskrit / Hindi
    'Bonjour',             // French
    'Buenos días',         // Spanish
    'Guten Morgen',        // German
    'Buongiorno',          // Italian
    'Bom dia',             // Portuguese
    'Günaydın',            // Turkish
    'Kalimera',            // Greek
    'Ohayou gozaimasu',    // Japanese
    'Subah bakhair',       // Urdu
    'Sabah alkhayr',       // Arabic
    'Dobroe utro',         // Russian
    'Selamat pagi',        // Malay/Indonesian
  ],
  afternoon: [
    'Good afternoon',
    'Shubh dopahar',       // Hindi
    'Bon après-midi',      // French
    'Buenas tardes',       // Spanish
    'Guten Nachmittag',    // German
    'Buon pomeriggio',     // Italian
    'Boa tarde',           // Portuguese
    'İyi öğleden sonralar', // Turkish
    'Konnichiwa',          // Japanese
    'Masa alkhayr',        // Arabic
    'Selamat siang',       // Malay
  ],
  evening: [
    'Good evening',
    'Shubh sandhya',       // Sanskrit
    'Bonsoir',             // French
    'Buenas noches',       // Spanish
    'Guten Abend',         // German
    'Buona sera',          // Italian
    'Boa noite',           // Portuguese
    'İyi akşamlar',        // Turkish
    'Konbanwa',            // Japanese
    'Masa alkhayr',        // Arabic
    'Selamat malam',       // Malay
  ],
}

const greeting = computed(() => {
  const h      = new Date().getHours()
  const bucket = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening'
  const list   = _GREETINGS[bucket]
  return list[Math.floor(Math.random() * list.length)]
})

const firstName = computed(() => {
  const name = user.value?.name || ''
  if (!name || name.includes('@')) return ''
  return name.split(/\s+/)[0]
})

// ── Skills + models ────────────────────────────────────────────────────────────
const skills        = ref([])
const chatModels    = ref([])
const modelsLoaded  = ref(false)
const noProviders   = computed(() => modelsLoaded.value && chatModels.value.length === 0)

// The skill currently being run (for the session flow bar)
const activeSkillId = ref(null)
const activeSkill   = computed(() => skills.value.find(s => s.id === activeSkillId.value) ?? null)

// Empty = no messages and not mid-pipeline
const isEmpty = computed(() =>
  !conv.messages.length && !conv.isStreaming && !conv.isPipelineRunning
)

async function loadSkills() {
  try {
    const res  = await apiFetch('/api/skills')
    const data = await res.json()
    skills.value = (data.skills || []).filter(s => s.installed)
  } catch (_) {}
}

// Fallback models shown when a provider is connected but hasn't been refreshed yet
const PROVIDER_DEFAULTS = {
  anthropic:  [
    { model: 'claude-sonnet-4-6', display: 'Sonnet 4.6', description: 'Balanced performance' },
    { model: 'claude-opus-4-7',   display: 'Opus 4.7',   description: 'Most powerful' },
    { model: 'claude-haiku-4-5-20251001', display: 'Haiku 4.5', description: 'Fast and lightweight' },
  ],
  openai:     [
    { model: 'gpt-4o',      display: 'GPT-4o',      description: 'Advanced reasoning' },
    { model: 'gpt-4o-mini', display: 'GPT-4o Mini', description: 'Fast and affordable' },
  ],
  google:     [
    { model: 'gemini-1.5-pro',   display: 'Gemini 1.5 Pro',   description: 'Advanced reasoning' },
    { model: 'gemini-1.5-flash', display: 'Gemini 1.5 Flash', description: 'Fast and efficient' },
  ],
  perplexity: [
    { model: 'sonar-pro', display: 'Sonar Pro', description: 'Web-grounded search' },
  ],
  groq: [
    { model: 'llama-3.3-70b-versatile', display: 'Llama 3.3 70B', description: 'Fast inference' },
  ],
}

async function loadChatModels() {
  try {
    const res  = await apiFetch('/api/models/active')
    if (!res.ok) return
    const data   = await res.json()
    chatModels.value = (data.models || []).map((m, i) => ({
      model:       m.model_id,
      display:     m.display_name,
      description: '',
      provider:    m.provider,
      default:     i === 0,
    }))
  } catch (_) {
  } finally {
    modelsLoaded.value = true
  }
}

function modelDisplay(modelId) {
  const map = {
    'claude-opus-4-7':             'Opus 4.7',
    'claude-sonnet-4-6':           'Sonnet 4.6',
    'claude-haiku-4-5-20251001':   'Haiku 4.5',
    'gpt-4o':                      'GPT-4o',
    'gpt-4o-mini':                 'GPT-4o Mini',
    'gemini-2.0-flash-001':        'Gemini 2.0 Flash',
    'gemini-1.5-pro':              'Gemini 1.5 Pro',
  }
  return map[modelId] || modelId
}

function modelDescription(modelId, provider) {
  if (provider === 'anthropic') {
    if (modelId.includes('opus'))   return 'Most powerful Claude model'
    if (modelId.includes('sonnet')) return 'Balanced performance'
    if (modelId.includes('haiku'))  return 'Fast and lightweight'
  }
  if (provider === 'openai') {
    if (modelId.includes('mini')) return 'Fast and affordable'
    return 'Advanced reasoning'
  }
  return ''
}

function fmtTokens(n) { return n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n) }
function fmtCost(c)   { return c < 0.01  ? `$${c.toFixed(6)}`           : `$${c.toFixed(5)}` }

function renderMd(text) {
  try { return marked.parse(text) } catch { return text }
}

// ── Skill palette ──────────────────────────────────────────────────────────────
const paletteVisible  = ref(false)
const paletteQuery    = ref('')
const skillPaletteRef = ref(null)

// Auto-close palette when query matches no skills
watch(paletteQuery, (q) => {
  if (!paletteVisible.value) return
  const matched = skills.value.filter(s =>
    !q || s.name.toLowerCase().includes(q.toLowerCase()) || s.id.toLowerCase().includes(q.toLowerCase())
  )
  if (matched.length === 0) hidePalette()
})
const chatInputRef   = ref(null)

function showPalette(query) { paletteQuery.value = query; paletteVisible.value = true }
function hidePalette()      { paletteVisible.value = false; paletteQuery.value = '' }

function onPaletteMove(dir) {
  if (dir === 'down') skillPaletteRef.value?.navigateDown()
  else                skillPaletteRef.value?.navigateUp()
}

function onPaletteConfirm() {
  skillPaletteRef.value?.selectActive()
}

function onPaletteSpace(command) {
  const filtered = skillPaletteRef.value?.filtered ?? []
  if (filtered.length === 1) {
    hidePalette()
    chatInputRef.value?.setSkill(filtered[0].id)
  } else {
    hidePalette()
  }
}

function onSkillSelect(skillId) {
  hidePalette()
  chatInputRef.value?.setSkill(skillId)
}

// ── Skill token parsing ────────────────────────────────────────────────────────
const pendingSkillSelection = ref(null) // { skills, brief } when multiple skills found

function parseSkillTokens(text) {
  const matches = [...text.matchAll(/\/(\w[\w-]*)/g)]
  const found   = matches
    .map(m => skills.value.find(s => s.id === m[1].toLowerCase()))
    .filter(Boolean)
  return [...new Map(found.map(s => [s.id, s])).values()]  // distinct by id
}

function buildBrief(text) {
  return text.replace(/\/\w[\w-]*/g, '').replace(/\s+/g, ' ').trim()
}

async function runSkill(skillId, originalText, brief, opts) {
  // Only validate when the user actually provided a brief — if empty, the
  // pipeline will ask for one via confirm_understanding interrupt.
  if (brief.trim()) {
    try {
      const vRes = await apiFetch(`/api/skills/${skillId}/validate-brief`, {
        method: 'POST',
        body:   JSON.stringify({ brief }),
      })
      if (vRes.ok) {
        const { valid, message } = await vRes.json()
        if (!valid) {
          conv.addLocalMessage('user', originalText)
          conv.addLocalMessage('agent', message)
          chatInputRef.value?.setText(originalText)
          return
        }
      }
    } catch (_) {
      // Network error — proceed and let the pipeline handle it
    }
  }

  briefWasEmpty.value = !brief.trim()
  activeSkillId.value = skillId
  conv.reset()
  sidebar.load()
  await conv.invokeSkill(skillId, brief, {
    chatProvider:    opts.provider,
    chatModel:       opts.model,
    originalMessage: originalText,
  })
  sidebar.load()
}

// ── Chat input events ──────────────────────────────────────────────────────────
async function onSubmit(text, opts) {
  hidePalette()

  // Resolve pending multi-skill selection
  if (pendingSkillSelection.value) {
    await resolvePendingSelection(text, opts)
    return
  }

  const foundSkills = parseSkillTokens(text)

  if (foundSkills.length === 1) {
    await runSkill(foundSkills[0].id, text, buildBrief(text), opts)
  } else if (foundSkills.length > 1) {
    await promptSkillSelection(foundSkills, text, opts)
  } else {
    await conv.sendMessage(text, { chatProvider: opts.provider, chatModel: opts.model })
    sidebar.load()
  }
}

async function promptSkillSelection(foundSkills, originalText, opts) {
  const brief = buildBrief(originalText)
  // Add user message and assistant prompt locally
  conv.addLocalMessage('user', originalText)
  const skillLines = foundSkills.map((s, i) =>
    `**${i + 1}. /${s.id}** — ${s.name}\n${s.description || ''}`
  ).join('\n\n')
  conv.addLocalMessage('agent',
    `I found ${foundSkills.length} skills in your message:\n\n${skillLines}\n\nWhich one would you like to run? (or say "none" to just chat)`
  )
  pendingSkillSelection.value = { skills: foundSkills, brief, originalText }
}

async function resolvePendingSelection(text, opts) {
  const { skills: pendingSkills, brief, originalText } = pendingSkillSelection.value
  pendingSkillSelection.value = null

  const res  = await apiFetch('/api/skills/classify-choice', {
    method: 'POST',
    body:   JSON.stringify({
      response: text,
      skills:   pendingSkills.map(s => ({ id: s.id, name: s.name, description: s.description || '' })),
    }),
  })
  const { skill_id } = await res.json()

  conv.addLocalMessage('user', text)

  if (skill_id && skill_id !== 'none') {
    await runSkill(skill_id, originalText, brief, opts)
  } else {
    await conv.sendMessage(text, { chatProvider: opts.provider, chatModel: opts.model })
    sidebar.load()
  }
}

async function onUpload(file, opts) {
  hidePalette()
  const skillId = skills.value[0]?.id
  if (!skillId) { conv.error = 'No skills installed. Go to Settings → Providers.'; return }
  activeSkillId.value             = skillId

  await conv.uploadAndInvoke(file, skillId, { chatProvider: opts.provider, chatModel: opts.model })
  sidebar.load()
}

// ── Confirm understanding ──────────────────────────────────────────────────────
const confirmError      = ref('')
const briefWasEmpty     = ref(false)   // true when skill was invoked with no brief

async function onConfirmUnderstanding(correction) {
  confirmError.value = ''

  // When brief was empty the correction field IS the brief — require it
  if (briefWasEmpty.value && !correction.trim()) {
    confirmError.value = 'Please describe the project you\'d like to architect.'
    return
  }

  const textToValidate = correction.trim()
  if (textToValidate && activeSkillId.value) {
    try {
      const vRes = await apiFetch(`/api/skills/${activeSkillId.value}/validate-brief`, {
        method: 'POST',
        body:   JSON.stringify({ brief: textToValidate }),
      })
      if (vRes.ok) {
        const { valid, message } = await vRes.json()
        if (!valid) {
          confirmError.value = message
          return
        }
      }
    } catch (_) {}
  }

  briefWasEmpty.value = false
  conv.confirmUnderstanding(correction)
}

// ── Provider conflict ──────────────────────────────────────────────────────────
async function smartPick() {
  conv.providerConflict = null
  await conv.retryExecution()
}

function goToProviders() {
  conv.providerConflict = null
  openSettings('providers')
}

// ── Init ───────────────────────────────────────────────────────────────────────
onMounted(async () => {
  const { loadTheme } = useTheme()
  const { isDark }    = useDarkMode()
  await Promise.all([
    loadTheme(isDark.value),
    sidebar.load(),
    loadSkills(),
    loadChatModels(),
  ])
})
</script>

<style scoped>
.chat-page {
  flex: 1; display: flex; flex-direction: column;
  background: var(--bg); min-width: 0; overflow: hidden;
}

/* ── Progress strip ── */
.progress-strip {
  position: relative; flex-shrink: 0; height: 0; overflow: hidden; opacity: 0;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: height .2s ease, opacity .2s ease;
}
.progress-strip.visible { height: 32px; opacity: 1; }
.progress-strip.intake,
.progress-strip.discovery,
.progress-strip.research,
.progress-strip.review,
.progress-strip.approval { background: rgba(255,208,128,0.07); }
.progress-strip::after {
  content: ''; position: absolute; top: 0; bottom: 0; width: 55%;
  animation: p-sweep 3.5s linear infinite;
  background: linear-gradient(90deg, transparent, rgba(255,208,128,0.45), transparent);
}
@keyframes p-sweep { 0% { left: -55%; } 100% { left: 100%; } }
.p-dot {
  position: relative; z-index: 1;
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
  background: var(--pri);
  animation: p-pulse 2s ease-in-out infinite;
}
@keyframes p-pulse { 0%,100% { opacity:1; transform:scale(1) } 50% { opacity:.35; transform:scale(.75) } }
.p-text { position: relative; z-index: 1; font-size: 12px; font-weight: 500; letter-spacing: .02em; white-space: nowrap; color: var(--pri); }

/* ── Session flow bar ── */
.session-flow-bar {
  flex-shrink: 0; display: flex; align-items: center; gap: 6px;
  padding: 5px 20px; background: var(--sbg);
  border-bottom: 1px solid var(--sbdr);
  font-size: 12.5px; font-weight: 500; color: var(--stx);
}
.sfb-icon  { font-size: 14px; }
.sfb-name  { font-weight: 600; }
.sfb-label {
  margin-left: 2px; font-size: 10.5px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .06em;
  padding: 1px 6px; border-radius: 10px;
  background: var(--sbdr); color: var(--stx); opacity: 0.8;
}

/* ── Centered empty state (greeting + input together) ── */
.cp-centered {
  flex: 1;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 0 20px 80px;
  gap: 32px;
}

/* Input group: palette floats above input as overlay */
.cp-input-group {
  width: 100%; max-width: 720px;
  position: relative;
}

.greeting-row  { display: flex; align-items: center; gap: 18px; }
.greeting-text {
  font-family: 'Martel', serif;
  font-size: clamp(28px, 3.5vw, 44px);
  font-weight: 400; color: var(--text);
  letter-spacing: -0.2px; margin: 0; line-height: 1.2;
}

/* ── Inline notices (sit above ChatInput inside cp-bottom) ── */
.cp-notice {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 20px; font-size: 13px; font-weight: 500;
  border-radius: 10px; margin: 0 20px 4px;
}
.cp-notice > span { flex: 1; min-width: 0; }
.cp-notice-icon { width: 16px; height: 16px; flex-shrink: 0; }
.cp-notice-warn {
  background: rgba(251,191,36,.12); color: #92400e;
  border: 1px solid rgba(251,191,36,.3);
}
.cp-notice-err {
  background: rgba(239,68,68,.08); color: #991b1b;
  border: 1px solid rgba(239,68,68,.25);
}
html.dark .cp-notice-warn { background: rgba(251,191,36,.08); color: #fcd34d; border-color: rgba(251,191,36,.2); }
html.dark .cp-notice-err  { background: rgba(239,68,68,.08); color: #fca5a5; border-color: rgba(239,68,68,.2); }

.cp-notice-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-left: auto; }
.cp-notice-btn {
  padding: 4px 12px; border-radius: 7px;
  border: 1px solid currentColor; background: none;
  cursor: pointer; font-size: 12px; font-weight: 600; color: inherit;
  white-space: nowrap;
}
.cp-notice-btn:hover { background: rgba(0,0,0,.06); }
.cp-notice-btn-pri { background: currentColor; }
.cp-notice-btn-pri span, .cp-notice-btn-pri { color: var(--bg); }

.ub-cell {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 2px; padding: 6px 20px;
}
.ub-sep    { width: 1px; background: var(--border); flex-shrink: 0; margin: 6px 0; }
.ub-name   { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); white-space: nowrap; }
.ub-tokens { font-size: 11.5px; font-weight: 500; color: var(--text); white-space: nowrap; }
.ub-cost   { font-size: 11.5px; font-weight: 600; color: var(--pri); white-space: nowrap; }

/* ── Bottom ── */
.cp-bottom {
  flex-shrink: 0;
  display: flex; flex-direction: column;
  max-width: 720px; width: 100%; margin: 0 auto;
  position: relative;
}
.cp-interrupt    { margin: 0 0 8px; }

/* Palette floats above input — left edge aligns with chat box (ci-outer has 20px padding) */
.cp-palette-wrap {
  position: absolute; bottom: calc(100% + 4px); left: 20px;
  z-index: 500;
}

/* ── Transitions ── */
.slide-up-enter-active, .slide-up-leave-active { transition: opacity .15s, transform .15s; }
.slide-up-enter-from,   .slide-up-leave-to     { opacity: 0; transform: translateY(8px); }
</style>
