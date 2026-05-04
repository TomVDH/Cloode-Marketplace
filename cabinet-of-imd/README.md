# The Cabinet of IMD Agents — v3.0.0

A **flavour layer** for Claude Code: eight college classmates with
distinct personalities, voices, working disciplines, and pairings.
They serve as specialised web-development agents — each member has
a role, terminal style, and colour accent. They speak in their own
voices, collaborate through known pairings, and follow a set of
working disciplines (handoffs, dissent, scope, version parity).

**v3.0.0** is the flavour-only cut. Functionality is sunset:
- No vault writes from cabinet
- No session anchors
- No gate enforcement
- No state-tracking hooks

What remains is the crew themselves and how they work. **Persistence
is delegated to `obsidian-bridge`** when active. When it's not,
moments stay in conversation.

## The Roster

| Member | Role | Vibe |
|---|---|---|
| **Thieuke** | Frontend Specialist | Terse, snarky, clean code purist |
| **Sakke** | Backend & Security | Convivial, direct, Flemish through and through |
| **Jonasty** | Integrations / API / QA | Sardonic warmth, efficient with personality |
| **Pitr** | Full-stack Generalist | Maximum insight, minimum effort |
| **Henske** | WebGL / Three.js / Innovation | Smooth confidence, substance behind the show |
| **Bostrol** | Documentation & Architecture | Enthusiastic, structured, the Docu Daemon |
| **Kevijntje** | Bosun / Team Lead | Steady captain with warm Brussels humour |
| **Poekie** | Co-bosun / Systems & UX | Plain-spoken, jolly, systems thinker |

## How It Works

### Automatic Role Selection
The cabinet detects task context and channels the appropriate
specialist automatically. Each response opens with a styled header
showing who's active and their colour accent.

### Pairings
Members work in known pairings (UI Polish, Data UX, Iteration,
Performance, Full-Stack Vertical Slice, User Documentation, Git
Deployment) and super pairings (The Audit, The Experience, The
Ship, The Chroniclers, All Hands). See `references/dynamics.md`.

### Working Disciplines
Micro-handoffs, escalation, dissent logging, override traceability,
rollback, scope snapshots, parking lot, temperature checks, session
momentum, Pitr's razor, Poekie's user hat, Henske's visual counsel,
**version parity discipline** (Jonasty + Bostrol + Kevijntje
co-own), and pushback. None of this is enforced by the harness —
it's how the crew works because that's who they are. See
`references/protocols.md`.

### Voice & Chatter
Members speak in-chat in their own voices, prefixed `[Member]:`.
Chatter is in-chat only — not persisted to a file. Frequency is
organic — silence is fine; performance is not. Voice cheat-sheet
and content rules in `references/chatter-system.md`.

### Memory Discipline
The crew has a shared memory — IMD lore, Tom's preferences,
in-jokes, project-derived moments. The cabinet supplies the
discipline (what to ask, who notices, how it sounds). Persistence
is delegated to `obsidian-bridge` when active. See
`references/memories-system.md`.

### Code Conventions
The `## CABINET @` marker system — `@TODO`, `@SECTION`,
`@KNOWLEDGE` — provides greppable inline markers for action items,
file ownership, and knowledge drops.

### Hooks
Two flavour hooks run quietly:
- **SessionStart → `boot-flair.sh`** — surfaces a historical lore
  question, anniversary, or session counter (reads vault state via
  the `obsidian-bridge` breadcrumb, never writes).
- **Notification → `crew-notify.sh`** — rewrites generic Claude
  Code notifications in crew voice.

Both fail silently — they never block.

## Commands

| Command | Purpose |
|---|---|
| **/cabinet** | Wake up the crew — loads characters, dynamics, and disciplines. Opens with in-character chatter. |

## Skills

| Skill | Purpose |
|---|---|
| **crew-roster** | Display the roster with dynamic quips. Display only, no project work. |

## Pairs With

- **`obsidian-bridge`** — persistence layer. When active, the
  cabinet's documentation discipline (Chroniclers trio, decision
  notes, session summaries, memory entries) flows through the
  bridge. When inactive, the discipline stays in voice; nothing is
  written.

## Usage Notes

- Colours are terminal cosmetics only — headers, name glyphs. No
  bearing on project design output.
- The cabinet speaks in plain language. No AI-sounding output.
- Context-aware tone scaling: personality dials down for debugging,
  up for creative work.

## Author

Onnozelaer
