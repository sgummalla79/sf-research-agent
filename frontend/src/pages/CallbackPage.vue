<template>
  <div class="cb-shell">
    <div class="cb-card">
      <svg class="cb-logo" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="2" width="20" height="20" rx="5"/>
        <line x1="9" y1="2" x2="9" y2="22"/>
      </svg>
      <p class="cb-msg" v-if="!error">Completing sign-in…</p>
      <p class="cb-err" v-else>{{ error }}<br/><a class="cb-link" href="/login">Back to login</a></p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth.js'

const router = useRouter()
const { handleCallback } = useAuth()
const error = ref('')

onMounted(async () => {
  const params = new URLSearchParams(window.location.search)
  const code   = params.get('code')
  const errMsg = params.get('error_description') || params.get('error')

  if (errMsg) { error.value = errMsg; return }
  if (!code)  { error.value = 'No authorization code received.'; return }

  const ok = await handleCallback(code)
  if (ok) {
    router.replace('/')
  } else {
    error.value = 'Authentication failed. Please try again.'
  }
})
</script>

<style scoped>
.cb-shell {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: #0f172a;
}
.cb-card {
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  color: #f1f5f9;
}
.cb-logo { width: 40px; height: 40px; color: #3b82f6; animation: spin 1.2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.cb-msg  { font-size: 15px; color: #94a3b8; }
.cb-err  { font-size: 14px; color: #fca5a5; text-align: center; line-height: 1.7; }
.cb-link { color: #3b82f6; text-decoration: underline; cursor: pointer; }
</style>
