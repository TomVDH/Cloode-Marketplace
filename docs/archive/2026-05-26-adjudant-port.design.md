---
date: 2026-05-26
status: approved
scope: adjudant plugin — new `port` verb
plugin: adjudant
version-target: 0.2.0
related: 2026-04-30-obsidian-bridge-design.md
---

# `/adjudant:adjudant port` — port legacy projects to adjudant compliance

## Problem statement

Adjudant standardises project context (`AGENTS.md` + `CLAUDE.md`), vault scaffolding, and the breadcrumb that links project ↔ vault. Today, the only onboarding verb is `connect`, which is **idempotent but non-destructive**: it leaves existing context files untouched and only fills gaps.

That works for green-field projects. It doesn't work for any of three legacy populations the user actively maintains:

- **X** — Raw repos with no vault tooling. (`connect` already handles this.)
- **Y** — Projects ported from the now-retired `obsidian-bridge`. Have `.claude/obsidian-bridge` breadcrumb, OB-shaped `AGENTS.md` / `CLAUDE.md`, vault folder in OB layout.
- **Z** — Projects with hand-authored `AGENTS.md` / `CLAUDE.md` (or copied from another standard). No breadcrumb, no adjudant-shaped vault scaffold, idiosyncratic file structure.

For Y and Z, running `connect` does the bare minimum (breadcrumb + vault folders) but leaves legacy `AGENTS.md` / `CLAUDE.md` and the vault `brief.md` un-migrated — the project ends up half-onboarded, never matching the consistency promise adjudant is built around.

This spec defines a new verb `port` that brings any project — X, Y, or Z — to full adjudant compliance in a single safe, idempotent, two-phase operation.

## Goals

1. **Universal entry point.** One verb handles X, Y, Z. Auto-detects the flavor; no flags required.
2. **Two-phase safety.** First run writes a preview. Second run applies. No destructive write without an audit trail.
3. **Doctrinal alignment.** Rigid (no flags), idempotent (re-runs safe), templated (uses the same `templates/` adjudant ships).
4. **Vault-aware.** Migrates both project-root files AND vault folder structure / `brief.md` in one verb.
5. **Recoverable.** Originals always backed up. Always a clear path to revert.
6. **Validator-enforceable.** New `validate.py` checks catch partial / corrupt port states at commit time.

## Non-goals

- Migrating from systems other than `obsidian-bridge`. (Could be added later as new mappings.)
- Automated cross-project porting (a `port-all` verb). Out of scope for v0.2.0.
- Reverting an applied port via a verb. Use the backup dir + git manually.
- Migrating MCP server configs, hooks, or other CC settings. Adjudant's concern is vault + context files only.

## Verb signature

`/adjudant:adjudant port` — no arguments. Always safe to invoke. Behavior changes based on detected project state.

## Detection (auto)

`scripts/port.py` checks the project state in this order:

| Order | Check | If true |
|---|---|---|
| 1 | `.adjudant-port-preview/` exists | **Apply mode** (phase 2) |
| 2 | `.adjudant-port-backup/` exists AND project is adjudant-compliant | "Already ported. Run `/adjudant:adjudant check`." Exit 0. |
| 3 | `.claude/obsidian-bridge` present | **Flavor Y** (OB legacy) |
| 4 | Project-root `AGENTS.md` OR `CLAUDE.md` present with non-template content | **Flavor Z** (hand-authored) |
| 5 | None of the above | **Flavor X** (raw repo). Behaves identically to `connect`. |

"Non-template content" detection (step 4): compute a hash of the file's content (excluding template placeholder values like `{Project Name}`, `{slug}`); compare against hashes of `templates/AGENTS.md` and `templates/CLAUDE.md`. Mismatch → user-authored.

## Phase 1 — Preview (first run)

Writes a fresh `.adjudant-port-preview/` directory containing:

```
.adjudant-port-preview/
├── AGENTS.md.proposed       full proposed new AGENTS.md
├── CLAUDE.md.proposed       full proposed new CLAUDE.md
├── breadcrumb.proposed      proposed `.claude/adjudant` body
├── vault-changes.txt        list of vault-side operations
└── summary.md               explains every move, classification, fold
```

### How preview is generated per flavor

