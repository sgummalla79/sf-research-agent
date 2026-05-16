<!-- Intake confirm_understanding panel — shown after document/image upload -->
<template>
  <div class="confirm-panel">
    <div class="confirm-header">
      <span>📋</span>
      <div>
        <p class="confirm-title">Here's what I understood from your project brief / upload</p>
        <p class="confirm-sub">Read through carefully. Add a correction below if anything is wrong.</p>
      </div>
    </div>
    <div class="confirm-content" v-html="rendered" />
    <div class="confirm-footer">
      <textarea v-model="correction" class="confirm-ta" rows="2" placeholder="Optional: add a correction…" />
      <p v-if="props.error" class="confirm-error">{{ props.error }}</p>
      <AppButton variant="primary" :disabled="isStreaming" @click="submit">
        Looks right — start discovery →
      </AppButton>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
import AppButton from '../ui/AppButton.vue'

const props = defineProps({
  content:     { type: String,  required: true },
  isStreaming:  { type: Boolean, default: false },
  error:        { type: String,  default: '' },
})
const emit = defineEmits(['confirm'])

const correction = ref('')
const rendered   = computed(() => {
  try { return marked.parse(props.content) } catch { return props.content }
})

function submit() {
  emit('confirm', correction.value.trim())
  correction.value = ''
}
</script>

<style scoped>
.confirm-panel   { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.confirm-header  { display: flex; gap: 12px; align-items: flex-start; font-size: 13px; }
.confirm-title   { font-weight: 600; color: var(--text); margin: 0 0 2px; font-size: 14px; }
.confirm-sub     { color: var(--muted); margin: 0; font-size: 12px; }
.confirm-content { font-size: 13px; color: var(--text); line-height: 1.6; max-height: 240px; overflow-y: auto; }
.confirm-footer  { display: flex; flex-direction: column; gap: 8px; }
.confirm-ta      { width: 100%; resize: vertical; min-height: 56px; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface); color: var(--text); font-size: 14px; font-family: inherit; }
.confirm-ta:focus { outline: none; border-color: var(--pri); }
.confirm-error    { margin: 0; font-size: 13px; color: var(--danger, #e53e3e); }
</style>
