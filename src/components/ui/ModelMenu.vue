<!--
  ModelMenu — flat grouped model picker.

  Shows provider names as dim section headers with models listed directly
  beneath. Checkmark on the left marks the active selection.

  Props:
    groups    Array   — [{ key, label, items: [{ label, value, selected? }] }]
    open      Boolean
    direction 'above' | 'below'

  Events:
    @select(value)
    @close
-->
<template>
  <div v-if="open" class="mm-shell"
    :class="direction === 'below' ? 'mm-below' : 'mm-above'"
    @click.stop>

    <div v-for="(grp, gi) in groups" :key="grp.key">
      <div class="mm-divider" v-if="gi > 0" />
      <div class="mm-provider">{{ grp.label }}</div>
      <div v-for="item in grp.items" :key="item.label"
        class="mm-item"
        @click="select(item.value)">
        <span class="mm-check">
          <svg v-if="item.selected" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
            width="13" height="13">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </span>
        <span class="mm-label">{{ item.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'

const props = defineProps({
  groups:    { type: Array,   required: true },
  open:      { type: Boolean, required: true },
  direction: { type: String,  default: 'above' },
})

const emit = defineEmits(['select', 'close'])

function select(value) {
  emit('select', value)
  emit('close')
}

function onOutsideClick() { emit('close') }

onMounted(()   => document.addEventListener('click', onOutsideClick))
onUnmounted(() => document.removeEventListener('click', onOutsideClick))
</script>

<style scoped>
.mm-shell {
  position: absolute; right: 0;
  z-index: 300;
  background: var(--surf);
  border: 1px solid var(--bdr);
  border-radius: 12px;
  padding: 6px 4px;
  box-shadow: 0 8px 28px rgba(0,0,0,.22);
  min-width: 200px;
}
.mm-above { bottom: calc(100% + 8px); }
.mm-below { top:    calc(100% + 8px); }

.mm-divider {
  height: 1px;
  background: var(--bdr);
  margin: 4px 8px;
}

.mm-provider {
  padding: 6px 12px 2px;
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  letter-spacing: .04em;
  text-transform: none;
  user-select: none;
}

.mm-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px 7px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .1s;
}
.mm-item:hover { background: var(--hover); }

.mm-check {
  width: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--tx);
}

.mm-label {
  font-size: 13px;
  font-weight: 450;
  color: var(--tx);
  white-space: nowrap;
}
</style>
