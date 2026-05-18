import { API_BASE } from './config.js'

export const API = {
  // ── Auth ──────────────────────────────────────────────────────────────────
  me:       `${API_BASE}/auth/me`,
  initiate: `${API_BASE}/auth/initiate`,
  token:    `${API_BASE}/auth/token`,
  logout:   `${API_BASE}/auth/logout`,

  // ── Providers ─────────────────────────────────────────────────────────────
  providers:                  `${API_BASE}/api/providers`,
  providerConnect:  (id)   => `${API_BASE}/api/providers/${id}/connect`,
  providerRefresh:  (id)   => `${API_BASE}/api/providers/${id}/refresh`,
  providerDelete:   (id)   => `${API_BASE}/api/providers/${id}`,

  // ── Skills ────────────────────────────────────────────────────────────────
  skills:                     `${API_BASE}/api/skills`,
  skillInstall:     (id)   => `${API_BASE}/api/skills/${id}`,
  skillUninstall:   (id)   => `${API_BASE}/api/skills/${id}`,
  skillAgents:      (id)   => `${API_BASE}/api/skills/${id}/agents`,
  agentDraft:   (sid, ak) => `${API_BASE}/api/skills/${sid}/agents/${ak}/draft`,
  agentPublish: (sid, ak) => `${API_BASE}/api/skills/${sid}/agents/${ak}/publish`,
  skillPublish:     (id)   => `${API_BASE}/api/skills/${id}/publish`,

  // ── Conversations ─────────────────────────────────────────────────────────
  conversations:              `${API_BASE}/api/conversations`,
  conversation:     (id)   => `${API_BASE}/api/conversations/${id}`,
  conversationMsg:  (id)   => `${API_BASE}/api/conversations/${id}/message`,
  conversationSkills:(id)  => `${API_BASE}/api/conversations/${id}/skills`,
  conversationSkill:(id,sid)=> `${API_BASE}/api/conversations/${id}/skills/${sid}`,
  skillConfig: (id, sid)   => `${API_BASE}/api/conversations/${id}/skills/${sid}/config`,
  skillInvoke: (id, sid)   => `${API_BASE}/api/conversations/${id}/skills/${sid}/invoke`,

  // ── Executions ────────────────────────────────────────────────────────────
  executionReply:   (eid)  => `${API_BASE}/api/executions/${eid}/reply`,
  executionRetry:   (eid)  => `${API_BASE}/api/executions/${eid}/retry`,
  executionStages:  (eid)  => `${API_BASE}/api/executions/${eid}/stages`,
  executionArtifacts:(eid) => `${API_BASE}/api/executions/${eid}/artifacts`,

  // ── Artifacts ─────────────────────────────────────────────────────────────
  artifact:         (id)   => `${API_BASE}/api/artifacts/${id}`,

  // ── Usage ─────────────────────────────────────────────────────────────────
  conversationUsage:(id)   => `${API_BASE}/api/conversations/${id}/usage`,
  usageSummary:             `${API_BASE}/api/usage/summary`,
}
