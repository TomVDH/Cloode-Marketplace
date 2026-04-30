# Changelog

## 0.1.0 — 2026-04-30

Initial release. Extracted from `cabinet-of-imd` v2.2.0.

- Plugin scaffold with commands, skills, hooks, references, templates.
- Vault schema v3: type-shaped projects (`coding`, `knowledge`, `plugin`, `tinkerage`).
- `/vault-bridge` command: create, connect, link, create-project, add-collection, sync, status, archive, unarchive, reindex, housekeeping, migrate, set-type, templates, iterations, handoff.
- `/dream` command: Pass 1 (structural sanitation) + Pass 2 (content analysis).
- SessionStart hook with vault discovery and context injection.
- SessionEnd hook with optional remember handoff nudge.
- 13 vault templates.
- v2 → v3 migration command.
- Remember plugin integration (handoff sync).
