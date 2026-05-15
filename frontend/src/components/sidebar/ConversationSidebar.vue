<!--
  ConversationSidebar — organism that reads the sidebar store directly.

  Emits: @select(conversationId), @new, @delete(conversation), @open-settings(tab)
-->
<template>
  <div class="sidebar" :class="{ collapsed: !sidebar.open }" @click.self="closeMenus">

    <!-- ── EXPANDED ─────────────────────────────────────────────────────── -->
    <template v-if="sidebar.open">

      <div class="sb-header">
        <SudarshanChakra :size="22" color="var(--pri)" />
        <span class="sb-app-name">Pragna</span>
        <button class="sb-collapse-btn" @click="sidebar.toggle()" title="Collapse">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="18" height="18">
            <rect x="2" y="2" width="20" height="20" rx="5"/><line x1="9" y1="2" x2="9" y2="22"/>
          </svg>
        </button>
      </div>

      <button class="sb-action-row" @click="$emit('new')">
        <span class="sba-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="16" height="16">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </span>
        <span class="sba-label">New Chat</span>
      </button>

      <div class="sb-action-row sb-section-head">
        <span class="sba-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" width="16" height="16">
            <path d="M17 8h2a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-1v3l-3-3h-3"/>
            <path d="M13 3H4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h1v3l3-3h5a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z"/>
          </svg>
        </span>
        <span class="sba-label">Chats</span>
      </div>

      <div class="sb-list">
        <div v-if="!filteredPinned.length && !filteredRecent.length" class="sb-empty">
          No conversations yet
        </div>

        <!-- Pinned -->
        <template v-if="filteredPinned.length">
          <div class="sb-section-hdr">📌 Pinned</div>
          <ConversationRow
            v-for="c in filteredPinned"
            :key="c.id"
            :conversation="c"
            :is-active="c.id === activeConversationId"
            @select="$emit('select', $event)"
            @pin="handlePin(c)"
            @rename="sidebar.rename($event[0], $event[1])"
            @delete="$emit('delete', $event)"
          />
        </template>

        <!-- Recent -->
        <template v-if="filteredRecent.length">
          <div v-if="filteredPinned.length" class="sb-divider" />
          <div class="sb-section-hdr">Recent</div>
          <ConversationRow
            v-for="c in filteredRecent"
            :key="c.id"
            :conversation="c"
            :is-active="c.id === activeConversationId"
            @select="$emit('select', $event)"
            @pin="handlePin(c)"
            @rename="(id, title) => sidebar.rename(id, title)"
            @delete="$emit('delete', $event)"
          />
        </template>
      </div>

    </template>

    <!-- ── COLLAPSED ─────────────────────────────────────────────────────── -->
    <template v-else>
      <button class="col-icon-btn brand" title="Pragna" @click="sidebar.toggle()">
        <SudarshanChakra :size="20" color="var(--pri)" />
      </button>
      <button class="col-icon-btn" title="New Chat" @click="$emit('new')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="18" height="18">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
      </button>
      <button class="col-icon-btn" title="Chats">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" width="18" height="18">
          <path d="M17 8h2a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-1v3l-3-3h-3"/>
          <path d="M13 3H4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h1v3l3-3h5a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z"/>
        </svg>
      </button>
      <div class="col-spacer" />
    </template>

    <!-- ── Avatar footer — always visible, adapts to collapsed state ─────── -->
    <div class="sb-footer" :class="{ 'sb-footer-collapsed': !sidebar.open }">
      <button class="avatar-btn"
        :class="{ 'avatar-btn-collapsed': !sidebar.open, 'avatar-btn-active': userMenuOpen }"
        @click.stop="userMenuOpen = !userMenuOpen">
        <img v-if="user?.picture?.trim() && !imgError" :src="user.picture" class="avatar-photo"
          @error="imgError = true" />
        <span v-else class="avatar-initials">{{ initials }}</span>
        <div v-if="sidebar.open && user" class="avatar-info">
          <span class="avatar-name">{{ user?.name || user?.email || 'Account' }}</span>
          <span class="avatar-email">{{ user?.email }}</span>
        </div>
      </button>

      <Transition name="um-pop">
        <div v-if="userMenuOpen" class="user-menu" @click.stop>
          <button class="um-item" @click="openSettings('providers')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            Settings
          </button>
          <div class="um-divider" />
          <div class="um-section-label">Appearance</div>

          <button class="um-item" @click="isDark = !isDark">
            <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15">
              <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
            {{ isDark ? 'Light mode' : 'Dark mode' }}
          </button>

          <div class="um-theme-row">
            <button
              v-for="t in THEMES" :key="t.id"
              class="um-swatch"
              :class="{ active: activeThemeId === t.id }"
              :style="{ background: isDark ? t.dark : t.light }"
              :title="t.label"
              @click.stop="pickTheme(t.id)"
            >
              <svg v-if="activeThemeId === t.id" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" width="10" height="10">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </button>
          </div>

          <div class="um-divider" />
          <div class="um-about-row">
            <span class="um-about-app">Pragna</span>
            <span class="um-about-ver">{{ appVersion ? `v${appVersion}` : '' }}</span>
          </div>
          <div class="um-divider" />
          <button class="um-item um-signout" @click="handleLogout">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Sign out
          </button>
        </div>
      </Transition>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSidebarStore }  from '../../stores/sidebar'
