/**
 * Auth composable — cookie-based sessions.
 *
 * The backend sets an httpOnly session cookie after login.
 * The browser sends it automatically on every fetch with credentials:'include'.
 * No token ever lives in localStorage or JavaScript memory.
 */

import { ref, computed } from 'vue'
import { API } from '../api/endpoints.js'
import { API_BASE } from '../api/config.js'
import { apiFetch } from './useFetch.js'

const _user    = ref(JSON.parse(sessionStorage.getItem('ta_user') || 'null'))
const _loading = ref(false)
const _error   = ref('')

const isAuthenticated = computed(() => !!_user.value)
const user            = computed(() => _user.value)
const loading         = computed(() => _loading.value)
const authError       = computed(() => _error.value)

async function fetchUser() {
  try {
    const res = await apiFetch(API.me)
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

async function loginWithPassword(email, password, connection = 'Username-Password-Authentication') {
  _loading.value = true
  _error.value   = ''
  try {
    const res = await apiFetch(API.token, {
      method: 'POST',
      body:   JSON.stringify({ email, password, connection }),
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
      ? 'Cannot reach the server. Make sure the API is running.'
      : 'Something went wrong. Please try again.'
    return false
  } finally {
    _loading.value = false
  }
}

function loginWithSocial(connectionName) {
  const url = connectionName
    ? `${API_BASE}/auth/initiate?connection=${encodeURIComponent(connectionName)}`
    : `${API_BASE}/auth/initiate`
  window.location.href = url
}

async function logout() {
  await apiFetch(API.logout, { method: 'POST' })
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
