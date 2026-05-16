/**
 * Component tests for chat/ChatInput.vue
 *
 * Tests: slash trigger, isPipelineRunning lock, send on Enter,
 *        file upload chip, model picker, clear() expose.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ChatInput from '../../../components/chat/ChatInput.vue'

// happy-dom doesn't implement URL.createObjectURL
global.URL.createObjectURL = vi.fn(() => 'blob:mock')
global.URL.revokeObjectURL = vi.fn()

function factory(props = {}) {
  return mount(ChatInput, {
    global: { plugins: [createPinia()] },
    props: {
      chatModels:        [],
      isPipelineRunning: false,
      isStreaming:       false,
      noProviders:       false,
      ...props,
    },
    attachTo: document.body,
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  document.body.innerHTML = ''
})

describe('slash command palette trigger', () => {
  it('emits show-palette with query when text starts with /', async () => {
    const w = factory()
    const ta = w.find('textarea')
    await ta.setValue('/arch')
    await ta.trigger('input')
    expect(w.emitted('show-palette')).toBeTruthy()
    expect(w.emitted('show-palette')[0]).toEqual(['arch'])
  })

  it('emits hide-palette when text no longer starts with /', async () => {
    const w = factory()
    const ta = w.find('textarea')
    await ta.setValue('/arch')
    await ta.trigger('input')
    await ta.setValue('normal message')
    await ta.trigger('input')
    const events = w.emitted('hide-palette')
    expect(events).toBeTruthy()
    expect(events.length).toBeGreaterThanOrEqual(1)
  })

  it('emits show-palette with empty query for bare /', async () => {
    const w = factory()
    const ta = w.find('textarea')
    await ta.setValue('/')
    await ta.trigger('input')
    expect(w.emitted('show-palette')[0]).toEqual([''])
  })
})

describe('isPipelineRunning', () => {
  it('disables textarea when pipeline is running', () => {
    const w = factory({ isPipelineRunning: true })
    expect(w.find('textarea').attributes('disabled')).toBeDefined()
  })

  it('disables the send button when pipeline is running', () => {
    const w = factory({ isPipelineRunning: true })
    const btn = w.find('button.cb-send')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('disables + button when pipeline is running', () => {
    const w = factory({ isPipelineRunning: true })
    const btn = w.find('button.cb-plus')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('hides model picker and adaptive button when pipeline is running', () => {
    const w = factory({
      isPipelineRunning: true,
      chatModels:        [{ model: 'gpt-4o', display: 'GPT-4o', provider: 'openai', default: true }],
    })
    expect(w.find('.cb-model-btn').exists()).toBe(false)
    expect(w.find('.cb-adaptive-btn').exists()).toBe(false)
  })
})

describe('send button', () => {
  it('is disabled when text is empty', () => {
    const w = factory()
    expect(w.find('button.cb-send').attributes('disabled')).toBeDefined()
  })

  it('is enabled when text is non-empty', async () => {
    const w = factory()
    await w.find('textarea').setValue('hello')
    expect(w.find('button.cb-send').attributes('disabled')).toBeUndefined()
  })

  it('emits submit with text and opts on button click', async () => {
    const w = factory()
    await w.find('textarea').setValue('hello world')
    await w.find('button.cb-send').trigger('click')
    const emitted = w.emitted('submit')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toBe('hello world')
    expect(emitted[0][1]).toMatchObject({ model: expect.any(String), provider: expect.any(String) })
  })

  it('clears textarea after submit', async () => {
    const w = factory()
    const ta = w.find('textarea')
    await ta.setValue('hello')
    await w.find('button.cb-send').trigger('click')
    expect(ta.element.value).toBe('')
  })
})

describe('no providers banner', () => {
  it('shows banner and hides textarea placeholder when noProviders=true', () => {
    const w = factory({ noProviders: true })
    expect(w.find('.cb-no-providers').exists()).toBe(true)
    expect(w.find('textarea').attributes('disabled')).toBeDefined()
  })

  it('emits open-settings when settings link clicked', async () => {
    const w = factory({ noProviders: true })
    await w.find('.cb-np-link').trigger('click')
    expect(w.emitted('open-settings')).toBeTruthy()
  })
})

describe('file chip', () => {
  /** Open the + menu so the hidden file input renders, then return the wrapper. */
  async function openPlusMenu(w) {
    await w.find('.cb-plus').trigger('click')
    await w.vm.$nextTick()
    return w.find('input[type="file"]')
  }

  it('shows chip after a file is set', async () => {
    const w = factory()
    const file  = new File(['content'], 'doc.pdf', { type: 'application/pdf' })
    const input = await openPlusMenu(w)
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    expect(w.find('.cb-file-chip').exists()).toBe(true)
    expect(w.find('.cb-file-chip span').text()).toContain('doc.pdf')
  })

  it('shows upload error for unsupported file type', async () => {
    const w    = factory()
    const file  = new File(['x'], 'file.exe', { type: 'application/octet-stream' })
    const input = await openPlusMenu(w)
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    expect(w.find('.cb-upload-err').text()).toContain('Unsupported')
  })
})

describe('clear() expose', () => {
  it('clears text and hides palette on clear()', async () => {
    const w = factory()
    const ta = w.find('textarea')
    await ta.setValue('/arch')
    await ta.trigger('input')
    w.vm.clear()
    await w.vm.$nextTick()
    expect(ta.element.value).toBe('')
    expect(w.emitted('hide-palette')).toBeTruthy()
  })
})

describe('model picker', () => {
  it('shows model button when chatModels provided and pipeline not running', () => {
    const w = factory({
      chatModels: [{ model: 'claude-sonnet-4-6', display: 'Sonnet 4.6', provider: 'anthropic', default: true }],
    })
    expect(w.find('.cb-model-btn').exists()).toBe(true)
    expect(w.find('.cb-model-btn').text()).toContain('Sonnet 4.6')
  })
})
