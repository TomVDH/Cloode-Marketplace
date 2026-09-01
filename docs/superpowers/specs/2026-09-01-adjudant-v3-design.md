---
date: 2026-09-01
status: design, approved (settled with Tom 2026-09-01 across a full template walkthrough)
scope: adjudant v3 - six verbs, fifteen kinds, template-as-schema, truth checks, lifecycle folders, generated twin
plugin: adjudant
version-target: 3.0.0
related: the hubspot-nightly cleanup session's findings (_docs/ADJUDANT-FINDINGS.md in that repo); ~/.claude/statusline-v2.sh, an undocumented consumer of adjudant's file surface
---

# Adjudant v3: cut the ceremony, make the vault navigable

## Context

Adjudant maintains an Obsidian vault from inside a code project. It has grown to
13 verbs, 1233 tests, ~13.5k lines of Python, and a ~42,000-token instruction
surface. In use it fails in one consistent way: it adds more than it removes.

The owner's verdict: verbs go unused, the cleanup tier "fills SO much more crud
than it actually cleans", frontmatter is "overengineered to a point it's painful",
and there is "a fetish and an adherence to MECHANICS that end up filling the vault
with crud, rather than helping".

This is a design correction, not a bug list. Two artefacts change together: the
main plugin here (v2.0.0) and its public twin in `furtive-follies` (v1.0.0).

## The evidence, compressed

Full audit detail is in the three agent reports from this session. The numbers
that drive the design:

| Finding | Number |
|---|---|
| Project folders in the vault, flat, no lifecycle grouping | 27 |
| Session notes containing zero information | 76 of 261 |
| Empty "session resumed" markers | 164 of 657 |
| Distinct frontmatter keys | 110 |
| Distinct `type:` values for ~8 real kinds | 45 |
| Distinct tags, 185 used exactly once | 420 |
| Tag applications that only restate `type:` | ~1735 |
| Broken wikilinks | 733 of 9611 |
| Index files, 24 staler than their own folder | 141 |
| Tool backup files never reaped, inside the vault | 193 |
| Hook output per human output in one session | 3 to 1 |
| Dream true-positive rate on 463 flagged contradictions | 0% |
| Template lines that are frontmatter | ~52% |

Two root causes explain nearly all of it. First, `tidy`, `port`, `shelf` and
`dream` write their previews and backups **inside the vault**, unbounded, never
reaped. Second, seven hooks write unprompted, the worst turning every unfinished
harness todo into a permanent vault note at session end.

The single best illustration: the session index in `hubspot-nightly` states the
rule that a session with no work is not listed, then hand-maintains eighteen
dates to skip. The fix was applied to the index, not the writer.

## Settled decisions (Tom, 2026-09-01)

1. **Six verbs**, from thirteen: `connect`, `status`, `clean`, `dream`, `draw`,
   `board`. `port` is sunset. `sync`, `sitrep`, `check`, `kebab`, `shelf` and
   `advisor` are absorbed.
2. **Fifteen kinds of file**, from 45 values in the wild. Five field names, from
   110. Two status vocabularies, from 31.
3. **The template file is the only declaration of a kind's shape.** The schema is
   parsed from it, never written twice.
4. **Four lifecycle folders**, guided triage across all 27 projects.
5. **Links omit the lifecycle folder**, so a project move rewrites nothing.
6. **`check` checks truth, not shape.** Ordered by cost of being wrong, never
   gates anything.
7. **Hooks: lazy writes, hard cut.** A session note appears on the first real
   write, never on open.
8. **Board stays, opt-in**, asked at `connect`. It feeds the statusline.
9. **Twin becomes generated.** One source of truth, profile-selected verbs.
10. **ASD-STE100 is a context reminder, not a gate**, plus a build-time validator
    over the plugin's own docs.
11. **HubSpot Nightly is out of scope.** A separate session owns it.

## The statusline is a consumer, and it is undocumented

`~/.claude/statusline-v2.sh` lives in iCloud and reads adjudant's file surface
directly. No adjudant document mentions it. Its vault segment reads eight
signals, and the earlier draft of this plan would have blinded four of them.

| Signal | Reads | Plan effect |
|---|---|---|
| Slug and vault path | `.claude/adjudant` breadcrumb | Unchanged |
| Verb in progress | preview dirs in repo and vault | **Re-sourced** to the temp path |
| Zone | walks `projects/{zone}/{slug}/brief.md`, zones hardcoded | **Updated** to four folders |
| Lifecycle drift | `brief.md` status versus `sessions/` mtime | Vocabulary updated |
| Handoff freshness | traffic-light banner in `_handoff.md` | Unchanged format |
| Board open count, direction, lag | `board/board-data.json`, `tasks/*.md` mtime | Unchanged |
| Dream age and drift count | newest `dreams/{date}.md`, greps a count line | **Kept**: dream still writes one report |
| In-flight tasks | `$TMPDIR/adjudant-task-ledger-{sid}.jsonl` | **Kept**: ledger stays, only its vault replay dies |

The plan therefore adds a written state contract: the exact files and lines the
statusline may depend on. Every phase below preserves it, and the statusline
script is edited in lockstep where a source moves. That edit is outside this
repo, in the iCloud suitcase, and syncs to both machines.

