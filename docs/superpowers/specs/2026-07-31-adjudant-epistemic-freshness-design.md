# Adjudant epistemic freshness — design

**Date:** 2026-07-31 · **Target:** adjudant v0.22.0 · **Origin:** 2026-07-31 ecosystem scan (vault note `notes/2026-07-31-ecosystem-scan-harvest.md`) — per-fact truth-lifetime metadata was the #1 convergent idea across both the GitHub and web sweeps (memento-vault's epistemic frontmatter, agentcairn's validity model, eugeniughelbur's OKM freshness rule, open-second-brain's confidence bands).

## Problem

Vault notes carry no model of whether they are still true. The cleanup tiers infer decay from mtime and prose heuristics: dream's `detect_staleness` treats "old" as "suspect", which both misses stale-but-recently-touched facts and nags about timeless ones. Supersession exists (`superseded_by`) but nothing checks that the pointer resolves. The standard critique of markdown memory systems — no forgetting, no contradiction handling — lands squarely here.

## Goal

A minimal, schema-native truth-lifetime layer: optional frontmatter fields that declare how a fact ages, mechanical validation of those declarations, a read-only freshness report in `check`, and dream refinements that PREFER declared signals over heuristics. Human-legible, stdlib-only, additive.

## Non-goals (later tranches, from the same scan)

- obsidian-kanban-compatible board export, `.base` dashboards, Obsidian CLI detection (tranche 2)
- SessionStart standup, PreCompact save-guard, transcript-sweep backfill (tranche 3)
- Plan-hash-gated tidy/ramasse/dream applies (tranche 4)
- Board claim/lease + WIP limits (tranche 5)
- Auto-migration of existing notes: no existing note gains fields; everything is opt-in at write time.

## Approaches considered

- **A. Schema-only** — legalize the fields, no behavior. Rejected: fields nobody reads are decoration; the scan's point was feeding the tiers a decay signal.
- **B. Schema + validation + check section + dream refinement (recommended)** — fields become legal, malformed declarations are schema drift, `check` gains a freshness section, dream's staleness/supersession detectors consume the declarations. Small surface, immediate value, no new verbs.
- **C. Full stack** — B plus tidy auto-migrations, standup surfacing, per-fact `as of` body stamps with body-parsing lint. Rejected for v0.22.0: body-parsing lint is a different beast (prose, not frontmatter), and tidy writing semantic fields violates the tier contract (tidy is mechanical).

## Design

### 1. Schema (`_vault_walk.py`)

New optional fields on the four content types `decision`, `note`, `doc`, `source` (never on system shapes — session, handoff, index, task, release, iteration, dream-report):

| Field | Shape | Meaning |
|---|---|---|
| `freshness:` | enum `timeless \| dated \| pointer` | How this note ages: never / by date / lives elsewhere (OKM rule: every stored fact is one of the three) |
| `certainty:` | int 1–5 | Author's confidence at write time |
| `validity_context:` | free string | Conditions under which the note holds ("while using Redis 7.x cluster mode") |
| `valid_from:` | `YYYY-MM-DD` | Fact became true |
| `valid_until:` | `YYYY-MM-DD` | Fact expires (declared, not guessed) |

`FRESHNESS_VALUES: tuple = ("timeless", "dated", "pointer")` beside the status vocabularies. Names use underscores (repo convention: `source_session`, `superseded_by`). `superseded_by` already exists and completes the set.

### 2. Value validation (`_schema_drift_core`)

Presence is legal; malformed values are drift, mirroring `status_invalid`:

- `freshness` not in enum → drift
- `certainty` not an integer 1–5 (string digits accepted, "3.5"/"high"/list rejected) → drift
- `valid_from`/`valid_until` not real calendar `YYYY-MM-DD` → drift (reuse the strptime discipline from the F19 fixes)
- both present and `valid_from` > `valid_until` → drift

Report key: `epistemic_invalid: [{field, value, reason}]` (list — a note can have several). Fires through every existing consumer for free: check's drift section, tidy's preview, and the PreToolUse schema gate, which means a bad declaration is refused before it lands.

### 3. Freshness report (`_vault_walk.freshness_report(files, today)` + check section)

Read-only semantics over VALID declarations (shape problems already covered by drift):

- **expired**: `valid_until` < today → `{file, valid_until, days_expired}`
- **dangling supersession**: `superseded_by` names a stem that resolves to no file in the project → `{file, target}`
- **dated-unbounded**: `freshness: dated` but neither `valid_from` nor `valid_until` → `{file}` (declared to age, no clock attached)
- **counts**: adoption tally per field so `check` can show uptake

`check.py` gains a `freshness` section (helper + key in `run_check`), rendered per `reference/check.md`: one line when quiet ("freshness: N declared, all current"), expired/dangling listed when present. Sitrep untouched (its cost budget is tight; the check sibling owns audits).

### 4. Dream refinement (`dream.py`)

Declared signals outrank heuristics; heuristics remain the fallback:

- `detect_staleness`: a note with `freshness: timeless` is exempt from mtime-based staleness; a note with expired `valid_until` becomes a staleness candidate with `reason: "declared validity expired"` regardless of mtime.
- `detect_supersession_signals`: notes whose `superseded_by` dangles join the catalog (currently prose-signal only).

No new category — the two existing categories get sharper, which keeps the dream-report schema stable.

### 5. Vocabulary lock + validator (#31)

`vault-standards.md` gains **section 10: Epistemic freshness (locked 2026-07-31)** — the field table, the timeless/dated/pointer rule, and the sentence "declared signals outrank heuristics in every tier." New validator `freshness-vocabulary` (#31) enforces `FRESHNESS_VALUES` parity between `_vault_walk.py` and section 10, mirroring the status-vocabulary validators. Templates deliberately untouched (token discipline; optional fields don't belong in scaffolds) — template-schema-parity stays green by construction since the schema only widened.

### 6. Docs

`reference/check.md` (freshness section render), `reference/internals.md` (schema table row), `reference/dream.md` (declared-signal precedence note), vault-standards section 10.

## Testing

TDD throughout: RED per unit before implementation. Schema drift cases (each malformed shape + valid pass-through), freshness_report cases (expired / dangling / dated-unbounded / clean), dream precedence cases (timeless exemption, declared expiry beats fresh mtime), validator parity case (vocabulary mismatch fails). Estimated +25–35 tests on the 1008 base.

## Migration

None. Fields are optional; zero existing notes change; the gate/tidy/check behavior for undeclared notes is byte-identical to v0.21.0.
