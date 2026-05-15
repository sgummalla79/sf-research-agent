/**
 * useConversations — conversation CRUD and regular chat messaging.
 *
 * Replaces the session management in useAgentChat.js.
 * Regular chat messages stream via SSE from /api/conversations/{id}/message.
 */

import { ref, readonly } from 'vue'
import { useFetch } from './useFetch'

export function useConversations() {
  const { apiFetch } = useFetch()

  const conversations = ref([])
  const loading       = ref(false)
  const error         = ref(null)

  // ── CRUD ────────────────────────────────────────────────────────────────────

  async function listConversations() {
    loading.value = true
    try {
      const data       = await apiFetch('/api/conversations')
      conversations.value = data.conversations || []
      return conversations.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createConversation({ title, chatProvider, chatModel } = {}) {
    const data = await apiFetch('/api/conversations', {
      method: 'POST',
      body:   JSON.stringify({
        title,
        chat_provider: chatProvider || 'anthropic',
        chat_model:    chatModel    || 'claude-sonnet-4-6',
      }),
    })
    return data
  }

  async function getConversation(conversationId) {
    return apiFetch(`/api/conversations/${conversationId}`)
  }

  async function renameConversation(conversationId, title) {
    return apiFetch(`/api/conversations/${conversationId}`, {
      method: 'PATCH',
      body:   JSON.stringify({ title }),
    })
  }

  async function deleteConversation(conversationId) {
    await apiFetch(`/api/conversations/${conversationId}`, { method: 'DELETE' })
    conversations.value = conversations.value.filter(c => c.id !== conversationId)
  }

  // ── Skills in a conversation ─────────────────────────────────────────────────

  async function addSkillToConversation(conversationId, skillId) {
    return apiFetch(`/api/conversations/${conversationId}/skills`, {
      method: 'POST',
      body:   JSON.stringify({ skill_id: skillId }),
    })
  }

  async function removeSkillFromConversation(conversationId, conversationSkillId) {
    return apiFetch(`/api/conversations/${conversationId}/skills/${conversationSkillId}`, {
      method: 'DELETE',
    })
  }

  async function getSkillConfig(conversationId, conversationSkillId) {
    return apiFetch(`/api/conversations/${conversationId}/skills/${conversationSkillId}/config`)
  }

  async function updateSkillConfig(conversationId, conversationSkillId, agents) {
    return apiFetch(`/api/conversations/${conversationId}/skills/${conversationSkillId}/config`, {
      method: 'PATCH',
      body:   JSON.stringify({ agents }),
    })
  }

  // ── Regular chat SSE ─────────────────────────────────────────────────────────

  /**
   * Send a regular (non-pipeline) chat message. Returns an async generator
   * of parsed SSE events so the caller can handle tokens, errors, done.
   */
  async function* sendChatMessage(conversationId, text, { chatProvider, chatModel } = {}) {
    const response = await fetch(`/api/conversations/${conversationId}/message`, {
      method:      'POST',
      credentials: 'include',
      headers:     { 'Content-Type': 'application/json' },
      body:        JSON.stringify({
        text,
        chat_provider: chatProvider,
        chat_model:    chatModel,
      }),
    })

    if (!response.ok) {
      throw new Error(`Chat message failed: ${response.status}`)
    }

    yield* _readSSEStream(response.body)
  }

  return {
    conversations:          readonly(conversations),
    loading:                readonly(loading),
    error:                  readonly(error),
    listConversations,
    createConversation,
    getConversation,
    renameConversation,
    deleteConversation,
    addSkillToConversation,
    removeSkillFromConversation,
    getSkillConfig,
    updateSkillConfig,
    sendChatMessage,
  }
}

// ── Shared SSE reader ─────────────────────────────────────────────────────────

export async function* _readSSEStream(body) {
  const reader  = body.getReader()
  const decoder = new TextDecoder()
  let   buffer  = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()   // keep incomplete line in buffer

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        yield JSON.parse(line.slice(6))
      } catch {
        // skip malformed lines
      }
    }
  }
}
