/**
 * useSkillExecution — handles skill pipeline invocation via SSE.
 *
 * Manages: invoke, reply to interrupts, retry after model update.
 * Emits a reactive `events` stream that the UI can subscribe to.
 */

import { ref, readonly } from 'vue'
import { _readSSEStream } from './useConversations'

export function useSkillExecution() {
  const isStreaming       = ref(false)
  const currentStage      = ref(null)
  const pendingQuestions  = ref([])
  const pendingConfirm    = ref(null)
  const isComplete        = ref(false)
  const isHalted          = ref(false)
  const documentVersion   = ref(0)
  const currentArtifactId = ref(null)
  const executionId       = ref(null)
  const streamError       = ref(null)

  // ── Invoke ────────────────────────────────────────────────────────────────

  async function invoke(conversationId, conversationSkillId, { brief, sourceType } = {}) {
    _resetState()
    isStreaming.value = true

    const response = await fetch(
      `/api/conversations/${conversationId}/skills/${conversationSkillId}/invoke`,
      {
        method:      'POST',
        credentials: 'include',
        headers:     { 'Content-Type': 'application/json' },
        body:        JSON.stringify({ brief: brief || '', source_type: sourceType || 'brief' }),
      }
    )

    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      isStreaming.value = false
      throw Object.assign(new Error(body.detail || `HTTP ${response.status}`), { body })
    }

    executionId.value = response.headers.get('X-Execution-Id')
    await _consumeStream(response.body)
  }

  // ── Reply to interrupt ────────────────────────────────────────────────────

  async function reply(answers) {
    if (!executionId.value) throw new Error('No active execution to reply to.')
    _clearInterrupt()
    isStreaming.value = true

    const response = await fetch(`/api/executions/${executionId.value}/reply`, {
      method:      'POST',
      credentials: 'include',
      headers:     { 'Content-Type': 'application/json' },
      body:        JSON.stringify({ answers }),
    })

    if (!response.ok) throw new Error(`Reply failed: ${response.status}`)
    await _consumeStream(response.body)
  }

  // ── Retry ─────────────────────────────────────────────────────────────────

  async function retry() {
    if (!executionId.value) throw new Error('No execution to retry.')
    _resetState()
    isStreaming.value = true

    const response = await fetch(`/api/executions/${executionId.value}/retry`, {
      method:      'POST',
      credentials: 'include',
    })

    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      isStreaming.value = false
      throw Object.assign(new Error(body.detail || `HTTP ${response.status}`), { body })
    }

    await _consumeStream(response.body)
  }

  // ── SSE event handler ─────────────────────────────────────────────────────

  const _handlers = {
    stage_start(e) {
      currentStage.value = e.stage
    },

    token() {
      // handled by caller via onToken callback
    },

    stage_end(e) {
      currentStage.value = null
    },

    document_ready(e) {
      documentVersion.value   = e.version
      currentArtifactId.value = e.artifact_id || null
    },

    review_complete() {
      // emit to caller
    },

    approval_complete() {
      // emit to caller
    },

    confirm_understanding(e) {
      pendingConfirm.value  = e.content
      executionId.value     = e.execution_id || executionId.value
      isStreaming.value     = false
    },

    question(e) {
      pendingQuestions.value = e.questions || []
      executionId.value      = e.execution_id || executionId.value
      isStreaming.value      = false
    },

    done(e) {
      isComplete.value      = e.status === 'complete'
      isHalted.value        = e.status === 'halted'
      documentVersion.value = e.document_version || documentVersion.value
      isStreaming.value     = false
      currentStage.value    = null
    },

    error(e) {
      streamError.value = e.message
      isStreaming.value = false
    },

    provider_error(e) {
      streamError.value = e.message
      isStreaming.value = false
    },
  }

  async function _consumeStream(body, callbacks = {}) {
    for await (const event of _readSSEStream(body)) {
      const handler = _handlers[event.type]
      if (handler) handler(event)
      if (callbacks[event.type]) callbacks[event.type](event)
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  function _resetState() {
    currentStage.value      = null
    pendingQuestions.value  = []
    pendingConfirm.value    = null
    isComplete.value        = false
    isHalted.value          = false
    streamError.value       = null
    documentVersion.value   = 0
    currentArtifactId.value = null
  }

  function _clearInterrupt() {
    pendingQuestions.value = []
    pendingConfirm.value   = null
    streamError.value      = null
  }

  return {
    // State (readonly)
    isStreaming:       readonly(isStreaming),
    currentStage:      readonly(currentStage),
    pendingQuestions:  readonly(pendingQuestions),
    pendingConfirm:    readonly(pendingConfirm),
    isComplete:        readonly(isComplete),
    isHalted:          readonly(isHalted),
    documentVersion:   readonly(documentVersion),
    currentArtifactId: readonly(currentArtifactId),
    executionId:       readonly(executionId),
    streamError:       readonly(streamError),
    // Actions
    invoke,
    reply,
    retry,
  }
}
