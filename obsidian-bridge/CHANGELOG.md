# Changelog

## 1.1.1 — 2026-05-05

**Decouple bridge from cabinet specifics.**

Bridge can mention cabinet (interop is fine) but never expects it to be installed or accessible. This release scrubs the leakage points where bridge docs presumed cabinet's namespace, characters, or file conventions.

- `skills/vault-bridge/SKILL.md` — Default subfolder name when scaffolding a vault inside a non-empty dir is now neutral (`_vault/` suggested or ask the user). Was hardcoded `_cabinet/`.
- `skills/vault-standards/SKILL.md` — "Specialist Names (cabinet integration)" section replaced with "Specialist field (opaque to bridge)". No longer enumerates 8 cabinet-specific character names; bridge treats the field as opaque pass-through.
- `skills/dream/SKILL.md` — Removed cabinet specialist names from the chronicler-voice description and the auto-suggest mention. Now describes "companion plugin" behavior generically; cabinet is one possible companion.
- `references/vault-integration.md` — Cosmetic: example breadcrumb uses `MyVault`, not `Claude Cabinet`.
- `skills/mermaid/SKILL.md` — Cosmetic: removed "cabinet integration" from a Mermaid timeline example.

What still mentions cabinet (correctly framed as interop-tolerant, not required):
- Anchor chain step 2: `.cabinet-anchor-hint` fallback (gracefully absent)
- `Home.md` type accepts `vault-home | cabinet-home` (union, not requirement)
- "Cabinet detection — `crew/` folder present, untouched by bridge" (detect-and-yield, no dependency)
- Tag preservation: `cabinet/*` tags preserved alongside `ob/*` during migration
- README "pairs cleanly with cabinet-of-imd when both are installed"
- `# optional (cabinet)` annotations on optional fields (provenance hint, not requirement)

Non-breaking. No schema change. Existing vaults unaffected.

## 1.1.0 — 2026-05-04

**New optional schema field — `relations:` on project briefs.**

Encodes cross-project topology: `parents`, `children`, `related`, each a list of slug strings. Lets projects declare gating / spinoff / sibling relationships in frontmatter rather than ad-hoc in body text. Frontmatter takes slugs; body still uses wikilinks. Field is optional — existing briefs are unaffected.

- `vault-standards` — Brief frontmatter spec extended; note added on slug-vs-wikilink semantics.
- `vault-bridge` — housekeeping check #16 (relations referencing unknown slugs flagged as manual items).
- All four `brief-*` templates carry the field, initialised to empty lists.

Non-breaking. No migration required.

## 1.0.1 — 2026-05-04

Bug fix + content-style guide.

**Fix:**
- `hooks/hooks.json` — quoted `${CLAUDE_PLUGIN_ROOT}` in all 5 hook commands. Without quotes, hooks failed when the plugin path contained spaces (e.g. macOS installs under `~/Library/Application Support/...`). Symptom: `python3: can't open file '/Users/.../Library/Application'`.

**vault-standards skill expanded:**
- Doc schema clarified — explicit definition of what a doc IS (evergreen, singleton, no date in filename) plus common examples (`MANIFESTO.md`, `STACK.md`, `STYLE.md`, etc.).
- New "Doc vs Decision — disambiguation" subsection — criteria table, the "When was this decided?" test, and worked examples. `/dream` will flag suspected mismatches.
- New "Content style" section — voice/tense rules, structure rules, callout usage, words to delete, acceptance-test friendly principle, and reference body shapes per file type. Designed for both AI and human readers.

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