The "tidied" and "ported" states, which only say a backup exists, are dropped.
The statusline's own header says it cuts signals that never vary. In-progress
states stay and read from the new temp location.

## The verb surface

| Verb | Sessions used | Fate |
|---|---|---|
| `connect` | 44 | Keep. Gains zone and board prompts |
| `dream` | 9 | **Keep, rebuild for precision** |
| `ramasse` | 7 | Merges into `clean` |
| `sync` | 6 | Absorbed into `status` |
| `check` | 5 | Absorbed into `status` |
| `tidy` | 4 | Becomes `clean` |
| `draw` | 4 | Keep |
| `sitrep` | 2 | Absorbed into `status` |
| `board` | 2 | Keep, opt-in |
| `shelf` | 1 | Deleted; `connect` and `status` ask instead |
| `port` | 1 | **Sunset** |
| `advisor` | 0 | Becomes a `connect` question |
| `kebab` | 0 | Absorbed into `status` |

**Six entry points remain.** Bare `/adjudant` opens a menu; direct invocation
still works.

| Verb | Absorbs | What it does |
|---|---|---|
| `connect` | `shelf` on first link, `advisor` toggle | Onboard. Asks lifecycle folder, board yes/no, proactive mode |
| `status` | `sync`, `sitrep`, `check`, `kebab`, `advisor pulse` | Make derived state current, then report: where you are, what is wrong, what is stale |
| `clean` | `tidy`, `ramasse` | Mechanical, fast, net-subtractive. Never creates a vault file |
| `dream` | | Semantic, judgement, one report. Rebuilt for precision |
| `draw` | | Diagrams, canvases, bases |
| `board` | | Opt-in kanban, asked at connect |

`sync` alone was thin: it bumped a date, mirrored a handoff the hooks already
write at session end, and updated an index row that is now generated. Folded into
`status`, which makes derived state current before reporting on it.

Lifecycle moves have no verb. `connect` asks on first link, and `status` offers
the move when it sees a project in `active/` with no session for 30 days. `shelf`
went unused for a year because nothing ever asked.

## Dream, rebuilt to work

The 13 August run turned 602 files into 602 candidates. The contradiction
detector fires on any two topically overlapping files where one contains a
negation cue such as "no longer" or "switched from". In a vault of decisions
that legitimately say "we switched from X to Y", that is every pair. The
reference doc's own doctrine is "the catalog is deliberately generous". That
doctrine is the defect.

Dream keeps its name, its five-phase shape, and its one report. Everything else
changes.

- **Precision over recall.** Every candidate carries a confidence score. The
  catalog is capped at the top twenty. Claude judges a shortlist, never a census.
- **Kill the zero-precision detector.** Contradiction by negation cue is removed.
  Its real cases are supersession, which stays and tightens: same-type decisions,
  both active, overlapping subject, older unmarked.
- **One report, nothing else.** `dreams/{YYYY-MM-DD}.md` is the findings and the
  actions taken, under a screen long. No iteration folder, no workspace
  directory, no backup tree in the vault. Backups go to the temp path.
- **Apply through `clean`'s primitives.** Mark superseded, merge, archive, and
  repoint all use the same in-place operations `clean` uses. No second execution
  engine.
- **Scoped by default.** A first pass runs on `decisions/`. Full-project dream is
  the explicit exception.
- **The report keeps one machine line.** A single "N findings" line the
  statusline can read, replacing the current "drift item" grep.

The dream report template is in the set below.

## Markdown element standards

One rule per element, applied to every template and stated in
`reference/vault-standards.md`. The vault currently uses three bullet markers,
two italic markers, two code-block styles, and two blockquote styles.

- **Headings.** One H1, the title, and only in documents that need one. H2 for
  sections. H3 sparingly. Never H4 or deeper. No decorative punctuation in
  headings.
- **Lists.** `-` for bullets, `1.` for ordered. Never `*` or `+`.
- **Emphasis.** `*italic*` and `**bold**`. Never `_underscore_` forms. Bold the
  first words of a bullet, never a whole sentence.
- **Code.** Fenced with a language tag, always. Never four-space indentation.
  This alone removes the class of bug where an unfenced `[[ -z "$VAR" ]]` became
  a wikilink.
- **Tables.** For anything with three or more parallel attributes. Escape pipes.
- **Callouts.** `> [!note]` and `> [!warning]` only. Plain `>` is a quotation.
- **Links.** Wikilinks with the project-relative path and a display alias for
  anything in the vault. Markdown links for anything outside it.
- **Mermaid.** For flow, sequence, and state. Never for a list or a table that
  would read better as one. Diagrams follow `draw`'s generation rules.
- **Emoji.** None as semantic markup, with one documented exception: the
  handoff traffic light, which the statusline reads.
- **Register.** ASD-STE100 across every write. One instruction per sentence,
  active voice, present tense, one word per meaning, under twenty words.

## Template specifications

Settled one at a time with Tom, 2026-09-01. These are the contract.

### The anti-drift mechanism

Drift happened because every rule was declared three times: a Python constant,
a template file, and a prose description, with a validator existing only to
check the three agreed. The decision status enum lived in a YAML comment.
Nothing ever compared a real vault file to its template.

