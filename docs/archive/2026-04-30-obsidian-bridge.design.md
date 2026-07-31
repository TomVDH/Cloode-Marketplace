# Obsidian Bridge — Design Spec

**Date:** 2026-04-30
**Status:** Approved for implementation planning
**Plugin name:** `obsidian-bridge`
**Marketplace:** `onnozelaer-claude-plugins`

---

## 1. Overview

`obsidian-bridge` is a new standalone plugin that owns the canonical Obsidian-vault layout, schema, primitives, and `/dream` cleanup workflow currently embedded in the `cabinet-of-imd` plugin. It is extracted from cabinet to allow vault-backed work to function without depending on cabinet's specialist crew.

Cabinet retains its understanding of *when* to write to the vault (gates, wrap-ups, preference capture, crew personality) but defers *how* the vault is structured, named, and validated to the bridge. Cabinet's `/vault-bridge` skill folder and `/dream` command are deleted from cabinet and re-homed in the bridge.

### Goals

- Obsidian-bridge functions standalone (no cabinet dependency) — a user can install only the bridge and get a working vault flow.
- One canonical schema for Obsidian content: frontmatter, naming, wikilinks, tags, file layout.
- Type-shaped projects — `coding`, `knowledge`, `plugin`, `tinkerage` — each with appropriate brief blocks and subfolder defaults.
- Hooks ensure every session has a connected vault (or a clear path to one).
- `/dream` extends the cabinet's content-analysis pass with a structural-sanitation pass and takes the lead on auto-fixable cleanup.
- Light, opt-in integration with the `remember` plugin.

### Non-goals

- Re-implementing cabinet's specialist crew, gates, chatter, or session anchor logic.
- Replacing remember's compression pipeline.
- Forcing pre-existing v2 vaults to migrate without explicit user consent.
- Supporting non-Obsidian markdown vaults (Logseq, Bear, etc.) — Obsidian-first.

### Decisions captured during brainstorming

| Question | Choice |
|---|---|
| Boundary between bridge and cabinet | **A** — bridge owns canonical vault layout end-to-end; cabinet keeps its understanding of how to use it |
| Project type → brief shape | **B** — type-shaped templates with type-shaped subfolders |
| Existing-vault migration UX | **B** — explicit `/vault-bridge migrate` command with backup, suggested but not auto-run |

---

## 2. Plugin scaffolding & marketplace

### File layout

```
onnozelaer-claude-plugins/obsidian-bridge/
├── .claude-plugin/
│   └── plugin.json
├── README.md
├── CHANGELOG.md
├── LICENSE
├── commands/
│   ├── vault-bridge.md
│   └── dream.md
├── skills/
│   ├── vault-bridge/
│   │   └── SKILL.md
│   └── dream/
│       └── SKILL.md
├── hooks/
│   ├── hooks.json
│   └── scripts/
│       ├── session-start-vault.sh
│       └── session-end-handoff.sh
├── references/
│   ├── vault-standards.md
│   ├── vault-integration.md
│   ├── obsidian-setup.md
│   └── remember-integration.md
└── examples/
    └── vault-templates/
        ├── brief-coding.md
        ├── brief-knowledge.md
        ├── brief-plugin.md
        ├── brief-tinkerage.md
        ├── decision.md
        ├── session.md
        ├── note.md
        ├── source.md
        ├── doc.md
        ├── handoff.md
        ├── home.md
        ├── projects-index.md
        └── collection-index.md
```

### Marketplace registration

Add to `onnozelaer-claude-plugins/.claude-plugin/marketplace.json`:

```json
{
  "name": "obsidian-bridge",
  "version": "0.1.0",
  "source": "./obsidian-bridge",
  "description": "Standalone Obsidian-vault primitive layer: canonical schema, type-shaped project layouts, /vault-bridge command, /dream cleanup, CLI-first writes with filesystem fallback. Pairs cleanly with the cabinet-of-imd plugin but functions on its own."
}
```

### Plugin manifest (`obsidian-bridge/.claude-plugin/plugin.json`)

```json
{
  "name": "obsidian-bridge",
  "version": "0.1.0",
  "description": "Canonical Obsidian-vault layout, schema, primitives, and cleanup workflow for Claude Code. Standalone and cabinet-aware.",
  "author": { "name": "Onnozelaer" },
  "homepage": "https://github.com/TomVDH/onnozelaer-claude-marketplace/tree/main/obsidian-bridge",
  "repository": "https://github.com/TomVDH/onnozelaer-claude-marketplace",
  "license": "MIT",
  "keywords": ["obsidian", "vault", "knowledge-management", "markdown", "frontmatter", "wikilinks"]
}
```

---

## 3. Vault structure (v3)

### Root layout

```
{vault root}/
├── .obsidian/                     ← Obsidian's own config (untouched)
├── Home.md                        ← type: vault-home, auto-rebuilt
├── projects/
│   ├── _index.md                  ← MOC: all projects
│   └── {slug}/...                 ← shape varies by project_type
├── archive/
│   └── {slug}/...                 ← same per-type shape; status: archived
└── templates/
    └── {brief-{type}|decision|session|...}.md
```

When `cabinet-of-imd` is also installed, cabinet adds and manages a `crew/` folder at vault root. Bridge knows it exists and **leaves it alone** — bridge's commands, `/dream`, and housekeeping never touch `crew/`.

### Per-type project subfolder defaults

Each subfolder is auto-scaffolded by `/vault-bridge create-project` based on `project_type`. Folders with sibling notes ("collections") get an `_index.md`; chronological or non-text folders do not.

| Type | Subfolders with `_index.md` | Subfolders without `_index.md` |
|---|---|---|
| **coding** | `decisions/`, `notes/`, `tasks/`, `references/` | `sessions/`, `images/` |
| **plugin** | coding + `releases/` | `sessions/`, `images/` |
| **knowledge** | `notes/`, `sources/`, `references/` | `sessions/` |
| **tinkerage** | (none by default) | `sessions/` (optional) |

