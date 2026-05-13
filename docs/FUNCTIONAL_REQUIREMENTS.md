# Functional Requirements — Technical Architecture Agent

## 1. Purpose

Technical Architecture Agent is a multi-agent AI system that guides users through a structured technical architecture engagement and produces a formal Architecture Recommendation Document. The system is platform-agnostic and works with any enterprise or SaaS technology stack. It serves both executive and delivery-team audiences.

---

## 2. User Roles

| Role | Description |
|---|---|
| **Architect / User** | Configures API keys, starts sessions, answers discovery questions, reviews and customises agent prompts, reviews output |
| **System (AI Agents)** | Intake, Discovery, Researcher, Reviewer, Approver |

---

## 3. First-Time Setup

Before starting any session, the user must configure API keys through the Settings UI:

1. Click the **avatar icon** (bottom-left of the shell footer)
2. Select **Settings**
3. Enter keys for all three providers:
   - **Anthropic API Key** — used by Intake, Discovery, Research (writing), Review, Approver, and session title generation
   - **Perplexity API Key** — used by Research Agent for live web search
   - **Google API Key** — used by Research Agent for architectural pattern reasoning (Gemini)
4. Click **Save Keys** — each key is validated against its provider's API before being saved

If any key is missing when **New Chat** is clicked, the Settings modal opens automatically with an error message indicating which keys are needed.

---

## 4. Session Types

### 4.1 Free-Form Chat

A direct conversation with Claude (no pipeline). Accessible from the main input when no Agent Flow is selected.

- Model selector: Opus 4.7, Sonnet 4.6 (default), Haiku 4.5
- Adaptive Thinking toggle: enables Anthropic Extended Thinking for deeper reasoning
- Supports `⌘/Ctrl + Enter` to send

### 4.2 Agent Flow Sessions

Structured 5-stage pipeline sessions. Triggered by selecting a flow from the **+** menu in the input box.

Available flows:
- **Technical Architect** — formal Architecture Recommendation Document via intake → discovery → research → review → approval

---

## 5. Agent Flow Session Lifecycle

### 5.1 Starting a Flow Session

1. Click **+** in the input box → select an Agent Flow
2. A pill appears in the bottom bar showing the selected flow
3. Placeholder updates to "Describe your project for [Flow Name]…"
4. Model picker and Adaptive Thinking are hidden (flow uses agent model config)
5. User types a project description and sends
6. Session starts — the flow is locked for the life of this session
7. A flow indicator bar appears below the progress strip showing which flow is active

**Mid-session flow change:** clicking a flow when a session is active shows a confirmation dialog. Confirming creates a new chat with the flow armed — session only starts when the user submits a description.

The user may **cancel** the selected flow before submitting (click ✕ on the pill) to return to normal chat mode.

### 5.2 Input Methods

| Method | Description |
|---|---|
| **Write Brief** | Type a project description directly |
| **Upload Document** | Upload PDF, DOCX, TXT, or MD — text extracted and summarised |
| **Upload Image** | Upload a PNG, JPG, GIF, or WebP architecture diagram — Claude Vision extracts the brief |

**File upload constraints:**
- Maximum file size: 10 MB (configurable)
- PDF: maximum 50 pages processed (configurable)
- Images: must depict architecture-related content (validated before session starts)

### 5.3 Intake Confirmation (document/image only)

After extracting a project brief from an uploaded file:
1. The graph pauses and displays the extracted understanding
2. The user optionally adds corrections
3. User clicks "Looks right — start discovery →" to proceed

### 5.4 Discovery Phase

The Discovery Agent conducts a platform-adaptive interrogation to close knowledge gaps.

**Behaviour:**
- Detects the platform(s) from the project brief and adapts questions accordingly
- Uses a platform-specific question checklist for the detected platform
- Groups independent questions together (up to 5 per round)
- Marks discovery complete when all critical gaps are closed
- Safety cap: maximum 30 questions before automatically proceeding

### 5.5 Research Phase

Runs automatically after discovery. Two agents run in parallel:

1. **Perplexity Sonar Pro** — real-time web search for current platform limits, official documentation, release notes, and citations. Restricted to official vendor sources and GA features only.
2. **Gemini 2.5 Pro** — deep architectural pattern reasoning and design guidance for the detected platforms.

Claude Sonnet synthesises both research outputs into the Architecture Recommendation Document.

### 5.6 Document Structure

The Architecture Recommendation Document contains:

1. Executive Summary
2. Engagement Context & Constraints
3. Current State Assessment (if applicable)
4. Proposed Architecture
5. Platform Limits & Constraints (official sources only, GA features only)
6. Security Architecture
7. Integration Architecture (if applicable)
8. Operational Considerations
9. Implementation Roadmap
10. Risks & Mitigations
11. Open Questions & Assumptions

### 5.7 Review Phase

The Review Agent performs a one-way peer review against a checklist covering technical accuracy, platform limits, completeness, soundness, and presentation quality. Returns: **PASSED** or **FAILED** with specific, actionable critical issues.

### 5.8 Approval Phase

