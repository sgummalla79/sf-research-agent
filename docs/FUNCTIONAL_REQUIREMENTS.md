# Functional Requirements Document — SF Research Agent

## 1. Purpose

SF Research Agent is a multi-agent AI system that guides users through a structured Salesforce architecture discussion and produces a formal Architecture Recommendation Document. The system targets **Service Cloud, Experience Cloud, and Data Cloud** implementations and serves both executive and delivery-team audiences.

---

## 2. User Roles

| Role | Description |
|---|---|
| **Architect / User** | Starts sessions, answers discovery questions, reviews output |
| **System (AI Agents)** | Intake, Discovery, Researcher, Reviewer, Approver |

---

## 3. Session Lifecycle

### 3.1 Starting a Session

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

### 3.2 Intake Confirmation (document/image only)

After extracting a project brief from an uploaded file:
1. The graph pauses and displays the extracted understanding to the user
2. The user reads and optionally adds corrections
3. User clicks "Looks right — start discovery →" to proceed
4. Any corrections are appended to the project brief before discovery begins

### 3.3 Discovery Phase

The Discovery Agent conducts a structured interrogation to close knowledge gaps before research begins.

**Behaviour:**
- Classifies the discussion type (Salesforce implementation, integration pattern, security design, architecture review, etc.)
- Asks only questions relevant to the confirmed discussion type — does not ask about clouds not in scope
- Groups independent questions together (up to 5 per round) to minimise back-and-forth
- Asks follow-up rounds only when prior answers open new dependent gaps
- Marks discovery complete when all critical gaps for the confirmed scope are closed
- Safety cap: maximum 30 questions total before automatically proceeding

**Question coverage (Salesforce implementation):**
- Business context: objective, stakeholders, timeline
- Cloud scope: Service Cloud, Experience Cloud, Data Cloud
- Salesforce edition and org type (greenfield/migration/extension)
- Scale: users, data volume, transaction volume
- Integration requirements and existing systems
- Compliance constraints (GDPR, HIPAA, PCI-DSS, etc.)
- Team maturity, certifications, CI/CD tooling
- Delivery partner and document audience

### 3.4 Research Phase

Runs automatically after discovery. No user interaction required.

Two research agents run in parallel:
1. **Perplexity Sonar Pro** — real-time web search for current Salesforce limits, Spring/Summer release notes, known issues, and citations
2. **Gemini 2.5 Pro** — deep architectural patterns, integration approaches, security models, Well-Architected Framework guidance

Claude Sonnet synthesises both research outputs into the final document.

### 3.5 Document Structure

The Architecture Recommendation Document contains:

1. Executive Summary
2. Architectural Goals & Constraints
3. Recommended Architecture (sub-sections per cloud)
   - 3a. Service Cloud (if in scope)
   - 3b. Experience Cloud (if in scope)
   - 3c. Data Cloud (if in scope)
   - 3d. Cross-Cloud Integration Design
4. Security Architecture
5. Technical Recommendations & Governor Limit Considerations
6. Deployment & Release Strategy
7. Risk Register
8. Open Questions & Assumptions

For non-Salesforce-centric discussions (pattern review, security design, etc.), a shorter focused document structure is used instead.

### 3.6 Review Phase

The Review Agent performs a one-way peer review against a 30-item checklist covering:
- Structure and completeness (all 8 sections present)
- Cloud-specific accuracy (per confirmed scope)
- Guest user security (Experience Cloud)
- Consent and PII handling (Data Cloud)
- Governor limit accuracy (no invented values)
- Async patterns and bulkification
- Deployment strategy
- Licensing flags

Returns: **PASSED** or **FAILED** with specific, actionable critical issues.

### 3.7 Approval Phase

The Approver Agent evaluates the document against 7 strategic lenses:
1. Business value alignment with the original brief
2. Audience fit (executive sections readable, technical sections actionable)
3. Delivery team readiness match
4. Salesforce roadmap alignment (GA vs Beta features)
5. Licensing reality check
6. Risk register quality and specificity
7. Open questions completeness

Returns: **APPROVED** or **REJECTED** with required changes.

### 3.8 Revision Loop

If the Approver rejects:
1. Required changes are returned to the Researcher
2. Researcher re-runs Perplexity + Gemini research (refreshed for this revision)
3. Claude produces a revised document with a `## Revision Summary` and `[RESOLVED: ...]` markers
4. Revised document goes through Reviewer → Approver again
5. Maximum 5 revision cycles before the session halts (configurable)

---

## 4. Document Output

### 4.1 Viewing

- The document appears as a **document card** in the chat (not streamed inline)
- Clicking "View →" opens a slide-in overlay panel (58% width)
- Full markdown rendering with headings, tables, code blocks

### 4.2 Downloading

Two formats available from the document overlay:
- **Markdown (.md)** — direct download of raw markdown
- **PDF** — opens a print-ready HTML page; user saves via browser print dialog

---

## 5. Session Management

### 5.1 Persistence

- Sessions persist for **15 days** (configurable via `SESSION_TTL_DAYS`)
- Sessions are automatically deleted after TTL expires
- Uploaded files are deleted alongside their session on expiry

### 5.2 Session Listing

- Sidebar shows all sessions ordered by **last modified date** (most recent first)
- Pinned sessions appear at the top, ordered by **pin date**

### 5.3 Session Operations

| Operation | Description |
|---|---|
| **New Chat** | Clears current session, shows brief input |
| **Restore** | Loads a previous session's messages, document state, and any pending questions |
| **Pin** | Moves session to pinned section; maximum 10 pinned sessions |
| **Unpin** | Returns session to recent list |
| **Rename** | Inline edit on the session row; Enter or blur saves |
| **Delete** | Requires confirmation dialog; removes session and uploaded files |

### 5.4 Smart Session Titles

Session titles are generated automatically by Claude Haiku within ~500ms of session creation:
- Text brief: title generated from the brief content
- Document upload: title generated from the extracted text
- Image upload: title generated from the filename/content description
- Fallback: raw brief snippet if Haiku generation fails

---

## 6. Search

### 6.1 Chats Page Search

- Full-page view accessible from sidebar "Chats" icon
- Real-time search across all session titles (pinned + recent)
- Filters as the user types; no submit required

---

## 7. Error Handling

| Scenario | Behaviour |
|---|---|
| LLM API rate limit or timeout | Automatic retry with exponential backoff (up to 5 attempts, 2s–32s) |
| Image not architecture-related | Clear rejection message shown; user can upload a different file |
| Unsupported file type | 415 error with accepted formats listed |
| File too large | Client-side check before upload; server enforces the same limit |
| Session not found on restore | Error message displayed in chat |
| Maximum revisions reached | Session marked as halted; human review message shown |
| Max 10 pinned sessions | Server-side 409 error; alert shown to user |

---

## 8. Accessibility & UX

- **Keyboard navigation:** Discovery questions support Enter to submit (single question mode)
- **Auto-scroll:** Messages area scrolls to bottom as new content streams in
- **Streaming cursor:** Blinking cursor shown while agent is actively generating text
- **Empty state:** Friendly prompt shown when no messages exist in a session
- **Tooltips:** Icon-only buttons in collapsed sidebar provide `title` tooltips
- **Confirmation on delete:** All delete operations require explicit confirmation
