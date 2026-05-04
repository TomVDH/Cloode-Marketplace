---
name: vault-standards
description: Use when writing or editing YAML frontmatter in an `obsidian-bridge` vault, or when the user references vault schema, `#ob/` tags, naming conventions, or wikilink rules.
allowed-tools: Read, Glob, Grep
version: 0.1.0
---

# Vault Standards

Canonical frontmatter schemas, naming conventions, tag taxonomy, wikilink forms, and structural rules for the Obsidian vault. Single source of truth — all vault writes must conform. Templates in `examples/vault-templates/` mirror these definitions.

## General Rules

### Frontmatter

Every vault file has YAML frontmatter. No exceptions.

- Use standard YAML — no Obsidian-specific syntax inside frontmatter values except `project` fields (piped wikilinks).
- Dates: ISO format `YYYY-MM-DD` for date-only, full ISO 8601 for timestamps.
- Strings with special characters (colons, brackets) must be quoted.
- Empty optional fields: **omit the key entirely** rather than `null` or empty string.
- Arrays use YAML list syntax, not inline `[]` (exception: empty arrays use `[]`).

### Project References

The `project` field in frontmatter uses a **piped wikilink to the brief**:

```yaml
project: "[[projects/hubspot-dev/brief|hubspot-dev]]"
```

Clickable in Obsidian, resolves to the brief, displays the slug as alias. Always this format — not bare slugs, not unpiped wikilinks.

### Specialist Names (cabinet integration)

When cabinet is installed and populates the `specialist:` field, names are always **lowercase**: `bostrol`, `thieuke`, `sakke`, `jonasty`, `pitr`, `henske`, `kevijntje`, `poekie`. Bridge preserves these values but does not require the field.

---

## Tag Taxonomy

Two flat categories, deliberately lean. No deep nesting.

### Structural tags — `#ob/{filetype}`

One per file, always present:

`#ob/project`, `#ob/decision`, `#ob/session`, `#ob/note`, `#ob/source`, `#ob/doc`, `#ob/handoff`, `#ob/release`, `#ob/iteration`, `#ob/dream-report`, `#ob/index`

### Type tags — `#type/{project_type}`

Briefs only: `#type/coding`, `#type/knowledge`, `#type/plugin`, `#type/tinkerage`

### Topical tags

Bare, lowercase, hyphenated. Optional, sparingly. Must be **queryable** — the user would actually filter on them. Bridge does not auto-add topical tags. `/dream` flags:

- Single-use tags
- Near-duplicate tags (`#postgres` vs `#postgresql`)
- Vague tags (`#wip`, `#misc`, `#general`, `#thoughts`)
- Tags drifting out of `ob/` namespace conventions

### Cabinet coexistence

Cabinet's `#cabinet/*` tags are preserved alongside `#ob/*` equivalents during migration (multi-tag). Bridge does not strip them.

---

## Naming Rules

| Item | Pattern |
|---|---|
| Project slug | lowercase, hyphenated, no spaces, no dots (`dff2026-web`) |
| Brief | always `brief.md` |
| Decision | `YYYY-MM-DD-{kebab-title}.md` |
| Session | `YYYY-MM-DD.md` (one per project per day; same-day re-runs append) |
| Note | `{kebab-title}.md` (no date prefix unless time-relevant) |
| Source | `{kebab-title}.md` |
| Reference | `{kebab-title}.md` |
| Release (plugin) | `vX.Y.Z.md` |
| Iteration (file form) | `YYYY-MM-DD-iter-{id}-{kebab-slug}.md` |
| Iteration (folder form) | `YYYY-MM-DD-iter-{id}-{kebab-slug}/` containing `_iteration.md` |
| Dream report | `YYYY-MM-DD.md` |
| Doc (singleton) | `{NAME}.md` (often UPPERCASE: `MANIFESTO.md`, `STANDARDS.md`) |
| Handoff | `_handoff.md` (single file per project, overwriteable) |
| Index | `_index.md` |

---

## Wikilink Rules

All vault-internal links use `[[note-name]]` form. Markdown-style `[text](path)` is **forbidden** inside the vault — `/dream` flags violations.

| Context | Form |
|---|---|
| Frontmatter `project:` field | `"[[projects/{slug}/brief\|{slug}]]"` (piped, always) |
| Body → brief | `[[projects/{slug}/brief\|{display}]]` |
| Body → decision | `[[projects/{slug}/decisions/{file}\|{short title}]]` |
| Body → session | `[[projects/{slug}/sessions/{date}\|{date}]]` |
| Body → source | `[[projects/{slug}/sources/{file}\|{author, year}]]` |
| Image embed | `![[image.png]]` with caption line below |

Briefs always carry `aliases: [{slug}]` so bare `[[my-project]]` resolves cleanly.

---

## File Type Schemas

### Brief — `projects/{slug}/brief.md`

```yaml
---
type: project                          # required
project_type: coding                   # required — coding | knowledge | plugin | tinkerage
slug: my-project                       # required — kebab-case
aliases:                               # required — at minimum contains the slug
  - my-project
status: active                         # required — active | paused | archived | complete
created: 2026-04-30                    # required
updated: 2026-04-30                    # required — date of last substantive update
tags:                                  # required
  - ob/project
  - type/coding                        # matches project_type
repo: git@github.com:owner/repo.git   # optional (coding/plugin only)
stack: [Next.js, Tailwind]             # optional (coding/plugin only)
marketplace: onnozelaer                # optional (plugin only)
---
```

