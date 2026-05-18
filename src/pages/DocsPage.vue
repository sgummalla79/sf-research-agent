<!-- Pragna API Reference — three-column resizable docs page -->
<template>
  <!-- Loading -->
  <div v-if="loading" class="docs-shell docs-center-state">
    <span class="docs-state-text">Loading API reference…</span>
  </div>

  <!-- Error -->
  <div v-else-if="fetchError" class="docs-shell docs-center-state">
    <span class="docs-state-text">{{ fetchError }}</span>
  </div>

  <!-- Loaded -->
  <div v-else class="docs-shell">

    <!-- ── Left sidebar ─────────────────────────────────────────────── -->
    <aside class="ds">
      <div class="ds-head">
        <a href="/" class="ds-back">← Pragna</a>
        <div class="ds-brand">API Reference</div>
        <input v-model="search" class="ds-search" placeholder="Search endpoints…" />
      </div>
      <nav class="ds-nav">
        <a :class="['ds-item', { active: activeId === 'overview' }]"
           @click.prevent="activeId = 'overview'">Overview</a>
        <template v-for="group in filteredGroups" :key="group.tag">
          <div class="ds-tag">{{ group.tag }}</div>
          <a v-for="ep in group.endpoints" :key="ep.id"
             :class="['ds-item ds-ep', { active: activeId === ep.id }]"
             @click.prevent="select(ep.id)">
            <span :class="['ds-ep-method', ep.method]">{{ ep.method.toUpperCase() }}</span>
            <span class="ds-ep-label">{{ endpointLabel(ep) }}</span>
          </a>
        </template>
      </nav>
    </aside>

    <div class="docs-divider" />

    <!-- ── Content (center + flyout) ─────────────────────────────────── -->
    <div class="docs-content">

      <main class="dc" ref="centerEl"
            :style="{ paddingBottom: flyoutOpen ? (flyoutH + 48) + 'px' : '80px' }">

        <!-- Overview -->
        <section v-if="activeId === 'overview'" class="dc-section">
          <h1 class="dc-h1">{{ spec.info.title }}</h1>
          <div class="dc-version">Version {{ spec.info.version }}</div>
          <div class="dc-prose" v-html="overviewHtml" />
          <div class="dc-meta-row">
            <div class="dc-meta-card">
              <div class="dc-meta-label">Base URL</div>
              <code class="dc-meta-code">{{ API_BASE || 'http://localhost:8000' }}</code>
            </div>
            <div class="dc-meta-card">
              <div class="dc-meta-label">Authentication</div>
              <code class="dc-meta-code">Cookie: session=&lt;token&gt;</code>
            </div>
            <div class="dc-meta-card">
              <div class="dc-meta-label">Content type</div>
              <code class="dc-meta-code">application/json</code>
            </div>
          </div>
          <h2 class="dc-h2">Common Error Codes</h2>
          <table class="dc-table">
            <thead><tr><th>Code</th><th>Meaning</th><th>What to do</th></tr></thead>
            <tbody>
              <tr v-for="e in ERROR_CODES" :key="e.code">
                <td><span :class="['dc-status', e.cls]">{{ e.code }}</span></td>
                <td>{{ e.meaning }}</td>
                <td class="dc-muted">{{ e.fix }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <!-- Endpoint detail -->
        <section v-else-if="active" class="dc-section">
          <div class="dc-ep-header">
            <span :class="['dc-method-lg', active.method]">{{ active.method.toUpperCase() }}</span>
            <code class="dc-path-lg">{{ active.path }}</code>
          </div>
          <h2 class="dc-summary">{{ active.summary }}</h2>
          <p v-if="active.description" class="dc-desc">{{ active.description }}</p>

          <template v-if="active.parameters?.length">
            <h3 class="dc-section-label">Parameters</h3>
            <table class="dc-table">
              <thead><tr><th>Name</th><th>In</th><th>Type</th><th>Required</th><th>Description</th></tr></thead>
              <tbody>
                <tr v-for="p in active.parameters" :key="p.name + p.in">
                  <td><code>{{ p.name }}</code></td>
                  <td><span class="dc-in-pill">{{ p.in }}</span></td>
                  <td><span class="dc-type">{{ p.schema?.type || 'string' }}</span></td>
                  <td>
                    <span v-if="p.required" class="dc-req">required</span>
                    <span v-else class="dc-opt">optional</span>
                  </td>
                  <td class="dc-muted">{{ p.description || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </template>

          <template v-if="reqBodyProps.length">
            <h3 class="dc-section-label">
              Request Body
              <span class="dc-content-type">application/json</span>
            </h3>
            <table class="dc-table">
              <thead><tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr></thead>
              <tbody>
                <tr v-for="p in reqBodyProps" :key="p.name">
                  <td><code>{{ p.name }}</code></td>
                  <td><span class="dc-type">{{ p.type }}</span></td>
                  <td>
                    <span v-if="p.required" class="dc-req">required</span>
                    <span v-else class="dc-opt">optional</span>
                  </td>
                  <td class="dc-muted">{{ p.description || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </template>

          <h3 class="dc-section-label">Responses</h3>
          <div class="dc-resp-list">
            <div v-for="(resp, code) in active.responses" :key="code" class="dc-resp-row">
              <span :class="['dc-status', statusCls(code)]">{{ code }}</span>
              <span class="dc-muted">{{ resp.description }}</span>
            </div>
          </div>
        </section>
      </main>

      <!-- ── Bottom flyout ──────────────────────────────────────────── -->
      <Transition name="flyout">
        <div v-if="active && activeId !== 'overview'"
             class="docs-flyout" :class="{ open: flyoutOpen }"
             :style="{ height: flyoutOpen ? flyoutH + 'px' : '0' }">

          <!-- Drag handle -->
          <div class="flyout-handle" @mousedown.prevent="startFlyoutDrag" />

          <div class="flyout-inner">
            <!-- Code panel -->
            <div class="flyout-code">
              <div class="flyout-tabs-row">
                <button v-for="l in LANGS" :key="l.id"
                  :class="['flyout-tab', { active: lang === l.id }]"
                  @click="lang = l.id">{{ l.label }}</button>
                <div class="flyout-tabs-gap" />
                <button class="flyout-icon-btn" @click="copyCode" :title="copiedCode ? 'Copied!' : 'Copy'">
                  <svg v-if="!copiedCode" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="var(--pri)" stroke-width="2.5" width="14" height="14"><polyline points="20 6 9 17 4 12"/></svg>
                </button>
                <button class="flyout-icon-btn" @click="flyoutOpen = false" title="Collapse (Esc)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="6 9 12 15 18 9"/></svg>
                </button>
              </div>
              <div class="flyout-scroll">
                <pre class="flyout-pre"><code>{{ currentCode }}</code></pre>
              </div>
            </div>

            <!-- Panel divider -->
            <div class="flyout-panel-div" />

            <!-- Response panel -->
            <div class="flyout-resp">
              <div class="flyout-resp-header">Response</div>
              <div class="flyout-scroll">
                <pre class="flyout-pre"><code>{{ respExample }}</code></pre>
              </div>
            </div>
          </div>
        </div>
      </Transition>

      <!-- Re-open bar -->
      <Transition name="bar">
        <div v-if="!flyoutOpen && active && activeId !== 'overview'"
             class="flyout-bar" @click="flyoutOpen = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          <span>Code examples</span>
          <span :class="['flyout-bar-method', active.method]">{{ active.method.toUpperCase() }}</span>
          <code class="flyout-bar-path">{{ active.path }}</code>
        </div>
      </Transition>

    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import { Api }      from '../api/service.js'
import { API_BASE } from '../api/config.js'

// ── Constants ─────────────────────────────────────────────────────────────────

const LANGS = [
  { id: 'curl', label: 'Curl' },
  { id: 'python', label: 'Python' },
  { id: 'js', label: 'JavaScript' },
]

const ERROR_CODES = [
  { code: '400', cls: 'client',   meaning: 'Bad Request',        fix: 'Check the request body — a field is missing or invalid.' },
  { code: '401', cls: 'client',   meaning: 'Unauthenticated',    fix: 'Get a session cookie via /auth/token or /auth/initiate.' },
  { code: '403', cls: 'client',   meaning: 'Forbidden',          fix: 'You do not own the requested resource.' },
  { code: '404', cls: 'client',   meaning: 'Not Found',          fix: 'Check the ID in the URL — the resource may have been deleted.' },
  { code: '409', cls: 'client',   meaning: 'Conflict',           fix: 'A skill is already running in this conversation.' },
  { code: '413', cls: 'client',   meaning: 'Payload Too Large',  fix: 'File exceeds the upload size limit.' },
  { code: '415', cls: 'client',   meaning: 'Unsupported Type',   fix: 'Use a supported file extension (pdf, docx, txt, png, jpg, etc.).' },
  { code: '422', cls: 'client',   meaning: 'Validation Error',   fix: 'A required field is missing or the wrong type. See the error detail array.' },
  { code: '500', cls: 'server',   meaning: 'Server Error',       fix: 'Something went wrong on the server. Retry or check the backend logs.' },
]

const QUICKSTART = `# 1. Authenticate — get a session cookie
curl -X POST "${API_BASE}/auth/token" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "you@example.com",
    "password": "your-password"
  }'
# Response sets: Set-Cookie: session=<token>; HttpOnly

# 2. Create a conversation
curl -X POST "${API_BASE}/api/conversations" \\
  -H "Cookie: session=<token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "chat_provider": "anthropic",
    "chat_model": "claude-3-5-sonnet-20241022"
  }'
# Response: { "id": "<conversation-id>", ... }

# 3. Run the Architect skill (streams SSE)
curl -X POST "${API_BASE}/api/conversations/<id>/skills/<snapshot-id>/invoke" \\
  -H "Cookie: session=<token>" \\
  -H "Content-Type: application/json" \\
  -d '{"brief": "Build a real-time order management system for 50k orders/day"}'`

// ── No sidebar resize — width is fixed in CSS ─────────────────────────────────

// ── Flyout ────────────────────────────────────────────────────────────────────

const flyoutOpen = ref(false)
const flyoutH    = ref(260)
let   _flyStartY = 0
let   _flyStartH = 0

function startFlyoutDrag(e) {
  _flyStartY = e.clientY
  _flyStartH = flyoutH.value
  document.addEventListener('mousemove', onFlyoutMove)
  document.addEventListener('mouseup',  stopFlyoutDrag)
}

function onFlyoutMove(e) {
  flyoutH.value = Math.max(160, Math.min(window.innerHeight * 0.6, _flyStartH + (_flyStartY - e.clientY)))
}

function stopFlyoutDrag() {
  document.removeEventListener('mousemove', onFlyoutMove)
  document.removeEventListener('mouseup',  stopFlyoutDrag)
}

function onKeydown(e) {
  if (e.key === 'Escape' && flyoutOpen.value) flyoutOpen.value = false
}

onUnmounted(() => {
  stopFlyoutDrag()
  document.removeEventListener('keydown', onKeydown)
})

// ── Fetch spec ────────────────────────────────────────────────────────────────

const spec       = ref(null)
const loading    = ref(true)
const fetchError = ref('')
const activeId   = ref('overview')
const lang       = ref('curl')
const search     = ref('')
const copiedCode = ref(false)
const copiedQs   = ref(false)
const centerEl   = ref(null)

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  try {
    spec.value = await Api.getOpenApiSpec()
  } catch (e) {
    fetchError.value = `Could not load API spec (${e.message}). Make sure the backend is reachable at ${API_BASE || 'localhost:8000'}.`
  } finally {
    loading.value = false
  }
})

// ── Endpoint parsing ──────────────────────────────────────────────────────────

const allEndpoints = computed(() => {
  if (!spec.value?.paths) return []
  const METHODS = ['get', 'post', 'put', 'patch', 'delete']
  const result = []
  for (const [path, item] of Object.entries(spec.value.paths)) {
    for (const method of METHODS) {
      const op = item[method]
      if (!op) continue
      const tag = op.tags?.[0] || 'Other'
      const id  = `${method}_${path.replace(/\//g, '__').replace(/[{}]/g, '').replace(/__+/g, '__')}`
      result.push({
        id, method, path,
        shortPath:   path.replace('/api', ''),
        tag,
        summary:     op.summary     || '',
        description: op.description || '',
        parameters:  op.parameters  || [],
        requestBody: op.requestBody || null,
        responses:   op.responses   || {},
      })
    }
  }
  return result
})

const groupedEndpoints = computed(() => {
  if (!spec.value) return []
  const order = spec.value.tags?.map(t => t.name) || []
  const map = {}
  for (const ep of allEndpoints.value) {
    ;(map[ep.tag] = map[ep.tag] || []).push(ep)
  }
  const ordered = order.filter(t => map[t]).map(t => ({ tag: t, endpoints: map[t] }))
  const extra   = Object.keys(map).filter(t => !order.includes(t)).map(t => ({ tag: t, endpoints: map[t] }))
  return [...ordered, ...extra]
})

const filteredGroups = computed(() => {
  const q = search.value.toLowerCase().trim()
  if (!q) return groupedEndpoints.value
  return groupedEndpoints.value
    .map(g => ({ ...g, endpoints: g.endpoints.filter(ep =>
      ep.path.toLowerCase().includes(q) ||
      ep.summary.toLowerCase().includes(q) ||
      ep.method === q
    )}))
    .filter(g => g.endpoints.length)
})

const active = computed(() => allEndpoints.value.find(ep => ep.id === activeId.value) || null)

const overviewHtml = computed(() => marked.parse(spec.value?.info?.description || ''))

// ── Schema helpers ────────────────────────────────────────────────────────────

function resolveSchema(s) {
  if (!s) return {}
  if (s.$ref) {
    const name = s.$ref.split('/').pop()
    return spec.value?.components?.schemas?.[name] || {}
  }
  return s
}

const reqBodyProps = computed(() => {
  if (!active.value?.requestBody) return []
  const content = active.value.requestBody.content?.['application/json']
  if (!content?.schema) return []
  const schema   = resolveSchema(content.schema)
  const required = new Set(schema.required || [])
  return Object.entries(schema.properties || {}).map(([name, s]) => ({
    name,
    type:        s.type || (s.anyOf ? s.anyOf.map(x => x.type || 'any').join(' | ') : 'any'),
    required:    required.has(name),
    description: s.description || '',
  }))
})

// ── Example generation ────────────────────────────────────────────────────────

const FIELD_EX = {
  id: '<uuid>', conversation_id: '<conversation-id>',
  execution_id: '<execution-id>', artifact_id: '<artifact-id>',
  conversation_skill_id: '<skill-snapshot-id>', skill_id: 'architect',
  agent_key: 'intake_agent', provider: 'anthropic', provider_id: 'anthropic',
  model: 'claude-3-5-sonnet-20241022', model_id: 'claude-3-5-sonnet-20241022',
  chat_provider: 'anthropic', chat_model: 'claude-3-5-sonnet-20241022',
  title: 'My architecture project', display_name: 'Claude 3.5 Sonnet',
  content: 'Build a scalable microservices platform for e-commerce',
  brief: 'Real-time order management system for 50,000 orders/day',
  original_message: '/architect build a SaaS analytics platform',
  text: 'How should I architect a multi-tenant SaaS platform?',
  email: 'user@example.com', name: 'Jane Smith',
  sub: 'auth0|507f1f77bcf86cd799439011', password: 'your-password',
  api_key: 'sk-ant-api03-...', theme: 'default',
  bedrock_url: 'https://bedrock.us-east-1.amazonaws.com',
  bedrock_token: '<aws-bedrock-token>',
  source_type: 'brief', response: '1', connection: 'google-oauth2',
}

function exVal(name, schema) {
  if (!schema) return 'string'
  if (schema.$ref) return exObj(resolveSchema(schema))
  if (name in FIELD_EX) return FIELD_EX[name]
  const t = schema.type || schema.anyOf?.[0]?.type
  if (t === 'string')  return schema.enum?.[0] || 'string'
  if (t === 'integer' || t === 'number') return 0
  if (t === 'boolean') return true
  if (t === 'array')   return schema.items ? [exVal(name, schema.items)] : []
  if (t === 'object')  return exObj(schema)
  if (schema.anyOf)    return exVal(name, schema.anyOf[0])
  return 'string'
}

function exObj(schema) {
  const s = resolveSchema(schema)
  if (!s.properties) return {}
  const out = {}
  for (const [k, v] of Object.entries(s.properties)) out[k] = exVal(k, v)
  return out
}

function bodyEx(rb) {
  if (!rb) return null
  const s = resolveSchema(rb.content?.['application/json']?.schema)
  return s.properties ? exObj(s) : null
}

function buildUrl(path, params) {
  let url = `${API_BASE}${path}`
  const q = (params || []).filter(p => p.in === 'query')
  if (q.length) url += '?' + q.map(p => `${p.name}=<${p.name}>`).join('&')
  return url
}

// ── Code generators ───────────────────────────────────────────────────────────

function toPy(val, d = 2) {
  const pad = '    '.repeat(d)
  const end = '    '.repeat(d - 1)
  if (val === null)  return 'None'
  if (val === true)  return 'True'
  if (val === false) return 'False'
  if (typeof val === 'string') return `"${val}"`
  if (typeof val === 'number') return String(val)
  if (Array.isArray(val)) {
    if (!val.length) return '[]'
    return `[\n${val.map(v => `${pad}${toPy(v, d + 1)}`).join(',\n')},\n${end}]`
  }
  if (typeof val === 'object') {
    const ks = Object.keys(val)
    if (!ks.length) return '{}'
    return `{\n${ks.map(k => `${pad}"${k}": ${toPy(val[k], d + 1)}`).join(',\n')},\n${end}}`
  }
  return String(val)
}

function genCurl(ep) {
  const body  = bodyEx(ep.requestBody)
  const lines = [`curl -X ${ep.method.toUpperCase()} "${buildUrl(ep.path, ep.parameters)}" \\`,
                 `  -H "Cookie: session=<your-session-token>"`]
  if (body) {
    lines[lines.length - 1] += ' \\'
    lines.push(`  -H "Content-Type: application/json" \\`)
    lines.push(`  -d '${JSON.stringify(body, null, 2)}'`)
  }
  return lines.join('\n')
}

function genPython(ep) {
  const body = bodyEx(ep.requestBody)
  let code = `import httpx\n\nresponse = httpx.${ep.method}(\n    "${buildUrl(ep.path, ep.parameters)}",\n    cookies={"session": "<your-session-token>"},\n`
  if (body) code += `    json=${toPy(body, 2)},\n`
  return code + `)\nprint(response.json())`
}

function genJS(ep) {
  const body = bodyEx(ep.requestBody)
  let code = `const response = await fetch(\n  "${buildUrl(ep.path, ep.parameters)}",\n  {\n    method: "${ep.method.toUpperCase()}",\n    credentials: "include",\n`
  if (body) {
    code += `    headers: { "Content-Type": "application/json" },\n`
    code += `    body: JSON.stringify(${JSON.stringify(body, null, 4).split('\n').map((l, i) => i ? '    ' + l : l).join('\n')}),\n`
  }
  return code + `  }\n);\nconst data = await response.json();\nconsole.log(data);`
}

// ── Sidebar labels ────────────────────────────────────────────────────────────

const CUSTOM_LABELS = {
  'get_/api/conversations':                                    'All Conversations',
  'get_/api/conversations/{conversation_id}':                  'Conversation',
  'post_/api/skills/{skill_id}/agents/{agent_key}/publish':    'Publish Agent Skill',
  'post_/api/skills/{skill_id}/publish':                       'Publish All Agents Skill',
  'get_/api/artifacts/{artifact_id}':                          'Fetch Artifact',
  'get_/api/executions/{execution_id}/artifacts':              'Fetch Execution Artifacts',
  'post_/api/providers/bedrock/connect':                       'Connect AWS Bedrock Provider',
  'post_/api/providers/{provider_id}/connect':                 'Connect Provider',
  'patch_/api/providers/bedrock/toggle':                       'Activate / Inactivate AWS Bedrock Provider',
  'patch_/api/providers/{provider_id}/toggle':                 'Activate / Inactivate Provider',
}

function endpointLabel(ep) {
  const key = `${ep.method}_${ep.path}`
  if (key in CUSTOM_LABELS) return CUSTOM_LABELS[key]
  const segs = ep.path.split('/').filter(s => s && !s.startsWith('{'))
  const last  = segs[segs.length - 1] || 'root'
  return last.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

const currentCode = computed(() => {
  if (!active.value) return ''
  if (lang.value === 'curl')   return genCurl(active.value)
  if (lang.value === 'python') return genPython(active.value)
  return genJS(active.value)
})

// ── Response examples ─────────────────────────────────────────────────────────

const respExample = computed(() => {
  if (!active.value) return ''
  const codes = Object.keys(active.value.responses)
  if (active.value.responses['302']) return 'HTTP/1.1 302 Found\nLocation: <redirect-url>'
  const hasSSE = Object.values(active.value.responses).some(r =>
    r.content?.['text/event-stream'])
  if (hasSSE) return `data: {"type":"stage_start","stage":"intake","label":"Intake Agent"}\n\ndata: {"type":"token","content":"Understanding your project..."}\n\ndata: {"type":"confirm_understanding","content":"...","execution_id":"<id>"}\n\ndata: {"type":"done","status":"completed"}`
  if (codes.some(c => c.startsWith('2'))) return `// 200 OK\n{\n  "ok": true\n}`
  return `// ${codes[0]}\n{\n  "detail": "See response description"\n}`
})

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusCls(code) {
  const n = parseInt(code)
  if (n >= 500) return 'server'
  if (n >= 400) return 'client'
  if (n >= 300) return 'redirect'
  return 'ok'
}

function select(id) {
  activeId.value = id
  flyoutOpen.value = true
  centerEl.value?.scrollTo({ top: 0 })
}

async function copyCode() {
  await navigator.clipboard.writeText(currentCode.value)
  copiedCode.value = true
  setTimeout(() => { copiedCode.value = false }, 2000)
}

async function copyQuickstart() {
  await navigator.clipboard.writeText(QUICKSTART)
  copiedQs.value = true
  setTimeout(() => { copiedQs.value = false }, 2000)
}
</script>

<style scoped>
/* ── Shell ─────────────────────────────────────────────────────────── */
.docs-shell {
  position: fixed; inset: 0;
  display: flex; flex-direction: row;
  background: var(--bg);
  overflow: hidden;
  font-family: 'Carlito', sans-serif;
  font-size: 15px;
  color: var(--text);
  z-index: 9999;
  user-select: none;
}

.docs-center-state {
  display: flex; align-items: center; justify-content: center;
}
.docs-state-text { font-size: 16px; color: var(--muted); }

/* ── Drag divider ──────────────────────────────────────────────────── */
.docs-divider {
  width: 1px; flex-shrink: 0;
  background: var(--border);
}

/* ── Left sidebar ──────────────────────────────────────────────────── */
.ds {
  width: 300px;
  background: var(--bg);
  display: flex; flex-direction: column;
  height: 100vh; overflow: hidden;
  flex-shrink: 0;
}
.ds-head {
  padding: 18px 14px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.ds-back {
  font-size: 14px; color: var(--muted); text-decoration: none;
  display: block; margin-bottom: 10px; transition: color .12s;
}
.ds-back:hover { color: var(--text); }
.ds-brand { font-size: 16px; font-weight: 700; margin-bottom: 10px; }
.ds-search {
  width: 100%; padding: 6px 10px; border-radius: 7px;
  border: 1px solid var(--border); background: var(--surface-2);
  color: var(--text); font-size: 15px; outline: none; box-sizing: border-box;
}
.ds-search:focus { border-color: var(--pri); }
.ds-nav { overflow-y: auto; flex: 1; padding: 6px 8px 32px; }
.ds-tag {
  font-size: 13px; font-weight: 700; letter-spacing: .07em;
  text-transform: uppercase; color: var(--muted); padding: 14px 8px 4px;
}
.ds-item {
  display: block; padding: 7px 10px; border-radius: 7px;
  color: var(--text); font-size: 15px; cursor: pointer;
  text-decoration: none; transition: background .1s; user-select: none;
}
.ds-item:hover { background: var(--hover); }
.ds-item.active { background: var(--pri); color: var(--pri-fg); }
.ds-ep { display: flex; align-items: baseline; gap: 7px; padding: 5px 10px; }
.ds-ep-method {
  font-size: 12px; font-weight: 700; letter-spacing: .04em;
  padding: 2px 5px; border-radius: 3px; color: #fff; flex-shrink: 0;
}
.ds-ep-method.get    { background: #10B981; }
.ds-ep-method.post   { background: #3B82F6; }
.ds-ep-method.put    { background: #8B5CF6; }
.ds-ep-method.patch  { background: #F59E0B; }
.ds-ep-method.delete { background: #EF4444; }
.ds-ep-label {
  font-size: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;
}

/* ── Center ────────────────────────────────────────────────────────── */
.dc-section { max-width: 680px; }

.dc-h1    { font-size: 28px; font-weight: 700; margin: 0 0 4px; }
.dc-h2    { font-size: 17px; font-weight: 700; margin: 40px 0 14px; }
.dc-version { font-size: 13px; color: var(--muted); margin-bottom: 24px; }

.dc-prose { font-size: 15px; line-height: 1.75; margin-bottom: 32px; }
.dc-prose :deep(h2) { font-size: 18px; font-weight: 700; margin: 28px 0 10px; }
.dc-prose :deep(h3) { font-size: 15px; font-weight: 600; margin: 20px 0 8px; }
.dc-prose :deep(code) {
  background: var(--bg); padding: 1px 5px; border-radius: 4px;
  font-family: 'Courier New', monospace; font-size: 15px; border: 1px solid var(--border);
}
.dc-prose :deep(ul) { padding-left: 20px; margin: 8px 0; }
.dc-prose :deep(li) { margin: 5px 0; }
.dc-prose :deep(strong) { font-weight: 700; }

.dc-meta-row   { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 40px; }
.dc-meta-card  { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; }
.dc-meta-label { font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }
.dc-meta-code  { font-family: 'Courier New', monospace; font-size: 15px; }

.dc-ep-header  { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; flex-wrap: wrap; }
.dc-method-lg  { font-size: 14px; font-weight: 700; padding: 4px 10px; border-radius: 5px; color: #fff; flex-shrink: 0; }
.dc-method-lg.get    { background: #10B981; }
.dc-method-lg.post   { background: #3B82F6; }
.dc-method-lg.put    { background: #8B5CF6; }
.dc-method-lg.patch  { background: #F59E0B; }
.dc-method-lg.delete { background: #EF4444; }
.dc-path-lg    { font-family: 'Courier New', monospace; font-size: 18px; word-break: break-all; }
.dc-summary    { font-size: 21px; font-weight: 700; margin: 0 0 12px; }
.dc-desc       { font-size: 15px; color: var(--muted); line-height: 1.65; margin: 0 0 32px; }

.dc-section-label {
  font-size: 11px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase;
  color: var(--muted); margin: 32px 0 12px; display: flex; align-items: center; gap: 8px;
}
.dc-content-type {
  font-family: 'Courier New', monospace; font-size: 11px; font-weight: 400; text-transform: none;
  background: var(--bg); border: 1px solid var(--border); padding: 1px 6px; border-radius: 4px;
}
.dc-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 8px; }
.dc-table th {
  text-align: left; padding: 8px 12px; color: var(--muted);
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
  border-bottom: 1px solid var(--border);
}
.dc-table td   { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
.dc-table tr:last-child td { border-bottom: none; }
.dc-table code { font-family: 'Courier New', monospace; font-size: 15px; }
.dc-in-pill { font-size: 13px; font-family: 'Courier New', monospace; background: var(--bg); border: 1px solid var(--border); padding: 1px 6px; border-radius: 4px; color: var(--muted); }
.dc-type    { font-family: 'Courier New', monospace; font-size: 15px; color: var(--pri); }
.dc-req     { font-size: 11px; font-weight: 600; color: #EF4444; }
.dc-opt     { font-size: 11px; color: var(--muted); }
.dc-muted   { color: var(--muted); font-size: 14px; }

.dc-status          { font-family: 'Courier New', monospace; font-size: 15px; font-weight: 700; padding: 2px 8px; border-radius: 4px; }
.dc-status.ok       { background: rgba(16,185,129,.12); color: #10B981; }
.dc-status.redirect { background: rgba(59,130,246,.12); color: #3B82F6; }
.dc-status.client   { background: rgba(245,158,11,.12);  color: #F59E0B; }
.dc-status.server   { background: rgba(239,68,68,.12);   color: #EF4444; }
.dc-resp-list { display: flex; flex-direction: column; gap: 6px; }
.dc-resp-row  { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: var(--bg); border-radius: 8px; border: 1px solid var(--border); }

/* ── Content wrapper ───────────────────────────────────────────────── */
.docs-content {
  flex: 1; min-width: 0;
  position: relative;
  display: flex; flex-direction: column;
  height: 100vh; overflow: hidden;
}
.dc {
  flex: 1; min-height: 0;
  overflow-y: auto;
  padding: 48px 52px 80px;
  transition: padding-bottom .25s ease;
}

/* ── Bottom flyout ─────────────────────────────────────────────────── */
.docs-flyout {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: var(--bg);
  border-top: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow: hidden;
  z-index: 100;
  transition: height .25s ease;
}
.flyout-handle {
  height: 5px; flex-shrink: 0; cursor: ns-resize;
  background: transparent; transition: background .15s;
}
.flyout-handle:hover { background: var(--pri); }
.flyout-inner {
  flex: 1; min-height: 0;
  display: flex; overflow: hidden;
}

/* Code panel */
.flyout-code {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; overflow: hidden;
}
.flyout-tabs-row {
  display: flex; align-items: center;
  border-bottom: 1px solid var(--border);
  padding: 0 12px; flex-shrink: 0;
  height: 44px; box-sizing: border-box;
}
.flyout-tab {
  background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--muted); font-size: 14px; font-weight: 500;
  padding: 10px 12px; cursor: pointer; transition: color .12s;
}
.flyout-tab:hover  { color: var(--text); }
.flyout-tab.active { color: var(--text); border-bottom-color: var(--pri); }
.flyout-tabs-gap   { flex: 1; }
.flyout-icon-btn {
  background: none; border: none; color: var(--muted);
  cursor: pointer; padding: 6px; border-radius: 5px;
  display: flex; align-items: center; transition: color .12s, background .12s;
}
.flyout-icon-btn:hover { color: var(--text); background: var(--hover); }

/* Panel divider */
.flyout-panel-div { width: 1px; background: var(--border); flex-shrink: 0; }

/* Response panel */
.flyout-resp { width: 380px; flex-shrink: 0; display: flex; flex-direction: column; overflow: hidden; }
.flyout-resp-header {
  font-size: 11px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase;
  color: var(--muted); padding: 0 20px; border-bottom: 1px solid var(--border);
  flex-shrink: 0; height: 44px; box-sizing: border-box;
  display: flex; align-items: center;
}

/* Shared scroll + pre */
.flyout-scroll { flex: 1; overflow-y: auto; min-height: 0; }
.flyout-pre {
  margin: 0; padding: 16px 20px;
  font-family: 'Courier New', monospace;
  font-size: 14px; line-height: 1.65; color: var(--text);
  overflow-x: auto; white-space: pre; background: transparent;
  tab-size: 2;
}

/* Re-open bar */
.flyout-bar {
  position: absolute; bottom: 0; left: 0; right: 0;
  display: flex; align-items: center; gap: 10px;
  padding: 8px 20px; border-top: 1px solid var(--border);
  background: var(--bg); cursor: pointer;
  font-size: 13px; color: var(--muted);
  transition: color .12s, background .12s;
  z-index: 100;
}
.flyout-bar:hover { color: var(--text); background: var(--hover); }
.flyout-bar-method {
  font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 3px; color: #fff;
}
.flyout-bar-method.get    { background: #10B981; }
.flyout-bar-method.post   { background: #3B82F6; }
.flyout-bar-method.put    { background: #8B5CF6; }
.flyout-bar-method.patch  { background: #F59E0B; }
.flyout-bar-method.delete { background: #EF4444; }
.flyout-bar-path { font-family: 'Courier New', monospace; font-size: 12px; color: var(--muted); }

/* Transitions */
.flyout-enter-active, .flyout-leave-active { transition: height .25s ease; }
.flyout-enter-from, .flyout-leave-to       { height: 0 !important; }
.bar-enter-active, .bar-leave-active { transition: opacity .2s; }
.bar-enter-from, .bar-leave-to       { opacity: 0; }
</style>
