# kebab

Put a name on a skewer. The joke is the name; the work is real.

Kebab-case is the vault's naming law (`vault-standards.md` §4), and §4 admits
most of it goes unchecked: "the rest are on you". `clean --deep` checks doc case,
the decision date prefix, session filenames, and canvas/base names. Nothing
checked the kebab-title portion of a note, a task, a source, or a decision.
This does, and it answers the question you actually have at write time: what
do I call this file?

## Two modes

```
/adjudant kebab <text>     name a thing
/adjudant kebab --scan     find §4 title drift
```

**Naming.** `kebab Fix the parser rewrite` → `fix-the-parser-rewrite`. Use it
before creating a note, task, source, or decision so the name is right the
first time. It delegates to the same slug rule `board_bridge` uses, so a
captured task and a hand-named note can never disagree about what one title
is called.

**Scanning.** `--scan` walks the project and reports every filename whose
title portion breaks §4, with the corrected name. Read-only, cheap, no cost
gate.

## What it checks, and what it leaves alone

| Type | Rule |
|---|---|
| `note`, `task`, `source` | `{kebab-title}.md` |
| `decision` | the title after `{YYYY-MM-DD}-`; the date shape is `clean --deep`'s finding |
| `doc` | **exempt** — §4 wants docs UPPERCASE, and a kebab rule applied blindly would fight the standard it serves |

Also exempt: files written for you (`brief.md`, `_handoff.md`, `_index.md`,
`_iteration.md`, `MEMORY.md`), and folders shaped by another rule
(`sessions/`, `dreams/`, `releases/`, `templates/`, `iterations/`, and the
generated `board/`, `bases/`, `canvases/`).

## It never renames

Renaming a file breaks every wikilink pointing at it, and that repair —
rename, rewrite the links, fix the index rows — is `clean --deep`'s, with its
preview and its backups. kebab tells you; it does not reach for the knife.

Render the scan as one line per violation: the path, then the suggested name.
A clean project gets one line saying so.
