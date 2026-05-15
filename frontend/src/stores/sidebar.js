/**
 * Sidebar store — owns the conversations list and sidebar UI state.
 *
 * Separate from conversation store because:
 * - The list persists across conversation switches
 * - The active conversation resets; the list never does
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiFetch } from '../composables/useFetch'

export const useSidebarStore = defineStore('sidebar', () => {
  const open    = ref(true)
  const pinned  = ref([])
  const recent  = ref([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const res  = await apiFetch('/api/conversations')
      const data = await res.json()
      pinned.value = data.pinned  || []
      recent.value = data.recent  || []
    } catch (_) {
    } finally {
      loading.value = false
    }
  }

  async function pin(conversationId) {
    await apiFetch(`/api/conversations/${conversationId}/pin`, { method: 'POST' })
    await load()
  }

  async function unpin(conversationId) {
    await apiFetch(`/api/conversations/${conversationId}/pin`, { method: 'DELETE' })
    await load()
  }

  async function remove(conversationId) {
    await apiFetch(`/api/conversations/${conversationId}`, { method: 'DELETE' })
    await load()
  }

  async function rename(conversationId, title) {
    if (!title.trim()) return
    await apiFetch(`/api/conversations/${conversationId}`, {
      method: 'PATCH',
      body:   JSON.stringify({ title: title.trim() }),
    })
    await load()
  }

  function toggle() {
    open.value = !open.value
  }

  return {
    open, pinned, recent, loading,
    load, pin, unpin, remove, rename, toggle,
  }
})