**The template file becomes the only declaration.** The schema is parsed out of
it at load time, never written a second time in Python. The standards document
links to templates instead of restating them. Three rules follow, and they apply
to every template:

1. **No inline fallbacks.** Four code paths carry a hardcoded copy of a template
   for when the file is missing. Each is a second declaration waiting to drift.
   A missing template is a loud failure.
2. **`check` compares real files to the template**, frontmatter keys and required
   headings both. Nothing does this today. It is what would have caught 45 type
   values while there were still five.
3. **An off-vocabulary value is reported, never coerced.** `board.py:205`
   silently refiles anything unrecognised as backlog, which is how `obsolete`
   became invisible work.

### Two new fields, on the doc family

Both already exist in the vault as hand-written prose. Promoting them to fields
makes them queryable, and they are the direct answer to "stop checking shape,
start checking truth".

- **`verified:`** the date this file was last checked against reality. Distinct
  from `updated:`, which only says the text changed. Makes "11 docs unverified
  for 90+ days" mechanically detectable.
- **`source:`** where truth lives when it does not live here: a repo path or a
  generator script. Absent means this file is authoritative. Two runbooks can no
  longer each call the other the copy.

### 1. `brief` — settled

```yaml
---
type: project
updated: 2026-09-01
verified: 2026-08-13
---

# Nightly

Multi-brand HubSpot theme and campaign tooling for four brands.

## Where things are
| | |
|---|---|
| Repo | ~/…/HubSpot - Nightly |
| Deploy | https://… |

## Stack
HubL, HubSpot CMS, Node functions, bash toolbox.

## Constraints
Brand assets stay brand-local. No cross-brand module sharing.
```

| Field | Required | Rule |
|---|---|---|
| `type` | yes | Literal `project`, the only legal value |
| `updated` | yes | ISO date, machine-bumped when the brief text changes |
| `verified` | yes | ISO date, set when a human checks it against reality |

Sections: H1 and identity sentence and `## Where things are` are required.
`## Stack` and `## Constraints` are conditional, written by the scaffold only for
coding and plugin projects. A section is never present and empty.

**No `## Status` section.** The zone folder, the handoff and the newest session
file already answer it, and a fourth hand-written answer is a fourth thing that
can disagree.

**Deleted from the old brief:** `status`, `slug`, `aliases`, `repo`, `stack`,
`marketplace`, `extra_folders`, `relations`, `codename`, `project_type`, `tags`,
`created`. Twenty-one lines of frontmatter against eleven of body, replaced by
three lines. The four `project-brief-*` variants collapse into this one file.

**What `check` reports:** repo path no longer resolves on disk; brief untouched
for 90 days while sessions kept landing; a required heading missing; identity
sentence still the template placeholder, which is the state of 91 files today.

### The date rule — settled

Every file carries `created:` and `updated:`. The doc family adds `verified:`.
No per-type exceptions, because an exception list is the thing nobody remembers.
Where the filename carries a date, `created:` is derived from it at write time
and `check` asserts the two match, so they cannot disagree. `date:` is retired as
a field name: two names for one concept is the drift being removed.

### 2. `session` — settled

```yaml
---
type: session
created: 2026-09-01
updated: 2026-09-01
---

Rebuilt the shader cache and split the cursor config.

## Log

- 09:05 · [[notes/shader-cache|shader-cache]] written
- 14:22 · decided: bucket-a tags go, the type field already says it
- 16:40 · commit: fix(shader) cold-cache rebuild
```

**Created lazily**, on the first real vault write, never on session open. This is
the single change that removes 76 empty session notes and 164 dead resume
markers at source.

**The line under the frontmatter is a summary, written at session end** from the
log. It is never written early, so it can never be a placeholder. Ninety-one
files hold the raw placeholder today because the start hook fires before the
session has a purpose, which the plugin's own internals doc admits.

**The log records artefacts, commits, and decisions with their one-sentence text
inline**, so a day reads as a narrative without opening anything. Nothing is
logged for session start, resume, end, pause or compaction. That removes the 34
files carrying truncated model reasoning and the 38 exact duplicate log lines.

**No `session:` field.** Provenance belongs on the artefact, not the log. A day
can hold four conversations, so a single origin UUID on a daily note was never
coherent, which is how one note came to carry eighteen. Every note, decision and
task carries its own origin; getting from a session note to a transcript is one
hop through a note it lists.

### 3. `decision` — settled

```yaml
---
type: decision
created: 2026-09-01
updated: 2026-09-01
status: active
session: 4f2a1b8c
---

# Bucket-A tags go

Every file stops carrying a tag that restates its type field.

## Why
The tag was two lines of YAML per file conveying nothing the type field
did not already say.

## Consequence
1,735 tag applications are removed by clean.
Work: [[tasks/strip-bucket-a-tags]]
```

**One axis only.** `status:` says whether the decision is in force:
`active | superseded | reversed`. Whether it has been carried out is a task card,
linked from `## Consequence`. One concept per file type, and the thing that
tracks work is the thing that already has a closing test and a board lane. The
half-applied branch decision that carried a bold prose warning becomes an open
card that is visibly unfinished.

