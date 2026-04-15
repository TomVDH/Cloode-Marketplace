---
name: iteration-shelf
description: >
  Generate terminal-aesthetic review boards for in-browser design iteration.
  Produces two artefact types — a curated shelf (_iterations.html) for
  hand-picked iterations, and a monster index (_monster-index.html) for
  reviewing every HTML artefact in a folder without frying the browser.
  EXPLICIT INVOCATION ONLY — never auto-suggested. Trigger only when the
  user types /iteration-shelf or explicitly asks for "a shelf", "iteration
  index", "monster index", "review board", or "reviewer console". Pairs
  with Superpowers (full-output-enforcement, design-taste-frontend) and
  the Cabinet plugin (Bostrol owns shelf operations when cabinet is active).
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
version: 0.1.0
---

# Iteration Shelf

Generate one or both terminal-aesthetic review boards for a project's in-browser iterations. The shelves are the reviewer's console — dark, monospace, hairline-bordered, zero AI gradient slop. The iterations themselves are not constrained; the shelf chrome is.

---

## Invocation

**Explicit only.** Do not auto-suggest this skill. It fires only when the user:

- Types `/iteration-shelf` (direct command)
- Asks for "a shelf", "an iteration shelf", "iteration index", "monster index", "review board", or "reviewer console"
- Explicitly names a folder of HTML iterations that need review UI

If the user mentions "review my iterations" in a general way without naming the pattern, ask once whether they want a shelf — do not assume.

---

## What This Skill Produces

Exactly two artefact types, both **self-contained HTML** (no build step, no dependencies, no external libraries).

### A. Curated shelf — `_iterations.html`
- Small, hand-edited, opinionated. One file per project.
- Sections per concept family (portal / component / layout / flow).
- Every card **eagerly loads** its iframe. Safe up to ~20 iframes.
- For iteration counts beyond that, pair with the monster index.

### B. Monster index — `_monster-index.html`
- Covers **every** HTML artefact in the target folder.
- Segmented by prefix / family / user-chosen taxonomy.
- **On-demand** iframe loading (per-segment bulk + per-card click).
- Sticky left sidebar outliner with scrollspy.
- Safe for 100+ iterations.

Both files live in the folder they index (or its parent). Filename prefix `_` keeps them at the top of alphabetical listings and signals "index, not content".

---

## When to Use Which

| Iteration count | Default output |
|---|---|
| ≤ 20 | Curated shelf only |
| 21 – 60 | Both (monster as safety net, curated as opinion) |
| > 60 | Monster only, unless user asks for both |

Always emit the monster if explicitly requested, regardless of count.

---

## Startup Sequence

### 1. Load Core References

At invocation, read these **all** from `${CLAUDE_PLUGIN_ROOT}/references/`:

- `design-tokens.md` — CSS custom properties, typography, anti-slop rules
- `card-anatomy.md` — card HTML schema and tag palette
- `interaction-model.md` — loading, keyboard, sidebar, warn-gate, safety rules
- `manifest-schema.md` — JSON manifest spec and field reference
- `integration.md` — Superpowers and Cabinet integration notes

Read the templates too:

- `${CLAUDE_PLUGIN_ROOT}/templates/curated-shelf.html` — canonical curated reference
- `${CLAUDE_PLUGIN_ROOT}/templates/monster-index.html` — canonical monster reference

Use these as the structural ground truth. The HTML you emit must match them token-for-token on colour, typography, and interaction — deviations from the aesthetic brief break the skill.

### 2. Check for Manifest

Look for `iteration-shelf.json` at the project root or beside the target folder. If found:

- Parse it (see `manifest-schema.md` for schema)
- Validate required fields: `project`, `title`, `target_folder`, `segments`
- Proceed to generation

If no manifest exists:

- Ask the user whether to (a) auto-scan the folder and emit a manifest for their review, or (b) have them write one and rerun.
- If (a): run the **init** subflow (below) to produce `iteration-shelf.json` first, then stop and hand back for user refinement — do not generate shelves on a machine-drafted manifest without confirmation.

### 3. Init subflow (auto-manifest)

When the user wants an auto-drafted manifest:

1. Use `Glob` to list every `*.html` in `target_folder`, excluding any file starting with `_`.
2. Group by filename prefix using this heuristic:
   - Strip trailing `-v\d+` suffix.
   - First dash-separated token is the family key (e.g. `hc-kinetic-typography-v18.html` → family `hc`).
   - Files that don't fit any existing family go into an `other` segment.
3. For each family, emit a segment object with `id`, `title` (title-cased family name), `description` (count + "iterations"), and `items`. Each item gets `id` (filename with `.html` stripped) and `file`.
4. Write the JSON to `iteration-shelf.json` at the project root (or alongside the target folder if user prefers).
5. Stop. Report what was found and ask the user to edit and rerun.

### 4. Generate Shelves

Once a valid manifest is in hand, decide which shelf (or both) to generate per the count table above, or per explicit user request.

For each generated file:

- Start from the template, preserve its CSS and JS verbatim.
- Replace the inline `SEGMENTS` array (monster) or the per-section card blocks (curated) with user data from the manifest.
- Replace `<title>`, `<h1>`, and the global link strip per `manifest.title` and `manifest.global_links`.
- Keep every CSS token, keyframe, and JS handler intact. The templates are not suggestions — they are the shelf.
- If both shelves are emitted, wire their footers/headers to cross-link (`← curated iterations` / `monster index →`).

### 5. Overwrite Protection

Before writing, check if the output file already exists:

- If missing — write it.
- If present with identical header signature — overwrite silently.
- If present but different — read it, diff against the new output, and ask the user to confirm overwrite. Never clobber a hand-edited shelf without confirmation.

---

