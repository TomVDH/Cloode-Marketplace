# GeminEye — Changelog

All notable changes to the `gemin-eye` plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  authorised (`scaffold X`, `full project review`, `write the X file`,
  `skip the gemin-eye folder`).
- Pairing rules for `vault-bridge` (auto-context, output routing,
  cross-linking from session notes) and `cabinet-of-imd` (Bostrol-mediated
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
