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
        @open-document="$emit('open-document', $event)"
      />

      <!-- Logo: always visible except while text is actively printing -->
      <div v-if="messages.length && !(isStreaming && hasStreamingAgentMsg)" class="ml-thinking">
        <SudarshanChakra :size="22" color="var(--pri)" :spin="isStreaming" />
        <span v-if="isStreaming" class="ml-thinking-text">{{ thinkingHint }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import MessageBubble   from './MessageBubble.vue'
import SudarshanChakra from '../SudarshanChakra.vue'

const props = defineProps({
  messages:    { type: Array,   default: () => [] },
  isStreaming: { type: Boolean, default: false },
})

defineEmits(['open-document'])

const listEl = ref(null)

// Index of the last agent text bubble — always shows copy button
const lastAgentIndex = computed(() => {
  for (let i = props.messages.length - 1; i >= 0; i--) {
    const m = props.messages[i]
    if (m.role === 'agent' && !['document','preparing','reviewing','approving','review_result','approval_result'].includes(m.type)) {
      return i
    }
  }
  return -1
})

// True when there's already a streaming agent message bubble showing
const hasStreamingAgentMsg = computed(() =>
  props.messages.some(m => m.role === 'agent' && m.isStreaming)
)

// Short hint text from the last user message
const thinkingHint = computed(() => {
  const last = [...props.messages].reverse().find(m => m.role === 'user')
  if (!last?.content) return 'Thinking…'
  const text = last.content.trim()
  return text.length > 72 ? text.slice(0, 72).trimEnd() + '…' : text
})

// Auto-scroll to bottom when messages change or streaming
watch(
  () => [props.messages.length, props.isStreaming],
  async () => {
    await nextTick()
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  },
)
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
.empty-hint kbd { display: inline-block; padding: 1px 6px; border: 1px solid var(--border); border-radius: 4px; font-family: monospace; background: var(--surface-2); }
</style>
