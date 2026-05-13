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
body { background: #0f172a; font-family: system-ui, -apple-system, sans-serif; }
</style>
