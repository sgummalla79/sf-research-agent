<template>
  <div class="shell" :class="{ dark: isDark }">

    <!-- ═══════════════════ SIDEBAR ═══════════════════ -->
    <div class="sidebar" :class="{ collapsed: !sidebar.open }">

      <!-- ── EXPANDED ────────────────────────────────────── -->
      <template v-if="sidebar.open">

        <!-- Brand header -->
        <div class="sb-header">
          <span class="sb-app-name">Salesforce Architect Agent</span>
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
              class="sb-row" :class="{ active: s.thread_id === sessionId }"
              @click="editingId !== s.thread_id && restoreSession(s.thread_id)">
              <input v-if="editingId === s.thread_id" class="rename-input"
                v-model="editingTitle" ref="renameInputRef"
                @blur="saveRename(s.thread_id)" @keydown.enter.prevent="saveRename(s.thread_id)"
                @keydown.esc="editingId = null" @click.stop />
              <span v-else class="sb-row-title">{{ s.brief_snippet || 'New conversation' }}</span>
              <div v-if="editingId !== s.thread_id" class="sb-row-actions" @click.stop>
                <button class="sa-btn" title="Unpin" @click="unpinSession(s.thread_id)">📌</button>
                <button class="sa-btn" title="Rename" @click="startRename(s)">✏️</button>
                <button class="sa-btn del" title="Delete" @click="confirmDelete(s)">🗑</button>
              </div>
            </div>
          </template>

          <!-- Recent -->
          <template v-if="sidebar.recent.filter(s => !searchQuery || (s.brief_snippet||'').toLowerCase().includes(searchQuery.toLowerCase())).length">
            <div class="sb-section-hdr">Recent</div>
            <div v-for="s in sidebar.recent.filter(s => !searchQuery || (s.brief_snippet||'').toLowerCase().includes(searchQuery.toLowerCase()))"
              :key="s.thread_id"
              class="sb-row" :class="{ active: s.thread_id === sessionId }"
              @click="editingId !== s.thread_id && restoreSession(s.thread_id)">
              <input v-if="editingId === s.thread_id" class="rename-input"
                v-model="editingTitle"
                @blur="saveRename(s.thread_id)" @keydown.enter.prevent="saveRename(s.thread_id)"
                @keydown.esc="editingId = null" @click.stop />
              <span v-else class="sb-row-title">{{ s.brief_snippet || 'New conversation' }}</span>
              <div v-if="editingId !== s.thread_id" class="sb-row-actions" @click.stop>
                <button class="sa-btn" title="Pin" @click="pinSession(s.thread_id)">📍</button>
                <button class="sa-btn" title="Rename" @click="startRename(s)">✏️</button>
                <button class="sa-btn del" title="Delete" @click="confirmDelete(s)">🗑</button>
              </div>
            </div>
          </template>

        </div>

        <!-- User footer — expanded -->
        <div class="sb-footer" @click.stop>
          <button class="avatar-btn" @click="userMenuOpen = !userMenuOpen">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
              <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
            </svg>
          </button>
          <transition name="um-pop">
            <div v-if="userMenuOpen" class="user-menu">
              <div class="um-section-label">Appearance</div>
              <button class="um-item" @click="isDark = !isDark; userMenuOpen = false">
                <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
                {{ isDark ? 'Light mode' : 'Dark mode' }}
              </button>
            </div>
          </transition>
        </div>

      </template>

      <!-- ── COLLAPSED ────────────────────────────────────── -->
      <template v-else>
        <!-- SF icon — click to expand -->
        <button class="col-icon-btn brand" title="Salesforce Architect Agent" @click="sidebar.open = true">
          <div class="sf-logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
              <rect x="2" y="2" width="20" height="20" rx="5"/>
              <line x1="9" y1="2" x2="9" y2="22"/>
            </svg>
          </div>
        </button>

        <!-- New Chat icon -->
        <button class="col-icon-btn" title="New Chat" @click="handleNewChat">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="18" height="18"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>

        <!-- Chats icon — opens full chats view -->
        <button class="col-icon-btn" :class="{ active: currentView === 'chats' }" title="Chats" @click="openChatsView">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" width="18" height="18">
            <path d="M17 8h2a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-1v3l-3-3h-3"/>
            <path d="M13 3H4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h1v3l3-3h5a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z"/>
          </svg>
        </button>

        <!-- Avatar at bottom — collapsed -->
        <div class="sb-footer-col" @click.stop>
          <button class="col-icon-btn avatar-col" title="Menu" @click="userMenuOpen = !userMenuOpen">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
              <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
            </svg>
          </button>
          <transition name="um-pop">
            <div v-if="userMenuOpen" class="user-menu user-menu-col">
              <div class="um-section-label">Appearance</div>
              <button class="um-item" @click="isDark = !isDark; userMenuOpen = false">
                <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
                {{ isDark ? 'Light mode' : 'Dark mode' }}
              </button>
            </div>
          </transition>
        </div>

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
      <div class="cp-subtitle">Your chats with Salesforce Architect Agent</div>

      <!-- Chat list -->
      <div class="cp-list">
        <div v-if="!filteredChats.length" class="cp-empty">No conversations found</div>

        <div v-for="s in filteredChats" :key="s.thread_id"
          class="cp-row" :class="{ active: s.thread_id === sessionId }"
          @click="selectChat(s.thread_id)">
          <div class="cp-row-body">
            <div class="cp-row-title">{{ s.brief_snippet || 'New conversation' }}</div>
            <div class="cp-row-meta">{{ relativeTime(s.last_modified || s.created_at) }}</div>
          </div>
          <div class="cp-row-actions" @click.stop>
            <button class="sa-btn" :title="s.pinned ? 'Unpin' : 'Pin'"
              @click="s.pinned ? unpinSession(s.thread_id) : pinSession(s.thread_id)">
              {{ s.pinned ? '📌' : '📍' }}
            </button>
            <button class="sa-btn" title="Rename" @click="startRename(s)">✏️</button>
            <button class="sa-btn del" title="Delete" @click="confirmDelete(s)">🗑</button>
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

      <!-- Messages -->
      <div class="messages" ref="messagesEl">
        <div v-if="!messages.length && !isStreaming" class="empty-state">
          <div class="empty-icon">🏗️</div>
          <p class="empty-sub">Write a project brief or upload a document to begin.</p>
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
              <strong>Technical Review — {{ msg.reviewPassed ? 'PASSED' : 'FAILED' }}</strong></div>
            <p class="verdict-body">{{ msg.reviewFeedback }}</p>
            <ul v-if="msg.criticalIssues?.length" class="verdict-list">
              <li v-for="(it, j) in msg.criticalIssues" :key="j">{{ it }}</li>
            </ul>
          </div>

          <div v-else-if="msg.type === 'approval_result'" class="verdict-card" :class="msg.approvalStatus === 'approved' ? 'pass' : 'fail'">
            <div class="verdict-head"><span>{{ msg.approvalStatus === 'approved' ? '🎉' : '🔄' }}</span>
              <strong>Approver Gate — {{ msg.approvalStatus?.toUpperCase() }}</strong></div>
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
          <div v-for="(q, i) in pendingQuestions" :key="i" class="multi-item">
            <label class="multi-label">{{ i + 1 }}. {{ q }}</label>
            <textarea v-model="replyAnswers[i]" class="ta" :placeholder="`Answer ${i + 1}…`" rows="2" />
          </div>
          <div class="action-row">
            <button class="btn-primary" @click="submitReplies"
              :disabled="replyAnswers.some(a => !a?.trim()) || isStreaming">Send All Answers →</button>
          </div>
        </template>
      </div>

      <!-- Initial input -->
      <div v-if="!sessionId && !isStreaming" class="input-panel">
        <div class="mode-toggle">
          <button class="mode-btn" :class="{ active: inputMode === 'brief' }" @click="inputMode = 'brief'">✏️ Write Brief</button>
          <button class="mode-btn" :class="{ active: inputMode === 'upload' }" @click="inputMode = 'upload'">📎 Upload File</button>
        </div>
        <template v-if="inputMode === 'brief'">
          <textarea v-model="briefText" class="ta brief-ta" rows="5" placeholder="Describe your Salesforce architecture project…" />
          <div class="action-row">
            <button class="btn-primary" @click="submitBrief" :disabled="!briefText.trim()">Start Session →</button>
          </div>
        </template>
        <template v-else>
          <div class="drop-zone" :class="{ over: isDragging, filled: !!selectedFile }"
            @dragover.prevent="isDragging = true" @dragleave.prevent="isDragging = false"
            @drop.prevent="onDrop" @click="fileInputRef.click()">
            <input ref="fileInputRef" type="file" style="display:none"
              accept=".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg,.gif,.webp" @change="onFileChange" />
            <template v-if="selectedFile && imagePreviewUrl">
              <img :src="imagePreviewUrl" class="img-prev" :alt="selectedFile.name" />
              <span class="fname">{{ selectedFile.name }}</span><span class="fmeta">{{ fmtSize(selectedFile.size) }}</span>
            </template>
            <template v-else-if="selectedFile">
              <span style="font-size:26px">📄</span>
              <span class="fname">{{ selectedFile.name }}</span><span class="fmeta">{{ fmtSize(selectedFile.size) }}</span>
            </template>
            <template v-else>
              <span style="font-size:24px">⬆</span>
              <span class="drop-lbl">Drop a file or click to browse</span>
              <span class="drop-hint">PDF, DOCX, TXT, MD · PNG, JPG, WebP · max {{ MAX_MB }} MB</span>
            </template>
          </div>
          <div v-if="uploadError" class="upload-err">{{ uploadError }}</div>
          <div class="action-row">
            <button class="btn-primary" @click="submitUpload" :disabled="!selectedFile">Upload &amp; Start →</button>
          </div>
        </template>
      </div>

      <!-- Banners -->
      <div v-if="isComplete"     class="banner ok">🎉 Document approved and finalised.</div>
      <div v-if="isHalted"       class="banner warn">⚠️ Session halted after maximum revisions.</div>
      <div v-if="isInvalidInput" class="banner err">❌ Image doesn't appear to be architecture-related.</div>
      <div v-if="error"          class="banner err">Error: {{ error }}</div>

    </div><!-- /chat-pane -->

    <!-- ═══════════════════ DOCUMENT RIGHT PANEL ═══════════════════ -->
    <div class="doc-panel" :class="{ open: documentPanel.open }">
      <div class="doc-panel-header">
        <span class="doc-panel-title">📄 Architecture Document v{{ documentPanel.version }}</span>
        <div class="doc-panel-actions">
          <button class="ol-btn" @click="downloadMD">⬇ Markdown</button>
          <button class="ol-btn accent" @click="doPDF">⬇ PDF</button>
          <button class="ol-btn close" @click="closeDocumentPanel">✕</button>
        </div>
      </div>
      <div class="doc-panel-body">
        <div v-if="documentPanel.loading" class="doc-loading"><span class="spin large" /> Loading…</div>
        <div v-else class="doc-content" v-html="renderContent(documentPanel.content)" />
      </div>
    </div>

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

  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { marked } from 'marked'
