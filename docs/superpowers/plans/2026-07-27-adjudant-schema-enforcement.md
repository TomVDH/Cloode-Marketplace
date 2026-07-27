# Adjudant Schema Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (this run is sequential,
> single owner, one commit per task; no parallel lanes because Waves A and B both touch
> `_vault_walk.py`). Steps use checkbox (`- [ ]`) syntax for tracking. Spec:
> `docs/superpowers/specs/2026-07-27-adjudant-schema-enforcement-design.md`.

**Goal:** Frontmatter drift becomes detectable (FIELD_SCHEMA + check schema section), repairable
(tidy strip/migrate, preview-gated), and stops being fed (project: retired from every writer,
source_session stamping opt-in).

**Architecture:** One detector, two consumers: `schema_drift_for_file` lives in `_vault_walk.py`
beside the constants it reads; check reports what tidy repairs, byte-for-byte the same rule set.
Parse-error and untyped files remain ramasse territory. Template enum comments stay, held to the
code constants by validators (the 0.14.0 pattern).

**Tech Stack:** stdlib-only Python 3, unittest, repo validate.py validators.

## Global Constraints

- Version target: 0.16.0, bumped only in Task 10 via `python3 scripts/bump_plugin_version.py adjudant 0.16.0`.
- Suite green after every task: `python3 -m unittest discover -s adjudant/scripts -p "test_*.py"`
  (685 baseline) and `python3 adjudant/scripts/validate.py` (27 baseline).
- Voice: no banned lexicon, no em dashes in any file this plan touches; commit subjects use plain hyphens.
- Symlinked skill dirs (`.claude/skills/`, `.gemini/skills/`, `source/skills/`) are never edited directly.
- No YAML library; `_parse_minimal_yaml` semantics are the contract (column-0 keys, `#` lines skipped).

---

### Task 1: Cherry-pick hook test coverage