**`superseded_by` is written only when true**, never as an empty string. A
`status: superseded` without it is an error `check` reports, and so is one
pointing at a file that does not exist.

**Two bugs fixed here, not designed around.** `dream.py:340` tests for a key
named `superseded` while the schema field is `superseded_by`, so that half of the
test has never passed. And `dream.py:593` skips any decision a session links to,
excluding 47 of 55 active decisions: adjudant tells you to link decisions from
sessions, then reads the link as proof of closure.

### 4. `task` — settled

```yaml
---
type: task
created: 2026-08-17
updated: 2026-09-01
status: doing
session: 4f2a1b8c
spec: "[[docs/SPEC-018-page-spinup|SPEC-018]]"    # optional
category: build                                    # optional
related: []                                        # optional
---

# Rebuild the board deck from task files

## Done when
`board-data.json` regenerates from `tasks/` with no card lost.

## Notes
Blocked on the status vocabulary landing first.
```

**Dates are the fix for accumulation.** Zero of 122 task files carry one today,
because task is the only template of seven with no date field. Nothing could age
a card out because nothing knew how old one was.

**`## Done when` is the fix for closure.** Forty-four cards are open partly
because nothing on them says what finished looks like, so nobody could close them
and a sweep moved them instead.

**Seven statuses, seven board columns, no aliases:**
`backlog | next | doing | review | done | icebox | dropped`. `blocked` stays an
alias of `review`. `dropped` is the value someone had to invent as `obsolete`,
which `board.py:205` then silently refiled as backlog. Off-vocabulary values are
reported, never coerced.

**Archiving is derived from status, never manual.** `clean` moves only `done` and
`dropped` cards older than 90 days into `tasks/_archive/`, and refuses anything
else. A card in the archive that still reads open is reported and moved back. The
17 August sweep that moved 97 cards and closed zero becomes impossible by
construction.

**`spec:` is a wikilink, not a bare code**, so `check` can report a card citing a
spec that does not exist, and a spec with no card and no commit. `category`,
`related` and `spec` are written only when they have a value; the four empty
strings in today's template are the ceremony, not the fields.

### The filename rule — settled

Kebab-case everywhere, no exceptions. Dated types keep the date prefix, numbered
types keep the number, everything else is lowercase words joined by hyphens. The
old UPPERCASE-for-docs rule is retired; the vault ran six competing styles under
it anyway.

### 5. `note` — settled

`type`, `created`, `updated`, `session`. Free-form body, no imposed sections. No
`verified:`. A doc claims something about the world outside itself and can be
re-checked; a note is a thought and cannot be wrong in that way.

Orphans are not a note problem. An orphan is an Obsidian graph concept; an
agent finds a note by its folder path, and the session log links every artefact
the day it is written. See the index section for why folder indexes were dropped.

### 6. `doc` — settled

`type`, `created`, `updated`, `verified`, and `source` when the file is a copy.
Body is a purpose sentence then sections. `verified:` is the only thing dividing
it from a note.

### 7. `spec` — settled

```yaml
---
type: spec
status: agreed          # draft | agreed | superseded
created / updated / verified
source: _docs/spec-012-campaign-factory.md    # when mirrored
superseded_by: "[[spec-013-props-mapping]]"   # only when true
---

# SPEC-012 Campaign factory

## Goal
## In scope
## Out of scope
## Done when
```

**Specs are permanent, not temporary.** Once the work exists the spec becomes the
normative description of it, which is onboarding reference. Nobody deletes an RFC
when it ships.

**`verified:` marks the jump from intent to reality.** Absent means agreed but
not built. Present means the built thing was confirmed to match. That gives the
state machine with no extra vocabulary, and makes the finding that would have
caught SPEC-012 a single line: agreed 60 days, zero cards citing it, never
verified.

**How much is built is the status of the cards citing it**, via the task
template's `spec:` wikilink. Same rule as decisions: the document states the
intent, the cards track the work.

**`## Out of scope` is what makes a spec unambiguous.** SPEC-012 lacked it, so a
reader could not tell contract from vision and someone bolted on a prose callout
months later explaining that two sections were never real.

### 8. `source` — settled

Material you did not write: a book, a paper, a page another team owns. Carries
`source:` for where it came from and `verified:` for when someone last confirmed
upstream still says the same thing. Author and year are optional, because a wiki
page has neither and a book has both.

Evidence for keeping it: 20 files carry `type: source` today, 17 of them imported
wiki documentation. A general vault tool needs somewhere for material it does not
own, and the shipped template asks for author, medium and year, which fits none
of the twenty.

### 9. `handoff` — settled, and corrected by evidence

**The mirror mechanism does not work.** Of 12 handoffs in the vault: 10 carry the
"Mirrored from `.remember/remember.md`" line, 7 flag themselves STALE, and **7
have nothing at all below the mirror line**. This project's is 412 bytes of
frontmatter and warning with an empty body, because the remember file it mirrored
is zero bytes.

The one useful handoff, HubSpot Nightly's, works by ignoring the mechanism: the
mirrored block contributes a banner, and a second hand-written `# Handoff`
underneath carries the standing order, the START HERE, the branch state and the
week's rulings. All the value is in the part a person wrote.