- **Flavor Y:** `port.py` does the full deterministic merge using the OB→adjudant mapping table (below). No AI required.
- **Flavor Z:** `port.py` scaffolds the preview structure. `reference/port.md` then instructs Claude to fill in the AI-classified merge for `AGENTS.md.proposed`, `CLAUDE.md.proposed`, and the per-decision notes in `summary.md`.
- **Flavor X:** `port.py` writes preview as-if running `connect` (vault scaffold, fresh templates filled with detected slug + prompted `project_type`).

User reviews the `.proposed` files. They may edit them freely; phase 2 applies whatever is in the preview directory at apply time, not the original generated content. Re-run `port` to apply.

## Phase 2 — Apply (second run, preview exists)

```
1. Validate preview integrity (validator: port-preview-coherence)
2. Move originals to `.adjudant-port-backup/{ISO-8601-basic-timestamp}/` (e.g. `20260526T163012Z`):
     AGENTS.md            → AGENTS.md.legacy             (if existed)
     CLAUDE.md            → CLAUDE.md.legacy             (if existed)
     .claude/obsidian-bridge → obsidian-bridge.legacy    (Y only)
3. Write `.proposed` files to live positions:
     AGENTS.md.proposed   → AGENTS.md
     CLAUDE.md.proposed   → CLAUDE.md
     breadcrumb.proposed  → .claude/adjudant
4. Apply vault-side changes per vault-changes.txt
     (renames, creates, archives, brief.md merge, _index.md regen)
5. Append `.adjudant-port-preview/` + `.adjudant-port-backup/` to `.gitignore`
6. Append `.claude/adjudant` to `.gitignore` (if not present)
7. Update `projects/_index.md` row in vault
8. Delete `.adjudant-port-preview/`
9. Print summary, recommend `/adjudant:adjudant check`
```

## Merge logic

### AGENTS.md — Flavor Y (deterministic OB → adjudant mapping)

Heading matching is **case-insensitive** with leading/trailing whitespace stripped. Markdown heading level (`##` vs `###`) is ignored; only the text after the hashes matters.

| Old OB section heading (case-insensitive) | New adjudant location |
|---|---|
| `Working tree` | `Where things live` table row (preserves the path noted in OB) |
| `Stack`, `Stack and tools` | `Conventions` section (prose preserved) |
| `Vault rules`, `Vault layout` | **DROPPED.** Now lives in `vault-standards.md` (single source of truth) |
| `Claude instructions`, `Claude-specific` | Moved to `CLAUDE.md` under the `@AGENTS.md` import |
| `Conventions`, `Project rules` | `Conventions` section (merged if multiple) |
| `What this is`, `Purpose`, `Overview` | `What this is` section |
| (any unmatched heading) | `## From legacy AGENTS.md` section appended at end |

The mapping is encoded as a dict in `port.py`; adding new aliases is a one-line change.

### Edge case: both legacy markers present

If `.claude/obsidian-bridge` AND `.claude/adjudant` both exist (interrupted previous port, or manual partial migration), detection treats this as Flavor Y. Existing `.claude/adjudant` is treated as part of the "original state" and gets backed up to `.adjudant-port-backup/{ts}/adjudant.legacy` before being overwritten with the new `breadcrumb.proposed`. summary.md notes the collision and lists both pre-existing breadcrumbs.

### AGENTS.md — Flavor Z (AI classifier)

Claude runs during preview phase. For each heading in the legacy file, classify into one of:

| Bucket | Goes to |
|---|---|
| `template-section:what-this-is` | `What this is` section in new AGENTS.md |
| `template-section:conventions` | `Conventions` section |
| `where-things-live-row` | Adds a row to the `Where things live` table |
| `claude-tool-specific` | Moved to CLAUDE.md (Bash allowlists, slash command behavior, tool routing) |
| `vault-rules` | DROPPED (advise user in summary.md to see `vault-standards.md`) |
| `unclassifiable` | Appended to `## From legacy AGENTS.md` section, with comment explaining why |

Every classification decision is logged in `summary.md` with the heading text and the chosen bucket. User reviewing the preview can see exactly why each move was made.

### CLAUDE.md merge (all flavors with legacy CLAUDE.md content)

AI per-section classifier. For each heading in legacy CLAUDE.md, decide:

- **Generic project context** (stack, code style, deploy paths, project conventions) → propose move to `AGENTS.md` `Conventions` section
- **Claude-tool-specific** (Bash allowlists, slash command preferences, tool routing, plugin invocation hints) → keep in `CLAUDE.md` under the `@AGENTS.md` import

New `CLAUDE.md` always starts with `@AGENTS.md` (validator: `claude-md-imports-agents`).

