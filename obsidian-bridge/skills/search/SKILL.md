---
name: search
description: Use when constructing or explaining Obsidian search queries — `tag:`, `path:`, `file:`, `line:`, `block:`, `section:`, `task:`, property `[key:value]`, regex, boolean operators, embedded `query` code blocks.
allowed-tools: Read, Write, Edit, Glob, Grep
version: 0.1.0
source: "https://help.obsidian.md/plugins/search"
upstream_redistribution: "Obsidian Help vault (CC BY 4.0)"
---

# Search

Obsidian's built-in Search supports a rich query language — boolean operators, scoping operators, property filters, and regex. This skill is the reference for writing valid queries (UI search bar, embedded `query` blocks, or vault-bridge tooling that wraps search).

## When to Use

- The user asks how to find files matching a complex condition.
- Writing an embedded `query` block in a Markdown note.
- Designing a Bases filter (Bases formulas use the same operator semantics — see `obsidian-bridge:bases`).
- Validating that a search query the user wrote will return what they expect.

## Boolean basics

| Form | Meaning |
|---|---|
| `meeting work` | Files containing **both** `meeting` and `work` (implicit AND) |
| `meeting OR work` | Files containing **either** `meeting` or `work` |
| `meeting -work` | Files with `meeting` but **not** `work` |
| `"star wars"` | **Exact phrase** (quoted) |
| `"they said \"hello\""` | Quoted phrase containing literal quotes (escaped with `\`) |
| `meeting (work OR meetup) personal` | Parentheses control precedence |
| `meeting -(work meetup)` | Exclude files containing **both** `work` and `meetup` |

Each whitespace-separated token is matched independently within each file.

## Scoping operators

Operators take a value (single word, parenthesised expression, quoted phrase, or regex). Some accept nested boolean queries.

| Operator | Effect | Example |
|---|---|---|
| `file:` | Match in filename | `file:.jpg`, `file:202209` |
| `path:` | Match in full file path | `path:"Daily notes/2022-07"` |
| `content:` | Match in file content (excluding filename/path) | `content:"happy cat"` |
| `match-case:` | Case-sensitive match for value | `match-case:HappyCat` |
| `ignore-case:` | Case-insensitive match | `ignore-case:ikea` |
| `tag:` | Match a tag (prefix `#` optional in operator) | `tag:#work`, `tag:work` |
| `line:` | At least one line in file matches inner query | `line:(mix flour)` |
| `-line:` | NO line in file matches inner query | `-line:(deprecated)` |
| `block:` | Match all terms within a single Markdown block | `block:(dog cat)` |
| `section:` | Match all terms within a single section (between two headings) | `section:(dog cat)` |
| `task:` | Match within any task list item | `task:call` |
| `task-todo:` | Match within an **uncompleted** task | `task-todo:call` |
| `task-done:` | Match within a **completed** task | `task-done:call` |

**Notes on tag matching:** `tag:#work` does NOT match nested `#myjob/work`. To match a nested namespace, use the full nested form (e.g. `tag:#myjob/work`). `tag:` is faster and more accurate than full-text searching for `#work` because it skips code blocks and non-Markdown content.

**Notes on `block:`:** Slower than other operators because it parses Markdown. Use only when needed.

## Property search

Square brackets target [Properties](https://help.obsidian.md/Editing+and+formatting/Properties) (frontmatter values).

| Form | Meaning |
|---|---|
| `[aliases]` | Files where the `aliases` property exists |
| `[aliases:Name]` | Files where `aliases` value matches `Name` |
| `[aliases:null]` | Files where the property exists but has **no value** |
| `[status:Draft OR Published]` | Property value is `Draft` or `Published` |
| `[duration:<5]` | Numeric comparison (`<`, `>`); brackets/quotes required around the operator |
| `[meeting [duration:>5]]` | Combine: text `meeting` AND property `duration > 5` |

`null` matches empty values like `aliases:` but **not** empty quotes `""` or empty arrays `[]`.

## Regex

Surround a JavaScript-flavoured regex with forward slashes (`/.../`).

| Example | Matches |
|---|---|
| `/\d{4}-\d{2}-\d{2}/` | ISO 8601 date in body |
| `path:/\d{4}-\d{2}-\d{2}/` | Same date in file path (combine with operators) |
| `tag:/^proj/` | Any tag starting with `proj` |

Obsidian uses **JavaScript-flavoured** regex (not PCRE). No `(?P<name>...)` named groups, no `\K`, no PCRE-only escapes.

## Embedded `query` blocks

Embed live search results inside a note:

````markdown
```query
tag:#work line:(blocker)
```
````

The block is re-evaluated when the note opens. Useful inside dashboards, briefs, project home notes.

> **`obsidian-bridge` vault?** Common dashboard queries to keep in briefs:
> - `tag:#ob/decision [project:[[projects/{slug}/brief|{slug}]]]` — all decisions for a project
> - `tag:#ob/iteration [status:on-shelf]` — on-shelf iterations across the vault
> - `task-todo: line:(@today)` — uncompleted tasks tagged for today

## Sorting & UI

Sort options (Search dropdown):
- File name (A→Z / Z→A)
- Modified time (new→old / old→new)
- Created time (new→old / old→new)

Embedded `query` blocks always sort by file name; for date sorting, prefer Bases (see `obsidian-bridge:bases`).

## Settings that change behavior

| Setting | Effect |
|---|---|
| **Match case** | Case-sensitive search globally (overrides `ignore-case:` not, augments others) |
| **Explain search term** | Shows a plain-text breakdown of how Obsidian parses your query — invaluable for debugging |
| **Excluded files** (vault settings) | Files matching these patterns never appear in results |

## Quick reference: most-used patterns

```text
# Find an exact phrase in a specific folder
path:"Daily notes" "team meeting"

# All decisions for a project (obsidian-bridge schema)
tag:#ob/decision [project:[[projects/foo/brief|foo]]]

# Files updated this month with a tag
tag:#review path:/2026-05/

# Untagged notes (regex on body)
-tag: /^---$\n((?!tags:).)*\n---$/

# All TODO items mentioning "review"
task-todo:review

# Property exists but is empty
[updated:null]

# Notes with no aliases set
-[aliases]
```

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Query matches everything | Whitespace inside an operator value not parenthesised | Wrap in `()` or `""`: `line:(mix flour)`, not `line:mix flour` |
| Regex doesn't match expected dates | Forgot to escape `\` inside string-quoted regex | Use the `/.../` form, not a quoted string |
| `tag:#proj/sub` returns nothing | Tag is actually `proj/sub` (no leading `#`) and Obsidian treats it as text | Confirm tag exists in Tags pane; the `#` in operator is optional |
| Nested query in `task:` ignored | Forgot parentheses | `task:(call OR email)` not `task:call OR email` |
| Property search returns nothing | Property value type mismatch (number vs string) | Try `[key:"value"]` to force string |
| `line:` query slow | Wide regex against large vault | Narrow with another operator first: `path:notes line:(...)` |

## Cross-references

- Properties / frontmatter the queries target: `obsidian-bridge:vault-standards`
- Bases use similar filter semantics: `obsidian-bridge:bases`
- Docs: <https://help.obsidian.md/plugins/search>
