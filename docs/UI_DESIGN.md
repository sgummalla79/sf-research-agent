# UI Design Document — Pragna

## 0. Typography

### Font family

| Context | Font | Notes |
|---|---|---|
| All UI text | **Carlito** | Loaded from Google Fonts. Set on `body` — all components inherit. |
| Brand name "Pragna" | **Martel** (serif) | Sidebar, login page, chat page header only. |
| Code blocks, prompt editors, model IDs, `kbd` | `monospace` | System monospace — intentional for code/technical content. |

**Rule:** No component should declare its own `font-family` unless it is one of the three cases above. Everything else inherits Carlito from `body`.

### Font smoothing

`-webkit-font-smoothing: antialiased` and `-moz-osx-font-smoothing: grayscale` are set globally on `body` for consistent sub-pixel rendering across platforms.

---

## 1. Layout Architecture

The application shell uses a **column flex layout** with three layers:

```
┌──────────────────────────────────────────────────────────────────┐
│  SHELL BODY (flex row, takes full height)                        │
│  ┌──────────────────┬──────────────────┬───────────────────────┐ │
│  │ SIDEBAR (240px)  │  CHAT PANE       │  DOC PANEL (0→42%)   │ │
│  │ (always dark)    │  (flex: 1)       │  (slides in inline)  │ │
│  │                  │                  │                       │ │
│  │  App Name   [⊟] │  Progress strip  │  Document header      │ │
│  │  [+] New Chat    │  Messages area   │  Rendered markdown    │ │
│  │  [💬] Chats     │  Input panel     │                       │ │
│  │  ─ Pinned ─      │  Privacy notice  │                       │ │
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

Clicking any sidebar item (conversation, New Chat) while on the Chats page navigates back to the chat view automatically.

---

## 2. Color System

All colours use CSS custom properties. Dark mode is the default; light mode is opt-in.

### Named palette — dark mode

Five named colours form the depth stack of the dark UI, ordered darkest → lightest:

```
┌──────────────────────────────────────────────┐
│  Elevated  #333333          --surface         │  ← Menus, modals, cards
├──────────────────────────────────────────────┤
│  Lift      ≈#313131         --hover           │  ← Hover & active states
├──────────────────────────────────────────────┤
│  Shade     #2c2c2c          --shade           │  ← Agent message bubbles
├──────────────────────────────────────────────┤
│  Ash       #282828          --bg  --sb-bg     │  ← All page backgrounds
├──────────────────────────────────────────────┤
│  Ink       #1a1a1a          --surface-2       │  ← Inset inputs, user bubbles
└──────────────────────────────────────────────┘
```

| Name | Hex | CSS token(s) | Role |
|---|---|---|---|
| **Ink** | `#1a1a1a` | `--surface-2` | Deepest layer — inset inputs, user message bubbles |
| **Ash** | `#282828` | `--bg`, `--sb-bg` | All page backgrounds — canvas, sidebar, settings, panels |
| **Shade** | `#2c2c2c` | `--shade` | Agent message bubbles |
| **Lift** | `≈#313131` (`rgba(255,255,255,0.06)` on Ash) | `--hover`, `--sb-hover`, `--sb-active` | Hover and active/selected states |
| **Elevated** | `#333333` | `--surface` | Menus, modals, cards, chat input box |

**Interaction rules:**
- **Hover** → **Lift** (`var(--hover)`) with `border-radius: 8px`
- **Selected / active** → **Lift** (`var(--hover)`) — same level as hover; selection is communicated by other means (font-weight, accent border) not by a different background
- **Exception — avatar menu items:** hover uses **Ash** (`var(--bg)`) since the popup itself sits on Lift, creating a subtle pressed-in feel

