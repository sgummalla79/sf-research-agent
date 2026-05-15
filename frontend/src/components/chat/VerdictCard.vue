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
    <p class="verdict-body">{{ feedback }}</p>
    <ul v-if="issues?.length" class="verdict-list">
      <li v-for="(it, i) in issues" :key="i">{{ it }}</li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue'

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
.verdict-card { padding: 14px 16px; border-radius: 10px; border: 1px solid; }
.pass { background: #f0fdf4; border-color: #86efac; }
.fail { background: #fff1f2; border-color: #fca5a5; }
.verdict-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 14px; }
.verdict-badge { margin-left: auto; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 700; }
.badge-pass { background: #dcfce7; color: #166534; }
.badge-fail { background: #fee2e2; color: #991b1b; }
.verdict-body { font-size: 13px; color: var(--text); margin: 0 0 8px; line-height: 1.5; }
.verdict-list { margin: 0; padding-left: 18px; font-size: 13px; color: var(--text); }
.verdict-list li { margin-bottom: 4px; }
</style>
