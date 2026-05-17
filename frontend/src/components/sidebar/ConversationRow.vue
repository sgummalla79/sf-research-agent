<!-- One row in the sidebar — purely presentational, events up -->
<template>
  <div
    class="sb-row"
    :class="{ active: isActive, 'menu-open': menuOpen }"
    @click="!editing && $emit('select', conversation.id)"
  >
    <!-- Rename input -->
    <input
      v-if="editing"
      class="rename-input"
      v-model="editTitle"
      ref="inputEl"
      @blur="saveRename"
      @keydown.enter.prevent="saveRename"
      @keydown.esc="editing = false"
      @click.stop
    />
    <span v-else class="sb-row-title">{{ conversation.title || 'New conversation' }}</span>

    <!-- Context menu trigger -->
    <div v-if="!editing" class="sb-row-menu" @click.stop>
      <button class="sb-more-btn" :class="{ active: menuOpen }" @click="menuOpen = !menuOpen">
        <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
          <circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/>
        </svg>
      </button>
      <div v-if="menuOpen" class="sb-ctx-menu" @click.stop>
        <button class="ctx-item" @click="$emit('pin', conversation.id); menuOpen = false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
          {{ conversation.pinned ? 'Unpin' : 'Pin' }}
        </button>
        <button class="ctx-item" @click="startRename">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          Rename
        </button>
        <div class="ctx-divider" />
        <button class="ctx-item ctx-delete" @click="$emit('delete', conversation); menuOpen = false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
          </svg>
          Delete
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  conversation: { type: Object,  required: true },
  isActive:     { type: Boolean, default: false },
})
const emit = defineEmits(['select', 'pin', 'rename', 'delete'])

const menuOpen  = ref(false)
const editing   = ref(false)
const editTitle = ref('')
const inputEl   = ref(null)

async function startRename() {
  menuOpen.value  = false
  editTitle.value = props.conversation.title || ''
  editing.value   = true
  await nextTick()
  inputEl.value?.focus()
  inputEl.value?.select()
}

function saveRename() {
  editing.value = false
  if (editTitle.value.trim() && editTitle.value !== props.conversation.title) {
    emit('rename', props.conversation.id, editTitle.value.trim())
  }
}
</script>

<style scoped>
.sb-row {
  display: flex; align-items: center;
  padding: 7px 8px; border-radius: 8px;
  cursor: pointer; min-width: 0; gap: 0;
  transition: background .12s;
}
.sb-row:hover    { background: var(--sb-hover); }
.sb-row.active   { background: var(--sb-active); }

.sb-row-title {
  flex: 1; font-size: 14px; color: var(--sb-tx);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;
}
.rename-input {
  flex: 1; font-size: 14px; background: var(--surface-2);
  border: 1px solid var(--border); border-radius: 5px;
  padding: 2px 6px; outline: none; min-width: 0; color: var(--sb-tx);
}

.sb-row-menu { position: relative; flex-shrink: 0; margin-left: 4px; }

.sb-more-btn {
  display: flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border: none; border-radius: 5px;
  background: transparent; color: var(--sb-muted);
  cursor: pointer; opacity: 0;
  transition: opacity .12s, background .12s;
}
.sb-row:hover .sb-more-btn,
.sb-row.menu-open .sb-more-btn,
.sb-more-btn.active { opacity: 1; }
.sb-more-btn:hover,
.sb-more-btn.active { background: var(--hover); color: var(--sb-tx); }

.sb-ctx-menu {
  position: absolute; right: 0; top: calc(100% + 4px);
  width: 164px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 10px;
  box-shadow: 0 8px 28px rgba(0,0,0,.22);
  z-index: 600; padding: 4px 0;
}
.ctx-item {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 8px 12px;
  background: none; border: none; cursor: pointer;
  font-size: 13px; color: var(--text); text-align: left;
  transition: background .1s;
}
.ctx-item:hover { background: var(--hover); }
.ctx-item svg   { flex-shrink: 0; color: var(--muted); }
.ctx-delete     { color: #ef4444; }
.ctx-delete svg { color: #ef4444; }
.ctx-delete:hover { background: rgba(239,68,68,.12); }
.ctx-divider { height: 1px; background: var(--border); margin: 4px 0; }
</style>