### Dark mode tokens

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#282828` (Ash) | Main canvas, all page backgrounds |
| `--surface` | `#333333` (Elevated) | Menus, modals, cards, chat input box |
| `--surface-2` | `#1a1a1a` (Ink) | Inset inputs, user message bubbles |
| `--shade` | `#2c2c2c` (Shade) | Agent message bubbles |
| `--hover` | `rgba(255,255,255,0.06)` (Lift ≈ #313131) | Hover and active/selected states |
| `--border` | `rgba(255,255,255,0.09)` | Dividers, borders |
| `--text` | `#ececea` | Primary text |
| `--muted` | `#888888` | Secondary text, placeholders |
| `--pri` | `#c97040` (default Gold theme) | Accent — buttons, focus rings |
| `--sb-bg` | `#282828` (Ash) | Sidebar background |
| `--sb-hover` | `rgba(255,255,255,0.06)` (Lift) | Sidebar item hover |
| `--sb-active` | `rgba(255,255,255,0.06)` (Lift) | Active conversation row |

### Light mode tokens

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#f5f5f4` | All page backgrounds |
| `--surface` | `#ffffff` | Cards, panels |
| `--surface-2` | `#f0efee` | Inset inputs |
| `--hover` | `#ebebea` | Menu item hover |
| `--sb-active` | `var(--hover)` | Active sidebar item |
| `--text` | `#1a1a1a` | Primary text |
| `--muted` | `#64748b` | Secondary text |
| `--pri` | `#b85c2a` | Accent |

### Agent accent colours

| Agent | Colour |
|---|---|
| Intake | `#3b82f6` Blue |
| Discovery | `#6366f1` Indigo |
| Research | `#ef4444` Red |
| Review | `#f59e0b` Amber |
| Approver | `#10b981` Emerald |

### Color usage rules

1. **No hardcoded hex values in components.** All colour references must use CSS custom properties (`var(--token)`). A single change in `App.vue` cascades everywhere automatically.
2. **CSS variables are the single source of truth.** Never duplicate a colour by writing its hex value in a component — reference the token instead.
3. **Standalone pages (Login, Callback) must also use global tokens.** These pages inherit all `:root` CSS variables. No exception.
4. **A colour change = one edit in `App.vue`.** If touching more than one file is needed, something is hardcoded and must be fixed first.
5. **Themes control accent only.** `useTheme.js` may only override accent tokens (`--pri`, `--pri-fg`, `--sbg`, `--stx`, `--sbdr`). Structural layout tokens like `--sb-active` must never be overridden by theme injection.

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

Removed from the top of the shell. Privacy information is now shown as a **notice line below the chat input**:

```
🔒  Incognito · stays on your device · never trains AI · not stored by providers
```

- Font: 14px, `var(--text)`, normal weight
- Centred below the chat input box
- Always visible, cannot be dismissed

---

## 4. Sidebar

### Background

The entire sidebar uses **Ash** (`var(--bg)`) as its background — same as the main canvas.

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

- App name left-aligned, collapse icon right-aligned
- Pinned and Recent sections have uppercase muted section headers
- Hover reveals: pin/unpin, rename, delete buttons
- Active session: **Lift** background (`--sb-active`)
- Chats button active: **Lift** background only — no text colour change

### Collapsed state (52px)

```
[⊟]   ← sidebar icon (click to expand)
[+]   ← New Chat
[💬]  ← Chats
```

All buttons centered, icon-only, `title` attribute provides tooltip.

### Navigation behaviour

Clicking any sidebar item (conversation row, New Chat button) while on the `/chats` page navigates back to `/` automatically before restoring or resetting the conversation.

---

## 5. Shell Footer

A full-width row shared between the sidebar avatar area and the token usage bar.

### Avatar area

- Width matches the sidebar, transitions with it
- Contains avatar button (initials or photo)
- Hover: **Lift** (`var(--sb-hover)`)
- Click opens the **user menu popup**

### Token usage bar

- Fills remaining width (flex: 1)
- Shows: Session totals + one cell per model used
- Each cell: model name · `↑ input ↓ output` · `est. $X.XXX`
- Models shown dynamically (only those used in the session), sorted by cost

---

## 6. User Menu

Triggered by clicking the avatar button. Pops up above the button. Background: **Lift** (`var(--hover)`).

```
  ⚙  Settings
  📊 Usage
  ─────────
  Appearance
  🌙 Dark mode  (or ☀️ Light mode)
  ─────────
  Sign out
```

- Menu items hover: **Ash** (`var(--bg)`) — pressed-in feel against Lift background
- Sign out hover: **Ash** (same as all other menu items — no accent colour)
- Transition: fade + slide-up (0.15s)
- Closes on any click outside

### Settings Page

Full-page view (replaces chat pane). Three-pane layout:

```
┌──────────────┬──────────────────────────────────────────────────┐
│ Settings nav │  Content area                                     │
│ (Ash bg)     │  (Ash bg)                                        │
│              │                                                   │
│  ← Back      │  [tab-specific content]                          │
│  Providers   │                                                   │
│  Skills      │                                                   │
│  Agents      │                                                   │
│  Prompts     │                                                   │
│  Usage       │                                                   │
│  Theme       │                                                   │
└──────────────┴──────────────────────────────────────────────────┘
```

- All pane backgrounds: **Ash**
- Skills tab renders the ConfigurationPage (3-pane: settings nav + file tree + content), all panes Ash
- Active nav item: **Lift** background + `font-weight: 600`

### Usage Modal

Opens from the user menu. Shows token usage and estimated cost by model.

---

## 7. Chats Full-Page View

Triggered by clicking the Chats icon. Renders in the main slot (sidebar remains visible).

- Search is real-time, filters as user types
- Clicking a conversation navigates to `/` and restores that conversation
- Rows show pin/unpin, rename, delete actions on hover

---

## 8. Agent Progress Bar

A 32px strip inside the chat pane, visible only when an agent is working:

- Per-agent tinted background (very subtle, 7% opacity)
- Animated shimmer sweeps left → right (3.5s loop)
- Pulsing dot + "Discovery Agent is working…" label centred
- Collapses to 0 height (CSS transition) when idle

| Agent | Shimmer colour |
|---|---|
| Intake | Blue `rgba(59,130,246,0.5)` |
| Discovery | Indigo `rgba(99,102,241,0.5)` |
| Research | Red `rgba(239,68,68,0.5)` |
| Review | Amber `rgba(245,158,11,0.5)` |
| Approver | Emerald `rgba(16,185,129,0.5)` |

---

## 9. Message Bubbles

### Colors

| Role | Background | Border | Alignment |
|---|---|---|---|
| User | **Ink** (`--surface-2`) | none | Right |
| Agent | **Ash** (`--bg`) | none | Left |

### Copy button

Both user and agent bubbles have a copy-to-clipboard button rendered **outside** the bubble, below it:

- Agent: bottom-left aligned
- User: bottom-right aligned
- Hidden by default; appears on hover of the bubble area
- On click: copies raw markdown content; icon switches to a green checkmark for 2 seconds
- Hover background: **Lift** (`var(--hover)`)

### Markdown rendering

**All LLM response content is rendered as markdown** (`MarkdownContent` component). This applies to:
- Regular chat text bubbles
- VerdictCard feedback text
- VerdictCard critical issues list

### Bubble types

| Type | Style |
|---|---|
| User text | Ink background, right-aligned |
| Agent text | Ash background, left-aligned, markdown rendered |
| Document card | Blue border, clickable "View →" button |
| Preparing / Reviewing / Approving | Spinner + status label (Ink background card) |
| Review result (pass) | Green tinted card, ✅ badge, markdown feedback |
| Review result (fail) | Red tinted card, ❌ badge, markdown feedback + issues |
| Approval result | Green (approved 🎉) or amber (rejected 🔄) card, markdown feedback |

---

## 10. Input Panel

### Chat input box

```
┌─────────────────────────────────────────────────────┐  ← Elevated bg
│  [file chip if attached]                            │
│  textarea (placeholder: "Message or type / …")     │
│  ─────────────────────────────────────────────────  │
│  [+]  [Architect ▾]  [model selector]    [Send →]  │
└─────────────────────────────────────────────────────┘
🔒 Incognito · stays on your device · never trains AI · not stored by providers
```

- Outer wrapper: **Ash** background
- Input box: **Elevated** background, rounded corners
- Privacy notice: 14px, `var(--text)`, centred below the box
- Dragging a file over the box highlights the border in accent colour

### Skill palette (`/` trigger)

Typing `/` opens the skill palette above the input:

- Lists installed skills with SVG icon + name
- Keyboard navigable (↑↓ Enter Escape)
- Hover/active row: **Lift**
- Hovering a row shows a description panel to the right

### Initial state (no session)

- Mode toggle: "✏️ Write Brief" / "📎 Upload File"
- Write Brief: textarea + "Start Session →" button
- Upload File: drag-and-drop zone, accepts PDF/DOCX/TXT/MD/PNG/JPG/GIF/WebP

### Intake confirmation (after upload)

- Full-panel card with extracted understanding
- Optional corrections textarea
- "Looks right — start discovery →" button

### Discovery reply

- Single question: inline textarea + Send
- Multiple questions: one labelled textarea per question + "Send All Answers →"

---

## 11. Document Right Panel

Opens inline when the user clicks "View →" on a document card. Chat pane narrows; doc panel grows 0 → 42%.

```
📄 Architecture Document v2      [⬇ Markdown] [⬇ PDF] [✕]
──────────────────────────────────────────────────────────
[Full rendered markdown — headings, tables, code blocks]
```

- Transition: `width 0.25s ease`
- Header: dark, title + download buttons
- Body: full markdown rendering, 28px side padding
- Close (✕) collapses to 0 width

---

## 12. Delete Confirmation Dialog

Centred modal with blurred backdrop:

```
Delete conversation?
"Kong API Token Review"
This cannot be undone.

                    [Cancel]  [Delete]
```

- Cancel or clicking outside dismisses
- Delete button: red (`var(--danger)`)

---

## 13. Dark / Light Mode

Toggle: 🌙 / ☀️ in the user menu (avatar → Appearance).

- **Default: dark mode**
- Implemented via `html.dark` class set by `useDarkMode` composable
- System preference used as fallback via `@media (prefers-color-scheme: dark)`
- All colours are CSS variables — no JavaScript colour logic
- Transition is instant

Themes (Gold, Sky Blue, Green, Purple, Red, White) change only the accent colour (`--pri` and derived tokens). They never override structural layout tokens.
