# Command surface redesign — design spec

**Status:** DRAFT, brainstormed, not implemented.
**Date:** 2026-05-04
**Goal:** Collapse the current ~25-subcommand `/vault-bridge` + `/dream` surface into 7 opinionated top-level verbs, without losing any current functionality. Move content creation from commands into conversation; keep commands for lifecycle, sync, status, cleanup, diagnostic, visual artefacts, and iteration state transitions.

---

## Goals

- **Easier to use** — slash menu shows 6–7 evocative verbs instead of 25.
- **More opinionated** — there's one obvious way to do common things; rare things are conversational.
- **No power loss** — every current capability is reachable, just via a different path.
- **Discoverability for visual features** — canvases, bases, and mermaid diagrams get a dedicated entry point (`/draw`) so they're not invisible in the slash menu.
- **Mechanical reliability for state transitions** — iteration status changes get a dedicated verb because they are state-machine operations, not conversation.

## Non-goals

- Revising the frontmatter schema (`vault-standards`) — kept as-is.
- Revising hooks (5 hooks) — kept as-is.
- Revising skills (`vault-standards`, `mermaid`, `canvas`, `search`, `bases`, `markdown`, `cli`, `clipper-template`, `dream`, `vault-bridge`) — kept as-is.
- Renaming the plugin or restructuring the marketplace.

---

## Final command surface

| Verb | Purpose | Slash-menu description |
|---|---|---|
| `/connect [path]` | Onboard: link folder to vault, infers create / connect / link | Link this folder to an Obsidian vault (creates one if needed) |
| `/sync` | Push current state to vault — brief + handoff in one | Push current state to the vault (brief + handoff) |
| `/check [section]` | Read-only summary; optional section for focused view | Read-only summary; optional section (`iterations`, `decisions`, `sessions`) |
| `/draw <subverb> [args]` | Create or list visual artefacts | Create or list visual artefacts — canvases, bases, mermaid diagrams |
| `/ramasse` | Tidy: reindex + housekeeping in one pass | Tidy the vault — rebuild indexes, fix drift, normalise tags |
| `/dream` | Deep diagnostic — structural and content drift | Deep diagnostic — surfaces structural and content issues |
| `/iterate <id> <status>` | Iteration state transition (state-machine reliability) | Set iteration status (`drafting`/`on-shelf`/`picked`/`parked`/`rejected`/`superseded`). May be sunset in favour of conversational use |

7 verbs. Two foreign-language for character (`/ramasse` French, ~~`/cupola` Italian~~ → `/draw` English). Rest English.

### `/draw` subverbs

The only command with subverbs. Subverbs route into specific skills:

```
/draw                   → list visual artefacts in current project (canvases, bases, recent mermaid blocks)
/draw canvas <name>     → create or edit a .canvas file (loads canvas skill)
/draw base <name>       → create or edit a .base file (loads bases skill)
/draw diagram [type]    → drop a mermaid diagram into the current note (loads mermaid skill);
                          type optional — flowchart | sequence | class | state | erd | gantt | mindmap |
                          timeline | gitGraph | pie | quadrant | journey | C4
```

Subverbs are accepted because each routes into a structurally distinct artefact (different file type or specialised markdown). They earn their place; other commands don't get subverbs.

### `/iterate` sunset note

`/iterate` exists for **mechanical state-machine reliability**. State transitions (`drafting → picked`, `picked → superseded`, etc.) are not creative writing — they're property updates with a small enum. Conversational handling ("promote D to picked") is feasible but carries misinterpretation risk ("create a new iter D, promote, and pick").

**This command may be sunset in a future release** if conversational handling proves robust enough across model versions. Conversational creation and listing of iterations is already preferred — only the state transition has its own verb. Documented in the `vault-bridge` skill body.

---

## What is killed / folded

| Killed command | Where it lives now |
|---|---|
| `create`, `connect` (the verb), `link`, `create-project` | `/connect` (single onboarding entry) |
| `add-collection`, `archive`, `unarchive`, `set-type`, `templates` | conversational |
| `add-iteration`, `add-iteration-artefact`, `iterations` | conversational (only `/iterate` for status transitions) |
| `sync`, `handoff sync` | `/sync` |
| `status`, `handoff status` | `/check` (optional `[section]`) |
| `reindex`, `housekeeping` | `/ramasse` |
| `migrate` (v2→v3) | conversational ("migrate this vault to v3") |
| `migrate-anchor` | **removed** — auto-migration in SessionStart hook step 0 replaces it (see Anchor chain section) |
| All `iteration-*` and `add-iteration-*` plurality | folded into `/iterate` (transitions only) + conversational (creation/listing) |

