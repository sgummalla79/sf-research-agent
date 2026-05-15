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
      <div class="bubble">
        <MarkdownContent :text="msg.content" />
        <span v-if="msg.isStreaming" class="cursor" />
      </div>
    </template>

  </div>
</template>

<script setup>
import DocumentCard    from './DocumentCard.vue'
import StatusCard      from './StatusCard.vue'
import VerdictCard     from './VerdictCard.vue'
import MarkdownContent from '../ui/MarkdownContent.vue'

defineProps({ msg: { type: Object, required: true } })
defineEmits(['open-document'])
</script>

<style scoped>
.message { display: flex; flex-direction: column; gap: 6px; max-width: 780px; }
.message.user  { align-self: flex-end; align-items: flex-end; }
.message.agent { align-self: flex-start; align-items: flex-start; }


.bubble { padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.6; }
.user  .bubble { background: var(--pri); color: var(--pri-fg); border-bottom-right-radius: 4px; }
.agent .bubble { background: var(--surface-2); color: var(--text); border-bottom-left-radius: 4px; border: 1px solid var(--border); }

.cursor { display: inline-block; width: 2px; height: 14px; background: var(--text); animation: blink 1s step-end infinite; margin-left: 2px; vertical-align: middle; }
@keyframes blink { 50% { opacity: 0; } }
</style>
