---
date: 2026-07-27
status: design, locked (four decisions settled with Tom 2026-07-27)
scope: adjudant plugin, frontmatter schema lock - FIELD_SCHEMA constants, drift detection in check, tidy strip/migrate phase, opt-in session stamping, project field retirement
plugin: adjudant
version-target: 0.16.0
related: vault note projects/onnozelaer-claude-marketplace/notes/2026-07-27-adjudant-nesting-and-schema-handoff.md; 2026-07-16-adjudant-cost-status-voice-design.md (zones + project status, shipped as 0.14.0)
---

# Adjudant frontmatter schema lock: detect drift, repair it, stop feeding it

A full vault pass on hubspot-nightly (248 files, evidence in the handoff note above) found
frontmatter drift accumulating unopposed: 36 files carrying both `type:` and `node_type:`, 102 UUID
stamps across three key spellings, 181 `project:` fields that duplicate the file's path, and 12
distinct decision-status values against the 4 the template declares. Frontmatter is 4.0% of vault
bytes; this is a drift problem, not a size problem.

Two root causes, both structural:

1. **validate.py has never validated a vault file.** All 27 validators are plugin self-tests
   (harness parity, template coverage, metadata coherence). No check ever compares a real note to
   its schema, so nothing pushes back.
2. **The note-level vocabulary is unreadable by tools.** The decision-status enum lives in a YAML
   comment in `templates/decision.md`. Real and unenforceable.

The project-level vocabulary was fixed in 0.14.0 (`PROJECT_STATUS_VALUES`, zones, shelf, validator
23). This release does the same for note-level frontmatter.

## Settled decisions (Tom, 2026-07-27)

1. **Project nesting (handoff Part A) is closed.** The 0.14.0 zones design covers the goal:
   status `active | stale | seed` live in `projects/`, `fridge` in `projects/_fridge/`,
   `done | dead` in `projects/_archive/`, `find_project_dir` resolves breadcrumbs across zones,
   `shelf` relocates with wikilink rewrites. No `project_path:` breadcrumb key, no symlinks.
2. **Decision status gains a fifth value: `deferred`.** Vocabulary: `active | superseded |
   reversed | implemented | deferred`. A parked decision with intent to revisit is a real state
   (2026-05-29-mjml-deferred) and maps to nothing among the four. Wild values `accepted`, `locked`,
   `current` are synonyms of active and get remapped vault-side after release.
3. **`project:` is retired.** Membership is the path (`projects/[zone/]slug/...`). Every template
   and every scaffold writer drops the field; existing files get flagged as unknown-field drift and
   tidy offers the strip. The Obsidian graph backlink flows through the index.
4. **tidy repairs schema drift through the standard preview -> apply contract.** Itemized preview,
   `.legacy` backup, never silent. No auto-strip.

## Workstream 1: FIELD_SCHEMA, single source of truth

New constants in `_vault_walk.py` beside the existing schema block:

- `DECISION_STATUS_VALUES = ("active", "superseded", "reversed", "implemented", "deferred")`
- `TASK_STATUS_VALUES`, `ITERATION_STATUS_VALUES` (lifting the enums already declared as template
  comments), and `STATUS_VALUES_FOR_TYPE` mapping decision/task/project/iteration to their enums.
- `FIELD_SCHEMA`: per Bucket-A type, required and optional frontmatter key sets. Required must be
  present; required plus optional is the full legal set; any other key is an unknown field.

| type | required | optional |
|---|---|---|
| decision | type, status, date, tags | supersedes, source_session |
| session | type, date, started, session_id, tags | - |
| note | type, created, updated, tags | source_session |
| doc | type, title, updated, tags | source_session |
| handoff | type, updated, source, tags | created |
| task | type, status, tags | category, code, related, note, source_session |
| release | type, version, date, tags | source_session |
| source | type, title, tags | author, url, medium, year, source_session |
| iteration | type, identifier, status, date, tags | track, register, supersedes, builds_on, artefacts, source_session |
| dream-report | type, date, tags | source_session |
| project | type, project_type, slug, aliases, status, created, updated, tags | repo, stack, marketplace, extra_folders, relations, codename |
| index | type, tags | updated |
| vault-home | type, updated | - |

