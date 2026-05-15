<template>
  <span :class="['app-badge', `app-badge--${variant}`]"><slot /></span>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'default' },  // default | ok | warn | err
})
</script>

<style scoped>
.app-badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.app-badge--default { background: var(--surface-2); color: var(--muted); }
.app-badge--ok      { background: #dcfce7; color: #166534; }
.app-badge--warn    { background: #fef9c3; color: #854d0e; }
.app-badge--err     { background: #fee2e2; color: #991b1b; }
</style>
