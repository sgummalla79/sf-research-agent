<!-- Review or approval verdict card -->
<template>
  <div class="verdict-card" :class="passed ? 'pass' : 'fail'">
    <div class="verdict-head">
      <span>{{ passed ? (type === 'approval' ? '🎉' : '✅') : (type === 'approval' ? '🔄' : '❌') }}</span>
      <strong>{{ type === 'approval' ? 'Approver Gate' : 'Technical Review' }}</strong>
      <span class="verdict-badge" :class="passed ? 'badge-pass' : 'badge-fail'">
        {{ badgeLabel }}
      </span>
    </div>
    <div class="verdict-body"><MarkdownContent :text="feedback" /></div>
    <ul v-if="issues?.length" class="verdict-list">
      <li v-for="(it, i) in issues" :key="i"><MarkdownContent :text="it" /></li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownContent from '../ui/MarkdownContent.vue'

const props = defineProps({
  type:     { type: String,  required: true },   // review | approval
  passed:   { type: Boolean, required: true },   // true = pass/approved
  feedback: { type: String,  default: '' },
  issues:   { type: Array,   default: () => [] },
})

const badgeLabel = computed(() => {
  if (props.type === 'approval') return props.passed ? 'APPROVED' : 'REJECTED'
  return props.passed ? 'PASSED' : 'FAILED'
})
</script>

<style scoped>
.verdict-card { padding: 12px 14px; border-radius: 10px; border: 1px solid; }
.pass { background: rgba(34,  197, 94,  0.08); border-color: rgba(34,  197, 94,  0.3); }
.fail { background: rgba(239, 68,  68,  0.08); border-color: rgba(239, 68,  68,  0.3); }

.verdict-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 14px; }
.verdict-badge { margin-left: auto; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 700; }
.badge-pass { background: rgba(34,  197, 94,  0.15); color: #22c55e; }
.badge-fail { background: rgba(239, 68,  68,  0.15); color: #ef4444; }

.verdict-body {
  font-size: 13px; color: var(--text); margin: 0 0 8px; line-height: 1.6;
  max-height: 120px; overflow-y: auto;
  scrollbar-width: thin;
}
.verdict-body :deep(.prose p:last-child) { margin-bottom: 0; }
.verdict-list :deep(.prose p) { margin: 0; }
.verdict-body::-webkit-scrollbar       { width: 4px; }
.verdict-body::-webkit-scrollbar-track { background: transparent; }
.verdict-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

.verdict-list {
  margin: 0; padding-left: 18px; font-size: 13px; color: var(--text);
  max-height: 120px; overflow-y: auto;
  scrollbar-width: thin;
}
.verdict-list::-webkit-scrollbar       { width: 4px; }
.verdict-list::-webkit-scrollbar-track { background: transparent; }
.verdict-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
.verdict-list li { margin-bottom: 4px; }
</style>