**So the model writes it at session end**, from real session context, into three
sections: Where I left off, Next, Context. Not mirrored, not derived from the
log, because a log-derived handoff is a list of filenames and fails the same way.
Remember's file is one input when present, never the source. The traffic-light
line keeps its exact current format because the statusline greps it.

### 10. `index` — settled, and mostly deleted

**Folder indexes are dropped.** All 90 of them, plus the 45 deeper ones. For an
agent they are worth nothing: listing a directory gives the true current contents
in one call, while a markdown copy is stale the moment anything changes. Of 139
folder indexes, 24 are already staler than their own folder and 15 have a body
under 25 bytes. Their only real beneficiary is Obsidian's graph view.

A correction to an earlier argument in this plan: generated folder indexes were
justified as making orphans structurally impossible. That was weak. An orphan is
an Obsidian graph concept; an agent cares whether it can find a file, and the
folder path already answers that.

**Two surfaces survive, both generated:**

- `Home.md` — every project grouped by lifecycle folder, with last-active dates.
  Replaces both current entry points, which are wrong: Home carries 39 project
  links against 27 projects, and `projects/_index.md` has 28 rows with two
  duplicated and malformed table pipes.
- `{slug}/_index.md` — the project contents page. A synthesis, not a listing:
  where to start, specs surfaced near the top as onboarding context, counts and
  newest entry per folder. Only 4 of 27 projects have one today, and two of those
  four are genuinely good documents, which says the surface is valuable and too
  much work by hand.

Roughly 28 generated files replace 141. `projects/_index.md` is retired because
Home now groups by zone and a second list adds nothing.

### 11. `release` — settled

`type`, `version`, `created`, `updated`, `session`. Body is a context paragraph,
`## Changes`, and `## Pointers`. The shipped template declares only `## Changes`,
so the good release notes drifted upward into something better; the template
catches up rather than the notes being corrected.

**The auto-stub hook is deleted.** It created a note with frontmatter and an
empty heading when it saw a `release(x): vN.N.N` commit, and the content was
written afterwards by a person. Same failure shape as the handoff. The model
writes the note at release time from what it knows about the work.

`version:` is derived from the filename, machine-written, and `check` asserts
they match, by the same rule as dates.

### 12. `dream` — settled

```yaml
---
type: dream
created / updated
---

# Dream 2026-09-01

14 findings, 9 acted on, 5 dismissed.

## Acted on
| File | Finding | Action |

## Dismissed
| Finding | Why | Suppress until |
```

One report per run, one screen long. The current arrangement writes a report note
plus an iteration folder plus a workspace directory plus a backup tree, all inside
the vault. All of that goes; backups move to the temp path.

The count line stays first and machine-readable because the statusline greps it.

**Dismissals stick.** Before reporting, dream reads the Dismissed tables from
previous reports in the project and drops anything already rejected, unless the
file it concerns has changed since. Two consecutive reports currently dismiss the
`_archive/` naming finding in identical words, which is the tool wasting the same
hour twice.

Reports today run 8.7 to 10.7 KB and the 13 August one is almost entirely an
explanation of why the scanner was wrong. With the detector fixed, the report is
findings and actions.

### The fifteen kinds — settled

```
project   session   decision  task     note
doc       source    spec      handoff  index
release   dream     component api      schema
```

Down from 45 distinct `type:` values in the vault today.

**Written as a page (`doc`) with a documented body, not their own kind:** runbook,
glossary, standard, bug log. The test that settled it: a thing gets its own kind
only when it needs a line at the top that a plain page does not have. A decision
needs to say what replaced it. A task needs its board column. A spec needs draft
or agreed. A runbook needs nothing extra, and neither does a glossary.

Evidence that made the rule concrete: `references/aap-confluence/attribution-test-runbook.md`
is `type: source`, because Confluence owns it. The same procedure written in-house
would be a doc. What a file *does* is its body; what it *is* follows from who owns
it and what extra line it needs.

### 13. `bug log` — settled as a page, no kind of its own

Tom's framing: a bug log is informal capture, jotted in passing, and its purpose
is to be spun into real work items. Imposing a schema on a low-friction capture
surface defeats the surface.

Evidence: `references/BUG-LOG.md` is one 291-line document holding BUG-001 to
BUG-016 as sections, and its own opening explains why it is one file: three
entries turned out to be the same defect class on different surfaces, which only
became visible once they sat in one list. Splitting them into 16 files would
destroy the only thing the document says it is for.

**The checkable part is what never got picked up.** `check` reports open bug
entries with no task card citing them, which is the 44-invisible-jobs failure in
miniature. That is the only mechanism the bug log needs.

The vault also names four separate number registries in play (`BUG-NNN`, `T<N>`,
harness numbers, GitHub numbers) with a standing rule never to cite a bare number.
That ambiguity is what let a second `BL-` sequence start in the repo.

### 14. `component` — settled

```yaml
---
type: component
created / updated / verified
source: build-module-inventory.py     # on the generated half only
---

# _big-list-email · email

## Diagram
## Schema
## Code
## Traps
```

Body headings counted from the real files: Diagram 39, Schema 41, Code 40, plus
occasional Traps.

