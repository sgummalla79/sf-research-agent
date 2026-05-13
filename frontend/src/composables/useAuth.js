/**
 * Auth0 authentication composable.
 *
 * Handles:
 *  - Token storage (access + refresh in localStorage)
 *  - Automatic token refresh before expiry
 *  - Login (username/password and social connections)
 *  - Logout
 *  - Current user profile
 */

import { ref, computed } from 'vue'

const ACCESS_TOKEN_KEY  = 'ta_access_token'
const REFRESH_TOKEN_KEY = 'ta_refresh_token'
const USER_KEY          = 'ta_user'

const _accessToken  = ref(localStorage.getItem(ACCESS_TOKEN_KEY) || '')
const _refreshToken = ref(localStorage.getItem(REFRESH_TOKEN_KEY) || '')
const _user         = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))
const _loading      = ref(false)
const _error        = ref('')

let _refreshTimer = null

// ── Helpers ───────────────────────────────────────────────────────────────────

function _parseJwt(token) {
  try {
    return JSON.parse(atob(token.split('.')[1]))
  } catch {
    return null
  }
}

function _secondsUntilExpiry(token) {
  const payload = _parseJwt(token)
  if (!payload?.exp) return 0
  return payload.exp - Math.floor(Date.now() / 1000)
}

function _persist(tokens) {
  if (tokens.access_token) {
    _accessToken.value = tokens.access_token
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
  }
  if (tokens.refresh_token) {
    _refreshToken.value = tokens.refresh_token
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
  }
}

function _clearStorage() {
  _accessToken.value  = ''
  _refreshToken.value = ''
  _user.value         = null
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

// ── Auto-refresh ──────────────────────────────────────────────────────────────

async function _doRefresh() {
  const rt = _refreshToken.value
  if (!rt) return false
  try {
    const res  = await fetch('/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    })
    if (!res.ok) { _clearStorage(); return false }
    const data = await res.json()
    _persist(data)
    _scheduleRefresh()
    return true
  } catch {
    return false
  }
}

function _scheduleRefresh() {
  if (_refreshTimer) clearTimeout(_refreshTimer)
  const at  = _accessToken.value
  if (!at)  return
  const secs = _secondsUntilExpiry(at)
  const wait = Math.max((secs - 60) * 1000, 0)   // refresh 60s before expiry
  _refreshTimer = setTimeout(_doRefresh, wait)
}

// ── Public API ────────────────────────────────────────────────────────────────

const isAuthenticated = computed(() => !!_accessToken.value)
const user            = computed(() => _user.value)
const accessToken     = computed(() => _accessToken.value)
const loading         = computed(() => _loading.value)
const authError       = computed(() => _error.value)

async function fetchUser() {
  if (!_accessToken.value) return
  try {
    const res = await fetch('/auth/me', {
      headers: { Authorization: `Bearer ${_accessToken.value}` },
    })
    if (res.ok) {
      const data = await res.json()
      _user.value = data
      localStorage.setItem(USER_KEY, JSON.stringify(data))
    }
  } catch { /* non-fatal */ }
}

async function loginWithPassword(email, password, connection = 'Username-Password-Authentication') {
  _loading.value = true
  _error.value   = ''
  try {
    const res  = await fetch('/auth/token', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ email, password, connection }),
    })
    const data = await res.json()
    if (!res.ok) {
      _error.value = data.detail || 'Login failed.'
      return false
    }
    _persist(data)
    await fetchUser()
    _scheduleRefresh()
    return true
  } catch (e) {
    _error.value = 'Network error. Is the server running?'
    return false
  } finally {
    _loading.value = false
  }
}

function loginWithSocial(connectionName) {
  // Route through backend — all Auth0 config lives server-side, no VITE_ vars needed.
  const url = connectionName
    ? `/auth/initiate?connection=${encodeURIComponent(connectionName)}`
    : '/auth/initiate'
  window.location.href = url
}

async function handleCallback(code) {
  _loading.value = true
  _error.value   = ''
  try {
    const res  = await fetch('/auth/callback', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ code, redirect_uri: window.location.origin + '/callback' }),
    })
    const data = await res.json()
    if (!res.ok) {
      _error.value = data.detail || 'Authentication failed.'
      return false
    }
    _persist(data)
    await fetchUser()
    _scheduleRefresh()
    return true
  } catch {
    _error.value = 'Network error during authentication.'
    return false
  } finally {
    _loading.value = false
  }
}

function logout() {
  if (_refreshTimer) clearTimeout(_refreshTimer)
  _clearStorage()
}

// Boot — schedule refresh if we have a stored token
if (_accessToken.value) {
  const secs = _secondsUntilExpiry(_accessToken.value)
  if (secs > 10) {
    _scheduleRefresh()
    fetchUser()
  } else if (_refreshToken.value) {
    _doRefresh().then(ok => { if (!ok) _clearStorage() })
  } else {
    _clearStorage()
  }
}

export function useAuth() {
  return {
    isAuthenticated,
    user,
    accessToken,
    loading,
    authError,
    loginWithPassword,
    loginWithSocial,
    handleCallback,
    logout,
    fetchUser,
  }
}
