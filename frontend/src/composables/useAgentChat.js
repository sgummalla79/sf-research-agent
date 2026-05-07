import { ref, reactive } from 'vue'

const API_BASE = '/api/chat'

export function useAgentChat() {
  const sessionId           = ref(null)
  const messages            = ref([])
  const currentStage        = ref(null)
  const pendingQuestions    = ref([])
  const pendingConfirmation = ref(null)
  const isStreaming         = ref(false)
  const isComplete          = ref(false)
  const isHalted            = ref(false)
  const isInvalidInput      = ref(false)
  const error               = ref(null)

  // Document panel
  const documentPanel = reactive({ open: false, content: '', version: 0, loading: false })

  // Sidebar
  const sidebar = reactive({
    open:    true,
    pinned:  [],
    recent:  [],
    loading: false,
  })

  // ── Helpers ───────────────────────────────────────────────────────────────

  function _addMessage(role, content = '', stage = null, type = 'text') {
    const msg = reactive({ role, content, stage, type, isStreaming: false })
    messages.value.push(msg)
    return msg
  }

  // ── SSE stream reader ─────────────────────────────────────────────────────

  async function _readStream(response) {
    const reader  = response.body.getReader()
    const decoder = new TextDecoder()
    let   buffer  = ''
    let   currentMsg = null

    isStreaming.value = true
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          let event
          try { event = JSON.parse(line.slice(6)) } catch { continue }
          _handleEvent(event, currentMsg, m => { currentMsg = m })
        }
      }
    } finally {
      isStreaming.value = false
    }
  }

  function _handleEvent(event, currentMsg, setCurrentMsg) {
    switch (event.type) {

      case 'stage_start': {
        currentStage.value = event.stage
        if (['researcher', 'reviewer', 'approver'].includes(event.stage)) {
          const typeMap = { researcher: 'preparing', reviewer: 'reviewing', approver: 'approving' }
          const m = _addMessage('agent', event.stage === 'researcher' ? 'Preparing your architecture document…' : '', event.stage, typeMap[event.stage])
          m.isStreaming = true
          setCurrentMsg(m)
        } else {
          setCurrentMsg(null)
        }
        break
      }

      case 'token': {
        if (!currentMsg) {
          const m = _addMessage('agent', '', currentStage.value)
          m.isStreaming = true
          setCurrentMsg(m)
          currentMsg = m
        }
        currentMsg.content += event.content
        break
      }

      case 'stage_end': {
        if (currentMsg) currentMsg.isStreaming = false
        setCurrentMsg(null)
        currentStage.value = null
        break
      }

      case 'document_ready': {
        if (currentMsg) {
          currentMsg.isStreaming = false
          currentMsg.type        = 'document'
          currentMsg.content     = ''
          currentMsg.docVersion  = event.version
          currentMsg.docSessionId = event.session_id || sessionId.value
          setCurrentMsg(null)
        }
        currentStage.value = null
        if (!sessionId.value && event.session_id) sessionId.value = event.session_id
        break
      }

      case 'review_complete': {
        if (currentMsg) {
          currentMsg.isStreaming    = false
          currentMsg.type           = 'review_result'
          currentMsg.reviewPassed   = event.passed
          currentMsg.reviewFeedback = event.feedback
          currentMsg.criticalIssues = event.critical_issues || []
          setCurrentMsg(null)
        }
        currentStage.value = null
        break
      }

      case 'approval_complete': {
        if (currentMsg) {
          currentMsg.isStreaming      = false
          currentMsg.type             = 'approval_result'
          currentMsg.approvalStatus   = event.status
          currentMsg.approvalComments = event.comments
          currentMsg.requiredChanges  = event.required_changes || []
          setCurrentMsg(null)
        }
        currentStage.value = null
        break
      }

      case 'confirm_understanding': {
        if (currentMsg) { currentMsg.isStreaming = false; setCurrentMsg(null) }
        pendingConfirmation.value = event.content
        if (!sessionId.value) sessionId.value = event.session_id
        break
      }

      case 'question': {
        if (currentMsg) { currentMsg.isStreaming = false; setCurrentMsg(null) }
        const qs = event.questions || []
        const formatted = qs.length === 1 ? qs[0] : qs.map((q, i) => `${i + 1}. ${q}`).join('\n\n')
        _addMessage('agent', formatted, 'discovery')
        pendingQuestions.value = qs
        if (!sessionId.value) sessionId.value = event.session_id
        break
      }

      case 'done': {
        if (currentMsg) { currentMsg.isStreaming = false; setCurrentMsg(null) }
        currentStage.value = null
        if (event.status === 'complete')      isComplete.value     = true
        else if (event.status === 'halted')   isHalted.value       = true
        else if (event.status === 'invalid_input') isInvalidInput.value = true
        // Refresh sidebar so new session appears / moves to top
        loadSessions()
        break
      }

      case 'error': {
        if (currentMsg) { currentMsg.isStreaming = false; setCurrentMsg(null) }
        error.value = event.message
        break
      }
    }
  }

  // ── Reset ─────────────────────────────────────────────────────────────────

  function _resetChat() {
    sessionId.value           = null
    messages.value            = []
    currentStage.value        = null
    pendingQuestions.value    = []
    pendingConfirmation.value = null
    isStreaming.value         = false
    isComplete.value          = false
    isHalted.value            = false
    isInvalidInput.value      = false
    error.value               = null
    documentPanel.open        = false
    documentPanel.content     = ''
    documentPanel.version     = 0
  }

  // ── Session CRUD ──────────────────────────────────────────────────────────

  async function loadSessions() {
    sidebar.loading = true
    try {
      const res  = await fetch(`${API_BASE}/sessions`)
      const data = await res.json()
      sidebar.pinned = data.pinned  || []
      sidebar.recent = data.recent  || []
    } finally {
      sidebar.loading = false
    }
  }

  function newChat() {
    _resetChat()
  }

  async function pinSession(threadId) {
    const res = await fetch(`${API_BASE}/session/${threadId}/pin`, { method: 'POST' })
    if (!res.ok) {
      const err = await res.json()
      alert(err.detail || 'Could not pin')
      return
    }
    await loadSessions()
  }

  async function unpinSession(threadId) {
    await fetch(`${API_BASE}/session/${threadId}/pin`, { method: 'DELETE' })
    await loadSessions()
  }

  async function deleteSession(threadId) {
    await fetch(`${API_BASE}/session/${threadId}`, { method: 'DELETE' })
    if (sessionId.value === threadId) _resetChat()
    await loadSessions()
  }

  async function renameSession(threadId, title) {
    if (!title.trim()) return
    await fetch(`${API_BASE}/session/${threadId}`, {
      method:  'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ title: title.trim() }),
    })
    await loadSessions()
  }

  async function restoreSession(sid) {
    _resetChat()
    sessionId.value = sid

    const res  = await fetch(`${API_BASE}/session/${sid}/restore`)
    const data = await res.json()
    if (data.error) { error.value = data.error; return }

    for (const m of data.messages) {
      if (m.content?.trim()) _addMessage(m.role, m.content, m.stage || null, 'text')
    }
    if (data.has_document) {
      const card       = _addMessage('agent', '', 'researcher', 'document')
      card.docVersion   = data.document_version
      card.docSessionId = sid
    }
    if (data.pending_confirmation)      pendingConfirmation.value = data.pending_confirmation
    else if (data.pending_questions?.length) {
      const qs = data.pending_questions
      _addMessage('agent', qs.map((q, i) => `${i+1}. ${q}`).join('\n\n'), 'discovery')
      pendingQuestions.value = qs
    } else if (data.current_stage === 'complete') isComplete.value = true
    else if (data.current_stage === 'halted')     isHalted.value   = true
  }

  // ── Sessions API ──────────────────────────────────────────────────────────

  async function startSession(brief) {
    _resetChat()
    _addMessage('user', brief)
    const response = await fetch(`${API_BASE}/start`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brief }),
    })
    const sid = response.headers.get('X-Session-Id')
    if (sid) sessionId.value = sid
    await _readStream(response)
    loadSessions()
  }

  async function uploadDocument(file) {
    _resetChat()
    _addMessage('user', `Uploaded: ${file.name}`)
    const formData = new FormData()
    formData.append('file', file)
    const response = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData })
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }))
      error.value = err.detail || 'Upload failed'; return
    }
    const sid = response.headers.get('X-Session-Id')
    if (sid) sessionId.value = sid
    await _readStream(response)
    loadSessions()
  }

  async function confirmUnderstanding(correction = '') {
    if (!sessionId.value) return
    pendingConfirmation.value = null
    _addMessage('user', correction.trim() ? `Correction: ${correction.trim()}` : 'Confirmed — looks right.')
    const response = await fetch(`${API_BASE}/reply/${sessionId.value}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers: [correction.trim()] }),
    })
    await _readStream(response)
  }

  async function sendReply(answers) {
    if (!sessionId.value) return
    const qs = pendingQuestions.value
    pendingQuestions.value = []
    const userText = qs.length === 1
      ? answers[0]
      : qs.map((q, i) => `**Q${i+1}:** ${q}\n**A:** ${answers[i] || '—'}`).join('\n\n')
    _addMessage('user', userText)
    const response = await fetch(`${API_BASE}/reply/${sessionId.value}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers }),
    })
    await _readStream(response)
  }

  // ── Document panel ────────────────────────────────────────────────────────

  async function openDocumentPanel(sid, version) {
    documentPanel.loading = true
    documentPanel.open    = true
    try {
      const res  = await fetch(`${API_BASE}/document/${sid || sessionId.value}`)
      const data = await res.json()
      documentPanel.content = data.content
      documentPanel.version = data.version ?? version
    } finally {
      documentPanel.loading = false
    }
  }

  function closeDocumentPanel() { documentPanel.open = false }

  function downloadMD() {
    if (!documentPanel.content) return
    const blob = new Blob([documentPanel.content], { type: 'text/markdown' })
    const url  = URL.createObjectURL(blob)
    const a    = Object.assign(document.createElement('a'), { href: url, download: `architecture-v${documentPanel.version}.md` })
    a.click(); URL.revokeObjectURL(url)
  }

  function downloadPDF() {
    if (!documentPanel.content) return
    // Rendered in caller (ChatWindow has access to renderContent)
    // Signal to component — component handles the print window
    documentPanel._triggerPDF = Date.now()
  }

  return {
    sessionId, messages, currentStage,
    pendingQuestions, pendingConfirmation,
    isStreaming, isComplete, isHalted, isInvalidInput, error,
    documentPanel, sidebar,
    // session ops
    loadSessions, newChat, restoreSession,
    pinSession, unpinSession, deleteSession, renameSession,
    // chat ops
    startSession, uploadDocument, confirmUnderstanding, sendReply,
    // doc panel
    openDocumentPanel, closeDocumentPanel, downloadMD, downloadPDF,
  }
}
