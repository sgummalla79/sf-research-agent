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

        <Transition name="slide-up">
          <div v-if="paletteVisible" class="cp-palette-wrap cp-palette-centered">
            <SkillPalette
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
          placeholder="How can I help you today?"
          @submit="onSubmit"
          @upload="onUpload"
          @show-palette="showPalette"
          @hide-palette="hidePalette"
          @open-settings="openSettings('providers')"
          @skill-select="onSkillSelect"
        />
      </div>

      <!-- ── ACTIVE STATE — messages + bottom input ────────────────────────── -->
      <template v-else>

        <MessageList
          :messages="conv.messages"
          :is-streaming="conv.isStreaming"
          @open-document="openDoc"
        />

        <!-- Status banners -->
        <div v-if="conv.providerConflict" class="banner provider-conflict">
          <span class="pc-icon">⚠️</span>
          <span>{{ conv.providerConflict.detail }}</span>
          <div class="pc-actions">
            <button class="retry-btn" @click="goToProviders">Configure Providers</button>
            <button v-if="conv.providerConflict.canSmartPick" class="retry-btn smart-pick-btn"
              :disabled="conv.isStreaming" @click="smartPick">
              {{ conv.isStreaming ? 'Retrying…' : 'Use Smart Config' }}
            </button>
          </div>
        </div>
        <div v-if="conv.isHalted"       class="banner warn">⚠️ Session halted after maximum revisions.</div>
        <div v-if="conv.isInvalidInput" class="banner err">❌ Input doesn't appear to be architecture-related.</div>
        <div v-if="conv.error" class="banner err">
          <span>{{ conv.error }}</span>
          <button class="retry-btn" @click="conv.retryExecution">↺ Retry</button>
        </div>

        <!-- Bottom: interrupts + palette + input -->
        <div class="cp-bottom">
          <Transition name="slide-up">
            <ConfirmPanel
              v-if="conv.pendingConfirmation"
              :content="conv.pendingConfirmation"
              :is-streaming="conv.isStreaming"
              class="cp-interrupt"
              @confirm="conv.confirmUnderstanding"
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
                :skills="skills"
                :query="paletteQuery"
                @select="onSkillSelect"
                @dismiss="hidePalette"
              />
            </div>
          </Transition>

          <ChatInput
            v-if="!conv.isPipelineRunning"
            ref="chatInputRef"
            :chat-models="chatModels"
            :skills="skills"
            :is-pipeline-running="false"
            :is-streaming="conv.isStreaming"
            :no-providers="noProviders"
            placeholder="How can I help you today?"
            @submit="onSubmit"
            @upload="onUpload"
            @show-palette="showPalette"
            @hide-palette="hidePalette"
            @open-settings="openSettings('providers')"
            @skill-select="onSkillSelect"
            />
        </div>

      </template>
    </div>

    <!-- Document panel -->
    <DocumentPanel
      v-if="docPanel.open"
      :panel="docPanel"
      @close="closeDoc"
      @download-m-d="downloadMD"
      @download-p-d-f="() => downloadPDF(renderMd)"
    />

  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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

const conv    = useConversationStore()
const sidebar = useSidebarStore()
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
    { model: 'gemini-2.0-flash-001', display: 'Gemini 2.0 Flash', description: 'Fast multimodal' },
    { model: 'gemini-1.5-pro',       display: 'Gemini 1.5 Pro',   description: 'Advanced reasoning' },
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
    const res  = await apiFetch('/api/providers')
    const data = await res.json()
    const models = []

    for (const p of (data.providers || [])) {
      if (!p.connected) continue

      const list = p.available_models?.length
        ? p.available_models.map(m => ({ model: m, display: modelDisplay(m), description: modelDescription(m, p.id) }))
        : (PROVIDER_DEFAULTS[p.id] || [])

      for (const m of list) {
        models.push({ ...m, provider: p.id, default: models.length === 0 })
      }
    }

    chatModels.value = models
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