### brief.md merge

- **Flavor Y:** Deterministic mapping from OB brief frontmatter shape to adjudant `project-brief-{type}.md` shape. Preserves user prose in the body verbatim.
- **Flavor Z:** No existing brief. Fresh from `templates/project-brief-{type}.md`. `project_type` resolved by prompt during preview (Claude asks, writes the choice into `summary.md` for confirmation at apply).
- **Flavor X:** Identical to `connect` — fresh from template.

## Vault-side migration (Flavor Y folder operations)

| OB folder | Action |
|---|---|
| `refs/` | Rename to `references/` |
| `iterations/` | Archive to `legacy/iterations/` (was OB-only; sunset) |
| `decisions/`, `sessions/`, `notes/` | Unchanged |
| (missing) `tasks/`, `images/` | Create empty + `_index.md` |
| `brief.md` | Replace (merged) |
| `_index.md` (per subfolder) | Regenerate from current contents |
| (vault root) `projects/_index.md` | Update this project's row |

For Z and X, the vault scaffold matches `connect`'s per-`project_type` defaults (see `reference/vault-standards.md`).

## Code layout

```
adjudant/
├── scripts/
│   ├── validate.py                 (existing — adds 3 new validators)
│   ├── command-metadata.json       (existing — adds 'port' entry)
│   └── port.py                     (NEW — mechanical operations)
└── skills/adjudant/
    ├── SKILL.md                    (existing — adds 'port' router row)
    └── reference/
        └── port.md                 (NEW — Claude runbook)
```

## Responsibility split

### `scripts/port.py` — mechanical, deterministic

- Detect flavor (X / Y / Z / preview / applied) per detection table above
- Vault path resolution (`OB_VAULT` env → walk-up for `Home.md type: vault-home` → prompt)
- Y-case: deterministic OB → adjudant section mapping (encoded as Python dict)
- Y-case: deterministic brief.md frontmatter shape migration
- Folder operations (rename / create / archive)
- Backup creation with ISO timestamp
- Preview directory scaffolding (creates the dir, writes `breadcrumb.proposed`, writes Y-case content directly)
- summary.md skeleton (Y-case fully filled; Z-case awaits Claude)
- `.gitignore` appends
- `projects/_index.md` row update
- Phase 2 apply (file moves, vault changes)
- CLI: `python3 port.py [preview|apply]` (called from `reference/port.md`)

### `reference/port.md` — Claude runbook

