<!-- Intake confirm_understanding panel — shown after document/image upload -->
<template>
  <div class="confirm-panel">
    <div class="confirm-header">
      <span>📋</span>
      <div>
        <p class="confirm-title">{{ headerTitle }}</p>
        <p class="confirm-sub">{{ headerSub }}</p>
      </div>
    </div>
    <div class="confirm-content" v-html="rendered" />
    <div class="confirm-footer">
      <textarea v-model="correction" class="confirm-ta" rows="2" placeholder="Optional: add a correction…" />
      <p v-if="props.error" class="confirm-error">{{ props.error }}</p>
      <AppButton variant="primary" :disabled="isStreaming" @click="submit">
        Submit
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

// If content is short and contains no bullet points or headings it's a prompt, not an understanding
const isPrompt = computed(() => {
  const text = props.content?.trim() || ''
  return text.length < 300 && !text.includes('##') && !text.includes('- ') && !text.includes('* ')
})

const headerTitle = computed(() =>
  isPrompt.value ? 'Intake Agent' : "Here's what I understood from your project brief"
)
const headerSub = computed(() =>
  isPrompt.value
    ? 'Describe your project below to get started.'
    : 'Read through carefully. Add a correction below if anything is wrong.'
)

function submit() {
  emit('confirm', correction.value.trim())
  correction.value = ''
}
</script>

<style scoped>
.confirm-panel   { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.confirm-header  { display: flex; gap: 14px; align-items: flex-start; }
.confirm-title   { font-weight: 600; color: var(--text); margin: 0 0 4px; font-size: 16px; }
.confirm-sub     { color: var(--muted); margin: 0; font-size: 14px; }
.confirm-content { font-size: 16px; color: var(--text); line-height: 1.7; max-height: 280px; overflow-y: auto; }
.confirm-content :deep(h1) { font-size: 1.4em; font-weight: 700; margin: 0.6em 0 0.3em; }
.confirm-content :deep(h2) { font-size: 1.2em; font-weight: 700; margin: 0.6em 0 0.3em; }
.confirm-content :deep(h3) { font-size: 1.05em; font-weight: 600; margin: 0.5em 0 0.2em; }
.confirm-content :deep(p)  { margin: 0 0 0.6em; }
.confirm-content :deep(ul), .confirm-content :deep(ol) { margin: 0 0 0.6em; padding-left: 1.4em; }
.confirm-content :deep(li) { margin-bottom: 0.2em; }
.confirm-content :deep(strong) { font-weight: 700; }
.confirm-content :deep(p:last-child) { margin-bottom: 0; }
.confirm-footer  { display: flex; flex-direction: column; gap: 10px; align-items: flex-end; }
.confirm-ta      { width: 100%; resize: vertical; min-height: 64px; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface); color: var(--text); font-size: 16px; font-family: inherit; line-height: 1.55; }
.confirm-ta:focus { outline: none; border-color: var(--pri); }
.confirm-error    { margin: 0; font-size: 14px; color: var(--danger, #e53e3e); }
</style>