`assets/`, `previews/`, and any folder of binaries also have no `_index.md`.

### User-extensible sub-collections

When a user (or cabinet, or another agent) creates a folder under a project that contains ≥2 sibling `.md` files, that folder is treated as a collection. `/vault-bridge add-collection <name>` scaffolds a new collection with `_index.md` already populated. `/dream` flags collections without `_index.md` and offers to create one.

This pattern is observed empirically in your existing vault: `tf-renewal/design-iterations/`, `dutchbc-poc/aesthetics/`, `tegenlicht-controls/dreams/`, etc., all already use `_index.md`.

### Root-of-project singleton docs

Files like `MANIFESTO.md`, `STANDARDS.md`, `CHANGELOG.md`, `brand.md`, `logotype.md` keep their organic names but must carry frontmatter (`type: doc`). `/dream` flags root-level singletons missing frontmatter and offers to add.

### `Home.md`

Auto-rebuilt by `update_home()` from disk state. Sections: Active Projects, Recent Decisions (last 5 across vault), Recent Sessions (last 5), Archived Projects, Quick Links. Frontmatter: `type: vault-home`. When `crew/` exists, Quick Links includes a pointer to it; bridge does not rewrite the crew section.

---

## 4. Frontmatter schemas

All schemas use ISO dates (`YYYY-MM-DD`), arrays in YAML list syntax, omit optional empty fields rather than setting `null`.

### Brief — `projects/{slug}/brief.md`

```yaml
---
type: project
project_type: coding | knowledge | plugin | tinkerage
slug: {slug}
aliases:
  - {slug}
status: active | paused | archived | complete
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags:
  - ob/project
  - type/{project_type}
# coding/plugin only:
repo: git@github.com:owner/repo.git
stack: [Next.js, Tailwind, Postgres]
# plugin only:
marketplace: onnozelaer
---
```

### Decision — `projects/{slug}/decisions/YYYY-MM-DD-{title}.md`

```yaml
---
type: decision
project: "[[projects/{slug}/brief|{slug}]]"
status: active | superseded | reversed | implemented
date: YYYY-MM-DD
tags:
  - ob/decision
# optional:
specialist: bostrol
supersedes: "[[projects/{slug}/decisions/YYYY-MM-DD-{title}]]"
---
```

### Session — `projects/{slug}/sessions/YYYY-MM-DD.md`

```yaml
---
type: session
project: "[[projects/{slug}/brief|{slug}]]"
date: YYYY-MM-DD
tags:
  - ob/session
# optional:
specialists: [bostrol]
branch: main
commits: [abc1234]
gates_completed: 0
---
```

### Note — `projects/{slug}/notes/{title}.md`

```yaml
---
type: note
project: "[[projects/{slug}/brief|{slug}]]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags:
  - ob/note
---
```

### Source — `projects/{slug}/sources/{title}.md` (knowledge type)

```yaml
---
type: source
project: "[[projects/{slug}/brief|{slug}]]"
title: "Title of source"
author: "Author name"
url: https://...
medium: book | paper | article | course | talk | other
year: YYYY
tags:
  - ob/source
---
```

### Doc (root-of-project singleton) — `projects/{slug}/{NAME}.md`

```yaml
---
type: doc
project: "[[projects/{slug}/brief|{slug}]]"
title: "Document title"
updated: YYYY-MM-DD
tags:
  - ob/doc
---
```

### Handoff — `projects/{slug}/_handoff.md`

```yaml
---
type: handoff
project: "[[projects/{slug}/brief|{slug}]]"
updated: YYYY-MM-DD
source: remember | manual
tags:
  - ob/handoff
---
```

### Iteration — `projects/{slug}/iterations/YYYY-MM-DD-iter-{id}-{slug}.md` (or folder + `_iteration.md`)

```yaml
---
type: iteration
project: "[[projects/{slug}/brief|{slug}]]"
identifier: D
status: drafting | on-shelf | picked | parked | rejected | superseded
date: YYYY-MM-DD
tags:
  - ob/iteration
# optional:
track: navy-dominant
register: "Navy-dominant · modern B2B SaaS"
supersedes: "[[projects/{slug}/iterations/{previous}|{previous}]]"
builds_on: "[[projects/{slug}/iterations/{ancestor}|{ancestor}]]"
artefacts:
  - shelf.html
  - concept-1.png
---
```

Full schema and lifecycle in §8.

### Release (plugin type) — `projects/{slug}/releases/vX.Y.Z.md`

```yaml
---
type: release
project: "[[projects/{slug}/brief|{slug}]]"
version: X.Y.Z
date: YYYY-MM-DD
tags:
  - ob/release
---
```

### Dream report (opt-in) — `projects/{slug}/dreams/YYYY-MM-DD.md`

```yaml
---
type: dream-report
project: "[[projects/{slug}/brief|{slug}]]"
date: YYYY-MM-DD
tags:
  - ob/dream-report
---
```

### Index files — `projects/_index.md`, `projects/{slug}/{collection}/_index.md`

```yaml
---
type: index
# project-scoped index only:
project: "[[projects/{slug}/brief|{slug}]]"
tags:
  - ob/index
---
```

### Home — `Home.md`

```yaml
---
type: vault-home
updated: YYYY-MM-DD
---
```

When the cabinet-home schema is also present (multi-plugin vault), `type` may be a YAML list:

```yaml
type:
  - vault-home
  - cabinet-home
```

---

## 5. Brief body templates per type

The brief body is a strict block set per type. Empty blocks are kept (with a one-line "TBD" or removed if the type allows it). Bridge's templates (`examples/vault-templates/brief-{type}.md`) ship with these exact section headers.

### `coding` & `plugin`

```markdown
# {Project Name}

## INTRO

## TECHNICAL STACK

## CONSTRAINTS

## WORK NOTES

## MILESTONES

## USER DECISIONS

## ITERATIONS        ← optional; auto-populated by bridge when first iteration is created
```

`plugin` adds:

```markdown
## RELEASE NOTES
```