import { useAgentChat } from '../composables/useAgentChat.js'

const {
  sessionId, messages, currentStage, pendingQuestions, pendingConfirmation,
  isStreaming, isComplete, isHalted, isInvalidInput, error,
  documentPanel, sidebar,
  loadSessions, newChat, restoreSession,
  pinSession, unpinSession, deleteSession, renameSession,
  startSession, uploadDocument, confirmUnderstanding, sendReply,
  openDocumentPanel, closeDocumentPanel, downloadMD,
} = useAgentChat()

// View state
const currentView  = ref('chat')   // 'chat' | 'chats'
const searchQuery  = ref('')
const editingId      = ref(null)
const editingTitle   = ref('')
const renameInputRef = ref(null)

// Delete confirmation state
const deleteConfirm = ref({ show: false, threadId: null, title: '' })

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

const isDark          = ref(false)
const userMenuOpen    = ref(false)
const briefText       = ref('')
const correctionText  = ref('')
const replyAnswers    = ref([])
const messagesEl      = ref(null)
const inputMode       = ref('brief')
const selectedFile    = ref(null)
const isDragging      = ref(false)
const fileInputRef    = ref(null)
const uploadError     = ref(null)
const imagePreviewUrl = ref(null)

const MAX_MB   = 10
const IMG_EXTS = new Set(['.png','.jpg','.jpeg','.gif','.webp'])
const ALL_EXTS = ['.pdf','.docx','.doc','.txt','.md',...IMG_EXTS]

