# Obsidian Setup

Recommended Obsidian configuration for optimal vault experience with obsidian-bridge.

## Required

### Obsidian CLI

Install the Obsidian CLI (v1.12+) for full vault primitive support.

```bash
# Verify installation
obsidian version
```

If CLI is unavailable, bridge falls back to filesystem mode. All core operations work, but `move`/`rename` lose automatic link rewriting, and `backlinks`/`tags` degrade to grep-based approximations.

## Recommended Plugins

### Dataview

Enables dynamic queries across vault frontmatter. Useful for:
- Listing all decisions by status
- Filtering projects by type
- Iteration tracking dashboards

### Templater

For manual vault work outside of Claude sessions. Bridge's templates in `examples/vault-templates/` can be copied to the vault's `templates/` folder for use with Templater.

### Tag Wrangler

Helps manage the `#ob/*` structural tags and topical tags. Useful for renaming or merging tags across the vault.

## Vault Settings

### Files & Links

- **Default location for new notes:** `In the folder specified below` → root
- **New link format:** `Shortest path when possible`
- **Use [[Wikilinks]]:** ON (mandatory — bridge uses wikilinks exclusively)

### Appearance

No requirements. Bridge's frontmatter and content render correctly with any theme.

## Folder Structure

Bridge manages:
- `projects/` — active project folders
- `archive/` — archived projects
- `templates/` — vault templates (optional, for Templater)
- `Home.md` — auto-rebuilt vault home

Bridge leaves alone:
- `.obsidian/` — Obsidian's internal config
- `crew/` — cabinet-of-imd owned (if installed)
- Any root-level files not matching known types
