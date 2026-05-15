<template>
  <span :class="['app-spinner', `app-spinner--${size}`]" :style="color ? { borderColor: color, borderTopColor: 'transparent' } : {}" />
</template>

<script setup>
defineProps({
  size:  { type: String, default: 'md' },  // sm | md | lg
  color: { type: String, default: '' },
})
</script>

<style scoped>
.app-spinner {
  display: inline-block;
  border-style: solid;
  border-radius: 50%;
  animation: spin .7s linear infinite;
  border-color: var(--pri);
  border-top-color: transparent;
}
.app-spinner--sm { width: 14px; height: 14px; border-width: 2px; }
.app-spinner--md { width: 20px; height: 20px; border-width: 2px; }
.app-spinner--lg { width: 32px; height: 32px; border-width: 3px; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
