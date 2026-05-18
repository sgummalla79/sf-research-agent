/**
 * useDarkMode — shared dark-mode state.
 *
 * Initialises from localStorage (user preference) falling back to the
 * system prefers-color-scheme.  The ref is module-level so all components
 * share the same value without a Pinia store.
 */

import { ref, watch } from 'vue'

const _STORAGE_KEY = 'pragna-dark-mode'

function _systemPrefersDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function _storedPreference() {
  const v = localStorage.getItem(_STORAGE_KEY)
  if (v === 'true')  return true
  if (v === 'false') return false
  return null   // no stored preference → use system
}

const isDark = ref(_storedPreference() ?? _systemPrefersDark())

// Apply to <html> element so CSS can react with [data-theme] if needed
function _applyClass(dark) {
  document.documentElement.classList.toggle('dark', dark)
  // Mark explicit light choice so the @media fallback doesn't override it
  if (!dark) document.documentElement.setAttribute('data-light', '')
  else        document.documentElement.removeAttribute('data-light')
}

_applyClass(isDark.value)

watch(isDark, (dark) => {
  _applyClass(dark)
  localStorage.setItem(_STORAGE_KEY, String(dark))
})

export function useDarkMode() {
  return { isDark }
}
