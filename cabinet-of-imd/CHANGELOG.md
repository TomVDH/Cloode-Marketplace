# Changelog

All notable changes to the Cabinet of IMD plugin.

## 3.0.0 — 2026-05-01

**Flavour-only cut.** The cabinet sunsets all functionality and
becomes a flavour layer: characters, voices, pairings, working
disciplines. Persistence is delegated to `obsidian-bridge`.

### Removed
- **Vault references** — `vault-integration.md`, `vault-standards.md`, `vault-images.md`, `obsidian-setup.md`. All vault structure and writes belong to `obsidian-bridge`.
- **Session anchor** — `session-anchor.md` and all anchor logic. The cabinet has no state file.
- **Gate enforcement** — `gate-protocol.md` deleted. Gates remain as informal milestones in working disciplines, not enforcement machinery.
- **Wrap-up ceremony** — `chatter-extended.md` deleted. Wrap-ups still happen organically through chatter and pairings; no dedicated ceremony protocol.
- **Superpowers integration** — `superpowers-integration.md` deleted.
- **Vault templates** — `examples/vault-templates/` folder removed (lived in `obsidian-bridge` already).
- **State-tracking hooks** — `save-anchor.sh`, `pulse.sh`, `session-close.sh`, `banter-roll.sh` deleted.
- **Skills** — `cabinet-resume`, `cabinet-status`, `cabinet-tune` deleted (anchor-dependent).
- **Commands** — `/invoke` (manual specialist activation; auto-selection from `dynamics.md` + `specialist-contract.md` is the only path now), `/create-classmate` (guest-specialist creation flow).

