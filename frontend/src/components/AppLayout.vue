<!--
  AppLayout — application shell.

  When settings is closed: sidebar (left) + default slot (right).
  When settings is open: sidebar (left) + SettingsPage (full-page, replaces slot).

  Provides: openSettings(tab?) via inject.
-->
<template>
  <div class="app-shell shell">

    <!-- ── Full-page views — cover the entire shell (no sidebar) ────────────── -->
    <SettingsPage
      v-if="app.view === 'settings'"
      :initial-tab="app.settingsTab"
      @back="app.openChat()"
    />
    <ConfigurationPage
      v-else-if="app.view === 'configuration'"
      @back="app.openChat()"
    />

    <!-- ── Normal layout: sidebar + main ────────────────────────────────────── -->
    <template v-else>
      <ConversationSidebar
        :active-conversation-id="activeConversationId"
        @select="onSelectConversation"
        @new="onNewConversation"
        @delete="onRequestDelete"
      />
      <div class="app-main">
        <slot />
      </div>
    </template>

    <!-- ── Delete confirmation dialog ───────────────────────────────────────── -->
    <ConfirmDialog
      :open="!!deleteTarget"
      :title="`Delete &quot;${deleteTarget?.title || 'Untitled'}&quot;?`"
      body="This cannot be undone."
      confirm-label="Delete"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSidebarStore }      from '../stores/sidebar'
import { useConversationStore } from '../stores/conversation'
import { useAppStore }          from '../stores/app'

import ConversationSidebar from './sidebar/ConversationSidebar.vue'
import SettingsPage        from './SettingsPage.vue'
import ConfigurationPage   from './ConfigurationPage.vue'
import ConfirmDialog       from './ui/ConfirmDialog.vue'

const props = defineProps({
  activeConversationId: { type: String, default: null },
})

const router  = useRouter()
const sidebar = useSidebarStore()
const conv    = useConversationStore()
const app     = useAppStore()

// ── Sidebar events ─────────────────────────────────────────────────────────────
function onSelectConversation(id) {
  app.openChat()
  conv.restore(id)
  router.push('/')
}

function onNewConversation() {
  app.openChat()
  conv.reset()
  sidebar.load()
  router.push('/')
}

// ── Delete flow ────────────────────────────────────────────────────────────────
const deleteTarget = ref(null)

function onRequestDelete(conversation) {
  deleteTarget.value = conversation
}

async function confirmDelete() {
  const c = deleteTarget.value
  deleteTarget.value = null
  await sidebar.remove(c.id)
  if (conv.conversationId === c.id) conv.reset()
}
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg);
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

</style>
