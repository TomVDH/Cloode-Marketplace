# Using Adjudant

A walkthrough, from installing it to living with it. For the terse reference, see [README.md](README.md).

## What it's for

You work in a code project. The thinking around that project — why you made a decision, what you tried last week, what's half-finished — usually lives in your head or scrolls out of a chat. Adjudant writes it down, in an Obsidian vault, in a consistent shape, and keeps it current without you managing it.

The mental model: **your code project is the work, the vault is its memory.** You keep coding; adjudant keeps the record.

You don't have to open Obsidian for any of this. The vault is plain markdown files. Obsidian just makes them nice to browse.

## 1. Install and link

Install once per machine:

```
/plugin marketplace add TomVDH/toolshed
/plugin install adjudant
```

Link each project once:

```
/adjudant connect
```

`connect` looks at your project, proposes a vault location, a slug, a type, and a status, and shows you one card to confirm. Approve it and it writes:

- `.claude/adjudant` — a small breadcrumb pointing at the vault. Every later verb reads this, so you never type vault paths.
- A project folder in the vault, with a `brief.md`, a `sessions/` folder, and the scaffolding.
- Today's session note.

`connect` is idempotent. Running it again on a linked project changes nothing.

**No vault yet?** Point `connect` at where you want one and it scaffolds it.

## 2. A normal session

After connect, most of adjudant is invisible. As you work:

- A **session note** for today is created and kept updated. Commits, decisions, and notes you write land in it.
- When you write a decision or a note into the vault, adjudant checks its shape first. If a required field is missing, the write is blocked with a message saying what's wrong, so it never lands malformed.
- A **handoff** file tracks where things stand, so the next session (or the same project on another machine) starts oriented.

You don't call a verb for any of that. It rides on hooks.

## 3. Tasks and the board

Write a task note under the project's `tasks/` folder and a **kanban board** is born automatically. From then on:

- The board reseeds itself when tasks change.
- Open it with `/adjudant board serve` — a single HTML file, drag cards between columns, changes save to disk.
- A card you drag writes its new status back into the task note, so the board and your notes never disagree.

You can also edit the board's `kanban.md` inside Obsidian; the drag is read back the same way.

Projects that never grow tasks never grow board files. Nothing to clean up.

## 4. Checking in

Two read-only verbs, neither writes anything:

- `/adjudant sitrep` — orientation after a break. Where you left off, what's done, where the vault is, what's next, plus your git and dev-server state. Start here when you come back to a project cold.
- `/adjudant check` — a health report. Project and vault snapshot, plus any notes that have drifted off-schema. Add `check repo` to also audit the code repo's structure, or `check all` for both.

## 5. Keeping the vault clean

Three verbs, in a deliberate ladder from safe to careful. Match the verb to how much you want to trust it:

| Verb | Cadence | What it touches | Risk |
|---|---|---|---|
| `tidy` | routine (daily/weekly) | indexes, wikilink form, dates, off-schema frontmatter | none — it never breaks anything |
| `ramasse` | sparing (quarterly) | folder shape, file types, naming, broken wikilinks | deliberate structural change, under your review |
| `dream` | as needed | the actual prose — stale, contradictory, redundant, or orphaned content | semantic, LLM-judged; you approve every change |

`tidy` and `ramasse` both **preview first**: they show you exactly what they'd change and wait. Apply only happens on your say-so, and it backs up what it touches. `dream` is the deepest: it reads the content itself, hands you a catalog of what looks stale or contradictory, and changes nothing until you judge each item.

Heavy verbs estimate their cost before running. If `dream` would pull a large vault into the conversation, it tells you the size and asks before proceeding.

## 6. Diagrams

```
/adjudant draw diagram <name>     # a mermaid diagram
/adjudant draw canvas <name>      # an Obsidian canvas
/adjudant draw base <name>        # an Obsidian base (a live table view)
```

Hand-author them, or let adjudant generate one from your vault's own data (project relations, the board, the cleanup tiers).

## 7. Project lifecycle

Projects don't stay active forever. `shelf` moves them between zones:

```
/adjudant shelf                        # list every project and its state
/adjudant shelf my-project fridge      # set aside, still around
/adjudant shelf my-project archive     # done, filed away
/adjudant shelf my-project active      # bring it back
```

A move updates the brief, logs the status change, relocates the folder, and rewrites wikilinks and index rows so nothing dangles.

## Living with it

- **Two machines.** The breadcrumb stores the vault's name as well as its path, so a project synced to another machine re-finds its vault even when the absolute path differs. Pull before you start; adjudant does the rest.
- **The voice.** Adjudant sets a direct, no-filler register for the session and refuses to write slop phrases into vault notes. If you'd rather it didn't, add `voice: off` to `.claude/adjudant` (per project) or set `ADJUDANT_VOICE_DISABLE=1` (per machine).
- **Turning down the noise.** Everything ambient is opt-out via the breadcrumb. The reference docs under `skills/adjudant/reference/` document each knob.

## When something looks wrong

- **A write got blocked.** The message names the missing or malformed field. Fix the frontmatter and write again, or run `/adjudant check` to see every drifted note at once.
- **The board didn't appear.** It's born on the first real task note under `tasks/`. No tasks, no board, by design.
- **A verb can't find the vault.** The breadcrumb is missing or points nowhere. Re-run `/adjudant connect`.
- **You want the details.** `/adjudant check` for state, `reference/internals.md` for how the machinery is wired.

## 8. The advisor (opt-in)

By default adjudant only speaks when spoken to. Turn the advisor on and it
also *notices* — open loops, missing notes, work that contradicts a decision,
context that has gone stale:

```
/adjudant advisor on
```

The flag is visible twice: `advisor: on` in `.claude/adjudant`, and a marker
line in AGENTS.md, so neither you nor a future session can forget it is
active. Every session start announces it.

- Urgent findings (contradicting a locked decision, diverging from the plan)
  surface inline, at most a sentence or two, marked with `❦`.
- Everything else is proposed as a board card or held for the next `check`.
- Nothing is ever written without your yes.

`/adjudant advisor pulse` runs the context-integrity check on demand: expired
facts, dangling supersessions, drift between the plan and the work.
`/adjudant advisor off` removes the flag, the marker, and the behaviour.

## 9. Naming things

Kebab-case is the vault's naming rule, and most of it is on you to follow.
`kebab` answers the question you actually have at write time:

```
/adjudant kebab Fix the parser rewrite
fix-the-parser-rewrite
```

Use it before you create a note, task, source, or decision, and the name is
right the first time.

```
/adjudant kebab --scan
```

Scans the project for filenames whose title broke the rule and shows the
corrected name for each. It never renames anything: renaming breaks every
wikilink pointing at the file, and that repair belongs to `ramasse`, which
previews it and keeps a backup. Docs are exempt, because the standard wants
those UPPERCASE.
