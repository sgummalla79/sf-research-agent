# UI Design Document — Pragna

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

All colours use CSS custom properties. Dark mode is the default; light mode is opt-in.

### Named palette — dark mode

Four named colours form the depth stack of the dark UI, ordered darkest → lightest:

```
┌──────────────────────────────────────────────┐
│  Elevated  #333333          --surface         │  ← Menus, modals, cards
├──────────────────────────────────────────────┤
│  Lift      ≈#313131         --hover           │  ← Hover state (6% white on Ash)
├──────────────────────────────────────────────┤
│  Ash       #282828          --bg  --sb-bg     │  ← All page backgrounds
├──────────────────────────────────────────────┤
│  Ink       #1a1a1a          --surface-2       │  ← Inset inputs, chat box
└──────────────────────────────────────────────┘
```

| Name | Hex | CSS token(s) | Role |
|---|---|---|---|
| **Ink** | `#1a1a1a` | `--surface-2` | Deepest layer — inset inputs, chat input box |
| **Ash** | `#282828` | `--bg`, `--sb-bg` | All page backgrounds — canvas, sidebar, panels |
| **Shade** | `#2c2c2c` | `--shade` | Agent message bubbles — between Ash and Lift |
| **Lift** | `≈#313131` (`rgba(255,255,255,0.06)` on Ash) | `--hover`, `--sb-hover` | Hover state — one step above Ash, below Elevated |
| **Elevated** | `#333333` | `--surface` | Menus, modals, cards, raised surfaces |

**Interaction rules:**
- **Hover** → **Lift** (`var(--hover)`) with `border-radius: 8px`
- **Selected / active** → **Lift** (`var(--hover)`) — same level as hover, selection is communicated by other means (font-weight, accent border, icon change), not by going darker or brighter

### Dark mode tokens

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#282828` (Ash) | Main canvas, all page backgrounds |
| `--surface` | `#333333` (Elevated) | Menus, modals, cards |
| `--surface-2` | `#1a1a1a` (Ink) | Inset inputs, chat box |
| `--hover` | `rgba(255,255,255,0.06)` (Lift ≈ #313131) | Menu item hover |
| `--border` | `rgba(255,255,255,0.09)` | Dividers, borders |
| `--text` | `#ececea` | Primary text |
| `--muted` | `#888888` | Secondary text, placeholders |
| `--pri` | `#c97040` | Accent — buttons, active states |
| `--sb-bg` | `#282828` (Ash) | Sidebar background |
| `--sb-hover` | `rgba(255,255,255,0.06)` (Lift) | Sidebar item hover |
| `--sb-active` | `rgba(255,255,255,0.08)` (Lift+) | Active conversation row |

### Light mode tokens

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#f5f5f4` | All page backgrounds |
| `--surface` | `#ffffff` | Cards, panels |
| `--surface-2` | `#f0efee` | Inset inputs |
| `--hover` | `#ebebea` | Menu item hover |
| `--text` | `#1a1a1a` | Primary text |
| `--muted` | `#64748b` | Secondary text |
| `--pri` | `#c97040` | Accent |

### Agent accent colours

| Agent | Colour |
|---|---|
| Intake | `#3b82f6` Blue |
| Discovery | `#6366f1` Indigo |
| Research | `#ef4444` Red |
| Review | `#f59e0b` Amber |
| Approver | `#10b981` Emerald |

### Color usage rules

1. **No hardcoded hex values in components.** All colour references must use CSS custom properties (`var(--token)`). This ensures a single change in `App.vue` cascades everywhere automatically.
2. **CSS variables are the single source of truth.** Never duplicate a colour by writing its hex value in a component — reference the token instead.
3. **Standalone pages (Login, Callback) must also use global tokens.** These pages render inside the same `<html>` element and therefore inherit all `:root` CSS variables. There is no exception.
4. **A colour change = one edit in `App.vue`.** If you need to touch more than one file to change a design token, it means something is hardcoded and must be fixed first.

---

## 2a. Icon System

Skills use custom SVG icons served from `/public/icons/`. Two variants are provided per skill — one per theme.

| File | Theme | Style |
|---|---|---|
| `/icons/skill-dark.svg` | Dark mode | White stroke, no fill, transparent bg |
| `/icons/skill-light.svg` | Light mode | Dark stroke, no fill, transparent bg |

Theme switching is handled by `useSkillIcon.js` composable which returns the correct URL based on `isDark`. The composable is used in all places where skill icons are rendered: ChatInput menu, SkillPalette, SkillDirectory, ConfigurationPage, SettingsPage nav, SkillsSettings.

**Adding a new skill icon:** Place `skill-{id}-dark.svg` and `skill-{id}-light.svg` in `frontend/public/icons/` and add the skill id to `SKILL_SVG_ICONS` in `useSkillIcon.js`.

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
Pragna    [⊟]   ← collapse icon
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
| User | Right-aligned, Ink (`--surface-2`) background, primary text |
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
