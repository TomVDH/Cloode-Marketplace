# Vault Standards

Canonical schema, naming, folder, and wikilink form for any Adjudant-managed vault. Every vault write must conform.

## What enforces what

Each rule states its shape once. Detail enforced mechanically is not restated:

| rule area | enforcer |
|---|---|
| frontmatter keys per type | the type's template, parsed by `_template_schema.py` into `FIELD_SCHEMA`; convention in `templates/README.md`; the PreToolUse gate; `tidy` feature 4 repairs |
| status vocabularies | the `status:` line's trailing `# a | b | c` comment in each template; the board's read aliases are declared in `board.py` `STATUS_TO_COLUMN` |
| wikilink form | `tidy` feature 3 |
| folder shape, some file naming | `ramasse_scan` detectors |

The parity validators are gone. They held this document, the templates and a set of `_vault_walk.py` constants to each other, a question that only exists while a rule is written down twice. The template is the one declaration now.

Caught at write time: a `Write` missing a required field, or setting both `type:` and `node_type:`, is blocked; an unknown field passes, for `tidy` to strip. The gate ignores `Edit`s and status values; its skip list is internals.md detail. Everything else is reported after the fact or is judgment.

## 1. Frontmatter

Every file has YAML frontmatter. Legal keys are the type's template: no trailing comment means required, `# optional` means optional, anything else is drift. Form rules, unenforced: standard YAML, no Obsidian syntax inside values except wikilink fields such as `supersedes`; ISO `YYYY-MM-DD` for dates and full ISO 8601 for timestamps; quote any string containing a colon or bracket; omit an empty optional key rather than writing `null` or `""`; write arrays as YAML lists, not inline, though an empty array is `[]`.

Project membership is the folder path (`projects/[zone/]slug/…`), never a frontmatter field: the retired `project:` field (dropped v0.16.0) duplicated the path on every note and drifted whenever a project changed zones. The graph backlink flows through each folder's `_index.md` instead.

`session:` holds the Claude Code conversation id behind a write, optional on the kinds whose template lists it and hook-stamped rather than hand-written. A stored id may dangle (transcripts are ephemeral): it retraces reasoning, never holds the conclusion, so a decision's content must land in the vault. The pre-v3 `session_id:` and `source_session:` are fields on no type; `tidy` strips them.

## 2. Tags (retired v3)

No template declares `tags:`, so a `tags:` block is an unknown field: the write gate lets it through, `check` reports it, and `tidy` feature 4 strips it. Nothing adjudant writes carries one.

The retired scheme mandated exactly one tag per file restating that file's own `type:`, policed by four bucket constants, two classifiers, a normaliser and a validator. A tag that repeats a field carries no information, and the nested topical form the buckets existed to police was never enforced anywhere. Inline `#tags` in body prose are yours; nothing reads or rewrites them. `cssclasses:` was never a tag and is unaffected.

## 3. File-type schemas

A template's kind is its `type:`, not its filename: `brief.md` is `project`; `home.md` and `index-project.md` are both `index`. Body shape is not machine-checked. Decision: `## Why` / `## Consequence`. Session: a closing summary line, then `## Log`. Doc: purpose sentence + `## {Section}`. Source: `## Key points` / `## Why it matters`. Release: `## Changes`. Task: `## Done when` / `## Notes`. Index: `# {Collection Name}`, one-line description, then `## Entries` of wikilinks, chronological where filenames carry dates and alphabetical otherwise. Note is free-form; the brief writes `## Stack` / `## Constraints` for coding and plugin only. handoff, dream and index are machine-written.

Doc vs decision, the common mix-up. A decision has a date-prefixed filename, lives in `decisions/`, says "we picked X over Y because Z", and is append-only history of a moment. A doc lives at project root or in `docs/`, says "what is true now / how X works", and gets rewritten as understanding evolves.

## 4. Naming rules

Only some names are checked: `ramasse_scan` flags doc and decision date-prefix, doc case, session filename, and `.canvas`/`.base` kebab-case. The rest are on you: decision `{YYYY-MM-DD}-{kebab-title}.md`; session and dream report `{YYYY-MM-DD}.md`, one session per project per day, appended on resume; note, task and source `{kebab-title}.md` with no date unless time-relevant; release `v{X.Y.Z}.md`; doc `{NAME}.md` in **UPPERCASE**; project slug lowercase kebab-case with no spaces or dots (`dff2026-web`); iteration, the folder `iterations/{YYYY-MM-DD}-iter-{id}-{kebab-slug}/` holding the artefacts, with an optional `_iteration.md` inside. `brief.md`, `_handoff.md` and `_index.md` are written for you. "References" is not a file type: files in `references/` take `type: doc`, `note`, or `source` by content shape.

