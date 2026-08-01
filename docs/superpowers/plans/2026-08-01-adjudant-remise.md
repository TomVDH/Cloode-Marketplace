# Adjudant remise — implementation plan

Spec: `docs/superpowers/specs/2026-08-01-adjudant-remise-design.md`. TDD per task: RED → verify fails → GREEN → module green. Full suite + 36 validators at the close.

## Task 1 — schema + walker groundwork

- [ ] RED: FIELD_SCHEMA `memory` type (legal/illegal fields), `MEMORY_HEADINGS` constant, `detect_staleness` + `freshness_report` exempt type memory, `DEFAULT_SKIP` covers `archived-context` + remise preview/backup dirs, `templates/memory.md` registered in template-coverage.
- [ ] GREEN: `_vault_walk.py` constants + exemptions, `templates/memory.md`.

## Task 2 — eligibility + preview

- [ ] RED: `test_remise.py` — scope in/out per the never-list, threshold via knob + `--days` override, date precedence (updated: > filename > mtime, F19-bounded), preview dir shape (summary.md, manifest.json with proposals hash + evidence, memory-proposals.md with mechanical candidates + epistemic suggestions), cost line present, idempotent re-preview replaces cleanly.
- [ ] GREEN: `remise.py` (eligibility walk + preview writer), breadcrumb knob read.

## Task 3 — apply transaction

- [ ] RED: drift abort (file changed/vanished/new date → no writes, drift named), proposals hash gate (untouched passes; edited re-hashes and applies the EDITS; missing aborts), backup dir written before first move, moves mirror structure into `archived-context/`, promotions append under correct headings with dated sourced entries, `archived-context/_index.md` manifest rows, mid-sequence failure leaves recovery note + nothing deleted, all under file_lock via atomic_write_text.
- [ ] GREEN: `remise.py apply` per shelf's transaction pattern.

## Task 4 — surfaces + validators + rider

- [ ] RED: check `remise` section (eligible count, oldest date, last-remise, check-only nudge line); reference/remise.md + SKILL router row + command-metadata + README/marketplace verb surfaces (validator 15 goes green at twelve verbs); validators 33-36 mutation-verified; `dream --folder` scopes the walk and states it in the report header.
- [ ] GREEN: check.py section, docs, command-metadata.json, validators, dream.py flag.

## Close

- [ ] Full suite green (expect ~1150-1165), 36 validators, parity PASS.
- [ ] Release v0.27.0: bump, description gains remise + twelve-verb count, tag `adjudant--v0.27.0` (adopting the work machine's tag convention), push.
- [ ] Vault release record + handoff NEXT; run the first real remise preview on this project as the live smoke test (apply stays Tom's call).
