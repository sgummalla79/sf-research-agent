<!--
  SkillPalette — command palette triggered by "/" in the chat input.

  Props:   skills[]    — installed skills from /api/skills
  Emits:   @select(skillId)
           @dismiss

  Keyboard: ArrowUp/Down to navigate, Enter to select, Escape to dismiss.
  The palette is rendered above the input by the parent (ChatPage).
-->
<template>
  <div class="palette-shell">

    <!-- Compact skill list -->
    <div class="palette" ref="paletteEl">
      <div class="palette-header">Available skills</div>
      <div class="palette-sep" />
      <div v-if="!filtered.length" class="palette-empty">No skills match "{{ query }}"</div>
      <button
        v-for="(skill, i) in filtered"
        :key="skill.id"
        :class="['palette-row', { active: i === activeIndex }]"
        @click="select(skill)"
        @mouseenter="activeIndex = i; hoveredIndex = i"
        @mouseleave="hoveredIndex = null"
      >
        <img v-if="skillIconUrl(skill.id)" :src="skillIconUrl(skill.id)" class="pr-icon-svg" :alt="skill.name" />
        <span v-else class="pr-icon">{{ skill.icon || '⚡' }}</span>
        <span class="pr-name">{{ skill.name }}</span>
      </button>
    </div>

    <!-- Description panel — only when explicitly hovering -->
    <div v-if="hoveredIndex !== null && filtered[hoveredIndex]?.description" class="palette-desc">
      {{ filtered[hoveredIndex].description }}
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useSkillIcon } from '../../composables/useSkillIcon.js'

const { skillIconUrl } = useSkillIcon()

const props = defineProps({
  skills: { type: Array,  default: () => [] },
  query:  { type: String, default: '' },
})
const emit = defineEmits(['select', 'dismiss'])

const activeIndex  = ref(0)
const hoveredIndex = ref(null)
const paletteEl    = ref(null)

const filtered = computed(() => {
  if (!props.query) return props.skills
  const q = props.query.toLowerCase()
  return props.skills.filter(
    s => s.name.toLowerCase().includes(q) || s.id.toLowerCase().includes(q)
  )
})

watch(filtered, () => { activeIndex.value = 0 })

function select(skill) { emit('select', skill.id) }

// Called by parent (ChatInput) via ref — keyboard nav stays in textarea
function navigateDown() { activeIndex.value = Math.min(activeIndex.value + 1, filtered.value.length - 1) }
function navigateUp()   { activeIndex.value = Math.max(activeIndex.value - 1, 0) }
function selectActive() { if (filtered.value[activeIndex.value]) select(filtered.value[activeIndex.value]) }

defineExpose({ navigateUp, navigateDown, selectActive, filtered })
</script>

<style scoped>
/* Shell: list only — description is absolutely positioned, never in flow */
.palette-shell {
  position: relative;
  display: inline-block;
}

/* Compact list */
.palette {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 -4px 20px rgba(0,0,0,.2);
  overflow: hidden;
  outline: none;
  min-width: 200px;
}

.palette-header {
  padding: 8px 14px 6px;
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em;
  color: var(--muted); cursor: default; user-select: none;
}
.palette-sep   { height: 1px; background: var(--border); margin-bottom: 2px; }
.palette-empty { padding: 10px 14px; font-size: 13px; color: var(--muted); }

.palette-row {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 8px 14px;
  background: none; border: none; cursor: pointer; text-align: left;
  border-radius: 8px;
  transition: background .1s;
}
.palette-row.active,
.palette-row:hover { background: var(--hover); }

.pr-icon     { font-size: 14px; flex-shrink: 0; width: 18px; text-align: center; }
.pr-icon-svg { width: 16px; height: 16px; object-fit: contain; flex-shrink: 0; }
.pr-name { font-size: 13px; font-weight: 500; color: var(--text); white-space: nowrap; }

/* Description panel — absolutely positioned to the right, never shifts layout */
.palette-desc {
  position: absolute;
  left: calc(100% + 8px);
  top: 0;
  width: 280px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 4px 20px rgba(0,0,0,.25);
  font-size: 13px;
  color: var(--text);
  line-height: 1.6;
  z-index: 201;
}
</style>
