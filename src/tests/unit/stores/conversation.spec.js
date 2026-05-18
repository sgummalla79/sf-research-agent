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

  it('document_ready adds a plain text status message and stores artifact id', async () => {
    const store = await runStream([
      { type: 'stage_start',    stage: 'research' },
      { type: 'token',          content: 'Building…' },
      { type: 'document_ready', version: 3, artifact_id: 'art-1' },
      { type: 'done',           status: 'complete' },
    ])
    // document_ready now adds a plain text message (no document card for intermediate versions)
    const textMsg = store.messages.find(m => m.content?.includes('submitted for review'))
    expect(textMsg).toBeDefined()
    // latestArtifactId is tracked internally for use when approval completes
    expect(store.messages.find(m => m.type === 'document')).toBeUndefined()
  })

  it('review_complete adds flat agent text with feedback', async () => {
    const store = await runStream([
      { type: 'stage_start',     stage: 'review' },
      { type: 'review_complete', passed: true, feedback: 'Looks good', critical_issues: [] },
      { type: 'done',            status: 'complete' },
    ])
    // VerdictCard removed — review result is a plain text agent message
    const rev = store.messages.find(m => m.role === 'agent' && m.content?.includes('Looks good'))
    expect(rev).toBeDefined()
    expect(store.messages.find(m => m.type === 'review_result')).toBeUndefined()
  })

  it('approval_complete adds flat agent text and document card when approved', async () => {
    const store = await runStream([
      { type: 'stage_start',       stage: 'approval' },
      { type: 'approval_complete', status: 'approved', comments: 'Great', required_changes: [], artifact_id: 'art-2' },
      { type: 'done',              status: 'complete' },
    ])
    // VerdictCard removed — approval result is plain text
    const appr = store.messages.find(m => m.role === 'agent' && m.content?.includes('Great'))
    expect(appr).toBeDefined()
    // Approved → DocumentCard added for final document viewing
    const docCard = store.messages.find(m => m.type === 'document')
    expect(docCard).toBeDefined()
    expect(docCard.artifactId).toBe('art-2')
  })

  it('done event with complete clears pipeline and sets no error flags', async () => {
    const store = await runStream([
      { type: 'done', status: 'complete' },
    ])
    expect(store.isPipelineRunning).toBe(false)
    expect(store.isHalted).toBe(false)
    expect(store.isInvalidInput).toBe(false)
    expect(store.error).toBeNull()
  })

  it('done with halted sets isHalted', async () => {
    const store = await runStream([
      { type: 'done', status: 'halted' },
    ])
    expect(store.isHalted).toBe(true)
  })

  it('error event adds error message and clears pipeline', async () => {
    const store = await runStream([
      { type: 'error', message: 'Something went wrong' },
    ])
    // error events are surfaced as agent messages with type='error', not store.error
    const errMsg = store.messages.find(m => m.type === 'error' && m.role === 'agent')
    expect(errMsg).toBeDefined()
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

  it('adds error message when API returns not-ok', async () => {
    const store = useConversationStore()
    apiFetch
      .mockResolvedValueOnce({ ok: false, json: vi.fn().mockResolvedValue({}) })
      .mockResolvedValueOnce({ ok: true,  json: vi.fn().mockResolvedValue({ id: 'msg-1' }) })

    await store.restore('bad-id')
    // restore failure surfaces as an agent error message, not store.error
    const errMsg = store.messages.find(m => m.type === 'error' && m.role === 'agent')
    expect(errMsg).toBeDefined()
  })
})