### Changed
- **`commands/cabinet.md` slimmed** — from 486 lines to ~150. Removed: vault discovery, anchor reads/writes, chatter level setting, vault chatter initialisation, memories file initialisation, anchor write triggers. Kept: lazy character loading, roster header, time/day-aware wake-up chatter, scene seeds, running-joke pulls, voice rules, ready state.
- **`references/memories-system.md` rewritten** — describes the memory **discipline** (what to ask, who notices, how it sounds). All persistence delegated to `obsidian-bridge` via a clean structured payload. If the bridge isn't active, moments are ephemeral.
- **`references/chatter-system.md` rewritten** — chatter is **in-chat only**. Stripped: file location, append method, vault paths. Kept and recast: voice cheat-sheet, in-chat formatting, markers (now "milestone" framing not "gate"), when-to-chime-in cadence, content guidelines, easter eggs, the nudge.
- **`references/protocols.md` rewritten** — kept all working disciplines (micro-handoffs, escalation, dissent, scope, parking lot, temperature, momentum, tone scaling, ambiguity, knowledge gaps, Pitr's razor, Poekie's user hat, Henske's visual counsel, version parity, pushback, accountability). Recast vault-write logic to delegate to `obsidian-bridge`. Documentation Authority section softened — Bostrol still cares; the bridge does the writing.
- **`references/specialist-contract.md` rewritten** — major slim. Removed all anchor/vault discovery logic. New flow: load identity, display header, acknowledge in voice. Documentation moments flagged in voice; the bridge picks them up.
- **`references/dynamics.md`** — Chroniclers trio recast: discipline persists, persistence flows through `obsidian-bridge`. "Governance Model > Gate Protocol" subsection rewritten as informal "Working in Stages."
- **`hooks/hooks.json`** — keeps only `SessionStart → boot-flair.sh` and `Notification → crew-notify.sh`.
- **`hooks/scripts/boot-flair.sh`** — simplified. Reads vault state only via `obsidian-bridge` breadcrumb. Removed cabinet's own `.cabinet-anchor-hint` fallback and the anchor-file existence gate.
- **`skills/crew-roster/SKILL.md`** — light pass; removed references to chatter logging and gate mechanics.
- README and plugin description rewritten around the flavour-only positioning.

### Kept (unchanged)
- All eight character YAMLs (`references/characters/`).
- `references/code-conventions.md` (CABINET marker system).
- `references/terminal-colours.md` (header colours).
- `hooks/scripts/crew-notify.sh` (notification voice).
- `hooks/lib/running-jokes.txt`.

---

## 2.3.0 — 2026-04-30

Vault structure & /dream extracted to obsidian-bridge plugin. Cabinet's /vault-bridge skill and /dream command removed. Cabinet's vault refactor pending; existing v2 vault behavior preserved as deprecated path.

---

## v2.2.0 — Vault-First + Hooks

- **Vault is now required.** `/cabinet` refuses to boot without a connected vault. No local-filesystem fallback. Rationale: ghost-state bugs and confusing "degraded mode." See `references/vault-integration.md § Vault Requirement`.
- **Session anchor moved into the vault.** Path: `{vault}/projects/{slug}/.anchor.json`. The `crew-notes/` directory is no longer created in project folders. Schema gained `vault.anchor_path` + a `hooks` block for hook-driven state. See `references/session-anchor.md`.
- **Four skills promoted to slash-commands** for context efficiency and cleaner trigger semantics:
  - `/cabinet` (was `skills/cabinet`)
  - `/invoke` (was `skills/invoke`)
  - `/dream` (was `skills/dream`)
  - `/create-classmate` (was `skills/create-classmate`)
- **Tightened skill descriptions** across the remaining skills (`cabinet-resume`, `cabinet-status`, `cabinet-tune`, `crew-roster`, `vault-bridge`) — ~⅓ the tokens in the auto-trigger scan, same triggering power.
- **New hooks layer** (`hooks/hooks.json`):
  - `SessionStart` — historical question, anniversary callback, per-project stats
  - `PreCompact` — saves anchor before context compaction clobbers it
  - `UserPromptSubmit` — silent character/running-joke pulse tracking
  - `Stop` — 1-in-5 banter-roll: promotes memorable lines to `crew/best-lines.md`
  - `SessionEnd` — marks interrupted sessions, emits farewell
  - `Notification` — rewrites generic "Claude needs input" in crew voice
- **New vault files:** `crew/scrapbook/questions.md`, `crew/best-lines.md`, `crew/pulse.json`.
- **`LICENSE`** (MIT) added.
- **`plugin.json`** gained `homepage`, `repository`, `license`, plus `obsidian` and `vault` keywords.

---

## [2.1.0] — 2026-04-12

### Added
- **Version Control Discipline protocol** (`protocols.md`) — new protocol section enforcing version parity across all version-bearing files. Defines canonical file list for both web projects and the Cabinet plugin itself. Jonasty owns enforcement, Bostrol owns CHANGELOG maintenance, Kevijntje validates version-to-scope alignment.
- **Version parity check in Pre-Gate QA** (`gate-protocol.md`) — added as a hard blocker alongside lint and type checks. All version-bearing files must agree before a gate passes.
- **Version parity step in Build Prep Gate** (`gate-protocol.md`) — dedicated step 2 in the build prep sequence. Blocks the gate on any drift.
- **Version drift as pushback trigger** (`protocols.md`) — added to pushback triggers table. Jonasty hard-blocks on version drift; Bostrol auto-writes missing CHANGELOG entries.
- **`scope.version` field in session anchor** (`session-anchor.md`) — tracks current project version. Read at resume to catch cross-session drift.
- **CHANGELOG verification in Build Prep documentation check** (`gate-protocol.md`) — Bostrol now explicitly verifies a dated CHANGELOG entry exists for the current version.
- **Git Gate Integration versioning rule** (`gate-protocol.md`) — explicit mandate that all version-bearing files must be updated in the same commit.

---

## [2.0.0] — 2026-03-28

### Added
- **`/dream` skill** — new Chroniclers-driven vault analysis. Bostrol hunts contradictions, Jonasty flags stale info, Kevijntje maps dangling scopes. Triggers after 5+ sessions, 14+ day gaps, or 3+ scope drifts. Output is in-chat only (ephemeral). Token-budgeted.
- **Vault chatter system** (`chatter-system.md`) — complete replacement of HTML chatter with Markdown files in `projects/{slug}/chatter/{YYYY-MM-DD}.md`. Organic event-driven frequency, horizontal-rule markers with emoji headers, simple `vault.append()` method. No HTML, no CSS, no python3 append scripts.
- **Vault templates** — new templates for `chatter.md`, `tasks.md`, `easter-eggs.md`, `preferences.md`, `lessons-learned.md`, `memories.md` in `examples/vault-templates/`.
- **"All Hands" pairing** (`dynamics.md`) — full 8-member war-room mode. Kevijntje facilitates, full-spectrum colour header.
- **Codebase scaffold** (`vault-bridge/SKILL.md`) — `create-project` now also creates `assets/`, `concepts/`, `previews/` directories in the codebase root with human-style READMEs.
- **Easter egg registry** — secret vault file at `crew/easter-eggs.md` with rules: rare during work, carte blanche at wrap-up.

### Changed
- **Chatter: HTML → Markdown** — all chatter output moved from `crew-notes/cabinet-chatter.html` to vault Markdown. Token cost reduced significantly. Wrap-up ceremony kept as HTML/Canvas/Three.js (sole exception).
- **Memories: HTML → Markdown** — `team-fun-memories.html` replaced by `crew/memories.md` in the vault. Plain Markdown entries with emoji type badges.
- **Lazy character loading** (`cabinet/SKILL.md`) — only Kevijntje and Poekie full YAMLs at boot. Other 6 load frontmatter only (~30 lines), full YAML on demand when activated.
- **Gates: big milestones only** (`gate-protocol.md`) — eliminated minor gates. Single pre-gate QA tier. Pseudocode decision tree for when to gate vs skip.
- **Bostrol's executive authority** (`protocols.md`) — Bostrol now writes documentation silently without approval gates. Chroniclers role shifted to vault auditing (`/dream`) and wrap-up sweeps.
- **Tone scaling reframed** (`protocols.md`) — vibes not percentages. "Let people be people." Metered personality identified as the worst outcome.
- **Character tech stacks** — Thieuke +Astro, Sakke flexible Node/Python/Go, Jonasty Playwright/REST, Pitr modern headless CMS, Henske +Framer Motion/GSAP/GLSL.
- **Vault-bridge bumped to 3.0.0** — 3-tier storage model (session state, persistent vault, codebase structure). `create` now scaffolds `crew/memories.md` and `crew/easter-eggs.md`.
- **Cabinet-resume bumped to 2.0.0** — all HTML references replaced with vault Markdown.
- **Session-anchor schema** — version bumped to 2.0.0. Removed HTML file references from file location docs.
- **Chatter-extended markers** — all HTML `<div>` markers replaced with Markdown horizontal rules + emoji italics. Recovery protocol rewritten for Markdown.
- **Memories-system** — entire HTML implementation section replaced with vault-native Markdown structure.
- **Cabinet-tune** — chatter frequency description updated from "HTML chatter log" to "vault chatter log".
- **README** — chatter description updated, `/dream` skill added to skills table.

### Removed
- HTML chatter generation (all files)
- HTML scrapbook / memories generation
- HTML-specific recovery protocols (closing marker checks, python3 append)
- Minor gate ceremonies
- CSS marker styling references
- Cadence-based chatter triggering (replaced by organic event-driven frequency)

---

## [1.9.0] — 2026-03-26

### Added
- **Chatter level selection at boot and resume** — Kevijntje now asks Tom how loud he wants the crew before each session (step 4.5 in `/cabinet`, step 7.5 in `/cabinet-resume`). Three options: Quiet (gates and alarms only), Normal (standard cadence), Full Noise (full banter + extra tangential cross-talk). Choice is informed by time of day, day of week, and vault context (last session temperature, days since last session). HTML chatter log remains always verbose regardless of setting. Response stored in `anchor.chatter.level`.
- **"The Chroniclers" super pairing** (`dynamics.md`) — Bostrol + Kevijntje + Jonasty formally named as a documentation power trio. Distinct from "The Ship" (release prep): The Chroniclers fire during and after work whenever something vault-documentable occurs. Three voices, one goal: nothing important leaves the session undocumented.
- **Vault Documentation Push protocol** (`protocols.md`) — full mechanics for The Chroniclers' aggressive push: what triggers it (decisions, API schemas, hard-won lessons, visual states, preferences, handoff points), how each member speaks, cadence rules to prevent spam, and a final wrap-up audit where Bostrol lists undocumented items before the session closes. Vault write ownership split: Bostrol writes narrative, Jonasty owns schema/spec blocks, Kevijntje confirms scope tagging.
- **CLI-First Policy** (`vault-integration.md`) — explicit principle: the Obsidian CLI is the unconditional preference for all vault operations when available, not just a transport option. Lists concrete reasons: native wikilink parsing, property writes without YAML re-parse, automatic link updates on move/rename, live graph queries, no fragile regex. Extends beyond vault ops — the crew favours canonical CLI tools across all domains.
- **`chatter.level` field in session anchor** — new enum field `"quiet"` | `"normal"` | `"full noise"` added to the `chatter` block. Write trigger 8a added (set at step 4.5 / step 7.5).
- **`vault-images.md` reference** — Playwright screenshot-to-vault pattern: capture viewport screenshots into `projects/{slug}/images/` and embed with `![[wikilinks]]` in session notes. Preserves visual state for cross-session handoffs. First used DutchBC PoC 2026-03-26.

### Changed
- `cabinet/SKILL.md` bumped to 1.9.0.
- `cabinet-resume/SKILL.md` bumped to 1.9.0.
- `session-anchor.md` schema version bumped to 1.9.0.
- Plugin version bumped to 1.9.0.

---

## [1.8.0] — 2026-03-25

### Added
- **Enriched wake-up chatter** — cold boot Step 4 completely overhauled. Time-of-day awareness (early bird, night owl, Friday, Monday), 12 scene seeds for structural variety, running joke pulls from character YAMLs, and an explicit banned-openers list to kill generic "coffee complaint" loops. Every boot should feel like walking into a different moment.
- **Enriched resume chatter** — cabinet-resume Step 7 now pulls from anchor state (active specialist, active task, time gap, last energy temperature) and running jokes. Replaces the static "Allez, terug aan de slag" script.

### Fixed
- **Vault abstraction consistency** — `protocols.md` preference capture and `gate-protocol.md` decision log both converted from `base_path + "/"` path concatenation to `vault.*()` abstraction calls with relative paths.
- **cabinet-status vault example** — example output line now matches the spec format (CLI mode, structured readout with loaded/session/last-write lines).
- **cabinet-resume anchor reset** — Step 8 counter resets corrected from flat field names (`chatter_count`, `break_count`) to proper nested schema paths (`chatter.message_count_approx`, `chatter.nudge_used`, `energy.break_count`, `energy.last_break`, `energy.session_start`).

### Changed
- **Member skills merged into `/invoke`** — 8 individual skills (`/bostrol`, `/thieuke`, etc.) consolidated into a single `/invoke {member}` skill with argument-based member resolution. All unique traits, acknowledgement styles, and consultation lists preserved in one file. Skill count reduced by 7.
- **`/cabinet-cheatsheet` removed** — redundant with reference files. All info lived authoritatively in `protocols.md`, `gate-protocol.md`, `dynamics.md`, `code-conventions.md`, and `chatter-system.md`. Removing eliminates a maintenance sync burden.
- **Chatter append timing** — `chatter-system.md` "When to Append" section rewritten from prose bullets to a single pseudocode decision tree (skip check → message count → cadence check).
- **Tone scaling** — `protocols.md` tone behaviour consolidated from separate table + 4 code-block examples into one compact table with inline examples.
- **Session momentum** — `protocols.md` momentum thresholds converted from prose bullets to pseudocode decision block.
- **Periodic question cross-reference** — `memories-system.md` cadence section now points to `gate-protocol.md § step 6` as the single source for firing logic (counter, energy skip, anchor updates). Fixed stale "step 5" reference.
- **Vault discovery Cowork fallback** — step 4 of the discovery chain now offers a `request_cowork_directory` picker in Cowork mode when no vault is found. Terminal mode remains silent. Can also bootstrap a new vault from templates.
- **Single-source-of-truth consolidation** — eliminated duplicated vault write logic between files:
  - Gate-completion writes: `gate-protocol.md` is authoritative; `vault-integration.md` now uses a `§` pointer.
  - Preference capture: `protocols.md` is authoritative; `vault-integration.md` now uses a `§` pointer.
  - Vault access methods: `vault-integration.md` is authoritative; `specialist-contract.md` now references it for method definitions.
  - Error handling: `specialist-contract.md` "never block" rule now explicitly references `vault-integration.md § "Graceful Degradation"` retry chain, resolving the apparent conflict.
- `cabinet/SKILL.md` version bumped to 1.8.0.
- `cabinet-status/SKILL.md` version bumped to 1.8.0.
- `session-anchor.md` schema version bumped to 1.8.0.
- Plugin version bumped to 1.8.0.

---

## [1.3.0] — 2026-03-23

### Added
- **Project-scoped vault layout (v2)** — vault structure redesigned from flat folders to `projects/{slug}/` subfolders containing `brief.md`, `decisions/`, and `sessions/`. Each project gets its own MOC (`decisions/_index.md`). Supports multi-project work without cross-contamination.
- **New vault-bridge commands** — `archive`, `unarchive`, `reindex`, `housekeeping`, and `migrate` (v1→v2). Vault-bridge SKILL.md rewritten from scratch (v2.0.0).
- **Obsidian setup reference** (`references/obsidian-setup.md`) — extracted from vault-bridge SKILL.md to keep skill lean. Covers core plugins, community plugins (Dataview queries updated for v2 paths), vault settings, hotkeys, first-time walkthrough.
- **Vault version tracking** — `vault.version` field added to session anchor schema. Values: `"2.0"` | `"1.0"` | `null`.
- **Auto-scaffold on write** — cabinet wrap-up and gate-protocol decision writes now ensure the project folder exists before writing, calling `create-project` if needed.
- **Same-day session append** — wrap-up session writes detect existing session files for the same day and append rather than overwrite.
- **Archived Projects section** in Home.md template.
- **Aliases in project briefs** — `aliases` frontmatter field ensures `[[project-slug]]` wikilinks resolve after file is nested as `brief.md`.

### Changed
- `vault-bridge/SKILL.md` rewritten — down from ~400 lines to ~180. Heavy specs moved to reference files.
- `cabinet/SKILL.md` wrap-up section — all vault writes now use project-scoped v2 paths. Home.md rebuilt via `update_home()` from disk state.
- `gate-protocol.md` decision writes — target `projects/{slug}/decisions/` with per-project MOC update.
- `specialist-contract.md` vault reads — brief path and decision grep updated to v2 project-scoped paths.
- `vault-integration.md` — full rewrite for v2 structure with path resolution functions, v1→v2 differences table, updated read/write triggers.
- `session-anchor.md` schema version bumped to 1.3.0.
- `cabinet/SKILL.md`, `cabinet-status/SKILL.md` bumped to 1.3.0.
- Plugin version bumped to 1.3.0.

### Fixed
- All remaining v1 vault paths (`/decisions/`, `/sessions/` at root, `/projects/{slug}.md`) replaced with v2 equivalents across entire plugin. Full grep scan confirmed zero v1 remnants.

---

## [1.2.0] — 2026-03-22

### Added
- **Vault awareness in specialist contract** — every agent now has baseline vault instructions: how to detect the vault from the anchor, when to read past decisions, how to check preferences before assuming defaults. Bostrol owns all writes; other specialists flag content for him.
- **Vault decision logging in gate protocol** — new step 5 explicitly triggers Bostrol to write non-trivial decisions to the vault after Tom approves a gate. Old step 5 (lore questions) is now step 6.
- **Preference detection protocol** — new section in `protocols.md`. Defines what counts as a preference, five categories (code style, tool choices, workflow, UX/design, communication), detection signals, capture flow with deduplication.
- **Expanded vault tracking in session anchor** — `vault` block now tracks: `decisions_written`, `preferences_captured`, `lessons_logged`, `last_write_at`, `preferences_loaded`, `lessons_loaded`. Three new anchor write triggers (9, 10, 11) for vault events.
- **Vault status in `/cabinet-status`** — Kevijntje's readout now includes vault connection state, what was loaded at boot, session write activity, and last write timestamp.
- **Vault chatter triggers** — `chatter-system.md` now lists vault activity as an elevated chatter event. Bostrol leads vault chatter ("Decision logged. [[auth-strategy]] — for next time."), crew reacts briefly.
- **Comprehensive Obsidian setup guide** in `/vault-bridge` — covers core plugins, community plugins (Dataview, Calendar, Kanban), appearance settings, hotkeys, first-time walkthrough, and a clear division of cabinet-owned vs. Tom-owned content.
- **Standardized vault discovery** in `vault-integration.md` — recommended default path (`~/vaults/cabinet/`), explicit Cowork vs. terminal scan paths, and a clear rule that discovery runs once at boot; specialists always read from the anchor.

### Changed
- `cabinet/SKILL.md` vault context injection now loads lessons-learned alongside brief and preferences, with explicit token budgets and anchor tracking.
- `cabinet/SKILL.md` wrap-up sequence expanded with explicit vault write steps (session summary, unrecorded decisions, MOC updates, lesson logging).
- `specialist-contract.md` anchor writes section updated to include vault writes as state-changing actions.
- `session-anchor.md` schema version bumped to 1.2.0.
- `cabinet-status/SKILL.md`, `cabinet/SKILL.md`, `vault-bridge/SKILL.md` bumped to 1.2.0.
- Plugin version bumped to 1.2.0.

### Fixed
- `session-anchor.md` referenced "step 5 in cabinet/SKILL.md" for initial anchor write — corrected to step 9.
- `specialist-contract.md` referenced gate-protocol.md step 6 for decision logging — corrected to step 5 (after renumbering).

---

## [1.0.0] — 2026-03-22

### Added
- **Vault integration** — persistent cross-session memory via Obsidian vault or external markdown folder. Supports dedicated vault, subfolder, and MCP modes. Wikilinks, YAML frontmatter, tag taxonomy (`#cabinet/...`), Dataview-compatible schemas.
- `/vault-bridge` skill — create, connect, status, and sync brief commands.
- Vault templates: `project-brief.md`, `decision.md`, `session-summary.md`, `home.md`.
- Wrap-up ceremony trigger in `cabinet/SKILL.md` core rules — detection, confirmation, vault sync, and ceremony delegation to `chatter-extended.md`.
- Dissent object schema in session anchor — `specialist`, `concern`, `raised_at`, `status`, `resolution`.
- Guest specialist example character file (`examples/guest-specialist-example.yaml`).
- Tone scaling decision tree in `protocols.md`.
- Colour accessibility guidance in `terminal-colours.md`.
- This changelog.

### Changed
- All 15 skills bumped to version 1.0.0.
- Character YAML colour values aligned to canonical ANSI RGB from `terminal-colours.md`.
- Build prep gate consolidated as a standalone section in `gate-protocol.md`.

### Fixed
- Stale class names in `cabinet/SKILL.md` message format (now Coast Mono: `.msg-content`, `.msg-name`, `.msg-time`, `.msg-text`).
- Ghost `avatars.json` reference removed (avatars are inline CSS circles).
- 5 remaining ASCII emoticon / `>_>` references replaced with deadpan emoji.
- `sed` vs `python3` append method conflict — all files now use python3.
- `.mcpb-cache/` excluded from plugin packaging.

---

## [0.9.1] — 2026-03-22

### Changed
- Token efficiency audit: boot reduced from ~30,500 to ~24,140 tokens (20% reduction).
- `chatter-system.md` split into core (~2,400 tokens at boot) and `chatter-extended.md` (~1,850 tokens deferred).
- `memories-system.md` moved to deferred loading (loaded at gate counter 3).
- 5 content duplications consolidated to single source of truth with cross-references.
- `session-anchor.md` field reference table replaced with key enums only.
- Environment detection and path discovery replaced with cross-references to canonical files.
- Covert golden rule centralized in `cabinet/SKILL.md`, other files reference it.

---

## [0.9.0] — 2026-03-21

### Added
- Coast Mono chatter template with CSS custom properties, dark/light mode toggle.
- Inline CSS avatar circles (28px, coloured, member initials) — no external dependencies.
- Semantic CSS classes: `.msg`, `.msg-content`, `.msg-name`, `.msg-time`, `.msg-text`.
- Marker pill badge format: `.marker.marker-gate`, `.marker.marker-mood`, etc.

### Changed
- Thieuke's emoticon system migrated from ASCII (`>_>`) to deadpan emoji (`😐`).

---

## [0.8.0] — 2026-03-20

### Added
- Initial release of the Cabinet of IMD Agents plugin.
- 8 specialist characters with full personality, expertise, colour, and relationship definitions.
- 14 skills: `/cabinet`, 8 specialist skills, `/crew-roster`, `/create-classmate`, `/cabinet-cheatsheet`, `/cabinet-status`, `/cabinet-tune`.
- Core reference system: dynamics, gate protocol, protocols, code conventions, chatter system, memories system, session anchor, terminal colours, specialist contract, superpowers integration.
- Covert file system: chatter log (HTML), memories scrapbook (HTML), session anchor (JSON).
- Gated handoff system with tiered QA.
- Scope management with parking lot.
- Energy and wellbeing monitoring.
