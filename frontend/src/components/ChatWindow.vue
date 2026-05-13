<template>
  <div class="shell" :class="{ dark: isDark }">

  <!-- ══════════════════ SETTINGS PAGE (full-page overlay) ══════════════════ -->
  <SettingsPage       v-if="appView === 'settings'"       @back="appView = 'chat'" />
  <ConfigurationPage  v-else-if="appView === 'configuration'" @back="appView = 'chat'" />

  <!-- ══════════════════ MAIN CHAT SHELL ══════════════════ -->
  <div v-else class="shell-chat">
  <!-- ══════════════════ PRIVACY BANNER ══════════════════ -->
  <div class="shell-body">

    <!-- ═══════════════════ SIDEBAR ═══════════════════ -->
    <div class="sidebar" :class="{ collapsed: !sidebar.open }">

      <!-- ── EXPANDED ────────────────────────────────────── -->
      <template v-if="sidebar.open">

        <!-- Brand header -->
        <div class="sb-header">
          <SudarshanChakra :size="22" color="#ffd080" />
          <span class="sb-app-name">Prajna</span>
          <button class="sb-collapse-btn" title="Collapse sidebar" @click="sidebar.open = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="18" height="18">
              <rect x="2" y="2" width="20" height="20" rx="5"/>
              <line x1="9" y1="2" x2="9" y2="22"/>
            </svg>
          </button>
        </div>

        <!-- New Chat -->
        <button class="sb-action-row" @click="handleNewChat">
          <span class="sba-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="16" height="16"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></span>
          <span class="sba-label">New Chat</span>
        </button>

        <!-- Chats section header — clickable, opens full chats view -->
        <button class="sb-action-row" :class="{ 'sb-active-row': currentView === 'chats' }" @click="openChatsView">
          <span class="sba-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" width="16" height="16">
              <path d="M17 8h2a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-1v3l-3-3h-3"/>
              <path d="M13 3H4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h1v3l3-3h5a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z"/>
            </svg>
          </span>
          <span class="sba-label">Chats</span>
        </button>

        <!-- Chat list — pinned section + recent section -->
        <div class="sb-list">
          <div v-if="!filteredChats.length" class="sb-empty">No conversations yet</div>

          <!-- Pinned -->
          <template v-if="sidebar.pinned.filter(s => !searchQuery || (s.brief_snippet||'').toLowerCase().includes(searchQuery.toLowerCase())).length">
            <div class="sb-section-hdr">📌 Pinned</div>
            <div v-for="s in sidebar.pinned.filter(s => !searchQuery || (s.brief_snippet||'').toLowerCase().includes(searchQuery.toLowerCase()))"
              :key="s.thread_id"
              class="sb-row" :class="{ active: s.thread_id === sessionId, 'menu-open': menuOpenId === s.thread_id }"
              @click="editingId !== s.thread_id && restoreSession(s.thread_id)">
              <input v-if="editingId === s.thread_id" class="rename-input"
                v-model="editingTitle" ref="renameInputRef"
                @blur="saveRename(s.thread_id)" @keydown.enter.prevent="saveRename(s.thread_id)"
                @keydown.esc="editingId = null" @click.stop />
              <span v-else class="sb-row-title">{{ s.brief_snippet || 'New conversation' }}</span>
              <div v-if="editingId !== s.thread_id" class="sb-row-menu" @click.stop>
                <button class="sb-more-btn" :class="{ active: menuOpenId === s.thread_id }"
                  @click="toggleMenu(s.thread_id)">
                  <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                    <circle cx="12" cy="5"  r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/>
                  </svg>
                </button>
                <div v-if="menuOpenId === s.thread_id" class="sb-ctx-menu">
                  <button class="ctx-item" @click="unpinSession(s.thread_id); menuOpenId = null">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    Unpin
                  </button>
                  <button class="ctx-item" @click="startRename(s); menuOpenId = null">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    Rename
                  </button>
                  <div class="ctx-divider"/>
                  <button class="ctx-item ctx-delete" @click="confirmDelete(s); menuOpenId = null">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                    Delete
                  </button>
                </div>
              </div>
            </div>
          </template>

          <!-- Recent -->
          <template v-if="sidebar.recent.filter(s => !searchQuery || (s.brief_snippet||'').toLowerCase().includes(searchQuery.toLowerCase())).length">
            <div class="sb-divider"/>
            <div class="sb-section-hdr">Recent</div>
            <div v-for="s in sidebar.recent.filter(s => !searchQuery || (s.brief_snippet||'').toLowerCase().includes(searchQuery.toLowerCase()))"
              :key="s.thread_id"
              class="sb-row" :class="{ active: s.thread_id === sessionId, 'menu-open': menuOpenId === s.thread_id }"
              @click="editingId !== s.thread_id && restoreSession(s.thread_id)">
              <input v-if="editingId === s.thread_id" class="rename-input"
                v-model="editingTitle"
                @blur="saveRename(s.thread_id)" @keydown.enter.prevent="saveRename(s.thread_id)"
                @keydown.esc="editingId = null" @click.stop />
              <span v-else class="sb-row-title">{{ s.brief_snippet || 'New conversation' }}</span>
              <div v-if="editingId !== s.thread_id" class="sb-row-menu" @click.stop>
                <button class="sb-more-btn" :class="{ active: menuOpenId === s.thread_id }"
                  @click="toggleMenu(s.thread_id)">
                  <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                    <circle cx="12" cy="5"  r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/>
                  </svg>
                </button>
                <div v-if="menuOpenId === s.thread_id" class="sb-ctx-menu">
                  <button class="ctx-item" @click="pinSession(s.thread_id); menuOpenId = null">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    Pin
                  </button>
                  <button class="ctx-item" @click="startRename(s); menuOpenId = null">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    Rename
                  </button>
                  <div class="ctx-divider"/>
                  <button class="ctx-item ctx-delete" @click="confirmDelete(s); menuOpenId = null">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                    Delete
                  </button>
                </div>
              </div>
            </div>
          </template>

        </div>

      </template>

      <!-- ── COLLAPSED ────────────────────────────────────── -->
      <template v-else>
        <button class="col-icon-btn brand" title="Prajna" @click="sidebar.open = true">
          <div class="sf-logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
              stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
              <rect x="2" y="2" width="20" height="20" rx="5"/>
              <line x1="9" y1="2" x2="9" y2="22"/>
            </svg>
          </div>
        </button>
        <button class="col-icon-btn" title="New Chat" @click="handleNewChat">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="18" height="18"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>
        <button class="col-icon-btn" :class="{ active: currentView === 'chats' }" title="Chats" @click="openChatsView">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" width="18" height="18">
            <path d="M17 8h2a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-1v3l-3-3h-3"/>
            <path d="M13 3H4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h1v3l3-3h5a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z"/>
          </svg>
        </button>
      </template>
    </div>

    <!-- ═══════════════ CHATS FULL-PAGE VIEW ══════════════ -->
    <div v-if="currentView === 'chats'" class="chat-pane chats-page">

      <!-- Header row -->
      <div class="cp-header">
        <h1 class="cp-heading">Chats</h1>
        <button class="cp-new-btn" @click="handleNewChat">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          New chat
        </button>
      </div>

      <!-- Search bar -->
      <div class="cp-search-wrap">
        <svg class="cp-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input v-model="searchQuery" class="cp-search" placeholder="Search your chats..." autofocus />
      </div>

      <!-- Subtitle -->
      <div class="cp-subtitle">Your conversations</div>

      <!-- Chat list -->
      <div class="cp-list">
        <div v-if="!filteredChats.length" class="cp-empty">No conversations found</div>

        <div v-for="s in filteredChats" :key="s.thread_id"
          class="cp-row" :class="{ active: s.thread_id === sessionId, 'menu-open': menuOpenId === s.thread_id }"
          @click="selectChat(s.thread_id)">
          <div class="cp-row-body">
            <div class="cp-row-title">{{ s.brief_snippet || 'New conversation' }}</div>
            <div class="cp-row-meta">{{ relativeTime(s.last_modified || s.created_at) }}</div>
          </div>
          <div class="cp-row-actions" @click.stop>
            <div class="sb-row-menu">
              <button class="sb-more-btn cp-more-btn" :class="{ active: menuOpenId === s.thread_id }"
                @click="toggleMenu(s.thread_id)">
                <svg viewBox="0 0 24 24" fill="currentColor" width="15" height="15">
                  <circle cx="12" cy="5"  r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/>
                </svg>
              </button>
              <div v-if="menuOpenId === s.thread_id" class="sb-ctx-menu cp-ctx-menu">
                <button class="ctx-item" @click="s.pinned ? unpinSession(s.thread_id) : pinSession(s.thread_id); menuOpenId = null">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                  {{ s.pinned ? 'Unpin' : 'Pin' }}
                </button>
                <button class="ctx-item" @click="startRename(s); menuOpenId = null">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  Rename
                </button>
                <div class="ctx-divider"/>
                <button class="ctx-item ctx-delete" @click="confirmDelete(s); menuOpenId = null">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- ═══════════════════ CHAT PANE ═══════════════════ -->
    <div v-else class="chat-pane">

      <!-- Progress strip -->
      <div class="progress-strip" :class="[currentStage, { visible: !!currentStage }]">
        <span class="p-dot" />
        <span class="p-text">{{ stageLabels[currentStage] }} is working…</span>
      </div>

      <!-- Active agent flow indicator (locked once session starts) -->
      <div v-if="sessionFlow && sessionId" class="session-flow-bar">
        <span class="sfb-icon">{{ sessionFlow.icon }}</span>
        <span class="sfb-name">{{ sessionFlow.name }}</span>
        <span class="sfb-label">active</span>
      </div>

      <!-- Messages -->
      <div class="messages" ref="messagesEl">
        <div v-if="!messages.length && !isStreaming" class="empty-state">
          <div class="greeting-row">
            <SudarshanChakra :size="48" />
            <h1 class="greeting-text">{{ greeting }}{{ firstName ? ', ' + firstName : '' }}</h1>
          </div>
        </div>

        <div v-for="(msg, i) in messages" :key="i" class="message" :class="msg.role">
          <span v-if="msg.role === 'agent'" class="stage-tag" :class="msg.stage">
            {{ stageLabels[msg.stage] || 'Agent' }}
          </span>

          <div v-if="msg.type === 'document'" class="doc-card">
            <span class="doc-card-icon">📄</span>
            <div class="doc-card-body">
              <p class="doc-card-title">Architecture Document v{{ msg.docVersion }}</p>
              <p class="doc-card-sub">Ready for review</p>
            </div>
            <button class="doc-card-btn" @click="openDocumentPanel(msg.docSessionId, msg.docVersion)">View →</button>
          </div>

          <div v-else-if="msg.type === 'preparing'" class="status-card preparing">
            <span class="spin" /> <span>{{ msg.content }}</span>
          </div>
          <div v-else-if="msg.type === 'reviewing'" class="status-card reviewing">
            <span class="spin" />
            <div><p class="sc-title">Review Agent is reviewing the document</p>
            <p class="sc-sub">Checking technical accuracy, completeness &amp; best practices…</p></div>
          </div>
          <div v-else-if="msg.type === 'approving'" class="status-card approving">
            <span class="spin" />
            <div><p class="sc-title">Approver Gate is evaluating the document</p>
            <p class="sc-sub">Assessing business value, audience fit &amp; strategic alignment…</p></div>
          </div>

          <div v-else-if="msg.type === 'review_result'" class="verdict-card" :class="msg.reviewPassed ? 'pass' : 'fail'">
            <div class="verdict-head"><span>{{ msg.reviewPassed ? '✅' : '❌' }}</span>
              <strong>Technical Review</strong>
              <span class="verdict-badge" :class="msg.reviewPassed ? 'badge-pass' : 'badge-fail'">{{ msg.reviewPassed ? 'PASSED' : 'FAILED' }}</span></div>
            <p class="verdict-body">{{ msg.reviewFeedback }}</p>
            <ul v-if="msg.criticalIssues?.length" class="verdict-list">
              <li v-for="(it, j) in msg.criticalIssues" :key="j">{{ it }}</li>
            </ul>
          </div>

          <div v-else-if="msg.type === 'approval_result'" class="verdict-card" :class="msg.approvalStatus === 'approved' ? 'pass' : 'fail'">
            <div class="verdict-head"><span>{{ msg.approvalStatus === 'approved' ? '🎉' : '🔄' }}</span>
              <strong>Approver Gate</strong>
              <span class="verdict-badge" :class="msg.approvalStatus === 'approved' ? 'badge-pass' : 'badge-fail'">{{ msg.approvalStatus?.toUpperCase() }}</span></div>
            <p class="verdict-body">{{ msg.approvalComments }}</p>
            <ul v-if="msg.requiredChanges?.length" class="verdict-list">
              <li v-for="(ch, j) in msg.requiredChanges" :key="j">{{ ch }}</li>
            </ul>
          </div>

          <template v-else>
            <div class="bubble" v-html="renderContent(msg.content)" />
            <span v-if="msg.isStreaming" class="cursor" />
          </template>
        </div>
      </div>

      <!-- Confirmation panel -->
      <div v-if="pendingConfirmation && !isComplete" class="confirm-panel">
        <div class="confirm-header">
          <span>📋</span>
          <div>
            <p class="confirm-title">Here's what I understood from your upload</p>
            <p class="confirm-sub">Read through this carefully. Add a correction below if anything is wrong.</p>
          </div>
        </div>
        <div class="confirm-content" v-html="renderContent(pendingConfirmation)" />
        <div class="confirm-footer">
          <textarea v-model="correctionText" class="ta" rows="2" placeholder="Optional: add a correction…" />
          <div class="action-row">
            <button class="btn-primary" @click="submitConfirmation" :disabled="isStreaming">
              Looks right — start discovery →
            </button>
          </div>
        </div>
      </div>

      <!-- Discovery reply -->
      <div v-if="pendingQuestions.length && !isComplete && !isInvalidInput" class="input-panel">
        <template v-if="pendingQuestions.length === 1">
          <div class="input-row">
            <textarea v-model="replyAnswers[0]" class="ta" placeholder="Type your answer…" rows="2"
              @keydown.enter.exact.prevent="submitReplies" />
            <button class="btn-send" @click="submitReplies" :disabled="!replyAnswers[0]?.trim() || isStreaming">Send</button>
          </div>
        </template>
        <template v-else>
          <div class="multi-scroll">
            <div v-for="(q, i) in pendingQuestions" :key="i" class="multi-item">
              <label class="multi-label">{{ i + 1 }}. {{ q }}</label>
              <textarea v-model="replyAnswers[i]" class="ta" :placeholder="`Answer ${i + 1}…`" rows="2" />
            </div>
          </div>
          <div class="action-row">
            <button class="btn-primary" @click="submitReplies"
              :disabled="replyAnswers.some(a => !a?.trim()) || isStreaming">Send All Answers →</button>
          </div>
        </template>
      </div>

      <!-- Banners -->
      <div v-if="isResumable" class="banner warn">
        <span>⚡ This session was interrupted mid-run.</span>
        <button class="retry-btn" @click="retrySession">↺ Resume Session</button>
      </div>
      <div v-if="isComplete" class="banner ok">
        🎉 Document approved and finalised. Continue chatting below, or add a new skill to start a follow-up session.
      </div>
      <div v-if="isHalted"       class="banner warn">⚠️ Session halted after maximum revisions.</div>
      <div v-if="isInvalidInput" class="banner err">❌ Image doesn't appear to be architecture-related.</div>
      <div v-if="error" class="banner err">
        <span>{{ error }}</span>
        <button v-if="sessionId && !isComplete && !isHalted" class="retry-btn" @click="retrySession">
          ↺ Retry
        </button>
      </div>

      <!-- Chat input — shown for new sessions AND for follow-up chat on completed sessions -->
      <ChatInput
        v-if="(!sessionId || isComplete) && !isStreaming"
        :chat-models="chatModels"
        :flows="flows"
        :pending-flow="isComplete ? null : pendingFlow"
        :hint="isComplete ? 'Ask a question about your document, or use + to add a new skill…' : undefined"
        @submit="handleChatSubmit"
        @upload="handleChatUpload"
        @flow-select="startWithFlow"
        @cancel-flow="pendingFlow = null"
        @manage-skills="appView = 'configuration'"
      />

      <!-- Mid-session flow selection popup -->
      <transition name="fade">
        <div v-if="flowPopup.show" class="del-overlay" @click.self="flowPopup.show = false">
          <div class="del-dialog">
            <p class="del-title">Switch to {{ flowPopup.flow?.name }}?</p>
            <p class="del-body">Your current conversation will be saved. You'll describe your project in the new chat before the agent starts.</p>
            <div class="del-btns">
              <button class="del-cancel" @click="flowPopup.show = false">Cancel</button>
              <button class="del-confirm" style="background:var(--pri-h);border-color:var(--pri);color:#fff"
                @click="confirmFlowStart">New Chat →</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Fork confirmation — new skill or file on a completed session -->
      <transition name="fade">
        <div v-if="forkConfirm.show" class="del-overlay" @click.self="forkConfirm.show = false">
          <div class="del-dialog">
            <template v-if="forkConfirm.type === 'skill'">
              <p class="del-title">Start a new session with {{ forkConfirm.flow?.name }}?</p>
              <p class="del-body">
                Your approved architecture document will be used as a starting reference.
                The full <strong>{{ forkConfirm.flow?.name }}</strong> pipeline will run from there —
                discovery, research, review, and approval — producing a new document in a separate session.
              </p>
            </template>
            <template v-else>
              <p class="del-title">Start a new session with this file?</p>
              <p class="del-body">
                Uploading a file on a completed session starts a fresh session.
                Your current document is preserved — this will not modify it.
              </p>
            </template>
            <div class="del-btns">
              <button class="del-cancel" @click="forkConfirm.show = false">Cancel</button>
              <button class="del-confirm" style="background:var(--pri-h);border-color:var(--pri);color:#fff"
                @click="executeFork">Continue →</button>
            </div>
          </div>
        </div>
      </transition>

    </div><!-- /chat-pane -->

    <!-- ═══════════════════ DOCUMENT RIGHT PANEL ═══════════════════ -->
    <div class="doc-panel" :class="{ open: documentPanel.open }">
      <div class="doc-panel-header">
        <span class="doc-panel-title">📄 Architecture Document v{{ documentPanel.version }}</span>
        <div class="doc-panel-actions">
          <button class="ol-btn" title="Models used" @click="sessionModelsOpen = !sessionModelsOpen">⚙ Models</button>
          <button class="ol-btn" @click="downloadMD">⬇ Markdown</button>
          <button class="ol-btn accent" @click="doPDF">⬇ PDF</button>
          <button class="ol-btn close" @click="closeDocumentPanel">✕</button>
        </div>
      </div>
      <!-- Session model lock info -->
      <div v-if="sessionModelsOpen && sessionId" class="session-models-bar">
        <div v-if="!sessionModelConfig" class="sm-loading">Loading model config…</div>
        <template v-else>
          <div class="sm-heading">Models locked for this session (read-only)</div>
          <div class="sm-rows">
            <div v-for="(cfg, slot) in sessionModelConfig" :key="slot" class="sm-row">
              <span class="sm-slot">{{ slotLabels[slot] || slot }}</span>
              <span class="sm-value">{{ cfg.provider }} / {{ cfg.model }}</span>
            </div>
          </div>
        </template>
      </div>
      <div class="doc-panel-body">
        <div v-if="documentPanel.loading" class="doc-loading"><span class="spin large" /> Loading…</div>
        <div v-else class="doc-content" v-html="renderContent(documentPanel.content)" />
      </div>
    </div>

  </div><!-- /shell-body -->

  <!-- ═══════════ SHELL FOOTER — full-width, one border-top ════════════ -->
  <div class="shell-footer" @click.stop>

    <!-- Avatar area — matches sidebar width -->
    <div class="sf-avatar-area" :class="{ collapsed: !sidebar.open }">
      <button class="avatar-btn" @click="userMenuOpen = !userMenuOpen">
        <img v-if="user?.picture" :src="user.picture" class="avatar-photo" />
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
          <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
        </svg>
        <div v-if="sidebar.open && user" class="avatar-user-info">
          <span class="avatar-user-name">{{ user.name || user.email }}</span>
          <span class="avatar-user-email">{{ user.email }}</span>
        </div>
      </button>
      <transition name="um-pop">
        <div v-if="userMenuOpen" class="user-menu">
          <button class="um-item" @click="openSettings(); userMenuOpen = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            Settings
          </button>
          <button class="um-item" @click="appView = 'configuration'; userMenuOpen = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
            Configuration
          </button>
          <button class="um-item" @click="openUsage(); userMenuOpen = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            Usage
          </button>
          <div class="um-divider"></div>
          <div class="um-section-label">Appearance</div>
          <button class="um-item" @click="isDark = !isDark; userMenuOpen = false">
            <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
            {{ isDark ? 'Light mode' : 'Dark mode' }}
          </button>
          <div class="um-divider"></div>
          <button class="um-item um-signout" @click="handleLogout">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            Sign out
          </button>
        </div>
      </transition>
    </div>

    <!-- Usage bar — takes remaining width -->
    <div class="usage-bar" v-if="sessionUsage.loaded && sessionId">
      <div class="ub-cell ub-total">
        <span class="ub-name">Session</span>
        <span class="ub-tokens">↑ {{ fmtTokens(sessionUsage.input_tokens) }} &nbsp;↓ {{ fmtTokens(sessionUsage.output_tokens) }}</span>
        <span class="ub-cost">{{ fmtCost(sessionUsage.cost_usd) }}</span>
      </div>
      <template v-for="row in sessionUsage.breakdown" :key="row.model">
        <div class="ub-sep"/>
        <div class="ub-cell">
          <span class="ub-name">{{ modelLabel(row.model) }}</span>
          <span class="ub-tokens">↑ {{ fmtTokens(row.input_tokens) }} &nbsp;↓ {{ fmtTokens(row.output_tokens) }}</span>
          <span class="ub-cost">{{ fmtCost(row.cost_usd) }}</span>
        </div>
      </template>
    </div>
    <div v-else class="usage-bar-empty"/>

  </div><!-- /shell-footer -->

  <!-- ══════════════════ PRIVACY STATUS BAR ══════════════════ -->
  <div class="privacy-banner">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
    <span>All conversations are <strong>incognito</strong> · Data never leaves <strong>your machine</strong> · Your inputs are <strong>never used</strong> to train AI models · No data is persisted by model providers</span>
  </div>

    <!-- ═══════════════════ USAGE MODAL ════════════════════ -->
    <transition name="fade">
      <div v-if="usageOpen" class="del-overlay" @click.self="usageOpen = false">
        <div class="settings-dialog" style="width:540px" @click.stop>
          <div class="settings-header">
            <span class="settings-title">Usage &amp; Cost Estimate</span>
            <button class="settings-close" @click="usageOpen = false">✕</button>
          </div>
          <div class="settings-body">
            <div v-if="globalUsage.loading" style="text-align:center;padding:20px;color:var(--muted)">Loading…</div>
            <template v-else>
              <div class="settings-section-label">All Sessions ({{ globalUsage.session_count }} with usage data)</div>
              <div class="usage-total-card">
                <div class="utc-stat"><span class="utc-val">{{ fmtTokens(globalUsage.totals.input_tokens) }}</span><span class="utc-lbl">↑ Input</span></div>
                <div class="utc-divider"/>
                <div class="utc-stat"><span class="utc-val">{{ fmtTokens(globalUsage.totals.output_tokens) }}</span><span class="utc-lbl">↓ Output</span></div>
                <div class="utc-divider"/>
                <div class="utc-stat"><span class="utc-val utc-cost">{{ fmtCost(globalUsage.totals.cost_usd) }}</span><span class="utc-lbl">Est. cost</span></div>
              </div>
              <div v-if="globalUsage.breakdown.length" class="settings-section-label" style="margin-top:4px">By Agent</div>
              <div v-if="globalUsage.breakdown.length" class="usage-table">
                <div class="ut-header">
                  <span>Agent</span><span>↑ Input</span><span>↓ Output</span><span>Est. cost</span>
                </div>
                <div v-for="row in globalUsage.breakdown" :key="row.model" class="ut-row">
                  <span>{{ modelLabel(row.model) }}</span>
                  <span>{{ fmtTokens(row.input_tokens) }}</span>
                  <span>{{ fmtTokens(row.output_tokens) }}</span>
                  <span class="ut-cost">{{ fmtCost(row.cost_usd) }}</span>
                </div>
              </div>
              <p v-if="!globalUsage.breakdown.length" style="color:var(--muted);font-size:13px;margin:0">No usage data yet. Start a session to see costs.</p>
              <p class="usage-disclaimer">Prices are estimates based on published API rates and may not reflect your exact billing.</p>
            </template>
          </div>
        </div>
      </div>
    </transition>

    <!-- ═══════════════════ SETTINGS MODAL ═══════════════════ -->
    <transition name="fade">
      <div v-if="settingsOpen" class="del-overlay" @click.self="settingsOpen = false">
        <div class="settings-dialog" @click.stop>
          <div class="settings-header">
            <span class="settings-title">Settings</span>
            <button class="settings-close" @click="settingsOpen = false">✕</button>
          </div>

          <div class="settings-body">
            <div class="settings-section-label">API Keys</div>
            <p class="settings-hint">Keys are encrypted at rest. Leave a field empty to keep the existing key.</p>

            <!-- Anthropic -->
            <div class="sk-row">
              <div class="sk-label-row">
                <span class="sk-label">Anthropic API Key</span>
                <span class="sk-badge" :class="keysConfigured.anthropic ? 'ok' : 'missing'">
                  {{ keysConfigured.anthropic ? 'Configured ✓' : 'Not set' }}
                </span>
              </div>
              <p class="sk-desc">Intake · Discovery · Research (writing) · Review · Approver</p>
              <input v-model="settingsKeys.anthropic" class="sk-input" :class="{ 'sk-input-err': settingsKeyErrors.anthropic }" type="password"
                :placeholder="keysConfigured.anthropic ? 'Enter new key to update…' : 'sk-ant-…'" autocomplete="off" />
              <p v-if="settingsKeyErrors.anthropic" class="sk-err">{{ settingsKeyErrors.anthropic }}</p>
            </div>

            <!-- Perplexity -->
            <div class="sk-row">
              <div class="sk-label-row">
                <span class="sk-label">Perplexity API Key</span>
                <span class="sk-badge" :class="keysConfigured.perplexity ? 'ok' : 'missing'">
                  {{ keysConfigured.perplexity ? 'Configured ✓' : 'Not set' }}
                </span>
              </div>
              <p class="sk-desc">Research Agent — live web search (Sonar Pro)</p>
              <input v-model="settingsKeys.perplexity" class="sk-input" :class="{ 'sk-input-err': settingsKeyErrors.perplexity }" type="password"
                :placeholder="keysConfigured.perplexity ? 'Enter new key to update…' : 'pplx-…'" autocomplete="off" />
              <p v-if="settingsKeyErrors.perplexity" class="sk-err">{{ settingsKeyErrors.perplexity }}</p>
            </div>

            <!-- Google -->
            <div class="sk-row">
              <div class="sk-label-row">
                <span class="sk-label">Google API Key</span>
                <span class="sk-badge" :class="keysConfigured.google ? 'ok' : 'missing'">
                  {{ keysConfigured.google ? 'Configured ✓' : 'Not set' }}
                </span>
              </div>
              <p class="sk-desc">Research Agent — architectural patterns (Gemini 2.5 Pro)</p>
              <input v-model="settingsKeys.google" class="sk-input" :class="{ 'sk-input-err': settingsKeyErrors.google }" type="password"
                :placeholder="keysConfigured.google ? 'Enter new key to update…' : 'AIza…'" autocomplete="off" />
              <p v-if="settingsKeyErrors.google" class="sk-err">{{ settingsKeyErrors.google }}</p>
            </div>

            <div v-if="settingsSaveMsg" class="settings-msg" :class="settingsSaveMsg.type">
              {{ settingsSaveMsg.text }}
            </div>
          </div>

          <div class="settings-footer">
            <button class="btn-primary" :disabled="settingsSaving" @click="saveSettings">
              {{ settingsSaving ? 'Validating…' : 'Save Keys' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- ═══════════════ DELETE CONFIRMATION ══════════════ -->
    <transition name="fade">
      <div v-if="deleteConfirm.show" class="del-overlay" @click.self="deleteConfirm.show = false">
        <div class="del-dialog">
          <p class="del-title">Delete conversation?</p>
          <p class="del-body">"{{ deleteConfirm.title }}"</p>
          <p class="del-warn">This cannot be undone.</p>
          <div class="del-btns">
            <button class="del-cancel" @click="deleteConfirm.show = false">Cancel</button>
            <button class="del-confirm" @click="executeDelete">Delete</button>
          </div>
        </div>
      </div>
    </transition>

  </div><!-- /shell-chat -->

  </div><!-- /shell -->
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import { useAgentChat } from '../composables/useAgentChat.js'
import { useAuth } from '../composables/useAuth.js'
import { apiFetch } from '../composables/useFetch.js'
import SettingsPage from './SettingsPage.vue'
import ConfigurationPage from './ConfigurationPage.vue'
import ChatInput from './ChatInput.vue'
import SudarshanChakra from './SudarshanChakra.vue'

const {
  sessionId, messages, currentStage, pendingQuestions, pendingConfirmation,
  isStreaming, isComplete, isHalted, isInvalidInput, isResumable, error,
  documentPanel, sidebar, sessionUsage,
  loadSessions, newChat, restoreSession,
  pinSession, unpinSession, deleteSession, renameSession,
  startSession, uploadDocument, confirmUnderstanding, sendReply, retrySession,
  sendMessage, forkSession,
  openDocumentPanel, closeDocumentPanel, downloadMD,
} = useAgentChat()

const router = useRouter()
const { user, logout } = useAuth()

const _GREETINGS = {
  morning: [
    'Good morning',       // English
    'Suprabhat',          // Sanskrit / Hindi
    'Bonjour',            // French
    'Buenos días',        // Spanish
    'Guten Morgen',       // German
    'Buongiorno',         // Italian
    'Bom dia',            // Portuguese
    'Günaydın',           // Turkish
    'Kalimera',           // Greek
    'Ohayou gozaimasu',   // Japanese
    'Subah bakhair',      // Urdu
    'Sabah alkhayr',      // Arabic
    'Dobroe utro',        // Russian
    'Selamat pagi',       // Malay/Indonesian
  ],
  afternoon: [
    'Good afternoon',
    'Shubh dopahar',      // Hindi
    'Bon après-midi',     // French
    'Buenas tardes',      // Spanish
    'Guten Nachmittag',   // German
    'Buon pomeriggio',    // Italian
    'Boa tarde',          // Portuguese
    'İyi öğleden sonralar', // Turkish
    'Konnichiwa',         // Japanese
    'Masa alkhayr',       // Arabic
    'Selamat siang',      // Malay
  ],
  evening: [
    'Good evening',
    'Shubh sandhya',      // Sanskrit
    'Bonsoir',            // French
    'Buenas noches',      // Spanish
    'Guten Abend',        // German
    'Buona sera',         // Italian
    'Boa noite',          // Portuguese
    'İyi akşamlar',       // Turkish
    'Konbanwa',           // Japanese
    'Masa alkhayr',       // Arabic
    'Selamat malam',      // Malay
  ],
}

const greeting = computed(() => {
  const h = new Date().getHours()
  const bucket = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening'
  const list = _GREETINGS[bucket]
  return list[Math.floor(Math.random() * list.length)]
})

const firstName = computed(() => {
  const name = user.value?.name || ''
  // Never use email — if name looks like an email or is empty, return nothing
  if (!name || name.includes('@')) return ''
  return name.split(/\s+/)[0]
})

async function handleLogout() {
  await logout()
  router.push('/login')
}

// App-level view
const appView      = ref('chat')   // 'chat' | 'settings' | 'configuration'

// View state
const currentView  = ref('chat')   // 'chat' | 'chats'
const searchQuery  = ref('')
const editingId      = ref(null)
const editingTitle   = ref('')
const renameInputRef = ref(null)

// Delete confirmation state
const deleteConfirm = ref({ show: false, threadId: null, title: '' })

// Three-dot context menu — tracks which row has its menu open
const menuOpenId = ref(null)
function toggleMenu(id) { menuOpenId.value = menuOpenId.value === id ? null : id }

// Fork confirmation — shown when user picks a new skill/file on a completed session
const forkConfirm = reactive({ show: false, flow: null, file: null, type: 'skill' })

function confirmDelete(s) {
  deleteConfirm.value = { show: true, threadId: s.thread_id, title: s.brief_snippet || 'this conversation' }
}
async function executeDelete() {
  await deleteSession(deleteConfirm.value.threadId)
  deleteConfirm.value.show = false
}

// Relative time helper
function relativeTime(iso) {
  if (!iso) return ''
  const diff  = Date.now() - new Date(iso).getTime()
  const mins  = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days  = Math.floor(diff / 86400000)
  if (mins  <  1) return 'Just now'
  if (mins  < 60) return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days  <  2) return 'Yesterday'
  if (days  < 30) return `Last message ${days} days ago`
  return 'Over a month ago'
}

function startRename(s) {
  editingId.value    = s.thread_id
  editingTitle.value = s.brief_snippet || ''
  nextTick(() => renameInputRef.value?.focus())
}
async function saveRename(threadId) {
  const title = editingTitle.value.trim()
  editingId.value = null
  if (title) await renameSession(threadId, title)
}

const isDark          = ref(true)
const userMenuOpen    = ref(false)
const settingsOpen    = ref(false)
const sessionModelsOpen  = ref(false)
const sessionModelConfig = ref(null)
const slotLabels = {
  discovery:            'Discovery',
  researcher_search:    'Research: Web Search',
  researcher_reasoning: 'Research: Architecture',
  researcher_writer:    'Research: Writer',
  reviewer:             'Review',
  approver:             'Approver',
}
const usageOpen       = ref(false)
const globalUsage     = reactive({ totals: { input_tokens: 0, output_tokens: 0, cost_usd: 0 }, breakdown: [], session_count: 0, loading: false })
const settingsKeys    = reactive({ anthropic: '', perplexity: '', google: '' })
const keysConfigured  = reactive({ anthropic: false, perplexity: false, google: false })
const settingsSaving   = ref(false)
const settingsSaveMsg  = ref(null)
const settingsKeyErrors = reactive({ anthropic: '', perplexity: '', google: '' })
const correctionText  = ref('')
const replyAnswers    = ref([])
const messagesEl      = ref(null)

// Chat model + flow state (passed to ChatInput as props)
const chatModels  = ref([])
const flows       = ref([])
const pendingFlow = ref(null)   // flow selected, session not yet started (cancellable)
const sessionFlow = ref(null)   // flow locked for the active session
const flowPopup   = reactive({ show: false, flow: null })


const stageLabels = {
  intake:    'Intake Agent',
  discovery: 'Discovery Agent',
  research:  'Research Agent',
  review:    'Review Agent',
  approval:  'Approver Gate',
}

// Flat sorted list: pinned first, then recent — filtered by search query
const filteredChats = computed(() => {
  const all = [...sidebar.pinned, ...sidebar.recent]
  const q   = searchQuery.value.trim().toLowerCase()
  return q ? all.filter(s => (s.brief_snippet || '').toLowerCase().includes(q)) : all
})

async function fetchKeyStatus() {
  try {
    const res = await apiFetch('/api/settings/keys')
    if (res.ok) {
      const data = await res.json()
      keysConfigured.anthropic  = !!data.anthropic
      keysConfigured.perplexity = !!data.perplexity
      keysConfigured.google     = !!data.google
    }
  } catch (_) {}
}

async function openUsage() {
  usageOpen.value   = true
  globalUsage.loading = true
  try {
    const res  = await apiFetch('/api/usage/summary')
    if (res.ok) {
      const data = await res.json()
      globalUsage.totals        = data.totals        ?? { input_tokens: 0, output_tokens: 0, cost_usd: 0 }
      globalUsage.breakdown     = data.breakdown     ?? []
      globalUsage.session_count = data.session_count ?? 0
    }
  } catch (_) {}
  finally { globalUsage.loading = false }
}

function openSettings() {
  userMenuOpen.value = false
  appView.value = 'settings'
}

async function saveSettings() {
  settingsSaving.value         = true
  settingsSaveMsg.value        = null
  settingsKeyErrors.anthropic  = ''
  settingsKeyErrors.perplexity = ''
  settingsKeyErrors.google     = ''
  try {
    const res = await fetch('/api/settings/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        anthropic:  settingsKeys.anthropic,
        perplexity: settingsKeys.perplexity,
        google:     settingsKeys.google,
      }),
    })
    const data = await res.json()
    if (res.ok) {
      keysConfigured.anthropic  = !!data.configured?.anthropic
      keysConfigured.perplexity = !!data.configured?.perplexity
      keysConfigured.google     = !!data.configured?.google
      settingsKeys.anthropic  = ''
      settingsKeys.perplexity = ''
      settingsKeys.google     = ''
      settingsSaveMsg.value = { type: 'ok', text: `Keys verified and saved.${data.saved.length ? '' : ' No changes.'}` }
    } else if (res.status === 422 && data.detail?.validation_errors) {
      const errs = data.detail.validation_errors
      settingsKeyErrors.anthropic  = errs.anthropic  || ''
      settingsKeyErrors.perplexity = errs.perplexity || ''
      settingsKeyErrors.google     = errs.google     || ''
      settingsSaveMsg.value = { type: 'err', text: 'One or more keys are invalid — see details above.' }
    } else {
      settingsSaveMsg.value = { type: 'err', text: data.detail || 'Save failed.' }
    }
  } catch (e) {
    settingsSaveMsg.value = { type: 'err', text: 'Network error. Is the backend running?' }
  } finally {
    settingsSaving.value = false
  }
}

