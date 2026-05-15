/**
 * Component tests for chat/DiscoveryForm.vue
 *
 * Key behavior:
 *   - Renders one textarea per question (multi-Q layout for ≥2 questions)
 *   - submit() guards: all answers must be non-empty
 *   - The Send button is disabled when any answer is blank OR isStreaming
 *   - Textareas themselves are NOT disabled (only the button is)
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DiscoveryForm from '../../../components/chat/DiscoveryForm.vue'

vi.mock('../../../components/ui/AppButton.vue', () => ({
  default: {
    template: '<button :disabled="disabled"><slot /></button>',
    props:    ['variant', 'disabled'],
  },
}))

const Q = ['What is your use case?', 'Who are the primary users?']

describe('rendering', () => {
  it('renders one textarea per question', () => {
    const w = mount(DiscoveryForm, { props: { questions: Q } })
    expect(w.findAll('textarea')).toHaveLength(2)
  })

  it('shows question labels', () => {
    const w = mount(DiscoveryForm, { props: { questions: Q } })
    expect(w.text()).toContain('What is your use case?')
    expect(w.text()).toContain('Who are the primary users?')
  })

  it('disables the Send button when answers are empty', () => {
    const w = mount(DiscoveryForm, { props: { questions: Q } })
    expect(w.find('button').attributes('disabled')).toBeDefined()
  })

  it('disables the Send button when isStreaming=true even with answers', async () => {
    const w = mount(DiscoveryForm, { props: { questions: Q, isStreaming: true } })
    const tas = w.findAll('textarea')
    await tas[0].setValue('A1')
    await tas[1].setValue('A2')
    expect(w.find('button').attributes('disabled')).toBeDefined()
  })

  it('enables the Send button when all questions have answers', async () => {
    const w = mount(DiscoveryForm, { props: { questions: Q } })
    const tas = w.findAll('textarea')
    await tas[0].setValue('A1')
    await tas[1].setValue('A2')
    expect(w.find('button').attributes('disabled')).toBeUndefined()
  })
})

describe('submit', () => {
  it('emits submit with array of answers when all answered', async () => {
    const w = mount(DiscoveryForm, { props: { questions: Q } })
    const textareas = w.findAll('textarea')
    await textareas[0].setValue('Answer 1')
    await textareas[1].setValue('Answer 2')
    await w.find('button').trigger('click')
    expect(w.emitted('submit')).toBeTruthy()
    expect(w.emitted('submit')[0][0]).toEqual(['Answer 1', 'Answer 2'])
  })

  it('does NOT emit submit when any answer is empty', async () => {
    const w = mount(DiscoveryForm, { props: { questions: Q } })
    await w.findAll('textarea')[0].setValue('A1')
    // second textarea left empty
    await w.find('button').trigger('click')
    expect(w.emitted('submit')).toBeFalsy()
  })

  it('single-question layout: Enter key submits', async () => {
    const w = mount(DiscoveryForm, { props: { questions: ['What is your goal?'] } })
    const ta = w.find('textarea')
    await ta.setValue('To build something great')
    await ta.trigger('keydown', { key: 'Enter' })
    expect(w.emitted('submit')).toBeTruthy()
    expect(w.emitted('submit')[0][0]).toEqual(['To build something great'])
  })
})
