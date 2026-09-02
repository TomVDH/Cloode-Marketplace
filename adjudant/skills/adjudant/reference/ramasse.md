# /adjudant ramasse

**Deep structural clean.** Used sparingly (quarterly, or after a major project shape change). Five-phase, superpowers-driven, human-in-the-loop.

*Ramasse* (French): pick up, gather, tidy — here the heavy kind.

## What ramasse does (vs tidy and dream)

```
tidy    = surface mechanical sweep (indexes, wikilink form, frontmatter). Routine.
ramasse = deep STRUCTURAL clean — folders, schema, file types, naming, renames,
          broken-wikilink triage, doc/decision mismatches. THIS verb.
dream   = content/knowledge/memory refresh (semantic). Separate verb.
```

Ramasse handles everything tidy refuses to auto-fix:
- File renames (UPPERCASE doc, decision missing date prefix) — paired with vault-wide wikilink rewrites
- `type:` field reassignments (`api-ref` → `doc`, `dream` → `dream-report`, etc.)
- Doc↔decision migrations (date-prefixed doc → move to decisions/; decision at root → move to decisions/)
- Folder restructures (e.g., `gemini/` → `references/`, or formalising `extra_folders`)
- Broken-wikilink triage (each link needs judgment — repoint, remove, or archive)
- Frontmatter drift cleanup (`: null` removal, missing required fields)
- Schema decisions (a recurring custom `type:` needs a template, or the files need retyping)

## The 5-phase shape (superpowers chain)

> **Cost pre-flight (locked).** Run the analyser with `--estimate-only` before the real scan. If `cost.warn` is true, stop and confirm with the user per the SKILL.md cost gate. When it warns, `--folder <path>` scopes the scan to one subtree (containment-checked; the estimate follows). The report then carries `scope` — **render it in the header** so a narrowed run never reads as a full one. A scoped run skips `folder_drift`: root shape is a whole-project question.

| Phase | Skill | Output |
|---|---|---|
| 1. Analyse | `ramasse_scan.py` + Claude | Full structural drift catalog (JSON → narrative) |
| 2. Brainstorm | `superpowers:brainstorming` | Explore restructure options with user |
| 3. Plan | `superpowers:writing-plans` | Concrete content arrangement plan (folder reshapes, file moves, schema changes) |
| 4. Review | (human checkpoint) | User reviews + approves plan; can edit |
| 5. Execute | `superpowers:executing-plans` | Apply with checkpoints; preview → apply pattern; calls `tidy.py` internally for mechanical bits |

## Phase 1 — Run the scanner

```bash
python3 "$(dirname "$0")/../../../scripts/ramasse_scan.py" \
  --project-dir "$PROJECT_ROOT" \
  --vault-dir "$VAULT_PATH" \
  --out /tmp/ramasse-scan-{slug}.json
```

JSON output covers: folder drift, index gaps, frontmatter drift, type drift, naming violations, wikilink form violations, broken wikilinks, doc/decision flags. Tag drift is not among them since v3: a `tags:` block is a field no template declares, so it surfaces as ordinary frontmatter drift.

Claude reads the JSON, renders a structural-state narrative for the user as input to
brainstorming. Shape (voice.md §Shape): the narrative leads with the largest
actionable drift item and ends with the single next step (proceed to phase 2, or stop).

## Phase 2 — Brainstorm

Invoke `superpowers:brainstorming` with the scanner output as context. Explore:
- Which drift items are real problems vs intentional (e.g., `extra_folders` declared in brief)?
- For type drift values (`api-ref`, etc.): write a template for the kind, or retype the files to a kind that has one?
- For naming violations: rename + wikilink rewrite, or accept?
- For broken wikilinks: triage by category (cross-project legacy refs vs genuine missing targets)?

Output: a shared understanding of what's worth restructuring.

## Phase 3 — Write the plan

Invoke `superpowers:writing-plans` to produce a concrete restructure plan:
- Specific files to rename + their new paths
- Schema additions (a new template for a new kind, `extra_folders` updates)
- Folder reshapes
- Broken-wikilink resolutions (per link: repoint to X, archive, or delete)
- Plus all the mechanical fixes (delegated to tidy)

Plan written under `iterations/{YYYY-MM-DD}-iter-{id}-ramasse/` per the adjudant iteration-folder convention.

## Phase 4 — Human review

User reviews the plan. May:
- Approve as-is
- Edit specific entries
- Reject and re-brainstorm
- Defer specific items (e.g., "rename docs to UPPERCASE in a separate session")

## Phase 5 — Execute

Invoke `superpowers:executing-plans` to apply with checkpoints. Each plan step is its own commit-able unit. For mechanical bits (index rebuilds, wikilink form, off-schema frontmatter), call `tidy.py preview` then `tidy.py apply` internally. For renames + structural changes, do the file moves directly + run a vault-wide wikilink rewrite pass after each.

A `.adjudant-ramasse-{ts}/` workspace dir holds the plan + checkpoint state. Backups for any destructive operation go to `.adjudant-ramasse-backup/{ts}/`.

## Inputs

Default: current project (resolved from breadcrumb). `--vault` invoking is not currently in scope — vault-wide ramasse means a deliberate per-project loop.

## Fail conditions

- No vault resolvable → exit non-zero
- ramasse_scan.py exits non-zero → halt before phase 2
- User aborts during phase 4 → leave `.adjudant-ramasse-{ts}/` for resume; no live changes
- Phase 5 partial failure → halt at last checkpoint, leave backup for rollback

## When NOT to use ramasse

- For routine tidy: use `/adjudant tidy`
- For semantic content cleanup (outdated decisions, redundant notes): use `/adjudant dream`
- For a single decision file rename: just rename it manually

## See also

- `reference/tidy.md` — surface mechanical sweep
- `reference/dream.md` — content/knowledge/memory refresh (semantic tier)
- `scripts/ramasse_scan.py` — phase 1 analyser
- `scripts/tidy.py` — phase 5 mechanical bits
- `docs/superpowers/2026-05-26-adjudant-tidy-ramasse-log.design.md` — design lock
