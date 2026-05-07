# UI Design Document — SF Research Agent

## 1. Layout Architecture

The application is a single-page layout with two primary zones:

```
┌──────────────────────────────────────────────────────────────┐
│  SIDEBAR (240px expanded / 52px collapsed)  │  CHAT PANE    │
│                                             │  (flex: 1)    │
│  [Open/Close icon]  App Name               │               │
│  [+] New Chat                               │  Header       │
│  [💬] Chats                                 │  Progress bar │
│                                             │  Messages     │
│  Chat-1                                     │               │
│  Chat-2                                     │  Input panel  │
│  Chat-3                                     │               │
└──────────────────────────────────────────────────────────────┘
```

The chat pane switches between two views:
- **Chat view** — active conversation
- **Chats page** — full-screen conversation browser with search

A document overlay slides in from the right when the user opens an architecture document.

---

## 2. Color System

All colors use CSS custom properties on `.shell` so dark/light mode is a single class toggle.

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

### Dark mode (`.shell.dark`)

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
| Research | `#8b5cf6` Purple |
| Review | `#f59e0b` Amber |
| Approver | `#10b981` Emerald |

---

## 3. Sidebar

### Expanded state (240px)

```
Salesforce Architect Agent         [⊟]   ← collapse icon
[+]  New Chat
[💬] Chats

  Kong API Token Review            📍✏️🗑  ← hover actions
  Service Cloud Migration
  Data Cloud Design
```

- App name left-aligned, collapse icon (open-sidebar SVG) right-aligned
- No `<` chevron — the sidebar icon itself is the toggle
- Chat rows: plain text only, no per-row icons
- Hover reveals: pin, rename, delete buttons
- Active session highlighted in `--sb-active`
- Pinned sessions appear first (no separate section header needed when mixed)

### Collapsed state (52px)

```
[⊟]   ← Salesforce sidebar icon (click to expand)
[+]   ← New Chat
[💬]  ← Chats (click opens full chats page)
```

- All buttons centered, icon-only
- `title` attribute provides tooltip on hover
- The sidebar icon uses the open-sidebar layout SVG (transparent background)

### Chats icon

Two overlapping speech bubbles SVG — represents "multiple chats" (plural).

---

## 4. Chats Full-Page View

Triggered by clicking the chats icon. Replaces the chat pane content.

```
Chats                                        [+ New chat]

🔍  Search your chats...

Your chats with Salesforce Architecture Agent
─────────────────────────────────────────────
Kong API Token Review
Last message 2 days ago
─────────────────────────────────────────────
Service Cloud Migration for Retail
Last message 7 days ago
```

- Background: `--bg` (respects theme)
- "Chats" heading: 28px bold
- "+ New chat" button: outlined, `--bdr` border
- Search input: full width, prominent (15px), border highlights to `--pri` on focus
- Rows: title (15px medium) + relative timestamp (13px muted), thin `--bdr` dividers
- Hover reveals pin / rename / delete actions

---

## 5. Agent Progress Bar

A 30px strip beneath the header, visible only when an agent is working:

- Full-width tinted background in the agent's accent colour
- Animated shimmer sweeps left → right (1.8s loop)
- Pulsing dot + "Discovery Agent is working…" label centered
- Collapses to 0 height (CSS transition) when no agent is running

---

## 6. Message Bubbles

| Type | Style |
|---|---|
| User | Right-aligned, `--pri` blue background, white text |
| Agent text | Left-aligned, `--surf` background, `--bdr` border |
| Document card | Blue border, clickable "View →" button, opens document panel |
| Preparing | Spinner + "Preparing your architecture document…" |
| Reviewing | Spinner + description text |
| Review result (pass) | Green tinted card, ✅ badge |
| Review result (fail) | Red tinted card, ❌ badge, critical issues list |
| Approval result | Green (approved 🎉) or amber (rejected 🔄) card |

Each agent message has a small stage tag above the bubble (e.g. "DISCOVERY AGENT") coloured with the agent's accent.

---

## 7. Input Panels

### Initial state (no session)

- Mode toggle: "✏️ Write Brief" / "📎 Upload File"
- Write Brief: multi-row textarea + "Start Session →" button
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

## 8. Document Overlay

Slides in from the right as an overlay (58% width, max 820px). Backdrop darkens the chat.

```
📄 Architecture Document v2         [⬇ Markdown] [⬇ PDF] [✕]
─────────────────────────────────────────────────────────────
[Full rendered markdown document with headings, tables, code]
```

- Header: dark (`--hbg`), title + download buttons
- Body: full markdown rendering — headings, tables, code blocks, blockquotes
- Smooth slide-in/out transition
- Click backdrop to close

---

## 9. Delete Confirmation Dialog

Centered modal with blurred backdrop:

```
Delete conversation?
"Kong API Token Review"
This cannot be undone.

                    [Cancel]  [Delete]
```

- Triggered by any delete action (sidebar or chats page)
- Cancel dismisses; clicking outside also dismisses
- Delete button: red (`#dc2626`)

---

## 10. Dark / Light Mode

Toggle: 🌙 / ☀️ button in the chat header (top right).

Implemented via a single `.dark` class on `.shell`. All colours are CSS variables — no JavaScript colour logic. Transition is instant (no animation).

The sidebar is always dark regardless of theme (matches industry convention for navigation panels).