import { useAppStore }      from '../../stores/app'
import { useAuth }          from '../../composables/useAuth'
import { THEMES, useTheme } from '../../composables/useTheme'
import { useDarkMode }      from '../../composables/useDarkMode'
import { apiFetch }         from '../../composables/useFetch'
import ConversationRow      from './ConversationRow.vue'
import SudarshanChakra      from '../SudarshanChakra.vue'

const props = defineProps({
  activeConversationId: { type: String, default: null },
})
defineEmits(['select', 'new', 'delete'])

const sidebar = useSidebarStore()

const { user, logout }           = useAuth()
const { activeThemeId, saveTheme } = useTheme()
const { isDark }                 = useDarkMode()

const userMenuOpen = ref(false)
const appVersion   = ref('')
const imgError     = ref(false)

// Injected from AppLayout — opens the settings drawer at a specific tab
const app = useAppStore()

function openSettings(tab) {
  userMenuOpen.value = false
  app.openSettings(tab)
}

function openConfiguration() {
  userMenuOpen.value = false
  app.openConfiguration()
}

function pickTheme(id) {
  saveTheme(id, isDark.value)
}

async function handleLogout() {
  userMenuOpen.value = false
  await logout()
  window.location.href = '/login'
}

function closeMenus() { userMenuOpen.value = false }
onMounted(async () => {
  document.addEventListener('click', closeMenus)
  try {
    const res = await apiFetch('/api/about')
    if (res.ok) appVersion.value = (await res.json()).version || ''
  } catch (_) {}
})
onUnmounted(() => document.removeEventListener('click', closeMenus))

const filteredPinned = computed(() => sidebar.pinned)
const filteredRecent  = computed(() => sidebar.recent)

const initials = computed(() => {
  const name = user.value?.name?.trim() || user.value?.email?.trim() || ''
  if (!name) return '?'
  const parts = name.split(/[\s@]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return parts[0].slice(0, 2).toUpperCase()
})

function handlePin(c) {
  c.pinned ? sidebar.unpin(c.id) : sidebar.pin(c.id)
}
</script>

<style scoped>
/* ── Shell ── */
.sidebar {
  flex-shrink: 0; width: 240px;
  display: flex; flex-direction: column;
  background: var(--bg);
  border-right: 1px solid rgba(128,128,128,0.12);
  height: 100%; overflow: visible;
  transition: width .22s ease;
  position: relative; z-index: 10;
}
.sidebar.collapsed { width: 52px; }

/* ── Header ── */
.sb-header { display: flex; align-items: center; gap: 10px; padding: 13px 10px 8px; flex-shrink: 0; }
.sb-app-name {
  flex: 1; font-size: 22px; font-weight: 700; color: var(--sb-tx);
  font-family: 'Martel', serif; letter-spacing: -0.3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;
}
.sb-collapse-btn {
  width: 28px; height: 28px; flex-shrink: 0; border: none; border-radius: 6px;
  background: transparent; color: var(--sb-muted);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: background .12s, color .12s; padding: 0;
}
.sb-collapse-btn:hover { background: rgba(128,128,128,0.15); color: var(--sb-tx); }

/* ── Action rows ── */
.sb-action-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; margin: 2px 6px; border-radius: 8px;
  cursor: pointer; border: none; background: transparent;
  color: var(--sb-tx); font-size: 13px; font-weight: 500;
  width: calc(100% - 12px); text-align: left;
  transition: background .12s;
}
.sb-action-row:hover { background: var(--sb-hover); }
.sb-section-head { cursor: default; color: var(--sb-muted); font-size: 12px; }
.sb-section-head:hover { background: transparent; }
.sba-icon  { display: flex; align-items: center; color: inherit; flex-shrink: 0; }
.sba-label { }

