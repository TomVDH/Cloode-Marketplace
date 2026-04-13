# Vault Standards

Canonical frontmatter schemas, naming conventions, and structural rules for the Cabinet's Obsidian vault. This is the single source of truth — all vault writes by the Cabinet must conform to these schemas. Templates in `examples/vault-templates/` mirror these definitions.

## General Rules

### Frontmatter

Every vault file has YAML frontmatter. No exceptions. If a file is created without frontmatter, the next specialist to touch it adds it.

- Use standard YAML — no Obsidian-specific syntax inside frontmatter values except for `project` fields (see below).
- Dates use ISO format: `YYYY-MM-DD` for date-only, full ISO 8601 for timestamps.
- Strings with special characters (colons, brackets) must be quoted.
- Empty optional fields: **omit the key entirely** rather than setting it to `null` or empty string. The schema below marks which fields are required vs optional.
- Arrays use YAML list syntax, not inline `[]` (exception: empty arrays use `[]`).

### Project References

The `project` field in frontmatter uses a **piped wikilink to the brief**:

```yaml
project: "[[projects/hubspot-dev/brief|hubspot-dev]]"
```

This format is clickable in Obsidian, resolves to the project brief, and displays the slug as the alias. Always use this format — not bare slugs, not unpiped wikilinks.

### Specialist Names

Always **lowercase**: `bostrol`, `thieuke`, `sakke`, `jonasty`, `pitr`, `henske`, `kevijntje`, `poekie`. This ensures Dataview queries and graph filters work reliably. Never capitalise specialist names in frontmatter.

### Tag Conventions

Tags use a two-tier system:

- **Structural tags** are namespaced under `cabinet/`: `cabinet/decision`, `cabinet/session`, `cabinet/project`, `cabinet/crew`. These identify the file type and are always present.
- **Topic tags** are bare: `codex`, `cleanup`, `architecture`, `email`, `animation`. These describe the subject matter and vary per file.

Every file gets at least one structural tag. Topic tags are optional but encouraged.

```yaml
tags:
  - cabinet/decision
  - architecture
  - email
```

### Wikilinks in Body Text

- Link to briefs: `[[projects/{slug}/brief|{Display Name}]]`
- Link to decisions: `[[projects/{slug}/decisions/{filename}|{Short Title}]]`
- Link to sessions: `[[projects/{slug}/sessions/{date}|{date}]]`
- Link to crew files: `[[crew/{filename}|{Display Name}]]`
- Embed images: `![[{filename}.png]]` with a caption line below

### File Naming

- Decisions: `YYYY-MM-DD-{kebab-case-title}.md`
- Sessions: `YYYY-MM-DD.md`
- Briefs: `brief.md` (always this name, inside the project folder)
- Indices: `_index.md`
- Crew files: `{descriptive-name}.md` (kebab-case)
- Chatter: `YYYY-MM-DD.md` (inside `chatter/` folder)

---

## File Type Schemas

### Brief (`projects/{slug}/brief.md`)

```yaml
---
type: project                          # required — always "project"
slug: hubspot-dev                      # required — kebab-case project identifier
aliases:                               # required — array, at minimum contains the slug
  - hubspot-dev
status: active                         # required — "active" | "paused" | "archived" | "complete"
created: 2026-03-12                    # required — date project was created
updated: 2026-04-01                    # required — date of last substantive update
tags:                                  # required
  - cabinet/project
  - {topic tags as relevant}
repo: git@github.com:owner/repo.git    # optional — git remote URL or local path
stack: [Next.js, Tailwind, Node]       # optional — tech stack summary
---
```

**Body structure**: `# Title`, then free-form sections. Common sections include Overview, Tech Stack, Scope (In / Out / Parked), Conventions, Team Notes. The brief is a living document — Bostrol updates it when scope or stack changes.

### Decision (`projects/{slug}/decisions/YYYY-MM-DD-{title}.md`)

```yaml
---
type: decision                                              # required
project: "[[projects/{slug}/brief|{slug}]]"                 # required — piped wikilink
specialist: bostrol                                         # required — lowercase
status: active                                              # required — "active" | "superseded" | "reversed" | "implemented"
date: 2026-03-12                                            # required — date decision was made
tags:                                                       # required
  - cabinet/decision
  - {topic tags as relevant}
---
```

**Body structure**:

```markdown
## {Decision Title}

**Context:** Why this decision was needed.

**Decision:** What was decided.

**Rationale:** Why this option was chosen over alternatives.

**Impact:** What changes as a result.
```

Alternative body format (from template — either is acceptable):

```markdown
## Decision
{what}

## Context
{why}

## Consequence
{impact}
```

The decision ends with a backlink: `[[projects/{slug}/brief|{slug}]]`

### Session Summary (`projects/{slug}/sessions/YYYY-MM-DD.md`)

```yaml
---
type: session                                               # required
project: "[[projects/{slug}/brief|{slug}]]"                 # required — piped wikilink
date: 2026-03-22                                            # required
specialists: []                                             # required — array of lowercase names who were active
tags:                                                       # required
  - cabinet/session
  - {topic tags as relevant}
branch: main                                                # optional — git branch if relevant
commits: []                                                 # optional — array of short hashes
gates_completed: 0                                          # optional — number of gates passed
---
```

**Body structure**: `## Session: {Title}`, then free-form. Summarise what happened, decisions made, open items, energy state. The session summary is written at wrap-up by Bostrol.

### Decision Index (`projects/{slug}/decisions/_index.md`)

```yaml
---
type: index
project: "[[projects/{slug}/brief|{slug}]]"
tags:
  - cabinet/index
---
```

**Body**: A list of wikilinks to all decisions in the project, maintained by Bostrol. New decisions are appended here when written.

### Project Index (`projects/_index.md`)

```yaml
---
type: index
tags:
  - cabinet/index
---
```

**Body**: Master list of all projects with status and last session date.

### Crew: Preferences (`crew/preferences.md`)

```yaml
---
type: preferences
updated: 2026-03-24
tags:
  - cabinet/crew
---
```

**Body**: Grouped by domain (General > Design & Aesthetic, Code & Architecture, Communication, Background; then project-specific sections). Each preference is a bullet with a date in parentheses: `- {preference text} (YYYY-MM-DD)`.

### Crew: Lessons Learned (`crew/lessons-learned.md`)

```yaml
---
type: lessons
updated: 2026-03-26
tags:
  - cabinet/crew
---
```

**Body**: Grouped by domain (Vault & Cross-Session, CSS & Animation, Process, Data & Parsing, etc.). Each lesson is a bold title followed by explanation and source in italics: `*(Project — YYYY-MM-DD)*`.

### Crew: Easter Eggs (`crew/easter-eggs.md`)

```yaml
---
type: easter-eggs
updated: 2026-04-01
tags:
  - cabinet/crew
  - cabinet/lore
---
```

**Body**: Free-form crew lore, anecdotes, running jokes. Each entry has a bold title with date and a project backlink.

### Crew: Concept Basket (`crew/concept-basket.md`)

```yaml
---
type: concepts
updated: 2026-03-23
tags:
  - cabinet/crew
  - cabinet/concepts
---
```

**Body**: Transferable design patterns and concepts harvested from project work. Grouped by source project, then by category (UX Patterns, AI Patterns, etc.). Each concept is numbered with a bold title and explanation.

### Chatter (`projects/{slug}/chatter/YYYY-MM-DD.md`)

```yaml
---
type: chatter
project: "[[projects/{slug}/brief|{slug}]]"
date: 2026-04-01
tags:
  - cabinet/chatter
---
```

**Body**: Markdown chatter entries separated by horizontal rules with emoji headers. See `chatter-system.md` for the full format specification.

### Home (`Home.md`)

```yaml
---
type: cabinet-home
updated: 2026-04-12
---
```

**Body**: Active Projects, Recent Decisions, Recent Sessions, Quick Links. Updated by Bostrol at every session wrap-up. The `updated` field tracks the last rebuild.

### Aesthetics Direction (`projects/{slug}/aesthetics/foundational/direction-{id}-{title}.md`)

```yaml
---
type: direction
tags:
  - cabinet/aesthetics
  - {topic tags}
---
```

**Body**: Free-form creative direction documentation.

---

## Enforcement

Bostrol is the vault standards owner. When writing any vault file, he conforms to this spec. If he encounters a non-conforming file during a `/dream` audit or a normal session, he silently fixes the frontmatter — no ceremony, no gate, just fixes it.

Jonasty can flag vault standards violations during QA if they notice them, but it's not a gate blocker (unlike version parity). Vault standards are a maintenance concern, not a release concern.

At project wrap-up, Bostrol's final audit includes a frontmatter conformance check across all files touched during the session.
