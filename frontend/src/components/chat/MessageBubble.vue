<!-- Single message — routes to correct sub-component based on type -->
<template>
  <div class="message" :class="msg.role">

    <!-- Document card -->
    <DocumentCard
      v-if="msg.type === 'document'"
      :artifact-id="msg.artifactId"
      :doc-version="msg.docVersion"
      @view="$emit('open-document', msg.artifactId)"
    />

    <!-- Stage status spinners -->
    <StatusCard
      v-else-if="['preparing','reviewing','approving'].includes(msg.type)"
      :stage="msg.type"
      :content="msg.content"
    />

    <!-- Review result -->
    <VerdictCard
      v-else-if="msg.type === 'review_result'"
      type="review"
      :passed="msg.reviewPassed"
      :feedback="msg.reviewFeedback"
      :issues="msg.criticalIssues"
    />

    <!-- Approval result -->
    <VerdictCard
      v-else-if="msg.type === 'approval_result'"
      type="approval"
      :passed="msg.approvalStatus === 'approved'"
      :feedback="msg.approvalComments"
      :issues="msg.requiredChanges"
    />

    <!-- Text bubble (regular chat + discovery + stage summaries) -->
    <template v-else>
      <div class="bubble-wrap" @mouseenter="hovered = true" @mouseleave="hovered = false">
        <div class="bubble">
          <MarkdownContent :text="msg.content" />
          <span v-if="msg.isStreaming" class="cursor" />
        </div>
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
      </div>
    </template>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import DocumentCard    from './DocumentCard.vue'
import StatusCard      from './StatusCard.vue'
import VerdictCard     from './VerdictCard.vue'
import MarkdownContent from '../ui/MarkdownContent.vue'

const props = defineProps({ msg: { type: Object, required: true } })
defineEmits(['open-document'])

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

.bubble { padding: 10px 14px; border-radius: 12px; font-size: 18px; line-height: 1.6; }
.user  .bubble { background: var(--surface-2); color: var(--text); border-bottom-right-radius: 4px; }
.agent .bubble { background: var(--bg); color: var(--text); border-bottom-left-radius: 4px; }

.bubble-wrap { display: flex; flex-direction: column; gap: 2px; }
.agent .bubble-wrap { align-items: flex-start; }
.user  .bubble-wrap { align-items: flex-end; }
.agent .copy-btn { margin-left: 8px; }
.user  .copy-btn { margin-right: 14px; }

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
