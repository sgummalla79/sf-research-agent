/**
 * Api — single entry point for every HTTP call in the app.
 *
 * Two return types:
 *   json methods  — parse the response body, throw on non-ok
 *   raw  methods  — return the raw Response (SSE streams, complex error branches)
 *
 * Nothing outside this file should import apiFetch or build API URLs.
 */

import { apiFetch } from '../composables/useFetch.js'
import { API_BASE  } from './config.js'

// ── Internal helpers ──────────────────────────────────────────────────────────

async function json(url, options = {}) {
  const res = await apiFetch(url, options)
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try { msg = (await res.json()).detail || msg } catch {}
    throw new Error(msg)
  }
  return res.json()
}

function raw(url, options = {}) {
  return apiFetch(url, options)
}

function b(data) { return JSON.stringify(data) }

// ── Service ───────────────────────────────────────────────────────────────────

export const Api = {

  // ── Auth ───────────────────────────────────────────────────────────────────
  me: async () => {
    const res = await apiFetch('/auth/me')
    if (!res.ok) return null
    return res.json()
  },
  connections:  ()                          => json('/auth/connections').then(d => d.connections ?? []),
  login:        (email, password, conn)     => json('/auth/token', { method: 'POST', body: b({ email, password, connection: conn }) }),
  logout:       ()                          => raw('/auth/logout', { method: 'POST' }),
  initiateLogin:(conn)                      => { window.location.href = `${API_BASE}/auth/initiate${conn ? `?connection=${encodeURIComponent(conn)}` : ''}` },

  // ── About ──────────────────────────────────────────────────────────────────
  about: () => json('/api/about'),

  // ── Settings ───────────────────────────────────────────────────────────────
  getTheme: async () => {
    try {
      const res = await apiFetch('/api/settings/theme')
      if (!res.ok) return null
      const d = await res.json()
      return d.theme ?? null
    } catch { return null }
  },
  saveTheme: async (themeId) => {
    try { await raw('/api/settings/theme', { method: 'POST', body: b({ theme: themeId }) }) }
    catch (e) { console.error('[theme] save error:', e) }
  },

  // ── Providers ──────────────────────────────────────────────────────────────
  getProviders:           ()                       => json('/api/providers'),
  getProviderModels:      (pid)                    => json(`/api/providers/${pid}/models`),
  updateModelDisplayName: (pid, modelId, name)     => json(`/api/providers/${pid}/models/${encodeURIComponent(modelId)}/display-name`, { method: 'PATCH', body: b({ display_name: name }) }),
  updateModel:            (pid, modelId, data)     => json(`/api/providers/${pid}/models/${encodeURIComponent(modelId)}`, { method: 'PATCH', body: b(data) }),
  refreshProvider:        (pid)                    => json(`/api/providers/${pid}/refresh`, { method: 'POST' }),
  connectProvider:        (pid, data)              => raw(`/api/providers/${pid}/connect`, { method: 'POST', body: b(data) }),
  connectBedrock:         (data)                   => raw('/api/providers/bedrock/connect', { method: 'POST', body: b(data) }),
  deleteProvider:         (pid)                    => raw(`/api/providers/${pid}`, { method: 'DELETE' }),
  deleteBedrock:          ()                       => raw('/api/providers/bedrock', { method: 'DELETE' }),
  toggleProvider:         (pid)                    => raw(`/api/providers/${pid}/toggle`, { method: 'PATCH' }),
  toggleBedrock:          ()                       => raw('/api/providers/bedrock/toggle', { method: 'PATCH' }),

  // ── Models ─────────────────────────────────────────────────────────────────
  getActiveModels: () => json('/api/models/active'),

  // ── Skills ─────────────────────────────────────────────────────────────────
  getSkills:        ()                 => json('/api/skills'),
  installSkill:     (id)               => json(`/api/skills/${id}`, { method: 'POST' }),
  uninstallSkill:   (id)               => raw(`/api/skills/${id}`, { method: 'DELETE' }),
  getSkillAgents:   (id)               => json(`/api/skills/${id}/agents`),
  publishSkill:     (id)               => json(`/api/skills/${id}/publish`, { method: 'POST' }),
  publishAgent:     (sid, ak)          => json(`/api/skills/${sid}/agents/${ak}/publish`, { method: 'POST' }),
  saveDraft:        (sid, ak, content) => raw(`/api/skills/${sid}/agents/${ak}/draft`, { method: 'PUT',  body: b({ content }) }),
  deleteDraft:      (sid, ak)          => raw(`/api/skills/${sid}/agents/${ak}/draft`, { method: 'DELETE' }),
  updateAgentModel: (sid, ak, data)    => json(`/api/skills/${sid}/agents/${ak}/model`, { method: 'PATCH', body: b(data) }),
  validateBrief:    (id, data)         => json(`/api/skills/${id}/validate-brief`, { method: 'POST', body: b(data) }),
  classifyChoice:   (data)             => json('/api/skills/classify-choice', { method: 'POST', body: b(data) }),
  suggestConfig:    (id)               => json(`/api/skills/${id}/suggest-config`),

  // ── Conversations ──────────────────────────────────────────────────────────
  getConversations:     ()              => json('/api/conversations'),
  createConversation:   (data)          => json('/api/conversations', { method: 'POST', body: b(data) }),
  getConversation:      (id)            => json(`/api/conversations/${id}`),
  renameConversation:   (id, title)     => json(`/api/conversations/${id}`, { method: 'PATCH', body: b({ title }) }),
  deleteConversation:   (id)            => raw(`/api/conversations/${id}`, { method: 'DELETE' }),
  pinConversation:      (id)            => raw(`/api/conversations/${id}/pin`, { method: 'POST' }),
  unpinConversation:    (id)            => raw(`/api/conversations/${id}/pin`, { method: 'DELETE' }),
  getConversationUsage: (id)            => json(`/api/conversations/${id}/usage`),
  addMessage:           (id, data)      => raw(`/api/conversations/${id}/messages`, { method: 'POST', body: b(data) }),

  // ── Conversation skills ────────────────────────────────────────────────────
  addSkill:        (cid, skillId)       => raw(`/api/conversations/${cid}/skills`, { method: 'POST', body: b({ skill_id: skillId }) }),
  removeSkill:     (cid, csid)          => raw(`/api/conversations/${cid}/skills/${csid}`, { method: 'DELETE' }),
  getSkillConfig:  (cid, csid)          => json(`/api/conversations/${cid}/skills/${csid}/config`),
  saveSkillConfig: (cid, csid, agents)  => json(`/api/conversations/${cid}/skills/${csid}/config`, { method: 'PATCH', body: b({ agents }) }),

  // ── Streaming — return raw Response, caller reads .body ───────────────────
  sendMessage:     (cid, data)          => raw(`/api/conversations/${cid}/message`, { method: 'POST', body: b(data) }),
  invokeSkill:     (cid, csid, data)    => raw(`/api/conversations/${cid}/skills/${csid}/invoke`, { method: 'POST', body: b(data) }),
  reply:           (eid, data)          => raw(`/api/executions/${eid}/reply`, { method: 'POST', body: b(data) }),
  retry:           (eid)                => raw(`/api/executions/${eid}/retry`, { method: 'POST' }),

  // ── Executions ─────────────────────────────────────────────────────────────
  getStages:             (eid)          => json(`/api/executions/${eid}/stages`),
  getExecutionArtifacts: (eid)          => json(`/api/executions/${eid}/artifacts`),

  // ── Artifacts ──────────────────────────────────────────────────────────────
  getArtifact: (id) => json(`/api/artifacts/${id}`),

  // ── Uploads ────────────────────────────────────────────────────────────────
  upload: (formData) => raw('/api/uploads', { method: 'POST', body: formData }),

  // ── Usage ──────────────────────────────────────────────────────────────────
  getUsageSummary: () => json('/api/usage/summary'),

  // ── OpenAPI spec ───────────────────────────────────────────────────────────
  getOpenApiSpec: () => json('/openapi.json'),
}
