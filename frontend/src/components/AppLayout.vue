<!--
  AppLayout — application shell.

  When settings is closed: sidebar (left) + default slot (right).
  When settings is open: sidebar (left) + SettingsPage (full-page, replaces slot).

  Provides: openSettings(tab?) via inject.
-->
<template>
  <div class="app-shell shell">

    <!-- ── Sidebar ──────────────────────────────────────────────────────────── -->
    <ConversationSidebar
      :active-conversation-id="activeConversationId"
      @select="onSelectConversation"
      @new="onNewConversation"
      @delete="onRequestDelete"
    />

    <!-- ── Main area ────────────────────────────────────────────────────────── -->
    <div class="app-main">
      <SettingsPage
        v-if="app.view === 'settings'"
        :initial-tab="app.settingsTab"
        @back="app.openChat()"
      />
      <ConfigurationPage
        v-else-if="app.view === 'configuration'"
        @back="app.openChat()"
      />
      <slot v-else />
    </div>

    <!-- ── Delete confirmation dialog ───────────────────────────────────────── -->
    <Transition name="overlay">
      <div v-if="deleteTarget" class="al-overlay" @click.self="deleteTarget = null" />
    </Transition>
    <Transition name="pop">
      <div v-if="deleteTarget" class="al-dialog">
        <p class="al-dialog-msg">
          Delete "<strong>{{ deleteTarget.title || 'Untitled' }}</strong>"?
          This cannot be undone.
        </p>
        <div class="al-dialog-actions">
          <button class="al-dialog-cancel" @click="deleteTarget = null">Cancel</button>
          <button class="al-dialog-confirm" @click="confirmDelete">Delete</button>
        </div>
      </div>
    </Transition>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useSidebarStore }      from '../stores/sidebar'
import { useConversationStore } from '../stores/conversation'
import { useAppStore }          from '../stores/app'

import ConversationSidebar from './sidebar/ConversationSidebar.vue'
import SettingsPage        from './SettingsPage.vue'
import ConfigurationPage   from './ConfigurationPage.vue'

const props = defineProps({
  activeConversationId: { type: String, default: null },
})

const sidebar = useSidebarStore()
const conv    = useConversationStore()
const app     = useAppStore()

// ── Sidebar events ─────────────────────────────────────────────────────────────
function onSelectConversation(id) {
  app.openChat()
  conv.restore(id)
}

function onNewConversation() {
  app.openChat()
  conv.reset()
  sidebar.load()
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

/* ── Delete dialog ──────────────────────────────────────────────────────────── */
.al-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.35);
  z-index: 400;
}

.al-dialog {
  position: fixed; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px; padding: 24px;
  width: 360px; max-width: calc(100vw - 32px);
  z-index: 500;
  box-shadow: 0 16px 48px rgba(0,0,0,.18);
}
.al-dialog-msg { margin: 0 0 20px; font-size: 14px; color: var(--text); line-height: 1.55; }
.al-dialog-actions { display: flex; justify-content: flex-end; gap: 10px; }

.al-dialog-cancel {
  padding: 8px 16px; border-radius: 8px;
  background: none; border: 1px solid var(--border);
  color: var(--text); cursor: pointer; font-size: 13px; font-weight: 500;
  transition: background .13s;
}
.al-dialog-cancel:hover { background: var(--surface-2); }

.al-dialog-confirm {
  padding: 8px 16px; border-radius: 8px;
  background: #dc2626; border: none;
  color: #fff; cursor: pointer; font-size: 13px; font-weight: 600;
  transition: background .13s;
}
.al-dialog-confirm:hover { background: #b91c1c; }

/* ── Transitions ──────────────────────────────────────────────────────────── */
.overlay-enter-active, .overlay-leave-active { transition: opacity .2s; }
.overlay-enter-from,   .overlay-leave-to     { opacity: 0; }

.pop-enter-active, .pop-leave-active { transition: opacity .15s, transform .15s; }
.pop-enter-from,   .pop-leave-to     { opacity: 0; transform: translate(-50%, -48%) scale(.96); }
</style>
