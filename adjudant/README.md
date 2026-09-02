# Adjudant

*Every unit has someone who keeps the records straight. Now your project does too.*

Run an Obsidian vault from inside your code project. Adjudant keeps a vault as your project's long-term memory: session notes, decisions, a handoff, and a kanban board, all written to a schema and kept current by background hooks. One command, `/adjudant`, with six verbs. Successor to `obsidian-bridge`.

**New here? Read the [walkthrough](GUIDE.md).** This page is the reference.

## Install

```
# in Claude Code
/plugin marketplace add TomVDH/toolshed
/plugin install adjudant
```

Then link your project once:

```
/adjudant connect
```

## The six verbs

| Verb | What it does |
|---|---|
| `/adjudant connect` | Link a project to its vault. Run once per project. |
| `/adjudant status [vault\|repo\|all]` | Make derived state current (brief date, handoff, project index row), then report in three bands: wrong now, going stale, worth a look. `--no-sync` for a read-only pass; `repo`/`all` also audit repo structure. |
| `/adjudant clean [vault\|repo\|all] [--deep]` | Cleanup: indexes, wikilinks, frontmatter. Preview then apply. It rewrites and removes; it never creates a vault file. `--deep` adds the structural pass. |
| `/adjudant dream` | Semantic refresh: flags stale, contradictory, or orphaned content for you to judge. |
| `/adjudant draw <canvas\|base\|diagram> <name>` | Create a canvas, base, or mermaid diagram. |
| `/adjudant board [scaffold\|serve\|status]` | Scaffold a self-hosted kanban seeded from your tasks. |

The two cleanup verbs form a ladder by risk:

```
clean        routine    surface mechanical, never breaks anything
clean --deep sparing    structural findings, reported for you to decide
dream        as needed  semantic, LLM-judged, you approve every change
```

## How it works

- **One breadcrumb.** `connect` writes `.claude/adjudant` in your code project, pointing at the vault. Every verb reads it, so you never pass paths by hand. It stores both an absolute path and the vault name, so it survives moving between machines.
- **Schema-locked writes.** Every note has a required frontmatter shape (`FIELD_SCHEMA`). A write that breaks it is blocked before it lands; `status` reports drift and `clean` repairs it.
- **Ambient by default.** Session notes, the handoff, and the board maintain themselves through background hooks. The board is born on your first task note and reseeds itself as tasks change. You rarely call these verbs directly.
- **Bounded cost.** Heavy verbs (`dream`, `clean --deep`, `status all`) estimate their context cost first and ask before pulling a large vault into the conversation.

## At a glance

| | |
|---|---|
| Command | `/adjudant <verb>` |
| Skill | one (`adjudant`); verbs dispatch to reference files on demand |
| Hooks | 11 entries across 10 events, all vault-aware |
| Templates | 16 file-type scaffolds + `board.html` |
| Helpers | stdlib-only Python, one per file-touching verb; no build step |
| Drift defense | `python3 scripts/validate.py` — 23 validators, run on pre-commit |
| Tests | 1213; `python3 -m unittest discover -p 'test_*.py'` |

Deep reference (hook wiring, the verb-to-helper map, cross-machine details) lives in [`skills/adjudant/reference/internals.md`](skills/adjudant/reference/internals.md). Vault rules (frontmatter, folders, naming) live in [`reference/vault-standards.md`](skills/adjudant/reference/vault-standards.md).

## Voice

Adjudant sets a direct, anti-slop register for the whole session and enforces it on every surface it writes. The full contract is in `reference/voice.md`. Turn it off per project with `voice: off` in `.claude/adjudant`, or per machine with `ADJUDANT_VOICE_DISABLE=1`.

## Pairing

- `hookify` — universal drift-defense hooks (git safety, secrets). Adjudant leaves those to it.
- `i-have-adhd` — soft dependency; shapes conversational output. Adjudant carries its own copy of the rules, so it isn't required.

## License

MIT
