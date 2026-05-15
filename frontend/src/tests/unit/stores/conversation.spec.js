/**
 * Unit tests for the conversation Pinia store.
 *
 * Focuses on:
 *  - SSE event dispatch (each event type → correct state mutation)
 *  - reset() clears all fields
 *  - isInputLocked computed
 *  - restore() rebuilds messages from API response
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia }           from 'pinia'
import { useConversationStore }                  from '../../../stores/conversation'

// ── SSE stream helpers ────────────────────────────────────────────────────────

/** Build a mock fetch Response whose body yields the given SSE events. */
function mockSseResponse(events, status = 200) {
  const lines = events
    .map(e => `data: ${JSON.stringify(e)}\n\n`)
    .join('')

  const encoder = new TextEncoder()
  const stream  = new ReadableStream({
    start(ctrl) {
      ctrl.enqueue(encoder.encode(lines))
      ctrl.close()
    },
  })

  return {
    ok:     status < 400,
    status,
    body:   stream,
    headers: { get: vi.fn().mockReturnValue(null) },
    json:   vi.fn().mockResolvedValue({}),
  }
}

/** Wait for the store's isStreaming to go false (stream consumed). */
async function drainStream(store) {
  await new Promise(resolve => {
    const stop = setInterval(() => {
      if (!store.isStreaming) { clearInterval(stop); resolve() }
    }, 5)
    setTimeout(() => { clearInterval(stop); resolve() }, 2000)
  })
}

// ── Mock apiFetch ─────────────────────────────────────────────────────────────

vi.mock('../../../composables/useFetch', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../../composables/useFetch'

// ── Tests ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('reset()', () => {
  it('clears all state fields to defaults', () => {
    const store = useConversationStore()
    store.conversationId      = 'abc'
    store.messages            = [{ role: 'user', content: 'hi' }]
    store.isPipelineRunning   = true
    store.pendingQuestions    = ['Q1']
    store.error               = 'oops'

    store.reset()

    expect(store.conversationId).toBeNull()
    expect(store.messages).toEqual([])
    expect(store.isPipelineRunning).toBe(false)
    expect(store.pendingQuestions).toEqual([])
    expect(store.error).toBeNull()
    expect(store.isStreaming).toBe(false)
  })
})

describe('isInputLocked computed', () => {
  it('is false when pipeline is not running', () => {
    const store = useConversationStore()
    expect(store.isInputLocked).toBe(false)
  })

  it('is true when pipeline running and no pending interrupt', () => {
    const store = useConversationStore()
    store.isPipelineRunning = true
    expect(store.isInputLocked).toBe(true)
  })

  it('is false when pipeline running BUT questions are pending', () => {
    const store = useConversationStore()
    store.isPipelineRunning  = true
    store.pendingQuestions   = ['What is your use case?']
    expect(store.isInputLocked).toBe(false)
  })

  it('is false when pipeline running BUT confirmation is pending', () => {
    const store = useConversationStore()
    store.isPipelineRunning    = true
    store.pendingConfirmation  = 'Here is what I understood…'
    expect(store.isInputLocked).toBe(false)
  })
})

