# Adjudant

Vault editor/writer and project initializer for Claude Code (and Gemini CLI). Successor to `obsidian-bridge`. One skill, one command, eleven verbs, Python helpers under each. Cost-gated heavy verbs, a shelf-driven project lifecycle across vault zones, a five-field connect contract, a locked voice layer, and a frontmatter schema lock (FIELD_SCHEMA: check detects drift, tidy strips/migrates after preview) round out the surface.

## Install

```
# in Claude Code
/plugin marketplace add TomVDH/onnozelaer-claude-marketplace
/plugin install adjudant
```

## Surface

| | |
|---|---|
| Command | `/adjudant {verb}` |
| Verbs | `connect`, `port`, `sync`, `check`, `sitrep`, `tidy`, `ramasse`, `dream`, `draw`, `board`, `shelf` |
| Skill | one (`adjudant`) — verbs dispatch internally via reference files |
| Hooks | ten entries across nine events (SessionStart, UserPromptSubmit, PreToolUse Write, PostToolUse Write\|Edit + Bash, PreCompact, PostCompact, TaskCreated, TaskCompleted, SessionEnd) |
| Templates | 20 file-type scaffolds + `board.html` (self-hosted kanban) |
| Python helpers | `_vault_walk.py` · `_handoff_freshness.py` · `_session_stamp.py` · `_cost.py` (primitives), `connect.py`, `port.py`, `sync.py`, `tidy.py`, `ramasse_scan.py`, `dream.py`, `board.py`, `board_bridge.py`, `graph.py`, `check.py`, `sitrep.py`, `shelf.py`; repo target: `repo_walk.py`, `repo_scan.py`, `repo_tidy.py` |
| Drift defense | `python3 scripts/validate.py`: 30 validators, runs via pre-commit |
| Tests | 1080 unit tests; `python3 -m unittest discover -p 'test_*.py'` |
| Context cost | `python3 scripts/token_budget.py`: per-surface token report, wired into `check repo` (report only, never fails a build) |

## The three-tier cleanup model (locked 2026-05-26)

```
tidy    = surface mechanical    (routine; tags, indexes, wikilink form, updated:)
ramasse = deep structural clean (sparing; folders, schema, file types, naming, renames)
dream   = content / knowledge / memory refresh  (semantic; staleness, contradictions, redundancy)
```

Risk tolerance is the dividing line: tidy never breaks anything; ramasse can break things deliberately under human supervision via the superpowers chain; dream is LLM-judgment-heavy semantic cleanup — `dream.py` emits a read-only comparator catalog, Claude judges, and a superpowers chain applies the refresh with backups for destructive content ops.

## Verbs

| Verb | Purpose | Helper |
|---|---|---|
| `/adjudant connect` | Onboard a code project to a vault. Rigid 5-step idempotent init. | `connect.py` |
| `/adjudant port` | Migrate a legacy project (raw / obsidian-bridge / hand-authored) to adjudant compliance. Two-phase preview → apply. | `port.py` |
| `/adjudant sync` | Push project state to the vault: refresh brief, mirror handoff, refresh project-row counts. | `sync.py` |
| `/adjudant check [vault\|repo\|all]` | Read-only summary — project + vault snapshot, schema compliance; `repo`/`all` also audit repo structure (versions, symlinks, registration, stale plans). | `check.py`, `repo_scan.py` |
| `/adjudant sitrep` | ELI5 orientation briefing — where we were, what's done, where the vault is, where to start. Read-only. | `sitrep.py` |
| `/adjudant tidy [vault\|repo\|all]` | Surface mechanical sweep — rebuild indexes, normalise tags, fix wikilink form, strip/migrate off-schema frontmatter. Two-phase preview → apply; `repo`/`all` also repair adopted-plugin harness symlinks. | `tidy.py`, `repo_tidy.py` |
| `/adjudant ramasse` | Deep structural clean — analysis phase via `ramasse_scan.py`, planning + execute via the superpowers chain. | `ramasse_scan.py` |
| `/adjudant dream` | Content/knowledge/memory refresh — semantic. Analysis via `dream.py` (read-only comparator catalog), judge + plan + execute via the superpowers chain, backups for destructive content ops. | `dream.py` |
| `/adjudant draw <canvas\|base\|diagram> <name\|type>` | Create visual artefacts — canvases, bases, mermaid diagrams (hand-authored or generated from vault data). | `graph.py` |
| `/adjudant board [scaffold\|serve\|status] [--project <slug>\|--all]` | Scaffold a self-hosted work-order kanban — drag-to-move, disk-persisted, seeded from `tasks/`. One project, a named one, or the whole vault. Re-seeds without clobbering dragged cards or custom columns; `status` prints terminal column counts. | `board.py` |
| `/adjudant shelf [<slug> <state>] [--reason "..."]` | Project lifecycle: status table across zones (list) and confirmed transitions (preview/apply): brief + status log + zone move + wikilink rewrite + index row. | `shelf.py` |

