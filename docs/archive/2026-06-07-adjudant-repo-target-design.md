---
date: 2026-06-07
status: design — ready for implementation
scope: adjudant plugin — extend check/tidy/ramasse with a [vault|repo|all] target so adjudant cleans the code repo as well as the vault
plugin: adjudant
version-target: 0.6.0
related: 2026-05-26-adjudant-tidy-ramasse-log.design.md, 2026-05-26-adjudant-port.design.md
---

# Repo as a second cleanup target: tidy/ramasse/check the repo, not just the vault

## Problem statement

Adjudant's three-tier cleanup model (`tidy` = surface mechanical, `ramasse` = deep structural, `check` = read-only audit) only ever points at one thing: the **vault** side of a linked project. The **code repo** side accumulates its own structural drift, and nothing in adjudant addresses it.

This marketplace is the proof. Right now:

1. **Version drift** — `.claude-plugin/marketplace.json` lists `gemineye 0.3.1`, but `gemineye/.claude-plugin/plugin.json` says `0.3.2`.
2. **Symlink pattern adopted by only one plugin** — only `adjudant/` implements the Impeccable canonical-source + `.claude`/`.gemini`/`source` symlink topology. The other four have no harness replication.
3. **Missing per-plugin context files** — no plugin ships its own `AGENTS.md`/`CLAUDE.md`; only the repo root has them.
4. **Stale plans** — `docs/superpowers/` holds plan files with no completion marker, some 40+ days old.

`AGENTS.md` already names exactly this gap and defers it:

> "Hooks that need logic (not regex) — symlink-integrity, plan-age, version-drift, AGENTS/CLAUDE presence — are not in hookify; they'd need custom shell hooks, currently deferred."

The same risk gradient adjudant already encodes for the vault applies cleanly to the repo: a marketplace-version sync never breaks (`tidy`-tier); migrating a plugin into the symlink pattern is deliberate and can break (`ramasse`-tier); reporting drift touches nothing (`check`-tier). So the fix is not new philosophy — it is a second **target** for the philosophy that already exists.

## Goals

1. **One target argument, three existing verbs.** `check`, `tidy`, `ramasse` each take `[vault|repo|all]`. No new verb vocabulary; the locked three-tier model stays intact rather than fracturing into two parallel trios.
2. **Exact back-compat.** Default target is `vault`. `/adjudant tidy` with no argument behaves identically to today.
3. **Layered detectors.** A general repo-hygiene core runs on any connected repo; a marketplace-aware layer auto-activates only when `.claude-plugin/marketplace.json` is present.
4. **Same safety contract.** `tidy repo` is two-phase `preview → apply`, idempotent, `.legacy`-backed, never breaks. `ramasse repo` is analysis-only, then the superpowers chain under human supervision.
5. **Mirror existing modules, don't reinvent.** New helpers parallel `_vault_walk.py`, `ramasse_scan.py`, `tidy.py` one-for-one in structure, CLI shape, and JSON I/O contract.
6. **Dogfood.** The first real `tidy repo --apply` fixes the gemineye version drift in this repo's own `marketplace.json`.

## Non-goals

- **No `dream repo`.** The semantic/content tier stays vault-only and reserved (v0.4+). Confirmed out of scope.
- **No target on `connect`/`port`/`sync`/`draw`.** Those are project↔vault flows, not cleanup tiers.
- **No overlap with hookify or linting.** Hookify owns regex drift-defense (whitespace, secrets, deprecated tags). This is *structural* drift only — versions, symlinks, context-file presence, plan age, registration coherence.
- **No auto-adoption in `tidy`.** Creating the symlink pattern for a plugin that lacks it is structural and lives in `ramasse`. `tidy` only *repairs* a broken symlink where the pattern is already adopted.

## Surface

| Invocation | Tier | Behaviour |
|---|---|---|
| `/adjudant check [vault\|repo\|all]` | read-only | Audit. Reports repo drift alongside the vault snapshot. Never writes. |
| `/adjudant tidy [vault\|repo\|all]` | surface mechanical | Safe repo fixes. Two-phase `preview → apply`. Idempotent. |
| `/adjudant ramasse [vault\|repo\|all]` | deep structural | Repo restructuring via the superpowers chain. Sparing, supervised. |

Default target = `vault`. `argumentHint` for each becomes `[vault|repo|all]` (was `(no args)`).

