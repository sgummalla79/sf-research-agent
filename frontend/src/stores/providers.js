/**
 * Providers store — shared signal for provider state changes.
 *
 * ProvidersSettings bumps `version` whenever a provider is connected,
 * disconnected, or toggled. Any component that loads provider-dependent
 * data (model lists, agent config) watches `version` and reloads.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useProvidersStore = defineStore('providers', () => {
  const version = ref(0)

  function markUpdated() {
    version.value++
  }

  return { version, markUpdated }
})
