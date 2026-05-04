# Obsidian Properties — authoritative spec

The vault-standards SKILL.md defines the **plugin's** schema (what keys we require per file type). This file points at Obsidian's **own** Properties spec — the rules every property in any Obsidian vault must follow regardless of plugin.

## Why this matters

The plugin's schema ADDS rules on top of Obsidian's. If the plugin says "tags: [ob/note]" but Obsidian's spec says tag values must lowercase with no spaces, both rules apply. When in doubt about the underlying mechanics (how Obsidian parses, validates, displays a property), defer to the spec below.

## Topic map

| Topic | Online | Local |
|---|---|---|
| Properties overview, supported types, list vs single, default types | <https://help.obsidian.md/properties> | `Editing and formatting/Properties.md` |
| Tags (parsing rules, characters allowed, nesting `parent/child`) | <https://help.obsidian.md/tags> | `Editing and formatting/Tags.md` |
| Aliases (how they enable bare `[[wikilink]]` resolution) | <https://help.obsidian.md/links/aliases> | `Linking notes and files/Aliases.md` |

## Key Obsidian-side rules (NOT plugin-specific)

- **Property keys:** case-sensitive when read by Bases/Search; conventionally lowercase with hyphens or underscores. Don't use spaces.
- **List values:** YAML block syntax (`-` per line) is preferred for properties Obsidian's UI knows are lists (`tags`, `aliases`, `cssclasses`). Inline `[a, b]` works but UI may rewrite.
- **Date values:** ISO 8601 (`YYYY-MM-DD` or full timestamp). Obsidian's Properties view renders date pickers only for ISO format.
- **Checkbox properties:** `true` / `false` lowercase. UI renders a checkbox.
- **Number properties:** unquoted; `42` not `"42"`.
- **Tags:** see Tags doc — characters limited to letters, digits (not first), `_`, `-`, `/`. Nested with `/`.
- **Aliases on briefs:** required for bare wikilinks to resolve. Plugin schema requires `aliases: [{slug}]` on every brief.
- **`cssclasses` property:** Obsidian-system property that adds CSS classes to the rendering view. Reserved name.
- **System properties Obsidian populates automatically:** `cssclasses`, `aliases`, `tags`. Don't repurpose these keys.

## Plugin schema vs Obsidian spec — at a glance

| Concern | Plugin (vault-standards) | Obsidian spec |
|---|---|---|
| What keys are required per file type | YES (we mandate `type`, `tags: [ob/X]`, etc.) | NO (Obsidian doesn't require any specific keys) |
| Tag namespace | YES (`#ob/{type}`, `#type/{project_type}`) | NO (any string allowed within character rules) |
| Date format | YES (ISO required) | RECOMMENDED (UI works best with ISO) |
| Wikilink form for project references | YES (piped: `"[[projects/{slug}/brief|{slug}]]"`) | NO (any wikilink form valid) |
| Naming patterns (kebab, date prefixes) | YES (per-type) | NO (any filename valid) |

When the model is generating frontmatter for a vault file, both layers apply: Obsidian spec gates *what's renderable*, plugin spec gates *what's correct for this vault*.