const stageLabels = {
  intake:     'Intake Agent',
  discovery:  'Discovery Agent',
  researcher: 'Research Agent',
  reviewer:   'Review Agent',
  approver:   'Approver Gate',
}

// Flat sorted list: pinned first, then recent — filtered by search query
const filteredChats = computed(() => {
  const all = [...sidebar.pinned, ...sidebar.recent]
  const q   = searchQuery.value.trim().toLowerCase()
  return q ? all.filter(s => (s.brief_snippet || '').toLowerCase().includes(q)) : all
})

onMounted(() => {
  loadSessions()
  document.addEventListener('click', () => { userMenuOpen.value = false })
})
watch(pendingQuestions, qs => { replyAnswers.value = qs.map(() => '') })
watch(messages, async () => {
  await nextTick()
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}, { deep: true })

marked.setOptions({ breaks: true })
function renderContent(c) {
  if (!c) return ''
  if (Array.isArray(c)) c = c.filter(b => b?.type === 'text').map(b => b?.text ?? '').join('\n')
  else if (typeof c !== 'string') c = String(c)
  return marked.parse(c)
}

function handleNewChat()        { newChat(); currentView.value = 'chat' }
function openChatsView()       { searchQuery.value = ''; currentView.value = 'chats' }
function selectChat(threadId)  { restoreSession(threadId); currentView.value = 'chat' }
async function submitBrief()        { if (!briefText.value.trim()) return; await startSession(briefText.value.trim()); briefText.value = '' }
async function submitConfirmation() { await confirmUnderstanding(correctionText.value); correctionText.value = '' }
async function submitReplies()      { if (replyAnswers.value.some(a => !a?.trim())) return; await sendReply(replyAnswers.value.map(a => a.trim())); replyAnswers.value = [] }
async function submitUpload() {
  if (!selectedFile.value) return
  await uploadDocument(selectedFile.value)
  if (imagePreviewUrl.value) { URL.revokeObjectURL(imagePreviewUrl.value); imagePreviewUrl.value = null }
  selectedFile.value = null
}

