# Onnozelaer Claude Marketplace

Personal collection of Claude Code plugins by Tom Vanderheyden.

## Plugins

| Plugin | Version | Description |
|--------|---------|-------------|
| [cabinet-of-imd](./cabinet-of-imd) | 1.8.0 | The Cabinet of IMD Agents — a crew of 8 specialized web development agents with gated handoffs, scope management, and team dynamics. |
| [bash-tui-toolkit](./bash-tui-toolkit) | 1.0.0 | Skill for generating polished Bash TUI scripts with consistent component patterns, colour palettes, and architecture. |

## Structure

```
├── .claude-plugin/
│   └── marketplace.json    # Marketplace manifest — lists all plugins with versions
├── cabinet-of-imd/         # Plugin: Cabinet of IMD Agents (v1.8.0, 8 skills)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/             # 8 invocable skills
│   ├── references/         # Character definitions, protocols, conventions
│   ├── examples/           # Templates and samples
│   ├── CHANGELOG.md
│   └── README.md
├── bash-tui-toolkit/       # Plugin: Bash TUI Toolkit
│   ├── references/         # Architecture, components, palette
│   └── SKILL.md
├── bash-tui-toolkit-workspace/  # Eval workspace for bash-tui-toolkit
└── README.md               # This file
```

## Adding a new plugin

1. Create a directory at the repo root with the plugin slug (e.g. `my-new-plugin/`).
2. Add a `.claude-plugin/plugin.json` inside it with name, version, description, and author.
3. Add skills under `my-new-plugin/skills/<skill-name>/SKILL.md`.
4. Register the plugin in `.claude-plugin/marketplace.json` under the `plugins` array.
