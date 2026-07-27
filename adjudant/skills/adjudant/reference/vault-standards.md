# Vault Standards

Canonical schema, naming, folder rules, and wikilink form for any Adjudant-managed vault. Single source of truth — every vault write must conform. `validate.py` enforces; `/adjudant dream` reports drift.

---

## 1. Frontmatter

Every vault file has YAML frontmatter. No exceptions except `Home.md` (which only needs `type` + `updated`).

- Standard YAML — no Obsidian-specific syntax inside frontmatter values except wikilink-valued fields (a decision's `supersedes`, piped wikilinks).
- Dates: ISO `YYYY-MM-DD` for date-only; full ISO 8601 for timestamps.
- Strings with special characters (colons, brackets) must be quoted.
- Empty optional fields: **omit the key entirely** rather than `null` or empty string.
- Arrays use YAML list syntax, not inline `[]` (exception: empty arrays use `[]`).

### Project membership

Project membership is the folder path (`projects/[zone/]slug/…`), never a frontmatter field.

The historical `project:` field (a piped wikilink to the brief, retired v0.16.0) duplicated the
path on every note and drifted whenever a project moved zones. Existing files still carrying it
are unknown-field drift: `check` reports them, `tidy` strips them after preview. The Obsidian
graph backlink flows through each folder's `_index.md` instead.

### Session traceability — `session_id` / `source_session`

Every vault write made during a Claude Code conversation is stamped so the
conversation that produced it is one wikilink hop away — not a grep through
`~/.claude/projects/**/*.jsonl`.

- **`session_id:`** (list, on session notes only) — every Claude Code
  conversation UUID that touched that day's session note. Stamped by the
  `SessionStart` hook on create and idempotently appended on resume.
  Empty list (`session_id: []`) is fine and the canonical initial state.

  ```yaml
  session_id:
    - 2ada03ff-687f-4a82-9e1f-1234567890ab
    - 7b1c5e2d-4f93-4cba-9e02-fedcba987654
  ```

- **`source_session:`** (scalar, optional, on decisions / notes / docs /
  sources / releases / iterations / dream-reports) — the conversation UUID
  that authored the file. Stamped by the `PostToolUse` hook when a new file
  appears under the project. Optional and omit-if-absent per the rule above.

  ```yaml
  source_session: 2ada03ff-687f-4a82-9e1f-1234567890ab
  ```

`_handoff.md`, `_index.md` / `_index-*`, `_iteration.md`, and session notes
themselves are excluded from `source_session` stamping — they're system-managed
or aggregate, so "which conversation authored this" doesn't apply.

**Honest caveat.** Claude Code transcripts under `…-private-tmp/` are
ephemeral, and `$HOME` can change across machines — so the stored UUID is a
*pointer that can dangle*. That is by design: a dangling pointer still tells
you which session and roughly when. The decision's *content* must land in the
vault; the UUID is for retracing reasoning, not a substitute for capturing
the conclusion.

---

## 2. Tag schema (locked 2026-05-25)

**Bare tags only — no prefix.** Adjudant does not namespace its tags.

### A. File-type tags (mandatory, one per file)

`#decision`, `#session`, `#note`, `#doc`, `#project`, `#handoff`, `#index`, `#iteration`, `#release`, `#source`, `#dream-report`, `#task`

`Home.md` is the lone exception — uses `type: vault-home` frontmatter, no tag.

### B. Project-specific custom file types

`#recon-item`, `#portal-concept`, `#preview`

Migrate from `cabinet/recon`, `cabinet/portal-concept`, `cabinet/preview` respectively during `/adjudant ramasse`.

### C. Topical tags (optional, queryable, sparingly)

Allowed topical clusters:

`#content/seafood-companies`, `#content/blog`, `#content/page`, `#content/hardware`, `#content/personnel`, `#content/videos`, `#content/workflows`, `#content/features`

Other topical tags allowed only if they meet all three criteria: namespaced (`category/value` form), queryable (you'd actually filter on it), used across ≥3 files.

### D. Deprecated / forbidden

- `#ob/*` (all) — replaced by bare equivalents
- `#cabinet/*` — cabinet sunset; file-type variants migrate to Bucket B, others drop
- Project-slug tags (`#dutchbc-poc`, `#hubspot-nightly`, etc.) — project membership is the folder path
- Vague topicals: `#architecture`, `#frontend`, `#cms`, `#toolbox`, `#moc`, `#scheduler`, `#campaign-request`, `#flow-c`, `#nightly`, `#hubspot`
- Crew names: `#bostrol`, `#kevijntje`, `#henske`, `#jonasty`

### E. Project-kind classification

NOT a tag. Lives in the `project_type:` frontmatter field on the brief. Values: `coding | knowledge | plugin | tinkerage`.

### Non-tag

`cssclasses: cabinet-sidecar` in frontmatter is an Obsidian CSS class, NOT a tag. Leave untouched.

---

## 3. File-type schemas

See `templates/*.md` for the canonical frontmatter shape of every file type. Validators check actual files against templates.

### File-type list (12 + `vault-home`)

| Type | Template | Body shape |
|---|---|---|
| `project` | `project-brief-{project_type}.md` | per-type body sections |
| `decision` | `decision.md` | `## Decision` / `## Context` / `## Consequence` |
| `session` | `session.md` | intent quote + `## Log` (append-only) |
| `note` | `note.md` | free-form |
| `doc` | `doc.md` | purpose sentence + `## {Section}` |
| `handoff` | `handoff.md` | sync-managed body |
| `source` | `source.md` | `## Key Points` / `## Notes` / `## Relevance` |
| `iteration` | `iteration.md` (folder index) | a **folder** of build artefacts (HTML tryouts, experiments, superpowers); the optional `_iteration.md` is a human-facing index of the folder's contents |
| `release` | `release.md` | `## Changes` |
| `dream-report` | `dream-report.md` | auto-populated by `/adjudant dream` |
| `task` | `task.md` | `## Task` / `## Notes` |
| `index` | `_index-projects.md` or `_index-collection.md` | table or list |
| `vault-home` | `home.md` | sections per template |

### Doc vs Decision (the most common mix-up)

| If… | It's a |
|---|---|
| Filename has a date prefix | **Decision** |
| Says "what's true now / how X works" | **Doc** |
| Says "we picked X over Y because Z" | **Decision** |
| Will be rewritten as understanding evolves | **Doc** |
| Append-only history of a moment | **Decision** |
| Lives in `decisions/` subfolder | **Decision** |
| Lives at project root or in `docs/` | **Doc** |

Quick test: "When was this decided?" — clear answer = decision; "it's just how we do things" = doc.

---

## 4. Naming rules

| Item | Pattern | Enforcement |
|---|---|---|
| Project slug | lowercase, hyphenated, no spaces, no dots (`dff2026-web`) | strict |
| Brief | `brief.md` | strict |
| Decision | `{YYYY-MM-DD}-{kebab-title}.md` | strict |
| Session | `{YYYY-MM-DD}.md` (one per project per day; append on resume) | strict |
| Note | `{kebab-title}.md` (no date unless time-relevant) | strict |
| Task | `{kebab-title}.md` (lives in `tasks/`) | strict |
| Source | `{kebab-title}.md` | strict |
| Release | `v{X.Y.Z}.md` | strict |
| Iteration (folder) | `iterations/{YYYY-MM-DD}-iter-{id}-{kebab-slug}/` — holds the artefacts (HTML, etc.); optional `_iteration.md` index inside | strict |
| Dream report | `{YYYY-MM-DD}.md` | strict |
| Doc | `{NAME}.md` — **UPPERCASE** (e.g. `STANDARDS.md`, `MANIFESTO.md`) | strict |
| Handoff | `_handoff.md` | strict |
| Index | `_index.md` | strict |
| `.canvas` artefact | `{kebab-name}.canvas` | strict |
| `.base` artefact | `{kebab-name}.base` | strict |

"References" is not a distinct file type — files in `references/` subfolders use `type: doc`, `type: note`, or `type: source` based on their content shape.

### Task frontmatter

Canonical shape (see `templates/task.md`):

```yaml
type: task
status: todo        # todo | doing | review | blocked | done | icebox
category: ""        # optional: board colour group
code: ""            # optional: short card id cross-linking specs, handoffs, commits
related: []
note: ""
tags:
  - task
```

`status:` on a task note takes exactly one of: `todo` | `doing` | `review` | `blocked` | `done` | `icebox`. Aliases are accepted on input and normalized by the board; the full alias table (mirrors `board.py` `STATUS_TO_COLUMN`):

| Alias | Board column |
|---|---|
| `backlog`, `todo`, `planned`, `proposed` | `backlog` |
| `next`, `ready`, `queued` | `next` |
| `doing`, `in-progress`, `in_progress`, `active`, `wip` | `doing` |
| `review`, `blocked`, `in-review` | `review` |
| `done`, `complete`, `completed`, `implemented`, `shipped`, `accepted` | `done` |
| `icebox`, `deferred`, `parked`, `shelved`, `someday` | `icebox` |

---

## 5. Folder structure

### Per-`project_type` defaults

| Type | Subfolders with `_index.md` | Subfolders without `_index.md` |
|---|---|---|
| `coding` | `decisions/`, `notes/`, `tasks/`, `references/` | `sessions/`, `images/` |
| `plugin` | coding + `releases/` | `sessions/`, `images/` |
| `knowledge` | `notes/`, `sources/`, `references/` | `sessions/` |
| `tinkerage` | (none by default) | `sessions/` (optional) |

### Extensions beyond defaults

Custom subfolders must be declared in the project brief's frontmatter:

```yaml
extra_folders:
  - content-recon
  - design-iterations
  - design-system
```

Anything actually present under the project but not in (defaults ∪ `extra_folders`) is **drift** — flagged by `/adjudant dream`.

### Auto-created

- `dreams/` — created when the dream flow writes its phase-3 report. Not in defaults.
- `canvases/`, `bases/` — created on first `/adjudant draw canvas/base` invocation if not in defaults.
- `board/`: created by `/adjudant board`, or born automatically on the first task note (holds the deck JSON plus the rendered board.html). Not in defaults.

### The `_index.md` rule

Every folder under a project (or at vault root) that holds ≥2 sibling `.md` files of the same conceptual type gets an `_index.md`.

**Exceptions:** `sessions/` (chronological ordering is the index), `images/`, `assets/`, `previews/`, and `iterations/` plus the iteration folders inside it (non-text / build artefacts — HTML tryouts, experiments; the optional `_iteration.md` is the only conformant file, and artefacts carry no frontmatter).

**Index shape:** `# {Collection Name}`, one-line description, `## Entries` with wikilinks. Chronological where dates are in filenames; alphabetical otherwise. `/adjudant tidy` rebuilds these mechanically (ramasse only detects gaps).

---

## 6. Wikilink rules

All vault-internal links use `[[note-name]]` form.

**Markdown-style links `[text](path)` are allowed if and only if `path` does NOT resolve to a vault `.md` file.** External code references, heading anchors (`#section`), and links to non-vault files are fine in markdown form.

| Context | Form |
|---|---|
| Body → brief | `[[projects/{slug}/brief\|{display}]]` |
| Body → decision | `[[projects/{slug}/decisions/{file}\|{short title}]]` |
| Body → session | `[[projects/{slug}/sessions/{date}\|{date}]]` |
| Body → source | `[[projects/{slug}/sources/{file}\|{author, year}]]` |
| Image embed | `![[image.png]]` with caption line below |

Briefs always carry `aliases: [{slug}]` so bare `[[my-project]]` resolves cleanly.

---

## 7. Content style

Body copy is **actionable, clear, unambiguous, and short**. Style is judgment, not mechanically enforced — `/adjudant dream` flags suspected style violations for human review (banned generic-AI-fluff terms, em dashes overused, three-word taglines, etc. — full list in the global voice rules, not duplicated here).

---

## 8. Project status and zones (locked 2026-07-16)

`status:` on a brief takes exactly one of: `active` | `stale` | `fridge` | `done` | `dead` | `seed`.

- `active`: being worked
- `stale`: declared active but quiet past `stale_after_days` (the only machine-suggested state)
- `fridge`: deliberately paused, intent to return
- `done`: shipped and complete (a success, not an abandonment)
- `dead`: abandoned
- `seed`: captured idea, not yet started

Physical placement follows status:

| Zone | Holds |
|---|---|
| `projects/` | active, stale, seed |
| `projects/_fridge/` | fridge |
| `projects/_archive/` | done, dead |

Transitions run through `/adjudant shelf` (two-phase preview/apply): brief frontmatter,
a dated `## Status log` line (newest first), the zone folder move, a vault-wide
`[[projects/...]]` prefix rewrite, and a `projects/_index.md` row refresh. Full-path
wikilinks into a project therefore survive zone moves; the `[[{slug}/brief\|{slug}]]`
index-row form resolves across zones by Obsidian suffix matching and is never rewritten.
Machines suggest only along the active/stale axis; `fridge`, `done`, `dead`, `seed`
are deliberate, user-set states. Breadcrumb key `stale_after_days:` (default 30)
tunes the staleness threshold per project.

---

## 9. Decision status vocabulary (locked 2026-07-27)

`status:` on a decision note takes exactly one of:
`active` | `superseded` | `reversed` | `implemented` | `deferred`.

- `active`: in force, guiding work
- `superseded`: replaced by a newer decision (name it in `supersedes:` on the successor)
- `reversed`: undone without a replacement
- `implemented`: the decided work has shipped; the record is historical
- `deferred`: parked with intent to revisit; not in force, not rejected

Wild historical values (`accepted`, `locked`, `current`) are synonyms of `active`:
`check` reports them as off-vocabulary, `tidy` migrates them after preview. The
machine-readable source of truth is `_vault_walk.DECISION_STATUS_VALUES`; the enum
comment in `templates/decision.md` and this section are held to it by validator 28.