**`sign_off` and `signed_off_by` are deleted, replaced by `verified:`.** The
counts show why they are the same idea: 71 `unreviewed`, 36 `settled`, 1
`retired`, and `signed_off_by` has exactly one value ever, "Tom". A date says
both that someone checked and when, which the word does not.

**Adjudant stays out of generated files.** 108 components have two pages: one the
inventory script writes and overwrites every run, one a person writes holding the
diagram and the traps. The script's page carries `source:`, and adjudant never
cleans, indexes, or nags about any file that has one. That single rule fixes
`tidy` writing an index into `_generated/`, a directory whose own docstring says
it is overwritten every run.

Today the two halves carry different kinds, `doc` on the generated one and
`reference` on the sidecar, which is why nothing treats them as related. Both
become `component`.

**The `source` template also gains what the real files already use:**
`source: confluence`, plus the upstream id and url, plus a read-only mirror
callout stating that upstream is canonical and local edits get overwritten.

### 15. `api` and `schema` — settled

```yaml
---                              ---
type: api                        type: schema
created / updated                created / updated
verified: 2026-08-13             verified / verified_by
verified_by: tested              ---
---
                                 # Event participation
# Custom objects                 Portal 50629780 · type id 2-62057387
                                 · FQN p50629780_event_participation
## Endpoints
## Quirks                        ## Object metadata
## Helpers                       ## Property groups
## See also                      ## Properties
```

Headings counted from the real files: See also 16, Endpoints 12, Quirks 9,
Helpers 8. The schema identity line stays in the body because a portal, a type id
and a fully-qualified name are read together and are useless as three fields
nothing queries.

