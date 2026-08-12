# Repository Guidelines

`toolshed` — personal Claude Code plugin marketplace by Tom Vanderheyden. Hosts multiple plugins; each plugin is self-contained in its own directory. (GitHub repo: `TomVDH/toolshed`, renamed from `onnozelaer-claude-marketplace`; GitHub redirects the old path.)

## Project Structure

```
.
├── .claude-plugin/
│   └── marketplace.json     # Marketplace manifest — source of truth for every plugin's version + description
├── adjudant/                # Vault editor/writer + project initializer, /adjudant with eleven verbs and a three-tier cleanup model (successor to the retired obsidian-bridge)
├── cabinet-of-imd/          # Crew/persona flavor layer (functionality sunset; character-only)
├── tui-toolbox/             # Operating language for agent-built helper CLIs (bash TUI + python helper); formerly cli-wrapper-helper
├── gemineye/                # Sandboxed Gemini second opinion via the agy CLI (SUNSET 2026-08-12: unlisted from marketplace, kept in tree)
├── iteration-shelf/         # Terminal-aesthetic in-browser design review boards (SUNSET 2026-08-12: unlisted from marketplace, kept in tree)
├── docs/                    # historical design docs, plans, and specs; archived material under docs/archive/
├── scripts/                 # repo-root tooling: bump_plugin_version.py, check_marketplace_versions.py + tests
├── .github/workflows/       # validate.yml: CI rerun of the local validators on push/PR
├── .gitignore               # ignores session-local .claude/ state and .superpowers/ working dirs
├── .pre-commit-config.yaml  # validators that fail the build on drift
├── README.md
└── AGENTS.md / CLAUDE.md    # this file + Claude overrides
```

## Adding a new plugin

1. Create `<plugin-name>/` at repo root with:
   - `.claude-plugin/plugin.json` — name, version, description, author, keywords
   - `commands/<plugin-name>.md` (if it has slash commands)
   - `skills/<skill-name>/SKILL.md` (if it has skills)
   - `hooks/hooks.json` + `hooks/scripts/` (if it has hooks)
   - `README.md`
2. Add an entry to `.claude-plugin/marketplace.json` with name, version, source path, description.
3. Bump marketplace version if needed.
4. Commit per the conventional-commits style below.

For plugins that follow the **Impeccable pattern** (one skill, one root command with sub-verbs):
- `<plugin>/skills/<plugin>/` is the real canonical directory (content lives here)
- `source/skills/<plugin>/`, `.claude/skills/<plugin>/`, and `.gemini/skills/<plugin>/` are all symlinks into it (`harness-parity` validator enforces they resolve to the canonical dir)
- `scripts/validate.py` enforces drift defense
- `scripts/command-metadata.json` is the single source of truth for verb metadata

`adjudant/` is the reference implementation of this pattern.

### Bumping a plugin version

A plugin's version is kept in lockstep across up to four files (`plugin.json`,
`scripts/command-metadata.json`, `SKILL.md` frontmatter, and the `marketplace.json`
entry). Don't edit them by hand — run `python3 scripts/bump_plugin_version.py <plugin>
<X.Y.Z>` to write all of them atomically (idempotent; enforced by the
`version-consistency` validator + `check_marketplace_versions.py`).

## Build & validate

No compile step. Symlinks propagate the canonical source to harness directories. Validators run via pre-commit (or manually).

```bash
# Install pre-commit hook (one-time per clone)
pre-commit install

# Run validators manually
pre-commit run --all-files

# Run adjudant's specific validators
python3 adjudant/scripts/validate.py
```

## Universal drift defense (via hookify)

Cross-machine, cross-project drift defense rules live in iCloud, NOT in this repo. Hookify reads them from each project's `.claude/` via symlinks.

| | |
|---|---|
| Canonical rules | `~/Library/Mobile Documents/com~apple~CloudDocs/Projects/IDE/claude/hookify/` |
| Install script | `~/Library/Mobile Documents/com~apple~CloudDocs/Projects/IDE/claude/install-hookify-rules.sh` |
| Install into a project | `cd /path/to/project && "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Projects/IDE/claude/install-hookify-rules.sh"` |

Current rules: `git-safety`, `destructive-bash`, `tom-voice`, `secret-scan`, `no-deprecated-tags`, `icloud-eviction-paths`, `path-quote`. Idempotent install; rules sync across machines via iCloud.

Hooks that need logic (not regex) — symlink-integrity, plan-age, version-drift, AGENTS/CLAUDE presence — are not in hookify; they'd need custom shell hooks, currently deferred.

## Cross-machine setup

This repo is mirrored across two machines. The OneDrive folder syncs the working tree; the `.git` store lives **inside** OneDrive (small enough that packfile-deadlock issues haven't surfaced — monitor and move out-of-tree if they do).

| Machine | macOS user |
|---|---|
| Personal | `tomlinson` |
| Work | `tomvanderhegden` |

Always `git pull --ff-only` before starting work; the other machine is often ahead. Branch is `main`; PRs not currently used (direct pushes from both machines).

## Commit conventions

Conventional Commits style. Match existing history:

```
feat(adjudant): shelf verb #11 wired into command-metadata, SKILL router, reference, parity surfaces
fix(gemineye): stop pinning model IDs the agy backend rejects
release(iteration-shelf): v0.1.1 - integration truth pass: adjudant persistence, standalone-skill attribution
chore(marketplace): bump adjudant to 0.14.0 in marketplace.json registry
docs(adjudant): migration guide from the retired obsidian-bridge verbs to /adjudant
```

- Scope is the plugin name (or `marketplace` for cross-plugin manifest changes).
- Version bumps use `release(<plugin>): vX.Y.Z - <summary>`.

## Naming

- Plugin slugs: kebab-case, no namespace prefix (`adjudant`, not `onnozelaer-adjudant`).
- Skill names inside a plugin: kebab-case.
- Command names: kebab-case after the `/`.

## What this repo does NOT contain

- No PR / branch workflow — work is pushed directly to `main` from either machine.
- No CI beyond a thin GitHub Action (`.github/workflows/validate.yml`) that reruns the local validators on push and PR; pre-commit remains the primary gate.
- No publish step beyond `git push origin main`. Claude Code's marketplace install pulls directly from the git remote.
