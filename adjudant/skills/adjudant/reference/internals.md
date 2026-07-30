# Adjudant internals

How adjudant itself is built: the hook wiring, the verb-to-helper map, and the
environment probes. Load this when the question is about adjudant's own
machinery. Running a verb does not need it - `SKILL.md` routes, and the verb's
own reference file describes the job.

## Environment awareness

`reference/suitcase.md` holds the standing summary of Tom's suitcase/cockpit
terminal environment and the ground rules for sessions that touch it (vault
writes via adjudant, `snap` before suitcase edits, `agent-bus protocol` for the
contract). Detection is a PATH probe for `suitcase-brief`; the SessionStart
hook points to it on fresh starts, `check` reports presence, `sitrep` renders
one line. Load the reference only when suitcase territory comes up.

## Python helper layer

Every file-touching verb is backed by a Python helper. Helpers follow the `.claude/adjudant` breadcrumb automatically — pass `--project-dir` pointed at the code project root and the helper auto-resolves to the vault project. Cross-machine portable via `vault_name` fallback resolution.

| Verb | Helper | Output |
|---|---|---|
| `connect` | `connect.py` | idempotent project init (5 steps + projects-index row) |
| `port` | `port.py` | preview/apply with backup |
| `sync` | `sync.py` | brief refresh + handoff mirror + projects-index row refresh |
| `tidy` | `tidy.py` + `_vault_walk.py` | preview/apply with backup |
| `ramasse` | `ramasse_scan.py` + `_vault_walk.py` | JSON drift catalog (analysis phase); planning + execute via superpowers |
| `dream` | `dream.py` + `_vault_walk.py` | JSON content/staleness comparator catalog (analysis phase); judge + plan + execute via superpowers |
| `check` | `check.py` + `_vault_walk.py` | JSON status snapshot |
| `sitrep` | `sitrep.py` + `_vault_walk.py` | JSON orientation briefing (recent activity, NEXT, vault location + counts); Claude renders ELI5 |
| `board` | `board.py` + `_vault_walk.py` | scaffold per-project `board-data.json` + a self-contained `board.html`; resolves any project by slug (or `--all`) via `enumerate_projects`. Refresh-without-clobber: re-seeding from `tasks/` merges, preserving dragged columns (idempotent; `--force` rebuilds with a `.bak`). `status` prints per-column counts |
| `draw` | `graph.py` + `_vault_walk.py` | generated mermaid fences from vault data — `relations` (wikilink graph, node-capped), `board` (kanban snapshot), `tiers` (cleanup model). Read-only |
| `shelf` | `shelf.py` + `_vault_walk.py` | lifecycle list JSON across zones; two-phase transition (preview/apply with backup): brief status + status log + zone folder move + vault-wide wikilink prefix rewrite + `projects/_index.md` row refresh |

`_vault_walk.py` is the shared primitives module (frontmatter, wikilinks, tags, vault index, vault/project resolvers, schema constants). Read-only CLI smoke-test: `python3 _vault_walk.py --project-dir PATH [--vault-dir PATH]`.

## Hooks

This plugin registers 10 hook entries across 9 events (vault-aware only):

| Event | Script | Purpose |
|---|---|---|
| SessionStart | `hooks/scripts/session-start.sh` | Discover vault, detect AGENTS.md+CLAUDE.md, init/resume session note; stamp the Claude Code conversation UUID into `session_id:` (list, idempotent on resume); no resumed marker on `compact`/`clear` sources; nudges the model to replace the intent placeholder until it's filled; renders a board status line when a board exists, plus a suitcase pointer on `startup` when `suitcase-brief` is on PATH |
| UserPromptSubmit | `hooks/scripts/user-prompt-reminder.sh` | Smart-fire vault reminder when project isn't linked and prompt has vault-y keywords (at most once per session) |
| PreToolUse (Write) | `hooks/scripts/pretooluse-schema-gate.py` | Validates the proposed frontmatter of a Write landing under the resolved vault project against `FIELD_SCHEMA`, via the same detector `check` reports and `tidy` phase 5 repairs; blocks (exit 2, stderr naming the expected shape) on a missing required field or on both `type:` and `node_type:` being set, so the model corrects within the same turn; allows unknown fields silently, since a PreToolUse hook's stderr only reaches anyone on a non-zero exit and `tidy` strips them after the fact anyway; fails open on anything infrastructural (no breadcrumb, unresolvable vault, unparseable payload, import failure); skips `brief.md`, session notes, `_legacy/` at any depth, and the `_`-prefixed system files (`_handoff.md`, `_index.md`, `_iteration.md`). Does not check status values. Write-only: an Edit payload carries no resulting file to judge |
| PostToolUse (Write\|Edit) | `hooks/scripts/posttooluse-vault-log.py` | Append vault file creation entries to today's session log; stamp `source_session: <uuid>` into the new file's frontmatter only when the breadcrumb opts in via `stamp_source_session: true` (default off — the session log already records the mapping; skips session notes / `_handoff` / `_index*` / `_iteration`); matcher widened to `Write\|Edit` so a task-note change under `tasks/` nudges the board via `board_bridge.py --ensure-only` (log + stamp jobs stay Write-only) |
| PostToolUse (Bash) | `hooks/scripts/posttooluse-commit-log.py` | Self-gated commit logging (async; the `if: Bash(git commit *)` filter is defense in depth): append `- HH:MM · commit: {subject}` to today's session log; on `release(<plugin>): vX.Y.Z` subjects also scaffold `releases/v{X.Y.Z}.md` + an index row, never overwriting an existing note |
| PreCompact | `hooks/scripts/precompact.py` | Mechanical, no model calls (5s budget): append enriched pause tombstone (`· next: …`) + mirror handoff with a freshness header (traffic light · age · NEXT · stale flag); a blank `.remember` source is never mirrored over a populated handoff |
| PostCompact | `hooks/scripts/postcompact.py` | Append `- HH:MM · compacted: {gist}` (single line, first 160 chars of the compaction summary) to today's session log; an empty or missing summary writes nothing |
| TaskCreated / TaskCompleted | `hooks/scripts/task-ledger.py` | One script wired to both events (async): append one JSONL entry per event to the TMPDIR session task ledger; zero vault writes in-session, the SessionEnd bridge replays survivors |
| SessionEnd | `hooks/scripts/sessionend.sh` | Append `session ended` marker only when something was logged since the last hook marker + sync handoff to vault; then bridge ledger survivors into `tasks/` notes and birth/reseed the board via `board_bridge.py` |

Universal drift-defense hooks (git safety, voice checks, etc.) live in hookify, not here.