(Pointer to `releases/` folder + last 2-3 release summaries inline.)

The `## ITERATIONS` block is omitted from the template until the first iteration is created — bridge inserts the block at that point with a single wikilink to `iterations/_index.md`. Projects that never iterate keep a clean brief.

### `knowledge`

```markdown
# {Project Name}

## INTRO

## SOURCES

## OPEN QUESTIONS

## WORK NOTES

## USER DECISIONS
```

### `tinkerage`

```markdown
# {Project Name}

## INTRO

## WORK NOTES
```

---

## 6. Naming, wikilinks, tags

### Naming rules

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
| Iteration (folder form) | folder name = `YYYY-MM-DD-iter-{id}-{kebab-slug}/` containing `_iteration.md` |
| Dream report | `YYYY-MM-DD.md` |
| Doc (singleton) | `{NAME}.md` (often UPPERCASE for emphasis: `MANIFESTO.md`, `STANDARDS.md`) |
| Handoff | `_handoff.md` (single file per project, overwriteable) |
| Index | `_index.md` |

### Wikilinks — single form, used consistently

- All vault-internal links use `[[note-name]]` form. Markdown-style `[text](path)` is forbidden inside the vault — `/dream` flags violations.
- Frontmatter `project` field is always piped: `project: "[[projects/{slug}/brief|{slug}]]"`.
- Body links to brief: `[[projects/{slug}/brief|{display}]]`.
- Body links to decisions: `[[projects/{slug}/decisions/{file}|{short title}]]`.
- Body links to sessions: `[[projects/{slug}/sessions/{date}|{date}]]`.
- Body links to sources: `[[projects/{slug}/sources/{file}|{author, year}]]`.
- Image embeds: `![[image.png]]` with caption line below.
- Briefs always carry `aliases: [{slug}]` so bare `[[my-project]]` resolves cleanly.

### Tag taxonomy — deliberately lean

Two flat categories, no deep nesting beyond namespace:

| Category | Format | When |
|---|---|---|
| Structural | `#ob/{filetype}` — one per file | Always, exactly one |
| Type tag | `#type/{project_type}` | Briefs only |
| Topical | bare lowercase, hyphenated | Optional, sparingly |

Structural set: `#ob/project`, `#ob/decision`, `#ob/session`, `#ob/note`, `#ob/source`, `#ob/doc`, `#ob/handoff`, `#ob/release`, `#ob/iteration`, `#ob/dream-report`, `#ob/index`.

Topical tags must be **queryable** — i.e., the user would actually filter on them. Bridge does not auto-add topical tags. `/dream` flags:

- Single-use tags
- Near-duplicate tags (`#postgres` vs `#postgresql`)
- Vague tags (`#wip`, `#misc`, `#general`, `#thoughts`)
- Tags drifting out of `ob/` namespace conventions

Cabinet's existing `#cabinet/*` tags are preserved during migration alongside `#ob/*` equivalents (multi-tag) — bridge does not strip them.

---

## 7. The `_index.md` rule

**Rule:** Every folder under a project (or at vault root) that holds ≥2 sibling `.md` files of the same conceptual type gets an `_index.md`.

**Exceptions:**
- `sessions/` — chronological, ordering is the index.
- `images/`, `assets/`, `previews/` — non-text or build artefacts.

**Auto-creation triggers:**
- `/vault-bridge create-project` scaffolds defaults per type.
- `/vault-bridge add-collection <name>` scaffolds an arbitrary user-defined collection.
- `/vault-bridge reindex` rebuilds all `_index.md` files from disk.
- `/dream` flags missing `_index.md` files and offers to create.
- Migration auto-creates missing `_index.md` files.

**Index content shape:**

```markdown
---
type: index
project: "[[projects/{slug}/brief|{slug}]]"
tags: [ob/index]
---

# {Collection Name}

{One-line description of what this collection holds.}

## Entries

- [[YYYY-MM-DD-some-decision|Some decision]] — {date}
- [[YYYY-MM-DD-other|Other entry]] — {date}
```

Sorting: chronological where dates are part of filenames; alphabetical otherwise.

---

## 8. Iterations — first-class collection type

Iterations are a recurring real-world pattern in your vault — `tf-renewal/design-iterations/` has 11 entries (A–N) on a `navy-dominant` track, each with `register` taglines and `on-shelf` statuses; `dutchbc-poc/aesthetics/` shows nested categorisation. Bridge canonicalises this so the vault treats iterations consistently across projects.

### 8.1 Folder

`projects/{slug}/iterations/` — single canonical name. Auto-scaffolded with `_index.md` on first iteration creation. Replaces emergent variants (`design-iterations/`, `aesthetics/`, `surfaces/`) for new projects. Existing emergent folders are not auto-renamed; `/dream` flags them and offers per-folder canonicalisation.

### 8.2 File-or-folder per iteration

**Default — single `.md`:** `iterations/YYYY-MM-DD-iter-{id}-{kebab-slug}.md`

**With artefacts — folder containing `_iteration.md` + assets:**

```
iterations/
├── _index.md
├── 2026-04-22-iter-D-home.md          ← simple iteration
├── 2026-04-22-iter-E-home/             ← rich iteration with artefacts
│   ├── _iteration.md
│   ├── shelf.html
│   ├── concept-1.png
│   └── concept-2.png
```

`/vault-bridge add-iteration <id> <slug>` creates the file form by default. `--with-folder` creates the folder form upfront. `add-iteration-artefact <iter-id> <file>` promotes a file-form iteration to a folder-form when the first artefact lands (moves the `.md` into the new folder, renames it `_iteration.md`, places the artefact alongside).

### 8.3 Frontmatter

```yaml
---
type: iteration
project: "[[projects/{slug}/brief|{slug}]]"
identifier: D                                       # letter, number, or short word
status: drafting | on-shelf | picked | parked | rejected | superseded
date: YYYY-MM-DD
track: navy-dominant                                # optional grouping (the "direction")
register: "Navy-dominant · modern B2B SaaS"         # optional short tagline
tags: [ob/iteration]
# optional:
supersedes: "[[projects/{slug}/iterations/{previous}|{previous}]]"
builds_on: "[[projects/{slug}/iterations/{ancestor}|{ancestor}]]"
artefacts: [shelf.html, concept-1.png]
---
```

