/**
 * Unit tests for the app Pinia store.
 * Covers: view transitions, settings tab tracking, openChat/openSettings/openConfiguration.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia }       from 'pinia'
import { useAppStore }                       from '../../../stores/app'

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('initial state', () => {
  it('starts in chat view', () => {
    const app = useAppStore()
    expect(app.view).toBe('chat')
    expect(app.settingsTab).toBe('providers')
  })
})

describe('openChat()', () => {
  it('sets view to chat', () => {
    const app = useAppStore()
    app.openSettings('agents')
    app.openChat()
    expect(app.view).toBe('chat')
  })
})

describe('openSettings()', () => {
  it('sets view to settings', () => {
    const app = useAppStore()
    app.openSettings()
    expect(app.view).toBe('settings')
  })

  it('stores the requested tab', () => {
    const app = useAppStore()
    app.openSettings('agents')
    expect(app.settingsTab).toBe('agents')
  })

  it('defaults tab to providers when not specified', () => {
    const app = useAppStore()
    app.openSettings()
    expect(app.settingsTab).toBe('providers')
  })

  it('updates tab if called again with different tab', () => {
    const app = useAppStore()
    app.openSettings('agents')
    app.openSettings('usage')
    expect(app.settingsTab).toBe('usage')
    expect(app.view).toBe('settings')
  })
})

describe('openConfiguration()', () => {
  it('sets view to configuration', () => {
    const app = useAppStore()
    app.openConfiguration()
    expect(app.view).toBe('configuration')
  })

  it('switches away from settings when configuration is opened', () => {
    const app = useAppStore()
    app.openSettings('agents')
    app.openConfiguration()
    expect(app.view).toBe('configuration')
  })
})

describe('view transitions', () => {
  it('cycles through all views correctly', () => {
    const app = useAppStore()
    expect(app.view).toBe('chat')

    app.openSettings('providers')
    expect(app.view).toBe('settings')

    app.openConfiguration()
    expect(app.view).toBe('configuration')

    app.openChat()
    expect(app.view).toBe('chat')
  })
})