Body: type-shaped block set (see §5 in spec). Block headers are UPPERCASE.

### Decision — `projects/{slug}/decisions/YYYY-MM-DD-{title}.md`

```yaml
---
type: decision                                              # required
project: "[[projects/{slug}/brief|{slug}]]"                 # required
status: active                                              # required — active | superseded | reversed | implemented
date: 2026-04-30                                            # required
tags:                                                       # required
  - ob/decision
specialist: bostrol                                         # optional (cabinet)
supersedes: "[[projects/{slug}/decisions/{prev}]]"          # optional
---
```

Body: `## Decision`, `## Context`, `## Consequence`. Ends with backlink to brief.

### Session — `projects/{slug}/sessions/YYYY-MM-DD.md`

```yaml
---
type: session                                               # required
project: "[[projects/{slug}/brief|{slug}]]"                 # required
date: 2026-04-30                                            # required
tags:                                                       # required
  - ob/session
specialists: [bostrol]                                      # optional (cabinet)
branch: main                                                # optional
commits: [abc1234]                                          # optional
gates_completed: 0                                          # optional (cabinet)
---
```

### Note — `projects/{slug}/notes/{title}.md`

```yaml
---
type: note
project: "[[projects/{slug}/brief|{slug}]]"
created: 2026-04-30
updated: 2026-04-30
tags:
  - ob/note
---
```

### Source — `projects/{slug}/sources/{title}.md`

```yaml
---
type: source
project: "[[projects/{slug}/brief|{slug}]]"
title: "Title of source"
author: "Author name"
url: https://example.com
medium: article                        # book | paper | article | course | talk | other
year: 2026
tags:
  - ob/source
---
```

### Doc — `projects/{slug}/{NAME}.md`

```yaml
---
type: doc
project: "[[projects/{slug}/brief|{slug}]]"
title: "Document title"
updated: 2026-04-30
tags:
  - ob/doc
---
```

### Handoff — `projects/{slug}/_handoff.md`

```yaml
---
type: handoff
project: "[[projects/{slug}/brief|{slug}]]"
updated: 2026-04-30
source: remember                       # remember | manual
tags:
  - ob/handoff
---
```

### Iteration — `projects/{slug}/iterations/YYYY-MM-DD-iter-{id}-{slug}.md`

```yaml
---
type: iteration
project: "[[projects/{slug}/brief|{slug}]]"
identifier: D                          # letter, number, or short word
status: drafting                       # drafting | on-shelf | picked | parked | rejected | superseded
date: 2026-04-30
tags:
  - ob/iteration
track: navy-dominant                   # optional — grouping/direction
register: "Navy-dominant · modern B2B SaaS"  # optional — short tagline
supersedes: "[[...]]"                  # optional
builds_on: "[[...]]"                   # optional
artefacts: [shelf.html, concept.png]   # optional (folder form only)
---
```

### Release — `projects/{slug}/releases/vX.Y.Z.md`

```yaml
---
type: release
project: "[[projects/{slug}/brief|{slug}]]"
version: X.Y.Z
date: 2026-04-30
tags:
  - ob/release
---
```

### Dream Report — `projects/{slug}/dreams/YYYY-MM-DD.md`

```yaml
---
type: dream-report
project: "[[projects/{slug}/brief|{slug}]]"
date: 2026-04-30
tags:
  - ob/dream-report
---
```

### Index — `_index.md` (project-scoped or vault-root)

```yaml
---
type: index
project: "[[projects/{slug}/brief|{slug}]]"    # only for project-scoped
tags:
  - ob/index
---
```

### Home — `Home.md`

```yaml
---
type: vault-home
updated: 2026-04-30
---
```

Multi-plugin vault (cabinet installed):

```yaml
type:
  - vault-home
  - cabinet-home
```

---

## The `_index.md` Rule

Every folder under a project (or at vault root) that holds ≥2 sibling `.md` files of the same conceptual type gets an `_index.md`.

**Exceptions:** `sessions/` (chronological ordering is the index), `images/`, `assets/`, `previews/` (non-text or build artefacts).

**Auto-creation triggers:**
- Conversational project creation ("new project foo, knowledge type") scaffolds defaults per type.
- Conversational collection add ("add a tasks/ folder to foo") scaffolds arbitrary collection.
- `/ramasse indexes` (or full `/ramasse`) rebuilds all.
- `/dream` flags missing `_index.md` and offers to create.
- Migration auto-creates missing ones.

**Index content shape:** `# {Collection Name}`, one-line description, `## Entries` with wikilinks. Chronological sort where dates are in filenames; alphabetical otherwise.

---

## Per-Type Project Subfolder Defaults

| Type | Subfolders with `_index.md` | Subfolders without `_index.md` |
|---|---|---|
| **coding** | `decisions/`, `notes/`, `tasks/`, `references/` | `sessions/`, `images/` |
| **plugin** | coding + `releases/` | `sessions/`, `images/` |
| **knowledge** | `notes/`, `sources/`, `references/` | `sessions/` |
| **tinkerage** | (none by default) | `sessions/` (optional) |