async function fetchFlows() {
  try {
    const res = await apiFetch('/api/flows')
    if (res.ok) {
      const data = await res.json()
      flows.value = data.flows || []
      chatModels.value = data.chat_models || []
    }
  } catch (_) {}
}

function startWithFlow(flow) {
  if (isComplete.value) {
    // Session finished — ask before forking into a new session
    forkConfirm.flow = flow
    forkConfirm.file = null
    forkConfirm.type = 'skill'
    forkConfirm.show = true
    return
  }
  if (sessionId.value) {
    // Mid-session: ask user to confirm new chat first
    flowPopup.flow = flow
    flowPopup.show = true
  } else {
    // No session: arm the pending flow, wait for user to type description
    pendingFlow.value = flow
    currentView.value = 'chat'
  }
}

function confirmFlowStart() {
  const flow = flowPopup.flow
  flowPopup.show = false
  sessionFlow.value = null
  newChat()
  currentView.value = 'chat'
  pendingFlow.value = flow   // arm — session starts only when user submits
}

onMounted(() => {
  loadSessions()
  fetchKeyStatus()
  fetchFlows()
  document.addEventListener('click', () => { userMenuOpen.value = false; menuOpenId.value = null })
})
watch(pendingQuestions, qs => { replyAnswers.value = qs.map(() => '') })

