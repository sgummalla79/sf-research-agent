<!-- Single message — routes to correct sub-component based on type -->
<template>
  <div v-if="!['preparing','reviewing','approving'].includes(msg.type)" class="message" :class="msg.role">

    <!-- Document card -->
    <DocumentCard
      v-if="msg.type === 'document'"
      :artifact-id="msg.artifactId"
      :doc-version="msg.docVersion"
      @view="$emit('open-document', msg.artifactId)"
    />

    <!-- User message — speech bubble -->
    <template v-else-if="msg.role === 'user'">
      <div class="bubble-wrap" @mouseenter="hovered = true" @mouseleave="hovered = false">
        <div class="bubble">
          <MarkdownContent :text="msg.content" />
          <span v-if="msg.isStreaming" class="cursor" />
        </div>
        <div class="bubble-actions">
          <button
            v-if="!msg.isStreaming"
            class="copy-btn"
            :class="{ copied, visible: hovered || copied }"
            @click="copyContent"
            title="Copy"
          >
            <svg v-if="!copied" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </button>
          <button
            v-if="props.showRetry"
            class="copy-btn"
            :class="{ visible: hovered }"
            @click="$emit('retry')"
            title="Retry"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
              <polyline points="1 4 1 10 7 10"/>
              <path d="M3.51 15a9 9 0 1 0 .49-4.5"/>
            </svg>
          </button>
        </div>
      </div>
    </template>

    <!-- Agent / error — flat, no bubble -->
    <template v-else>
      <div class="agent-wrap" @mouseenter="hovered = true" @mouseleave="hovered = false">
        <div class="agent-row">
          <span v-if="msg.type === 'error'" class="msg-icon msg-icon-error" title="Error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="17" height="17">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </span>
          <div class="agent-content" :class="{ 'agent-error': msg.type === 'error' }">
            <MarkdownContent :text="msg.content" />
            <span v-if="msg.isStreaming" class="cursor" />
          </div>
        </div>
        <div class="bubble-actions">
          <button
            v-if="!msg.isStreaming"
            class="copy-btn"
            :class="{ copied, visible: hovered || copied || props.isLatest }"
            @click="copyContent"
            title="Copy"
          >
            <svg v-if="!copied" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </button>
        </div>
      </div>
    </template>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import DocumentCard    from './DocumentCard.vue'
import MarkdownContent from '../ui/MarkdownContent.vue'

const props = defineProps({
  msg:       { type: Object,  required: true },
  isLatest:  { type: Boolean, default: false },
  showRetry: { type: Boolean, default: false },
})
defineEmits(['open-document', 'retry'])

const copied  = ref(false)
const hovered = ref(false)

function copyContent() {
  navigator.clipboard.writeText(props.msg.content).then(() => {
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  })
}
</script>

<style scoped>
.message { display: flex; flex-direction: column; gap: 6px; max-width: 780px; }
.message.user  { align-self: flex-end; align-items: flex-end; }
.message.agent { align-self: flex-start; align-items: flex-start; }

/* User bubble */
.bubble { padding: 10px 14px; border-radius: 12px; border-bottom-right-radius: 4px; font-size: 18px; line-height: 1.6; background: var(--surface-2); color: var(--text); }

.bubble-wrap { display: flex; flex-direction: column; gap: 2px; align-items: flex-end; }

/* Agent flat content — no bubble */
.agent-wrap    { display: flex; flex-direction: column; gap: 2px; align-items: flex-start; }
.agent-row     { display: flex; align-items: flex-start; gap: 10px; }
.agent-content { font-size: 18px; line-height: 1.7; color: var(--text); }
.agent-error   { color: var(--fail-tx); }

.msg-icon            { flex-shrink: 0; margin-top: 3px; display: flex; align-items: center; }
.msg-icon-error      { color: var(--fail-tx); }

.bubble-actions { display: flex; align-items: center; gap: 4px; }

.copy-btn {
  display: flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: 6px;
  border: none; background: transparent; cursor: pointer;
  color: var(--muted);
  opacity: 0; transition: opacity .15s, background .12s, color .12s;
}
.copy-btn.visible { opacity: 1; }
.copy-btn:hover { background: var(--hover); color: var(--text); }
.copy-btn.copied { color: #22c55e; }

.cursor { display: inline-block; width: 2px; height: 14px; background: var(--text); animation: blink 1s step-end infinite; margin-left: 2px; vertical-align: middle; }
@keyframes blink { 50% { opacity: 0; } }
</style>
