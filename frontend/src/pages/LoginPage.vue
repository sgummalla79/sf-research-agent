<template>
  <div class="login-shell">
    <div class="login-card">

      <!-- Brand -->
      <div class="login-brand">
        <svg class="login-logo" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="2" width="20" height="20" rx="5"/>
          <line x1="9" y1="2" x2="9" y2="22"/>
        </svg>
        <span class="login-app-name">Technical Architecture Agent</span>
      </div>

      <h1 class="login-heading">Sign in</h1>

      <!-- Error -->
      <div v-if="authError" class="login-error">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" style="flex-shrink:0">
          <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
          <path d="M8 5v3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="8" cy="11" r=".75" fill="currentColor"/>
        </svg>
        {{ authError }}
      </div>

      <!-- Email / password form — always visible -->
      <form class="login-form" @submit.prevent="submitPassword">
        <input v-model="email" class="lf-input" type="email"
          placeholder="Email address" autocomplete="email" required />
        <input v-model="password" class="lf-input" type="password"
          placeholder="Password" autocomplete="current-password" required />
        <button class="login-btn primary" :disabled="loading" type="submit">
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>

      <!-- Divider -->
      <div class="login-divider"><span>or</span></div>

      <!-- Social connections -->
      <div class="login-social">

        <!-- Loading -->
        <div v-if="loadingConnections" class="login-loading">
          Loading sign-in options…
        </div>

        <!-- Specific social buttons -->
        <template v-else-if="connections.length">
          <button v-for="conn in connections" :key="conn.name"
            class="login-btn social" @click="loginWithSocial(conn.name)">
            <!-- Google logo -->
            <svg v-if="conn.strategy === 'google-oauth2'" width="15" height="15"
              viewBox="0 0 24 24" style="flex-shrink:0">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            <span v-else class="social-dot" :data-strategy="conn.strategy" />
            Continue with {{ conn.display_name }}
          </button>
        </template>

        <!-- Fallback when connections couldn't be fetched -->
        <button v-else class="login-btn social" @click="loginWithAuth0()">
          <span class="social-dot" />
          Continue with Auth0
        </button>

      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth.js'

const router = useRouter()
const { loginWithPassword, loginWithSocial, loading, authError, isAuthenticated } = useAuth()

const email    = ref('')
const password = ref('')
const connections       = ref([])
const loadingConnections = ref(true)

async function fetchConnections() {
  try {
    const res  = await fetch('/auth/connections')
    const data = await res.json()
    connections.value = data.connections || []
  } catch {
    connections.value = []
  } finally {
    loadingConnections.value = false
  }
}

async function submitPassword() {
  const ok = await loginWithPassword(email.value, password.value)
  if (ok) router.push('/')
}

function loginWithAuth0() {
  const domain   = import.meta.env.VITE_AUTH0_DOMAIN || ''
  const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID || ''
  const params   = new URLSearchParams({
    client_id:     clientId,
    response_type: 'code',
    redirect_uri:  window.location.origin + '/callback',
    scope:         'openid profile email offline_access',
  })
  window.location.href = `https://${domain}/authorize?${params}`
}

onMounted(() => {
  if (isAuthenticated.value) { router.push('/'); return }
  fetchConnections()
})
</script>

<style scoped>
.login-shell {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: #0f172a; padding: 20px;
}
.login-card {
  width: 100%; max-width: 380px;
  background: #1e293b; border: 1px solid #334155; border-radius: 16px;
  padding: 36px 32px; display: flex; flex-direction: column; gap: 18px;
  box-shadow: 0 20px 60px rgba(0,0,0,.4);
}
.login-brand { display: flex; align-items: center; gap: 10px; }
.login-logo  { color: #3b82f6; width: 26px; height: 26px; flex-shrink: 0; }
.login-app-name { font-size: 14px; font-weight: 700; color: #f1f5f9; }
.login-heading  { font-size: 22px; font-weight: 700; color: #f1f5f9; margin: 0; }

.login-error {
  display: flex; align-items: flex-start; gap: 8px;
  background: #1f0000; border: 1px solid #991b1b; border-radius: 8px;
  padding: 10px 12px; font-size: 13px; color: #fca5a5;
}

.login-form  { display: flex; flex-direction: column; gap: 10px; }
.lf-input {
  padding: 10px 13px; background: #0f172a; border: 1.5px solid #334155;
  border-radius: 8px; color: #f1f5f9; font-size: 14px; outline: none;
  transition: border-color .15s; width: 100%; box-sizing: border-box;
}
.lf-input:focus       { border-color: #3b82f6; }
.lf-input::placeholder { color: #475569; }

.login-divider {
  display: flex; align-items: center; gap: 10px;
  color: #475569; font-size: 12px;
}
.login-divider::before,
.login-divider::after { content: ''; flex: 1; height: 1px; background: #334155; }

.login-social { display: flex; flex-direction: column; gap: 8px; }
.login-loading { font-size: 13px; color: #64748b; text-align: center; padding: 8px 0; }

.login-btn {
  width: 100%; padding: 10px 16px; border-radius: 8px; border: none;
  font-size: 14px; font-weight: 600; cursor: pointer;
}
.login-btn:disabled { opacity: .5; cursor: not-allowed; }

.login-btn.primary { background: #3b82f6; color: #fff; }
.login-btn.primary:hover:not(:disabled) { background: #2563eb; }

.login-btn.social {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  background: #0f172a; color: #f1f5f9; border: 1.5px solid #334155;
}
.login-btn.social:hover { border-color: #64748b; }

.social-dot {
  width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0;
  background: #6366f1;
}
.social-dot[data-strategy="github"]   { background: #f1f5f9; }
.social-dot[data-strategy="twitter"]  { background: #1d9bf0; }
.social-dot[data-strategy="linkedin"] { background: #0a66c2; }
.social-dot[data-strategy="facebook"] { background: #1877f2; }
</style>
