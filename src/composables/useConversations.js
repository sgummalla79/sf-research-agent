/**
 * useConversations — conversation CRUD and regular chat messaging via SSE.
 */

import { ref, readonly } from 'vue'
import { Api } from '../api/service.js'
import { _readSSEStream } from './useFetch.js'

export function useConversations() {
  const conversations = ref([])
  const loading       = ref(false)
  const error         = ref(null)

  async function listConversations() {
    loading.value = true
    try {
      const data = await Api.getConversations()
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
    return Api.createConversation({ title, chat_provider: chatProvider, chat_model: chatModel })
  }

  async function getConversation(conversationId) {
    return Api.getConversation(conversationId)
  }

  async function renameConversation(conversationId, title) {
    return Api.renameConversation(conversationId, title)
  }

  async function deleteConversation(conversationId) {
    await Api.deleteConversation(conversationId)
    conversations.value = conversations.value.filter(c => c.id !== conversationId)
  }

  async function addSkillToConversation(conversationId, skillId) {
    return Api.addSkill(conversationId, skillId)
  }

  async function removeSkillFromConversation(conversationId, conversationSkillId) {
    return Api.removeSkill(conversationId, conversationSkillId)
  }

  async function getSkillConfig(conversationId, conversationSkillId) {
    return Api.getSkillConfig(conversationId, conversationSkillId)
  }

  async function updateSkillConfig(conversationId, conversationSkillId, agents) {
    return Api.saveSkillConfig(conversationId, conversationSkillId, agents)
  }

  async function* sendChatMessage(conversationId, text, { chatProvider, chatModel } = {}) {
    const response = await Api.sendMessage(conversationId, {
      text,
      chat_provider: chatProvider,
      chat_model:    chatModel,
    })
    if (!response.ok) throw new Error(`Chat message failed: ${response.status}`)
    yield* _readSSEStream(response.body)
  }

  return {
    conversations: readonly(conversations),
    loading:       readonly(loading),
    error:         readonly(error),
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
