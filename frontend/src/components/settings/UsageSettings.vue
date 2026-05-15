<template>
  <div class="us-wrap">
    <div class="us-heading">
      <h2 class="us-title">Usage &amp; Cost</h2>
      <p class="us-subtitle">Estimated token usage and cost across all sessions. Prices are based on published API rates.</p>
    </div>

    <div v-if="loading" class="us-loading">Loading…</div>

    <div v-else-if="error" class="us-empty">{{ error }}</div>

    <template v-else>
      <div class="us-section-label">
        {{ totals.conversation_count }} conversation{{ totals.conversation_count !== 1 ? 's' : '' }} tracked
      </div>

      <div v-if="totals.input_tokens || totals.output_tokens">
        <div class="us-totals">
          <div class="us-stat">
            <span class="us-val">{{ fmtTokens(totals.input_tokens) }}</span>
            <span class="us-lbl">↑ Input tokens</span>
          </div>
          <div class="us-divider" />
          <div class="us-stat">
            <span class="us-val">{{ fmtTokens(totals.output_tokens) }}</span>
            <span class="us-lbl">↓ Output tokens</span>
          </div>
          <div class="us-divider" />
          <div class="us-stat">
            <span class="us-val us-cost">{{ fmtCost(totals.cost_usd) }}</span>
            <span class="us-lbl">Est. cost</span>
          </div>
        </div>
      </div>

      <div v-else class="us-no-data">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="32" height="32">
          <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
        </svg>
        <p class="us-no-data-title">No usage data yet</p>
        <p class="us-no-data-sub">Start a conversation or run a skill — token usage will appear here.</p>
      </div>

      <p v-if="totals.input_tokens" class="us-disclaimer">
        Prices are estimates based on published API rates and may not reflect your exact billing.
      </p>
    </template>
  </div>
</template>

<script setup>
import { apiFetch } from '../../composables/useFetch.js'
import { ref, onMounted } from 'vue'

const loading = ref(true)
const error   = ref(null)
const totals  = ref({ input_tokens: 0, output_tokens: 0, cost_usd: 0, conversation_count: 0 })

function fmtTokens(n) {
  if (!n) return '0'
  return n >= 1_000_000 ? (n / 1_000_000).toFixed(1) + 'M'
       : n >= 1_000      ? (n / 1_000).toFixed(1) + 'K'
       : String(n)
}
function fmtCost(c) {
  if (!c) return '$0.00'
  return c < 0.01 ? `$${c.toFixed(5)}` : `$${c.toFixed(4)}`
}

onMounted(async () => {
  try {
    const res  = await apiFetch('/api/usage/summary')
    if (res.ok) {
      const data = await res.json()
      totals.value = data.totals || totals.value
    } else {
      error.value = 'Could not load usage data.'
    }
  } catch (_) {
    error.value = 'Could not load usage data.'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.us-wrap { display: flex; flex-direction: column; gap: 24px; padding: 20px; }
.us-heading { display: flex; flex-direction: column; gap: 6px; }
.us-title { font-size: 15px; font-weight: 700; color: var(--text); margin: 0; }
.us-subtitle { font-size: 13px; color: var(--muted); margin: 0; }
.us-loading { font-size: 13px; color: var(--muted); }
.us-section-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); }

.us-totals {
  display: flex; gap: 0; background: var(--surface-2);
  border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
}
.us-stat { flex: 1; display: flex; flex-direction: column; gap: 4px; padding: 20px 24px; }
.us-val  { font-size: 22px; font-weight: 700; color: var(--text); }
.us-cost { color: var(--pri); }
.us-lbl  { font-size: 11px; color: var(--muted); }
.us-divider { width: 1px; background: var(--border); }

.us-table {
  background: var(--surface-2); border: 1px solid var(--border);
  border-radius: 10px; overflow: hidden;
}
.us-th, .us-tr {
  display: grid; grid-template-columns: 1fr auto auto auto;
  gap: 16px; padding: 11px 16px; align-items: center;
}
.us-th { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); border-bottom: 1px solid var(--border); }
.us-tr { font-size: 13px; border-bottom: 1px solid var(--border); }
.us-tr:last-child { border-bottom: none; }
.us-model { font-family: monospace; font-size: 12px; color: var(--text); }
.us-cost-cell { color: var(--pri); font-weight: 600; }
.us-empty { font-size: 13px; color: var(--muted); margin: 0; }

.us-no-data {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 10px; padding: 48px 20px; text-align: center; color: var(--muted);
}
.us-no-data-title { font-size: 15px; font-weight: 600; color: var(--text); margin: 0; }
.us-no-data-sub   { font-size: 13px; color: var(--muted); margin: 0; max-width: 320px; line-height: 1.5; }
.us-disclaimer { font-size: 11px; color: var(--muted); margin: 0; }
</style>
