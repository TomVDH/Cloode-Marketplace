# Adjudant Obsidian-native interop — implementation plan (tranche 2)

Spec: `docs/superpowers/specs/2026-07-31-adjudant-obsidian-interop-design.md`. TDD per task. Full suite + 32 validators at the close.

## Task 1 — kanban renderer + preservation

- [x] RED: `test_board.py` — render_kanban lane order/checkbox mapping/id bolding; settings + Archive + unknown `%% %%` blocks preserved byte-for-byte on rewrite; frontmatter key exact.
- [x] GREEN: `render_kanban(deck)`, `_split_kanban_preserved(text)`, emission in scaffold_one/ensure under the deck lock.

## Task 2 — birth flag + ambient refresh + read-back

- [x] RED: `--kanban` births the file; ensure refreshes only when present; kanban-newer-than-deck reseed applies lane placement as drag state; unknown lane keeps deck column; malformed file skipped.
- [x] GREEN: scaffold `--kanban` flag, `read_kanban_placement(path)`, mtime-gated apply inside ensure_board's reseed path.

## Task 3 — base dashboard templates + connect provisioning

- [x] RED: `test_connect.py` — provisioning writes four bases into `bases/` when absent, never overwrites an edited one, `{slug}` templated.
- [x] GREEN: `templates/bases/dashboard-{sessions,decisions,tasks,freshness}.base`, `provision_dashboards()` in connect.py wired into the idempotent step list.

## Task 4 — validator 32 + CLI probe + URI affordance

- [x] RED: validator 32 fails on a template referencing a non-schema property (mutation-verify); `obsidian_cli_path()` with/without fake binary; `check` environment line; board prints `obsidian://open` URI with vault name + vault-relative path.
- [x] GREEN: `validate_base_dashboards` (#32, docstring 31→32), `obsidian_cli_path()` in `_vault_walk`, check line, URI print after kanban write.

## Close

- [x] Full suite green, 32 validators, parity PASS.
- [x] Release v0.23.0: bump, description clause (kanban export, base dashboards), push.
- [x] Vault release record + handoff NEXT (tranche 3).