- Phase-1-vs-2 decision logic (re-states the detection table for Claude's reading)
- Calls `port.py preview` to do mechanical scaffolding
- For Z: AI classifier instructions
  - Read legacy AGENTS.md and CLAUDE.md
  - Classify each section per the buckets above
  - Write classified content into `AGENTS.md.proposed` and `CLAUDE.md.proposed`
  - Append per-section decisions to `summary.md`
  - For each ambiguous classification, log reasoning in `summary.md`
- For Z, project_type unknown: prompt user once, write to summary.md
- For Apply: validate preview integrity via `port-preview-coherence`, call `port.py apply`
- Error handling: detect partial states, point user at backup dir + manual revert
- Fallback: if AI classifier fails (e.g. out-of-tokens), fall back to "## From legacy" append for AGENTS.md content + dump CLAUDE.md verbatim under @AGENTS.md; log fallback in summary.md

## Validator additions (`scripts/validate.py`)

| Validator | Checks |
|---|---|
| `port-preview-coherence` | If `.adjudant-port-preview/` exists, has all required files (`AGENTS.md.proposed`, `CLAUDE.md.proposed`, `breadcrumb.proposed`, `vault-changes.txt`, `summary.md`) |
| `port-backup-integrity` | If `.adjudant-port-backup/{ts}/` exists, has the files its `summary.md` claims to back up |
| `gitignore-includes-port-dirs` | `.gitignore` includes `.adjudant-port-preview/` and `.adjudant-port-backup/` (only enforced if either dir exists) |

## Idempotency rules

| State on invocation | Behavior |
|---|---|
| No legacy markers, no breadcrumb | Acts as `connect` (creates everything). Exit 0. |
| `.adjudant-port-preview/` exists | **Apply mode** (phase 2). |
| `.adjudant-port-backup/` exists AND project is adjudant-compliant (breadcrumb at `.claude/adjudant` + template-shape AGENTS.md + CLAUDE.md starts with `@AGENTS.md` + no `.claude/obsidian-bridge`) | "Already ported. Use `/adjudant:adjudant check` to verify." Exit 0. |
| Legacy markers still present after a port attempt | Error: "Port appears incomplete. Inspect `.adjudant-port-backup/` and re-run." Exit non-zero. |
| `.adjudant-port-preview/` exists AND legacy markers also present AND not phase 2 trigger | Treat as phase 2 (preview generated previously; legacy markers persist until apply removes them). |

## Versioning

- adjudant `0.1.2` → `0.2.0` (minor — new verb, backwards-compatible)
- marketplace `1.1.2` → `1.2.0`

## Fail conditions

| Condition | Behavior |
|---|---|
| Vault path unresolvable AND user declines to provide | Exit non-zero with message |
| Preview corrupted in apply mode | Exit non-zero, suggest delete preview + restart |
| Project root files changed since preview generated (mtime check on backed-up paths vs preview generation time recorded in summary.md) | Warn, ask user to re-run preview |
| Y case, OB breadcrumb unparseable | Exit non-zero, suggest manual breadcrumb creation |
| Z case, AI classifier unavailable | Fall back: "## From legacy" append for AGENTS.md, verbatim dump for CLAUDE.md; log fallback in summary.md |
| Apply phase, vault folder rename collides with existing path | Exit non-zero, ask user to resolve manually |
| `project_type` not provided and not promptable | Exit non-zero |
| Slug contains invalid characters | Exit non-zero with rename suggestion |

## summary.md format (example for Flavor Y)

```markdown
# Port preview summary
Generated: 2026-05-26 16:30 · Flavor: Y (obsidian-bridge legacy)
Vault: /path/to/vault/projects/myproject

## File changes (project side)
| File | Action |
|---|---|
| AGENTS.md | Replace (merged) |
| CLAUDE.md | Replace (merged) |
| .claude/obsidian-bridge | Remove (migrated to .claude/adjudant) |
| .claude/adjudant | Create |
| .gitignore | Append (.adjudant-port-*) |

## Vault changes
| Path | Action |
|---|---|
| projects/myproject/refs/ | Rename to references/ |
| projects/myproject/iterations/ | Archive to legacy/iterations/ |
| projects/myproject/tasks/, images/ | Create |
| projects/myproject/brief.md | Replace (merged) |
| projects/_index.md | Update row |

## AGENTS.md merge decisions
- OB "## Working tree" → adjudant "Where things live" row (deterministic OB mapping)
- OB "## Stack" → adjudant "Conventions" section (deterministic OB mapping)
- OB "## Vault rules" → DROPPED (now in vault-standards.md, deterministic OB mapping)
- OB "## Custom project notes" → "## From legacy AGENTS.md" section at end (no template match)

## CLAUDE.md merge decisions
- Legacy "## Bash allowlist" → Kept in CLAUDE.md (Claude-tool-specific)
- Legacy "## Stack details" → Moved to AGENTS.md Conventions (generic project context)

To apply: re-run `/adjudant:adjudant port`.
To discard: delete `.adjudant-port-preview/` and start over.
```

## Open questions / deferred

- **Cross-project porting.** A `port-all` orchestrator that walks a directory, detects child repos, and runs `port` on each. Deferred to a future version. For now, the user runs `port` once per project.
- **Reverting an applied port.** Use the timestamped backup dir manually + git. No `unport` verb; manual revert is fine for v0.2.0.
- **Other legacy systems.** Adding mappings for non-OB tooling (e.g., a different vault plugin) would be additive to `port.py`'s mapping table. No spec change needed.
- **Preview editing safety.** If the user heavily edits the `.proposed` files, the apply phase trusts them. No round-trip validation of the user's edits. Acceptable for v0.2.0.
- **Concurrent runs.** Two `port` invocations in the same project at once is undefined behavior. Lock file (`.adjudant-port-preview/.lock`) could be added later if it becomes a real problem.

## Implementation phasing

Per design approval: **ship all three flavors (X, Y, Z) in v0.2.0**, not in two release cycles. AI classifier (Z) ships at the same time as the deterministic mapping (Y) and the connect-equivalent (X).

## Out of scope (explicit)

- Modifying hookify rules, MCP configs, or other CC global state
- Touching files outside the project root and the linked vault's `projects/{slug}/` directory
- Reading the user's existing git history to inform merge decisions
- Migrating commit history or branches in any way
