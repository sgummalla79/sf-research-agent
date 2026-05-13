<template>
  <RouterView />
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useAuth } from './composables/useAuth.js'

const { fetchUser } = useAuth()

// Restore session from httpOnly cookie on every page load
onMounted(fetchUser)
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, #app { height: 100%; }
body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #1a1a1a;   /* neutral dark — matches chat dark theme */
}
@media (prefers-color-scheme: light) {
  body { background: #f5f5f4; }
}
</style>
