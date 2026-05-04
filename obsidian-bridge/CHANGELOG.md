# Changelog

## 1.0.0 — 2026-05-04

First stable release. Major surface redesign + skill expansion.

**Breaking changes:**
- The `/vault-bridge` command is removed. Replaced by 6 opinionated top-level verbs: `/connect`, `/sync`, `/check`, `/draw`, `/ramasse`, `/iterate` (plus `/dream`, unchanged).
- The anchor file moved from `$CLAUDE_PROJECT_DIR/.obsidian-bridge` to `$CLAUDE_PROJECT_DIR/.claude/obsidian-bridge`. **Auto-migrated silently** by the SessionStart hook on first session — no user action required.

**New commands (6 verbs):**
- `/connect [path]` — onboard vault + project (replaces create / connect / link / create-project).
- `/sync` — push state to vault (combines sync + handoff sync).
- `/check [section]` — read-only summary; sections: iterations, decisions, sessions, handoff, tags.
- `/draw <subverb>` — visual artefacts; subverbs `canvas <name>`, `base <name>`, `diagram [type]` route to the canvas / bases / mermaid skills.
- `/ramasse` — tidy (combines reindex + housekeeping). French verb for "pick up / gather."
- `/iterate <id> <status>` — iteration state transitions. **May be sunset** in a future release if conversational handling proves robust.

**Conversational operations:**
Operations that lost their slash-command (add-collection, archive/unarchive, set-type, templates, add-iteration, add-iteration-artefact, iteration listing, schema migration) are now invoked conversationally. The `vault-bridge` skill body documents the trigger phrases and dispatches to existing pseudocode.

**New skills:**
- `obsidian-bridge:canvas` — JSON Canvas v1 reference (the `.canvas` file format).
- `obsidian-bridge:search` — Obsidian search query syntax (operators, property filters, regex, embedded `query` blocks).
- `obsidian-bridge:vault-standards` — promoted from a reference doc to an active skill that auto-loads when frontmatter is being written. Single source of truth for the schema.
- `obsidian-bridge:mermaid` — diagram syntax reference, plus a new `references/GENERATION_RULES.md` covering topology / labels / direction / styling discipline for *generating* diagrams.
- Imported four upstream skills from `kepano/obsidian-skills` (via antigravity-awesome-skills, MIT + CC BY 4.0): `bases`, `markdown`, `cli`, `clipper-template`. With schema-gate preambles deferring to `vault-standards` when in a bridge vault.

**New hook behaviours:**
- `SessionStart` step 0: silent auto-migration of legacy anchor + `.gitignore` rewrite.
- `UserPromptSubmit`: smart keyword-gated reminder (no longer fires on every turn when no vault is linked).
- `PostToolUse` (Write/Edit): validates vault-file frontmatter against `vault-standards`. Auto-bumps `updated:`, warns on missing `type:` / `ob/` tag / markdown-link-to-`.md`. Non-blocking.
- `PreCompact`: mirrors `.remember/remember.md` → vault `_handoff.md` before context compaction. Preserves human-edited content above a marker line.

**Other:**
- Migration guide at `notes/2026-05-04-command-surface-redesign-migration.md` maps every old command to its new equivalent.
- Plugin description rewritten to mention canvas / bases / mermaid know-how.
- README rewritten around the 7-verb surface.
- ATTRIBUTIONS.md credits upstream sources (kepano/obsidian-skills, antigravity-awesome-skills, Obsidian Help vault, JSON Canvas spec).

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