## What is preserved (no change)

- All 10 skills (`vault-standards`, `mermaid`, `canvas`, `search`, `bases`, `markdown`, `cli`, `clipper-template`, `dream`, `vault-bridge`) and their references.
- All 5 hooks (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PostToolUse`, `PreCompact`).
- Frontmatter schema (canonical in `vault-standards` skill).
- Vault layout and naming rules.
- Frontmatter validator hook behaviour (PostToolUse) and PreCompact handoff sync — same logic, just reads canonical anchor only.

**Changed (no longer "preserved"):**

- Anchor file location → `.claude/obsidian-bridge` is now the **only** read location. Legacy `.obsidian-bridge` at project root is auto-migrated on encounter (SessionStart step 0). See "Anchor chain" section below.

---

## Plugin description (umbrella, shows in plugin browsers)

> Operate an Obsidian vault from Claude — opinionated layout, frontmatter schema, content know-how (canvas, bases, mermaid), and cleanup workflows.

(Replaces: "Canonical Obsidian-vault layout, schema, primitives, and cleanup workflow for Claude Code. Standalone and cabinet-aware.")

---

## How content creation works post-redesign

**Commands are for lifecycle, sync, status, cleanup, diagnostic, visual-artefact creation, and iteration state.**
**Content creation is conversational** for everything else. Examples:

| What you say | What happens |
|---|---|
| "add a decision: we're using postgres because X" | Model loads `vault-standards` + `markdown` skills, creates `projects/{slug}/decisions/YYYY-MM-DD-<title>.md` with canonical frontmatter |
| "make a quick source from this article: <url>" | Model creates `projects/{slug}/sources/<title>.md` with source schema |
| "new project foo, knowledge type" | Model creates `projects/foo/` scaffold with type-shaped templates |
| "archive foo" | Model moves `projects/foo/` → `archive/foo/` and rewrites frontmatter status |
| "change foo to plugin type" | Model updates `project_type` in `projects/foo/brief.md` and adjusts subfolder defaults |
| "promote iter D to picked" | Either: model updates frontmatter directly, OR you use `/iterate D picked` for guaranteed correctness |
| "show me on-shelf iterations" | Model greps `iterations/` folders for `status: on-shelf` and renders summary |
| "add a tasks/ folder to foo" | Model creates `projects/foo/tasks/_index.md` |
| "what does the brief template look like" | Model reads `examples/vault-templates/brief-{type}.md` |

The bet: with `vault-bridge` skill + `vault-standards` skill auto-loading, the model is reliable enough to handle these conversationally. Commands exist only where a command is genuinely better than conversation (lifecycle moments, mechanical state changes, visual entry points).

---

## Trade-offs accepted

- **Loss of slash-menu discoverability** for niche operations (set-type, archive, add-collection, templates, etc.). Mitigation: the `vault-bridge` skill body lists these capabilities so the model surfaces them when relevant.
- **Conversational risk** for state-changing operations like archive/migrate. Mitigation: model always confirms before destructive actions; PostToolUse validator catches bad frontmatter writes.
- **`/connect` does three things** (create / connect / link) by inference. Mitigation: clear flags for explicit override (`/connect --new`, `/connect --link-only`).
- **`/draw` has subverbs** while other commands don't. Justified: visual artefacts are distinct file types and warrant the routing; no other command's domain has this level of internal divergence.

---

## Anchor chain — cleaned up (no legacy reads)

The SessionStart hook resolves the vault via this chain. First hit wins.

```
0.  AUTO-MIGRATE  IF $CLAUDE_PROJECT_DIR/.obsidian-bridge exists AND
                     $CLAUDE_PROJECT_DIR/.claude/obsidian-bridge does NOT:
                       mkdir -p .claude
                       mv .obsidian-bridge → .claude/obsidian-bridge
                       rewrite ".obsidian-bridge" → ".claude/obsidian-bridge" in .gitignore (if present)
                       emit one-line notice: "[obsidian-bridge] auto-migrated anchor → .claude/obsidian-bridge"
        ↓ then proceed to read chain…
1.  $CLAUDE_PROJECT_DIR/.claude/obsidian-bridge        ← canonical anchor (only location read)
        ↓ not present
2.  $CLAUDE_PROJECT_DIR/.cabinet-anchor-hint           ← cabinet-of-imd interop (active contract, NOT legacy)
        ↓ not present
3.  OB_DEFAULT_VAULT env var                           ← global default
        ↓ not set
4.  walk parent dirs (≤5) for Home.md
        with frontmatter `type: vault-home` or `type: cabinet-home`
        ↓ none found
    → "Not Linked" — user must run /connect
```

Step 0 makes step 1's "legacy fallback" unnecessary — anchors get transparently upgraded the next time anyone opens Claude in that project. After migration, only canonical reads happen.

`/vault-bridge migrate-anchor` is **removed** (auto-migration replaces it).

## Resolved: previously-open questions

| Question | Resolution |
|---|---|
| `/draw` — own skill or direct dispatch? | **Direct dispatch.** Command body routes to `canvas` / `bases` / `mermaid` skills via context. No new `draw` skill. |
| Deprecation aliases for old commands? | **No aliases.** Old `/vault-bridge` and `/dream` commands removed in the same commit as the new surface — modernise invocations cleanly. |
| `/check` — multi-section? | **Yes.** `/check iterations decisions` returns both sections in one call. |
| `/connect` — inference rule order? | path doesn't exist → **create** new vault; path exists with `Home.md` (`type: vault-home` or `cabinet-home`) → **connect**; path exists with `projects/` folder but no `Home.md` → **connect** (best-effort); path exists with neither → **error** with clear "expected `Home.md` or a `projects/` folder" message. |
| Cabinet-anchor-hint — keep in chain? | **Keep** as step 2. Cabinet-of-imd v3 explicitly delegates persistence to obsidian-bridge — interop contract is active, not legacy. |

---

## Implementation outline (for the writing-plans phase)

1. **Author the 6 new commands** — `*.md` files in `obsidian-bridge/commands/`:
   - `connect.md`, `sync.md`, `check.md`, `draw.md`, `ramasse.md`, `iterate.md`
   - (`/dream` already exists; keep its file but refresh its description if needed)
2. **Remove old commands** in the same commit:
   - Delete `commands/vault-bridge.md` and `commands/dream.md` if `/dream` is being recreated; OR keep `dream.md` if it's already correctly shaped.
   - No deprecation aliases — clean break.
3. **Refactor `vault-bridge` skill** — same pseudocode primitives, new dispatch surface. Sections now organised by new verb:
   - `/connect` — combines create + connect + link logic with inference
   - `/sync` — combines sync + handoff sync
   - `/check` — status with optional sections (`iterations`, `decisions`, `sessions`)
   - `/ramasse` — reindex + housekeeping merged
   - `/iterate` — iteration state transitions only (creation/listing conversational)
4. **Add `/iterate` sunset note** in `vault-bridge` skill body.
5. **Update SessionStart hook** to add step 0 (auto-migrate legacy anchor + .gitignore rewrite).
6. **Update other hooks** (UserPromptSubmit, PostToolUse, PreCompact) to read ONLY canonical anchor — drop the legacy fallback added in `feat/anchor-in-dot-claude` (auto-migration replaces the need).
7. **Update plugin description** in `.claude-plugin/plugin.json` to the new punchier copy.
8. **Update README** with the new 7-verb surface.
9. **Update notes** referencing old command names (`mermaid-house-style.md`, `ATTRIBUTIONS.md`, etc.) — sweep for `vault-bridge` mentions in commands context.
10. **Add a brief migration guide** in `notes/` mapping old → new commands, for anyone with old surface in muscle memory (mostly Tom). Single page, ~30 lines.

## Reconciliation with in-flight branches

Before this redesign lands, two branches from earlier in the session need to be merged or absorbed:

- **`feat/anchor-in-dot-claude`** — moved anchor to `.claude/obsidian-bridge` with canonical-then-legacy fallback in all readers. The redesign **drops the legacy fallback** in favour of auto-migration. Two options:
  - (a) Merge the branch first, then this redesign edits readers again to drop legacy fallback.
  - (b) Cherry-pick only the canonical-write changes from the branch, drop the fallback-read changes, do the rest fresh.
  - **Recommended: (a)** — simpler, less mental tax, the eventual diff is small.
- **`feat/obsidian-deepening`** — added canvas + search skills, deepening references. Independent of command surface; merge cleanly before or after.

---

## Next step

Spec written and committed. On user approval (no further changes), invoke writing-plans to produce the detailed implementation plan.