Status values map onto the natural lifecycle: `drafting` (in progress) → `on-shelf` (presented for review) → `picked` (chosen direction) | `parked` (deferred) | `rejected` (not pursued). `superseded` is set automatically when another iteration declares `supersedes:` this one.

### 8.4 Naming

`YYYY-MM-DD-iter-{identifier}-{kebab-slug}.md`

- Date prefix because chronology matters and iterations stack quickly.
- `iter-{identifier}` for sorting and quick reference; identifier can be a letter (A–Z), number, or short word (`mobile-baseline`).
- Trailing slug describes the iteration in one phrase.
- Folder form replaces the `.md` extension with a directory of the same base name; the iteration's writeup file inside is always `_iteration.md`.

Examples (all valid): `2026-04-22-iter-D-home.md`, `2026-04-23-iter-12-product-grid.md`, `2026-04-24-iter-mobile-baseline-controls/`.

### 8.5 `_index.md` shape

Iterations grouped by track, with status badges:

```markdown
---
type: index
project: "[[projects/{slug}/brief|{slug}]]"
tags: [ob/index]
---

# Iterations — {project_name}

## Track: navy-dominant
- [[2026-04-22-iter-D-home|iter D — first navy attempt]] — picked
- [[2026-04-22-iter-E-home|iter E — product-UI hero]] — on-shelf
- [[2026-04-22-iter-F-home|iter F — before/after comparison]] — on-shelf

## Track: mobile-fluid
- [[2026-04-23-iter-A-mobile-baseline|iter A — mobile baseline]] — drafting

## Loose (no track)
- [[2026-04-15-iter-X-experiment|iter X — quick experiment]] — parked
```

Sorting within a track is chronological. Tracks themselves are listed in order of most recent activity.

### 8.6 Brief integration

`coding` and `plugin` briefs gain an optional `## ITERATIONS` block (added to the type-shaped templates in §5). Empty/omitted by default; auto-populated by bridge with a single wikilink to `iterations/_index.md` when the first iteration is created. Non-iterating projects keep clean briefs.

### 8.7 Auto-linking

- Iteration `project:` frontmatter links back to the brief.
- Brief's `## ITERATIONS` block links forward to `iterations/_index.md`.
- `_index.md` aggregates from disk on every `reindex`/`housekeeping`/`dream` pass.
- `supersedes:` and `builds_on:` form an explicit lineage tree; bridge can render it on demand via `/vault-bridge iterations <slug> --tree`.

### 8.8 iteration-shelf plugin integration

The `iteration-shelf` plugin generates HTML iteration boards from a JSON manifest. Bridge supports it without owning its format:

- Bridge provides the canonical write target: `projects/{slug}/iterations/{iteration-folder}/`.
- The breadcrumb file gains an `iterations_path` field so iteration-shelf knows where to drop output:
  ```
  iterations_path=projects/oz-floer/iterations
  ```
- iteration-shelf is responsible for its own `manifest.json` schema and HTML generation. Bridge does not parse or modify it.
- When iteration-shelf writes a `shelf.html` into an iteration folder, bridge's `/dream` recognises it as a valid artefact (no flag for "stray HTML").

### 8.9 Type applicability

`iterations/` is opt-in for **all** project types — bridge does not auto-create it on `create-project`. User runs `/vault-bridge add-iteration` (which creates the folder if missing) or `/vault-bridge add-collection iterations` to scaffold explicitly. Most common use is in `coding`, `plugin`, and `tinkerage` projects; rare in `knowledge`.

---

## 9. Hooks

Three hooks. Each justified by what it injects, nothing more.

### 9.1 `SessionStart` — mandatory vault discovery

Script: `hooks/scripts/session-start-vault.sh`. Configured for matcher `*`, timeout 10s.

Flow:

```
1. Read breadcrumb $CLAUDE_PROJECT_DIR/.obsidian-bridge if it exists.
   Format: KEY=VALUE lines:
     vault_path=/abs/path/to/Claude Cabinet
     vault_name=Claude Cabinet
     project_slug=oz-floer
     linked_at=YYYY-MM-DD

2. If no breadcrumb:
   a. Try $OB_DEFAULT_VAULT env var
   b. Try CLI: `obsidian vault="<known name>" files total` for known vault names
   c. Walk parent dirs of $CLAUDE_PROJECT_DIR for a Home.md with type: vault-home
      (also accept type: cabinet-home for backwards compatibility)
   d. None found → emit ASK_USER_TO_LINK context

3. Detect CLI: `command -v obsidian` and `obsidian version`

4. Read brief frontmatter for project_type if project_slug is known

5. Emit additionalContext block (see § 9.4)
```

Hook **never** blocks the session. If discovery fails, it injects context that strongly steers the model to ask the user to link or create a vault before doing vault-dependent work.

### 9.2 `SessionEnd` — opt-in handoff nudge

Script: `hooks/scripts/session-end-handoff.sh`. Configured for matcher `*`, timeout 5s. Disabled by default; user enables via `OB_SESSION_END_NUDGE=1` env var or settings.

Flow:

```
1. If breadcrumb exists and project is active:
   a. Check $CLAUDE_PROJECT_DIR/.remember/remember.md mtime
   b. Check {vault}/projects/{slug}/_handoff.md mtime
   c. If remember.md is newer (or _handoff.md missing) and remember.md exists:
      Emit: "remember.md updated since last handoff — run /vault-bridge handoff sync to mirror."
2. Otherwise: silent.
```

### 9.3 `UserPromptSubmit` — only when not yet linked

Inline command in `hooks.json`, no script. Injects a short reminder if `.obsidian-bridge` does not exist in `$CLAUDE_PROJECT_DIR`. Goes silent (no injection) once the breadcrumb is present. Avoids per-prompt cost in the steady state.

