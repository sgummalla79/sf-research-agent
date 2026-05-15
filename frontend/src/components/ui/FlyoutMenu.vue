<!--
  FlyoutMenu — reusable grouped flyout menu.

  Shows a list of groups. Hovering a group opens its items as a flyout to the right.
  Handles hover timing internally so the mouse can cross the gap without closing.

  Props:
    groups    Array  — [{ key, label, items: [{ label, value, selected? }] }]
    open      Boolean — controlled by parent
    direction 'above' | 'below' — which side of the trigger to open toward

  Events:
    @select(value)  — item was clicked; value is whatever was in item.value
    @close          — user clicked outside or selected an item

  Usage:
    <FlyoutMenu
      :groups="modelGroups"
      :open="menuOpen"
      direction="above"
      @select="onSelect"
      @close="menuOpen = false"
    />

  Where modelGroups is:
    [
      {
        key: 'anthropic',
        label: 'Anthropic',
        items: [
          { label: 'Claude Sonnet 4.6', value: modelObj, selected: selectedModel === modelObj }
        ]
      }
    ]
-->
<template>
  <div v-if="open" class="fm-shell"
    :class="direction === 'below' ? 'fm-below' : 'fm-above'"
    @click.stop>
    <div class="fm-groups">
      <div v-for="grp in groups" :key="grp.key"
        class="fm-group-wrap"
        @mouseenter="enterGroup(grp.key)"
        @mouseleave="leaveGroup">

        <div class="fm-group-row" :class="{ active: hovered === grp.key }">
          <span class="fm-group-label">{{ grp.label }}</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2.5" stroke-linecap="round" width="11" height="11">
            <polyline points="9 6 15 12 9 18"/>
          </svg>
        </div>

        <!-- Flyout — absolutely positioned to the right, never shifts the groups panel -->
        <div v-if="hovered === grp.key" class="fm-flyout"
          @mouseenter="enterGroup(grp.key)"
          @mouseleave="leaveGroup">
          <div v-for="item in grp.items" :key="item.label"
            class="fm-item" :class="{ selected: item.selected }"
            @click="select(item.value)">
            <span class="fm-item-label">{{ item.label }}</span>
            <svg v-if="item.selected" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2.5" stroke-linecap="round" width="12" height="12">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  groups:    { type: Array,   required: true },
  open:      { type: Boolean, required: true },
  direction: { type: String,  default: 'above' },  // 'above' | 'below'
})

const emit = defineEmits(['select', 'close'])

const hovered = ref(null)
let   _leaveTimer = null

function enterGroup(key) {
  clearTimeout(_leaveTimer)
  hovered.value = key
}

function leaveGroup() {
  _leaveTimer = setTimeout(() => { hovered.value = null }, 150)
}

function select(value) {
  hovered.value = null
  emit('select', value)
  emit('close')
}

function onOutsideClick() { emit('close') }

onMounted(()   => document.addEventListener('click', onOutsideClick))
onUnmounted(() => { document.removeEventListener('click', onOutsideClick); clearTimeout(_leaveTimer) })
</script>

<style scoped>
.fm-shell {
  position: absolute; right: 0;
  z-index: 300;
}
.fm-above { bottom: calc(100% + 8px); }
.fm-below { top:    calc(100% + 8px); }

/* Groups panel */
.fm-groups {
  background: var(--surf);
  border: 1px solid var(--bdr); border-radius: 12px;
  padding: 4px;
  box-shadow: 0 8px 24px rgba(0,0,0,.18);
  min-width: 140px;
}

/* Each row is a relative container for the flyout */
.fm-group-wrap { position: relative; }

.fm-group-row {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; border-radius: 8px;
  color: var(--tx); font-size: 13px; font-weight: 500;
  cursor: default; transition: background .12s; white-space: nowrap;
}
.fm-group-row.active { background: var(--hover); }
.fm-group-label { flex: 1; }
.fm-group-row svg { color: var(--muted); flex-shrink: 0; }

/* Flyout panel — absolutely positioned to the right */
.fm-flyout {
  position: absolute; left: calc(100% + 6px); top: 0;
  background: var(--surf);
  border: 1px solid var(--bdr); border-radius: 12px;
  padding: 4px;
  box-shadow: 0 8px 24px rgba(0,0,0,.18);
  min-width: 180px;
  z-index: 1;
}

.fm-item {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 8px 12px; border-radius: 8px;
  cursor: pointer; transition: background .12s; white-space: nowrap;
}
.fm-item:hover    { background: var(--hover); }
.fm-item.selected { background: var(--sbg); }
.fm-item-label    { font-size: 13px; font-weight: 500; color: var(--tx); }
.fm-item svg      { color: var(--pri); flex-shrink: 0; }
</style>
