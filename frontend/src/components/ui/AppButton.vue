<template>
  <button
    :class="['app-btn', `app-btn--${variant}`, { 'app-btn--loading': loading }]"
    :disabled="disabled || loading"
    v-bind="$attrs"
  >
    <span v-if="loading" class="app-btn__spinner" />
    <slot />
  </button>
</template>

<script setup>
defineProps({
  variant:  { type: String,  default: 'primary' },  // primary | secondary | ghost | danger
  loading:  { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
</script>

<style scoped>
.app-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: opacity .15s, background .15s;
}
.app-btn:disabled { opacity: .5; cursor: not-allowed; }
.app-btn--primary   { background: var(--pri); color: var(--pri-fg); }
.app-btn--secondary { background: var(--surface-2); color: var(--text); border: 1px solid var(--border); }
.app-btn--ghost     { background: transparent; color: var(--text); }
.app-btn--danger    { background: #ef4444; color: #fff; }
.app-btn__spinner   { width: 14px; height: 14px; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
