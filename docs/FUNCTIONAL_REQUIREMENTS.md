# Functional Requirements Document — SF Research Agent

## 1. Purpose

SF Research Agent is a multi-agent AI system that guides users through a structured Salesforce architecture discussion and produces a formal Architecture Recommendation Document. The system targets **Service Cloud, Experience Cloud, and Data Cloud** implementations and serves both executive and delivery-team audiences.

---

## 2. User Roles

| Role | Description |
|---|---|
| **Architect / User** | Configures API keys, starts sessions, answers discovery questions, reviews output |
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

## 4. Session Lifecycle

### 4.1 Starting a Session

The user may start a session in three ways:

| Method | Description |
|---|---|
| **Write Brief** | Type a free-form project brief directly into the chat |
| **Upload Document** | Upload a PDF, DOCX, TXT, or MD file; the system extracts and summarises the brief |
| **Upload Image** | Upload a PNG, JPG, GIF, or WebP architecture diagram; Claude Vision validates and extracts the brief |

**File upload constraints:**
- Maximum file size: 10 MB (configurable)
- PDF: maximum 50 pages processed (configurable)
- Images: must depict architecture-related content (validated by Claude Vision before session starts)

### 4.2 Intake Confirmation (document/image only)

After extracting a project brief from an uploaded file:
1. The graph pauses and displays the extracted understanding to the user
2. The user reads and optionally adds corrections
3. User clicks "Looks right — start discovery →" to proceed
4. Any corrections are appended to the project brief before discovery begins

### 4.3 Discovery Phase

The Discovery Agent conducts a structured interrogation to close knowledge gaps before research begins.

**Behaviour:**
- Classifies the discussion type (Salesforce implementation, integration pattern, security design, architecture review, etc.)
- Asks only questions relevant to the confirmed discussion type
- Groups independent questions together (up to 5 per round) to minimise back-and-forth
- Asks follow-up rounds only when prior answers open new dependent gaps
- Marks discovery complete when all critical gaps for the confirmed scope are closed
- Safety cap: maximum 30 questions total before automatically proceeding

### 4.4 Research Phase

Runs automatically after discovery. No user interaction required.

Two research agents run in parallel:
1. **Perplexity Sonar Pro** — real-time web search for current Salesforce limits, Spring/Summer release notes, known issues, and citations
2. **Gemini 2.5 Pro** — deep architectural patterns, integration approaches, security models, Well-Architected Framework guidance

Claude Sonnet synthesises both research outputs into the final document.

### 4.5 Document Structure

The Architecture Recommendation Document contains:

1. Executive Summary
2. Architectural Goals & Constraints
3. Recommended Architecture (sub-sections per cloud)
4. Security Architecture
5. Technical Recommendations & Governor Limit Considerations
6. Deployment & Release Strategy
7. Risk Register
8. Open Questions & Assumptions

For non-Salesforce-centric discussions (pattern review, security design, etc.), a shorter focused document structure is used.

### 4.6 Review Phase

The Review Agent performs a one-way peer review against a 30-item checklist. Returns: **PASSED** or **FAILED** with specific, actionable critical issues.

### 4.7 Approval Phase

The Approver Agent evaluates the document against 7 strategic lenses. Returns: **APPROVED** or **REJECTED** with required changes.

### 4.8 Revision Loop

If the Approver rejects:
1. Required changes are returned to the Researcher
2. Researcher re-runs Perplexity + Gemini research (refreshed for this revision)
3. Claude produces a revised document with a `## Revision Summary` and `[RESOLVED: ...]` markers
4. Revised document goes through Reviewer → Approver again
5. Maximum 5 revision cycles before the session halts

---

## 5. Document Output

### 5.1 Viewing

- The document appears as a **document card** in the chat
- Clicking "View →" opens an inline right panel (42% width) — the chat pane narrows
- Full markdown rendering with headings, tables, code blocks

### 5.2 Downloading

Two formats available from the document panel:
- **Markdown (.md)** — direct download of raw markdown
- **PDF** — opens a print-ready HTML page; user saves via browser print dialog

---

## 6. Session Management

### 6.1 Persistence

- Sessions persist for **15 days** (configurable via `SESSION_TTL_DAYS`)
- Sessions are automatically deleted after TTL expires
- Uploaded files are deleted alongside their session on expiry

### 6.2 Session Listing