/* ── List ── */
.sb-list { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 4px 6px 8px; }
.sb-empty    { font-size: 12px; color: var(--sb-muted); padding: 8px 6px; }
.sb-section-hdr {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--sb-muted); padding: 10px 8px 3px;
}
.sb-divider { height: 1px; background: rgba(128,128,128,0.15); margin: 6px 8px; }

/* ── Avatar footer ── */
.sb-footer {
  flex-shrink: 0;
  border-top: 1px solid rgba(128,128,128,0.12);
  padding: 8px;
  position: relative;
}
/* In collapsed mode: no border, no padding — blend with the icon buttons above */
.sb-footer-collapsed {
  border-top: none;
  padding: 4px 0;
  display: flex;
  justify-content: center;
}

.avatar-btn {
  width: 100%; display: flex; align-items: center; gap: 9px;
  padding: 6px 8px; border-radius: 8px; border: none;
  background: transparent; cursor: pointer; color: var(--sb-tx);
  transition: background .13s;
}
.avatar-btn:hover          { background: var(--sb-hover); }
.avatar-btn.avatar-btn-active { background: var(--hover); }
/* Collapsed: same style as col-icon-btn */
.avatar-btn-collapsed {
  width: 40px; height: 40px;
  border-radius: 10px; padding: 0;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--sb-muted);
}
.avatar-btn-collapsed:hover { background: var(--sb-hover); }

.avatar-photo { width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0; object-fit: cover; }
.avatar-initials {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
  background: var(--pri); color: var(--pri-fg);
  font-size: 11px; font-weight: 700; letter-spacing: .02em;
  display: flex; align-items: center; justify-content: center;
  user-select: none;
}
.avatar-info  { display: flex; flex-direction: column; gap: 1px; min-width: 0; text-align: left; }
.avatar-name  { font-size: 13px; font-weight: 600; color: var(--sb-tx); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.avatar-email { font-size: 11px; color: var(--sb-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ── User menu popup ── */
.user-menu {
  position: absolute; bottom: calc(100% + 4px); left: 8px;
  width: calc(100% - 16px);
  background: var(--hover);
  border: 1px solid rgba(128,128,128,0.18);
  border-radius: 12px; padding: 6px;
  box-shadow: 0 16px 48px rgba(0,0,0,.55), 0 0 0 0.5px rgba(255,255,255,.04);
  z-index: 200;
}
/* Collapsed: appear above the avatar, extend right */
.sb-footer-collapsed .user-menu {
  bottom: calc(100% + 4px);
  left: 0;
  width: 220px;
}

.um-divider { height: 1px; background: rgba(128,128,128,0.15); margin: 4px 0; }
.um-section-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); padding: 4px 8px 6px; }

.um-item {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 8px 10px; border: none; border-radius: 7px;
  background: transparent; color: var(--text); font-size: 13px;
  cursor: pointer; text-align: left; transition: background .12s;
}
.um-item:hover   { background: rgba(128,128,128,0.12); }
.um-signout      { color: var(--text); }
.um-signout:hover { background: var(--pri); color: var(--pri-fg); }

.um-theme-row { display: flex; gap: 8px; padding: 4px 10px 8px; justify-content: center; }
.um-swatch {
  width: 18px; height: 18px; border-radius: 50%;
  border: 2px solid transparent; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: transform .15s, border-color .15s; flex-shrink: 0;
}
.um-swatch:hover  { transform: scale(1.2); }
.um-swatch.active { border-color: var(--sb-tx, var(--text)); }
.um-swatch svg    { stroke: rgba(255,255,255,.9); }

.um-about-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 10px; gap: 8px;
}
.um-about-app { font-size: 12px; font-weight: 600; color: var(--muted); }
.um-about-ver { font-size: 11px; color: var(--muted); font-variant-numeric: tabular-nums; }

/* ── Collapsed ── */
.col-icon-btn {
  display: flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; margin: 4px auto 0;
  border: none; border-radius: 10px; background: transparent;
  color: var(--sb-muted); cursor: pointer;
  transition: background .12s, color .12s;
}
.col-icon-btn:hover { background: var(--sb-hover); color: var(--sb-tx); }
.col-icon-btn.brand { margin-top: 10px; color: var(--pri); }
.col-spacer { flex: 1; }


/* ── Transition ── */
.um-pop-enter-active { transition: opacity .15s ease, transform .15s ease; }
.um-pop-leave-active { transition: opacity .1s  ease, transform .1s  ease; }
.um-pop-enter-from   { opacity: 0; transform: translateY(6px); }
.um-pop-leave-to     { opacity: 0; transform: translateY(4px); }
</style>
