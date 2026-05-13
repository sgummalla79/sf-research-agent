<template>
  <div class="login-shell">
    <div class="login-card">

      <!-- Brand -->
      <div class="login-brand">
        <div class="login-logo-wrap">
          <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polygon fill="none" stroke="#f5a55a" stroke-width="4" stroke-linejoin="round"
              points="50,3 60.4,13.2 73.2,9.7 77.5,23 90.3,27.2 87,40.9 97,50 87,59.1 90.3,72.8 77.5,77 73.2,90.3 60.4,86.8 50,97 39.6,86.8 26.8,90.3 22.5,77 9.7,72.8 13,59.1 3,50 13,40.9 9.7,27.2 22.5,23 26.8,9.7 39.6,13.2"/>
            <circle cx="50" cy="50" r="33" stroke="#f5a55a" stroke-width="3.5"/>
            <g stroke="#f5a55a" stroke-width="2.8">
              <line x1="50" y1="17" x2="50" y2="41"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(30,50,50)"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(60,50,50)"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(90,50,50)"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(120,50,50)"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(150,50,50)"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(180,50,50)"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(210,50,50)"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(240,50,50)"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(270,50,50)"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(300,50,50)"/>
              <line x1="50" y1="17" x2="50" y2="41" transform="rotate(330,50,50)"/>
            </g>
            <circle cx="50" cy="50" r="16" stroke="#f5a55a" stroke-width="3.5"/>
            <circle cx="50" cy="50" r="8" stroke="#f5a55a" stroke-width="3" fill="#f5a55a" fill-opacity="0.25"/>
            <circle cx="50" cy="50" r="4" fill="#f5a55a"/>
          </svg>
        </div>
        <span class="login-app-name">Prajna</span>
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
            <component :is="providerIcon(conn.strategy)" class="social-icon" />
            Continue with {{ conn.display_name }}
          </button>
        </template>

        <!-- Fallback when connections couldn't be fetched -->
        <button v-else class="login-btn social" @click="loginWithSocial('')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style="flex-shrink:0">
            <circle cx="12" cy="12" r="10" stroke="#6366f1" stroke-width="2"/>
            <path d="M8 12h8M12 8l4 4-4 4" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Continue with Auth0
        </button>

      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth.js'

// ── Provider icon components ───────────────────────────────────────────────────

const IconGoogle = {
  render: () => h('svg', { width: 16, height: 16, viewBox: '0 0 24 24', style: 'flex-shrink:0' }, [
    h('path', { fill: '#4285F4', d: 'M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z' }),
    h('path', { fill: '#34A853', d: 'M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z' }),
    h('path', { fill: '#FBBC05', d: 'M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z' }),
    h('path', { fill: '#EA4335', d: 'M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z' }),
  ]),
}

const IconGitHub = {
  render: () => h('svg', { width: 16, height: 16, viewBox: '0 0 24 24', fill: '#f1f5f9', style: 'flex-shrink:0' },
    h('path', { d: 'M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0 1 12 6.836c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.202 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z' }),
  ),
}

const IconMicrosoft = {
  render: () => h('svg', { width: 16, height: 16, viewBox: '0 0 24 24', style: 'flex-shrink:0' }, [
    h('rect', { x: '1', y: '1',   width: '10', height: '10', fill: '#f25022' }),
    h('rect', { x: '13', y: '1',  width: '10', height: '10', fill: '#7fba00' }),
    h('rect', { x: '1', y: '13',  width: '10', height: '10', fill: '#00a4ef' }),
    h('rect', { x: '13', y: '13', width: '10', height: '10', fill: '#ffb900' }),
  ]),
}

const IconLinkedIn = {
  render: () => h('svg', { width: 16, height: 16, viewBox: '0 0 24 24', fill: '#0a66c2', style: 'flex-shrink:0' },
    h('path', { d: 'M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z' }),
  ),
}

const IconTwitter = {
  render: () => h('svg', { width: 16, height: 16, viewBox: '0 0 24 24', fill: '#f1f5f9', style: 'flex-shrink:0' },
    h('path', { d: 'M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z' }),
  ),
}

const IconFacebook = {
  render: () => h('svg', { width: 16, height: 16, viewBox: '0 0 24 24', fill: '#1877f2', style: 'flex-shrink:0' },
    h('path', { d: 'M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z' }),
  ),
}

const IconApple = {
  render: () => h('svg', { width: 16, height: 16, viewBox: '0 0 24 24', fill: '#f1f5f9', style: 'flex-shrink:0' },
    h('path', { d: 'M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701' }),
  ),
}

const PROVIDER_ICONS = {
  'google-oauth2': IconGoogle,
  'github':        IconGitHub,
  'microsoft':     IconMicrosoft,
  'windowslive':   IconMicrosoft,
  'linkedin':      IconLinkedIn,
  'twitter':       IconTwitter,
  'facebook':      IconFacebook,
  'apple':         IconApple,
}

function providerIcon(strategy) {
  return PROVIDER_ICONS[strategy] || IconGitHub   // fallback: generic dark circle icon
}

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
.login-logo-wrap { flex-shrink: 0; display: flex; align-items: center; }
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

.social-icon { flex-shrink: 0; }
</style>
