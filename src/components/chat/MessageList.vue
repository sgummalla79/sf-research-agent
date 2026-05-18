<!-- Scrollable message list — purely presentational -->
<template>
  <div class="message-list" ref="listEl">
    <div class="ml-col">

      <!-- Empty state -->
      <div v-if="!messages.length && !isStreaming" class="empty-state">
        <slot name="empty">
          <p class="empty-hint">Message or type <kbd>/</kbd> to use a skill</p>
        </slot>
      </div>

      <MessageBubble
        v-for="(msg, i) in messages"
        :key="i"
        :msg="msg"
        :is-latest="i === lastAgentIndex"
        :show-retry="i === retryMessageIndex"
        @open-document="$emit('open-document', $event)"
        @retry="$emit('retry')"
      />

      <!-- Spinning logo — visible during any pipeline stage or streaming -->
      <div v-if="messages.length && (isStreaming || isPipelineRunning)" class="ml-thinking">
        <SudarshanChakra :size="32" color="var(--pri)" :spin="true" style="filter: brightness(1.5) saturate(1.4);" />
        <span class="ml-thinking-text">
          {{ activeHint }}<span class="ml-dots"><span>.</span><span>.</span><span>.</span></span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed, onMounted } from 'vue'
import MessageBubble   from './MessageBubble.vue'
import SudarshanChakra from '../SudarshanChakra.vue'

const props = defineProps({
  messages:          { type: Array,   default: () => [] },
  isStreaming:       { type: Boolean, default: false },
  isPipelineRunning: { type: Boolean, default: false },
  currentStage:      { type: String,  default: '' },
  stageLabel:        { type: String,  default: '' },
  executionId:       { type: String,  default: null },
  executionDone:     { type: Boolean, default: false },
})

defineEmits(['open-document', 'retry'])

const listEl = ref(null)

// Index of the user message just before the last error — shows retry icon when
// there's an active execution and no stream currently running.
const retryMessageIndex = computed(() => {
  if (!props.executionId || props.isStreaming || props.isPipelineRunning || props.executionDone) return -1
  const lastErrorIdx = props.messages.reduceRight((found, m, i) => found === -1 && m.type === 'error' ? i : found, -1)
  if (lastErrorIdx <= 0) return -1
  for (let i = lastErrorIdx - 1; i >= 0; i--) {
    if (props.messages[i].role === 'user') return i
  }
  return -1
})

// Index of the last agent text bubble — always shows copy button
const lastAgentIndex = computed(() => {
  for (let i = props.messages.length - 1; i >= 0; i--) {
    const m = props.messages[i]
    if (m.role === 'agent' && m.type !== 'document') {
      return i
    }
  }
  return -1
})

// True when there's already a streaming agent message bubble showing
const hasStreamingAgentMsg = computed(() =>
  props.messages.some(m => m.role === 'agent' && m.isStreaming)
)

// Short hint text — agent stage name takes priority over last user message
const thinkingHint = computed(() => {
  const last = [...props.messages].reverse().find(m => m.role === 'user')
  if (!last?.content) return 'Thinking'
  const text = last.content.trim()
  return text.length > 72 ? text.slice(0, 72).trimEnd() : text
})

const STAGE_HINTS = {
  intake:    'Intake Agent — understanding your project brief',
  discovery: 'Discovery Agent — asking clarifying questions',
  research:  'Research Agent — running parallel research branches',
  review:    'Review Agent — checking technical accuracy',
  approval:  'Approver Gate — evaluating business alignment',
}

const activeHint = computed(() => {
  if (props.isPipelineRunning) {
    return STAGE_HINTS[props.currentStage] || (props.stageLabel ? `${props.stageLabel} — working` : 'Agent pipeline is running')
  }
  return thinkingHint.value
})

const scrollToBottom = async () => {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

// Scroll on mount and when conversation is switched (array reference changes)
onMounted(scrollToBottom)
watch(() => props.messages, scrollToBottom)

// Scroll when messages are added or streaming changes
watch(() => [props.messages.length, props.isStreaming], scrollToBottom)
</script>

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  scroll-behavior: smooth;
  padding: 24px 0;
}

.ml-col {
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
  padding: 0 20px 100px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}

.empty-state { flex: 1; display: flex; align-items: center; justify-content: center; }
.empty-hint  { font-size: 15px; color: var(--muted); }
.ml-thinking {
  display: flex; align-items: center; gap: 10px;
  padding-top: 8px; margin-left: 8px;
}
.ml-thinking-text {
  font-size: 16px; color: var(--muted);
  font-style: italic;
}
.ml-dots span {
  animation: dot-blink 1.4s infinite;
  opacity: 0;
}
.ml-dots span:nth-child(2) { animation-delay: .2s; }
.ml-dots span:nth-child(3) { animation-delay: .4s; }
@keyframes dot-blink {
  0%, 80%, 100% { opacity: 0; }
  40%           { opacity: 1; }
}
.empty-hint kbd { display: inline-block; padding: 1px 6px; border: 1px solid var(--border); border-radius: 4px; font-family: monospace; background: var(--surface-2); }
</style>