function setFile(file) {
  uploadError.value = null; imagePreviewUrl.value = null
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!ALL_EXTS.includes(ext)) { uploadError.value = 'Unsupported type.'; return }
  if (file.size > MAX_MB * 1048576) { uploadError.value = `Max ${MAX_MB} MB.`; return }
  selectedFile.value = file
  if (IMG_EXTS.has(ext)) imagePreviewUrl.value = URL.createObjectURL(file)
}
function onFileChange(e) { const f = e.target.files?.[0]; if (f) setFile(f) }
function onDrop(e)       { isDragging.value = false; const f = e.dataTransfer?.files?.[0]; if (f) setFile(f) }
function fmtSize(b)      { return b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(1)} MB` }

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
  --c-intake:#3b82f6;--c-discovery:#6366f1;--c-researcher:#8b5cf6;--c-reviewer:#f59e0b;--c-approver:#10b981;
}
.shell.dark {
  --bg:#0f172a;--surf:#1e293b;--surf2:#0f172a;--bdr:#334155;
  --tx:#f1f5f9;--muted:#94a3b8;--pri:#3b82f6;--pri-h:#2563eb;
  --ub:#3b82f6;--ab:#1e293b;--abdr:#334155;
  --sbg:#172554;--stx:#93c5fd;--sbdr:#1e40af;
  --hbg:#020617;--hfg:#f1f5f9;--cbg:#0f172a;--ibdr:#475569;--ifocus:#3b82f6;
  --pass-bg:#052e16;--pass-bdr:#166534;--pass-tx:#86efac;
  --fail-bg:#1f0000;--fail-bdr:#991b1b;--fail-tx:#fca5a5;
}

/* ── Shell ───────────────────────────────────────────────────────────────────── */
.shell {
  display: flex; flex-direction: row;
  width: 100%; height: 100%;
  border-radius: 14px; overflow: hidden;
  border: 1px solid var(--bdr);
  font-family: system-ui, -apple-system, sans-serif;
  color: var(--tx);
}

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
  display: none; align-items: center; gap: 2px; flex-shrink: 0; margin-left: 12px;
}
.cp-row:hover .cp-row-actions,
.cp-row.active .cp-row-actions { display: flex; }

/* Action buttons inside chats page use theme colours, not sidebar colours */
.cp-row .sa-btn        { color: var(--muted); }
.cp-row .sa-btn:hover  { background: var(--bdr); color: var(--tx); }
.cp-row .sa-btn.del:hover { background: rgba(220,38,38,.15); color: #dc2626; }

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
  flex: 1; font-size: 13px; font-weight: 600; color: var(--sb-tx);
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
.sb-empty        { font-size: 12px; color: var(--sb-muted); padding: 8px 6px; }
.sb-loading      { font-size: 12px; color: var(--sb-muted); padding: 10px 6px; }

.sb-row {
  display: flex; align-items: center;
  padding: 7px 8px; border-radius: 8px;
  cursor: pointer; min-width: 0; gap: 0;
  transition: background .12s;
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
.sb-row-actions {
  display: none; align-items: center; gap: 1px; flex-shrink: 0; margin-left: 4px;
}
.sb-row:hover .sb-row-actions,
.sb-row.active .sb-row-actions { display: flex; }
.sa-btn {
  width: 22px; height: 22px; border: none; border-radius: 4px;
  background: transparent; color: var(--sb-muted);
  cursor: pointer; font-size: 11px;
  display: flex; align-items: center; justify-content: center;
  transition: background .1s, color .1s;
}
.sa-btn:hover     { background: rgba(255,255,255,0.1); color: var(--sb-tx); }
.sa-btn.del:hover { background: rgba(239,68,68,0.2);   color: #f87171; }

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
.sb-footer {
  flex-shrink: 0; position: relative;
  padding: 8px 10px;
  border-top: 1px solid rgba(255,255,255,0.07);
}
.avatar-btn {
  width: 36px; height: 36px; border-radius: 50%;
  background: rgba(255,255,255,0.1); border: 1.5px solid rgba(255,255,255,0.15);
  color: var(--sb-tx); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background .15s, border-color .15s;
}
.avatar-btn:hover { background: rgba(255,255,255,0.18); border-color: rgba(255,255,255,0.28); }

/* User footer (collapsed) */
.sb-footer-col {
  flex-shrink: 0; position: relative;
  margin-top: auto; padding: 8px 0 10px;
  display: flex; justify-content: center;
  border-top: 1px solid rgba(255,255,255,0.07);
}
.avatar-col { margin: 0; }

/* User menu popup */
.user-menu {
  position: absolute; bottom: calc(100% + 6px); left: 8px;
  width: calc(100% - 16px);
  background: #1e2d42; border: 1px solid rgba(255,255,255,0.12);
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

/* Track tint — per agent, very subtle */
.progress-strip.intake     { background: rgba(59,  130, 246, 0.07); }
.progress-strip.discovery  { background: rgba(99,  102, 241, 0.07); }
.progress-strip.researcher { background: rgba(239, 68, 68, 0.07); }
.progress-strip.reviewer   { background: rgba(245, 158,  11, 0.07); }
.progress-strip.approver   { background: rgba(16,  185, 129, 0.07); }

/* Slow shimmer — per agent, muted opacity */
.progress-strip::after {
  content: '';
  position: absolute; top: 0; bottom: 0;
  width: 55%;
  animation: p-sweep 3.5s linear infinite;
}
.intake::after     { background: linear-gradient(90deg, transparent, rgba(59,  130, 246, 0.5), transparent); }
.discovery::after  { background: linear-gradient(90deg, transparent, rgba(99,  102, 241, 0.5), transparent); }
.researcher::after { background: linear-gradient(90deg, transparent, rgba(239, 68, 68, 0.5), transparent); }
.reviewer::after   { background: linear-gradient(90deg, transparent, rgba(245, 158,  11, 0.5), transparent); }
.approver::after   { background: linear-gradient(90deg, transparent, rgba(16,  185, 129, 0.5), transparent); }

@keyframes p-sweep {
  0%   { left: -55%; }
  100% { left: 100%; }
}

/* Dot + label — per agent colour */
.p-dot { position:relative;z-index:1;width:6px;height:6px;border-radius:50%;flex-shrink:0;animation:p-pulse 2s ease-in-out infinite; }
.intake .p-dot    { background: #3b82f6; }
.discovery .p-dot { background: #6366f1; }
.researcher .p-dot{ background: #ef4444; }
.reviewer .p-dot  { background: #f59e0b; }
.approver .p-dot  { background: #10b981; }
@keyframes p-pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.75)}}

.p-text { position:relative;z-index:1;font-size:12px;font-weight:500;letter-spacing:.02em;white-space:nowrap; }
.intake .p-text    { color: #2563eb; } .discovery .p-text { color: #4f46e5; }
.researcher .p-text{ color: #dc2626; } .reviewer .p-text  { color: #b45309; }
.approver .p-text  { color: #059669; }
.dark .intake .p-text    { color: #93c5fd; } .dark .discovery .p-text { color: #a5b4fc; }
.dark .researcher .p-text{ color: #fca5a5; } .dark .reviewer .p-text  { color: #fcd34d; }
.dark .approver .p-text  { color: #6ee7b7; }

/* Messages */
.messages { flex:1;overflow-y:auto;padding:20px 28px;display:flex;flex-direction:column;gap:14px;min-height:0; }
.empty-state{margin:auto;text-align:center;color:var(--muted);padding:40px 20px}
.empty-icon{font-size:42px;margin-bottom:12px}.empty-title{font-size:16px;font-weight:600;color:var(--tx);margin:0 0 6px}.empty-sub{font-size:14px;margin:0}
.message{display:flex;flex-direction:column;max-width:82%}
.message.user{align-self:flex-end;align-items:flex-end}.message.agent{align-self:flex-start;align-items:flex-start}
.stage-tag{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;border-radius:99px;margin-bottom:5px;background:var(--sbg);color:var(--stx)}
.stage-tag.discovery{background:#dbeafe;color:#1e40af}.stage-tag.researcher{background:#fee2e2;color:#991b1b}.stage-tag.reviewer{background:#ffedd5;color:#9a3412}.stage-tag.approver{background:#dcfce7;color:#166534}
.dark .stage-tag.discovery{background:#1e3a5f;color:#93c5fd}.dark .stage-tag.researcher{background:#450a0a;color:#fca5a5}.dark .stage-tag.reviewer{background:#431407;color:#fdba74}.dark .stage-tag.approver{background:#052e16;color:#86efac}
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
.verdict-body{margin:0 0 7px;color:var(--tx);line-height:1.5}
.verdict-list{margin:0;padding-left:1.3em;font-size:13px}.verdict-card.pass .verdict-list{color:var(--pass-tx)}.verdict-card.fail .verdict-list{color:var(--fail-tx)}.verdict-list li{margin:3px 0}
.spin{display:inline-block;width:16px;height:16px;flex-shrink:0;border:2px solid var(--sbdr);border-top-color:var(--stx);border-radius:50%;animation:spin .7s linear infinite}
.spin.large{width:22px;height:22px}
@keyframes spin{to{transform:rotate(360deg)}}

/* Input panel */
.input-panel{flex-shrink:0;padding:15px 28px;background:var(--surf);border-top:1px solid var(--bdr);display:flex;flex-direction:column;gap:10px}
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
.banner{flex-shrink:0;padding:12px 28px;font-size:13px;font-weight:500;text-align:center}
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
</style>
