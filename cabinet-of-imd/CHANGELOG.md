# Changelog

All notable changes to the Cabinet of IMD plugin.

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
