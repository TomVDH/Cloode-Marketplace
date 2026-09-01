# Adjudant v3, Plan 2: Templates Are The Schema

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A note's shape is declared exactly once, in its template file, and nothing can disagree with it.

**Architecture:** Today three things declare the same rule: a Python constant, a template file, and a prose description, with validators existing only to check the three agree. This plan makes the template file the sole declaration and derives `FIELD_SCHEMA` from it at import time. The fifteen templates are rewritten to the v3 shape first, then the parser replaces the constant, then the three parity validators are deleted because there is no longer a second declaration to be parity with.

**Tech Stack:** Python 3.9+ stdlib only, `unittest`. No YAML library: the repo has a minimal frontmatter parser in `_vault_walk.py` and this plan uses it.

**Spec:** `docs/superpowers/specs/2026-09-01-adjudant-v3-design.md` (phase 2, and the whole "Template specifications" section, which is the contract for every template body below)

**Assumes:** Plan 1 has landed. Scratch lives outside the vault, session notes are created lazily, and the ambient hooks no longer write.

## Global Constraints

- **Stdlib only.** No new dependencies.
- **Python 3.9 floor.**
- **The suite must be green after every task.** `python3 -m unittest discover -p 'test_*.py'` from `adjudant/scripts/`.
- **Validators must be green.** `python3 adjudant/scripts/validate.py` from the repo root. This plan deletes three of them and the count in `validate.py`'s docstring must be updated in the same commit.
- **The fifteen kinds are fixed:** `project session decision task note doc source spec handoff index release dream component api schema`. No sixteenth without a spec change.
- **The five field names are fixed:** `type status created updated session`, plus `verified` and `verified_by` on the doc family, plus `source`, `superseded_by`, `version`, `spec`, `category` and `related` where the spec names them. Nothing else is legal.
- **No pre-written empty fields.** An optional field appears in a written file only when it has a value. Today `templates/task.md` ships four empty strings and `templates/iteration.md` is 93% frontmatter.
- **Commit style:** Conventional Commits, scope `adjudant`, ending with:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`

## File Structure

| File | Responsibility |
|---|---|
| `adjudant/skills/adjudant/templates/*.md` | Fifteen templates. Each is simultaneously the example, the schema and the documentation for its kind. |
| `adjudant/scripts/_template_schema.py` | **New.** Parses the templates into the schema at import. Single responsibility; `_vault_walk.py` imports from it. |
| `adjudant/scripts/test__template_schema.py` | **New.** Tests for the parser, including the test that proves there is only one declaration. |
| `adjudant/scripts/_vault_walk.py` | `FIELD_SCHEMA` and the status vocabularies become derived, not declared. |
| `adjudant/scripts/_render.py` | **New.** One `render(kind, fields, body)` used by every mechanical writer. |
| `adjudant/scripts/validate.py` | Validators 28, 29 and 31 deleted. |
| `adjudant/scripts/connect.py`, `board_bridge.py`, `hooks/scripts/posttooluse-commit-log.py` | Inline template fallbacks deleted; all route through `_render`. |

---

## Task 1: Establish the template header convention

Every template must declare which of its fields are required. Today that lives in Python. The convention has to exist before any template is rewritten.

**Files:**
- Create: `adjudant/skills/adjudant/templates/README.md`
- Test: none (documentation task, verified by Task 2's parser)

**Interfaces:**
- Consumes: nothing.
- Produces: the comment convention every template in Tasks 3 to 6 follows, and that Task 7's parser reads. Exact form:
  - A field with no trailing comment is **required**.
  - A field with a trailing `# optional` comment is **optional** and is omitted from a written file when it has no value.
  - A field with a trailing `# optional: a | b | c` comment is optional and its value must be one of the listed words.
  - A field with a trailing `# a | b | c` comment (no `optional:`) is required and its value must be one of the listed words.

- [ ] **Step 1: Write the convention**

Create `adjudant/skills/adjudant/templates/README.md`:

```markdown
# Templates

Each file here is three things at once: the example a writer copies, the schema
`check` enforces, and the documentation of what a kind of note is for. There is
no second declaration anywhere. `_template_schema.py` parses these files at
import time and `_vault_walk.FIELD_SCHEMA` is the result.

Before v3 the same rule was written three times — a Python constant, the
template, and a prose section in `vault-standards.md` — with three validators
whose entire job was checking the three agreed. When they disagreed the vault
was already wrong. One declaration cannot disagree with itself.

## How a template declares its schema

Frontmatter, with trailing comments carrying the rules:

```yaml
---
type: decision
created: 2026-09-01
updated: 2026-09-01
status: active                    # active | superseded | reversed
superseded_by: ""                 # optional
session: 4f2a1b8c                 # optional
---
```

| Trailing comment | Means |
|---|---|
| none | Required. Must be present on every file of this kind. |
| `# optional` | Optional. Written only when it has a value, never as an empty string. |
| `# a \| b \| c` | Required, and the value must be one of these words. |
| `# optional: a \| b \| c` | Optional, and when present the value must be one of these words. |

The `type:` value is always a literal and is always the kind's name.

## How a template declares its body

Every `##` heading in the template is a required section. A heading that only
sometimes applies is marked:

```markdown
## Stack
<!-- when: coding, plugin -->
```

`check` reports a file missing a required heading. It does not care about
prose.

## Rules

1. **No empty optional fields in a written file.** The template shows an
   optional field so a reader knows it exists; a writer omits it. Today's
   `task.md` ships four empty strings and 181 files in the real vault carry a
   field whose only value is `""`.
2. **A heading is a section a reader needs.** No scaffolding. If a section
   would be empty, the template should not have it.
3. **Frontmatter should be the minority of the file.** Across the pre-v3
   templates it was 52% of all lines, and `iteration.md` was 93%.
4. **Adding a field means editing one file.** If you find yourself editing
   Python to add a field, stop: the design has regressed.
```

- [ ] **Step 2: Commit**

```bash
git add adjudant/skills/adjudant/templates/README.md
git commit -m "docs(adjudant): the template convention that replaces FIELD_SCHEMA

A trailing comment carries required/optional and the value vocabulary, so a
template file is the only place a kind's shape is declared.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Write the five record templates

**Files:**
- Modify: `adjudant/skills/adjudant/templates/{decision,session,task,note,source}.md`
- Test: `adjudant/scripts/test_templates.py` (new)

**Interfaces:**
- Consumes: the comment convention from Task 1.
- Produces: five template files whose parsed schema Task 7 asserts. Kind names are exactly `decision`, `session`, `task`, `note`, `source`.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_templates.py`:

```python
"""Tests every shipped template against the v3 contract.

These assertions are the contract from the design spec's "Template
specifications" section, in code. A template that drifts from the spec fails
here rather than in the vault six weeks later.
"""

import re
import unittest
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "skills" / "adjudant" / "templates"

# The fifteen kinds, and nothing else.
KINDS = {
    "project", "session", "decision", "task", "note",
    "doc", "source", "spec", "handoff", "index",
    "release", "dream", "component", "api", "schema",
}

# Every field name legal anywhere in the vault.
LEGAL_FIELDS = {
    "type", "created", "updated", "session", "status",
    "verified", "verified_by", "source", "superseded_by",
    "version", "spec", "category", "related",
}


def _frontmatter(path: Path) -> list[str]:
    text = path.read_text()
    if not text.startswith("---\n"):
        return []
    end = text.index("\n---", 4)
    return [ln for ln in text[4:end].splitlines() if ln.strip()]


def _field_name(line: str) -> str:
    return line.split(":", 1)[0].strip()


class TestEveryTemplate(unittest.TestCase):

    def _templates(self):
        for p in sorted(TEMPLATES.glob("*.md")):
            if p.name == "README.md":
                continue
            yield p

    def test_only_legal_fields(self):
        for p in self._templates():
            for line in _frontmatter(p):
                name = _field_name(line)
                self.assertIn(name, LEGAL_FIELDS,
                              f"{p.name} declares unknown field '{name}'")

    def test_type_is_a_known_kind(self):
        for p in self._templates():
            fm = _frontmatter(p)
            types = [ln for ln in fm if _field_name(ln) == "type"]
            self.assertEqual(len(types), 1, f"{p.name} needs exactly one type:")
            value = types[0].split(":", 1)[1].split("#")[0].strip()
            self.assertIn(value, KINDS, f"{p.name} declares unknown kind '{value}'")

    def test_body_outweighs_frontmatter(self):
        # Pre-v3 templates were 52% frontmatter and one was 93%.
        for p in self._templates():
            text = p.read_text()
            fm = len(_frontmatter(p))
            body = len([ln for ln in text.split("\n---", 1)[-1].splitlines() if ln.strip()])
            self.assertLess(fm, body,
                            f"{p.name} is {fm} frontmatter lines to {body} body lines")

    def test_no_empty_string_defaults(self):
        # An optional field is omitted when empty, never written as "".
        for p in self._templates():
            for line in _frontmatter(p):
                if '""' in line or "''" in line:
                    self.assertIn("# optional", line,
                                  f"{p.name}: {line.strip()} ships an empty value "
                                  "and is not marked optional")

    def test_dates_present_on_every_kind(self):
        # The date rule: created and updated on everything, no exceptions.
        for p in self._templates():
            names = {_field_name(ln) for ln in _frontmatter(p)}
            self.assertIn("created", names, f"{p.name} has no created:")
            self.assertIn("updated", names, f"{p.name} has no updated:")


class TestRecordTemplates(unittest.TestCase):

    def test_decision_has_one_status_axis(self):
        fm = _frontmatter(TEMPLATES / "decision.md")
        status = [ln for ln in fm if _field_name(ln) == "status"][0]
        self.assertIn("active | superseded | reversed", status)
        for gone in ("implemented", "deferred"):
            self.assertNotIn(gone, status,
                             "decision status mixes force with progress again")

    def test_task_has_seven_statuses_and_dates(self):
        text = (TEMPLATES / "task.md").read_text()
        fm = _frontmatter(TEMPLATES / "task.md")
        status = [ln for ln in fm if _field_name(ln) == "status"][0]
        for value in ("backlog", "next", "doing", "review", "done", "icebox", "dropped"):
            self.assertIn(value, status, f"task status missing {value}")
        self.assertIn("## Done when", text,
                      "task has no closing test; 44 real cards could not be closed")

    def test_session_is_one_field_plus_dates(self):
        names = {_field_name(ln) for ln in _frontmatter(TEMPLATES / "session.md")}
        self.assertEqual(names, {"type", "created", "updated"})
        self.assertNotIn("session_id", names,
                         "one note carried 18 conversation UUIDs")

    def test_note_has_no_verified(self):
        names = {_field_name(ln) for ln in _frontmatter(TEMPLATES / "note.md")}
        self.assertNotIn("verified", names,
                         "a note is a thought and cannot be re-checked")

    def test_source_records_where_it_came_from(self):
        names = {_field_name(ln) for ln in _frontmatter(TEMPLATES / "source.md")}
        self.assertIn("source", names)
        self.assertIn("verified", names)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_templates -v`
Expected: FAIL. The shipped templates carry `tags`, `date`, `session_id` and empty strings.

- [ ] **Step 3: Write the five templates**

`adjudant/skills/adjudant/templates/decision.md`:

```markdown
---
type: decision
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: active                    # active | superseded | reversed
superseded_by: ""                 # optional
session: ""                       # optional
---

# {What was decided}

{One sentence stating the decision.}

## Why

{The reason. Two or three sentences. This is the part a reader comes back for.}

## Consequence

{What changes because of this. Link the card doing the work:
[[{slug}/tasks/{task-slug}]]}
```

`adjudant/skills/adjudant/templates/session.md`:

```markdown
---
type: session
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
---

{One line, written at session end, saying what this session did.}

## Log

- {HH:MM} · [[{slug}/notes/{note}|{note}]] written
- {HH:MM} · decided: {the decision in one sentence}
- {HH:MM} · commit: {subject}
```

`adjudant/skills/adjudant/templates/task.md`:

```markdown
---
type: task
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: backlog                   # backlog | next | doing | review | done | icebox | dropped
session: ""                       # optional
spec: ""                          # optional
category: ""                      # optional
related: ""                       # optional
---

# {What needs doing}

## Done when

{The test that closes this card. One sentence, checkable by someone who was
not there.}

## Notes

{Anything the person picking this up needs.}
```

`adjudant/skills/adjudant/templates/note.md`:

```markdown
---
type: note
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
session: ""                       # optional
---

# {Title}

{Prose. No imposed sections: this is the one kind with no shape, and the
moment it has required headings it stops being the place you can put
anything.}
```

`adjudant/skills/adjudant/templates/source.md`:

```markdown
---
type: source
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
verified: {YYYY-MM-DD}
verified_by: read                 # tested | read | docs
source: ""                        # optional
---

# {Title}

{Author}, {year}. {url}

## Key points

{What this says that matters here.}

## Why it matters

{Why it is in this vault rather than a bookmark.}
```

- [ ] **Step 4: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_templates -v 2>&1 | tail -5`
Expected: the five record tests PASS. `TestEveryTemplate` still fails on the ten templates not yet rewritten; that is expected until Task 6.

- [ ] **Step 5: Commit**

```bash
git add adjudant/skills/adjudant/templates/decision.md adjudant/skills/adjudant/templates/session.md adjudant/skills/adjudant/templates/task.md adjudant/skills/adjudant/templates/note.md adjudant/skills/adjudant/templates/source.md adjudant/scripts/test_templates.py
git commit -m "feat(adjudant): the five record templates, v3 shape

decision loses implemented and deferred: status says whether it is in force,
and a card tracks whether it is done. task gains created, updated and a
closing test — it was the only template of seven with no date, so zero of 122
cards in the real vault could be aged out. session drops session_id, which had
stacked to 18 UUIDs in one note.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Write the project and doc-family templates

**Files:**
- Create: `adjudant/skills/adjudant/templates/{brief,spec,component,api,schema}.md`
- Delete: `adjudant/skills/adjudant/templates/project-brief-{coding,knowledge,plugin,tinkerage}.md`
- Modify: `adjudant/skills/adjudant/templates/doc.md`
- Test: `adjudant/scripts/test_templates.py`

**Interfaces:**
- Consumes: the convention from Task 1, and the `<!-- when: ... -->` heading marker it defines.
- Produces: kinds `project`, `doc`, `spec`, `component`, `api`, `schema`. `brief.md` is the template for kind `project`; the filename differs from the kind name, and Task 7's parser reads the kind from `type:`, never from the filename.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_templates.py`:

```python
class TestDocFamily(unittest.TestCase):

    DOC_FAMILY = ("brief", "doc", "spec", "component", "api", "schema", "source")

    def test_every_doc_family_template_has_verified(self):
        # verified: is what separates a page that claims something about the
        # world from a note that is just a thought.
        for name in self.DOC_FAMILY:
            names = {_field_name(ln) for ln in _frontmatter(TEMPLATES / f"{name}.md")}
            self.assertIn("verified", names, f"{name}.md has no verified:")
            self.assertIn("verified_by", names, f"{name}.md has no verified_by:")

    def test_verified_by_vocabulary_is_uniform(self):
        for name in self.DOC_FAMILY:
            line = [ln for ln in _frontmatter(TEMPLATES / f"{name}.md")
                    if _field_name(ln) == "verified_by"][0]
            for value in ("tested", "read", "docs"):
                self.assertIn(value, line, f"{name}.md verified_by missing {value}")

    def test_brief_has_no_status_field(self):
        # The zone folder is the status; a second answer can disagree with it.
        names = {_field_name(ln) for ln in _frontmatter(TEMPLATES / "brief.md")}
        self.assertNotIn("status", names)
        self.assertNotIn("slug", names)
        self.assertNotIn("aliases", names)

    def test_brief_marks_conditional_sections(self):
        text = (TEMPLATES / "brief.md").read_text()
        self.assertIn("<!-- when: coding, plugin -->", text)

    def test_the_four_brief_variants_are_gone(self):
        for variant in ("coding", "knowledge", "plugin", "tinkerage"):
            self.assertFalse((TEMPLATES / f"project-brief-{variant}.md").exists(),
                             f"project-brief-{variant}.md survived")

    def test_spec_has_three_statuses_and_scope_bounds(self):
        text = (TEMPLATES / "spec.md").read_text()
        status = [ln for ln in _frontmatter(TEMPLATES / "spec.md")
                  if _field_name(ln) == "status"][0]
        for value in ("draft", "agreed", "superseded"):
            self.assertIn(value, status)
        self.assertIn("## Out of scope", text,
                      "the section that makes a spec unambiguous")
        self.assertIn("## Done when", text)

    def test_component_declares_the_generated_half(self):
        text = (TEMPLATES / "component.md").read_text()
        names = {_field_name(ln) for ln in _frontmatter(TEMPLATES / "component.md")}
        self.assertIn("source", names,
                      "no way to mark a page a script owns")
        for heading in ("## Diagram", "## Schema", "## Code"):
            self.assertIn(heading, text)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_templates.TestDocFamily -v`
Expected: FAIL with `FileNotFoundError` for `brief.md`.

- [ ] **Step 3: Write the templates**

`brief.md`:

```markdown
---
type: project
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
verified: {YYYY-MM-DD}
verified_by: read                 # tested | read | docs
---

# {Project Name}

{One sentence. What this is and who it is for.}

## Where things are

| | |
|---|---|
| Repo | {path or url} |
| Deploy | {url, or none} |

## Stack
<!-- when: coding, plugin -->

{One line. Languages, frameworks, hosting.}

## Constraints
<!-- when: coding, plugin -->

{What must stay true. The things a newcomer would otherwise break.}
```

`doc.md`:

```markdown
---
type: doc
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
verified: {YYYY-MM-DD}
verified_by: read                 # tested | read | docs
source: ""                        # optional
session: ""                       # optional
---

# {Name}

{One sentence: what this document tells you.}

## {Section}

{What is true now. Rewritten as understanding changes, not appended to.}
```

`spec.md`:

```markdown
---
type: spec
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
verified: {YYYY-MM-DD}
verified_by: read                 # tested | read | docs
status: draft                     # draft | agreed | superseded
superseded_by: ""                 # optional
source: ""                        # optional
---

# {SPEC-NNN} {Title}

{One sentence: what gets built.}

## Goal

{Why this is worth building.}

## In scope

{What this covers. Be specific enough that a reader can tell.}

## Out of scope

{What this deliberately does not cover. Without this section a reader cannot
tell a contract from a sketch, which is how one spec came to need a prose
callout months later explaining that two of its sections were never real.}

## Done when

{The test that says this is built. Cards citing this spec close against it.}
```

`component.md`:

```markdown
---
type: component
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
verified: {YYYY-MM-DD}
verified_by: read                 # tested | read | docs
source: ""                        # optional
---

# {name} · {surface}

## Diagram

{A mermaid graph of the structure. What contains what.}

## Schema

| Field | Type | Default | Notes |
|---|---|---|---|

## Code

{The markup or code, fenced with its language.}

## Traps

{What breaks. The reason someone reads this page twice.}
```

`api.md`:

```markdown
---
type: api
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
verified: {YYYY-MM-DD}
verified_by: tested               # tested | read | docs
---

# {Endpoint family}

{One sentence. What this family is for.}

## Endpoints

| Method | Path | Scope |
|---|---|---|

## Quirks

{What the documentation does not say. The reason this page exists.}

## Helpers

{Scripts or commands in this project that call it.}

## See also

{Related pages.}
```

`schema.md`:

```markdown
---
type: schema
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
verified: {YYYY-MM-DD}
verified_by: tested               # tested | read | docs
---

# {Object name}

{Identity line: the ids needed to address this object, read together.}

## Object metadata

| Field | Value |
|---|---|

## Properties

| Internal name | Label | Type | Group |
|---|---|---|---|
```

- [ ] **Step 4: Delete the four brief variants**

```bash
git rm adjudant/skills/adjudant/templates/project-brief-coding.md \
       adjudant/skills/adjudant/templates/project-brief-knowledge.md \
       adjudant/skills/adjudant/templates/project-brief-plugin.md \
       adjudant/skills/adjudant/templates/project-brief-tinkerage.md
```

- [ ] **Step 5: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_templates.TestDocFamily -v`
Expected: PASS, 6 tests

- [ ] **Step 6: Commit**

```bash
git add adjudant/skills/adjudant/templates/ adjudant/scripts/test_templates.py
git commit -m "feat(adjudant): project and doc-family templates, and verified_by

One brief replaces four variants; project type now picks which sections get
written, not which file you get. The brief loses status, because the zone
folder is the status and a second answer can disagree with it.

verified_by (tested | read | docs) joins verified everywhere: a live probe and
a skim of vendor docs are both 'verified' and are not the same claim.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Write the four generated templates

**Files:**
- Modify: `adjudant/skills/adjudant/templates/{handoff,release,home}.md`
- Create: `adjudant/skills/adjudant/templates/{dream,index-project}.md`
- Delete: `adjudant/skills/adjudant/templates/{dream-report,memory,iteration,_index-collection,_index-projects}.md`
- Test: `adjudant/scripts/test_templates.py`

**Interfaces:**
- Consumes: Task 1's convention.
- Produces: kinds `handoff`, `release`, `dream`, `index`. `home.md` and `index-project.md` both declare `type: index`; Task 7's parser must therefore key its schema by `type:` and merge two files declaring the same kind, asserting they agree.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_templates.py`:

```python
class TestGeneratedTemplates(unittest.TestCase):

    def test_handoff_keeps_the_statusline_banner_shape(self):
        # The statusline greps this line. It is the one place emoji are
        # load-bearing. See reference/state-contract.md.
        text = (TEMPLATES / "handoff.md").read_text()
        self.assertIn("handoff age:", text)
        for section in ("## Where I left off", "## Next", "## Context"):
            self.assertIn(section, text)

    def test_handoff_is_not_a_mirror(self):
        # 7 of 12 real handoffs were a banner and an empty body, because the
        # remember file they mirrored was empty.
        text = (TEMPLATES / "handoff.md").read_text()
        self.assertNotIn("Mirrored from", text)
        names = {_field_name(ln) for ln in _frontmatter(TEMPLATES / "handoff.md")}
        self.assertNotIn("source", names)

    def test_dream_leads_with_a_machine_readable_count(self):
        text = (TEMPLATES / "dream.md").read_text()
        self.assertIn("findings", text)
        self.assertIn("## Dismissed", text,
                      "dismissals must persist or the same finding returns")
        self.assertIn("Suppress until", text)

    def test_release_has_context_and_pointers(self):
        text = (TEMPLATES / "release.md").read_text()
        for section in ("## Changes", "## Pointers"):
            self.assertIn(section, text)
        names = {_field_name(ln) for ln in _frontmatter(TEMPLATES / "release.md")}
        self.assertIn("version", names)

    def test_retired_templates_are_gone(self):
        for name in ("dream-report", "memory", "iteration",
                     "_index-collection", "_index-projects"):
            self.assertFalse((TEMPLATES / f"{name}.md").exists(),
                             f"{name}.md survived")

    def test_index_templates_agree_on_their_kind(self):
        for name in ("home", "index-project"):
            fm = _frontmatter(TEMPLATES / f"{name}.md")
            value = [ln for ln in fm if _field_name(ln) == "type"][0]
            self.assertIn("index", value)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_templates.TestGeneratedTemplates -v`
Expected: FAIL — `dream.md` and `index-project.md` do not exist, and `handoff.md` still says "Mirrored from".

- [ ] **Step 3: Write the templates**

`handoff.md`:

```markdown
---
type: handoff
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
---

{🟢|🟡|🔴} **handoff age: {N}{h|d}**

## Where I left off

{What was in hand when the session ended.}

## Next

{The one thing to do first on resuming.}

## Context

{What a fresh session needs to know that is not obvious from the repo.}
```

`release.md`:

```markdown
---
type: release
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
version: {X.Y.Z}
session: ""                       # optional
---

# v{X.Y.Z}

{One paragraph: what this release is, and the window it was built in.}

## Changes

- {one line per change}

## Pointers

- {spec, plan, or decisions behind it}
```

`dream.md`:

```markdown
---
type: dream
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
---

# Dream {YYYY-MM-DD}

{N} findings, {N} acted on, {N} dismissed.

## Acted on

| File | Finding | Action |
|---|---|---|

## Dismissed

| Finding | Why | Suppress until |
|---|---|---|
```

`home.md`:

```markdown
---
type: index
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
---

# Vault

{Generated. Every project, grouped by lifecycle folder, newest activity first.}

## Active

| Project | Last worked |
|---|---|

## Paused

| Project | Last worked |
|---|---|

## Finished

| Project | Finished |
|---|---|

## Archive

| Project | Last worked |
|---|---|
```

`index-project.md`:

```markdown
---
type: index
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
---

# {Project Name}

{Generated. This is where an agent starts.}

## Start here

- [[{slug}/brief|What this is]]
- [[{slug}/_handoff|Where I left off]]

## Specs

| Spec | Status | Cards |
|---|---|---|

## Contents

| Folder | Files | Newest |
|---|---|---|
```

- [ ] **Step 4: Delete the retired templates**

```bash
git rm adjudant/skills/adjudant/templates/dream-report.md \
       adjudant/skills/adjudant/templates/memory.md \
       adjudant/skills/adjudant/templates/iteration.md \
       adjudant/skills/adjudant/templates/_index-collection.md \
       adjudant/skills/adjudant/templates/_index-projects.md
```

`memory.md` documented `/adjudant remise`, a verb that exists in neither repo. `iteration.md` was 93% frontmatter with one user in the whole vault. The two `_index-*` templates go with the 113 folder indexes that plan 4 deletes.

- [ ] **Step 5: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_templates -v 2>&1 | tail -5`
Expected: `OK`. All fifteen kinds now have a template and `TestEveryTemplate` passes.

- [ ] **Step 6: Commit**

```bash
git add adjudant/skills/adjudant/templates/ adjudant/scripts/test_templates.py
git commit -m "feat(adjudant): the four generated templates; five retired

handoff stops being a mirror and gains the three sections a person actually
writes. dream leads with a machine-readable count the statusline reads and
gains a Dismissed table, because two consecutive reports dismissed the same
finding in identical words.

Retired: memory.md (its verb never existed), iteration.md (93% frontmatter),
dream-report.md, and the two folder-index templates.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Build the schema parser

**Files:**
- Create: `adjudant/scripts/_template_schema.py`
- Create: `adjudant/scripts/test__template_schema.py`

**Interfaces:**
- Consumes: the fifteen templates from Tasks 2 to 4 and the comment convention from Task 1.
- Produces, imported by Task 6:
  - `load_schema(templates_dir: Path) -> dict[str, dict]` — maps kind to `{"required": frozenset[str], "optional": frozenset[str], "vocab": dict[str, tuple[str, ...]], "headings": tuple[str, ...], "conditional": dict[str, tuple[str, ...]]}`.
  - `TEMPLATES_DIR: Path` — the shipped directory.
  - `FIELD_SCHEMA: dict[str, dict[str, frozenset[str]]]` — the `required`/`optional` view, shaped exactly like the constant it replaces so existing callers need no change.
  - `STATUS_VALUES_FOR_TYPE: dict[str, tuple[str, ...]]` — derived from the `status` field's vocabulary comment.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test__template_schema.py`:

```python
"""Tests for _template_schema.py — the parser that makes templates the schema.

The test that matters most is test_deleting_a_field_changes_the_schema: if it
ever fails, a second declaration has crept back in and the whole design has
regressed.
"""

import tempfile
import unittest
from pathlib import Path

from _template_schema import (
    FIELD_SCHEMA,
    STATUS_VALUES_FOR_TYPE,
    TEMPLATES_DIR,
    load_schema,
)


class TestParsing(unittest.TestCase):

    def _write(self, tmp: Path, name: str, text: str) -> None:
        (tmp / name).write_text(text)

    def test_bare_field_is_required(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._write(tmp, "thing.md",
                        "---\ntype: thing\ncreated: x\n---\n\n# T\n\nbody\n")
            s = load_schema(tmp)
            self.assertEqual(s["thing"]["required"], frozenset({"type", "created"}))
            self.assertEqual(s["thing"]["optional"], frozenset())

    def test_optional_comment_makes_it_optional(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._write(tmp, "thing.md",
                        '---\ntype: thing\nnote: ""    # optional\n---\n\n# T\n\nbody\n')
            s = load_schema(tmp)
            self.assertEqual(s["thing"]["required"], frozenset({"type"}))
            self.assertEqual(s["thing"]["optional"], frozenset({"note"}))

    def test_pipe_comment_is_a_required_vocabulary(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._write(tmp, "thing.md",
                        "---\ntype: thing\nstatus: a    # a | b | c\n---\n\n# T\n\nbody\n")
            s = load_schema(tmp)
            self.assertIn("status", s["thing"]["required"])
            self.assertEqual(s["thing"]["vocab"]["status"], ("a", "b", "c"))

    def test_optional_vocabulary(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._write(tmp, "thing.md",
                        "---\ntype: thing\nk: a    # optional: a | b\n---\n\n# T\n\nbody\n")
            s = load_schema(tmp)
            self.assertIn("k", s["thing"]["optional"])
            self.assertEqual(s["thing"]["vocab"]["k"], ("a", "b"))

    def test_headings_are_collected(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._write(tmp, "thing.md",
                        "---\ntype: thing\n---\n\n# T\n\n## One\n\nx\n\n## Two\n\ny\n")
            s = load_schema(tmp)
            self.assertEqual(s["thing"]["headings"], ("One", "Two"))

    def test_conditional_headings_are_separated(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._write(tmp, "thing.md",
                        "---\ntype: thing\n---\n\n# T\n\n## Always\n\nx\n\n"
                        "## Sometimes\n<!-- when: coding, plugin -->\n\ny\n")
            s = load_schema(tmp)
            self.assertEqual(s["thing"]["headings"], ("Always",))
            self.assertEqual(s["thing"]["conditional"]["Sometimes"], ("coding", "plugin"))

    def test_two_files_one_kind_must_agree(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._write(tmp, "a.md", "---\ntype: index\nx: 1\n---\n\n# A\n\nbody\n")
            self._write(tmp, "b.md", "---\ntype: index\nx: 2\n---\n\n# B\n\nbody\n")
            load_schema(tmp)   # same key set: fine

    def test_two_files_one_kind_disagreeing_raises(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._write(tmp, "a.md", "---\ntype: index\nx: 1\n---\n\n# A\n\nbody\n")
            self._write(tmp, "b.md", "---\ntype: index\ny: 2\n---\n\n# B\n\nbody\n")
            with self.assertRaises(ValueError):
                load_schema(tmp)

    def test_readme_is_skipped(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._write(tmp, "README.md", "# Templates\n\nprose, no frontmatter\n")
            self._write(tmp, "thing.md", "---\ntype: thing\n---\n\n# T\n\nbody\n")
            self.assertEqual(set(load_schema(tmp)), {"thing"})


class TestShippedSchema(unittest.TestCase):

    def test_all_fifteen_kinds_load(self):
        expected = {
            "project", "session", "decision", "task", "note",
            "doc", "source", "spec", "handoff", "index",
            "release", "dream", "component", "api", "schema",
        }
        self.assertEqual(set(FIELD_SCHEMA), expected)

    def test_status_vocabularies_are_derived(self):
        self.assertEqual(STATUS_VALUES_FOR_TYPE["decision"],
                         ("active", "superseded", "reversed"))
        self.assertEqual(STATUS_VALUES_FOR_TYPE["task"],
                         ("backlog", "next", "doing", "review",
                          "done", "icebox", "dropped"))
        self.assertEqual(STATUS_VALUES_FOR_TYPE["spec"],
                         ("draft", "agreed", "superseded"))

    def test_deleting_a_field_changes_the_schema(self):
        """The whole design in one test.

        Removing a line from a template must change what the schema accepts,
        with no Python edit anywhere. If this fails, a second declaration
        exists and the pre-v3 drift is back.
        """
        import shutil
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            for p in TEMPLATES_DIR.glob("*.md"):
                shutil.copy2(p, tmp / p.name)
            before = load_schema(tmp)
            self.assertIn("status", before["decision"]["required"])

            target = tmp / "decision.md"
            target.write_text("\n".join(
                ln for ln in target.read_text().splitlines()
                if not ln.startswith("status:")) + "\n")

            after = load_schema(tmp)
            self.assertNotIn("status", after["decision"]["required"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__template_schema -v`
Expected: FAIL with `ModuleNotFoundError: No module named '_template_schema'`

- [ ] **Step 3: Write the parser**

Create `adjudant/scripts/_template_schema.py`:

```python
#!/usr/bin/env python3
"""The templates ARE the schema.

Before v3 a note's shape was declared three times: FIELD_SCHEMA in
_vault_walk.py, the template file, and a prose section in vault-standards.md,
with validators 28, 29 and 31 existing only to check the three agreed. When
they disagreed the vault was already wrong — the real vault reached 45 `type:`
values and 110 frontmatter keys under that arrangement.

This module parses the shipped templates at import and produces the schema.
There is no second declaration to drift from. Adding a field is editing one
file; if you find yourself editing Python to add a field, the design has
regressed and test__template_schema.test_deleting_a_field_changes_the_schema
should have caught it.

The comment convention is documented for humans in templates/README.md:

    field: value                  -> required
    field: value  # optional      -> optional, omitted when empty
    field: value  # a | b | c     -> required, value must be one of these
    field: value  # optional: a|b -> optional, value must be one of these

and a body heading is required unless it carries `<!-- when: a, b -->`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "skills" / "adjudant" / "templates"

# `key: value  # comment`. The value may be quoted and may itself contain a
# '#', so the comment is only what follows whitespace-hash.
_FIELD_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*):(?P<rest>.*)$")
_COMMENT_RE = re.compile(r"\s+#\s*(?P<comment>.*)$")
_HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
_WHEN_RE = re.compile(r"^<!--\s*when:\s*(?P<kinds>[^>]*?)\s*-->\s*$")


def _split_comment(rest: str) -> tuple[str, str]:
    """Return (value, comment) for the text after `key:`."""
    m = _COMMENT_RE.search(rest)
    if not m:
        return rest.strip(), ""
    return rest[:m.start()].strip(), m.group("comment").strip()


def _parse_rule(comment: str) -> tuple[bool, tuple[str, ...]]:
    """Return (is_optional, vocabulary) for a trailing comment."""
    c = comment.strip()
    if not c:
        return False, ()
    optional = c.startswith("optional")
    if optional:
        c = c[len("optional"):].lstrip(": ").strip()
    vocab = tuple(v.strip() for v in c.split("|") if v.strip()) if "|" in c else ()
    return optional, vocab


def _parse_one(path: Path) -> tuple[str, dict[str, Any]]:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"{path.name}: no frontmatter")
    try:
        end = text.index("\n---", 4)
    except ValueError:
        raise ValueError(f"{path.name}: unterminated frontmatter")
    front, body = text[4:end], text[end + 4:]

    required: set[str] = set()
    optional: set[str] = set()
    vocab: dict[str, tuple[str, ...]] = {}
    kind = ""

    for line in front.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _FIELD_RE.match(line)
        if not m:
            continue                      # a list continuation line
        key = m.group("key")
        value, comment = _split_comment(m.group("rest"))
        is_optional, values = _parse_rule(comment)
        (optional if is_optional else required).add(key)
        if values:
            vocab[key] = values
        if key == "type":
            kind = value

    if not kind:
        raise ValueError(f"{path.name}: no type: value, so it declares no kind")

    headings: list[str] = []
    conditional: dict[str, tuple[str, ...]] = {}
    lines = body.splitlines()
    for i, line in enumerate(lines):
        hm = _HEADING_RE.match(line)
        if not hm:
            continue
        title = hm.group("title")
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        wm = _WHEN_RE.match(nxt.strip())
        if wm:
            conditional[title] = tuple(
                k.strip() for k in wm.group("kinds").split(",") if k.strip())
        else:
            headings.append(title)

    return kind, {
        "required": frozenset(required),
        "optional": frozenset(optional),
        "vocab": vocab,
        "headings": tuple(headings),
        "conditional": conditional,
    }


def load_schema(templates_dir: Path = TEMPLATES_DIR) -> dict[str, dict[str, Any]]:
    """Parse every template in `templates_dir` into the schema.

    Two files may declare the same kind (home.md and index-project.md are both
    `type: index`). They must agree on their key sets; disagreeing is a build
    error, not a silent merge, because a reader of either file would otherwise
    be reading a rule that is not enforced.
    """
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(templates_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        kind, parsed = _parse_one(path)
        prior = out.get(kind)
        if prior is None:
            out[kind] = parsed
            continue
        if (prior["required"] != parsed["required"]
                or prior["optional"] != parsed["optional"]):
            raise ValueError(
                f"two templates declare kind '{kind}' with different fields: "
                f"required {sorted(prior['required'])} vs {sorted(parsed['required'])}")
        # Same fields, different bodies: keep the union of headings so a file
        # of either shape validates.
        merged = dict(prior)
        merged["headings"] = tuple(sorted(set(prior["headings"]) | set(parsed["headings"])))
        out[kind] = merged
    return out


_SCHEMA = load_schema()

# The view existing callers already expect, so nothing downstream changes.
FIELD_SCHEMA: dict[str, dict[str, frozenset[str]]] = {
    kind: {"required": spec["required"], "optional": spec["optional"]}
    for kind, spec in _SCHEMA.items()
}

# Derived, not declared: the vocabulary is whatever the template's status line
# says it is.
STATUS_VALUES_FOR_TYPE: dict[str, tuple[str, ...]] = {
    kind: spec["vocab"]["status"]
    for kind, spec in _SCHEMA.items()
    if "status" in spec.get("vocab", {})
}

HEADINGS_FOR_TYPE: dict[str, tuple[str, ...]] = {
    kind: spec["headings"] for kind, spec in _SCHEMA.items()
}
```

- [ ] **Step 4: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test__template_schema -v`
Expected: PASS, 12 tests. `test_deleting_a_field_changes_the_schema` is the one to watch.

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/_template_schema.py adjudant/scripts/test__template_schema.py
git commit -m "feat(adjudant): parse the schema out of the templates

The shape of a note was declared three times, with three validators whose only
job was checking the three agreed. This parses the templates at import and is
the single declaration.

test_deleting_a_field_changes_the_schema is the design in one assertion:
removing a line from a template must change what check accepts, with no Python
edit anywhere.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Replace the constant with the derived schema

**Files:**
- Modify: `adjudant/scripts/_vault_walk.py:905-1038` (delete the constants, import the derived ones)
- Test: `adjudant/scripts/test__vault_walk.py`

**Interfaces:**
- Consumes: `FIELD_SCHEMA`, `STATUS_VALUES_FOR_TYPE`, `HEADINGS_FOR_TYPE` from `_template_schema` (Task 5).
- Produces: `_vault_walk.FIELD_SCHEMA` and `_vault_walk.STATUS_VALUES_FOR_TYPE` keep their names and shapes, so `pretooluse-schema-gate.py`, `tidy.py`, `dream.py`, `check.py` and `board.py` need no change. This is deliberate: the inversion should be invisible to every consumer.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test__vault_walk.py`:

```python
class TestSchemaIsDerived(unittest.TestCase):

    def test_vault_walk_reexports_the_template_schema(self):
        import _template_schema
        import _vault_walk
        self.assertIs(_vault_walk.FIELD_SCHEMA, _template_schema.FIELD_SCHEMA)
        self.assertIs(_vault_walk.STATUS_VALUES_FOR_TYPE,
                      _template_schema.STATUS_VALUES_FOR_TYPE)

    def test_no_hand_written_field_schema_remains(self):
        # A literal FIELD_SCHEMA dict in this file would be the second
        # declaration this plan exists to remove.
        src = Path(_vault_walk.__file__).read_text()
        self.assertNotIn("FIELD_SCHEMA: dict[str, dict[str, frozenset[str]]] = {", src)
        for gone in ("DECISION_STATUS_VALUES", "TASK_STATUS_VALUES",
                     "ITERATION_STATUS_VALUES", "_EPISTEMIC_OPTIONAL",
                     "FRESHNESS_VALUES", "MEMORY_HEADINGS"):
            self.assertNotIn(f"{gone}:", src, f"{gone} survived")

    def test_the_retired_kinds_are_absent(self):
        import _vault_walk
        for gone in ("memory", "iteration", "dream-report", "vault-home"):
            self.assertNotIn(gone, _vault_walk.FIELD_SCHEMA)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestSchemaIsDerived -v`
Expected: FAIL — `FIELD_SCHEMA` is still a literal in `_vault_walk.py`.

- [ ] **Step 3: Delete the constants and import the derived ones**

In `adjudant/scripts/_vault_walk.py`, delete `PROJECT_STATUS_VALUES` (line 900),
then everything from the `DECISION_STATUS_VALUES` definition (line 909) through
the close of the `FIELD_SCHEMA` literal (line 1038). That removes
`DECISION_STATUS_VALUES`, `TASK_STATUS_VALUES`, `ITERATION_STATUS_VALUES`,
`STATUS_VALUES_FOR_TYPE`, `_CONTENT_OPTIONAL`, `FRESHNESS_VALUES`,
`_EPISTEMIC_OPTIONAL`, `MEMORY_HEADINGS` and `FIELD_SCHEMA`.

`PROJECT_STATUS_VALUES` goes because the brief has no `status:` field: the zone
folder is the project's state, and `shelf` is deleted in plan 3.

In their place:

```python
# ============================================================
# Note-level schema — DERIVED, not declared (v3)
# ============================================================
# The templates are the schema. Editing a template changes what check accepts;
# there is no constant here to fall out of step with it. See
# _template_schema.py and templates/README.md.
#
# The epistemic block (freshness / certainty / validity_context / valid_from /
# valid_until) is gone with the constants: five optional fields serving two
# read-only reporters, whose malformed values were the strictest thing the
# write gate blocked on. So are the Bucket-A tag constants — a tag that
# restates `type:` carries no information, and there were ~1735 of them.

from _template_schema import (          # noqa: E402  (after the parser exists)
    FIELD_SCHEMA,
    HEADINGS_FOR_TYPE,
    STATUS_VALUES_FOR_TYPE,
)
```

Move that import to the top of the file with the other imports; the comment stays where the constants were, pointing at it.

- [ ] **Step 4: Fix the fallout**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -20`

Expect failures in modules referencing the deleted names. Resolve each as follows, and make no other change:

| Symbol | Resolution |
|---|---|
| `PROJECT_STATUS_VALUES` in `STATUS_VALUES_FOR_TYPE` | Gone. The brief has no `status:` field; the zone folder is the status. Delete the reference. |
| `FRESHNESS_VALUES`, `_EPISTEMIC_OPTIONAL` | Gone. Delete the epistemic branch in `pretooluse-schema-gate.py` and `schema_drift_for_file`'s `epistemic_invalid` key. |
| `MEMORY_HEADINGS` | Gone with the `memory` kind. |
| `BUCKET_A_TYPES` used as "the set of known kinds" | Replace with `frozenset(FIELD_SCHEMA)`. |
| `ITERATION_STATUS_VALUES` | Gone with the `iteration` kind. |

- [ ] **Step 5: Run the suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -3`
Expected: validators 4, 23, 26, 28, 29 and 31 fail. That is correct and Task 7 removes them. Do not patch them here.

- [ ] **Step 6: Commit**

```bash
git add adjudant/scripts/_vault_walk.py adjudant/scripts/test__vault_walk.py adjudant/hooks/scripts/pretooluse-schema-gate.py
git commit -m "refactor(adjudant): FIELD_SCHEMA is derived from the templates

The constant is deleted and _vault_walk re-exports the parsed schema, so every
consumer is unchanged. The epistemic block goes with it: five optional fields
serving two reporters, and the strictest thing the write gate blocked on.

Validators 4, 23, 26, 28, 29 and 31 fail after this commit by design; they
check that two declarations agree and there is now only one. Task 7 removes
them.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Delete the parity validators

**Files:**
- Modify: `adjudant/scripts/validate.py` (docstring registry and six validator functions)
- Test: `adjudant/scripts/test_validate.py`

**Interfaces:**
- Consumes: Task 6's derived schema.
- Produces: `validate.py` reports 29 validators. One new validator replaces the six: `template-schema-loads`, which asserts the parser succeeds and yields exactly the fifteen kinds.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_validate.py`:

```python
class TestParityValidatorsRemoved(unittest.TestCase):

    def test_the_six_are_gone(self):
        src = Path(validate.__file__).read_text()
        for name in ("template-coverage", "status-vocabulary",
                     "task-status-vocabulary", "decision-status-vocabulary",
                     "template-schema-parity", "freshness-vocabulary"):
            self.assertNotIn(name, src,
                             f"{name} survived; it checks a second declaration "
                             "that no longer exists")

    def test_the_replacement_exists(self):
        src = Path(validate.__file__).read_text()
        self.assertIn("template-schema-loads", src)

    def test_declared_count_matches_reality(self):
        src = Path(validate.__file__).read_text()
        declared = int(re.search(r"(\d+) validators total", src).group(1))
        listed = len(re.findall(r"^\s*\d+\. [a-z-]+", src, re.M))
        self.assertEqual(declared, listed)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_validate.TestParityValidatorsRemoved -v`
Expected: FAIL — all six names are still present.

- [ ] **Step 3: Delete the six and add the replacement**

Delete these validator functions and their registry lines from `adjudant/scripts/validate.py`:

| # | Name | Why it goes |
|---|---|---|
| 4 | `template-coverage` | Checked every kind in vault-standards has a template. The templates now *are* the kinds. |
| 23 | `status-vocabulary` | Checked constants, prose and templates agree on project status. There is no project status. |
| 26 | `task-status-vocabulary` | Checked every board alias is documented. There are no aliases. |
| 28 | `decision-status-vocabulary` | Checked three declarations agree. There is one. |
| 29 | `template-schema-parity` | Checked templates match `FIELD_SCHEMA`. They *are* `FIELD_SCHEMA`. |
| 31 | `freshness-vocabulary` | The epistemic block is gone. |

Add in their place:

```python
def validate_template_schema_loads(r: Result) -> None:
    """N. template-schema-loads — the templates parse into exactly the fifteen
    kinds, and every declared vocabulary is non-empty.

    This is the only validator the schema needs now. The six it replaces all
    checked that two declarations agreed; with one declaration the question
    cannot be asked, and the only remaining risk is a template that does not
    parse or a kind that quietly appears or disappears.
    """
    name = "template-schema-loads"
    expected = {
        "project", "session", "decision", "task", "note",
        "doc", "source", "spec", "handoff", "index",
        "release", "dream", "component", "api", "schema",
    }
    try:
        import _template_schema
        schema = _template_schema.load_schema()
    except Exception as e:
        r.add_fail(name, f"templates do not parse: {e}")
        return
    got = set(schema)
    if got != expected:
        missing, extra = sorted(expected - got), sorted(got - expected)
        r.add_fail(name, f"kinds drifted — missing {missing}, unexpected {extra}")
        return
    for kind, spec in schema.items():
        for field, values in spec.get("vocab", {}).items():
            if not values:
                r.add_fail(name, f"{kind}.{field} declares an empty vocabulary")
                return
    r.add_pass(name)
```

Renumber the registry in the module docstring and update the total to 29.

- [ ] **Step 4: Run the validators and the suite**

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -3`
Expected: `PASS — 29 validator(s) green`

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/validate.py adjudant/scripts/test_validate.py
git commit -m "refactor(adjudant): delete the six parity validators

Every one existed to check that two or three declarations of the same rule
agreed. There is one declaration now, so the question cannot be asked. One
validator replaces them: the templates parse into exactly fifteen kinds.

35 validators become 29.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: One renderer, and no inline fallbacks

**Files:**
- Create: `adjudant/scripts/_render.py`
- Create: `adjudant/scripts/test__render.py`
- Modify: `adjudant/scripts/connect.py:500-520` and `:419-430`, `adjudant/scripts/board_bridge.py`, `adjudant/hooks/scripts/posttooluse-commit-log.py:253-271`

**Interfaces:**
- Consumes: `_template_schema.TEMPLATES_DIR` and `load_schema` (Task 5).
- Produces: `render(kind: str, fields: dict[str, str], body: dict[str, str] | None = None) -> str`. Fills the template's frontmatter from `fields`, **omitting any optional field whose value is empty**, and substitutes `{placeholder}` tokens in the body from `body`. Raises `FileNotFoundError` when the template is missing: a missing template is a loud failure, never a silent substitution.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test__render.py`:

```python
"""Tests for _render.py — the single writer for every mechanical vault write.

Four code paths used to carry a hardcoded copy of a template for when the file
was missing. Each was a second declaration waiting to drift, and one of them
(board_bridge) had already drifted far enough that its output carried the
template's guidance comments into card ids.
"""

import unittest

from _render import render


class TestRender(unittest.TestCase):

    def test_required_fields_are_filled(self):
        out = render("decision", {
            "created": "2026-09-01", "updated": "2026-09-01", "status": "active"})
        self.assertIn("type: decision", out)
        self.assertIn("created: 2026-09-01", out)
        self.assertIn("status: active", out)

    def test_empty_optional_fields_are_omitted(self):
        # 181 fields in the real vault held nothing but an empty string.
        out = render("decision", {
            "created": "2026-09-01", "updated": "2026-09-01", "status": "active",
            "superseded_by": "", "session": ""})
        self.assertNotIn("superseded_by:", out)
        self.assertNotIn("session:", out)

    def test_present_optional_fields_are_kept(self):
        out = render("decision", {
            "created": "2026-09-01", "updated": "2026-09-01",
            "status": "active", "session": "4f2a"})
        self.assertIn("session: 4f2a", out)

    def test_no_guidance_comments_survive(self):
        # The frontmatter parser keeps a trailing comment on a quoted value,
        # which is how template guidance ended up poisoning card ids.
        out = render("task", {
            "created": "2026-09-01", "updated": "2026-09-01", "status": "doing"})
        front = out.split("---")[1]
        self.assertNotIn("#", front)

    def test_body_placeholders_are_substituted(self):
        out = render("decision",
                     {"created": "2026-09-01", "updated": "2026-09-01",
                      "status": "active"},
                     {"What was decided": "Bucket-A tags go"})
        self.assertIn("# Bucket-A tags go", out)

    def test_unsubstituted_placeholders_survive_for_a_human(self):
        out = render("decision", {
            "created": "2026-09-01", "updated": "2026-09-01", "status": "active"})
        self.assertIn("{What was decided}", out)

    def test_missing_template_raises(self):
        with self.assertRaises(FileNotFoundError):
            render("no-such-kind", {})

    def test_every_shipped_kind_renders(self):
        from _template_schema import FIELD_SCHEMA
        for kind in FIELD_SCHEMA:
            out = render(kind, {"created": "2026-09-01", "updated": "2026-09-01"})
            self.assertTrue(out.startswith("---\n"), kind)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__render -v`
Expected: FAIL with `ModuleNotFoundError: No module named '_render'`

- [ ] **Step 3: Write the renderer**

Create `adjudant/scripts/_render.py`:

```python
#!/usr/bin/env python3
"""One renderer for every mechanical vault write.

Six writers used to hand-build markdown from string literals, and four carried
a hardcoded fallback copy of a template for when the file was missing. Each
fallback was a second declaration, and one had already drifted far enough to
carry the template's guidance comments into card ids.

A write goes through here or it is a bug. A missing template raises rather
than substituting something plausible: a loud failure is recoverable, a quiet
wrong one is what filled the vault.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from _template_schema import TEMPLATES_DIR, load_schema

# Filenames differ from kind names in two cases (brief.md is `project`, and
# home.md / index-project.md are both `index`), so the map is built from the
# parsed `type:` value rather than assumed from the filename.
_COMMENT_RE = re.compile(r"\s+#\s.*$")


def _template_for(kind: str) -> Path:
    for path in sorted(TEMPLATES_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        head = path.read_text()[:400]
        m = re.search(r"^type:\s*(\S+)", head, re.M)
        if m and m.group(1) == kind:
            return path
    raise FileNotFoundError(
        f"no template declares kind '{kind}' in {TEMPLATES_DIR}")


def render(kind: str, fields: dict[str, str],
           body: Optional[dict[str, str]] = None) -> str:
    """Render a note of `kind`, filling `fields` and substituting `body`.

    An optional field whose value is empty or absent is omitted entirely,
    never written as `""`. Guidance comments never survive into output.
    Body placeholders left unfilled stay as `{Their Name}`, so a human editing
    the file afterwards can see what belongs there.
    """
    path = _template_for(kind)
    text = path.read_text()
    schema = load_schema()[kind]

    end = text.index("\n---", 4)
    front_lines = text[4:end].splitlines()
    out_lines: list[str] = []

    for line in front_lines:
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$", line)
        if not m:
            continue
        key = m.group(1)
        if key == "type":
            out_lines.append(f"type: {kind}")
            continue
        value = str(fields.get(key, "")).strip()
        if not value and key in schema["optional"]:
            continue                       # omit, never write an empty string
        if not value:
            # A required field with no value keeps the template's own token so
            # the gap is visible rather than silently blank.
            value = _COMMENT_RE.sub("", m.group(2)).strip()
        out_lines.append(f"{key}: {value}")

    rendered_body = text[end + 4:]
    for placeholder, replacement in (body or {}).items():
        rendered_body = rendered_body.replace("{" + placeholder + "}", replacement)

    return "---\n" + "\n".join(out_lines) + "\n---" + rendered_body
```

- [ ] **Step 4: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test__render -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Route the writers through it and delete the fallbacks**

In `connect.py`, replace the template-or-fallback branch at lines ~490-520 with a single `render("session", {...})` call, and the brief write at ~419-430 with `render("project", {...})`. Delete the `else:` fallback block entirely.

In `board_bridge.py`, delete `_FALLBACK_TEMPLATE` and `_strip_frontmatter_comments` if plan 1 has not already removed them, and route any remaining task write through `render("task", {...})`.

In `posttooluse-commit-log.py`, replace `_release_note` / `_release_frontmatter` (lines ~248-271) with `render("release", {...})`. Note plan 1 deleted the auto-stub; if only the index row remains, this step is a no-op and should be recorded as such in the commit.

- [ ] **Step 6: Run the full suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 7: Commit**

```bash
git add adjudant/scripts/_render.py adjudant/scripts/test__render.py adjudant/scripts/connect.py adjudant/scripts/board_bridge.py adjudant/hooks/scripts/posttooluse-commit-log.py
git commit -m "feat(adjudant): one renderer, and the inline template fallbacks deleted

Four writers carried a hardcoded copy of a template for when the file was
missing. Each was a second declaration, and board_bridge's had drifted far
enough to carry guidance comments into card ids. A missing template now raises.

An optional field with no value is omitted rather than written as an empty
string: 181 fields in the real vault held nothing else.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Retire tags, and prove the schema bites

**Files:**
- Modify: `adjudant/scripts/_vault_walk.py` (tag bucket constants), `adjudant/scripts/tidy.py` (`normalize_tags`)
- Create: `adjudant/scripts/test_schema_enforcement.py`
- Test: `adjudant/scripts/test_tidy.py`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing new. This task removes and proves.

- [ ] **Step 1: Write the acceptance test**

Create `adjudant/scripts/test_schema_enforcement.py`:

```python
"""Acceptance test for plan 2: the template is the schema, and it bites.

Before v3 nothing ever compared a real vault file to its template, which is
how the vault reached 45 type values, 110 frontmatter keys and 420 tags.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from _template_schema import FIELD_SCHEMA, TEMPLATES_DIR, load_schema
from _vault_walk import schema_drift_for_text


class TestSchemaBites(unittest.TestCase):
    """`schema_drift_for_text` returns Optional[dict] and omits a key entirely
    when that class of drift is absent, so every assertion below goes through
    `.get()` with a default rather than indexing."""

    def _drift(self, text: str, rel: str) -> dict:
        return schema_drift_for_text(text, rel) or {}

    def test_a_missing_required_field_is_drift(self):
        text = "---\ntype: decision\ncreated: 2026-09-01\nupdated: 2026-09-01\n---\n\n# X\n"
        drift = self._drift(text, "decisions/x.md")
        self.assertIn("status", drift.get("missing_required", []))

    def test_a_retired_field_is_unknown(self):
        text = ("---\ntype: note\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
                "tags:\n  - note\n---\n\n# X\n")
        drift = self._drift(text, "notes/x.md")
        self.assertIn("tags", drift.get("unknown_fields", []))

    def test_an_off_vocabulary_status_is_reported(self):
        text = ("---\ntype: task\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
                "status: obsolete\n---\n\n# X\n")
        drift = self._drift(text, "tasks/x.md")
        invalid = drift.get("status_invalid") or {}
        self.assertEqual(invalid.get("value"), "obsolete",
                         "the value someone had to invent is still accepted")

    def test_dropped_is_now_a_real_status(self):
        text = ("---\ntype: task\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
                "status: dropped\n---\n\n# X\n")
        drift = self._drift(text, "tasks/x.md")
        self.assertIsNone(drift.get("status_invalid"))

    def test_editing_a_template_changes_enforcement(self):
        """One declaration, proven end to end."""
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            for p in TEMPLATES_DIR.glob("*.md"):
                shutil.copy2(p, tmp / p.name)
            self.assertIn("verified", load_schema(tmp)["doc"]["required"])
            doc = tmp / "doc.md"
            doc.write_text("\n".join(
                ln for ln in doc.read_text().splitlines()
                if not ln.startswith("verified:")) + "\n")
            self.assertNotIn("verified", load_schema(tmp)["doc"]["required"])


class TestTagsAreGone(unittest.TestCase):

    def test_no_kind_accepts_tags(self):
        for kind, spec in FIELD_SCHEMA.items():
            self.assertNotIn("tags", spec["required"] | spec["optional"],
                             f"{kind} still accepts tags")

    def test_the_bucket_constants_are_gone(self):
        import _vault_walk
        src = Path(_vault_walk.__file__).read_text()
        for gone in ("BUCKET_A_TYPES", "BUCKET_B_MIGRATIONS",
                     "BUCKET_D_TAG_EXACT", "BUCKET_D_TAG_PREFIXES",
                     "PROJECT_TYPE_TAGS", "CREW_NAMES",
                     "VAGUE_TOPICAL_TAGS", "PROJECT_STATUS_VALUES"):
            self.assertNotIn(f"{gone}:", src, f"{gone} survived")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_schema_enforcement -v`
Expected: FAIL — the bucket constants are still present.

- [ ] **Step 3: Delete the tag machinery**

In `_vault_walk.py`, delete these, with their real line numbers:

| Line | Symbol |
|---|---|
| 829 | `BUCKET_A_TYPES` |
| 834 | `BUCKET_A_TYPES_PLUS_HOME` |
| 837 | `BUCKET_B_MIGRATIONS` |
| 847 | `BUCKET_D_TAG_PREFIXES` |
| 849 | `VAGUE_TOPICAL_TAGS` |
| 856 | `CREW_NAMES` |
| 861 | `PROJECT_TYPE_TAGS` |
| 865 | `BUCKET_D_TAG_EXACT` |
| 1533 | `is_bucket_d_tag` |
| 1555 | `is_bucket_b_migration` |

`VAGUE_TOPICAL_TAGS` and `CREW_NAMES` are also two of the four constants that
forked between the trees, so deleting them here removes work from plan 5.

In `tidy.py`, delete `_migrate_ob_to_bucket_a` (line 70), `normalize_tags`
(line 114) and `_rewrite_tags_block` (line 409), and remove the tag feature from
the preview builder. `clean` in plan 3 strips `tags:` as an unknown field through the schema, which is the general mechanism rather than a special case.

Replace every `BUCKET_A_TYPES` use with `frozenset(FIELD_SCHEMA)`.

- [ ] **Step 4: Run the suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`. Validator 2 (`templates-tag-schema`, `validate.py:155`) checks
that no template carries a deprecated `#ob/` or `#cabinet/` tag. No template
carries any tag at all now, so delete it and update the count to 28.

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS — 28 validator(s) green`

- [ ] **Step 5: Update the README test count**

`adjudant/README.md:66` carries the test count. Update it from the suite output.

- [ ] **Step 6: Commit**

```bash
git add adjudant/scripts/ adjudant/README.md
git commit -m "feat(adjudant): retire tags entirely

Every file carried exactly one tag restating its own type field: ~1735
applications conveying nothing, maintained by four bucket constants, a
normaliser, three helpers and a validator. The nested a/b form the buckets
existed to police was never enforced at all.

Stripping tags is now an ordinary unknown-field strip through the schema,
which is the general mechanism rather than a special case.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Done when

- `python3 -m unittest discover -p 'test_*.py'` reports `OK`.
- `python3 adjudant/scripts/validate.py` reports `PASS — 28 validator(s) green`.
- `test__template_schema.test_deleting_a_field_changes_the_schema` passes.
- `test_schema_enforcement.test_editing_a_template_changes_enforcement` passes.
- `grep -rn "FIELD_SCHEMA.*= {" adjudant/scripts/_vault_walk.py` returns nothing.
- Fifteen templates exist and no sixteenth.

## Not in this plan

The verb surface, `clean` and the dream rebuild are plan 3. Lifecycle folders, the link form, index generation and the truth checks are plan 4. Twin generation is plan 5.

The vault's existing files are not migrated here. This plan changes what adjudant writes and what it accepts; plan 4's `clean` does the vault-side migration, because it needs the lifecycle folders and the link rewrite to land in the same pass.
