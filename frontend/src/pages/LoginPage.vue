<template>
  <div class="login-shell">
    <div class="login-card">

      <!-- Logo / brand -->
      <div class="login-brand">
        <svg class="login-logo" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="2" width="20" height="20" rx="5"/>
          <line x1="9" y1="2" x2="9" y2="22"/>
        </svg>
        <span class="login-app-name">Technical Architecture Agent</span>
      </div>

      <h1 class="login-heading">Sign in</h1>
      <p class="login-sub">Continue to your workspace</p>

      <!-- Error banner -->
      <div v-if="authError" class="login-error">{{ authError }}</div>

      <!-- Loading connections -->
      <div v-if="loadingConnections" class="login-loading">Loading sign-in options…</div>

      <template v-else>

        <!-- Username / Password form (auth0 database connections) -->
        <template v-for="conn in dbConnections" :key="conn.name">
          <form class="login-form" @submit.prevent="submitPassword(conn)">
            <div class="lf-field">
              <label class="lf-label">Email</label>
              <input v-model="email" class="lf-input" type="email"
                placeholder="you@example.com" autocomplete="email" required />
            </div>
            <div class="lf-field">
              <label class="lf-label">Password</label>
              <input v-model="password" class="lf-input" type="password"
                placeholder="••••••••" autocomplete="current-password" required />
            </div>
            <button class="login-btn primary" :disabled="loading" type="submit">
              {{ loading ? 'Signing in…' : 'Sign in' }}
            </button>
          </form>
        </template>

        <!-- Divider (only when both DB and social exist) -->
        <div v-if="dbConnections.length && socialConnections.length" class="login-divider">
          <span>or continue with</span>
        </div>

        <!-- Social connection buttons -->
        <div class="login-social">
          <button v-for="conn in socialConnections" :key="conn.name"
            class="login-btn social" @click="loginWithSocial(conn.name)">
            <img v-if="providerIcon(conn.strategy)"
              :src="providerIcon(conn.strategy)" :alt="conn.display_name" class="social-icon" />
            <span v-else class="social-fallback">{{ conn.display_name[0] }}</span>
            Continue with {{ conn.display_name }}
          </button>
        </div>

      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth.js'

const router = useRouter()
const { loginWithPassword, loginWithSocial, loading, authError, isAuthenticated } = useAuth()

const email    = ref('')
const password = ref('')
const connections      = ref([])
const loadingConnections = ref(true)

const dbConnections     = computed(() => connections.value.filter(c => c.strategy === 'auth0'))
const socialConnections = computed(() => connections.value.filter(c => c.strategy !== 'auth0'))

// Social provider icon map
function providerIcon(strategy) {
  const icons = {
    'google-oauth2': 'https://www.google.com/favicon.ico',
    'github':        'https://github.com/favicon.ico',
    'microsoft':     'https://www.microsoft.com/favicon.ico',
    'linkedin':      'https://www.linkedin.com/favicon.ico',
  }
  return icons[strategy] || null
}

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

async function submitPassword(conn) {
  const ok = await loginWithPassword(email.value, password.value, conn.name)
  if (ok) router.push('/')
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
  width: 100%; max-width: 400px;
  background: #1e293b; border: 1px solid #334155;
  border-radius: 16px; padding: 40px 36px;
  display: flex; flex-direction: column; gap: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,.4);
}

.login-brand {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 4px;
}
.login-logo { color: #3b82f6; flex-shrink: 0; width: 28px; height: 28px; }
.login-app-name { font-size: 15px; font-weight: 700; color: #f1f5f9; }

.login-heading { font-size: 24px; font-weight: 700; color: #f1f5f9; margin: 0; }
.login-sub     { font-size: 14px; color: #94a3b8; margin: -12px 0 0; }

.login-error {
  background: #1f0000; border: 1px solid #991b1b; border-radius: 8px;
  padding: 10px 14px; font-size: 13px; color: #fca5a5;
}

.login-loading { font-size: 14px; color: #94a3b8; text-align: center; padding: 12px 0; }

.login-form { display: flex; flex-direction: column; gap: 14px; }

.lf-field { display: flex; flex-direction: column; gap: 5px; }
.lf-label { font-size: 13px; font-weight: 500; color: #cbd5e1; }
.lf-input {
  padding: 10px 13px; background: #0f172a; border: 1.5px solid #334155;
  border-radius: 8px; color: #f1f5f9; font-size: 14px; outline: none;
  transition: border-color .15s;
}
.lf-input:focus       { border-color: #3b82f6; }
.lf-input::placeholder { color: #475569; }

.login-divider {
  display: flex; align-items: center; gap: 12px;
  color: #64748b; font-size: 13px;
}
.login-divider::before,
.login-divider::after {
  content: ''; flex: 1; height: 1px; background: #334155;
}

.login-social { display: flex; flex-direction: column; gap: 10px; }

.login-btn {
  width: 100%; padding: 11px 16px; border-radius: 9px; border: none;
  font-size: 14px; font-weight: 600; cursor: pointer; transition: opacity .15s;
}
.login-btn:disabled { opacity: .5; cursor: not-allowed; }

.login-btn.primary {
  background: #3b82f6; color: #fff;
}
.login-btn.primary:hover:not(:disabled) { background: #2563eb; }

.login-btn.social {
  display: flex; align-items: center; gap: 10px; justify-content: center;
  background: #0f172a; color: #f1f5f9;
  border: 1.5px solid #334155;
}
.login-btn.social:hover { border-color: #64748b; background: #1e293b; }

.social-icon    { width: 18px; height: 18px; border-radius: 3px; flex-shrink: 0; }
.social-fallback {
  width: 18px; height: 18px; border-radius: 3px; background: #334155;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: #94a3b8; flex-shrink: 0;
}
</style>
