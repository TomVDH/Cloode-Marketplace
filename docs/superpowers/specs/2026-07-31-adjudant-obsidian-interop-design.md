# Adjudant Obsidian-native interop — design (tranche 2)

**Date:** 2026-07-31 · **Target:** adjudant v0.23.0 · **Origin:** ecosystem scan tranche 2 (`notes/2026-07-31-ecosystem-scan-harvest.md`): meet Obsidian where it is. Three features, one theme — the vault surfaces adjudant writes should render natively in the app the vault lives in.

## Problem

The board renders only in adjudant's own board.html; Obsidian users see a JSON file and an HTML blob. The vault has no database views over the schema adjudant enforces (and the community is migrating off Dataview onto core Bases, which adjudant ignores). And adjudant never tells the user how to open what it just made in the app they are already running.

## Non-goals

- Two-way live sync between board.html and the kanban file (one truth, bounded read-back only — see A).
- Dataview compatibility (legacy; Bases is core).
- Obsidian CLI command wrappers (subcommand surface is young; detection + URI affordance only).
- Editing/verb changes to draw (its hand-authoring reference already covers bases).

## A. obsidian-kanban-compatible board export

**Format** (de-facto standard, mgmeyers/obsidian-kanban): frontmatter `kanban-plugin: board`; lanes as `## {Lane Name}` in deck column order; cards as `- [ ] **{id}** {title}` (`- [x]` in the `done` lane); an optional `## Archive` section and a trailing `%% kanban:settings … %%` comment block are THE PLUGIN'S STATE.

**Files**: `board/kanban.md` beside `board-data.json` and `board.html`.

**Writer** (`render_kanban(deck)` + emission inside the existing deck lock):
- Deck is truth; lanes/cards regenerate from the deck every write.
- An existing file's `%% kanban:settings %%` block and `## Archive` section are preserved verbatim, byte-for-byte — the never-destroy-plugin-state rule from the scan. Unknown `%% … %%` blocks likewise.
- Atomic write via `atomic_write_text`, inside the same `file_lock(data_path)` critical section as the deck and html, so the three surfaces cannot diverge.

**Birth and upkeep** (mirrors board.html's template-hash pattern):
- Born explicitly: `board.py scaffold --kanban` (and `ensure_board` never births it).
- Refreshed ambiently: `ensure_board` and `scaffold_one` re-emit it whenever the file already exists.

**Read-back** (refresh-without-clobber, the merge_deck philosophy): when `kanban.md`'s mtime is newer than `board-data.json`'s, a reseed first reads card placement from the kanban file (`**id**` tokens under `## {lane}` headings, lane matched to column by name then id, case-insensitive) and applies it as drag state before the tasks/ merge runs. A card in an unknown lane keeps its deck column. Malformed/undecodable kanban file: skipped entirely, deck wins, never an error.

## B. `.base` dashboards

Four templates in `templates/bases/`, provisioned into `{project}/bases/` (already an auto-created, index-exempt folder):

| file | view |
|---|---|
| `dashboard-sessions.base` | sessions table, newest first |
| `dashboard-decisions.base` | decisions grouped by `status` |
| `dashboard-tasks.base` | task notes grouped by `status`, terminal lanes filtered out of the default view |
| `dashboard-freshness.base` | content notes with any epistemic field; columns `freshness`, `certainty`, `valid_until` (tranche 1's fields become filterable columns) |

- Syntax per the vendored `reference/content-bases.md` (filters/views/order YAML). Filters scope by `type` property + folder so a base dropped in `{project}/bases/` shows that project only; `{slug}` is templated at provision time.
- Provisioned by **connect** (new idempotent step: write-if-absent, never overwrite an edited base). Existing projects get them by re-running `/adjudant connect`, which is documented as idempotent.
- **Validator #32 (`base-dashboards`)**: each shipped template parses structurally (known top-level keys), and every bare property it references is a legal FIELD_SCHEMA field, `file.*` builtin, or declared `formula.*` — so a schema rename can never silently orphan a dashboard column. Mirror of template-schema-parity, regex-level (no YAML dependency, stdlib rule).

## C. Obsidian app affordance

- `_vault_walk.obsidian_cli_path()`: `shutil.which("obsidian")`, None-safe. Surfaced as one `environment` line in `check` (`obsidian-cli: present/absent`) — a capability probe, not a wrapper.
- After writing board surfaces, `board.py` prints an `obsidian://open?vault={vault_name}&file={vault-relative path}` URI for `kanban.md` (the URI scheme is stable public API and works with or without the CLI). Print-only; nothing auto-opens.

## Testing

TDD throughout. A: render shape (lanes order, checkbox mapping, id bolding), settings/archive/unknown-block preservation byte-for-byte, read-back precedence + mtime gate + malformed-file skip, three-surface lock coherence. B: provisioning idempotence (absent→written, present→untouched), template structural validity, validator 32 catches a bogus property (mutation-verified). C: probe behavior with and without a fake `obsidian` on PATH; URI correctness for a zoned project path. Estimated +30-40 tests on the 1024 base.

## Migration

None. No existing file changes shape; kanban.md exists only where explicitly born; bases only write-if-absent.