## Deliverable Rules

**The two shelves are production artefacts, not drafts.** Follow the Superpowers `full-output-enforcement` skill (if available) — no placeholder comments, no skeletons, no "rest follows the same pattern." Every segment, every card, every event binding must ship in full.

Specific anti-patterns that are forbidden in the emitted HTML:

- `// ...rest of items` or any `...` standing in for omitted cards
- Truncated `SEGMENTS` array with "truncated for brevity" comments
- Missing event handlers (sidebar, expand, column switcher, scrollspy, keyboard)
- Any deviation from the CSS tokens in `design-tokens.md`
- Any HTML output using variable-width fonts, rounded corners > 4px, box-shadows beyond the expand backdrop, or gradient backgrounds

If the manifest is large, generate the full output. If the response would exceed the token budget, use the `full-output-enforcement` split protocol — do not compress.

---

## Browser-Safety Rules (the OOM guard)

Non-negotiable — the whole point of the monster index.

1. **Never auto-load iframes in the monster index.** Placeholders only until explicit user action.
2. **Warn at 20+ loaded.** `confirm()` prompt before bulk-loading another segment.
3. **Use `loading="lazy"`** on every injected iframe.
4. **Inject, don't hide.** Create iframe on load, `.remove()` on unload — never `display:none` on a live iframe (still runs JS and holds memory).
5. **Cache-bust reloads** with `?r={Date.now()}` so iterations picked up during development reflect instantly.

These rules are enforced by the monster template's JS. Do not edit them out when parameterising.

---

## First-Run Checklist

When invoked for a project that has never had a shelf:

- [ ] Confirm target folder with the user.
- [ ] Scan folder with `Glob`, surface the file count.
- [ ] If > 20 items, mention both artefact types and recommend the monster at minimum.
- [ ] Offer to draft `iteration-shelf.json` from the folder scan.
- [ ] On user approval of the manifest, generate the chosen shelf(s) at full fidelity.
- [ ] Wire cross-links between the two outputs when both are emitted.
- [ ] Respect any pre-existing `_iterations.html` — diff and propose, never clobber silently.
- [ ] Report paths of what was written and what (if anything) was skipped.

---

## Integration

### With Superpowers

- **`full-output-enforcement`** — mandatory. Emit complete shelves, never placeholder stubs. If the user has this skill installed, follow it explicitly.
- **`design-taste-frontend`** — the tokens in `design-tokens.md` override that skill's defaults **inside the shelf chrome only**. The indexed concepts are not constrained by either.
- **`high-end-visual-design`** — explicitly **suppressed** for the shelf chrome. Terminal aesthetic is intentional and non-negotiable.
- **`redesign-existing-projects`** — if the target folder already has an old index file, follow that skill's audit-then-upgrade pattern rather than duplicating.

See `${CLAUDE_PLUGIN_ROOT}/references/integration.md` for the full matrix.

### With Cabinet plugin

When the Cabinet is active, **Bostrol** owns shelf operations.

- Announce each generation with one short Bostrol line, e.g.
  `[Bostrol]: Emitting _monster-index.html · 12 segments · 130 items.`
- Writing a shelf is a **session-notable event** — append to the chatter under `## What we did`.
- Adding new tag slugs or changing the tag palette is a **decision** — log under `decisions/YYYY-MM-DD-shelf-tag-{slug}.md`.
- If no vault is connected, operate standalone. No prompts, no nudges — the shelf is the deliverable.

See `${CLAUDE_PLUGIN_ROOT}/references/integration.md § Cabinet` for the full auto-log skeleton.

### Standalone

Runs cleanly without either plugin. Outputs are plain HTML files, no dependencies, no build step, no runtime integrations.

---

## Open Variations

Reference implementations ship as templates:

| Template | Purpose | Status |
|---|---|---|
| `templates/curated-shelf.html` | Default curated — hand-picked per family | Shipped |
| `templates/monster-index.html` | Default monster — all files, on-demand loading | Shipped |
| `templates/curated-shelf-era.html` | Era-grouping variant — chronological / version-banded | Planned (v0.2) |

The default `layout: "family"` maps to the standard curated template. If a manifest sets `layout: "era"` in v0.1.0, warn the user that the era template ships later and fall back to `"family"`.

See `manifest-schema.md` for how `layout` is declared.

---

## What This Skill Does NOT Do

- **Does not generate the iterations themselves.** Use `design-taste-frontend` and aesthetic sibling skills for that — the shelf indexes work that already exists.
- **Does not run a web server.** The shelves assume same-folder or sibling-folder relative paths. If the iterations reference assets via `../../`, point that out to the user but do not attempt to resolve it.
- **Does not expose theme params.** The terminal aesthetic is hard-coded. Future versions may surface `--accent` / `--bg` if a reuse project asks for it — do not pre-generalise.
- **Does not modify iteration files.** Only the two shelf files are written. Everything else is read-only input.

---

## Reference Index

| Topic | File | Always loaded? |
|---|---|---|
| CSS tokens, typography, anti-slop | `design-tokens.md` | Yes |
| Card HTML schema, tag palette | `card-anatomy.md` | Yes |
| Keyboard, sidebar, segment controls | `interaction-model.md` | Yes |
| JSON manifest spec | `manifest-schema.md` | Yes |
| Superpowers / Cabinet hookup | `integration.md` | Yes |
| Curated reference HTML | `templates/curated-shelf.html` | Yes |
| Monster reference HTML | `templates/monster-index.html` | Yes |
| Sample manifest | `examples/iteration-shelf.json` | On demand |

All reference files live in `${CLAUDE_PLUGIN_ROOT}`. Read everything in the top block at invocation — the templates are not small, but shelf fidelity depends on not reconstructing them from memory.
