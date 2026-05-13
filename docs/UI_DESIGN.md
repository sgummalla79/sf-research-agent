# UI Design Document — Technical Architecture Agent

## 1. Layout Architecture

The application shell uses a **column flex layout** with three layers:

```
┌──────────────────────────────────────────────────────────────────┐
│  PRIVACY BANNER (full width, always visible)                     │
├──────────────────────────────────────────────────────────────────┤
│  SHELL BODY (flex row, takes remaining height)                   │
│  ┌──────────────────┬──────────────────┬───────────────────────┐ │
│  │ SIDEBAR (240px)  │  CHAT PANE       │  DOC PANEL (0→42%)   │ │
│  │ (always dark)    │  (flex: 1)       │  (slides in inline)  │ │
│  │                  │                  │                       │ │
│  │  App Name   [⊟] │  Progress strip  │  Document header      │ │
│  │  [+] New Chat    │  Messages area   │  Rendered markdown    │ │
│  │  [💬] Chats     │  Input panel     │                       │ │
│  │  ─ Pinned ─      │  Banners         │                       │ │
│  │  Chat-1          │                  │                       │ │
│  │  ─ Recent ─      │                  │                       │ │
│  │  Chat-2          │                  │                       │ │
│  └──────────────────┴──────────────────┴───────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│  SHELL FOOTER (flex row, always visible)                         │
│  ┌──────────────────┬──────────────────────────────────────────┐ │
│  │  Avatar area     │  Token usage bar (per model, full width) │ │
│  │  (sidebar width) │                                          │ │
│  └──────────────────┴──────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

The chat pane switches between two views:
- **Chat view** — active conversation
- **Chats page** — full-screen conversation browser with search

The document panel slides in **inline** (not as an overlay), pushing the chat pane narrower.

---

## 2. Color System

All colors use CSS custom properties on `.shell` so dark/light mode is a single class toggle.
**Default mode is dark.**

### Light mode

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#f1f5f9` | Chat pane background |
| `--surf` | `#ffffff` | Cards, panels, bubbles |
| `--surf2` | `#f8fafc` | Input backgrounds, hover |
| `--bdr` | `#e2e8f0` | Borders, dividers |
| `--tx` | `#0f172a` | Primary text |
| `--muted` | `#64748b` | Secondary text, placeholders |
| `--pri` | `#2563eb` | Primary actions, user bubbles |

### Dark mode (`.shell.dark`) — default

| Token | Value |
|---|---|
| `--bg` | `#0f172a` |
| `--surf` | `#1e293b` |
| `--bdr` | `#334155` |
| `--tx` | `#f1f5f9` |
| `--muted` | `#94a3b8` |

### Sidebar (always dark)

| Token | Value |
|---|---|
| `--sb-bg` | `#1a2535` |
| `--sb-hover` | `#243044` |
| `--sb-active` | `#2d3f5a` |
| `--sb-tx` | `#c8d4e6` |
| `--sb-muted` | `#6b7f99` |

### Agent accent colours

Each agent stage has a unique accent used in the progress bar and stage tags:

| Agent | Colour |
|---|---|
| Intake | `#3b82f6` Blue |
| Discovery | `#6366f1` Indigo |
| Research | `#ef4444` Red |
| Review | `#f59e0b` Amber |
| Approver | `#10b981` Emerald |

---

## 3. Privacy Banner

A permanent slim banner at the very top of the shell, above all content:

```
🔒  All conversations are incognito · Data never leaves your machine ·
    Your inputs are never used to train AI models · No data is persisted by model providers
```

- Background: muted green tint (`rgba(16,185,129,0.08)`)
- Border-bottom: green tint (`rgba(16,185,129,0.2)`)
- Text: 13px, green tones in both light (`#065f46`) and dark (`#6ee7b7`) mode
- Always visible — cannot be dismissed

---

## 4. Sidebar

### Expanded state (240px)

