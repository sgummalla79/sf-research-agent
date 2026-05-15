/**
 * Component tests for sidebar/ConversationRow.vue
 *
 * Interaction model:
 *   - Click row → select
 *   - Click ⋮ → opens context menu
 *   - Context menu has Pin, Rename, Delete
 *   - Rename: shows input inline, Enter saves, Escape cancels
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ConversationRow from '../../../components/sidebar/ConversationRow.vue'

const CONV = { id: 'c1', title: 'My Chat', pinned: false, pinned_at: null }

function factory(props = {}) {
  return mount(ConversationRow, {
    props: { conversation: CONV, isActive: false, ...props },
    attachTo: document.body,
  })
}

/** Open the context menu by clicking the ⋮ button. */
async function openMenu(w) {
  // Hover so the button becomes visible, then click
  await w.find('.sb-row').trigger('mouseenter')
  await w.find('.sb-more-btn').trigger('click')
}

beforeEach(() => { document.body.innerHTML = '' })

describe('rendering', () => {
  it('shows conversation title', () => {
    const w = factory()
    expect(w.find('.sb-row-title').text()).toBe('My Chat')
  })

  it('applies active class when isActive=true', () => {
    const w = factory({ isActive: true })
    expect(w.find('.sb-row').classes()).toContain('active')
  })

  it('shows fallback text for conversations with no title', () => {
    const w = factory({ conversation: { ...CONV, title: null } })
    expect(w.find('.sb-row-title').text()).toBe('New conversation')
  })
})

describe('select event', () => {
  it('emits select with conversation id on row click', async () => {
    const w = factory()
    await w.find('.sb-row').trigger('click')
    expect(w.emitted('select')).toBeTruthy()
    expect(w.emitted('select')[0][0]).toBe('c1')
  })
})

describe('context menu', () => {
  it('opens context menu when ⋮ button is clicked', async () => {
    const w = factory()
    await openMenu(w)
    expect(w.find('.sb-ctx-menu').exists()).toBe(true)
  })

  it('emits pin with conversation id when Pin is clicked', async () => {
    const w = factory()
    await openMenu(w)
    const items = w.findAll('.ctx-item')
    // First item is Pin/Unpin
    await items[0].trigger('click')
    expect(w.emitted('pin')).toBeTruthy()
    expect(w.emitted('pin')[0][0]).toBe('c1')
  })

  it('emits delete with conversation when Delete is clicked', async () => {
    const w = factory()
    await openMenu(w)
    await w.find('.ctx-delete').trigger('click')
    expect(w.emitted('delete')).toBeTruthy()
    expect(w.emitted('delete')[0][0]).toMatchObject({ id: 'c1' })
  })
})

describe('inline rename', () => {
  it('shows rename input after clicking Rename in context menu', async () => {
    const w = factory()
    await openMenu(w)
    // Second ctx-item is Rename (first = Pin, second = Rename)
    const items = w.findAll('.ctx-item')
    await items[1].trigger('click')
    expect(w.find('.rename-input').exists()).toBe(true)
  })

  it('emits rename with id and trimmed title on Enter', async () => {
    const w = factory()
    await openMenu(w)
    await w.findAll('.ctx-item')[1].trigger('click')
    const input = w.find('.rename-input')
    await input.setValue('New Title')
    await input.trigger('keydown', { key: 'Enter' })
    expect(w.emitted('rename')).toBeTruthy()
    expect(w.emitted('rename')[0]).toEqual(['c1', 'New Title'])
  })

  it('cancels rename on Escape — hides input', async () => {
    const w = factory()
    await openMenu(w)
    await w.findAll('.ctx-item')[1].trigger('click')
    const input = w.find('.rename-input')
    await input.trigger('keydown.esc')
    expect(w.find('.rename-input').exists()).toBe(false)
  })

  it('does not emit rename when title is unchanged', async () => {
    const w = factory()
    await openMenu(w)
    await w.findAll('.ctx-item')[1].trigger('click')
    const input = w.find('.rename-input')
    // input pre-filled with current title — blur without change
    await input.trigger('blur')
    expect(w.emitted('rename')).toBeFalsy()
  })
})
