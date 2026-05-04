# GeminEye — Changelog

All notable changes to the `gemin-eye` plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-05-01

Action-oriented restructure. Sandboxed by default. Rigid prompt template.

### Added
- `/gemin-eye` command with seven action-shaped subcommands:
  `review`, `megareview`, `wip`, `sanity`, `name`, `compare`, `save`.
- **Mandatory prompt template** — every Gemini call wraps the prompt
  in `ROLE / DO / DON'T / SCOPE — IN / SCOPE — OUT / OUTPUT / CONTEXT`.
  No exceptions. Filled-in per subcommand in `invocation-patterns.md`.
- **Sandbox by default** — every call passes `--sandbox`. Folder is
  not trusted. Gemini reviews only — never writes files. No `--yolo`.
- **Edit format** — proposed changes return as elaborate code blocks
  (`PROPOSED EDIT — file:line` + BEFORE/AFTER blocks + WHY). Claude
  reviews and applies.
- **Model split** — default `gemini-3.5-flash`; `megareview` switches
  to `gemini-3.5-pro` for the deeper pass.
- `megareview` subcommand — broad sweep across module / feature /
  plugin. Cross-file patterns, inconsistencies, architectural concerns.
- `wip` subcommand — review uncommitted changes + current branch diff.
  "Before you commit" framing.
- `compare` subcommand — head-to-head ranking of 2+ options with
  explicit criteria, comparison table, winner + runner-up condition.
- `save` subcommand — explicit persist trigger; in-line stays in-line
  until `save` runs.
- Override clause: `"drop the sandbox"` for the rare case Tom needs
  Gemini outside the sandbox (logged in frontmatter).

### Changed
- SKILL.md sharpened end-to-end. Tighter prose, imperative voice,
  table-led where prose was redundant. Operating-modes section
  collapsed — modes now correspond to subcommands.
- `references/invocation-patterns.md` rewritten — every prompt
  scaffold conforms to the rigid template. Loose prose prompts removed.
- `name` subcommand broadened — now works on a single thing or a
  related set with internal coherence.
- `compare` subcommand broadened — supports 2+ options, not just two.
- README rewritten around subcommands and sandbox/review-only defaults.
- Updated vault-bridge references — vault integration now lives in
  `obsidian-bridge` (post v2.3.0 cabinet refactor), not `cabinet-of-imd`.

### Removed
- Implicit "operating modes" abstraction (in-line / CLI / persisted) —
  replaced by explicit subcommands and `save`.
- Loose prose prompt scaffolds in `invocation-patterns.md` — every
  scaffold now uses the rigid template.

## [0.1.0] — 2026-04-28

Initial release.

### Added
- `gemin-eye` skill — invoke Gemini as a review and coding partner from
  inside Claude Code, with strict context-sourcing and output-routing
  rules.
- Three operating modes: in-line review (default), CLI review with file
  context, persisted review.
- Context-sourcing protocol prioritising Claude-prepared bundles, project
  Markdown, and Obsidian vault context (when `vault-bridge` is active).
- Output protocol routing all persisted Gemini reviews to `gemin-eye/`
  subfolders (vault project folder or `docs/gemin-eye/`), never into
  source paths.
- Override clauses for relaxing default containment when explicitly
  authorised.
- Pairing rules for `vault-bridge` and `cabinet-of-imd` (Bostrol-mediated
  indexing of Gemini reviews as documentation artefacts).
- `references/invocation-patterns.md` — reusable prompt scaffolds (code
  review, doc review, architecture sanity check, naming bikeshed, prompt
  review), CLI usage patterns, context-bundle assembly guidance, and
  anti-patterns.
- Pre-flight check for the `gemini` CLI on `PATH`.
- `README.md` with install + behaviour-at-a-glance summary.

### Dependencies
- `gemini` CLI — Google's official Gemini CLI must be on `PATH`.
- Optional: `vault-bridge` skill (from `cabinet-of-imd`) for vault
  integration.
- Optional: `cabinet-of-imd` plugin for Bostrol-mediated indexing.