**`verified_by:` is added to everything that carries `verified:`.** Values:
`tested | read | docs`. Tested means someone ran it against the live thing, read
means someone read the code it describes, docs means someone took a vendor's word
for it. Your `api/custom-objects.md` already records this in prose ("live probes
on prod 50629780, both type IDs answer 200"), and a bare date throws away the
difference between a live probe and a skim of vendor documentation.

Off-vocabulary values are reported, never accepted, which is what stops this
growing a fourth value the way `sign_off` grew `retired`.

## Folder structure, naming and links — settled

```
{vault}/
  Home.md
  projects/
    active/ paused/ finished/ archive/
      {slug}/
        brief.md  _handoff.md  _index.md
        sessions/     2026-09-01.md
        decisions/    2026-09-01-drop-bucket-a-tags.md
        tasks/        rebuild-board-deck.md
        notes/        cold-cache-quadratic.md
        docs/         cache.md  bug-log.md  glossary.md
        specs/        spec-018-page-spinup.md
        components/   modules/button.md
        api/          contacts.md
        schemas/      ep-object.md
        sources/      attribution-test-runbook.md
        releases/     v2.1.0.md
        dreams/       2026-09-01.md
        images/
```

**A folder exists when something is in it.** `connect` today creates four to seven
folders up front and drops an empty index into each, which is where the fifteen
index files with a body under 25 bytes came from. A scratchpad project gets
`sessions/` and nothing else.

**One level of grouping inside a folder, never two.** 225 component pages need
`components/modules/` and `components/templates/`. Nothing needs to go deeper.

**`references/` retires.** It holds six unrelated things today: api pages,
schemas, specs, sections, component inventories and imported wiki pages. Each now
has a folder that names it. `clean` offers the split and rewrites the links.

**Filenames are kebab-case everywhere**, no exceptions. Dated kinds keep the date
prefix, numbered kinds keep the number.

**Links omit the lifecycle folder:** `[[hubspot-nightly/decisions/2026-08-12-branch-track|branch track]]`.
Obsidian resolves by matching the end of the path, so a project moving between
`active/` and `paused/` breaks nothing. This is already how the project index row
works, and it lets the vault-wide link rewrite in `shelf.py:243` be deleted
outright: 380 lines whose only job was repairing the choice to put the zone in
every link.

## The repo side — settled

The rule is sound and does not change. `AGENTS.md` is canonical and
harness-agnostic, `CLAUDE.md` imports it and holds Claude-only overrides,
`GEMINI.md` does the same for agy, and the vault contains none of them. Verified
by full-depth search. The project brief points at the repo file rather than
copying it.

**Ownership becomes one rule: `connect` provisions once if missing, and adjudant
never overwrites.** Today five paths write these files under three contradictory
policies: `connect` never overwrites, `port` overwrites wholesale, and `advisor`
appends a marker a later `port` silently drops. Sunsetting `port` removes two of
the three.

**`check` reaches outside the vault for this one file.** AGENTS.md is the first
thing every agent reads and nothing keeps it true: HubSpot Nightly's carries five
false statements, including traps about a module deleted on 2026-08-23 and a rule
described as "enforced mechanically" by a script that does not exist. Three of
those five are detectable without adjudant knowing anything about the project.

- Every path, file and script AGENTS.md names is checked for existence.
- How many commits have landed since AGENTS.md last changed.

No frontmatter is added to it and nothing is rewritten. The repo's own AGENTS.md
in this marketplace says adjudant has eleven verbs; it has thirteen; nothing
checks it. That is the same failure at home.

## What `check` does — settled

Every item is mechanically detectable and traces to a real failure.

**Names something that is not there.** AGENTS.md naming a missing script, four in
HubSpot Nightly. A brief's repo path that no longer resolves. A broken wikilink,
733 at 7.6%. A `superseded_by` pointing at nothing. A card citing a spec that was
never written.

**Nobody has checked it lately.** `verified:` over 90 days old. Pages only ever
`verified_by: docs`, never tested. Pages with no `verified:` at all, which is 71
component sidecars.

**Work nobody can see.** Open cards in an archive folder, the 44. Bug log entries
open with no card citing them. A spec agreed with zero cards and no verification,
which is SPEC-012 exactly. A decision whose consequence names work with no card.

**Records that disagree.** A decision marked superseded with no target. A status
value outside its vocabulary, reported rather than refiled as backlog.

**Went stale quietly.** A brief untouched while sessions landed. AGENTS.md
unchanged across N commits. A handoff older than the newest session. A generated
page older than the script that writes it. A `created` date disagreeing with its
own filename.

**A project in the wrong folder.** In `active/` with no session for 30 days. This
is the prompt that makes lifecycle triage happen instead of never happening.

**Output is a read-only report ordered by cost of being wrong**, in three bands:
wrong now, going stale, worth a look. It never gates anything.

**What check stops doing:** grading the memory folder against a schema adjudant
does not own, which produced 69 of 99 failures; re-raising the archive naming
convention after two dismissals; reporting unknown frontmatter keys, since with
five fields an unknown one is a typo or a real need.

**Check versus dream.** Check finds what a file's existence or a date comparison
proves, runs in seconds, safe to run constantly. Dream reads prose to find what
only comprehension finds, and is the expensive one.

## Plan

### Phase 0: back-port, then stop the bleeding

- Back-port `suggest_vault_roots()` and `--create-vault` from the twin into main
  before anything else, or they are lost.
- Move every preview and backup directory out of the vault to
  `$TMPDIR/adjudant/{slug}/`. Affects `tidy.py:777` and `:969`,
  `repo_tidy.py:80`, and the dream reference doc. `port.py` and `shelf.py` are
  skipped here because phase 3 deletes them.
- Add retention caps modelled on `board.py:69`.
- Repoint the statusline's verb-state detection at the new temp path; drop the
  "tidied" and "ported" states.
- Write `reference/state-contract.md`: the files and lines the statusline and
  the session-start banner may depend on.

### Phase 1: the hook diet

- Session note created on the first real vault write, never on open.
- Delete the session-end replay at `board_bridge.py:150-165` that turns todos
  into vault notes. Keep the temp ledger; the statusline reads it.
- Delete UUID stamping, resume markers, compaction gists, and session-end
  markers.
- Handoff written once, at session end. Tradeoff stated once: a session that
  dies before its end leaves the previous handoff in place, and the STALE flag
  will show it.
- Declare the remember dependency with a presence probe shaped like
  `_suitcase_status()` in `check.py`, and report plainly when absent.
- De-duplicate `_pick_remember_source()` into `_handoff_freshness.py`.

### Phase 2: templates first, because everything else reads them

The template file becomes the only declaration of a kind's shape. The schema is
parsed out of it at load time and never written a second time in Python.

- Write the fifteen templates specified above. Retire `memory.md`,
  `iteration.md`, `dream-report.md`, and the four `project-brief-*` variants.
- Parse `FIELD_SCHEMA` from the templates. Delete the Python constants that
  currently declare the same thing, and validators 28, 29 and 31, which exist
  only to check the two declarations agree.
- Delete the four inline template fallbacks in `connect.py:507-518`,
  `board_bridge.py:46-60`, and `posttooluse-commit-log.py:253-271`. A missing
  template is a loud failure.
- Route every machine writer through one `render(template, fields)` call, so
  machine writes match the template by construction.
- Migrate the vocabularies: seven task statuses with no aliases, three decision
  statuses, three spec statuses, `verified_by` of tested, read or docs. Delete
  `sign_off`, `signed_off_by`, and the ~25 board aliases.

### Phase 3: the verb surface

- Sunset `port`: script, tests, reference, metadata entry, four validators.
- Merge `tidy` and `ramasse` into `clean`. Net-subtractive in code: it may
  delete, merge and rewrite in place, and may not create a vault file.
- Fold `sync`, `sitrep`, `check`, `kebab --scan` and `advisor pulse` into
  `status`. It makes derived state current, then reports.
- `advisor` on and off become a `connect` question written to the breadcrumb.
- Lifecycle moves lose their verb. `connect` asks on first link; `status` offers
  the move on 30 days of silence. `shelf.py` is deleted, including the 380-line
  vault-wide link rewrite that the zone-less link form makes unnecessary.
- Rebuild `dream`: cap at twenty candidates with confidence scores, delete the
  contradiction-by-negation detector, fix the `superseded` versus
  `superseded_by` key bug at `dream.py:340`, and remove the session-link skip at
  `:593` that excludes 47 of 55 active decisions.
- `board` opt-in at `connect`, never auto-seeded.
- Bare `/adjudant` opens a menu.

### Phase 4: structure, navigation and truth

- Four lifecycle folders. Update `PROJECT_ZONES`, `ZONE_FOR_STATUS`,
  `find_project_dir` and the statusline zone walk together.
- Guided triage: one prompt per project across all 27, moving nothing until
  confirmed.
- Folders are created on demand, never scaffolded empty.
- One `place()` and one `link()` function. Links omit the lifecycle folder.
  Stop accepting bare-stem matches anywhere in the vault.
- Generate `Home.md` and `{slug}/_index.md`. Delete the other 113 index files.
- `clean` offers the `references/` split into `api/`, `schemas/`, `specs/`,
  `components/` and `sources/`, and repoints the 733 broken links.
- Replace check's shape rules with the truth checks specified above, including
  the AGENTS.md reach. Exempt the memory folder, which adjudant does not own and
  which produced 69 of its 99 failures.
- Rewrite `reference/vault-standards.md` as structure, naming, links and the
  markdown element standards, linking to templates instead of restating them.
  Rewrite `reference/content-markdown.md` to stop contradicting it.
- Add the ASD-STE100 reminder to session start and the turn reminder, and extend
  the pre-commit validator over templates and reference docs.

### Phase 5: twin generation

- Move forked constants out of `_vault_walk.py` into a data file.
- Environment probes behind capability checks.
- Audience field per verb in `command-metadata.json`; generate router table,
  both descriptions, and README verb table from it.
- Wire the twin's 31 validators to pre-commit; copy `bump_plugin_version.py`.
- Regenerate the field guide at a release boundary only.

### Loose ends needing a decision, not a design

- `projects/_port-test-hubspot/`, 195 files, 3.6 MB, a May test artefact.
  Deletion needs explicit approval.
- 193 unreaped backup files and 33 zero-byte lock files.
- Seven hookify symlinks in `.claude/` dangle on this machine.
- `Home.md` says `type: cabinet-home`; the resolver looks for `vault-home`.
- Both `onnozelaer-claude-plugins/` and `onnozelaer-claude-marketplace/` exist.
- Repo `AGENTS.md` says eleven verbs. Nothing checks it.

## Execution split (Tom, 2026-09-01)

Split by risk. The plan is specific enough, with file and line references and a
verification test per phase, that the mechanical majority runs on Sonnet against
the existing 1,233-test suite. Four pieces stay on a stronger model because they
are new logic, irreversible, or need judgement the tests cannot express.

**Sonnet, roughly 70% of the work:**

- Phase 0: move backups and previews out of the vault, retention caps, statusline
  re-pointing, the state contract document.
- Phase 1: the hook diet, in full.
- Phase 2: writing the fifteen templates and retiring the seven, deleting the
  inline fallbacks, routing writers through `render()`, vocabulary migrations.
- Phase 3: sunsetting `port`, `shelf` and `kebab`; merging `tidy` and `ramasse`
  into `clean`; folding five verbs into `status`; the menu.
- Phase 4: lifecycle folders, triage loop, on-demand folder creation, `place()`
  and `link()`, generating the two index surfaces and deleting 113, the
  `references/` split, rewriting the standards docs, the STE reminder.

**Stronger model:**

- **Parsing `FIELD_SCHEMA` from templates.** Inverts the plugin's architecture;
  every consumer changes at once; a subtle error makes the write gate silently
  permissive instead of failing loudly. Worst failure mode in the plan.
- **The truth checks.** New logic with no pattern in the codebase to follow, and
  a check that produces noise is how the vault got here.
- **Dream's precision rebuild.** Needs running against real data and judging
  whether findings are real, which no test expresses.
- **Twin generation.** The one irreversible step. The twin holds code that exists
  nowhere else, and a regeneration that drops it looks like success until
  someone tries to onboard.

**Before any execution:** commit this plan to `docs/superpowers/specs/` in the
repo, where design docs already live, and put the statusline consumer in front of
whoever executes. It lives in iCloud outside this repo and greps files this plan
moves.

## Verification

- Full suite green in both trees after every commit.
- **The no-crud test.** A scripted session that writes six notes, commits three
  times and compacts once must leave zero unrequested files in the vault.
  Currently fails by eight files, eleven whole-file rewrites and fourteen log
  lines.
- **The net-subtractive test.** `clean` on a copied project must reduce both file
  count and byte count, and create nothing inside the vault.
- **The precision test.** `dream` on a copy of a real decisions folder returns at
  most twenty candidates, and a hand review finds better than one in two real.
  The 13 August baseline was 602 candidates and zero real.
- **The template-is-the-schema test.** Deleting a field from a template must
  change what `check` accepts, with no Python edit. If it does not, two
  declarations still exist.
- **The truth test.** Seed a fixture where AGENTS.md names a missing script, a
  card sits open in an archive, a decision is superseded with no target, and a
  page is 100 days unverified. All four must appear, ranked, in one `status` run.
- **Link round-trip.** One file of every kind, every link resolving by path with
  no full-vault scan, and every link still resolving after the project moves
  between lifecycle folders.
- **Statusline contract.** Every signal renders after each phase, checked by
  running the script against a fixture breadcrumb.
- **Triage dry-run** yields exactly 27 prompts and moves nothing.
- **Twin regeneration.** Every deletion intentional and named, and the
  vault-suggestion code survives.

## Deferred by decision

HubSpot Nightly remediation belongs to another session. That session's findings
drove much of this design and are cited throughout.
