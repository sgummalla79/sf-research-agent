export const API = {
  // ── Auth ──────────────────────────────────────────────────────────────────
  me:       '/auth/me',
  initiate: '/auth/initiate',
  token:    '/auth/token',
  logout:   '/auth/logout',

  // ── Providers ─────────────────────────────────────────────────────────────
  providers:                  '/api/providers',
  providerConnect:  (id)   => `/api/providers/${id}/connect`,
  providerRefresh:  (id)   => `/api/providers/${id}/refresh`,
  providerDelete:   (id)   => `/api/providers/${id}`,

  // ── Skills ────────────────────────────────────────────────────────────────
  skills:                     '/api/skills',
  skillInstall:     (id)   => `/api/skills/${id}`,
  skillUninstall:   (id)   => `/api/skills/${id}`,
  skillAgents:      (id)   => `/api/skills/${id}/agents`,
  agentDraft:   (sid, ak) => `/api/skills/${sid}/agents/${ak}/draft`,
  agentPublish: (sid, ak) => `/api/skills/${sid}/agents/${ak}/publish`,
  skillPublish:     (id)   => `/api/skills/${id}/publish`,

  // ── Conversations ─────────────────────────────────────────────────────────
  conversations:              '/api/conversations',
  conversation:     (id)   => `/api/conversations/${id}`,
  conversationMsg:  (id)   => `/api/conversations/${id}/message`,
  conversationSkills:(id)  => `/api/conversations/${id}/skills`,
  conversationSkill:(id,sid)=> `/api/conversations/${id}/skills/${sid}`,
  skillConfig: (id, sid)   => `/api/conversations/${id}/skills/${sid}/config`,
  skillInvoke: (id, sid)   => `/api/conversations/${id}/skills/${sid}/invoke`,

  // ── Executions ────────────────────────────────────────────────────────────
  executionReply:   (eid)  => `/api/executions/${eid}/reply`,
  executionRetry:   (eid)  => `/api/executions/${eid}/retry`,
  executionStages:  (eid)  => `/api/executions/${eid}/stages`,
  executionArtifacts:(eid) => `/api/executions/${eid}/artifacts`,

  // ── Artifacts ─────────────────────────────────────────────────────────────
  artifact:         (id)   => `/api/artifacts/${id}`,

  // ── Usage ─────────────────────────────────────────────────────────────────
  conversationUsage:(id)   => `/api/conversations/${id}/usage`,
  usageSummary:             '/api/usage/summary',
}
