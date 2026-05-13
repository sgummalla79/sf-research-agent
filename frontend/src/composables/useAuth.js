/**
 * Auth composable — cookie-based sessions, mirrors sgummalla_works pattern.
 *
 * The backend sets an httpOnly session cookie after login.
 * The browser sends it automatically on every fetch with credentials:'include'.
 * No token ever lives in localStorage or JavaScript memory.
 *
 * Bootstrap: call fetchUser() on app mount to restore session from /auth/me.
 */

import { ref, computed } from 'vue'

const _user    = ref(JSON.parse(sessionStorage.getItem('ta_user') || 'null'))
const _loading = ref(false)
const _error   = ref('')

const isAuthenticated = computed(() => !!_user.value)
const user            = computed(() => _user.value)
const loading         = computed(() => _loading.value)
const authError       = computed(() => _error.value)

// ── Bootstrap — call once on mount to restore session from cookie ─────────────

async function fetchUser() {
  try {
    const res = await fetch('/auth/me', { credentials: 'include' })
    if (res.ok) {
      const data = await res.json()
      _user.value = data
      sessionStorage.setItem('ta_user', JSON.stringify(data))
    } else {
      _user.value = null
      sessionStorage.removeItem('ta_user')
    }
  } catch {
    _user.value = null
  }
}

// ── Email / password ──────────────────────────────────────────────────────────

async function loginWithPassword(email, password, connection = 'Username-Password-Authentication') {
  _loading.value = true
  _error.value   = ''
  try {
    const res = await fetch('/auth/token', {
      method:      'POST',
      credentials: 'include',
      headers:     { 'Content-Type': 'application/json' },
      body:        JSON.stringify({ email, password, connection }),
    })

    let data = {}
    try { data = await res.json() } catch { /* non-JSON body */ }

    if (!res.ok) {
      _error.value = data.detail || 'Invalid email or password.'
      return false
    }
    _user.value = data.user
    sessionStorage.setItem('ta_user', JSON.stringify(data.user))
    return true
  } catch (e) {
    _error.value = e?.message?.includes('fetch')
      ? 'Cannot reach the server. Make sure the backend is running.'
      : 'Something went wrong. Please try again.'
    return false
  } finally {
    _loading.value = false
  }
}

// ── Social login — redirect through backend, which handles Auth0 flow ─────────

function loginWithSocial(connectionName) {
  const url = connectionName
    ? `/auth/initiate?connection=${encodeURIComponent(connectionName)}`
    : '/auth/initiate'
  window.location.href = url
}

// ── Logout ────────────────────────────────────────────────────────────────────

async function logout() {
  await fetch('/auth/logout', { method: 'POST', credentials: 'include' })
  _user.value = null
  sessionStorage.removeItem('ta_user')
}

export function useAuth() {
  return {
    isAuthenticated,
    user,
    loading,
    authError,
    fetchUser,
    loginWithPassword,
    loginWithSocial,
    logout,
  }
}