// Fetch the session's locked model config whenever the session changes
watch(() => sessionId.value, async (id) => {
  sessionModelConfig.value = null
  sessionModelsOpen.value  = false
  if (!id) { sessionFlow.value = null; return }
  try {
    const res = await apiFetch(`/api/chat/session-config/${id}`)
    if (res.ok) {
      const data = await res.json()
      sessionModelConfig.value = data.config || null
    }
  } catch (_) {}
})
watch(messages, async () => {
  await nextTick()
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}, { deep: true })

marked.setOptions({ breaks: true })

const _VERDICT_PASS = '<span class="vb-pass">$&</span>'
const _VERDICT_FAIL = '<span class="vb-fail">$&</span>'

function renderContent(c) {
  if (!c) return ''
  if (Array.isArray(c)) c = c.filter(b => b?.type === 'text').map(b => b?.text ?? '').join('\n')
  else if (typeof c !== 'string') c = String(c)
  return marked.parse(c)
    .replace(/\bPASSED\b/g,   _VERDICT_PASS)
    .replace(/\bAPPROVED\b/g, _VERDICT_PASS)
    .replace(/\bFAILED\b/g,   _VERDICT_FAIL)
    .replace(/\bREJECTED\b/g, _VERDICT_FAIL)
}

const AGENT_LABELS = { intake: 'Intake Agent', discovery: 'Discovery Agent', researcher: 'Research Agent', reviewer: 'Review Agent', approver: 'Approver Gate' }
const MODEL_NAMES = {
  'claude-sonnet-4-6':         'Claude Sonnet 4.6',
  'claude-haiku-4-5-20251001': 'Claude Haiku 4.5',
  'sonar-pro':                 'Perplexity Sonar Pro',
  'gemini-2.5-pro':            'Gemini 2.5 Pro',
}
function modelLabel(m) { return MODEL_NAMES[m] || m }
function fmtTokens(n) { return n >= 1000 ? `${(n/1000).toFixed(1)}K` : String(n) }
function fmtCost(c)   { return c < 0.01 ? `$${(c).toFixed(4)}` : `$${c.toFixed(3)}` }

