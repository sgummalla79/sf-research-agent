/**
 * App view store — controls which top-level page is shown.
 *
 * view: 'chat' | 'settings' | 'configuration'
 *
 * Any component can import this store directly — no provide/inject needed.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const view        = ref('chat')       // current top-level view
  const settingsTab = ref('providers')  // which tab is active when settings opens

  function openChat()                        { view.value = 'chat' }
  function openSettings(tab = 'providers')   { settingsTab.value = tab; view.value = 'settings' }
  function openSkills()                      { settingsTab.value = 'skills'; view.value = 'settings' }
  function openConfiguration()               { view.value = 'configuration' }

  return { view, settingsTab, openChat, openSettings, openSkills, openConfiguration }
})