All helpers follow the breadcrumb: pass `--project-dir` (connect/port also accept it as an alias of their original `--project-root`) pointed at your **code project root** (where `.claude/adjudant` lives) and the helper auto-resolves to the vault project. Direct vault-project paths still work for backward compatibility.

## Architecture

- **Canonical skill location**: `skills/adjudant/` — single source of truth.
- **Harness copies**: `source/skills/adjudant/`, `.claude/skills/adjudant/`, `.gemini/skills/adjudant/` are symlinks. Edit the canonical, all harnesses see it. No build step.
- **Helper layer doctrine**: every verb touching >10 files gets a Python helper that pre-digests structured output Claude renders. Keeps per-verb context cost bounded regardless of project size.
- **Cross-machine portability**: the breadcrumb stores both `vault_path` (absolute, current machine) and `vault_name` (canonical). If the absolute path doesn't resolve on another machine, `vault_name` triggers a search of standard Obsidian locations under the current user's `$HOME`.
- **Validators**: `scripts/validate.py` enforces schema + version coherence on pre-commit.

## Vault standards

`skills/adjudant/reference/vault-standards.md` is the authoritative spec for tag taxonomy, frontmatter, folder structure, file-naming, and wikilink form. All vault writes conform.

## Ambient board

The kanban board maintains itself. It is born on the first real `tasks/*.md` note
(projects that never grow tasks never grow board files), reseeded when tasks
change (a Write or Edit under `tasks/`, and again at session end), and surfaced
without being asked: a SessionStart status line, a `check` board section, a
`sitrep` board line. Harness tasks left incomplete at session end are bridged
into `tasks/` notes by `board_bridge.py`, deduped by slug; reseeds never clobber
dragged cards or custom columns.

## Hooks

Ten hook entries across nine events, all vault-aware:

| Event | Script | Purpose |
|---|---|---|
| SessionStart | `hooks/scripts/session-start.sh` | Discover vault, detect AGENTS.md+CLAUDE.md, init/resume session note; stamp the Claude Code conversation UUID into `session_id:` (list, idempotent on resume); no resumed marker on `compact`/`clear` sources; nudges the model to replace the intent placeholder until it's filled; renders a board status line when a board exists, plus a suitcase pointer on `startup` when `suitcase-brief` is on PATH; echoes the handoff freshness banner (and a STALE warning) so a red handoff cannot sit unseen |
| UserPromptSubmit | `hooks/scripts/user-prompt-reminder.sh` | Smart-fire vault reminder when project isn't linked and prompt has vault-y keywords (at most once per session) |
| PreToolUse (Write) | `hooks/scripts/pretooluse-schema-gate.py` | Validates proposed frontmatter against `FIELD_SCHEMA` before a vault write lands; blocks (exit 2, stderr naming the expected shape) on a missing required field or a `type`/`node_type` conflict, allows unknown fields silently for `tidy` to strip later, fails open on anything infrastructural. Skips `brief.md`, session notes, `_legacy/`, and the `_`-prefixed system files; does not check status values. Write-only: an Edit payload carries no resulting file |
| PostToolUse (Write\|Edit) | `hooks/scripts/posttooluse-vault-log.py` | Append vault file creation entries to today's session log; stamp `source_session: <uuid>` only when the breadcrumb opts in via `stamp_source_session: true` (default off; skips session notes / `_handoff` / `_index*` / `_iteration`); matcher widened to `Write\|Edit` so a task-note change under `tasks/` nudges the board via `board_bridge.py --ensure-only` (log + stamp jobs stay Write-only) |
| PostToolUse (Bash) | `hooks/scripts/posttooluse-commit-log.py` | Self-gated commit logging (async; the `if: Bash(git commit *)` filter is defense in depth): append `- HH:MM · commit: {subject}` to today's session log; on `release(<plugin>): vX.Y.Z` subjects also scaffold `releases/v{X.Y.Z}.md` + an index row, never overwriting an existing note |
| PreCompact | `hooks/scripts/precompact.py` | Mechanical, no model calls (5s budget): append enriched pause tombstone with a `next:` pointer + mirror handoff with a freshness header (traffic light · age · NEXT · stale flag); a blank `.remember` source is never mirrored over a populated handoff |
| PostCompact | `hooks/scripts/postcompact.py` | Append `- HH:MM · compacted: {gist}` (single line, first 160 chars of the compaction summary) to today's session log; an empty or missing summary writes nothing |
| TaskCreated / TaskCompleted | `hooks/scripts/task-ledger.py` | One script wired to both events (async): append one JSONL entry per event to the TMPDIR session task ledger; zero vault writes in-session, the SessionEnd bridge replays survivors |
| SessionEnd | `hooks/scripts/sessionend.sh` | Append `session ended` marker only when something was logged since the last hook marker + sync handoff to vault; then bridge ledger survivors into `tasks/` notes and birth/reseed the board via `board_bridge.py` |

Universal drift-defense (git safety, voice checks, etc.) lives in `hookify` — not here.

## Pairing

Pairs with `gemineye` for Gemini-assisted review hand-off (see the Gemineye plugin).

## License

MIT
