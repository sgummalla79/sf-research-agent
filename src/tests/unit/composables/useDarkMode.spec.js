/**
 * Unit tests for useDarkMode composable.
 * Covers: localStorage persistence, system-preference fallback, class toggling.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

const STORAGE_KEY = 'pragna-dark-mode'

// Reset module between tests so the module-level ref re-initialises
beforeEach(() => {
  vi.resetModules()
  localStorage.clear()
  document.documentElement.classList.remove('dark')
  document.documentElement.removeAttribute('data-light')
})

describe('initial value — localStorage preference', () => {
  it('starts dark when stored preference is "true"', async () => {
    localStorage.setItem(STORAGE_KEY, 'true')
    const { useDarkMode } = await import('../../../composables/useDarkMode')
    const { isDark } = useDarkMode()
    expect(isDark.value).toBe(true)
  })

  it('starts light when stored preference is "false"', async () => {
    localStorage.setItem(STORAGE_KEY, 'false')
    const { useDarkMode } = await import('../../../composables/useDarkMode')
    const { isDark } = useDarkMode()
    expect(isDark.value).toBe(false)
  })
})

describe('initial value — system preference fallback', () => {
  it('follows system dark preference when no localStorage entry', async () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockReturnValue({ matches: true }),
    })
    const { useDarkMode } = await import('../../../composables/useDarkMode')
    const { isDark } = useDarkMode()
    expect(isDark.value).toBe(true)
  })

  it('follows system light preference when no localStorage entry', async () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockReturnValue({ matches: false }),
    })
    const { useDarkMode } = await import('../../../composables/useDarkMode')
    const { isDark } = useDarkMode()
    expect(isDark.value).toBe(false)
  })
})

describe('class application', () => {
  it('adds .dark class to <html> when isDark is true', async () => {
    localStorage.setItem(STORAGE_KEY, 'true')
    await import('../../../composables/useDarkMode')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('removes .dark class from <html> when isDark is false', async () => {
    localStorage.setItem(STORAGE_KEY, 'false')
    await import('../../../composables/useDarkMode')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('sets data-light attribute when isDark is false', async () => {
    localStorage.setItem(STORAGE_KEY, 'false')
    await import('../../../composables/useDarkMode')
    expect(document.documentElement.hasAttribute('data-light')).toBe(true)
  })
})

describe('isDark ref is shared', () => {
  it('returns the same ref from multiple calls', async () => {
    localStorage.setItem(STORAGE_KEY, 'true')
    const { useDarkMode } = await import('../../../composables/useDarkMode')
    const a = useDarkMode()
    const b = useDarkMode()
    expect(a.isDark).toBe(b.isDark)
  })
})
