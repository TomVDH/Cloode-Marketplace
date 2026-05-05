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
relations:                             # optional — cross-project links
  parents: []                          # slugs this project is gated by / descends from
  children: []                         # slugs gated by / descended from this one
  related: []                          # peer cross-references (siblings, spinoffs, deps)
---
```

Project briefs may declare cross-project relationships in frontmatter via `relations:` (optional). Sub-fields `parents`, `children`, `related` are each lists of slug strings — *not* wikilinks. Body text still uses `[[wikilink]]` form for reader-facing cross-references; the `relations` field is for tooling (housekeeping checks, future graph views, indexers). A project can have multiple parents (e.g. a shared lib gated by two products). Cycles in `parents`/`children` are flagged by housekeeping; cycles in `related` are fine.

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

A **doc** is an evergreen, singleton statement of how something is or how it works. No date in the filename. Gets rewritten as understanding evolves — the file IS the current canonical statement, not a record of when it became so.

Common examples: `MANIFESTO.md`, `STANDARDS.md`, `STACK.md`, `STYLE.md`, `SPEC.md`, `ROADMAP.md`, `FAQ.md`, `GLOSSARY.md`, `ARCHITECTURE.md`, `RUNBOOK.md`.

```yaml
---
type: doc
project: "[[projects/{slug}/brief|{slug}]]"
title: "Document title"
updated: 2026-04-30                # required — bump on every substantive edit
tags:
  - ob/doc
---
```

Body shape: 1–2 sentence purpose statement, then `## Sections` (no fixed structure beyond H2-as-section). Follow `## Content style` for body copy rules.

If a doc starts feeling like an entry in a chronological log ("today I changed…"), it should be a `decision` instead. See the disambiguator below.

### Doc vs Decision — disambiguation

The most common mix-up. Use these criteria:

| If… | It's a |
|---|---|
| Has a date in the filename | **Decision** |
| Says "what's true now / how X works / what we believe" | **Doc** |
| Says "we picked X over Y because Z" | **Decision** |
| Will be rewritten as understanding evolves | **Doc** |
| Append-only history of a moment | **Decision** |
| Lives in `decisions/` subfolder | **Decision** |
| Lives at project root or in `docs/` | **Doc** |

**Quick test: "When was this decided?"**
- Has a clear answer → **decision** (timestamp it).
- "It's just how we do things" → **doc** (no timestamp; the file is the canonical statement).

A doc is often a *living rollup* of many decisions. As decisions accumulate, the doc gets rewritten to reflect current state. The decisions stay frozen in `decisions/` as the audit trail.

**Examples**

| File | Type | Why |
|---|---|---|
| `decisions/2026-04-30-use-postgres.md` | decision | The moment of choosing |
| `STACK.md` | doc | Current stack — rewritten when the choice changes |
| `decisions/2026-05-15-rename-classes.md` | decision | The moment of agreement |
| `STYLE.md` | doc | Current naming conventions |
| `decisions/2026-06-01-skip-redux.md` | decision | The trade-off accepted on a date |
| `ARCHITECTURE.md` | doc | Current shape — built from many decisions |

`/dream` flags suspected mismatches (a `type: doc` file with a date prefix, a `type: decision` file at project root, a doc with append-only "log entry" feel, etc.) for human review.

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

## Content style

All vault body copy must be **actionable, clear, unambiguous, and short**. Files are read by both humans and AI agents — both deserve crisp output. Fluff, hedging, and throat-clearing are forbidden. Apply this to every body section of every file type.

### Voice and tense

- **Active voice.** "We chose Postgres." Not "Postgres was chosen."
- **Present tense for current state.** "The auth flow uses JWT." Not "The auth flow will use JWT."
- **Past tense for decisions and events.** "On 2026-04-30 we switched to JWT."
- **Imperative for instructions.** "Run `/sync` after every brief edit." Not "You should run /sync."
- **First-person plural for project decisions** ("we"), third-person for facts ("the auth flow").

### Structure

