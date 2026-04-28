# Onnozelaer Claude Marketplace

Personal collection of Claude Code plugins by Onnozelaer.

## Plugins

| Plugin | Version | Description |
|--------|---------|-------------|
| [cabinet-of-imd](./cabinet-of-imd) | 2.2.0 | The Cabinet of IMD Agents — an 8-classmate crew of specialized web dev agents. Vault-required (Obsidian or any markdown folder) for chatter, decisions, sessions, and memories. Gated handoffs, lazy character loading, hooks-driven UI flair, and `/dream` vault analysis. |
| [taste-claude](./taste-package) | 0.1.0 | Premium frontend design skills — high-end typography, calibrated color, asymmetric layouts, motion choreography, and anti-generic UI standards across multiple aesthetic modes. |
| [iteration-shelf](./iteration-shelf) | 0.1.0 | Terminal-aesthetic review boards for in-browser design iteration — curated shelves and monster indexes with on-demand iframe loading, sidebar outliner, and browser-safety guards. Explicit invocation only. |
| [bash-tui-toolkit](./bash-tui-toolkit) | 0.1.0 | Build polished, interactive bash CLI tools with rich terminal UI — menus, tables, loading bars, spinners, splash screens, transitions, and animated effects. Makes shell scripts look crafted, not cobbled. |
| [gemin-eye](./gemin-eye) | 0.1.0 | Invoke Gemini as a review and coding partner from inside Claude Code. Vault-aware, context-disciplined, contained outputs — Gemini reviews land under `gemin-eye/` subfolders, never scattered across the codebase. |

### Taste Claude — Skills & Suggested Commands

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `design-taste-frontend` | Building new interfaces, UI components | Senior UI/UX engineer with tunable dials (variance, motion, density). Strict component architecture, CSS hardware acceleration, anti-slop patterns, Bento motion paradigms. |
| `high-end-visual-design` | Premium/agency-level design work | $150k agency directive. Three vibe archetypes (Ethereal Glass, Editorial Luxury, Soft Structuralism), double-bezel components, cinematic motion. |
| `minimalist-ui` | Clean, editorial interfaces | Warm monochrome, serif/sans pairing, flat bento grids, muted pastels. Notion-meets-Linear aesthetic. |
| `industrial-brutalist-ui` | Raw, mechanical interfaces | Swiss typographic print meets military terminal. Rigid grids, extreme type contrast, halftones, CRT scanlines, dithering. |
| `redesign-existing-projects` | Upgrading existing sites/apps | Audits current design, identifies generic AI patterns, applies targeted premium fixes without breaking functionality. |
| `stitch-design-taste` | Google Stitch screen generation | Generates DESIGN.md files optimized for Stitch's semantic design language. |
| `full-output-enforcement` | Preventing truncated output | Bans placeholder patterns (`// ...rest of code`), enforces complete generation, handles token-limit splits. Use alongside any design skill. |
| `find-skills` | Discovering new skills | Searches the open skills ecosystem via Skills CLI (`npx skills`). |

**Layering**: `design-taste-frontend` provides the engineering foundation. Layer an aesthetic skill on top (`high-end-visual-design`, `minimalist-ui`, or `industrial-brutalist-ui`) for a specific visual direction. Use `full-output-enforcement` with any of them to prevent truncation.

### Iteration Shelf — Skill & Suggested Command

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `iteration-shelf` | `/iteration-shelf` (explicit only) | Generates two review boards — a curated shelf and a monster index — from a JSON manifest. Terminal aesthetic, zero dependencies, on-demand iframe loading, warn-gate at 20+ loaded, sticky outliner sidebar with scrollspy. Pairs with `full-output-enforcement` for complete emission and with the Cabinet plugin when active (Bostrol owns shelf ops). |

**Layering**: the shelf chrome has its own hard-coded aesthetic and deliberately overrides `design-taste-frontend` / `high-end-visual-design` defaults. The iterations it indexes are unconstrained — use aesthetic skills freely on those.

### Bash TUI Toolkit — Skill

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `bash-tui-toolkit` | Building bash scripts, shell tools, CLI launchers, terminal utilities; mentions of "TUI", "CLI menu", "progress bar", "spinner", "splash screen", or polishing shell-script aesthetics | Pattern library for crafted-looking bash CLIs. Mandatory checklist (strict mode, cleanup, consistent palette/spacing/motion), copy-paste component implementations (menus, tables, loaders, spinners, splash screens, transitions), and architecture guidance for multi-file projects. |

### GeminEye — Skill

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `gemin-eye` | `/gemin-eye`, "ask Gemini", "second opinion", "Gemini review", "Gemini's take" | Calls the `gemini` CLI with a deliberately bundled context (Claude-prepared, project Markdown, vault context when `vault-bridge` is active). Default mode is in-line; persistence routes Gemini outputs to `gemin-eye/` subfolders only — never into source. Override clauses unlock scaffolding, full-repo reviews, or direct file writes when Tom explicitly asks. |

**Layering**: GeminEye is a partner, not a successor — Claude remains the architect. Pairs with `vault-bridge` to auto-load project context and route outputs into the project's vault folder; pairs with `cabinet-of-imd` so Bostrol indexes Gemini reviews as documentation artefacts.

## Structure

```
├── .claude-plugin/
│   └── marketplace.json    # Marketplace manifest — lists all plugins with versions
├── cabinet-of-imd/         # Plugin: Cabinet of IMD Agents (v2.2.0)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/             # 5 invocable skills (cabinet-resume, cabinet-status, cabinet-tune, crew-roster, vault-bridge)
│   ├── commands/           # 4 slash commands (/cabinet, /invoke, /dream, /create-classmate)
│   ├── hooks/              # SessionStart, PreCompact, UserPromptSubmit, Stop, SessionEnd, Notification
│   ├── references/         # Character definitions, protocols, conventions, vault integration
│   ├── examples/           # Templates and samples
│   ├── CHANGELOG.md
│   └── README.md
├── taste-package/          # Plugin: Taste Claude (v0.1.0, 8 skills)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── design-taste-frontend/
│   ├── high-end-visual-design/
│   ├── minimalist-ui/
│   ├── industrial-brutalist-ui/
│   ├── redesign-existing-projects/
│   ├── stitch-design-taste/
│   ├── full-output-enforcement/
│   ├── find-skills/
│   └── README.md
├── iteration-shelf/        # Plugin: Iteration Shelf (v0.1.0, 1 skill)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/iteration-shelf/SKILL.md
│   ├── references/         # Design tokens, schemas, interaction spec
│   ├── templates/          # curated-shelf.html, monster-index.html
│   ├── examples/           # Sample iteration-shelf.json
│   ├── CHANGELOG.md
│   └── README.md
├── bash-tui-toolkit/       # Plugin: Bash TUI Toolkit (v0.1.0, 1 skill)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/bash-tui-toolkit/SKILL.md
│   ├── references/         # components.md, palette.md, architecture.md
│   └── evals/              # Skill evaluation cases
├── gemin-eye/              # Plugin: GeminEye (v0.1.0, 1 skill)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/gemin-eye/SKILL.md
│   ├── references/         # invocation-patterns.md (prompt scaffolds, CLI usage)
│   └── README.md
└── README.md               # This file
```

## Adding a new plugin

1. Create a directory at the repo root with the plugin slug (e.g. `my-new-plugin/`).
2. Add a `.claude-plugin/plugin.json` inside it with name, version, description, and author.
3. Add skills under `my-new-plugin/skills/<skill-name>/SKILL.md`.
4. Register the plugin in `.claude-plugin/marketplace.json` under the `plugins` array.
