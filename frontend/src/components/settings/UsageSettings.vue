<template>
  <div class="us-wrap">
    <div class="us-heading">
      <h2 class="us-title">Usage &amp; Cost</h2>
      <p class="us-subtitle">Estimated token usage and cost across all sessions. Prices are based on published API rates.</p>
    </div>

    <div v-if="loading" class="us-loading">Loading…</div>

    <template v-else>
      <div class="us-section-label">All Sessions ({{ data.session_count }} with usage data)</div>

      <div class="us-totals">
        <div class="us-stat">
          <span class="us-val">{{ fmtTokens(data.totals.input_tokens) }}</span>
          <span class="us-lbl">↑ Input tokens</span>
        </div>
        <div class="us-divider" />
        <div class="us-stat">
          <span class="us-val">{{ fmtTokens(data.totals.output_tokens) }}</span>
          <span class="us-lbl">↓ Output tokens</span>
        </div>
        <div class="us-divider" />
        <div class="us-stat">
          <span class="us-val us-cost">{{ fmtCost(data.totals.cost_usd) }}</span>
          <span class="us-lbl">Est. cost</span>
        </div>
      </div>

      <div v-if="data.breakdown.length">
        <div class="us-section-label">By Model</div>
        <div class="us-table">
          <div class="us-th">
            <span>Model</span><span>↑ Input</span><span>↓ Output</span><span>Est. cost</span>
          </div>
          <div v-for="row in data.breakdown" :key="row.model" class="us-tr">
            <span class="us-model">{{ row.model }}</span>
            <span>{{ fmtTokens(row.input_tokens) }}</span>
            <span>{{ fmtTokens(row.output_tokens) }}</span>
            <span class="us-cost-cell">{{ fmtCost(row.cost_usd) }}</span>
          </div>
        </div>
      </div>

      <p v-if="!data.breakdown.length" class="us-empty">No usage data yet. Start a session to see costs.</p>

      <p class="us-disclaimer">Prices are estimates based on published API rates and may not reflect your exact billing.</p>
    </template>
  </div>
</template>

<script setup>
import { apiFetch } from '../../composables/useFetch.js'
import { ref, onMounted } from 'vue'

const loading = ref(true)
const data    = ref({ totals: { input_tokens: 0, output_tokens: 0, cost_usd: 0 }, breakdown: [], session_count: 0 })

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
    const res = await apiFetch('/api/usage/summary')
    if (res.ok) data.value = await res.json()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.us-wrap { display: flex; flex-direction: column; gap: 24px; }
.us-heading { display: flex; flex-direction: column; gap: 6px; }
.us-title { font-size: 22px; font-weight: 700; color: var(--tx); margin: 0; }
.us-subtitle { font-size: 13px; color: var(--muted); margin: 0; }
.us-loading { font-size: 13px; color: var(--muted); }
.us-section-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); }

.us-totals {
  display: flex; gap: 0; background: var(--inp);
  border: 1.5px solid var(--bdr); border-radius: 12px; overflow: hidden;
}
.us-stat { flex: 1; display: flex; flex-direction: column; gap: 4px; padding: 20px 24px; }
.us-val  { font-size: 22px; font-weight: 700; color: var(--tx); }
.us-cost { color: var(--pri); }
.us-lbl  { font-size: 11px; color: var(--muted); }
.us-divider { width: 1px; background: var(--bdr); }

.us-table {
  background: var(--inp); border: 1.5px solid var(--bdr);
  border-radius: 10px; overflow: hidden;
}
.us-th, .us-tr {
  display: grid; grid-template-columns: 1fr auto auto auto;
  gap: 16px; padding: 11px 16px; align-items: center;
}
.us-th { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); border-bottom: 1px solid var(--bdr); }
.us-tr { font-size: 13px; border-bottom: 1px solid var(--bdr); }
.us-tr:last-child { border-bottom: none; }
.us-model { font-family: monospace; font-size: 12px; color: var(--tx); }
.us-cost-cell { color: var(--pri); font-weight: 600; }
.us-empty { font-size: 13px; color: var(--muted); margin: 0; }
.us-disclaimer { font-size: 11px; color: var(--muted); margin: 0; }
</style>
