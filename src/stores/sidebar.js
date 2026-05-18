/**
 * Sidebar store — owns the conversations list and sidebar UI state.
 *
 * Separate from conversation store because:
 * - The list persists across conversation switches
 * - The active conversation resets; the list never does
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { Api } from '../api/service.js'

export const useSidebarStore = defineStore('sidebar', () => {
  const open    = ref(true)
  const pinned  = ref([])
  const recent  = ref([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const data   = await Api.getConversations()
      pinned.value = data.pinned || []
      recent.value = data.recent || []
    } catch (_) {
    } finally {
      loading.value = false
    }
  }

  async function pin(conversationId) {
    await Api.pinConversation(conversationId)
    await load()
  }

  async function unpin(conversationId) {
    await Api.unpinConversation(conversationId)
    await load()
  }

  async function remove(conversationId) {
    await Api.deleteConversation(conversationId)
    await load()
  }

  async function rename(conversationId, title) {
    if (!title.trim()) return
    await Api.renameConversation(conversationId, title.trim())
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