`status:` on a task note takes one of `todo` | `next` | `doing` | `review` | `blocked` | `done` | `icebox`, one per board lane. Aliases are accepted on input and never rewritten; the board maps them to lanes (mirrors `board.py` `STATUS_TO_COLUMN`), and a card dragged on any board surface writes its lane's canonical status back here:

| Alias | Board column |
|---|---|
| `backlog`, `todo`, `planned`, `proposed` | `backlog` |
| `next`, `ready`, `queued` | `next` |
| `doing`, `in-progress`, `in_progress`, `active`, `wip` | `doing` |
| `review`, `blocked`, `in-review` | `review` |
| `done`, `complete`, `completed`, `implemented`, `shipped`, `accepted` | `done` |
| `icebox`, `deferred`, `parked`, `shelved`, `someday` | `icebox` |

## 5. Folder structure

Defaults per `project_type`. `coding`: `decisions/`, `notes/`, `tasks/`, `references/`, each carrying an `_index.md`, plus `sessions/` and `images/` without one. `plugin`: the coding set plus `releases/`. `knowledge`: `notes/`, `sources/`, `references/` plus `sessions/`. `tinkerage`: `sessions/` only, optional. Anything beyond the defaults must be in the brief's `extra_folders:`; an undeclared folder is ramasse-flagged drift. Auto-created, so exempt: `dreams/`, `canvases/`, `bases/`, `board/`.

Every folder under a project, or at vault root, holding two or more sibling `.md` files of the same conceptual type gets an `_index.md`. Exceptions: `sessions/` (ordering is the index), `images/`, `assets/`, `previews/`, and `iterations/` plus the iteration folders inside it, where build artefacts carry no frontmatter and `_iteration.md` is the only conformant file. `/adjudant tidy` rebuilds indexes mechanically; ramasse only detects the gaps.

## 6. Wikilink rules

All vault-internal links use `[[note-name]]` form. **Markdown-style `[text](path)` is allowed if and only if `path` does NOT resolve to a vault `.md` file.** Heading anchors and non-vault targets are fine in markdown form.

Body links carry the full path and a display alias: `[[projects/{slug}/brief|{display}]]`, `[[projects/{slug}/decisions/{file}|{short title}]]`, and the same shape per zone folder. Images embed as `![[image.png]]` with a caption line below. Briefs carry `aliases: [{slug}]` so a bare `[[my-project]]` resolves cleanly.

## 7. Content style

Body copy is **actionable, clear, unambiguous, and short**. Style is judgment: `dream` flags suspects. The banned-term list lives in `reference/voice.md` and `validate.py`.

## 8. Project status and zones (locked 2026-07-16)

A project's state is one of `active` | `stale` | `fridge` | `done` | `dead` | `seed`, and picking between them is judgment. The zone folder carries it; the brief has no `status:` field, because a second answer can disagree with the first. `active`: being worked. `stale`: declared active but quiet past `stale_after_days` (default 30), the only machine-suggested state. `fridge`: deliberately paused, intent to return. `done`: shipped and complete, a success rather than an abandonment. `dead`: abandoned. `seed`: captured idea, not yet started.

Placement follows status: `projects/` holds active, stale and seed; `projects/_fridge/` holds fridge; `projects/_archive/` holds done and dead. Transitions run only through `/adjudant shelf`, which moves the folder and rewrites `[[projects/…]]` prefixes vault-wide, so full-path wikilinks survive a zone move. The `[[{slug}/brief|{slug}]]` index-row form resolves across zones by Obsidian suffix matching and is never rewritten.

## 9. Decision status vocabulary (locked 2026-07-27)

`status:` on a decision note takes exactly one of `active` | `superseded` | `reversed`, one axis: whether the decision is in force. `active`: guiding work. `superseded`: replaced by a newer decision. `reversed`: undone without a replacement. Whether the decided work has shipped is a card's business, not the decision's. Historical values (`accepted`, `locked`, `current`) are synonyms of `active`: `check` reports them off-vocabulary, `tidy` migrates them after preview.

## 10. Verification

The doc family (`project`, `doc`, `spec`, `component`, `api`, `schema`, `source`) carries `verified:` (a date) and `verified_by:` = `tested` | `read` | `docs`. A live probe and a skim of vendor docs are both verification and are not the same claim, so the page says which. It replaced a five-field epistemic block serving two read-only reporters.
