<!--
  StatusBar — shared bottom dock used by sidebar and main window.

  Defines the single source of truth for the bottom bar height (--status-bar-h).
  Both sidebar footer and main window usage bar sit inside this component,
  ensuring their border-top lines always align horizontally.

  Props:
    justify  'start' | 'end' | 'center'  — flex justify-content (default 'start')

  Usage:
    <StatusBar>               ← sidebar avatar footer
      <AvatarButton />
    </StatusBar>

    <StatusBar justify="end"> ← main window usage bar
      <UsageCells />
    </StatusBar>
-->
<template>
  <div class="status-bar" :class="`status-bar--${justify}`">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  justify: { type: String, default: 'start' },
})
</script>

<style scoped>
.status-bar {
  flex-shrink: 0;
  height: var(--status-bar-h, 60px);
  display: flex; align-items: center;
  border-top: 1px solid var(--border);
  background: var(--bg);
  position: relative;
}

.status-bar--start  { justify-content: flex-start; }
.status-bar--end    { justify-content: flex-end; }
.status-bar--center { justify-content: center; }
</style>
