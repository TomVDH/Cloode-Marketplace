---
name: adjudant
description: Operate an Obsidian vault from a code project. `/adjudant {connect|port|sync|check|sitrep|tidy|ramasse|dream|draw|board|shelf}` — project init and migration, schema-enforced writes, three-tier cleanup (tidy/ramasse/dream), read-only status (check) and orientation (sitrep), diagrams and canvases (draw), a self-hosted kanban board, and lifecycle transitions (shelf). Also fires whenever decisions, sessions, or notes are written into a linked vault.
version: 0.16.0
user-invocable: true
argument-hint: "[connect|port|sync|check|sitrep|tidy|ramasse|dream|draw|board|shelf] [args]"
license: MIT
---

# Adjudant

Vault editor/writer and project initializer. One skill, one command, eleven verbs. Pairs with hookify for universal drift-defense hooks, and with Gemineye for Gemini-assisted review hand-off.

## Verb router

| Verb | Loads | Purpose |
|---|---|---|
| `connect` | `reference/connect.md` | Rigid project init — breadcrumb, AGENTS.md+CLAUDE.md, vault scaffold, session note, .gitignore |
| `port` | `reference/port.md` | Migrate any legacy project (raw / obsidian-bridge / hand-authored) to adjudant compliance via two-phase preview → apply |
| `sync` | `reference/sync.md` | Push brief + handoff to vault |
| `check` | `reference/check.md` | Read-only project + vault summary (consumes `check.py` JSON). `[vault\|repo\|all]` also audits repo structure — versions, symlinks, registration, stale plans — via `repo_scan.py` |
| `sitrep` | `reference/sitrep.md` | ELI5 orientation briefing — where we were, what's done, where the vault is, where to start. Read-only (consumes `sitrep.py` JSON). For re-orienting after a break |
| `tidy` | `reference/tidy.md` | Surface mechanical sweep — indexes, tags, wikilink form, `updated:`, frontmatter schema strip/migrate. Routine cadence. Two-phase preview→apply (via `tidy.py`). `[vault\|repo\|all]` also repairs adopted-plugin harness symlinks via `repo_tidy.py` |
| `ramasse` | `reference/ramasse.md` | Deep structural clean — folder shape, schema, file types, naming, doc/decision mismatches. Sparing cadence. Analysis via `ramasse_scan.py`, planning + execute via superpowers |
| `dream` | `reference/dream.md` | Content/knowledge/memory refresh — semantic, judgment-heavy. `dream.py` (read-only) emits a 10-category comparator catalog (staleness, supersession, contradictions, redundancy, stale refs, orphans, unacted decisions, gaps, dangling scopes); Claude judges, superpowers executes |
| `draw` | `reference/draw.md` | Create canvas / base / mermaid diagram — hand-authored or generated from vault data via `graph.py` (relations / board / tiers) |
| `board` | `reference/board.md` | Scaffold a self-hosted work-order kanban — drag-to-move, disk-persisted, seeded from `tasks/`. `--project <slug>` for one project, `--all` for the whole vault; `status` prints terminal column counts |
| `shelf` | `reference/shelf.md` | Project lifecycle: status table across zones (list) and confirmed transitions (preview/apply): brief + status log + zone move + wikilink rewrite + index row |
| _(internals)_ | `reference/internals.md` | Not a verb. Hook wiring, verb-to-helper map, environment probes. Load only when the question is about adjudant's own machinery |

When a verb is invoked, load **only** the matching reference file. Do not bring all reference files into context.

## The locked three-tier model

```
tidy    = surface mechanical    (routine, daily/weekly, never breaks)
ramasse = deep structural clean (sparing, quarterly, deliberate)
dream   = content/knowledge/memory refresh (semantic; judgment-heavy)
```

`dream` reads actual prose and surfaces outdated/contradictory/redundant/stale/orphaned content as *candidates* for Claude to judge. `dream.py` is its read-only analyser: net-new, not to be confused with the v0.3.0 file once named `dream.py` that did structural drift and was renamed `ramasse_scan.py` to feed ramasse's analysis phase.

## Cost gate (locked)

Verb weights live in `scripts/command-metadata.json` (`weight: light | medium | heavy`). The estimate approximates what Claude will read back into context; helpers compute it with a stat-only walk (`bytes // 4`).

- **Heavy verbs** (`dream`, `ramasse`, `check all`): run the backing helper with `--estimate-only` FIRST. If `cost.warn` is true, stop and show the numbers ("dream would pull ~85k tokens into context: 210 files, 1.1 MB prose") and ask the user to choose: proceed, scope down (offer only where the verb has a real scoping flag), or abort. Proceed only on explicit confirmation. If `warn` is false, run normally and include the estimate as one line in the rendered output.
- **Medium verbs** (`check`, `sitrep`, `tidy`): no pre-flight. The helper's JSON carries a `cost` block; render it as one line ("cost: ~12k tokens, 96 files").
- **Light verbs** (`connect`, `sync`, `draw`, `board`, `shelf`): no estimate; the static weight badge is enough (`port` is medium but carries only the static badge; it has no dynamic estimate).
- `check all` sums two estimates: `check.py --estimate-only` plus `repo_scan.py --estimate-only`.
- If an estimate cannot be computed (unresolvable vault or breadcrumb), treat it as `warn: true` and ask before proceeding.
- Threshold default is 30000 estimated read tokens; per-project override via `cost_warn_tokens:` in `.claude/adjudant`.

## Voice (locked)

Load `reference/voice.md` with every verb (the one exception to
load-only-the-matching-reference; it is small). It defines the banned lexicon, the
glazing ban, the pushback contract, the ELI5/ELI12/ELICTO explanation modes with
per-verb defaults, and typography (no em dashes in rendered output or vault writes).
The `voice-lexicon` validator enforces the machine-checkable subset.

## Vault standards — single source of truth

`reference/vault-standards.md` is the authoritative spec for tag taxonomy, frontmatter requirements per file type, folder structure, file-naming rules, and wikilink form. All vault writes must conform. The build's `validate.py` enforces.

## Content authoring

For specialized content types, load the matching reference on demand:

- `reference/content-canvas.md` — `.canvas` files
- `reference/content-bases.md` — `.base` files
- `reference/content-mermaid.md` — mermaid diagrams (syntax)
- `reference/mermaid-generation-rules.md` — mermaid generation discipline (always applies when producing fences)
- `reference/content-markdown.md` — Obsidian-flavoured markdown (callouts, embeds, wikilinks)
- `reference/content-clipper.md` — Web Clipper templates
- `reference/content-cli.md` — Obsidian CLI
- `reference/repo-standards.md` — code-repo conventions (the `check`/`tidy` `[repo|all]` target)

## Templates

`templates/` contains the canonical scaffolds for every file type Adjudant ships. Provisioning is done by `/adjudant connect`. Schema is enforced — every write must match the template frontmatter shape per `reference/vault-standards.md`.

