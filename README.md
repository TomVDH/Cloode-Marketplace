# Onnozelaer Claude Marketplace

Personal collection of Claude Code plugins by Onnozelaer.

## Plugins

| Plugin | Version | Description |
|--------|---------|-------------|
| [adjudant](./adjudant) | 3.0.0 | Obsidian vault editor/writer and project initializer. One command, `/adjudant`, with six verbs (connect, status, clean, dream, draw, board) — each backed by a Python helper. Two-tier cleanup model (clean, then dream), where clean rewrites and removes but never creates; vault-aware hooks, drift-defense validators. Successor to the retired `obsidian-bridge`. |
| [cabinet-of-imd](./cabinet-of-imd) | 3.0.1 | The Cabinet of IMD Agents — a flavour layer for Claude Code. Eight college classmates with distinct personalities, voices, and disciplines serve as specialised web-development agents. Flavour-only (characters, voices, pairings, working disciplines); persistence is delegated to `adjudant` when active. |
| [iteration-shelf](./iteration-shelf) | 0.1.1 | Terminal-aesthetic review boards for in-browser design iteration — curated shelves and monster indexes with on-demand iframe loading, sidebar outliner, and browser-safety guards. Explicit invocation only. |
| [cli-wrapper-helper](./cli-wrapper-helper) | 2.0.1 | The shared operating language for agent-built helper CLIs — one visual + interaction + safety language across interactive bash TUIs and python helper scripts. Two skills: `bash-tui` and `python-helper`. |
| [gemineye](./gemineye) | 0.6.0 | A sandboxed second opinion from a Gemini-family model via the Antigravity CLI (`agy`) — review-only, read-trusted, write-sandboxed. Eight subcommands from quick `wip` checks to `megareview`. Pairs with `adjudant` for vault context. |

### Iteration Shelf — Skill & Suggested Command

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `iteration-shelf` | `/iteration-shelf` (explicit only) | Generates two review boards — a curated shelf and a monster index — from a JSON manifest. Terminal aesthetic, zero dependencies, on-demand iframe loading, warn-gate at 20+ loaded, sticky outliner sidebar with scrollspy. The Cabinet plugin, when active, adds flavour only; persistence is delegated to `adjudant`. |

**Layering**: the shelf chrome has its own hard-coded terminal aesthetic. The iterations it indexes are unconstrained — use any aesthetic freely on those.

### CLI Wrapper Helper — Skills & Commands

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `bash-tui` | bash script, shell tool, TUI, CLI menu, progress bar, spinner, splash screen, terminal polish | Pattern library for crafted bash CLIs. Mandatory checklist (strict mode, cleanup, semantic palette), copy-paste components (menus, tables, spinners, splash, transitions), multi-file architecture guide. |
| `python-helper` | python helper, read local data, query sqlite, python CLI, sqlite reader, csv reader, data reporter | Stdlib-only Python read-and-report scripts. `die()`, `section()`, `cell()` helpers, argparse, sqlite3, JSON/CSV patterns. Clean emoji-led output, `--json` mode for piping. |

| Command | What it scaffolds |
|---------|------------------|
| `/bash-new` | Full bash TUI script — palette, cleanup trap, splash, menu or linear flow |
| `/bash-component` | Single component — menu, spinner, loading bar, table, splash, or transition |
| `/py-new` | Python helper script — argparse, die/section/cell helpers, data source of choice |
| `/py-sqlite` | Python sqlite reader — named columns, truncated table, emoji readout |
| `/py-csv` | Python CSV reader — DictReader, filtering, optional aggregation |

### Gemineye — Skill

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `gemineye` | `/gemineye`, "ask Gemini", "second opinion", "Gemini review", "Gemini's take" | Calls the Antigravity CLI (`agy`) write-sandboxed and read-trusted to the project root, with a deliberately bundled context (Claude-prepared, project Markdown, vault context when `adjudant` is active). Eight verbs: review, megareview, wip, sanity, name, compare, save, harvest. Models are pinned per tier: fast verbs use `Gemini 3.5 Flash (Medium)`, `megareview` uses `Gemini 3.1 Pro (High)`. Review-only: Gemini proposes edits as code blocks and Claude applies them. Default mode is in-line; persistence routes Gemini outputs to `gemineye/` subfolders only, never into source. |

**Layering**: Gemineye is a partner, not a successor; Claude remains the architect. Pairs with `adjudant` to auto-load project context and route outputs into the project's vault folder.

## Structure

```
├── .claude-plugin/
│   └── marketplace.json    # Marketplace manifest — lists all plugins with versions
├── adjudant/               # Plugin: Adjudant (1 skill, six verbs, 5 hooks)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/adjudant/    # Canonical skill — SKILL.md + reference/ + templates/
│   ├── scripts/            # Python helpers (connect, status, clean, dream, …) + validate.py
│   ├── hooks/              # SessionStart, UserPromptSubmit, PostToolUse, PreCompact, SessionEnd
│   └── README.md
├── cabinet-of-imd/         # Plugin: Cabinet of IMD Agents (flavour-only)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/             # 1 invocable skill (crew-roster)
│   ├── commands/           # 1 slash command (/cabinet)
│   ├── references/         # Character definitions, dynamics, protocols, conventions
│   ├── CHANGELOG.md
│   └── README.md
├── iteration-shelf/        # Plugin: Iteration Shelf (1 skill)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/iteration-shelf/SKILL.md
│   ├── references/         # Design tokens, schemas, interaction spec
│   ├── templates/          # curated-shelf.html, monster-index.html
│   ├── examples/           # Sample iteration-shelf.json
│   ├── CHANGELOG.md
│   └── README.md
├── cli-wrapper-helper/     # Plugin: CLI Wrapper Helper (2 skills, 5 commands)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/bash-tui/    # Bash TUI skill — interactive terminal tools
│   ├── skills/python-helper/ # Python helper skill — read-and-report scripts
│   ├── commands/           # /bash-new, /bash-component, /py-new, /py-sqlite, /py-csv
│   ├── references/         # 9 files: architecture, bash-safety, components, data-cli, design-language, interaction, operations, palette, python-helpers
│   └── evals/              # Skill evaluation cases
├── gemineye/              # Plugin: Gemineye (1 skill)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/gemineye/SKILL.md
│   ├── references/         # invocation-patterns.md (prompt scaffolds, CLI usage)
│   ├── CHANGELOG.md
│   └── README.md
└── README.md               # This file
```

## Adding a new plugin

1. Create a directory at the repo root with the plugin slug (e.g. `my-new-plugin/`).
2. Add a `.claude-plugin/plugin.json` inside it with name, version, description, and author.
3. Add skills under `my-new-plugin/skills/<skill-name>/SKILL.md`.
4. Register the plugin in `.claude-plugin/marketplace.json` under the `plugins` array.
