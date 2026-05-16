<!--
  ChatsPage — full conversation list with search.
  Route: /chats
  Layout: AppLayout (sidebar stays visible on the left)
-->
<template>
  <AppLayout>
    <div class="chats-page">

      <div class="cp-header">
        <h1 class="cp-title">Chats</h1>

        <div class="cp-search-wrap">
          <svg class="cp-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.2" width="16" height="16">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            ref="searchEl"
            v-model="q"
            class="cp-search-input"
            placeholder="Search conversations…"
            autocomplete="off"
          />
          <button v-if="q" class="cp-search-clear" @click="q = ''">✕</button>
        </div>
      </div>

      <div class="cp-list">
        <template v-if="filteredPinned.length">
          <div class="cp-section-hdr">📌 Pinned</div>
          <div
            v-for="c in filteredPinned"
            :key="c.id"
            class="cp-item"
            @click="openConversation(c.id)"
          >
            <span class="cp-item-title">{{ c.title || 'New Chat' }}</span>
            <span class="cp-item-date">{{ relTime(c.last_modified) }}</span>
          </div>
        </template>

        <template v-if="filteredRecent.length">
          <div class="cp-section-hdr">Recent</div>
          <div
            v-for="c in filteredRecent"
            :key="c.id"
            class="cp-item"
            @click="openConversation(c.id)"
          >
            <span class="cp-item-title">{{ c.title || 'New Chat' }}</span>
            <span class="cp-item-date">{{ relTime(c.last_modified) }}</span>
          </div>
        </template>

        <div v-if="!filteredPinned.length && !filteredRecent.length" class="cp-empty">
          {{ q ? 'No conversations match your search.' : 'No conversations yet.' }}
        </div>
      </div>

    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useSidebarStore }      from '../stores/sidebar'
import { useConversationStore } from '../stores/conversation'

import AppLayout from '../components/AppLayout.vue'

const router  = useRouter()
const sidebar = useSidebarStore()
const conv    = useConversationStore()

const q        = ref('')
const searchEl = ref(null)

onMounted(async () => {
  await sidebar.load()
  searchEl.value?.focus()
})

const filteredPinned = computed(() => {
  const s = q.value.trim().toLowerCase()
  return s
    ? sidebar.pinned.filter(c => (c.title || 'New Chat').toLowerCase().includes(s))
    : sidebar.pinned
})

const filteredRecent = computed(() => {
  const s = q.value.trim().toLowerCase()
  return s
    ? sidebar.recent.filter(c => (c.title || 'New Chat').toLowerCase().includes(s))
    : sidebar.recent
})

function openConversation(id) {
  conv.restore(id)
  router.push('/')
}

function relTime(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1)   return 'just now'
  if (m < 60)  return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24)  return `${h}h ago`
  const d = Math.floor(h / 24)
  if (d < 7)   return `${d}d ago`
  return new Date(iso).toLocaleDateString()
}
</script>

<style scoped>
.chats-page {
  flex: 1; display: flex; flex-direction: column;
  max-width: 720px; margin: 0 auto; width: 100%;
  padding: 40px 24px 24px;
  box-sizing: border-box;
}

.cp-header {
  display: flex; flex-direction: column; gap: 18px;
  margin-bottom: 24px;
}

.cp-title {
  font-size: 26px; font-weight: 700; color: var(--tx); margin: 0;
}

.cp-search-wrap {
  display: flex; align-items: center; gap: 10px;
  background: var(--surf); border: 1.5px solid var(--bdr);
  border-radius: 12px; padding: 10px 14px;
  transition: border-color .15s;
}
.cp-search-wrap:focus-within { border-color: var(--ifocus); }
.cp-search-icon  { flex-shrink: 0; color: var(--muted); }
.cp-search-input {
  flex: 1; background: none; border: none; outline: none;
  font-size: 15px; color: var(--tx);
}
.cp-search-input::placeholder { color: var(--muted); }
.cp-search-clear {
  background: none; border: none; cursor: pointer;
  color: var(--muted); font-size: 13px; padding: 0;
}
.cp-search-clear:hover { color: var(--tx); }

.cp-list   { display: flex; flex-direction: column; gap: 2px; overflow-y: auto; }

.cp-section-hdr {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--muted);
  padding: 14px 4px 6px;
}

.cp-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px; border-radius: 10px; cursor: pointer;
  transition: background .12s; gap: 12px;
}
.cp-item:hover { background: var(--hover); }

.cp-item-title {
  font-size: 14px; font-weight: 500; color: var(--tx);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  flex: 1; min-width: 0;
}
.cp-item-date {
  font-size: 12px; color: var(--muted); flex-shrink: 0;
}

.cp-empty {
  padding: 40px 0; text-align: center;
  font-size: 14px; color: var(--muted);
}
</style>