```
Technical Architecture Agent    [⊟]   ← collapse icon
[+]  New Chat
[💬] Chats

📌 PINNED
  Kong API Token Review            📌✏️🗑
  Service Cloud Migration          📌✏️🗑

RECENT
  Data Cloud Design                📍✏️🗑
  Experience Cloud SSO             📍✏️🗑
```

- App name left-aligned, collapse icon (open-sidebar SVG) right-aligned
- Pinned and Recent sections have uppercase muted section headers
- Pinned rows show unpin (📌) action; recent rows show pin (📍) action
- Hover reveals: pin/unpin, rename, delete buttons
- Active session highlighted in `--sb-active`

### Collapsed state (52px)

```
[⊟]   ← sidebar icon (click to expand)
[+]   ← New Chat
[💬]  ← Chats
```

- All buttons centered, icon-only, `title` attribute provides tooltip

### Chats icon

Two overlapping speech bubbles SVG — represents multiple chats.

---

## 5. Shell Footer

A full-width row shared between the sidebar avatar area and the token usage bar. A single `border-top` line spans the entire width, perfectly aligned.

### Avatar area

- Width matches the sidebar (240px expanded / 52px collapsed), transitions with it
- Contains a circular avatar button (user silhouette icon)
- Click opens the **user menu popup** (see Section 6)

### Token usage bar

- Fills the remaining width (flex: 1)
- Always visible when a session with usage data is active
- Shows: **Session totals** cell + one cell per model used
- Each cell: model name (e.g. "Claude Sonnet 4.6") · `↑ input ↓ output` · `est. $X.XXX`
- Models shown: only those actually used in the session (dynamic, not fixed slots)
- Sorted by cost descending

---

## 6. User Menu

Triggered by clicking the avatar button in the shell footer. Pops up above the button.

```
  ⚙  Settings
  📊 Usage
  ─────────
  Appearance
  🌙 Dark mode  (or ☀️ Light mode)
```

- Transition: fade + slide-up (0.15s)
- Closes on any click outside

### Settings Modal

Opens from the user menu. Full-width modal, centered.

```
┌─ Settings ─────────────────────────────────────────────────────┐
│  API Keys                                                        │
│  Keys are encrypted at rest. Leave a field empty to keep key.   │
│                                                                  │
│  Anthropic API Key              [Configured ✓]                  │
│  Intake · Discovery · Research · Review · Approver               │
│  [••••••••••••••••••••••]                                       │
│                                                                  │
│  Perplexity API Key             [Not set]                       │
│  Research Agent — live web search (Sonar Pro)                    │
│  [pplx-…                       ]                                │
│  ⚠ Invalid Perplexity API key — check perplexity.ai/settings   │
│                                                                  │
│  Google API Key                 [Configured ✓]                  │
│  Research Agent — architectural patterns (Gemini 2.5 Pro)        │
│  [••••••••••••••••••••••]                                       │
│                                                  [Validating…]  │
└────────────────────────────────────────────────────────────────┘
```

- Each key shows **Configured ✓** (green) or **Not set** (red) badge
- Keys are validated against the provider's API before saving
- Invalid keys show a red border + inline error message
- Button shows "Validating…" during the API check (runs in parallel, ~2–4s)
- Empty fields are skipped (partial update allowed)

### Usage Modal

Opens from the user menu. Shows token usage and estimated cost.

```
┌─ Usage & Cost Estimate ────────────────────────────────────────┐
│  All Sessions (12 with usage data)                               │
│  ┌──────────────┬──────────────┬──────────────┐                │
│  │ ↑ 284.5K     │ ↓ 98.3K      │ est. $2.33   │                │
│  │ Input        │ Output       │ Cost          │               │
│  └──────────────┴──────────────┴──────────────┘                │
│                                                                  │
│  By Model                                                        │
│  Model                     ↑ Input  ↓ Output  Est. cost        │
│  Claude Sonnet 4.6          180K     60K       $1.47            │
│  Gemini 2.5 Pro              55K     22K       $0.29            │
│  Perplexity Sonar Pro        45K     15K       $0.34            │
│  Claude Haiku 4.5             4.5K   1.3K      $0.009           │
│                                                                  │
│  Prices are estimates based on published API rates.              │
└────────────────────────────────────────────────────────────────┘
```

