<template>
  <div class="cb-shell">
    <div class="cb-card">
      <svg class="cb-logo" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="2" width="20" height="20" rx="5"/>
        <line x1="9" y1="2" x2="9" y2="22"/>
      </svg>
      <p class="cb-msg" v-if="!error">Completing sign-in…</p>
      <div v-else class="cb-err">
        <p>{{ errorMessage }}</p>
        <a class="cb-link" href="/login">← Back to login</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router      = useRouter()
const error       = ref(false)
const errorMessage = ref('')

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  const err    = params.get('error')

  if (err) {
    error.value        = true
    errorMessage.value = err === 'auth_failed'
      ? 'Authentication failed. Please try again.'
      : decodeURIComponent(err)
    return
  }

  // Backend handled the real callback and redirected here — just go home
  router.replace('/')
})
</script>

<style scoped>
:root { --cb-bg: var(--bg); --cb-tx: var(--text); --cb-muted: var(--muted); --cb-pri: var(--pri); --cb-err: var(--danger); }
.cb-shell {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: var(--cb-bg);
}
.cb-card {
  display: flex; flex-direction: column; align-items: center; gap: 16px;
}
.cb-logo {
  width: 40px; height: 40px; color: var(--cb-pri);
  animation: spin 1.2s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.cb-msg  { font-size: 15px; color: var(--cb-muted); }
.cb-err  { text-align: center; display: flex; flex-direction: column; gap: 12px; }
.cb-err p { font-size: 14px; color: var(--cb-err); }
.cb-link { font-size: 13px; color: var(--cb-pri); text-decoration: underline; }
</style>
