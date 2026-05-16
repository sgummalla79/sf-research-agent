/**
 * Conversation store — owns the active conversation and all pipeline state.
 *
 * Single source of truth for:
 *   - Which conversation is open
 *   - All messages in the chat
 *   - Skill pipeline execution state (stage, questions, completion)
 *   - Streaming state for both regular chat and skill pipeline
 *
 * Actions call the API and update state — no API calls from components.
 */

import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import { apiFetch } from '../composables/useFetch'

const DEFAULT_SKILL = 'architect'

// ── SSE stream reader ─────────────────────────────────────────────────────────

async function* readSSE(body) {
  const reader  = body.getReader()
  const decoder = new TextDecoder()
  let   buffer  = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try { yield JSON.parse(line.slice(6)) } catch { /* skip malformed */ }
    }
  }
}

// ── Store ─────────────────────────────────────────────────────────────────────

export const useConversationStore = defineStore('conversation', () => {
  // ── Identity ───────────────────────────────────────────────────────────────
  const conversationId       = ref(null)
  const executionId          = ref(null)
  const conversationSkillId  = ref(null)   // snapshot id for the active skill
  const conversationTitle    = ref(null)   // set when backend emits session_titled
  const lockedProvider       = ref(null)   // provider locked once first message is sent

  // ── Messages ───────────────────────────────────────────────────────────────
  const messages = ref([])

  // ── Pipeline state ─────────────────────────────────────────────────────────
  const currentStage      = ref(null)
  const isPipelineRunning = ref(false)   // true only during a skill pipeline
  const isStreaming       = ref(false)   // true for chat SSE + pipeline SSE
  const isHalted          = ref(false)
  const isInvalidInput    = ref(false)

  // ── Interrupts ─────────────────────────────────────────────────────────────
  const pendingQuestions    = ref([])
  const pendingConfirmation = ref(null)

  // ── Token usage ────────────────────────────────────────────────────────────
  const sessionUsage = reactive({ input_tokens: 0, output_tokens: 0, cost_usd: 0, breakdown: [], loaded: false })

  // ── Errors ─────────────────────────────────────────────────────────────────
  const error            = ref(null)
  const providerConflict = ref(null)  // { detail, canSmartPick }

  function _friendlyError(msg) {
    if (!msg) return msg
    const low = msg.toLowerCase()
    if (
      low.includes('not_found') || low.includes('not found') ||
      low.includes('no longer available') || low.includes('is not found for api') ||
      low.includes('deprecated') || low.includes('does not exist') ||
      low.includes('model is not available') || low.includes('unsupported')
    ) {
      return 'The selected model is unavailable or no longer supported. Please choose a different model in Settings → Agents.'
    }
    if (low.includes('api key') || low.includes('authentication') || low.includes('unauthorized') || low.includes('invalid_api_key')) {
      return 'Invalid or missing API key. Please check your credentials in Settings → Providers.'
    }
    if (low.includes('quota') || low.includes('rate limit') || low.includes('too many requests')) {
      return 'Rate limit reached. Please wait a moment and try again.'
    }
    // Strip raw JSON blobs that leaked through
    if (msg.includes("{'error':") || msg.includes('{"error":')) {
      return 'An error occurred with the AI provider. Please check your model selection and try again.'
    }
    return msg
  }

  // ── Computed ───────────────────────────────────────────────────────────────
  const hasActiveConversation = computed(() => !!conversationId.value)
  const isInputLocked         = computed(() => isPipelineRunning.value && !pendingQuestions.value.length && !pendingConfirmation.value)

  // ── Message helpers ────────────────────────────────────────────────────────

  function _addMessage(role, content = '', stage = null, type = 'text', extra = {}) {
    const msg = { role, content, stage, type, isStreaming: false, ...extra }
    messages.value.push(msg)
    return messages.value[messages.value.length - 1]
  }

  // ── Reset ──────────────────────────────────────────────────────────────────

  function reset() {
    conversationId.value       = null
    executionId.value          = null
    conversationSkillId.value  = null
    messages.value             = []
    currentStage.value         = null
    isPipelineRunning.value    = false
    isStreaming.value          = false
    isHalted.value             = false
    isInvalidInput.value       = false
    pendingQuestions.value     = []
    pendingConfirmation.value  = null
    error.value                = null
    providerConflict.value     = null
    sessionUsage.input_tokens  = 0
    sessionUsage.output_tokens = 0
    sessionUsage.cost_usd      = 0
    sessionUsage.breakdown     = []
    sessionUsage.loaded        = false
    lockedProvider.value       = null
    conversationTitle.value    = null
  }

  async function _refreshUsage() {
    if (!conversationId.value) return
    try {
      const res  = await apiFetch(`/api/conversations/${conversationId.value}/usage`)
      if (!res.ok) return
      const data = await res.json()
      sessionUsage.input_tokens  = data.totals?.input_tokens  ?? 0
      sessionUsage.output_tokens = data.totals?.output_tokens ?? 0
      sessionUsage.cost_usd      = data.totals?.cost_usd      ?? 0
      sessionUsage.breakdown     = data.breakdown             ?? []
      sessionUsage.loaded        = true
    } catch { /* non-critical */ }
  }

  // ── SSE event dispatcher ───────────────────────────────────────────────────

  function _handleEvent(event, currentMsgHolder) {
    switch (event.type) {

      case 'stage_start': {
        currentStage.value = event.stage
        if (['research', 'review', 'approval'].includes(event.stage)) {
          const typeMap = { research: 'preparing', review: 'reviewing', approval: 'approving' }
          const m = _addMessage('agent', '', event.stage, typeMap[event.stage])
          m.isStreaming = true
          currentMsgHolder.msg = m
        } else {
          currentMsgHolder.msg = null
        }
        break
      }

      case 'token': {
        if (!currentMsgHolder.msg) {
          const m = _addMessage('agent', '', currentStage.value)
          m.isStreaming = true
          currentMsgHolder.msg = m
        }
        currentMsgHolder.msg.content += event.content
        break
      }

      case 'stage_end': {
        if (currentMsgHolder.msg) currentMsgHolder.msg.isStreaming = false
        currentMsgHolder.msg   = null
        currentStage.value     = null
        break
      }

      case 'document_ready': {
        if (currentMsgHolder.msg) {
          currentMsgHolder.msg.isStreaming = false
          currentMsgHolder.msg.type        = 'document'
          currentMsgHolder.msg.content     = ''
          currentMsgHolder.msg.artifactId  = event.artifact_id || null
          currentMsgHolder.msg.docVersion  = event.version
          currentMsgHolder.msg             = null
        }
        currentStage.value = null
        break
      }

      case 'review_complete': {
        if (currentMsgHolder.msg) {
          currentMsgHolder.msg.isStreaming    = false
          currentMsgHolder.msg.type           = 'review_result'
          currentMsgHolder.msg.reviewPassed   = event.passed
          currentMsgHolder.msg.reviewFeedback = event.feedback
          currentMsgHolder.msg.criticalIssues = event.critical_issues || []
          currentMsgHolder.msg                = null
        }
        currentStage.value = null
        break
      }

      case 'approval_complete': {
        if (currentMsgHolder.msg) {
          currentMsgHolder.msg.isStreaming      = false
          currentMsgHolder.msg.type             = 'approval_result'
          currentMsgHolder.msg.approvalStatus   = event.status
          currentMsgHolder.msg.approvalComments = event.comments
          currentMsgHolder.msg.requiredChanges  = event.required_changes || []
          currentMsgHolder.msg                  = null
        }
        currentStage.value = null
        break
      }

      case 'confirm_understanding': {
        if (currentMsgHolder.msg) { currentMsgHolder.msg.isStreaming = false; currentMsgHolder.msg = null }
        pendingConfirmation.value = event.content
        if (event.execution_id) executionId.value = event.execution_id
        break
      }

      case 'question': {
        if (currentMsgHolder.msg) { currentMsgHolder.msg.isStreaming = false; currentMsgHolder.msg = null }
        const qs        = event.questions || []
        const formatted = qs.length === 1 ? qs[0] : qs.map((q, i) => `${i + 1}. ${q}`).join('\n\n')
        _addMessage('agent', formatted, 'discovery')
        pendingQuestions.value = qs
        if (event.execution_id) executionId.value = event.execution_id
        break
      }

      case 'done': {
        if (currentMsgHolder.msg) { currentMsgHolder.msg.isStreaming = false; currentMsgHolder.msg = null }
        currentStage.value      = null
        isPipelineRunning.value = false
        if (event.status === 'halted')             isHalted.value       = true
        else if (event.status === 'invalid_input') isInvalidInput.value = true
        break
      }

      case 'session_titled': {
        conversationTitle.value = event.title
        break
      }

      case 'error': {
        if (currentMsgHolder.msg) { currentMsgHolder.msg.isStreaming = false; currentMsgHolder.msg = null }
        error.value             = _friendlyError(event.message)
        isPipelineRunning.value = false
        isStreaming.value       = false
        break
      }

      case 'provider_error': {
        currentMsgHolder.msg    = null
        providerConflict.value  = { detail: _friendlyError(event.message), canSmartPick: event.can_smart_pick }
        isPipelineRunning.value = false
        isStreaming.value       = false
        break
      }
    }
  }

  async function _consumeStream(response) {
    isStreaming.value = true
    const holder      = { msg: null }
    try {
      for await (const event of readSSE(response.body)) {
        _handleEvent(event, holder)
      }
    } finally {
      isStreaming.value = false
      if (holder.msg) holder.msg.isStreaming = false
      await _refreshUsage()
    }
  }

  // ── Ensure conversation exists ─────────────────────────────────────────────

  async function _ensureConversation(chatProvider = 'anthropic', chatModel = 'claude-sonnet-4-6') {
    if (conversationId.value) return conversationId.value

    const res  = await apiFetch('/api/conversations', {
      method: 'POST',
      body:   JSON.stringify({ chat_provider: chatProvider, chat_model: chatModel }),
    })
    const data = await res.json()
    conversationId.value = data.id
    lockedProvider.value = chatProvider
    return data.id
  }

  // ── Regular chat ───────────────────────────────────────────────────────────

  async function sendMessage(text, opts = {}) {
    error.value           = null
    providerConflict.value = null

    await _ensureConversation(opts.chatProvider, opts.chatModel)
    _addMessage('user', text)

    const response = await apiFetch(`/api/conversations/${conversationId.value}/message`, {
      method: 'POST',
      body:   JSON.stringify({
        text,
        chat_provider: opts.chatProvider,
        chat_model:    opts.chatModel,
      }),
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      error.value = _friendlyError(err.detail) || 'Message failed.'
      return
    }

    await _consumeStream(response)
  }

  // ── Skill invocation ───────────────────────────────────────────────────────

  function addLocalMessage(role, content) {
    _addMessage(role, content, null, 'text')
  }

  async function invokeSkill(skillId, brief = '', opts = {}) {
    error.value            = null
    providerConflict.value = null
    isHalted.value         = false
    isInvalidInput.value   = false

    await _ensureConversation(opts.chatProvider, opts.chatModel)

    // Add skill to conversation (creates snapshot) — idempotent via UI tracking
    const addRes  = await apiFetch(`/api/conversations/${conversationId.value}/skills`, {
      method: 'POST',
      body:   JSON.stringify({ skill_id: skillId }),
    })

    if (!addRes.ok) {
      const err = await addRes.json().catch(() => ({}))
      // Model not configured → surface as provider conflict
      if (addRes.status === 422 && err.detail?.error === 'model_not_configured') {
        providerConflict.value = { detail: err.detail.message, canSmartPick: true, agents: err.detail.agents }
        return
      }
      error.value = err.detail || 'Could not add skill.'
      return
    }

    const addData          = await addRes.json()
    conversationSkillId.value = addData.conversation_skill_id

    // Show original message in UI (with /skill tokens); backend stores it too
    const displayMsg = opts.originalMessage || brief
    if (displayMsg.trim()) _addMessage('user', displayMsg)

    isPipelineRunning.value = true
    currentStage.value      = null

    const invokeRes = await apiFetch(
      `/api/conversations/${conversationId.value}/skills/${conversationSkillId.value}/invoke`,
      {
        method: 'POST',
        body:   JSON.stringify({
          brief:            brief,
          original_message: opts.originalMessage || '',
          source_type:      opts.sourceType || 'brief',
          uploaded_file_path:  opts.uploadedFilePath  || '',
          uploaded_image_path: opts.uploadedImagePath || '',
          raw_document_text:   opts.rawDocumentText   || '',
        }),
      }
    )

    const eid = invokeRes.headers.get('X-Execution-Id')
    if (eid) executionId.value = eid

    if (!invokeRes.ok) {
      const err = await invokeRes.json().catch(() => ({}))
      if (invokeRes.status === 422 && err.detail?.error === 'model_not_configured') {
        providerConflict.value  = { detail: err.detail.message, canSmartPick: true }
        isPipelineRunning.value = false
        return
      }
      error.value             = err.detail || 'Could not invoke skill.'
      isPipelineRunning.value = false
      return
    }

    await _consumeStream(invokeRes)
  }

  // ── File upload then invoke ────────────────────────────────────────────────

  async function uploadAndInvoke(file, skillId = DEFAULT_SKILL, opts = {}) {
    error.value = null

    const formData = new FormData()
    formData.append('file', file)

    _addMessage('user', `Uploaded: ${file.name}`)

    const uploadRes = await apiFetch('/api/uploads', { method: 'POST', body: formData })
    if (!uploadRes.ok) {
      const err = await uploadRes.json().catch(() => ({ detail: 'Upload failed' }))
      error.value = err.detail || 'Upload failed.'
      return
    }

    const upload = await uploadRes.json()
    await invokeSkill(skillId, '', { ...opts, ...upload })
  }

  // ── Reply to interrupts ────────────────────────────────────────────────────

  async function sendReply(answers) {
    if (!executionId.value) return
    const qs            = pendingQuestions.value
    pendingQuestions.value = []

    const userText = qs.length === 1
      ? answers[0]
      : qs.map((q, i) => `**Q${i + 1}:** ${q}\n**A:** ${answers[i] || '—'}`).join('\n\n')
    _addMessage('user', userText)

    const response = await apiFetch(`/api/executions/${executionId.value}/reply`, {
      method: 'POST',
      body:   JSON.stringify({ answers }),
    })
    await _consumeStream(response)
  }

  async function confirmUnderstanding(correction = '') {
    if (!executionId.value) return
    pendingConfirmation.value = null
    _addMessage('user', correction.trim() ? `Correction: ${correction.trim()}` : 'Confirmed — looks right.')

    const response = await apiFetch(`/api/executions/${executionId.value}/reply`, {
      method: 'POST',
      body:   JSON.stringify({ answers: [correction.trim()] }),
    })
    await _consumeStream(response)
  }

  // ── Retry ──────────────────────────────────────────────────────────────────

  async function retryExecution() {
    if (!executionId.value || isStreaming.value) return
    error.value            = null
    providerConflict.value = null
    messages.value         = messages.value.filter(m => !m.isStreaming)

    const response = await apiFetch(`/api/executions/${executionId.value}/retry`, { method: 'POST' })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      if (response.status === 409) {
        providerConflict.value = { detail: data.detail, canSmartPick: data.can_smart_pick }
        return
      }
      error.value = data.detail || 'Retry failed.'
      return
    }
    isPipelineRunning.value = true
    await _consumeStream(response)
  }

  // ── Restore conversation ───────────────────────────────────────────────────

  async function restore(convId) {
    reset()
    conversationId.value = convId

    const res  = await apiFetch(`/api/conversations/${convId}`)
    if (!res.ok) { error.value = 'Conversation not found.'; return }

    const data = await res.json()

    lockedProvider.value = data.chat_provider || null

    // Rebuild messages from DB — only visible ones
    for (const m of (data.messages || [])) {
      if (m.message_state !== 'visible') continue
      const role = m.role === 'user' ? 'user' : 'agent'

      if (m.message_type === 'artifact_ref' && m.artifact_id) {
        _addMessage(role, '', 'research', 'document', {
          artifactId: m.artifact_id,
          docVersion: null,
        })
        continue
      }

      // Determine stage from execution_id presence + message_type
      const stage = m.message_type === 'stage_summary' ? 'research'
                  : m.message_type === 'question'       ? 'discovery'
                  : null
      _addMessage(role, m.content || '', stage, 'text')
    }

    // Load token usage for this conversation
    _refreshUsage()

    // Detect pending interrupt from skills
    // (If a skill was active when restored, the execution table has running status)
    // For now, rely on frontend state — the pipeline will be resumable via /retry
    // if the user had a mid-run session.
  }

  return {
    // State
    conversationId, executionId, conversationSkillId, conversationTitle, lockedProvider,
    messages, currentStage,
    isPipelineRunning, isStreaming,
    isHalted, isInvalidInput,
    pendingQuestions, pendingConfirmation,
    error, providerConflict,
    sessionUsage,
    // Computed
    hasActiveConversation, isInputLocked,
    // Actions
    reset,
    addLocalMessage,
    sendMessage,
    invokeSkill,
    uploadAndInvoke,
    sendReply,
    confirmUnderstanding,
    retryExecution,
    restore,
  }
})
