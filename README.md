# Onnozelaer Claude Marketplace

Personal collection of Claude Code plugins by Onnozelaer.

## Plugins

| Plugin | Version | Description |
|--------|---------|-------------|
| [cabinet-of-imd](./cabinet-of-imd) | 2.1.0 | The Cabinet of IMD Agents — 8 specialized web dev agents with vault-native Markdown chatter, lazy loading, gated handoffs, Obsidian integration, and /dream vault analysis. |

## Structure

```
├── .claude-plugin/
│   └── marketplace.json    # Marketplace manifest — lists all plugins with versions
├── cabinet-of-imd/         # Plugin: Cabinet of IMD Agents (v2.1.0, 9 skills)
│   ├── .claude-plugin/     # Plugin metadata (plugin.json)
│   ├── skills/             # 9 invocable skills
│   ├── references/         # Character definitions, protocols, conventions
│   ├── examples/           # Templates and samples
│   ├── CHANGELOG.md
│   └── README.md
└── README.md               # This file
```

## Adding a new plugin

1. Create a directory at the repo root with the plugin slug (e.g. `my-new-plugin/`).
2. Add a `.claude-plugin/plugin.json` inside it with name, version, description, and author.
3. Add skills under `my-new-plugin/skills/<skill-name>/SKILL.md`.
4. Register the plugin in `.claude-plugin/marketplace.json` under the `plugins` array.