### 9.4 Context budget

Bridge holds a hard cap on injected context. Approximate token counts:

**Vault linked (~300 tokens):**

```
## Obsidian Bridge

- Vault: `Claude Cabinet` at `/Users/.../Claude Cabinet` (CLI: yes)
- Project: `oz-floer` (type: coding) — status: active

Decisions: `projects/oz-floer/decisions/YYYY-MM-DD-{slug}.md`
Sessions: `projects/oz-floer/sessions/YYYY-MM-DD.md`
Root docs require `type: doc` frontmatter.
Standards: `obsidian-bridge/references/vault-standards.md` (read on demand).
```

**Vault not linked (~150 tokens):**

```
## Obsidian Bridge — Not Linked

No vault linked to this session. Before vault-dependent work, ask the user
to run `/vault-bridge connect <path>` or `/vault-bridge create`. Do not
fabricate vault paths or invent a layout.
```

The full schema (`vault-standards.md`) is **not** preloaded — model reads it when first writing to the vault that session.

---

## 10. Vault primitives — `vault.*` layer

Defined in `references/vault-integration.md`. Single abstraction that resolves CLI vs filesystem at call time:

```
FUNCTION vault.<op>(args):
    IF cli_available() AND op is supported by CLI:
        RUN obsidian CLI command
    ELSE:
        RUN filesystem equivalent
```

### CLI-first hard rule

