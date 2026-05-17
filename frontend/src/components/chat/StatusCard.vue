<!-- Stage-start status spinner card (research/review/approval in-progress) -->
<template>
  <div :class="['status-card', stage]">
    <AppSpinner size="sm" />
    <div>
      <p class="sc-title">{{ title }}</p>
      <p class="sc-sub">{{ subtitle }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppSpinner from '../ui/AppSpinner.vue'

const props = defineProps({
  stage:   { type: String, required: true },
  content: { type: String, default: '' },
})

const LABELS = {
  preparing: { title: 'Research Agent is working',    sub: 'Running parallel research branches…' },
  reviewing: { title: 'Review Agent is reviewing',    sub: 'Checking technical accuracy and completeness…' },
  approving: { title: 'Approver Gate is evaluating',  sub: 'Assessing business value and strategic alignment…' },
}

const title    = computed(() => LABELS[props.stage]?.title    || props.content || 'Working…')
const subtitle = computed(() => LABELS[props.stage]?.sub      || '')
</script>

<style scoped>
.status-card { display: flex; align-items: flex-start; gap: 12px; padding: 14px 16px; border-radius: 10px; background: var(--surface-2); border: 1px solid var(--border); }
.sc-title { font-size: 18px; font-weight: 600; color: var(--text); margin: 0 0 2px; }
.sc-sub   { font-size: 16px; color: var(--muted); margin: 0; }
</style>
