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

/* ── Light mode ── */
:root {
  --bg:        #f5f5f4;
  --surface:   #ffffff;
  --surface-2: #f0efee;
  --border:    #e5e5e3;
  --text:      #1a1a1a;
  --muted:     #737373;
  --hover:     #ebebea;
  --ifocus:    #b85c2a;
  --pri:       #b85c2a;
  --pri-fg:    #ffffff;
  --sbg:       rgba(184,92,42,0.08);
  --stx:       #9a4a1e;
  --sbdr:      rgba(184,92,42,0.25);
  --danger:    #ef4444;
  --danger-h:  rgba(239,68,68,0.1);
  --pass-bg:   #f0fdf4; --pass-tx: #15803d;
  --fail-bg:   #fef2f2; --fail-tx: #b91c1c;
  --draft-bg:  #fef3c7; --draft-tx: #92400e;
  /* Sidebar-specific (now same bg as main, hover/active relative to --bg) */
  --sb-bg:     #f5f5f4;
  --sb-hover:  #ebebea;
  --sb-active: rgba(184,92,42,0.1);
  --sb-tx:     #1a1a1a;
  --sb-muted:  #737373;
  /* Aliases for legacy components */
  --tx:    var(--text);
  --surf:  var(--surface);
  --surf2: var(--surface-2);
  --bdr:   var(--border);
  --inp:   var(--surface-2);
}

/* ── Dark mode — via html.dark class set by useDarkMode ── */
/*
   Two background colors only:
     Ink  #1a1a1a  — base layer (sidebar, main canvas, inset inputs)
     Ash  #282828  — elevated layer (menus, modals, panels, cards, hover)
*/
html.dark {
  --bg:        #1a1a1a;   /* Ink */
  --surface:   #282828;   /* Ash */
  --surface-2: #1a1a1a;   /* Ink — inset / input areas */
  --border:    rgba(255,255,255,0.09);
  --text:      #ececea;
  --muted:     #888888;
  --hover:     #282828;   /* Ash */
  --ifocus:    #c97040;
  --pri:       #c97040;
  --pri-fg:    #ffffff;
  --sbg:       rgba(201,112,64,0.12);
  --stx:       #d4945a;
  --sbdr:      rgba(201,112,64,0.28);
  --danger:    #ef4444;
  --danger-h:  rgba(239,68,68,0.15);
  --pass-bg:   #0d1f10; --pass-tx: #86efac;
  --fail-bg:   #1f0d0d; --fail-tx: #fca5a5;
  --draft-bg:  #1c1400; --draft-tx: #fcd34d;
  --sb-bg:     #1a1a1a;   /* Ink */
  --sb-hover:  #282828;   /* Ash */
  --sb-active: #282828;   /* Ash */
  --sb-tx:     #d9d9d7;
  --sb-muted:  #5e5e5e;
  --tx:    var(--text);
  --surf:  var(--surface);
  --surf2: var(--surface-2);
  --bdr:   var(--border);
  --inp:   var(--surface-2);
}

/* System dark fallback when no explicit class is set yet */
@media (prefers-color-scheme: dark) {
  :root:not(.dark):not([data-light]) {
    --bg:        #1a1a1a;   /* Ink */
    --surface:   #282828;   /* Ash */
    --surface-2: #1a1a1a;   /* Ink */
    --border:    rgba(255,255,255,0.09);
    --text:      #ececea;
    --muted:     #888888;
    --hover:     #282828;   /* Ash */
    --ifocus:    #c97040;
    --pri:       #c97040;
    --pri-fg:    #ffffff;
    --sbg:       rgba(201,112,64,0.12);
    --stx:       #d4945a;
    --sbdr:      rgba(201,112,64,0.28);
    --danger:    #ef4444;
    --danger-h:  rgba(239,68,68,0.15);
    --pass-bg:   #0d1f10; --pass-tx: #86efac;
    --fail-bg:   #1f0d0d; --fail-tx: #fca5a5;
    --draft-bg:  #1c1400; --draft-tx: #fcd34d;
    --sb-bg:     #1a1a1a;   /* Ink */
    --sb-hover:  #282828;   /* Ash */
    --sb-active: #282828;   /* Ash */
    --sb-tx:     #d9d9d7;
    --sb-muted:  #5e5e5e;
    --tx:    var(--text);
    --surf:  var(--surface);
    --surf2: var(--surface-2);
    --bdr:   var(--border);
    --inp:   var(--surface-2);
  }
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
}
</style>
