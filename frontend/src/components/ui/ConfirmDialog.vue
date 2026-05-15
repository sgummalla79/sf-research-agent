<!--
  ConfirmDialog — confirmation modal with title / body / footer sections.

  Usage:
    <ConfirmDialog
      :open="pending"
      title="Discard draft?"
      body="Unpublished changes will be permanently lost."
      confirm-label="Discard"
      @confirm="doIt"
      @cancel="pending = false"
    />

  Props:
    open         Boolean  — controls visibility
    title        String   — heading text
    body         String?  — explanation text shown in body section
    confirmLabel String   — confirm button text  (default "Confirm")
    cancelLabel  String   — cancel button text   (default "Cancel")
    danger       Boolean  — red confirm + warning icon (default true)
-->
<template>
  <Teleport to="body">
    <Transition name="cd-fade">
      <div v-if="open" class="cd-backdrop" @click.self="$emit('cancel')">
        <Transition name="cd-pop">
          <div v-if="open" class="cd-dialog" role="dialog" :aria-modal="true" :aria-label="title">

            <!-- ── Title ──────────────────────────────────────────────────── -->
            <div class="cd-header">
              <span class="cd-icon" :class="danger ? 'cd-icon-danger' : 'cd-icon-info'">
                <!-- Warning triangle (danger) -->
                <svg v-if="danger" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                  width="18" height="18">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <!-- Info circle (non-danger) -->
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                  width="18" height="18">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="16" x2="12" y2="12"/>
                  <line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
              </span>
              <span class="cd-title">{{ title }}</span>
            </div>

            <!-- ── Body ──────────────────────────────────────────────────── -->
            <div v-if="body" class="cd-body">{{ body }}</div>

            <!-- ── Footer ────────────────────────────────────────────────── -->
            <div class="cd-footer">
              <button class="cd-btn cd-cancel" @click="$emit('cancel')">
                {{ cancelLabel }}
              </button>
              <button class="cd-btn cd-confirm" :class="{ 'cd-confirm-danger': danger }"
                @click="$emit('confirm')">
                {{ confirmLabel }}
              </button>
            </div>

          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
defineProps({
  open:         { type: Boolean, required: true },
  title:        { type: String,  required: true },
  body:         { type: String,  default: '' },
  confirmLabel: { type: String,  default: 'Confirm' },
  cancelLabel:  { type: String,  default: 'Cancel' },
  danger:       { type: Boolean, default: true },
})

defineEmits(['confirm', 'cancel'])
</script>

<style scoped>
/* ── Backdrop ─────────────────────────────────────────────────────────────── */
.cd-backdrop {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, .45);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}

/* ── Dialog shell ─────────────────────────────────────────────────────────── */
.cd-dialog {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: 400px; max-width: calc(100vw - 32px);
  display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, .25);
  overflow: hidden;
}

/* ── Header (title) ───────────────────────────────────────────────────────── */
.cd-header {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
}

.cd-icon {
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%;
}

.cd-icon-danger {
  background: rgba(220, 38, 38, .1);
  color: #dc2626;
}
.cd-icon-info {
  background: rgba(59, 130, 246, .1);
  color: #3b82f6;
}

html.dark .cd-icon-danger { background: rgba(248, 113, 113, .12); color: #f87171; }
html.dark .cd-icon-info   { background: rgba(96, 165, 250, .12);  color: #60a5fa; }

.cd-title {
  font-size: 14px; font-weight: 700; color: var(--text); line-height: 1.3;
}

/* ── Body ─────────────────────────────────────────────────────────────────── */
.cd-body {
  padding: 14px 20px;
  font-size: 13px; color: var(--muted); line-height: 1.6;
  border-bottom: 1px solid var(--border);
}

/* ── Footer ───────────────────────────────────────────────────────────────── */
.cd-footer {
  display: flex; align-items: center; justify-content: flex-end; gap: 8px;
  padding: 12px 16px;
}

/* ── Buttons ──────────────────────────────────────────────────────────────── */
.cd-btn {
  padding: 8px 18px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: background .13s, opacity .13s;
  white-space: nowrap;
}

.cd-cancel {
  border: 1px solid var(--border); background: transparent; color: var(--text);
}
.cd-cancel:hover { background: var(--surface-2); }

.cd-confirm {
  border: none; background: var(--pri); color: var(--pri-fg);
}
.cd-confirm:hover { opacity: .88; }

.cd-confirm-danger { background: #dc2626; }
.cd-confirm-danger:hover { background: #b91c1c; opacity: 1; }

html.dark .cd-confirm-danger       { background: #ef4444; }
html.dark .cd-confirm-danger:hover { background: #dc2626; }

/* ── Transitions ──────────────────────────────────────────────────────────── */
.cd-fade-enter-active, .cd-fade-leave-active { transition: opacity .2s; }
.cd-fade-enter-from,   .cd-fade-leave-to     { opacity: 0; }

.cd-pop-enter-active, .cd-pop-leave-active { transition: opacity .18s, transform .18s; }
.cd-pop-enter-from,   .cd-pop-leave-to     { opacity: 0; transform: scale(.95) translateY(6px); }
</style>