Bridge prefers CLI for **every** op the CLI supports. Reasons (preserved from cabinet's policy):

- Wikilinks in frontmatter are recognised natively by Obsidian's parser.
- `property:set` writes frontmatter without re-parsing the file.
- `move` and `rename` trigger Obsidian's automatic internal-link updater.
- `search` uses Obsidian's index — vault-aware, faster.
- `backlinks` and `tags` return live graph data.
- No manual YAML parsing, no fragile regex.

### Operations

**CLI + filesystem (both supported):**
- `vault.read(path)`
- `vault.write(path, content)` — overwrite, creates parent dirs
- `vault.append(path, content)`
- `vault.search(query, folder?)` / `vault.search_context(query, folder?)`
- `vault.exists(path)`
- `vault.list(dir)`

**CLI-exclusive (filesystem fallback degrades to best-effort):**
- `vault.property_read(path, name)` — fallback: parse YAML
- `vault.property_set(path, name, value)` — fallback: rewrite YAML and the file
- `vault.backlinks(path)` — fallback: grep `[[{filename}]]`
- `vault.tags(path?)` — fallback: parse frontmatter + grep
- `vault.move(from, to)` / `vault.rename(from, new_name)` — fallback: filesystem move + manual link rewrite (lossy)

### CLI detection

```bash
command -v obsidian >/dev/null 2>&1 && obsidian version 2>/dev/null
```

Bridge stores `vault.mode = "cli" | "filesystem"` in the breadcrumb after first successful op. Re-detection happens only on next SessionStart.

### Graceful degradation

If CLI was selected but a CLI op fails mid-session (e.g., Obsidian closed), bridge attempts filesystem fallback transparently for that op, logs once, and continues.

---

## 11. Breadcrumb file — `.obsidian-bridge`

Plain `KEY=VALUE` text file in the working directory. Written by `/vault-bridge connect` or `/vault-bridge link`. Default `.gitignore` line added.

```
vault_path=/Users/tom/Library/Mobile Documents/iCloud~md~obsidian/Documents/Claude Cabinet
vault_name=Claude Cabinet
project_slug=oz-floer
linked_at=2026-04-30
mode=cli
```

Cabinet's `.cabinet-anchor-hint` is a similar idea. Bridge reads its own breadcrumb first; if absent, falls back to `.cabinet-anchor-hint` (forward-compatible). Cabinet should be updated to also read `.obsidian-bridge`. Both files may coexist during the cabinet refactor.

---

## 12. `/vault-bridge` command surface

The skill body lives in `skills/vault-bridge/SKILL.md`; `commands/vault-bridge.md` is a thin wrapper.

```
/vault-bridge create [path]                     Scaffold new v3 vault at path or prompt
/vault-bridge connect <path>                    Point at existing vault; write breadcrumb
/vault-bridge link <slug>                       Set CWD breadcrumb to <slug> (switch project)
/vault-bridge create-project <slug> <type>      Scaffold project with type-shaped layout
/vault-bridge add-collection <name>             Add sub-collection folder + _index.md to current project
/vault-bridge sync                              Write/update current project's brief from session context
/vault-bridge status                            Vault summary + per-project counts + drift teaser
/vault-bridge archive <slug>                    Move project → archive/
/vault-bridge unarchive <slug>                  Restore archive/ → projects/
/vault-bridge reindex                           Rebuild all _index.md files from disk
/vault-bridge housekeeping                      Full consistency check, auto-fix safe items
/vault-bridge migrate                           v2 → v3 walkthrough (cabinet vaults)
/vault-bridge handoff sync                      Mirror .remember/remember.md → _handoff.md
/vault-bridge handoff status                    Show last sync time + drift
/vault-bridge set-type <slug> <type>            Change project_type post-hoc (re-scaffolds folders)
/vault-bridge templates [list|print <name>]     List/print available templates

# Iteration commands (see §8):
/vault-bridge add-iteration <id> <slug> [--track <name>] [--with-folder]
                                                Create iteration in current project
/vault-bridge add-iteration-artefact <iter-id> <file>
                                                Promote .md to folder; move file in
/vault-bridge iterations [<slug>] [--tree]      List + group by track + status; --tree shows lineage
/vault-bridge iteration-set-status <iter-id> <status>
                                                Change status; if "picked", offers to mark siblings "superseded"
```

### Behavior notes

**`create-project` requires both `<slug>` and `<type>`.** Bridge asks if either omitted. Slug is validated against the slug rule (§6); user is offered a corrected slug if invalid.

**`status` includes:**
- Vault path, mode (CLI/filesystem), schema version
- Per-project: status, project_type, decision count, session count, last session date, drift flags (none / N issues — see /dream)
- Cabinet detection: "Cabinet detected — `crew/` folder present, untouched by bridge"
- Remember detection: "Remember plugin: detected — last handoff sync: {date}"

**`housekeeping` runs all the structural checks from §17** and offers auto-fix. Less personality than `/dream`, more thorough on auto-fixable items.

---

## 13. `/dream` — two-pass cleanup

Lives in `commands/dream.md` + `skills/dream/SKILL.md`. Bridge owns it; cabinet's old `commands/dream.md` is deleted.

### Pass 1 — Structural sanitation (bridge-native)

Scans current project (or `--vault-wide` for all):

| Check | Action |
|---|---|
| Empty project folder | Flag; offer to archive or delete |
| Project missing `brief.md` | Flag; offer to scaffold from template |
| Slug shape violation (dots, spaces, uppercase) | Flag; offer to rename via CLI (link-update aware) |
| Collection folder without `_index.md` | Flag; offer to create from template |
| `_index.md` out of sync with disk | Flag; offer to rebuild |
| File without frontmatter | Flag; offer to add from template |
| File with malformed/incomplete frontmatter | Flag; offer to repair |
| Broken wikilink (target missing) | Flag; suggest closest match or removal |
| Markdown-style links inside vault (`[text](path)`) | Flag; offer wikilink replacement |
| Tag clutter (single-use, near-duplicate, vague) | Flag; suggest consolidation |
| Stale `updated:` on active project (>90d) | Flag; offer to refresh or change status |
| Decision filename not `YYYY-MM-DD-{slug}.md` | Flag; offer to rename |
| Session filename not `YYYY-MM-DD.md` | Flag; offer to rename or merge |
| Root-of-project doc without `type: doc` frontmatter | Flag; offer to add |
| Emergent iteration folder (`design-iterations/`, `surfaces/`, `aesthetics/`) | Flag; offer to canonicalise to `iterations/` (CLI move with link rewrite) |
| Iteration with `status: drafting` >30d | Flag; ask whether to park, finish, or reject |
| Track with one `picked` iteration but siblings not `superseded` | Flag status drift; offer to set siblings to `superseded` |
| Broken `supersedes:` / `builds_on:` link | Flag; suggest closest match or removal |
| Iteration filename not `YYYY-MM-DD-iter-{id}-{slug}.md` | Flag; offer to rename |
| `iterations/_index.md` out of sync | Auto-fix; rebuild from disk |

### Pass 2 — Content analysis (preserved from cabinet's OG dream)

| Check | Action |
|---|---|
| Contradictory decisions | Report only — user decides |
| Stale info (active decision >30d, unreferenced) | Report only |
| Dangling scopes (parking lot items never revisited) | Report only |
| Unacted decisions (consequences never implemented) | Report only |
| Documentation gaps (sessions with no decisions; brief missing core sections) | Report only |

### Output

Default: in-chat structured report with wikilinks. Format:

```markdown
# Dream Report — {project_name}
*{DATE}*

## Structural — Auto-fixable (X items)
1. ...
2. ...
[Fix all] [Pick] [Skip]

## Structural — Needs decision (X items)
- ...

## Content — Findings (X items)
### Contradictions
- ...
### Stale info
- ...
### Dangling scopes
- ...
### Unacted decisions
- ...
### Documentation gaps
- ...
```

### Take-the-lead behavior

For Pass 1 auto-fixable items, bridge offers `Fix all (N)` / `Pick` / `Skip`. "Fix all" runs corrections sequentially, prompting only on destructive ops (archive/delete/rename-with-link-rewrite). Pass 2 items are **never** auto-actioned — bridge proposes, user decides.

### Persistence — opt-in `--save`

`/dream --save` writes the report to `projects/{slug}/dreams/YYYY-MM-DD.md` with `type: dream-report` frontmatter. Auto-creates `dreams/_index.md` if missing on first save. Matches the empirically-observed pattern in `tegenlicht-controls/dreams/`.

### Personality layer

When cabinet is installed and we're inside a `/cabinet` session, the chronicler voice (Bostrol/Kevijntje/Jonasty) wraps the report. Implementation: cabinet detects `/dream` invocations during its session and reformats the in-chat output. Bridge's `/dream` is dry without cabinet — no personality, no flair, just the report.

### Token budget

`/dream` is the hungriest command. Mitigations:

- Read frontmatter first; full body only when needed for content checks.
- Summarise findings as the scan proceeds; don't accumulate then dump.
- Target: full project dream in <5 minutes wall time.
- `--vault-wide` is opt-in; default scope is current project.

---

## 14. Cabinet contract + stale flag

### What gets removed from cabinet

- `cabinet-of-imd/skills/vault-bridge/` — folder deleted.
- `cabinet-of-imd/commands/dream.md` — file deleted.

### What gets stale-marked but not removed

- `cabinet-of-imd/references/vault-integration.md` — top banner: `> **STALE.** Superseded by `obsidian-bridge/references/vault-integration.md`. Cabinet refactor pending.`
- `cabinet-of-imd/references/vault-standards.md` — same banner.
- `cabinet-of-imd/references/obsidian-setup.md` — same banner.
- `cabinet-of-imd/examples/vault-templates/` — same banner in a top-level `STALE.md` inside the folder.

### Light edits

- `cabinet-of-imd/.claude-plugin/plugin.json`: bump `version` to `2.3.0`. Append to description: `(Vault structure & /dream now owned by obsidian-bridge plugin — cabinet refactor pending.)`
- `cabinet-of-imd/README.md`: short banner at top with the same message + link to `obsidian-bridge`.
- `cabinet-of-imd/CHANGELOG.md`: new entry: `v2.3.0 — Vault structure & /dream extracted to obsidian-bridge plugin. Cabinet's /vault-bridge skill and /dream command removed. Cabinet's vault refactor pending; existing v2 vault behavior preserved as deprecated path.`
- `cabinet-of-imd/commands/cabinet.md` step 1.5 ("Vault Check"): replace existing detection with: "If `obsidian-bridge` plugin is installed, defer to its discovery. Otherwise use cabinet's existing v2 vault discovery (deprecated path)."
- `cabinet-of-imd/commands/cabinet.md` references list: keep loading `references/vault-integration.md` and `vault-standards.md` **only when bridge is not installed** (cabinet's deprecated fallback path). When bridge is installed, cabinet loads bridge's references instead and skips its own stale ones.

### What keeps working — and what drifts

- Cabinet's hooks (`boot-flair`, `save-anchor`, `session-close`) — read bridge's `.obsidian-bridge` breadcrumb first, fall back to `.cabinet-anchor-hint` for backward compatibility.
- Cabinet's `crew/` files — entirely cabinet-owned. Bridge knows they exist; never modifies them.
- Cabinet's covert writes (decisions, sessions, chatter) keep using cabinet's v2 schema — `#cabinet/*` tags, `## Overview`/`## Tech Stack`/etc. brief blocks, no `project_type` field. **This is not a strict subset of v3.** A vault with both bridge and unrefactored cabinet active will accumulate mixed-schema entries: post-migration v3 files plus new v2 cabinet writes.
- Bridge tolerates v2 entries — they remain readable and queryable. `/dream` Pass 1 detects them as schema drift (missing `#ob/*` tag, missing `project_type`, wrong brief block headers, etc.) and offers per-file upgrade. Until cabinet is refactored, the user re-runs `/dream` periodically to clean drift, or accepts the dual-schema state. The cabinet refactor is a follow-up spec.

### One-way dependency invariant

Bridge's references and code never name `cabinet-of-imd`. Cabinet's references may name `obsidian-bridge`. Bridge detects cabinet only via observable artefacts:

- Presence of `crew/` folder at vault root.
- Presence of `#cabinet/*` tags or `type: cabinet-home` in `Home.md`.
- Presence of `.cabinet-anchor-hint` in working dirs.

Bridge surfaces cabinet detection in `/vault-bridge status` and adjusts `/dream` to skip `crew/`. That's the entire awareness surface.

---

## 15. Remember plugin integration

Light, opt-in. Bridge does not absorb remember's compression pipeline.

| Direction | Mechanism | Behavior |
|---|---|---|
| remember → vault | `/vault-bridge handoff sync` | Read `$CLAUDE_PROJECT_DIR/.remember/remember.md`, mirror to `{vault}/projects/{slug}/_handoff.md` with `type: handoff` frontmatter. Single file per project, overwriteable. |
| remember → vault (auto) | `SessionEnd` hook (opt-in) | If `remember.md` mtime > `_handoff.md` mtime + active project breadcrumb, emit one-line nudge. |
| vault → remember | n/a | Bridge never writes to `.remember/`. |
| Status surface | `/vault-bridge status` | Shows `Remember plugin: detected — last handoff sync: 2026-04-29` if `.remember/` exists. |

`_handoff.md` lives at `projects/{slug}/_handoff.md` (underscore prefix pins it at top of folder listing). Body content is a verbatim copy of `remember.md` plus a short header noting the source and timestamp.

---

## 16. Migration `/vault-bridge migrate` (v2 → v3)

One-shot opt-in command. Idempotent — re-running on a v3 vault does nothing except re-run housekeeping.

### Steps

```
1. Confirm scope. List projects, count files, explain what changes. Ask "proceed?".

2. Backup. Full file copy → {vault}/.backup-v2-{YYYY-MM-DD}/.
   User can delete after verifying.

3. For each project:
   a. Prompt for project_type. Defaults:
      - Has decisions/ folder → coding
      - Has sources/ folder → knowledge
      - Has releases/ folder → plugin
      - Otherwise → ask user (offer all four)
   b. Brief frontmatter:
      - Add project_type
      - Add aliases: [{slug}] if missing
      - Normalise tags: keep #cabinet/project, add #ob/project, add #type/{project_type}
      - Ensure slug field is present and slug-shape valid
   c. Brief body:
      - Best-effort reformat into v3 block set for that type
      - Preserve all existing content under best-fit blocks (Overview → INTRO,
        Tech Stack → TECHNICAL STACK, Scope → CONSTRAINTS + USER DECISIONS, etc.)
      - Empty blocks added explicitly (one-line "TBD" placeholder)
   d. Slug repair: if slug has dots/spaces/uppercase, offer rename via CLI move
      (auto link-update). User confirms each.

4. For each collection folder (decisions/, notes/, tasks/, references/, sources/,
   releases/, dreams/, iterations/, plus any custom):
   a. Add _index.md if missing (from template)
   b. Rebuild _index.md content from folder contents

5. For emergent iteration-pattern folders (design-iterations/, surfaces/, aesthetics/):
   a. Detect and prompt user to canonicalise → iterations/
   b. On confirm: CLI move with link rewrite, frontmatter type: design-iteration → iteration,
      tag cabinet/design-iteration → ob/iteration (keep both during transition),
      preserve all custom fields (register, identifier, status, etc.)
   c. On decline: leave folder as-is, mark as user-defined collection

6. For root-level singleton docs (STANDARDS.md, MANIFESTO.md, CHANGELOG.md, etc.):
   - Add type: doc frontmatter where missing (preserve body)

7. Update Home.md frontmatter:
   - If type: cabinet-home, change to type: [vault-home, cabinet-home]
   - If only type: cabinet-home and cabinet not detected, change to type: vault-home

8. Run housekeeping pass — auto-fix all safe items.

9. Write breadcrumb files in any working dirs known via $OB_DEFAULT_VAULT
   or detected via cabinet's old hint files.

10. Report summary: changed N files, skipped M, drift remaining: [...]
```

### Heuristic mapping for brief body

| v2 section | v3 block (for `coding`) |
|---|---|
| `## Overview` | `## INTRO` |
| `## Tech Stack` | `## TECHNICAL STACK` |
| `## Scope` (and sub-headers) | Split — `## CONSTRAINTS` for limits, `## USER DECISIONS` for in/out choices |
| `## Conventions` | `## TECHNICAL STACK` (appended) or `## CONSTRAINTS` |
| `## Team Notes` | `## WORK NOTES` |
| anything else | `## WORK NOTES` |

Migration preserves original content verbatim under best-fit headers. User reviews and reorganises post-migration if they want.

### Re-runnability

Re-running `/vault-bridge migrate` on a vault that has already been migrated:
- Detects `project_type` already set → no prompts for that project.
- Brief body already in v3 shape → no reformat.
- All `_index.md` present → no creation.
- Effectively becomes `housekeeping`.

---

## 17. Housekeeping checks (full list)

Run by both `/vault-bridge housekeeping` and `/dream` Pass 1. Each is auto-fixable except where noted.

| Check | Auto-fixable? |
|---|---|
| Empty project folder | Manual — archive vs delete |
| Project missing `brief.md` | Yes — scaffold from template |
| Slug shape violation | Manual — rename with CLI link-update |
| Collection folder missing `_index.md` | Yes — create from template |
| `_index.md` out of sync | Yes — rebuild from disk |
| File missing frontmatter | Yes — add minimal valid frontmatter |
| Frontmatter malformed/incomplete | Yes — repair required fields |
| Broken wikilink | Manual — suggest closest match |
| `[text](path)` markdown link inside vault | Yes — replace with wikilink |
| Tag clutter | Manual — suggest consolidation |
| Stale `updated:` (>90d active) | Manual — refresh or change status |
| Decision filename pattern violation | Yes — rename |
| Session filename pattern violation | Yes — rename or merge same-day |
| Iteration filename pattern violation | Yes — rename |
| Iteration `status: drafting` >30d | Manual — park, finish, or reject |
| Iteration track has `picked` but siblings not `superseded` | Yes — auto-set siblings to `superseded` after confirmation |
| Broken `supersedes:` / `builds_on:` link | Manual — suggest closest match |
| Emergent iteration folder (`design-iterations/`, `surfaces/`, `aesthetics/`) | Manual — offer to canonicalise to `iterations/` |
| Root-of-project doc missing `type: doc` | Yes — add frontmatter |
| Brief body missing required block headers for type | Yes — add empty block |

---

## 18. Open questions (defer to plan)

None blocking. Items the implementation plan will need to handle:

- **Tag normalisation across cabinet/ob namespaces during migration.** Plan should specify the exact dual-tag policy: keep both, prefer one, or sunset cabinet/ tags after a grace period?
- **Session-anchor relocation.** Cabinet's `projects/{slug}/.anchor.json` is cabinet-private. Bridge does not touch it. Confirm in plan.
- **Cabinet's `crew/scrapbook/questions.md`** (referenced in boot-flair) — entirely cabinet-owned, untouched by bridge. Confirm in plan.
- **CLI command syntax verification.** Spec assumes Obsidian CLI 1.12+ command set as documented in cabinet's `vault-integration.md`. Plan should add a "verify CLI commands work as documented" task before primitive implementation.

---

## 19. Out of scope

- Refactoring cabinet to use bridge's primitives directly. Cabinet keeps its v2 code path; the refactor happens later as a separate spec.
- Cross-vault dream (multi-vault analysis).
- Vault sync (Git, Obsidian Sync, iCloud) — out of bridge's responsibility.
- Non-Obsidian markdown vault support.
- A web UI or visual MOC builder.
- Auto-tagging or auto-classification of project content.

---

## 20. Testing & validation strategy (rough)

The implementation plan will detail tests. High-level:

- Unit-level: each `vault.*` primitive has CLI + filesystem implementation parity tests.
- Integration: full migration on a copy of the user's existing vault → diff-check before/after → verify no data loss.
- Hook: SessionStart with breadcrumb, without breadcrumb, with stale breadcrumb, with broken vault path.
- `/dream` Pass 1: synthetic vault with each drift type → verify each is detected and fixable.
- `/dream` Pass 2: verified against cabinet's OG dream test cases.
- Cabinet coexistence: install both plugins → run cabinet session → verify cabinet writes land cleanly in v3 vault.
- Cabinet absence: install bridge only → run `/vault-bridge` ops → verify nothing references or assumes cabinet.

---

## 21. Implementation phasing (rough — full plan to follow)

Suggested order, to be detailed in `writing-plans` step:

1. Plugin scaffold + manifest + marketplace registration.
2. References (`vault-standards.md`, `vault-integration.md`, `obsidian-setup.md`, `remember-integration.md`).
3. Templates (all 13 in `examples/vault-templates/`).
4. `vault.*` primitives layer (CLI + filesystem).
5. `SessionStart` hook + breadcrumb file.
6. `/vault-bridge` skill: `create`, `connect`, `link`, `create-project`, `status`.
7. `/vault-bridge`: `sync`, `add-collection`, `archive`, `unarchive`, `reindex`.
8. `/vault-bridge housekeeping` (full check list).
9. Iteration support: `add-iteration`, `add-iteration-artefact`, `iterations`, `iteration-set-status`; iteration template + `_index.md` rendering by track + brief `## ITERATIONS` auto-population.
10. `/dream` skill — Pass 1 (structural, includes iteration checks).
11. `/dream` skill — Pass 2 (content, ported from cabinet).
12. `/vault-bridge migrate` — v2 → v3 walkthrough (includes iteration folder canonicalisation prompt).
13. `SessionEnd` hook + `/vault-bridge handoff sync`.
14. Cabinet stale-flag edits + cabinet hook updates to read bridge breadcrumb.
15. iteration-shelf plugin coordination: breadcrumb `iterations_path` field, write-target documentation.
16. End-to-end test on user's actual vault (full migration dry run + verification, including the `tf-renewal/design-iterations/` canonicalisation flow).
17. README, CHANGELOG, plugin.json polish.

---

*End of spec.*
