/**
 * Auth composable — cookie-based sessions.
 *
 * The backend sets an httpOnly session cookie after login.
 * The browser sends it automatically on every fetch with credentials:'include'.
 * No token ever lives in localStorage or JavaScript memory.
 */

import { ref, computed } from 'vue'
import { Api } from '../api/service.js'

const _user    = ref(JSON.parse(sessionStorage.getItem('ta_user') || 'null'))
const _loading = ref(false)
const _error   = ref('')

const isAuthenticated = computed(() => !!_user.value)
const user            = computed(() => _user.value)
const loading         = computed(() => _loading.value)
const authError       = computed(() => _error.value)

async function fetchUser() {
  try {
    const data = await Api.me()
    _user.value = data
    if (data) sessionStorage.setItem('ta_user', JSON.stringify(data))
    else       sessionStorage.removeItem('ta_user')
  } catch {
    _user.value = null
  }
}

async function loginWithPassword(email, password, connection = 'Username-Password-Authentication') {
  _loading.value = true
  _error.value   = ''
  try {
    const data = await Api.login(email, password, connection)
    _user.value = data.user
    sessionStorage.setItem('ta_user', JSON.stringify(data.user))
    return true
  } catch (e) {
    _error.value = e?.message?.includes('fetch')
      ? 'Cannot reach the server. Make sure the API is running.'
      : (e?.message || 'Invalid email or password.')
    return false
  } finally {
    _loading.value = false
  }
}

function loginWithSocial(connectionName) {
  Api.initiateLogin(connectionName)
}

async function logout() {
  await Api.logout()
  _user.value = null
  sessionStorage.removeItem('ta_user')
}

export function useAuth() {
  return { isAuthenticated, user, loading, authError, fetchUser, loginWithPassword, loginWithSocial, logout }
}