async function handleNewChat() {
  pendingFlow.value = null
  sessionFlow.value = null
  const missing = Object.entries(keysConfigured).filter(([, v]) => !v).map(([k]) => k)
  if (missing.length) {
    openSettings()
    settingsSaveMsg.value = { type: 'err', text: `Please save your API keys before starting a session. Missing: ${missing.join(', ')}.` }
    return
  }
  newChat()
  currentView.value = 'chat'
}
function openChatsView()       { searchQuery.value = ''; currentView.value = 'chats' }
function selectChat(threadId)  { restoreSession(threadId); currentView.value = 'chat' }
// ChatInput event handlers
async function handleChatSubmit(text, opts) {
  if (isComplete.value) {
    // Post-completion follow-up chat — stay in same session
    await sendMessage(text, opts.model)
    return
  }
  if (pendingFlow.value) {
    // Lock the flow for this session, then start
    sessionFlow.value = pendingFlow.value
    pendingFlow.value = null
    await startSession(text, { sessionType: 'agent_flow', flowId: sessionFlow.value.id })
  } else {
    await startSession(text, {
      sessionType:      'chat',
      chatModel:        opts.model,
      extendedThinking: opts.extendedThinking,
    })
  }
}
async function handleChatUpload(file) {
  if (isComplete.value) {
    // File upload on a completed session → fork into a new session
    forkConfirm.file = file
    forkConfirm.flow = null
    forkConfirm.type = 'file'
    forkConfirm.show = true
    return
  }
  await uploadDocument(file)
}

