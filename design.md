# design.md — UI/UX for The Lenny Growth Assistant

## Principles

1. **The chat is the product; the artifact viewer is a peer, not a modal.**
   Generated documents open in a side-by-side panel (not a new tab, not a
   popup) so the user can keep the conversation and the output in view at
   once — closer to how Claude's own Artifacts work than to a "download and
   open elsewhere" pattern, per the assignment's explicit ask.
2. **Grounding is always visible, never a tooltip you have to hunt for.**
   Every grounded answer shows which provider answered, which skill handled
   it, and which transcript episodes it drew from, inline under the message
   — so trust in the answer is verifiable at a glance, not asserted.
3. **Failure states look like failure states.** A provider outage or an
   empty knowledge-base result renders as a distinct, clearly-labeled error
   bubble (red border, ⚠️ prefix) — never styled identically to a normal
   assistant reply, so the user never mistakes "I couldn't answer" for a
   real (possibly hallucinated) answer.
4. **Minimal chrome, maximal legibility.** Dark, high-contrast theme with a
   single accent color reserved for interactive/affirmative elements
   (send button, active session, links) so it's obvious what's clickable.

## Information architecture

```
┌─────────────┬─────────────────────────────────────────────┐
│  Sidebar     │  Top bar: KB status · provider dropdown       │
│  - New chat  ├───────────────────────┬───────────────────────┤
│  - Session   │  Chat pane             │  Artifact Viewer       │
│    list      │  - messages            │  (only rendered when   │
│              │  - skill chips         │   an artifact exists   │
│              │  - composer            │   for the session)     │
└─────────────┴───────────────────────┴───────────────────────┘
```
- **Sidebar**: session switcher. Each session is independent (own DB row,
  own message history) — switching sessions is instant and doesn't lose
  in-flight state elsewhere.
- **Top bar**: two pieces of system state the evaluator specifically needs
  to see per the assignment brief — knowledge-base health, and which model
  provider is active (with per-provider configured/reachable status in the
  dropdown itself, not hidden in a settings page).
- **Chat pane**: standard message list + composer. Skill chips (`Auto`,
  `Grounded Q&A`, `Ship 30/30 essay`, `Artifact`) let the user override the
  keyword-based router explicitly when they know what they want.
- **Artifact Viewer**: appears only when the active session has produced an
  artifact; closing it collapses the layout back to a single chat column.

## Key interaction states

| State | Treatment |
|---|---|
| Backend unreachable at load | Full-screen message pointing to README troubleshooting, instead of a blank/broken UI |
| No sessions yet | A session is auto-created on first load — zero-click start |
| Message in flight | Composer's Send button disables; a "Thinking…" bubble appears | 
| Grounded answer | Assistant bubble + provider/skill badges + collapsible-style source list underneath |
| "Not covered" answer | Same assistant bubble styling as any other reply (still `grounded: false` in the API, but not visually alarming — it's a normal, expected outcome, not an error) |
| Provider/DB failure | Distinct red-bordered error bubble with the server's actual error detail, not a generic "something went wrong" |
| Artifact generated | Viewer opens automatically; an "Open artifact →" pill remains on the originating message so it can be reopened later in the session |

## Responsive behavior

- **≥ 1000px**: chat pane and artifact viewer render side-by-side (50/50).
- **800–1000px**: artifact viewer stacks below/takes over full width when
  open (grid collapses to a single column) rather than squeezing both panes
  unreadably thin.
- **< 800px**: sidebar hides entirely (mobile-first assumption: session
  switching is a secondary action on small screens); chat becomes the full
  viewport.

## Accessibility considerations

- All interactive elements are real `<button>`/`<select>`/`<textarea>`
  elements (no click-handler `<div>`s) so they're keyboard-reachable and
  screen-reader-focusable by default.
- Composer submits on `Enter`, inserts a newline on `Shift+Enter` — matches
  the convention users already expect from chat apps.
- Color is never the only signal: error state combines a red border **and**
  a `⚠️` glyph **and** distinct copy, not color alone.
- Text contrast: the dark theme uses `#e8e9ec` text on `#0f1115`/`#171a21`
  backgrounds, comfortably above WCAG AA for body text.
- The artifact iframe has a descriptive `title` attribute (the artifact's
  own title) for assistive tech announcing the embedded frame.

## Design decisions worth calling out

- **No client-side HTML rendering of raw artifact content outside the
  sandboxed iframe.** This was a deliberate design constraint, not an
  oversight — see architecture.md#artifact-security for the full rationale.
- **Sources are shown as episode titles, not raw excerpts, in the compact
  view** — full excerpts are available via the API (`ChatResponse.sources`)
  but the chat UI keeps the primary reading surface uncluttered; a future
  iteration could make each source expandable inline.
- **No streaming response animation** — a deliberate scope cut (see PRD)
  to keep the demo's request/response contract simple and testable; the
  "Thinking…" state is honest about latency rather than simulating
  responsiveness it doesn't have.
