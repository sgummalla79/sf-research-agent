<!--
  SkillPalette — command palette triggered by "/" in the chat input.

  Props:   skills[]    — installed skills from /api/skills
  Emits:   @select(skillId)
           @dismiss

  Keyboard: ArrowUp/Down to navigate, Enter to select, Escape to dismiss.
  The palette is rendered above the input by the parent (ChatPage).
-->
<template>
  <div class="palette" @keydown="onKeydown" tabindex="-1" ref="paletteEl">
    <div class="palette-header">
      <span class="palette-title">SKILLS — TYPE TO FILTER</span>
    </div>

    <div v-if="!filtered.length" class="palette-empty">
      No skills match "{{ query }}"
    </div>

    <button
      v-for="(skill, i) in filtered"
      :key="skill.id"
      :class="['palette-row', { active: i === activeIndex }]"
      @click="select(skill)"
      @mouseenter="activeIndex = i"
    >
      <span class="pr-icon">{{ skill.icon || '⚡' }}</span>
      <div class="pr-body">
        <span class="pr-name">{{ skill.name }}</span>
        <span class="pr-desc">{{ skill.description }}</span>
      </div>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  skills: { type: Array,  default: () => [] },
  query:  { type: String, default: '' },
})
const emit = defineEmits(['select', 'dismiss'])

const activeIndex = ref(0)
const paletteEl   = ref(null)

const filtered = computed(() => {
  if (!props.query) return props.skills
  const q = props.query.toLowerCase()
  return props.skills.filter(
    s => s.name.toLowerCase().includes(q) || (s.description || '').toLowerCase().includes(q)
  )
})

watch(filtered, () => { activeIndex.value = 0 })

function select(skill) { emit('select', skill.id) }

function onKeydown(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, filtered.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (filtered.value[activeIndex.value]) select(filtered.value[activeIndex.value])
  } else if (e.key === 'Escape') {
    emit('dismiss')
  }
}

// Focus the palette when mounted for keyboard nav
watch(paletteEl, async (el) => {
  if (el) { await nextTick(); el.focus() }
})
</script>

<style scoped>
.palette { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,.15); overflow: hidden; min-width: 320px; outline: none; }
.palette-header { padding: 8px 14px; border-bottom: 1px solid var(--border); }
.palette-title  { font-size: 10px; font-weight: 700; letter-spacing: .8px; color: var(--muted); }
.palette-empty  { padding: 14px; font-size: 13px; color: var(--muted); text-align: center; }

.palette-row    { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 14px; background: none; border: none; cursor: pointer; text-align: left; transition: background .1s; }
.palette-row.active,
.palette-row:hover { background: var(--surface-2); }

.pr-icon { font-size: 22px; width: 32px; text-align: center; flex-shrink: 0; }
.pr-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.pr-name { font-size: 14px; font-weight: 600; color: var(--text); }
.pr-desc { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