- **Short paragraphs.** 1–3 sentences. Break frequently. Walls of text fail both AI parsing and human scanning.
- **Headings as outline.** H2 = section, H3 = subsection. Don't skip levels (no H2 → H4). No H1 in body — the file is its own H1.
- **Lists when enumerating.** "First… second… third" inline → make it a list.
- **Tables when comparing.** ≥2 items with shared dimensions → table. Not prose with "whereas X…"
- **Code fences with language tags.** ```bash, ```python, ```yaml, etc. Plain ` ``` ` only when truly language-agnostic.
- **One blank line between blocks.** Two only at major section breaks. Never three.
- **Wikilinks for vault-internal references** (`[[projects/foo/brief|foo]]`). Markdown-style links inside the vault are forbidden — `/dream` flags violations. External URLs use markdown (`[GitHub](https://…)`) or bare angle brackets (`<https://…>`).

### Callouts — signal, not emphasis

Callouts mark the *type* of information. Never use them for "look at this!" emphasis (that's bold's job, sparingly).

| Callout | Use for |
|---|---|
| `> [!note]` | Aside or context that's true but tangential |
| `> [!tip]` | A non-obvious trick or shortcut |
| `> [!warning]` | A real foot-gun |
| `> [!important]` | A constraint that, if missed, breaks something |
| `> [!example]` | A worked example demonstrating a rule |
| `> [!quote]` | Direct quote from a source |

Don't stack callouts. Don't use them as section dividers. Aim for ≤1 callout per ~3 paragraphs of body.

### Cuts — delete on first read

Words and phrases that almost always remove cleanly:

- "I think", "perhaps", "it might be the case that" — say it or don't
- "In this document, we will…" / "The purpose of this section is…" — just write the content
- "As mentioned above" / "as you can see" — references the reader is forced to scroll for
- "Basically", "essentially", "simply" — usually a tell that the next claim isn't simple
- "Of course", "obviously" — patronising
- Adverbs that don't change meaning ("very", "really", "quite", "actually", "just")
- Restating a heading in the first sentence of its section (`# Authentication\n\nAuthentication is…`) — get to the point

### Acceptance-test friendly

Every claim should be checkable:

- "Auth uses JWT" — check the code → yes/no ✓
- "We deploy on Tuesdays" — check the calendar → yes/no ✓
- "This is robust" — not checkable ✗ — say what it tolerates ("survives DB restart") or cut

### Reference body shapes

Common shapes that work. Use them unless the file's specific frontmatter spec says otherwise.

**Decision body**

```markdown
## Decision
[1–3 sentences. The actual decision in plain language.]

## Context
[Why this decision needed to be made. The constraints. 2–4 sentences.]

## Consequence
[What this commits us to. What we accepted in trade. 2–4 sentences.]

[Backlink to brief]
```

**Note body (atomic)**

```markdown
[Single idea. 1–3 paragraphs.]
[Wikilinks to related notes inline.]
```

**Doc body (sectioned)**

```markdown
[1–2 sentence purpose statement.]

## [Section]
[Content. Short paragraphs. Lists where relevant.]

## [Section]
[Content.]
```

**Source body (capture)**

```markdown
[1–3 sentences: why this source is in the vault.]

## Notes
- [Bullet list of takeaways or pull quotes.]

## Cited in
- [[Wikilinks to vault notes that reference this source.]]
```

**Iteration body**

```markdown
[1–2 sentences: what this iteration explores.]

## Approach
[The shape of the variant. Bullet list if multiple moving parts.]

## Strengths / Weaknesses
| Strengths | Weaknesses |
|---|---|
| … | … |

## Verdict
[Why drafting / on-shelf / picked / parked / rejected. 1–3 sentences.]
```

### Validator behaviour

The PostToolUse validator hook checks frontmatter. The full content-style rules above are *not* mechanically enforced (style is judgment). `/dream` (Pass 2) flags suspected style violations for human review — wall-of-text paragraphs, callout misuse, throat-clearing openings, restating-the-heading patterns.

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