**Path resolution.** Repo ops use `--project-dir` as the repo root directly (the breadcrumb's own location). Only vault ops follow the breadcrumb into the vault. No new resolution logic — the repo *is* the project dir.

## Tier behaviour on the repo

### `check repo` (read-only)
Renders, from `repo_scan.py` JSON: a version-coherence table (marketplace.json ↔ each plugin.json), a symlink-integrity matrix, an AGENTS/CLAUDE presence matrix per plugin, a stale-plan list, marketplace-registration gaps, and a single `drift_items` score. Writes nothing.

### `tidy repo` (surface mechanical — safe, two-phase)
Safe structured fixes only:
- **Version sync** — rewrite `marketplace.json` plugin versions to match each plugin's `plugin.json`.
- **Symlink repair** — recreate a broken/missing Impeccable symlink *where the canonical source exists and the pattern is already adopted*.
- **Structured normalization** — obvious, non-breaking field fixes surfaced by the scan.

Two-phase, mirroring `tidy.py`: `preview` writes `.adjudant-repo-tidy-preview/` (`changes.json`, `files/`, `summary.md`); `apply` backs live files up to `.adjudant-repo-tidy-backup/{ts}/*.legacy`, copies the preview into place, deletes the preview.

### `ramasse repo` (deep structural — sparing, supervised)
Deliberate, can-break work, gated behind the superpowers chain (`analyse → brainstorm → plan → review → execute`), exactly as `ramasse` vault does today:
- Migrate a plugin **into** the Impeccable pattern (canonical `skills/` + `.claude`/`.gemini`/`source` symlinks).
- Scaffold missing per-plugin `AGENTS.md`/`CLAUDE.md` (CLAUDE imports AGENTS).
- Archive stale plan files.
- Restructure plugin directories to convention.

Analysis phase is `repo_scan.py`; planning and execution run through superpowers, calling `repo_tidy.py` for any mechanical sub-steps.

## Layered detectors

**General core** (any connected repo):
- AGENTS/CLAUDE presence + `@AGENTS.md` import check
- Plan-file age / missing completion marker
- Doc-vs-code freshness signals

**Marketplace layer** (auto-activates when `.claude-plugin/marketplace.json` found — `repo_walk.is_marketplace_repo()`):
- plugin ↔ marketplace.json version coherence
- Impeccable symlink integrity
- registration coherence (every plugin dir registered, and every registered source path exists)

## New modules & files

All mirror an existing adjudant module one-for-one:

| New file | Mirrors | Role |
|---|---|---|
| `adjudant/scripts/repo_walk.py` | `_vault_walk.py` | Primitives: `walk_plugins(root)`, `parse_plugin_json`, `parse_marketplace_json`, `plugin_symlink_status`, `context_files_status`, `plan_file_ages`, `is_marketplace_repo`. |
| `adjudant/scripts/repo_scan.py` | `ramasse_scan.py` | `detect_*()` per drift class + `run_scan()` → JSON with cardinality-based `drift_items`. Feeds `check repo` and `ramasse repo` analysis. |
| `adjudant/scripts/repo_tidy.py` | `tidy.py` | `detect`/`preview`/`apply` phases for the safe fixes. |
| `adjudant/scripts/test_repo_walk.py` | `test__vault_walk.py` | Unit tests. |
| `adjudant/scripts/test_repo_scan.py` | `test_ramasse_scan.py` | Unit tests. |
| `adjudant/scripts/test_repo_tidy.py` | `test_tidy.py` | Unit tests (preview → apply, idempotency). |
| `adjudant/skills/adjudant/reference/repo-standards.md` | `reference/vault-standards.md` | NEW single source of truth for repo conventions (version coherence, Impeccable pattern, context-file requirement, plan-age policy, registration rule). |

**Edits:**
- `reference/check.md`, `reference/tidy.md`, `reference/ramasse.md` — add the `[target]` dimension and a repo section each.
- `scripts/command-metadata.json` — `argumentHint` → `[vault|repo|all]` for the three verbs; bump `version`.
- `skills/adjudant/SKILL.md` — verb-router table notes dual target; three-tier block notes target orthogonality; `argument-hint` frontmatter; bump `version`.
- `scripts/validate.py` — new validators (below).
- `.gitignore` — add `.adjudant-repo-tidy-preview/` and `.adjudant-repo-tidy-backup/`.

## I/O contract & drift scoring (unchanged)

Helpers emit structured JSON on **stdout** (Claude renders), diagnostics on **stderr**. `drift_items` is cardinality-based — distinct items summed, never frequency-weighted — identical to `ramasse_scan.py`. CLI shape mirrors the originals: `python3 repo_scan.py --project-dir PATH [--json]`; `python3 repo_tidy.py {detect|preview|apply} --project-dir PATH`.

## Validators (added to validate.py)

- **`repo-standards-coverage`** — `reference/repo-standards.md` exists and documents each detector category (mirrors `template-coverage`).
- **`repo-helper-parity`** — `repo_walk.py`, `repo_scan.py`, `repo_tidy.py` each exist with a matching `test_*.py`.
- **`repo-tidy-preview-coherence` / `repo-tidy-backup-integrity` / `gitignore-includes-repo-tidy-dirs`** — parallel to existing tidy validators #11–13 for the new preview/backup dirs.

Existing **`version-consistency`** (#10) already enforces the 0.6.0 bump across `plugin.json` / `command-metadata.json` / `SKILL.md` / `marketplace.json`.

## Versioning

Bump **0.5.2 → 0.6.0** (minor — additive feature) across all four version-bearing files, then add the marketplace registry row update. Commit style: `release(adjudant): v0.6.0 — repo as a second cleanup target (check/tidy/ramasse [vault|repo|all])`.

## Verification (end-to-end)

1. **Scan finds the known drift:**
   `python3 adjudant/scripts/repo_scan.py --project-dir . --json` → reports gemineye `0.3.1`≠`0.3.2`, the four un-migrated plugins, missing per-plugin context files, and stale plans; `drift_items` > 0.
2. **Tidy preview is non-destructive:**
   `python3 adjudant/scripts/repo_tidy.py preview --project-dir .` → writes `.adjudant-repo-tidy-preview/` with the gemineye version fix; live files untouched.
3. **Tidy apply + backup:**
   `python3 adjudant/scripts/repo_tidy.py apply --project-dir .` → `marketplace.json` now says gemineye `0.3.2`; original preserved as `.legacy` under `.adjudant-repo-tidy-backup/{ts}/`.
4. **Idempotent:** second `preview` reports zero changes.
5. **Verbs end-to-end:** `/adjudant check repo`, `/adjudant tidy repo`, `/adjudant ramasse repo` each load the right reference and dispatch the right helper.
6. **Tests green:** `python3 -m unittest discover -s adjudant/scripts -p 'test_repo_*.py'`.
7. **Validators green:** `python3 adjudant/scripts/validate.py` exits 0 with the new checks.
