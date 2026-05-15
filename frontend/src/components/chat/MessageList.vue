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
        @open-document="$emit('open-document', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'

const props = defineProps({
  messages:    { type: Array,   default: () => [] },
  isStreaming: { type: Boolean, default: false },
})

defineEmits(['open-document'])

const listEl = ref(null)

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
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}

.empty-state { flex: 1; display: flex; align-items: center; justify-content: center; }
.empty-hint  { font-size: 15px; color: var(--muted); }
.empty-hint kbd { display: inline-block; padding: 1px 6px; border: 1px solid var(--border); border-radius: 4px; font-family: monospace; background: var(--surface-2); }
</style>