The Approver Agent evaluates the document against 7 strategic lenses: business alignment, platform authorisation (GA sources only), risk honesty, completeness, scope discipline, commercial prudence, and client readiness. Returns: **APPROVED** or **REJECTED** with required changes.

### 5.9 Revision Loop

If the Approver rejects:
1. Required changes are returned to the Researcher
2. Researcher re-runs Perplexity + Gemini research (refreshed for this revision)
3. Claude produces a revised document with a `## Revision Summary` and `[RESOLVED: ...]` markers
4. Revised document goes through Reviewer → Approver again
5. Maximum 5 revision cycles before the session halts

---

## 6. Document Output

### 6.1 Viewing

- The document appears as a **document card** in the chat
- Clicking "View →" opens an inline right panel (42% width)
- Full markdown rendering with headings, tables, code blocks

### 6.2 Downloading

Two formats:
- **Markdown (.md)** — direct download of raw markdown
- **PDF** — opens a print-ready HTML page; user saves via browser print dialog

---

## 7. Agent Prompt Versioning

Accessible via **avatar icon → Configuration → Agent Prompts**.

### 7.1 Overview

Each agent's system prompt is versioned independently:

- **Draft** — editable, not yet applied to new sessions
- **Published** — immutable once published; applied to all new sessions
- Every publish automatically creates a new **Flow Snapshot** capturing the current published version of all agents in the flow

### 7.2 Workflow

1. Select an agent from the list (shows current version badge)
2. Edit the prompt in the editor
3. Click **Save as Draft** — changes are staged but not active
4. Click **Publish vN** — draft becomes the new published version; new flow snapshot is created
5. All new sessions from this point use the new version
6. **↩ Revert to published** — resets editor to current published content (no API call)
7. **Discard draft** — deletes the draft; published version remains active

### 7.3 Session Audit

Each session records the Flow Snapshot ID at start time. The snapshot captures the exact version of every agent prompt used in that session — fully auditable.

### 7.4 Version History

Each agent shows a collapsible version history. Past published versions can be loaded into the editor ("Restore") to create a new draft from them.

---

## 8. Session Management

### 8.1 Persistence

- Sessions persist for **15 days** (configurable via `SESSION_TTL_DAYS`)
- Sessions are automatically deleted after TTL expires

### 8.2 Session Listing

- Sidebar shows **Pinned** (ordered by pin date) and **Recent** (ordered by last modified)
- Smart titles generated by Claude Haiku within ~500ms of session creation

### 8.3 Session Operations

| Operation | Description |
|---|---|
| **New Chat** | Clears current session, shows brief input. Blocked if API keys are missing. |
| **Restore** | Loads a previous session's messages, document state, and pending questions |
| **Pin** | Moves session to Pinned section; maximum 10 pinned sessions |
| **Unpin** | Returns session to Recent list |
| **Rename** | Inline edit on the session row; Enter or blur saves |
| **Delete** | Requires confirmation dialog; removes session and uploaded files |

---

## 9. Settings

Accessible via **avatar icon → Settings**.

### 9.1 Providers

- Three password-masked inputs for Anthropic, Perplexity, and Google API keys
- Each shows a **Configured ✓** or **Not set** badge
- Keys validated against provider APIs before saving; encrypted at rest

### 9.2 Usage & Cost

Accessible via **avatar icon → Usage**.

- Token counts captured after every LLM call
- Permanent usage bar in shell footer shows current session totals per model
- Usage modal shows global totals and per-model breakdown across all sessions

**Pricing estimates** (per 1M tokens):

| Model | Input | Output |
|---|---|---|
| Claude Sonnet 4.6 | $3.00 | $15.00 |
| Claude Haiku 4.5 | $0.80 | $4.00 |
| Perplexity Sonar Pro | $3.00 | $15.00 |
| Gemini 2.5 Pro | $1.25 | $10.00 |

---

## 10. Configuration

Accessible via **avatar icon → Configuration**.

### 10.1 Agent Prompts

Versioned prompt editor — see Section 7.

### 10.2 Agent Models

Per-agent LLM assignment. Changes take effect on new sessions (locked at session start).

---

## 11. Privacy

- **All conversations are incognito** — no data shared beyond the live API call
- **Data never leaves your machine** — stored in local SQLite or self-hosted PostgreSQL
- **API keys encrypted at rest** — Fernet AES encryption; encryption key never reaches the client
- **No model training** — API usage does not contribute to model training
- Permanent privacy banner visible at all times

---

## 12. Error Handling

| Scenario | Behaviour |
|---|---|
| LLM API rate limit or timeout | Automatic retry with exponential backoff (up to 5 attempts, 2s–32s) |
| Invalid API key on save | Inline error per key; key not saved |
| API keys missing on New Chat | Settings modal opens automatically; session blocked |
| Image not architecture-related | Clear rejection message; user can upload a different file |
| Unsupported file type | 415 error with accepted formats listed |
| File too large | Client-side check before upload; server enforces the same limit |
| Session not found on restore | Error message displayed in chat |
| Maximum revisions reached | Session marked as halted |
| Max 10 pinned sessions | Server-side 409 error; alert shown |
| No draft to publish | 400 error from API |
