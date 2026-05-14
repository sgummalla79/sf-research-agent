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
  const fg = bright ? '#111111' : '#ffffff'

  target.style.setProperty('--pri',       color)
  target.style.setProperty('--pri-fg',    fg)
  target.style.setProperty('--pri-h',     a(0.06))
  target.style.setProperty('--ifocus',    color)
  target.style.setProperty('--sbg',       a(isDark ? 0.12 : 0.08))
  target.style.setProperty('--stx',       color)
  target.style.setProperty('--sbdr',      a(isDark ? 0.28 : 0.25))
  target.style.setProperty('--sb-active', a(isDark ? 0.15 : 0.10))
  // User message bubble uses --ub (background) and --uf (text)
  target.style.setProperty('--ub',        color)
  target.style.setProperty('--uf',        fg)

  _updateFavicon(color)
  activeThemeId.value = themeId
}

function _updateFavicon(color) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
  <g stroke="${color}" stroke-width="3.5">
    <polygon fill="none" stroke-linejoin="round"
      points="50,3 60.4,13.2 73.2,9.7 77.5,23 90.3,27.2 87,40.9 97,50 87,59.1 90.3,72.8 77.5,77 73.2,90.3 60.4,86.8 50,97 39.6,86.8 26.8,90.3 22.5,77 9.7,72.8 13,59.1 3,50 13,40.9 9.7,27.2 22.5,23 26.8,9.7 39.6,13.2"/>
    <circle cx="50" cy="50" r="33"/>
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
    <circle cx="50" cy="50" r="16"/>
    <circle cx="50" cy="50" r="8" fill="${color}" fill-opacity="0.2" stroke-width="3.8"/>
  </g>
  <circle cx="50" cy="50" r="4" fill="${color}"/>
</svg>`
  const url = `data:image/svg+xml,${encodeURIComponent(svg)}`
  let link = document.querySelector("link[rel~='icon']")
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.href = url
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
    const res = await apiFetch('/api/settings/theme', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ theme: themeId }),
    })
    if (!res.ok) console.error('[theme] save failed:', res.status, await res.text().catch(() => ''))
  } catch (e) {
    console.error('[theme] save error:', e)
  }
}

// ── Export ────────────────────────────────────────────────────────────────────

export function useTheme() {
  return { THEMES, activeThemeId, applyTheme, loadTheme, saveTheme }
}
