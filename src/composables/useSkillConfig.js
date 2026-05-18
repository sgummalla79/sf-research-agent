/**
 * useSkillConfig — manage model config for a conversation skill snapshot.
 *
 * Used on the configure page (/conversations/{id}/skills/{sid}/config).
 * Only `provider` and `model` are editable — prompt content is frozen.
 */

import { ref, readonly } from 'vue'
import { apiFetch } from './useFetch.js'

export function useSkillConfig() {

  const agents  = ref([])
  const loading = ref(false)
  const saving  = ref(false)
  const error   = ref(null)

  async function loadConfig(conversationId, conversationSkillId) {
    loading.value = true
    error.value   = null
    try {
      const data   = await apiFetch(
        `/api/conversations/${conversationId}/skills/${conversationSkillId}/config`
      )
      agents.value = data.agents || []
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function saveConfig(conversationId, conversationSkillId) {
    saving.value = true
    error.value  = null
    try {
      await apiFetch(
        `/api/conversations/${conversationId}/skills/${conversationSkillId}/config`,
        {
          method: 'PATCH',
          body:   JSON.stringify({ agents: agents.value }),
        }
      )
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      saving.value = false
    }
  }

  function updateAgentModel(agentId, provider, model) {
    const agent = agents.value.find(a => a.id === agentId)
    if (agent) {
      agent.provider = provider
      agent.model    = model
    }
  }

  return {
    agents:       readonly(agents),
    loading:      readonly(loading),
    saving:       readonly(saving),
    error:        readonly(error),
    loadConfig,
    saveConfig,
    updateAgentModel,
  }
}
