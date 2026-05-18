/**
 * Component tests for chat/MessageBubble.vue
 *
 * Tests: routing to correct sub-component based on msg.type,
 *        text rendering with markdown, streaming cursor.
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageBubble from '../../../components/chat/MessageBubble.vue'

// Stub heavy child component so tests focus on routing logic
vi.mock('../../../components/chat/DocumentCard.vue', () => ({
  default: { template: '<div class="stub-doc" />', props: ['artifactId', 'docVersion'] },
}))

function factory(msg) {
  return mount(MessageBubble, { props: { msg } })
}

describe('text messages', () => {
  it('renders user bubble with content', () => {
    const w = factory({ role: 'user', content: 'Hello', type: 'text', isStreaming: false })
    expect(w.find('.bubble').exists()).toBe(true)
    expect(w.text()).toContain('Hello')
    expect(w.classes()).toContain('user')
  })

  it('renders agent message flat (no bubble) for agent role', () => {
    const w = factory({ role: 'agent', content: 'Hi there', type: 'text', isStreaming: false })
    expect(w.classes()).toContain('agent')
    expect(w.find('.agent-wrap').exists()).toBe(true)
    expect(w.find('.bubble').exists()).toBe(false)
  })

  it('shows streaming cursor when isStreaming=true', () => {
    const w = factory({ role: 'agent', content: 'typing…', type: 'text', isStreaming: true })
    expect(w.find('.cursor').exists()).toBe(true)
  })

  it('hides streaming cursor when isStreaming=false', () => {
    const w = factory({ role: 'agent', content: 'done', type: 'text', isStreaming: false })
    expect(w.find('.cursor').exists()).toBe(false)
  })

  it('renders agent message flat without stage label', () => {
    const w = factory({ role: 'agent', content: 'output', type: 'text', stage: 'research', isStreaming: false })
    expect(w.find('.stage-tag').exists()).toBe(false)
    expect(w.find('.agent-wrap').exists()).toBe(true)
  })
})

describe('document messages', () => {
  it('renders DocumentCard stub for type=document', () => {
    const w = factory({ role: 'agent', type: 'document', artifactId: 'art-1', docVersion: 2, isStreaming: false })
    expect(w.find('.stub-doc').exists()).toBe(true)
  })
})

describe('legacy status message types (StatusCard removed)', () => {
  it('suppresses rendering for type=preparing', () => {
    const w = factory({ role: 'agent', type: 'preparing', content: '', isStreaming: true })
    // StatusCard removed — preparing messages render nothing
    expect(w.find('.message').exists()).toBe(false)
  })

  it('suppresses rendering for type=reviewing', () => {
    const w = factory({ role: 'agent', type: 'reviewing', content: '', isStreaming: true })
    expect(w.find('.message').exists()).toBe(false)
  })
})

describe('review / approval result messages (VerdictCard removed)', () => {
  it('renders review_result as flat agent message', () => {
    const w = factory({
      role: 'agent', type: 'review_result',
      reviewPassed: true, reviewFeedback: 'Good', criticalIssues: [], isStreaming: false,
    })
    expect(w.find('.agent-wrap').exists()).toBe(true)
    expect(w.find('.stub-verdict').exists()).toBe(false)
  })

  it('renders approval_result as flat agent message', () => {
    const w = factory({
      role: 'agent', type: 'approval_result',
      approvalStatus: 'approved', approvalComments: 'Done', requiredChanges: [], isStreaming: false,
    })
    expect(w.find('.agent-wrap').exists()).toBe(true)
    expect(w.find('.stub-verdict').exists()).toBe(false)
  })
})