async function executeFork() {
  const prevId = sessionId.value
  const flow   = forkConfirm.flow
  const file   = forkConfirm.file
  forkConfirm.show = false

  if (forkConfirm.type === 'file' && file) {
    // File fork: start a completely fresh session with the uploaded file
    sessionFlow.value = null
    await uploadDocument(file)
    return
  }

  // Skill fork: new session seeded with the existing document
  if (!flow) return
  sessionFlow.value = flow
  await forkSession(prevId, flow)
}

async function submitConfirmation() { await confirmUnderstanding(correctionText.value); correctionText.value = '' }
async function submitReplies()      { if (replyAnswers.value.some(a => !a?.trim())) return; await sendReply(replyAnswers.value.map(a => a.trim())); replyAnswers.value = [] }

function doPDF() {
  if (!documentPanel.content) return
  const html = renderContent(documentPanel.content)
  const win  = window.open('', '_blank')
  win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Architecture Document v${documentPanel.version}</title>
  <style>@page{margin:2.2cm 2cm}*{box-sizing:border-box}body{font-family:-apple-system,system-ui,sans-serif;font-size:11pt;line-height:1.65;color:#111}
  h1{font-size:19pt;margin:1.2em 0 .4em}h2{font-size:14pt;margin:1em 0 .3em;border-bottom:1px solid #ddd;padding-bottom:4px}h3{font-size:11.5pt;font-weight:600;margin:.8em 0 .25em}
  p{margin:.45em 0}ul,ol{padding-left:1.5em;margin:.4em 0}li{margin:.2em 0}
  table{border-collapse:collapse;width:100%;margin:.7em 0;font-size:10pt;page-break-inside:avoid}th,td{border:1px solid #bbb;padding:6px 10px;text-align:left;vertical-align:top}th{background:#f2f2f2;font-weight:600}
  code{background:#f5f5f5;padding:1px 4px;border-radius:3px;font-size:9.5pt;font-family:'Courier New',monospace}pre{background:#f5f5f5;padding:10px 12px;border-radius:5px;overflow-x:auto;font-size:9.5pt;page-break-inside:avoid;margin:.6em 0}
  blockquote{border-left:3px solid #2563eb;padding-left:12px;color:#444;margin:.5em 0}strong{font-weight:600}
  @media print{body{print-color-adjust:exact;-webkit-print-color-adjust:exact}}</style></head><body>${html}</body></html>`)
  win.document.close()
  setTimeout(() => { win.focus(); win.print() }, 400)
}
</script>

<style scoped>
/* ── Variables ───────────────────────────────────────────────────────────────── */
.shell {
  --bg:       #f1f5f9; --surf:    #fff;  --surf2:  #f8fafc; --bdr:   #e2e8f0;
  --tx:       #0f172a; --muted:   #64748b;
  --pri:      #2563eb; --pri-h:   #1d4ed8; --pri-fg: #fff;
  --ub:       #2563eb; --uf:      #fff;
  --ab:       #fff;    --abdr:    #e2e8f0;
  --sbg:      #eff6ff; --stx:     #1d4ed8; --sbdr:  #bfdbfe;
  --hbg:      #1e293b; --hfg:     #f8fafc;
  --cbg:      #f1f5f9; --ibdr:    #cbd5e1; --ifocus: #2563eb;
  --pass-bg:  #f0fdf4; --pass-bdr:#bbf7d0; --pass-tx:#15803d;
  --fail-bg:  #fef2f2; --fail-bdr:#fecaca; --fail-tx:#b91c1c;
  --sb-bg:    #1a2535;   /* sidebar background */
  --sb-hover: #243044;
  --sb-active:#2d3f5a;
  --sb-tx:    #c8d4e6;
  --sb-muted: #6b7f99;
  --c-intake:#3b82f6;--c-discovery:#6366f1;--c-research:#8b5cf6;--c-review:#f59e0b;--c-approval:#10b981;
  --inp: #f8fafc; --hover: #f1f5f9; --active-nav: #eff6ff; --sidebar: #f8fafc;
}
.shell.dark {
  --bg:#1a1a1a;--surf:#212121;--surf2:#181818;--bdr:rgba(255,255,255,0.09);
  --tx:#ececea;--muted:#888888;--pri:#c97040;--pri-h:#b5602e;--pri-fg:#fff;
  --ub:#c97040;--ab:#212121;--abdr:rgba(255,255,255,0.09);
  --sbg:rgba(201,112,64,0.12);--stx:#d4945a;--sbdr:rgba(201,112,64,0.28);
  --hbg:#0e0e0e;--hfg:#ececea;--cbg:#1a1a1a;--ibdr:rgba(255,255,255,0.14);--ifocus:#c97040;
  --pass-bg:#0d1f10;--pass-bdr:#1a4620;--pass-tx:#86efac;
  --fail-bg:#1f0d0d;--fail-bdr:#4a1a1a;--fail-tx:#fca5a5;
  --inp:#111111;--hover:#282828;--active-nav:rgba(255,255,255,0.06);--sidebar:#141414;
  --sb-bg:#111111;--sb-hover:#1e1e1e;--sb-active:#252525;
  --sb-tx:#d9d9d7;--sb-muted:#5e5e5e;
  --c-intake:#c97040;--c-discovery:#a06030;--c-research:#8b5a28;--c-review:#b07820;--c-approval:#5a8a30;
}

/* ── Privacy banner ──────────────────────────────────────────────────────────── */
.privacy-banner {
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  height: 28px; padding: 0 20px;
  background: var(--sb-bg);
  border-top: 1px solid rgba(255,255,255,0.06);
  font-size: 11px; color: #a8bdd4; letter-spacing: 0.01em;
  white-space: nowrap; overflow: hidden;
}
.privacy-banner svg { flex-shrink: 0; opacity: 0.8; }
.privacy-banner strong { font-weight: 700; color: #d0e2f4; }

/* ── Shell ───────────────────────────────────────────────────────────────────── */

.shell {
  display: flex; flex-direction: column;
  width: 100%; height: 100%;
  border-radius: 14px; overflow: hidden;
  border: 1px solid var(--bdr);
  font-family: system-ui, -apple-system, sans-serif;
  color: var(--tx);
}
/* SettingsPage fills the full shell when open — deep selector needed because sp-root is scoped */
.shell :deep(.sp-root) { flex: 1; min-height: 0; }
/* Transparent wrapper — children stay direct flex items of .shell */
.shell-chat { display: contents; }
.shell-body {
  display: flex; flex-direction: row;
  flex: 1; min-height: 0;
}
/* ── Shell footer — single full-width bottom bar ─────────────────────────── */
.shell-footer {
  display: flex; flex-direction: row; flex-shrink: 0;
  border-top: 1px solid rgba(255,255,255,0.07);
  background: var(--sb-bg);
}
.sf-avatar-area {
  width: 240px; flex-shrink: 0;
  display: flex; align-items: center;
  padding: 6px 8px; position: relative;
  border-right: 1px solid rgba(255,255,255,0.06);
}
.sf-avatar-area.collapsed { width: 52px; justify-content: center; padding: 6px 0; }
.usage-bar-empty { flex: 1; }

/* ═══════════════════════ SIDEBAR ═══════════════════════ */
.sidebar {
  flex-shrink: 0;
  width: 240px;
  display: flex; flex-direction: column;
  background: var(--sb-bg);
  border-right: 1px solid rgba(255,255,255,0.06);
  transition: width 0.22s ease;
  overflow: visible;   /* allow flyout to overflow */
  position: relative;
  z-index: 10;
}
.sidebar.collapsed { width: 52px; overflow: visible; }

/* ── Shared icon ────────────────────────────────────────── */
.sf-logo {
  width: 32px; height: 32px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: var(--sb-muted);
}

/* ── Active sidebar row ──────────────────────────────────── */
.sb-active-row { background: var(--sb-active) !important; color: var(--sb-tx) !important; }

/* ═══════════════════ CHATS FULL-PAGE VIEW ══════════════════ */
.chats-page { background: var(--bg); color: var(--tx); }

/* Header */
.cp-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 28px 32px 20px; flex-shrink: 0;
}
.cp-heading { font-size: 28px; font-weight: 700; color: var(--tx); margin: 0; }
.cp-new-btn {
  display: flex; align-items: center; gap: 7px;
  padding: 9px 18px; background: transparent;
  border: 1.5px solid var(--bdr);
  border-radius: 10px; color: var(--tx); font-size: 14px; font-weight: 500;
  cursor: pointer; white-space: nowrap; transition: background .12s, border-color .12s;
}
.cp-new-btn:hover { background: var(--surf2); border-color: var(--input-border); }

/* Search bar */
.cp-search-wrap {
  position: relative; display: flex; align-items: center;
  padding: 0 32px 16px; flex-shrink: 0;
}
.cp-search-icon { position: absolute; left: 48px; color: var(--muted); pointer-events: none; }
.cp-search {
  width: 100%; padding: 13px 16px 13px 44px;
  background: var(--surf);
  border: 1.5px solid var(--ibdr);
  border-radius: 12px; color: var(--tx); font-size: 15px; outline: none;
  transition: border-color .15s; font-family: inherit;
}
.cp-search::placeholder { color: var(--muted); }
.cp-search:focus { border-color: var(--pri); }

/* Subtitle */
.cp-subtitle {
  padding: 0 32px 8px; font-size: 13px; color: var(--muted); flex-shrink: 0;
}

/* List */
.cp-list { flex: 1; overflow-y: auto; padding: 0; }
.cp-empty { color: var(--muted); font-size: 14px; padding: 60px 32px; }

.cp-row {
  display: flex; align-items: center;
  padding: 16px 32px; cursor: pointer; min-width: 0;
  border-bottom: 1px solid var(--bdr);
  transition: background .1s;
}
.cp-row:hover  { background: var(--surf2); }
.cp-row.active { background: var(--sbg); }
.cp-row-body { flex: 1; min-width: 0; }
.cp-row-title {
  font-size: 15px; font-weight: 500; color: var(--tx);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 3px;
}
.cp-row-meta { font-size: 13px; color: var(--muted); }
.cp-row-actions {
  display: flex; align-items: center; flex-shrink: 0; margin-left: 12px;
}

/* ═══════════════════════ SETTINGS MODAL ════════════════════ */
.settings-dialog {
  background: var(--surf); border: 1px solid var(--bdr);
  border-radius: 16px; width: 480px; max-width: 95%;
  box-shadow: 0 24px 64px rgba(0,0,0,0.4);
  display: flex; flex-direction: column; overflow: hidden;
}
.settings-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 24px; border-bottom: 1px solid var(--bdr); flex-shrink: 0;
}
.settings-title { font-size: 16px; font-weight: 700; color: var(--tx); }
.settings-close {
  width: 28px; height: 28px; border: none; border-radius: 6px;
  background: transparent; color: var(--muted); cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center; transition: background .12s;
}
.settings-close:hover { background: var(--surf2); color: var(--tx); }
.settings-body { padding: 20px 24px; display: flex; flex-direction: column; gap: 18px; overflow-y: auto; }
.settings-section-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); }
.settings-hint { font-size: 12px; color: var(--muted); margin: -10px 0 0; }
.settings-footer { padding: 16px 24px; border-top: 1px solid var(--bdr); display: flex; justify-content: flex-end; flex-shrink: 0; }

.sk-row { display: flex; flex-direction: column; gap: 5px; }
.sk-label-row { display: flex; align-items: center; gap: 10px; }
.sk-label { font-size: 14px; font-weight: 600; color: var(--tx); }
.sk-badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 99px; }
.sk-badge.ok      { background: var(--pass-bg); color: var(--pass-tx); }
.sk-badge.missing { background: var(--fail-bg);  color: var(--fail-tx); }
.sk-desc  { font-size: 12px; color: var(--muted); margin: 0; }
.sk-input {
  width: 100%; box-sizing: border-box;
  padding: 9px 12px; border: 1px solid var(--ibdr); border-radius: 8px;
  font-size: 13px; font-family: monospace; background: var(--surf2);
  color: var(--tx); outline: none; transition: border-color .15s;
}
.sk-input:focus    { border-color: var(--ifocus); }
.sk-input-err      { border-color: #ef4444 !important; }
.sk-input::placeholder { font-family: inherit; color: var(--muted); }
.sk-err { font-size: 12px; color: #ef4444; margin: 3px 0 0; }

.settings-msg { font-size: 13px; font-weight: 500; padding: 10px 14px; border-radius: 8px; }
.settings-msg.ok  { background: var(--pass-bg); color: var(--pass-tx); }
.settings-msg.err { background: var(--fail-bg);  color: var(--fail-tx); }

.um-divider { height: 1px; background: rgba(255,255,255,0.08); margin: 4px 0; }

/* ── Session usage bar ───────────────────────────────────────────────────── */
.usage-bar {
  flex: 1; display: flex; align-items: stretch;
  background: var(--surf2);
  font-size: 11px;
}
.ub-cell {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 5px 6px; gap: 1px; min-width: 0;
}
.ub-total { background: rgba(37,99,235,0.05); }
.dark .ub-total { background: rgba(59,130,246,0.08); }
.ub-sep   { width: 1px; background: var(--bdr); flex-shrink: 0; margin: 5px 0; }
.ub-name  { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); white-space: nowrap; }
.ub-tokens{ color: var(--tx); font-weight: 500; white-space: nowrap; }
.ub-cost  { color: var(--pri); font-weight: 600; white-space: nowrap; }
.ub-idle  { color: var(--muted); font-size: 13px; }

/* ── Usage modal ─────────────────────────────────────────────────────────── */
.usage-total-card {
  display: flex; align-items: center;
  background: var(--surf2); border: 1px solid var(--bdr);
  border-radius: 10px; padding: 16px 20px; gap: 0;
}
.utc-stat  { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px; }
.utc-val   { font-size: 20px; font-weight: 700; color: var(--tx); }
.utc-cost  { color: var(--pri); }
.utc-lbl   { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }
.utc-divider { width: 1px; height: 40px; background: var(--bdr); flex-shrink: 0; }
.usage-table  { border: 1px solid var(--bdr); border-radius: 8px; overflow: hidden; font-size: 13px; }
.ut-header {
  display: grid; grid-template-columns: 1fr 80px 80px 80px;
  padding: 8px 12px; background: var(--surf2);
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .05em; color: var(--muted); border-bottom: 1px solid var(--bdr);
}
.ut-row {
  display: grid; grid-template-columns: 1fr 80px 80px 80px;
  padding: 8px 12px; border-bottom: 1px solid var(--bdr); color: var(--tx);
}
.ut-row:last-child { border-bottom: none; }
.ut-cost { color: var(--pri); font-weight: 600; }
.usage-disclaimer { font-size: 11px; color: var(--muted); margin: 4px 0 0; }

/* ═══════════════════ DELETE CONFIRMATION ══════════════════ */
.del-overlay {
  position: absolute; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(2px);
}
.del-dialog {
  background: var(--surf); border: 1px solid var(--bdr);
  border-radius: 14px; padding: 24px 28px;
  width: 340px; max-width: 90%;
  box-shadow: 0 20px 60px rgba(0,0,0,0.4);
}
.del-title { font-size: 16px; font-weight: 700; color: var(--tx); margin: 0 0 8px; }
.del-body  { font-size: 14px; color: var(--tx); margin: 0 0 6px; font-style: italic; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.del-warn  { font-size: 13px; color: var(--muted); margin: 0 0 20px; }
.del-btns  { display: flex; gap: 10px; justify-content: flex-end; }
.del-cancel {
  padding: 8px 18px; border: 1px solid var(--bdr);
  border-radius: 8px; background: transparent; color: var(--tx);
  font-size: 14px; cursor: pointer; transition: background .12s;
}
.del-cancel:hover { background: var(--surf2); }
.del-confirm {
  padding: 8px 18px; border: none;
  border-radius: 8px; background: #dc2626; color: #fff;
  font-size: 14px; font-weight: 600; cursor: pointer; transition: background .12s;
}
.del-confirm:hover { background: #b91c1c; }
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── EXPANDED header ────────────────────────────────────── */
.sb-header {
  display: flex; align-items: center; gap: 10px;
  padding: 13px 10px 8px; flex-shrink: 0;
}
.sb-app-name {
  flex: 1; font-size: 26px; font-weight: 700; color: var(--sb-tx);
  font-family: 'Martel', serif; letter-spacing: -0.3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;
}
.sb-collapse-btn {
  width: 28px; height: 28px; flex-shrink: 0; border: none; border-radius: 6px;
  background: transparent; color: var(--sb-muted);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: background .12s, color .12s; padding: 0;
}
.sb-collapse-btn:hover { background: rgba(255,255,255,0.1); color: var(--sb-tx); }

/* ── Action rows (New Chat, Chats header) ────────────────── */
.sb-action-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; margin: 2px 6px; border-radius: 8px;
  cursor: pointer; border: none; background: transparent;
  color: var(--sb-tx); font-size: 13px; font-weight: 500;
  width: calc(100% - 12px); text-align: left;
  transition: background .12s;
}
.sb-action-row:hover { background: var(--sb-hover); }
.sb-section-head { cursor: default; color: var(--sb-muted); font-size: 12px; }
.sb-section-head:hover { background: transparent; }
.sba-icon { display: flex; align-items: center; color: inherit; flex-shrink: 0; }
.sba-label { }

/* ── Chat list (expanded) ────────────────────────────────── */
.sb-list {
  flex: 1; overflow-y: auto; overflow-x: hidden; padding: 4px 6px 8px;
}
.sb-section-hdr { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--sb-muted); padding: 10px 8px 3px; }
.sb-divider { height: 1px; background: rgba(255,255,255,0.07); margin: 6px 8px; }
.sb-empty        { font-size: 12px; color: var(--sb-muted); padding: 8px 6px; }
.sb-loading      { font-size: 12px; color: var(--sb-muted); padding: 10px 6px; }

.sb-row {
  display: flex; align-items: center;
  padding: 7px 8px; border-radius: 8px;
  cursor: pointer; min-width: 0; gap: 0;
}
.sb-row:hover  { background: var(--sb-hover); }
.sb-row.active { background: var(--sb-active); }

.sb-row-title {
  flex: 1; font-size: 13px; color: var(--sb-tx);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;
}
.rename-input {
  flex: 1; font-size: 13px; background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.25); border-radius: 5px;
  padding: 2px 6px; outline: none; min-width: 0; color: var(--sb-tx);
}
/* ── Three-dot context menu (sidebar + chats-page) ───────────────────────── */
.sb-row-menu { position: relative; flex-shrink: 0; margin-left: 4px; }

.sb-more-btn {
  display: flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border: none; border-radius: 5px;
  background: transparent; color: var(--sb-muted);
  cursor: pointer; opacity: 0;
}
.sb-row:hover .sb-more-btn,
.sb-row.menu-open .sb-more-btn,
.sb-more-btn.active { opacity: 1; }
.sb-more-btn:hover,
.sb-more-btn.active { background: rgba(255,255,255,0.12); color: var(--sb-tx); }

.sb-ctx-menu {
  position: absolute; right: 0; top: calc(100% + 4px);
  width: 164px; background: var(--surf);
  border: 1px solid var(--bdr); border-radius: 10px;
  box-shadow: 0 8px 28px rgba(0,0,0,.22);
  z-index: 600; padding: 4px 0;
}
.ctx-item {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 8px 12px;
  background: none; border: none; cursor: pointer;
  font-size: 13px; color: var(--tx); text-align: left;
}
.ctx-item:hover { background: rgba(100,116,139,0.13); }
.ctx-item svg { flex-shrink: 0; color: var(--muted); }
.ctx-divider { height: 1px; background: var(--bdr); margin: 4px 0; }
.ctx-delete { color: #ef4444; }
.ctx-delete svg { color: #ef4444; }
.ctx-delete:hover { background: rgba(239,68,68,.12); }

/* chats-page overrides — button always visible, menu opens upward */
.cp-more-btn { display: flex !important; color: var(--muted); }
.cp-more-btn:hover, .cp-more-btn.active { background: var(--hover); color: var(--tx); }
.cp-ctx-menu { top: auto; bottom: calc(100% + 4px); }

/* ── COLLAPSED icon buttons ──────────────────────────────── */
.col-icon-btn {
  display: flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; margin: 4px auto 0;
  border: none; border-radius: 10px; background: transparent;
  color: var(--sb-muted); cursor: pointer;
  transition: background .12s, color .12s;
}
.col-icon-btn:hover, .col-icon-btn.active { background: var(--sb-hover); color: var(--sb-tx); }
.col-icon-btn.brand { margin-top: 10px; }
.col-icon-btn.brand .sf-logo { pointer-events: none; }

/* ── User footer (expanded) ──────────────────────────────── */
.avatar-photo {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0; object-fit: cover;
}
.avatar-user-info {
  display: flex; flex-direction: column; gap: 1px; min-width: 0; text-align: left;
}
.avatar-user-name {
  font-size: 14px; font-weight: 600; color: var(--sb-tx);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.avatar-user-email {
  font-size: 12px; color: var(--sb-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.avatar-btn {
  width: 100%; border-radius: 8px; border: none;
  background: transparent; color: var(--sb-tx); cursor: pointer;
  display: flex; align-items: center; gap: 9px;
  padding: 5px 6px;
  transition: background .13s;
}
.avatar-btn:hover { background: var(--sb-hover); }
/* When sidebar is collapsed, shrink back to icon-only circle */
.sf-avatar-area.collapsed .avatar-btn {
  width: 36px; height: 36px; border-radius: 50%; padding: 0;
  justify-content: center;
  background: rgba(255,255,255,0.1); border: 1.5px solid rgba(255,255,255,0.15);
}
.sf-avatar-area.collapsed .avatar-btn:hover {
  background: rgba(255,255,255,0.18);
}

/* User menu popup */
.user-menu {
  position: absolute; bottom: calc(100% + 6px); left: 8px;
  width: calc(100% - 16px);
  background: var(--sb-hover); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px; padding: 6px;
  box-shadow: 0 8px 28px rgba(0,0,0,0.4);
  z-index: 200;
}
.user-menu-col { left: 4px; width: 180px; }
.um-section-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--sb-muted);
  padding: 4px 8px 6px;
}
.um-item {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 8px 10px; border: none; border-radius: 7px;
  background: transparent; color: var(--sb-tx); font-size: 13px;
  cursor: pointer; text-align: left;
  transition: background .12s;
}
.um-item:hover { background: var(--sb-hover); }
.um-signout { color: #f87171; }
.um-signout:hover { background: rgba(239,68,68,.15); }

.um-user-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px 6px;
}
.um-avatar { width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0; }
.um-user-info { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.um-user-name { font-size: 13px; font-weight: 600; color: var(--sb-tx); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.um-user-email { font-size: 11px; color: var(--sb-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Menu pop transition */
.um-pop-enter-active { transition: opacity .15s ease, transform .15s ease; }
.um-pop-leave-active { transition: opacity .1s ease, transform .1s ease; }
.um-pop-enter-from   { opacity: 0; transform: translateY(6px); }
.um-pop-leave-to     { opacity: 0; transform: translateY(4px); }


/* ═══════════════════════ CHAT PANE ═══════════════════════ */
.chat-pane {
  flex: 1; display: flex; flex-direction: column;
  background: var(--bg); min-width: 0;
}


/* Progress strip */
/* ── Agent progress strip ─────────────────────────────────────── */
.progress-strip {
  position: relative; flex-shrink: 0; height: 0; overflow: hidden; opacity: 0;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: height .2s ease, opacity .2s ease;
}
.progress-strip.visible { height: 32px; opacity: 1; }

/* Active agent flow indicator bar */
.session-flow-bar {
  flex-shrink: 0; display: flex; align-items: center; gap: 6px;
  padding: 5px 20px; background: var(--sbg);
  border-bottom: 1px solid var(--sbdr);
  font-size: 12.5px; font-weight: 500; color: var(--stx);
}
.sfb-icon  { font-size: 14px; }
.sfb-name  { font-weight: 600; }
.sfb-label {
  margin-left: 2px; font-size: 10.5px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .06em;
  padding: 1px 6px; border-radius: 10px;
  background: var(--sbdr); color: var(--stx); opacity: 0.8;
}

/* Track tint — per agent, very subtle */
.progress-strip.intake     { background: rgba(59,  130, 246, 0.07); }
.progress-strip.discovery  { background: rgba(99,  102, 241, 0.07); }
.progress-strip.research { background: rgba(239, 68, 68, 0.07); }
.progress-strip.review   { background: rgba(245, 158,  11, 0.07); }
.progress-strip.approval   { background: rgba(16,  185, 129, 0.07); }

/* Slow shimmer — per agent, muted opacity */
.progress-strip::after {
  content: '';
  position: absolute; top: 0; bottom: 0;
  width: 55%;
  animation: p-sweep 3.5s linear infinite;
}
.intake::after     { background: linear-gradient(90deg, transparent, rgba(59,  130, 246, 0.5), transparent); }
.discovery::after  { background: linear-gradient(90deg, transparent, rgba(99,  102, 241, 0.5), transparent); }
.research::after { background: linear-gradient(90deg, transparent, rgba(239, 68, 68, 0.5), transparent); }
.review::after   { background: linear-gradient(90deg, transparent, rgba(245, 158,  11, 0.5), transparent); }
.approval::after   { background: linear-gradient(90deg, transparent, rgba(16,  185, 129, 0.5), transparent); }

@keyframes p-sweep {
  0%   { left: -55%; }
  100% { left: 100%; }
}

/* Dot + label — per agent colour */
.p-dot { position:relative;z-index:1;width:6px;height:6px;border-radius:50%;flex-shrink:0;animation:p-pulse 2s ease-in-out infinite; }
.intake .p-dot    { background: #3b82f6; }
.discovery .p-dot { background: #6366f1; }
.research .p-dot{ background: #ef4444; }
.review .p-dot  { background: #f59e0b; }
.approval .p-dot  { background: #10b981; }
@keyframes p-pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.75)}}

.p-text { position:relative;z-index:1;font-size:12px;font-weight:500;letter-spacing:.02em;white-space:nowrap; }
.intake .p-text    { color: #2563eb; } .discovery .p-text { color: #4f46e5; }
.research .p-text{ color: #dc2626; } .review .p-text  { color: #b45309; }
.approval .p-text  { color: #059669; }
.dark .intake .p-text    { color: #93c5fd; } .dark .discovery .p-text { color: #a5b4fc; }
.dark .research .p-text{ color: #fca5a5; } .dark .review .p-text  { color: #fcd34d; }
.dark .approval .p-text  { color: #6ee7b7; }

/* Messages */
.messages { flex:1;overflow-y:auto;padding:20px 28px;display:flex;flex-direction:column;gap:14px;min-height:0; }
.empty-state {
  margin: auto; display: flex; align-items: center; justify-content: center;
  padding: 40px 20px;
}
.greeting-row {
  display: flex; align-items: center; gap: 18px;
}
.greeting-text {
  font-family: 'Martel', serif;
  font-size: clamp(28px, 3.5vw, 44px);
  font-weight: 400;
  color: var(--tx);
  letter-spacing: -0.2px;
  margin: 0;
  line-height: 1.2;
}
.message{display:flex;flex-direction:column;max-width:82%}
.message.user{align-self:flex-end;align-items:flex-end}.message.agent{align-self:flex-start;align-items:flex-start}
.stage-tag{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;border-radius:99px;margin-bottom:5px;background:var(--sbg);color:var(--stx)}
.stage-tag.discovery{background:#dbeafe;color:#1e40af}.stage-tag.research{background:#fee2e2;color:#991b1b}.stage-tag.review{background:#ffedd5;color:#9a3412}.stage-tag.approval{background:#dcfce7;color:#166534}
.dark .stage-tag.discovery{background:#1e3a5f;color:#93c5fd}.dark .stage-tag.research{background:#450a0a;color:#fca5a5}.dark .stage-tag.review{background:#431407;color:#fdba74}.dark .stage-tag.approval{background:#052e16;color:#86efac}
.bubble{padding:11px 15px;border-radius:14px;font-size:14px;line-height:1.65;word-break:break-word}
.message.user .bubble{background:var(--ub);color:var(--uf);border-radius:14px 14px 3px 14px}
.message.agent .bubble{background:var(--ab);color:var(--tx);border:1px solid var(--abdr);border-radius:3px 14px 14px 14px}
.bubble :deep(h1),.bubble :deep(h2),.bubble :deep(h3){margin:.6em 0 .3em;font-size:1em}.bubble :deep(p){margin:.35em 0}.bubble :deep(ul),.bubble :deep(ol){padding-left:1.4em;margin:.35em 0}.bubble :deep(code){background:var(--cbg);padding:1px 5px;border-radius:4px;font-size:12px}.bubble :deep(pre){background:var(--cbg);padding:10px;border-radius:6px;overflow-x:auto;margin:.5em 0}.bubble :deep(table){border-collapse:collapse;width:100%;margin:.5em 0;font-size:13px}.bubble :deep(th),.bubble :deep(td){border:1px solid var(--bdr);padding:5px 9px}.bubble :deep(th){background:var(--surf2);font-weight:600}.bubble :deep(strong){font-weight:600}
.cursor{display:inline-block;width:2px;height:15px;background:var(--muted);animation:blink .75s step-end infinite;vertical-align:text-bottom;margin-left:3px}
@keyframes blink{50%{opacity:0}}

/* Card types */
.doc-card{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--surf);border:1px solid var(--pri);border-radius:12px;min-width:260px}
.doc-card-icon{font-size:24px;flex-shrink:0}.doc-card-body{flex:1}.doc-card-title{font-size:14px;font-weight:600;margin:0 0 2px}.doc-card-sub{font-size:12px;color:var(--muted);margin:0}
.doc-card-btn{padding:7px 14px;background:var(--pri);color:var(--pri-fg);border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;transition:background .15s}
.doc-card-btn:hover{background:var(--pri-h)}
.status-card{display:flex;align-items:flex-start;gap:10px;padding:12px 16px;border-radius:12px;font-size:14px;border:1px solid var(--sbdr);background:var(--sbg)}
.sc-title{font-weight:600;color:var(--tx);margin:0 0 2px;font-size:14px}.sc-sub{color:var(--muted);margin:0;font-size:13px}
.verdict-card{padding:13px 15px;border-radius:12px;width:100%;border:1px solid;font-size:14px}
.verdict-card.pass{background:var(--pass-bg);border-color:var(--pass-bdr)}.verdict-card.fail{background:var(--fail-bg);border-color:var(--fail-bdr)}
.verdict-head{display:flex;align-items:center;gap:8px;margin-bottom:7px}
.verdict-card.pass .verdict-head strong{color:var(--pass-tx)}.verdict-card.fail .verdict-head strong{color:var(--fail-tx)}
.verdict-badge{padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700;letter-spacing:.06em;line-height:1.8}
.badge-pass{background:#16a34a;color:#fff}
.badge-fail{background:#dc2626;color:#fff}
/* Same badges inside streamed v-html content */
.bubble :deep(.vb-pass),.doc-content :deep(.vb-pass){display:inline;padding:1px 8px;border-radius:99px;font-size:.85em;font-weight:700;background:#16a34a;color:#fff;white-space:nowrap}
.bubble :deep(.vb-fail),.doc-content :deep(.vb-fail){display:inline;padding:1px 8px;border-radius:99px;font-size:.85em;font-weight:700;background:#dc2626;color:#fff;white-space:nowrap}
.verdict-body{margin:0 0 7px;color:var(--tx);line-height:1.5}
.verdict-list{margin:0;padding-left:1.3em;font-size:13px}.verdict-card.pass .verdict-list{color:var(--pass-tx)}.verdict-card.fail .verdict-list{color:var(--fail-tx)}.verdict-list li{margin:3px 0}
.spin{display:inline-block;width:16px;height:16px;flex-shrink:0;border:2px solid var(--sbdr);border-top-color:var(--stx);border-radius:50%;animation:spin .7s linear infinite}
.spin.large{width:22px;height:22px}
@keyframes spin{to{transform:rotate(360deg)}}

/* Input panel */
.input-panel{flex-shrink:0;padding:15px 28px;background:var(--surf);border-top:1px solid var(--bdr);display:flex;flex-direction:column;gap:10px}
.multi-scroll{max-height:50vh;overflow-y:auto;display:flex;flex-direction:column;gap:12px;padding-right:4px}
.multi-scroll::-webkit-scrollbar{width:4px}.multi-scroll::-webkit-scrollbar-thumb{background:var(--bdr);border-radius:99px}
.multi-item{display:flex;flex-direction:column;gap:5px}.multi-label{font-size:13px;font-weight:500;color:var(--tx);line-height:1.4}
.input-row{display:flex;gap:10px;align-items:flex-end}
.ta{width:100%;box-sizing:border-box;padding:10px 13px;border:1px solid var(--ibdr);border-radius:10px;font-size:14px;font-family:inherit;resize:vertical;outline:none;background:var(--surf2);color:var(--tx);transition:border-color .15s;line-height:1.5}
.input-row .ta{flex:1;resize:none}.brief-ta{min-height:100px}.ta:focus{border-color:var(--ifocus)}.ta::placeholder{color:var(--muted)}
.action-row{display:flex;justify-content:flex-end}
.btn-primary,.btn-send{padding:10px 22px;background:var(--pri);color:var(--pri-fg);border:none;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap;transition:background .15s,opacity .15s;flex-shrink:0}
.btn-primary:hover:not(:disabled),.btn-send:hover:not(:disabled){background:var(--pri-h)}.btn-primary:disabled,.btn-send:disabled{opacity:.45;cursor:not-allowed}
.mode-toggle{display:flex;border:1px solid var(--bdr);border-radius:10px;overflow:hidden;width:fit-content}
.mode-btn{padding:7px 16px;background:transparent;color:var(--muted);border:none;font-size:13px;font-weight:500;cursor:pointer;transition:background .15s,color .15s}
.mode-btn:hover{background:var(--surf2);color:var(--tx)}.mode-btn.active{background:var(--pri);color:var(--pri-fg)}
.drop-zone{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;padding:28px 16px;border:2px dashed var(--bdr);border-radius:10px;cursor:pointer;transition:border-color .15s,background .15s;min-height:110px;background:var(--surf2)}
.drop-zone:hover,.drop-zone.over{border-color:var(--pri);background:var(--sbg)}.drop-zone.filled{border-style:solid;border-color:var(--pri)}
.drop-lbl{font-size:14px;font-weight:500;color:var(--tx)}.drop-hint{font-size:12px;color:var(--muted);text-align:center}.fname{font-size:14px;font-weight:600;color:var(--pri);word-break:break-all;text-align:center}.fmeta{font-size:12px;color:var(--muted)}.img-prev{max-width:100%;max-height:140px;border-radius:8px;object-fit:contain;border:1px solid var(--bdr)}.upload-err{font-size:13px;color:#ef4444}

/* Confirmation panel */
.confirm-panel{flex-shrink:0;display:flex;flex-direction:column;gap:14px;padding:20px 28px;background:var(--surf);border-top:2px solid var(--pri);max-height:70vh;overflow-y:auto}
.confirm-header{display:flex;gap:12px;align-items:flex-start}.confirm-title{font-size:15px;font-weight:700;color:var(--tx);margin:0 0 3px}.confirm-sub{font-size:13px;color:var(--muted);margin:0}
.confirm-content{background:var(--surf2);border:1px solid var(--bdr);border-radius:10px;padding:14px 16px;font-size:14px;line-height:1.7;color:var(--tx);overflow-y:auto}
.confirm-content :deep(p){margin:.4em 0}.confirm-content :deep(ul){padding-left:1.4em;margin:.4em 0}.confirm-content :deep(strong){font-weight:600}
.confirm-footer{display:flex;flex-direction:column;gap:10px}

/* Banners */
.banner{flex-shrink:0;padding:12px 28px;font-size:13px;font-weight:500;text-align:center;display:flex;align-items:center;justify-content:center;gap:12px}
.retry-btn{padding:5px 14px;border-radius:7px;border:1.5px solid currentColor;background:transparent;color:inherit;font-size:13px;font-weight:600;cursor:pointer;opacity:0.85;transition:opacity .15s}
.retry-btn:hover{opacity:1}
.banner.ok{background:#dcfce7;color:#166534}.banner.warn{background:#fef3c7;color:#92400e}.banner.err{background:#fee2e2;color:#991b1b}
.dark .banner.ok{background:#052e16;color:#86efac}.dark .banner.warn{background:#1c1400;color:#fcd34d}.dark .banner.err{background:#1f0000;color:#fca5a5}

/* ── Document right panel ──────────────────────────────────────────────────── */
.doc-panel {
  width: 0; flex-shrink: 0;
  display: flex; flex-direction: column;
  background: var(--surf);
  border-left: 0px solid var(--bdr);
  overflow: hidden;
  transition: width 0.25s ease, border-left-width 0.25s ease;
}
.doc-panel.open {
  width: 42%;
  min-width: 340px;
  max-width: 680px;
  border-left-width: 1px;
}
.doc-panel-header { display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 18px;background:var(--hbg);color:var(--hfg);flex-shrink:0 }
.doc-panel-title  { font-size:13px;font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap }
.doc-panel-actions { display:flex;gap:8px;flex-shrink:0 }
.session-models-bar { background:var(--surf);border-bottom:1px solid var(--bdr);padding:12px 18px;display:flex;flex-direction:column;gap:8px;flex-shrink:0 }
.sm-loading { font-size:12px;color:var(--muted); }
.sm-heading { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--muted); }
.sm-rows { display:flex;flex-direction:column;gap:4px; }
.sm-row { display:flex;gap:10px;align-items:center;font-size:12px; }
.sm-slot { color:var(--muted);min-width:140px;flex-shrink:0; }
.sm-value { font-family:monospace;color:var(--tx); }
.ol-btn { padding:5px 12px;border:1px solid rgba(255,255,255,.2);border-radius:7px;background:rgba(255,255,255,.1);color:var(--hfg);font-size:12px;font-weight:500;cursor:pointer;transition:background .15s;white-space:nowrap }
.ol-btn:hover  { background:rgba(255,255,255,.2) }
.ol-btn.accent { background:var(--pri);border-color:var(--pri) }
.ol-btn.accent:hover { background:var(--pri-h) }
.ol-btn.close  { border-color:rgba(255,255,255,.15) }
.doc-panel-body { flex:1;overflow-y:auto;padding:24px 28px }
.doc-loading { display:flex;align-items:center;gap:10px;color:var(--muted);font-size:14px;padding:40px 0;justify-content:center }
.doc-content { font-size:14px;line-height:1.75;color:var(--tx) }
.doc-content :deep(h1){font-size:20px;font-weight:700;margin:1.2em 0 .4em}
.doc-content :deep(h2){font-size:16px;font-weight:700;margin:1em 0 .3em;border-bottom:1px solid var(--bdr);padding-bottom:4px}
.doc-content :deep(h3){font-size:14px;font-weight:600;margin:.8em 0 .3em}
.doc-content :deep(p){margin:.5em 0}
.doc-content :deep(ul),.doc-content :deep(ol){padding-left:1.4em;margin:.4em 0}
.doc-content :deep(table){border-collapse:collapse;width:100%;margin:.8em 0;font-size:13px}
.doc-content :deep(th),.doc-content :deep(td){border:1px solid var(--bdr);padding:7px 12px;vertical-align:top}
.doc-content :deep(th){background:var(--surf2);font-weight:600}
.doc-content :deep(code){background:var(--cbg);padding:1px 5px;border-radius:4px;font-size:12px}
.doc-content :deep(pre){background:var(--cbg);padding:12px;border-radius:8px;overflow-x:auto;margin:.6em 0}
.doc-content :deep(blockquote){border-left:3px solid var(--pri);padding-left:12px;color:var(--muted);margin:.5em 0}
.doc-content :deep(strong){font-weight:600}

/* Scrollbars */
.messages::-webkit-scrollbar,.doc-panel-body::-webkit-scrollbar,.sb-content::-webkit-scrollbar{width:4px}
.messages::-webkit-scrollbar-thumb,.doc-panel-body::-webkit-scrollbar-thumb,.sb-content::-webkit-scrollbar-thumb{background:var(--bdr);border-radius:99px}
.sb-content::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1)}

/* ChatInput component handles its own styles */
</style>
