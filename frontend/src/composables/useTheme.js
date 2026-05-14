/**
 * Theme composable — per-user accent colour, persisted in app_config.
 *
 * Each theme defines a light-mode and dark-mode hex for --pri.
 * Derived variables (hover tints, sidebar active state, etc.) are
 * computed from the base colour so they always stay in sync.
 *
 * Usage:
 *   const { THEMES, activeThemeId, applyTheme, loadTheme, saveTheme } = useTheme()
 */

import { ref } from 'vue'
import { apiFetch } from './useFetch.js'

export const THEMES = [
  { id: 'default', label: 'Gold',     light: '#b85c2a', dark: '#c97040' },
  { id: 'blue',    label: 'Sky Blue', light: '#0284c7', dark: '#0ea5e9' },
  { id: 'green',   label: 'Green',    light: '#16a34a', dark: '#22c55e' },
  { id: 'purple',  label: 'Purple',   light: '#9333ea', dark: '#a855f7' },
  { id: 'red',     label: 'Red',      light: '#dc2626', dark: '#ef4444' },
  { id: 'mono',    label: 'White',    light: '#222222', dark: '#eeeeee' },
]

const activeThemeId = ref('default')

// ── Helpers ───────────────────────────────────────────────────────────────────

function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  }
}

function luminance({ r, g, b }) {
  // Perceived brightness — determines whether to use white or dark text on buttons
  return (r * 299 + g * 587 + b * 114) / 1000
}

// ── Core apply ────────────────────────────────────────────────────────────────

function applyTheme(themeId, isDark, el = null) {
  const theme = THEMES.find(t => t.id === themeId) ?? THEMES[0]
  const color = isDark ? theme.dark : theme.light
  const { r, g, b } = hexToRgb(color)
  const bright = luminance({ r, g, b }) > 160
  const target = el ?? document.documentElement
  const a = (alpha) => `rgba(${r},${g},${b},${alpha})`

  // Set as inline CSS variables on the target element so they override
  // any scoped component styles regardless of specificity
  target.style.setProperty('--pri',       color)
  target.style.setProperty('--pri-fg',    bright ? '#111111' : '#ffffff')
  target.style.setProperty('--pri-h',     a(isDark ? 0.06 : 0.06))
  target.style.setProperty('--ifocus',    color)
  target.style.setProperty('--sbg',       a(isDark ? 0.12 : 0.08))
  target.style.setProperty('--stx',       color)
  target.style.setProperty('--sbdr',      a(isDark ? 0.28 : 0.25))
  target.style.setProperty('--sb-active', a(isDark ? 0.15 : 0.10))

  activeThemeId.value = themeId
}

// ── Persistence ───────────────────────────────────────────────────────────────

async function loadTheme(isDark, el = null) {
  try {
    const res = await apiFetch('/api/settings/theme')
    if (res.ok) {
      const data = await res.json()
      applyTheme(data.theme || 'default', isDark, el)
    }
  } catch (_) {
    applyTheme('default', isDark, el)
  }
}

async function saveTheme(themeId, isDark, el = null) {
  applyTheme(themeId, isDark, el)
  try {
    await apiFetch('/api/settings/theme', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ theme: themeId }),
    })
  } catch (_) {}
}

// ── Export ────────────────────────────────────────────────────────────────────

export function useTheme() {
  return { THEMES, activeThemeId, applyTheme, loadTheme, saveTheme }
}