---

## 7. Chats Full-Page View

Triggered by clicking the chats icon. Replaces the chat pane content.

```
Chats                                        [+ New chat]

🔍  Search your chats...

Your conversations
─────────────────────────────────────────────
Kong API Token Review
Last message 2 days ago
─────────────────────────────────────────────
Service Cloud Migration for Retail
Last message 7 days ago
```

- Search is real-time, filters as user types
- Rows show pin/unpin, rename, delete actions on hover

---

## 8. Agent Progress Bar

A 32px strip beneath the privacy banner (inside the chat pane), visible only when an agent is working:

- Per-agent tinted background (very subtle, 7% opacity)
- Animated shimmer sweeps left → right (3.5s loop, `linear`)
- Opacity: 50% — visible but not harsh
- Pulsing dot + "Discovery Agent is working…" label centered
- Collapses to 0 height (CSS transition) when no agent is running

| Agent | Shimmer colour |
|---|---|
| Intake | Blue `rgba(59,130,246,0.5)` |
| Discovery | Indigo `rgba(99,102,241,0.5)` |
| Research | Red `rgba(239,68,68,0.5)` |
| Review | Amber `rgba(245,158,11,0.5)` |
| Approver | Emerald `rgba(16,185,129,0.5)` |

---

## 9. Message Bubbles

| Type | Style |
|---|---|
| User | Right-aligned, `--pri` blue background, white text |
| Agent text | Left-aligned, `--surf` background, `--bdr` border |
| Document card | Blue border, clickable "View →" button, opens doc panel |
| Preparing | Spinner + "Preparing your architecture document…" |
| Reviewing | Spinner + description text |
| Review result (pass) | Green tinted card, ✅ badge |
| Review result (fail) | Red tinted card, ❌ badge, critical issues list |
| Approval result | Green (approved 🎉) or amber (rejected 🔄) card |

Each agent message has a small stage tag above the bubble (e.g. "DISCOVERY AGENT") in the agent's accent colour.

---

## 10. Input Panels

### Initial state (no session)

- Mode toggle: "✏️ Write Brief" / "📎 Upload File"
- Write Brief: multi-row textarea + "Start Session →" button (placeholder: "Describe your project…")
- Upload File: drag-and-drop zone, accepts PDF/DOCX/TXT/MD/PNG/JPG/GIF/WebP

### Intake confirmation (after file upload)

- Full-panel card showing the extracted understanding
- Optional corrections textarea
- "Looks right — start discovery →" button
- Graph is paused until confirmed

### Discovery reply

- Single question: inline textarea + Send button (Enter key submits)
- Multiple questions: one labelled textarea per question + "Send All Answers →"

---

## 11. Document Right Panel

Opens as an **inline right panel** (not an overlay) when the user clicks "View →" on a document card. The chat pane narrows; the doc panel grows from 0 → 42% width.

```
📄 Architecture Document v2      [⬇ Markdown] [⬇ PDF] [✕]
──────────────────────────────────────────────────────────
[Full rendered markdown — headings, tables, code blocks]
```

- Transition: `width 0.25s ease`
- Header: dark (`--hbg`), title + download buttons
- Body: full markdown rendering with 28px side padding
- Close button (✕) returns panel to 0 width

---

## 12. Delete Confirmation Dialog

Centered modal with blurred backdrop:

```
Delete conversation?
"Kong API Token Review"
This cannot be undone.

                    [Cancel]  [Delete]
```

- Triggered by any delete action (sidebar or chats page)
- Cancel or clicking outside dismisses
- Delete button: red (`#dc2626`)

---

## 13. Dark / Light Mode

Toggle: 🌙 / ☀️ in the user menu (avatar → Appearance).

- **Default: dark mode**
- Implemented via a single `.dark` class on `.shell`
- All colours are CSS variables — no JavaScript colour logic
- Transition is instant

The sidebar and shell footer are always dark regardless of theme.