- [ ] `git cherry-pick b61c7d4` (origin/claude/brave-moore-618ab7): adds only
      `adjudant/scripts/test_posttooluse_vault_log.py` (18 tests, avoids `tasks/` paths, green
      against main's Job 0 addition).
- [ ] Suite: expect 685 + 18 = 703 OK.

### Task 2: FIELD_SCHEMA + status vocabularies

**Files:** `adjudant/scripts/_vault_walk.py` (constants after `BUCKET_A_TYPES_PLUS_HOME`),
`adjudant/scripts/test__vault_walk.py`.

- [ ] Failing tests: DECISION/TASK/ITERATION tuples exact; `STATUS_VALUES_FOR_TYPE` keys are
      {decision, task, project, iteration}; FIELD_SCHEMA covers every BUCKET_A_TYPE plus index and
      vault-home; `project` absent from every set; required and optional disjoint per type.
- [ ] Implement per the spec table. Commit:
      `feat(adjudant): FIELD_SCHEMA + status vocabularies - single source of truth in _vault_walk`

### Task 3: Retire project: from every writer

**Files:** 11 templates under `adjudant/skills/adjudant/templates/` (decision, session, note, doc,
handoff, task, release, source, iteration, dream-report, _index-collection);
`adjudant/scripts/connect.py` (~442, ~496); `adjudant/scripts/tidy.py` (`generate_index_content`);
`adjudant/scripts/board_bridge.py` (`_FALLBACK_TEMPLATE`); `adjudant/scripts/_handoff_freshness.py`
(`HANDOFF_FRONTMATTER_TEMPLATE`); `adjudant/hooks/scripts/precompact.py` (degraded template);
`adjudant/hooks/scripts/session-start.sh` (heredoc); `adjudant/hooks/scripts/posttooluse-commit-log.py`
(release fallback + `_index.md` scaffold); `adjudant/skills/adjudant/reference/vault-standards.md`
(sections naming the field).

- [ ] Failing tests first where assertions exist: flip `project:` presence assertions to absence in
      `test_commit_log.py`, `test_board_bridge.py`, plus any connect/sync/hook-shell fixtures found
      by `git grep -n 'project: \"\[\[' adjudant/`.
- [ ] Remove the line from all templates and all nine writer sites; `{slug}`-only `.replace` calls
      become no-ops, verify no writer breaks on placeholder checks.
- [ ] vault-standards.md: membership is the path; piped-wikilink exception re-anchored to
      `supersedes`; task frontmatter block and wikilink table updated.
- [ ] Suite green. Commit:
      `feat(adjudant): drop project: field - templates and every scaffold writer, path is the membership`

### Task 4: Validators 28 + 29, deferred joins the enum

**Files:** `adjudant/skills/adjudant/templates/decision.md` (enum comment),
`adjudant/skills/adjudant/reference/vault-standards.md` (new decision-vocabulary section),
`adjudant/scripts/validate.py`, `adjudant/scripts/test_validate.py`.

- [ ] Failing tests (pattern: `_PatchedTree`): validator 28 passes on the real tree, fails on a
      tampered enum comment and on vault-standards missing a value; validator 29 passes on the real
      tree, fails on a template with an alien key and on one missing a required key.
- [ ] decision.md comment becomes `# active | superseded | reversed | implemented | deferred`;
      vault-standards gains the five-value section with one-line meanings.
- [ ] Register both validators in `main()` and the module docstring; count line 27 -> 29.
- [ ] Suite green. Commit:
      `feat(adjudant): validators 28-29 - decision vocabulary parity + template-schema parity, deferred joins the enum`

### Task 5: schema_drift detector

**Files:** `adjudant/scripts/_vault_walk.py`, `adjudant/scripts/test__vault_walk.py`.

- [ ] Failing tests: clean decision passes; missing `date` flagged; `project:` flagged unknown;
      `node_type` beside `type` -> type_conflict; `metadata:` nested shape -> unknown `metadata`
      only; off-enum decision status flagged; task alias (`wip`) marked normalizable when the alias
      set is passed; session with `session_id: []` clean; parse-error and untyped files skipped
      (counted, not field-checked).
- [ ] Implement `schema_drift_for_file(vf, aliases=None)` and `schema_drift(files, aliases=None)`
      (counts + capped samples, `[:20]` convention).
- [ ] Suite green. Commit:
      `feat(adjudant): schema_drift detector - required/unknown/status/type-conflict per FIELD_SCHEMA`

### Task 6: check renders the schema section

**Files:** `adjudant/scripts/check.py`, `adjudant/scripts/test_check.py`,
`adjudant/skills/adjudant/reference/check.md`.

- [ ] Failing tests: `run_check` JSON carries `schema`; clean project reports zero flagged; seeded
      drift file counted with samples; output stays JSON-serializable.
- [ ] `run_check` gains the section (alias set via `from board import STATUS_TO_COLUMN`, the
      validator-26 import precedent); reference/check.md gains the render block plus a tidy nudge
      line above the closing next step.
- [ ] Suite green. Commit: `feat(adjudant): check renders the schema drift section`

### Task 7: tidy feature 5, strip + migrate

**Files:** `adjudant/scripts/tidy.py`, `adjudant/scripts/test_tidy.py`,
`adjudant/skills/adjudant/reference/tidy.md`, `adjudant/scripts/command-metadata.json` (tidy
description), `adjudant/skills/adjudant/SKILL.md` (router tidy line, same wording).

- [ ] Failing tests: `_drop_frontmatter_keys` on single-line, block-list, nested-map, quoted-colon
      values; `_rename_frontmatter_key`; preview proposes `project:` strip and `originSessionId`
      migration; `node_type` -> `type` rename when type absent, drop when both; required keys never
      dropped; parse-error and non-canonical files untouched; idempotent (second preview after
      apply proposes nothing); `.legacy` backup present after apply; handoff fixture does not
      re-add stripped keys via `preserved_frontmatter`.
- [ ] Implement feature 5 in `build_preview` + the two primitives modeled on `_rewrite_tags_block`;
      summary gains a Schema section; `updated:` bump rides feature 2.
- [ ] tidy.md documents the five features; metadata + SKILL router line updated in lockstep
      (validators 5 and 17 hold them).
- [ ] Suite green. Commit:
      `feat(adjudant): tidy phase 5 - strip unknown fields, migrate node_type and originSessionId, preview-gated`

### Task 8: stamp gate

**Files:** `adjudant/hooks/scripts/posttooluse-vault-log.py`, `adjudant/scripts/connect.py`
(`write_breadcrumb` preserve list), `adjudant/scripts/test_posttooluse_vault_log.py`,
`adjudant/scripts/test_connect.py`, `adjudant/skills/adjudant/SKILL.md` (hooks table),
`adjudant/skills/adjudant/reference/connect.md` (breadcrumb keys),
`adjudant/skills/adjudant/reference/vault-standards.md` (traceability note).

- [ ] Failing tests: `test_stamp_default_off`, `test_stamp_opt_in_true`,
      `test_stamp_garbage_value_off`; adapt the three cherry-picked stamping assertions to opt-in
      fixtures; connect preserve test (re-connect keeps `stamp_source_session: true`).
- [ ] Gate Job 2 on the hook's own `read_breadcrumb()` dict; truthy = `true|1|yes|on`
      case-insensitive; absent = off. Docstring updated. `_session_stamp.py` untouched.
- [ ] Docs: SKILL hooks-table PostToolUse row, connect.md key roster, vault-standards historic
      stamps stay legal.
- [ ] Suite green. Commit:
      `feat(adjudant): source_session stamping is breadcrumb opt-in - stamp_source_session, default off`

### Task 9: truth pass

**Files:** `adjudant/README.md`, `adjudant/.claude-plugin/plugin.json` (description only).

- [ ] README: 29 validators, new test count, check/tidy verb rows mention schema, hooks blurb says
      opt-in stamping. plugin.json description matches.
- [ ] Suite green. Commit: `docs(adjudant): v0.16.0 truth pass - README counts, validator list, schema surfaces`

### Task 10: release

- [ ] `python3 scripts/bump_plugin_version.py adjudant 0.16.0` (plugin.json, command-metadata,
      SKILL frontmatter, marketplace.json in lockstep; validator 10 holds it).
- [ ] `pre-commit run --all-files` green.
- [ ] End-to-end, read-only, against the live vault: `check.py --project-dir .` shows the schema
      section; tidy preview (no apply) lists strips/migrations; test apply on a scratch fixture
      only.
- [ ] Commit: `release(adjudant): v0.16.0 - frontmatter schema lock: FIELD_SCHEMA, check drift section, tidy strip phase, opt-in session stamps, project: retired`
- [ ] `chore(marketplace): adjudant description matches v0.16.0 - 29 validators, schema drift defense, opt-in stamps`
- [ ] `git push origin main`. Vault: session note + release record per the commit-log hook; parked
      questions (none expected) recorded if any.
