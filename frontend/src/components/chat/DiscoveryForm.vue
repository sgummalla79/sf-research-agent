<!-- Discovery Q&A form — shown when the pipeline sends questions -->
<template>
  <div class="discovery-form">
    <!-- Single question -->
    <template v-if="questions.length === 1">
      <div class="df-row">
        <textarea
          v-model="answers[0]"
          class="df-ta"
          placeholder="Type your answer…"
          rows="2"
          @keydown.enter.exact.prevent="submit"
        />
        <AppButton
          variant="primary"
          :disabled="!answers[0]?.trim() || isStreaming"
          @click="submit"
        >Send</AppButton>
      </div>
    </template>

    <!-- Multiple questions -->
    <template v-else>
      <div class="df-scroll">
        <div v-for="(q, i) in questions" :key="i" class="df-item">
          <label class="df-label">{{ i + 1 }}. {{ q }}</label>
          <textarea v-model="answers[i]" class="df-ta" :placeholder="`Answer ${i + 1}…`" rows="2" />
        </div>
      </div>
      <div class="df-footer">
        <AppButton
          variant="primary"
          :disabled="answers.some(a => !a?.trim()) || isStreaming"
          @click="submit"
        >Send All Answers →</AppButton>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import AppButton from '../ui/AppButton.vue'

const props = defineProps({
  questions:  { type: Array,   required: true },
  isStreaming: { type: Boolean, default: false },
})
const emit = defineEmits(['submit'])

const answers = ref([])

watch(() => props.questions, (qs) => {
  answers.value = qs.map(() => '')
}, { immediate: true })

function submit() {
  if (answers.value.some(a => !a?.trim())) return
  emit('submit', [...answers.value])
}
</script>

<style scoped>
.discovery-form { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.df-row  { display: flex; gap: 8px; align-items: flex-end; }
.df-ta   { flex: 1; width: 100%; resize: vertical; min-height: 60px; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface); color: var(--text); font-size: 14px; font-family: inherit; }
.df-ta:focus { outline: none; border-color: var(--pri); }
.df-scroll { display: flex; flex-direction: column; gap: 14px; max-height: 300px; overflow-y: auto; margin-bottom: 12px; }
.df-item   { display: flex; flex-direction: column; gap: 6px; }
.df-label  { font-size: 13px; font-weight: 500; color: var(--text); }
.df-footer { display: flex; justify-content: flex-end; }
</style>