`project` is deliberately absent from every set: that is the cleanup. `source_session` stays legal
(optional) wherever the stamper could historically write it, so old stamps never read as drift.
Template enum comments stay in place; validators hold them to the constants (the 0.14.0 pattern).

## Workstream 2: detection (check)

- `schema_drift_for_file(vf)` / `schema_drift(files)` in `_vault_walk.py`: per parsed, canonically
  typed file report `missing_required`, `unknown_fields`, `status_invalid` (per
  `STATUS_VALUES_FOR_TYPE`; task aliases from `board.STATUS_TO_COLUMN` are accepted input and never
  flagged - the board normalizes lanes on read, and lanes like `next` have no canonical status
  equivalent), and `type_conflict` (`node_type` beside `type`; a `metadata:`-nested shape surfaces
  as unknown key `metadata`). Parse-error and untyped files stay ramasse territory
  (`detect_frontmatter_drift`, `detect_type_drift`); no duplication.
- `check` gains a schema section: counts plus capped samples, rendered per `reference/check.md`
  with a tidy nudge when drift exists. check's metadata description already promises "schema
  compliance"; this makes it true.
- Detection lives in check, not a validate.py vault mode: validate.py is pre-commit CI with no
  vault, check is the breadcrumb-resolved vault auditor (the 0.13.0 repo-target precedent).

## Workstream 3: repair (tidy feature 5)

- New tidy feature beside the existing four: strip unknown fields, migrate legacy keys, normalise
  decision-status aliases (`accepted`/`locked`/`current` to `active`; task aliases untouched).
  Migrations preserve provenance: `node_type` renames to `type` when `type` is absent, drops when
  both exist; `originSessionId` renames to `source_session` on the same rule.
- Two rewrite primitives modeled on `_rewrite_tags_block`: `_drop_frontmatter_keys` (consumes
  indented continuation lines, list and nested-map) and `_rename_frontmatter_key`.
- Flows through the existing preview -> apply pipeline untouched: `changes.json`, `files/`,
  summary section, `.adjudant-tidy-backup/{ts}` `.legacy` copies. Guards: never strip a required
  key, never touch files with parse errors or non-canonical types (wild `type: tasks` roadmaps are
  safe), `updated:` bumps ride the existing feature-2 rule.

## Workstream 4: stamp gate

`posttooluse-vault-log.py` Job 2 stamps `source_session: <uuid>` into every new vault file; the
session log (Job 1) already records the same mapping and no verb reads the per-file stamp. The
stamp becomes breadcrumb opt-in: `stamp_source_session: true` (accepted truthy spellings
`true | 1 | yes | on`) enables it, absent means off. `_session_stamp.py` is untouched; `connect`
preserves the key on re-connect like the existing `cost_warn_tokens` / `stale_after_days`
overrides. Historic stamps remain legal schema (optional field), so check never flags them.

## Enforcement and tests

- Validator 28 `decision-status-vocabulary`: code tuple, decision template enum comment, and the
  vault-standards vocabulary section agree on the five values.
- Validator 29 `template-schema-parity`: every registered template parses to a key set that covers
  its type's required set and stays inside required plus optional. Doubles as the permanent
  regression guard against `project:` re-entering a template.
- Cherry-pick `b61c7d4` (claude/brave-moore-618ab7) first: 18 house-style tests for the vault-log
  hook, written against main's Jobs 1-2, adapted to the gate in the same commit that flips the
  default. Unit coverage for every new primitive; suite green after every commit.

## Non-goals

No vault-side sweep in this release: the 17-file decision-status remap, the hubspot-nightly
`project:` strips, and the node_type migration run per project through the new check/tidy tooling
after release, preview-gated, each on its own evidence. No YAML library. No new verb. No changes
to zones, shelf, board merge semantics, or the symlinked skill dirs. No `--vault` mode on
validate.py.