function renderMd(text) {
  try { return marked.parse(text) } catch { return text }
}

// ── Skill palette ──────────────────────────────────────────────────────────────
const paletteVisible = ref(false)
const paletteQuery   = ref('')
const chatInputRef   = ref(null)

function showPalette(query) { paletteQuery.value = query; paletteVisible.value = true }
function hidePalette()      { paletteVisible.value = false; paletteQuery.value = '' }

async function onSkillSelect(skillId) {
  hidePalette()
  chatInputRef.value?.clear()
  activeSkillId.value             = skillId

  conv.reset()
  sidebar.load()
  await conv.invokeSkill(skillId, '')
  sidebar.load()
}

// ── Chat input events ──────────────────────────────────────────────────────────
async function onSubmit(text, opts) {
  hidePalette()
  await conv.sendMessage(text, { chatProvider: opts.provider, chatModel: opts.model })
  sidebar.load()
}

async function onUpload(file, opts) {
  hidePalette()
  const skillId = skills.value[0]?.id
  if (!skillId) { conv.error = 'No skills installed. Go to Settings → Providers.'; return }
  activeSkillId.value             = skillId

  await conv.uploadAndInvoke(file, skillId, { chatProvider: opts.provider, chatModel: opts.model })
  sidebar.load()
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
  padding: 0 20px 80px;   /* shift slightly above true center */
  gap: 32px;
}
.cp-centered > :deep(.ci-outer) { width: 100%; max-width: 720px; }
.cp-palette-centered { width: 100%; max-width: 720px; }

.greeting-row  { display: flex; align-items: center; gap: 18px; }
.greeting-text {
  font-family: 'Martel', serif;
  font-size: clamp(28px, 3.5vw, 44px);
  font-weight: 400; color: var(--text);
  letter-spacing: -0.2px; margin: 0; line-height: 1.2;
}

/* ── Banners ── */
.banner {
  flex-shrink: 0; padding: 12px 28px; font-size: 13px; font-weight: 500;
  text-align: center; display: flex; align-items: center; justify-content: center; gap: 12px;
}
.banner-dismiss { background: none; border: none; cursor: pointer; font-size: 13px; opacity: .6; padding: 0; line-height: 1; color: inherit; flex-shrink: 0; }
.banner-dismiss:hover { opacity: 1; }
.retry-btn { padding: 5px 12px; border-radius: 8px; border: 1px solid currentColor; background: none; cursor: pointer; font-size: 12.5px; font-weight: 600; color: inherit; }
.smart-pick-btn { opacity: .85; }

.banner.ok   { background: #dcfce7; color: #166534; }
.banner.warn { background: #fef3c7; color: #92400e; }
.banner.err  { background: #fee2e2; color: #991b1b; }

html.dark .banner.ok   { background: #052e16; color: #86efac; }
html.dark .banner.warn { background: #1c1400; color: #fcd34d; }
html.dark .banner.err  { background: #1f0000; color: #fca5a5; }

.banner.provider-conflict {
  background: #fff7ed; color: #7c2d12;
  flex-direction: row; align-items: center; justify-content: flex-start;
  text-align: left; gap: 8px; padding: 10px 20px; flex-wrap: wrap;
}
html.dark .banner.provider-conflict { background: #1c0f00; color: #fdba74; }
.pc-icon { font-size: 16px; flex-shrink: 0; }
.pc-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-left: auto; }

/* ── Bottom ── */
.cp-bottom { flex-shrink: 0; display: flex; flex-direction: column; }
.cp-interrupt   { margin: 0 20px 8px; }
.cp-palette-wrap { position: relative; margin: 0 20px 6px; }

/* ── Transitions ── */
.slide-up-enter-active, .slide-up-leave-active { transition: opacity .15s, transform .15s; }
.slide-up-enter-from,   .slide-up-leave-to     { opacity: 0; transform: translateY(8px); }
</style>
