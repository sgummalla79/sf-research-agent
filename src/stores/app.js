/**
 * App view store — controls which top-level page is shown.
 *
 * view: 'chat' | 'settings' | 'configuration'
 *
 * Any component can import this store directly — no provide/inject needed.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { Api } from '../api/service.js'

export const useAppStore = defineStore('app', () => {
  const view        = ref('chat')
  const settingsTab = ref('providers')

  const uploadConfig = ref({
    max_file_size_mb:   10,
    allowed_image_exts: ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
    allowed_doc_exts:   ['.pdf', '.docx', '.doc', '.txt', '.md'],
  })

  async function loadAbout() {
    try {
      const data = await Api.about()
      if (data.upload) uploadConfig.value = data.upload
    } catch (_) {}
  }

  function openChat()                        { view.value = 'chat' }
  function openSettings(tab = 'providers')   { settingsTab.value = tab; view.value = 'settings' }
  function openSkills()                      { settingsTab.value = 'skills'; view.value = 'settings' }
  function openConfiguration()               { view.value = 'configuration' }

  return { view, settingsTab, uploadConfig, loadAbout, openChat, openSettings, openSkills, openConfiguration }
})
