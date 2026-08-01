# Adjudant remise — design

**Date:** 2026-08-01 · **Target:** adjudant v0.27.0 · **Origin:** Tom's 2026-07-27 archive request, greenlit by the work machine's parked-work ruling (`docs/superpowers/specs/2026-07-31-adjudant-parked-work.md` §1), decisions closed with Tom 2026-08-01.

## Name

**`remise`** — French: putting away / the storeroom. Pairs with `ramasse` (pick up → put away) and leaves `archive` unambiguous: `projects/_archive/` remains the shelf zone for whole projects; remise moves files *within* a live project. Verb #12.

## Decisions (closed 2026-08-01, superseding where noted)

| Decision | Ruling |
|---|---|
| Promotion | **One atomic transaction**: preview carries moves + proposed MEMORY.md entries; apply lands both or aborts |
| Memory shape | Fixed heading starter set + escape hatch (unknown headings legal) |
| Threshold | `archive_after_days: 30` breadcrumb knob, `--days` flag override (`stale_after_days` precedent) |
| Epistemic promotion | Promoted entries carry `certainty` + `validity_context` from the analysis; MEMORY.md is timeless by construction |
| Surfacing | **check only** — SUPERSEDES the parked-work doc's check+sitrep+SessionStart nudge design; sitrep and SessionStart stay quiet |

## Non-negotiables (inherited from the parked-work ruling)

Shelf's transaction pattern, not tidy's: re-plan at apply, abort before any write, manifest backup. Containment checks, `atomic_write_text` + `file_lock`, zone-awareness from birth, every guard mutation-proven.

## Mechanics

### Eligibility (`remise.py`, stdlib-only)

- In scope: `sessions/`, `dreams/`, `notes/` (by `updated:`), and `tasks/` in terminal status (`done`, `icebox`) — untouched ≥ threshold. Dates via the F19-hardened readers (real calendar, bounded to today; frontmatter `updated:`/`date:` first, filename date next, mtime last).
- Never: `references/`, `releases/`, `decisions/`, `brief.md`, `_handoff.md`, `MEMORY.md`, `board/`, `bases/`, `canvases/`, any `_index*.md`, anything under `archived-context/` already.

### Preview (`remise.py preview`)

Writes `.adjudant-remise-preview/` in the project dir:
- `summary.md` — human-readable: what moves where, per-folder counts, reclaimed token estimate (reuses the cost estimator).
- `manifest.json` — the exact move list (src → `archived-context/{original relative path}`), threshold used, eligibility snapshot (per-file date evidence), and the SHA-256 of `memory-proposals.md`.
- `memory-proposals.md` — the promotion candidates: per outgoing cluster, a proposed MEMORY.md entry (`- {date} · {fact} — from [[archived-context/…]]`, with `certainty:`/`validity_context:` suggestions). The helper emits mechanical candidates (decision citations, repeated headings, task outcomes); Claude judges and rewrites them in conversation; **Tom can edit the file directly**. Apply ingests exactly this file.

### Apply (`remise.py apply`)

1. Re-plan: recompute eligibility fresh; any drift from `manifest.json` (file changed, vanished, new date) → **abort before any write**, naming the drift.
2. Hash gate: `memory-proposals.md` must match the manifest SHA **or** carry edits newer than the preview — then its current content is re-hashed into the manifest before proceeding (edits are the point; silent divergence is not).
3. Backup: manifest + proposals copied to `.adjudant-remise-backup/{timestamp}/` before the first move.
4. Transaction: under `file_lock`, move files to `archived-context/` (structure mirrored), append promotions to `MEMORY.md` under their headings, write/update `archived-context/_index.md` (what moved, when, from where), all via `atomic_write_text`. Any failure mid-sequence: recorded in the backup dir with a recovery note; nothing is deleted, moves are renames.
5. Session log line via the existing PostToolUse machinery (no new hooks).

### MEMORY.md

- New FIELD_SCHEMA type `memory`: required `{type, updated, tags}`; template `templates/memory.md`. Registered in template-coverage + template-schema-parity.
- `MEMORY_HEADINGS` starter set in `_vault_walk.py`: `## Decisions that held`, `## Preferences`, `## Gotchas`, `## Domain facts`. Unknown headings legal (escape hatch). Entries: `- {YYYY-MM-DD} · {fact} — from [[source]]`, optional trailing `(certainty {1-5}; {validity_context})`.
- Never archived, never staled: type `memory` is exempt in `detect_staleness` and `freshness_report` (timeless by construction), and remise's never-list includes it.

### Walker + validators

- `DEFAULT_SKIP` += `archived-context`, `.adjudant-remise-preview`, `.adjudant-remise-backup` (check/dream/ramasse/board/cost stop paying for archived volume — the point of the verb).
- Validators (mirroring tidy/shelf trios): **33** remise-preview-coherence, **34** remise-backup-integrity, **35** gitignore-includes-remise-dirs, **36** memory-headings parity (`MEMORY_HEADINGS` ↔ template ↔ reference doc). Existing 15 (verb-surface-parity) enforces the twelve-verb surfaces automatically.

### check section

`remise`: eligible count + oldest eligible date + last-remise date (from `archived-context/_index.md`), rendered as one line with the check-only nudge ("N files eligible → run /adjudant remise"). No sitrep/SessionStart surface.

### dream --folder (rider)

`dream.py --folder PATH` scopes the walk to one subtree, stated in the report header. Deliberate operator scoping, no inferred relevance (per the parked-work ruling's rejection of the four narrowing strategies).

## Testing

TDD throughout; RED per unit. Eligibility (scope, never-list, threshold, date precedence), preview shape (manifest, proposals hash, cost line), apply (drift abort, hash gate with edited proposals, backup, move+promotion atomicity, mid-sequence failure recovery note), MEMORY.md schema + exemptions, walker skips, validators 33-36 mutation-verified, dream --folder scoping. Estimated +45-60 tests on the 1104 base.

## Non-goals

- Un-remise (reverse mover): archived-context is greppable and manually restorable; a mover back is YAGNI until real demand.
- Any sitrep/SessionStart nudge (decided against, recorded above).
- Auto-run on cadence (remise is a deliberate ritual; cron-ability can ride the scheduled-agents tranche later if ever).
- Deleting `_port-test-hubspot` (Tom's manual call; not the verb's job).
