# Obsidian Bridge

Canonical Obsidian-vault layout, schema, primitives, and cleanup workflow for Claude Code.

Standalone plugin — works without any other plugins. Pairs cleanly with `cabinet-of-imd` when both are installed.

## What it does

- **Type-shaped projects** — `coding`, `knowledge`, `plugin`, `tinkerage` — each with appropriate brief blocks and subfolder defaults.
- **Vault primitives** — CLI-first Obsidian operations with filesystem fallback. Read, write, search, move, rename — abstracted behind `vault.*` calls.
- **SessionStart hook** — discovers vault, injects context, steers toward vault connection when not linked.
- **`/vault-bridge`** — create, connect, scaffold, sync, archive, reindex, housekeeping, iterations, migration.
- **`/dream`** — two-pass cleanup. Pass 1: structural sanitation (auto-fixable). Pass 2: content analysis (report-only).
- **Remember integration** — mirror `.remember/remember.md` to vault as `_handoff.md`.

## Commands

| Command | Description |
|---|---|
| `/vault-bridge` | Vault operations — create, connect, scaffold, sync, status, housekeeping, migrate |
| `/dream` | Two-pass vault analysis — structural fixes + content review |

## Install

Add to your Claude Code plugins or install from the Onnozelaer marketplace.

## Vault schema version

This plugin uses vault schema **v3**. Projects created with cabinet-of-imd v2 vaults can be migrated via `/vault-bridge migrate`.

## License

MIT
