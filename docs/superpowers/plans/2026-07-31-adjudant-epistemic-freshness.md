# Adjudant epistemic freshness — implementation plan

Spec: `docs/superpowers/specs/2026-07-31-adjudant-epistemic-freshness-design.md`. TDD per task: RED → verify fails → GREEN → full module green. Full suite + 31 validators at the end.

## Task 1 — schema + value validation

- [x] RED: `test__vault_walk.py` — five fields legal on decision/note/doc/source, illegal on session/task/release; `epistemic_invalid` fired for bad freshness enum, non-1-5 certainty, malformed/impossible dates, `valid_from` > `valid_until`; valid declarations pass clean; PreToolUse gate path (`schema_drift_for_text`) refuses a bad declaration.
- [x] GREEN: `FRESHNESS_VALUES`, `_EPISTEMIC_OPTIONAL` set added to the four types' optional sets, `_validate_epistemic()` in `_schema_drift_core`.

## Task 2 — freshness_report + check section

- [x] RED: `test__vault_walk.py` — expired, dangling supersession, dated-unbounded, adoption counts, clean vault. `test_check.py` — `freshness` key present in run_check output.
- [x] GREEN: `freshness_report(files, today)` in `_vault_walk.py`; `_freshness_status()` helper + key in `check.py`; render contract in `reference/check.md`.

## Task 3 — dream refinement

- [x] RED: `test_dream.py` — timeless note exempt from mtime staleness; expired `valid_until` is a staleness candidate despite fresh mtime with reason "declared validity expired"; dangling `superseded_by` joins supersession signals.
- [x] GREEN: precedence edits in `detect_staleness` + `detect_supersession_signals`.

## Task 4 — vocabulary lock, validator 31, docs

- [x] RED: `validate.py` self-test path — freshness-vocabulary validator fails when section 10 and `FRESHNESS_VALUES` diverge (verify by deliberate mismatch, then fix).
- [x] GREEN: vault-standards section 10 (locked 2026-07-31); validator #31 `freshness-vocabulary`; docstring count 30→31; `reference/internals.md` + `reference/dream.md` touches.

## Close

- [x] Full suite green (expect ~1035-1045), 31 validators green, version-parity PASS.
- [x] Release v0.22.0: bump script, description gains the epistemic layer clause, push.
- [x] Vault release record + handoff NEXT update.