describe('SSE event dispatch via sendMessage', () => {
  async function runStream(events) {
    const store = useConversationStore()
    store.conversationId = 'conv-1'

    apiFetch.mockResolvedValueOnce(mockSseResponse(events))

    const p = store.sendMessage('hello', {})
    await drainStream(store)
    await p
    return store
  }

  it('token events accumulate into a message', async () => {
    const store = await runStream([
      { type: 'token', content: 'Hello ' },
      { type: 'token', content: 'world' },
      { type: 'done',  status: 'complete' },
    ])
    const msgs = store.messages.filter(m => m.role === 'agent')
    expect(msgs.length).toBe(1)
    expect(msgs[0].content).toBe('Hello world')
  })

  it('stage_start + stage_end creates and closes a message', async () => {
    const store = await runStream([
      { type: 'stage_start', stage: 'research' },
      { type: 'token',       content: 'Working…' },
      { type: 'stage_end',   stage: 'research' },
      { type: 'done',        status: 'complete' },
    ])
    const msg = store.messages.find(m => m.stage === 'research')
    expect(msg).toBeDefined()
    expect(msg.isStreaming).toBe(false)
    expect(msg.content).toBe('Working…')
  })

  it('question event sets pendingQuestions and adds agent message', async () => {
    const store = await runStream([
      { type: 'question', questions: ['Q1', 'Q2'], execution_id: 'exec-1' },
    ])
    expect(store.pendingQuestions).toEqual(['Q1', 'Q2'])
    expect(store.executionId).toBe('exec-1')
    const discoveryMsg = store.messages.find(m => m.stage === 'discovery')
    expect(discoveryMsg).toBeDefined()
  })

  it('confirm_understanding event sets pendingConfirmation', async () => {
    const store = await runStream([
      { type: 'confirm_understanding', content: 'Here is what I understood', execution_id: 'exec-2' },
    ])
    expect(store.pendingConfirmation).toBe('Here is what I understood')
    expect(store.executionId).toBe('exec-2')
  })

  it('document_ready upgrades message type to document', async () => {
    const store = await runStream([
      { type: 'stage_start',    stage: 'research' },
      { type: 'token',          content: 'Building…' },
      { type: 'document_ready', version: 3, artifact_id: 'art-1' },
      { type: 'done',           status: 'complete' },
    ])
    const docMsg = store.messages.find(m => m.type === 'document')
    expect(docMsg).toBeDefined()
    expect(docMsg.artifactId).toBe('art-1')
    expect(docMsg.docVersion).toBe(3)
  })

  it('review_complete upgrades message to review_result', async () => {
    const store = await runStream([
      { type: 'stage_start',     stage: 'review' },
      { type: 'review_complete', passed: true, feedback: 'Looks good', critical_issues: [] },
      { type: 'done',            status: 'complete' },
    ])
    const rev = store.messages.find(m => m.type === 'review_result')
    expect(rev).toBeDefined()
    expect(rev.reviewPassed).toBe(true)
    expect(rev.reviewFeedback).toBe('Looks good')
  })

  it('approval_complete upgrades message to approval_result', async () => {
    const store = await runStream([
      { type: 'stage_start',       stage: 'approval' },
      { type: 'approval_complete', status: 'approved', comments: 'Great', required_changes: [] },
      { type: 'done',              status: 'complete' },
    ])
    const appr = store.messages.find(m => m.type === 'approval_result')
    expect(appr).toBeDefined()
    expect(appr.approvalStatus).toBe('approved')
  })

  it('done event with complete sets isComplete and clears pipeline', async () => {
    const store = await runStream([
      { type: 'done', status: 'complete' },
    ])
    expect(store.isComplete).toBe(true)
    expect(store.isPipelineRunning).toBe(false)
  })

  it('done with halted sets isHalted', async () => {
    const store = await runStream([
      { type: 'done', status: 'halted' },
    ])
    expect(store.isHalted).toBe(true)
  })

  it('error event sets error and clears pipeline', async () => {
    const store = await runStream([
      { type: 'error', message: 'Something went wrong' },
    ])
    expect(store.error).toBe('Something went wrong')
    expect(store.isPipelineRunning).toBe(false)
  })

  it('provider_error event sets providerConflict', async () => {
    const store = await runStream([
      { type: 'provider_error', message: 'No provider', can_smart_pick: true },
    ])
    expect(store.providerConflict).toEqual({ detail: 'No provider', canSmartPick: true })
    expect(store.isPipelineRunning).toBe(false)
  })
})

describe('restore()', () => {
  it('rebuilds visible messages from API response', async () => {
    const store = useConversationStore()

    apiFetch.mockResolvedValueOnce({
      ok:   true,
      json: vi.fn().mockResolvedValue({
        messages: [
          { role: 'user',      content: 'hello',   message_state: 'visible', message_type: 'chat' },
          { role: 'assistant', content: 'world',   message_state: 'visible', message_type: 'chat' },
          { role: 'assistant', content: 'hidden',  message_state: 'hidden',  message_type: 'chat' },
        ],
      }),
    })

    await store.restore('conv-123')

    expect(store.conversationId).toBe('conv-123')
    expect(store.messages).toHaveLength(2)     // hidden excluded
    expect(store.messages[0].content).toBe('hello')
    expect(store.messages[1].content).toBe('world')
  })

  it('maps artifact_ref messages to document type', async () => {
    const store = useConversationStore()

    apiFetch.mockResolvedValueOnce({
      ok:   true,
      json: vi.fn().mockResolvedValue({
        messages: [
          {
            role: 'assistant', content: null,
            message_state: 'visible', message_type: 'artifact_ref',
            artifact_id: 'art-99',
          },
        ],
      }),
    })

    await store.restore('conv-abc')
    expect(store.messages[0].type).toBe('document')
    expect(store.messages[0].artifactId).toBe('art-99')
  })

  it('sets error when API returns not-ok', async () => {
    const store = useConversationStore()
    apiFetch.mockResolvedValueOnce({ ok: false, json: vi.fn().mockResolvedValue({}) })

    await store.restore('bad-id')
    expect(store.error).toBeTruthy()
  })
})