- Sidebar shows all sessions in two sections: **Pinned** (ordered by pin date) and **Recent** (ordered by last modified)
- Smart titles generated by Claude Haiku within ~500ms of session creation

### 6.3 Session Operations

| Operation | Description |
|---|---|
| **New Chat** | Clears current session, shows brief input. Blocked if API keys are missing. |
| **Restore** | Loads a previous session's messages, document state, and pending questions |
| **Pin** | Moves session to Pinned section; maximum 10 pinned sessions |
| **Unpin** | Returns session to Recent list |
| **Rename** | Inline edit on the session row; Enter or blur saves |
| **Delete** | Requires confirmation dialog; removes session and uploaded files |

---

## 7. Settings

Accessible via **avatar icon → Settings**.

### 7.1 API Key Management

- Three password-masked inputs for Anthropic, Perplexity, and Google API keys
- Each shows a **Configured ✓** or **Not set** badge
- On save, each provided key is validated against its provider's live API before being stored
- Keys are encrypted at rest using Fernet symmetric encryption (`SETTINGS_SECRET`)
- Partial updates allowed — leaving a field empty keeps the existing key
- Invalid keys show inline error messages with provider-specific guidance

---

## 8. Usage & Cost Estimation

Accessible via **avatar icon → Usage**.

### 8.1 Token Tracking

Token counts are captured after every LLM call (including structured-output calls via `include_raw=True`). Records are grouped by model and stored per session.

### 8.2 Session Usage Bar

A permanent bar at the very bottom of the shell footer shows the current session's usage:
- **Session** cell: total input tokens, output tokens, estimated cost
- One cell per model used (dynamic — only models that ran appear): Claude Sonnet 4.6, Perplexity Sonar Pro, Gemini 2.5 Pro, Claude Haiku 4.5
- Updates after every stream segment (not just at completion)

### 8.3 Usage Modal

The Usage modal (avatar → Usage) shows:
- Overall totals across all sessions
- Per-model breakdown with input tokens, output tokens, and estimated cost
- Session count

**Pricing used for estimates** (approximate, based on published rates):

| Model | Input | Output |
|---|---|---|
| Claude Sonnet 4.6 | $3.00 / 1M | $15.00 / 1M |
| Claude Haiku 4.5 | $0.80 / 1M | $4.00 / 1M |
| Perplexity Sonar Pro | $3.00 / 1M | $15.00 / 1M |
| Gemini 2.5 Pro | $1.25 / 1M | $10.00 / 1M |

---

## 9. Privacy

- **All conversations are incognito** — no data is shared beyond the live API call
- **Data never leaves your machine** — sessions, messages, and documents are stored in a local SQLite database (or self-hosted PostgreSQL)
- **API keys encrypted at rest** — stored using Fernet AES encryption; the encryption key (`SETTINGS_SECRET`) never leaves the server
- **No model training** — API usage does not contribute to model training (per provider API terms)
- A permanent privacy banner at the top of the UI reinforces these guarantees

---

## 10. Search

### 10.1 Chats Page Search

- Full-page view accessible from sidebar "Chats" icon
- Real-time search across all session titles (pinned + recent)
- Filters as the user types; no submit required

---

## 11. Error Handling

| Scenario | Behaviour |
|---|---|
| LLM API rate limit or timeout | Automatic retry with exponential backoff (up to 5 attempts, 2s–32s) |
| Invalid API key on save | Inline error per key with provider-specific guidance; key not saved |
| API keys missing on New Chat | Settings modal opens automatically; session blocked |
| Image not architecture-related | Clear rejection message shown; user can upload a different file |
| Unsupported file type | 415 error with accepted formats listed |
| File too large | Client-side check before upload; server enforces the same limit |
| Session not found on restore | Error message displayed in chat |
| Maximum revisions reached | Session marked as halted; human review message shown |
| Max 10 pinned sessions | Server-side 409 error; alert shown to user |

---

## 12. Accessibility & UX

- **Keyboard navigation:** Discovery questions support Enter to submit (single question mode)
- **Auto-scroll:** Messages area scrolls to bottom as new content streams in
- **Streaming cursor:** Blinking cursor shown while agent is actively generating text
- **Empty state:** Friendly prompt shown when no messages exist in a session
- **Tooltips:** Icon-only buttons in collapsed sidebar provide `title` tooltips
- **Confirmation on delete:** All delete operations require explicit confirmation
- **Dark mode default:** App launches in dark mode; toggle available in user menu
