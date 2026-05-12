<template>
  <div class="app">
    <ChatWindow />
  </div>
</template>

<script setup>
import ChatWindow from './components/ChatWindow.vue'
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body { background: #0f172a; font-family: system-ui, -apple-system, sans-serif; }
.app { height: 100vh; display: flex; padding: 16px; }
.app > * { flex: 1; min-width: 0; }
</style>
