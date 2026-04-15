# iteration-shelf

Terminal-aesthetic review boards for in-browser design iteration. Generates two self-contained HTML files from a simple JSON manifest — a **curated shelf** for shortlisted work, and a **monster index** that safely previews every HTML artefact in a folder without frying the browser.

**Version:** 0.1.0
**Invocation:** explicit only (`/iteration-shelf` or when the user explicitly asks for one)

---

## Why

When a project spawns dozens of HTML iterations — portal variants, component explorations, layout studies — reviewing them all becomes its own problem. Eagerly embedding every iteration in an iframe crashes the browser. Opening them one at a time breaks flow. The tabs app is not a reviewer's console.

`iteration-shelf` solves that by producing two complementary artefacts:

- `_iterations.html` — **curated shelf.** Hand-picked shortlist, sectioned by concept family, all iframes eagerly loaded. Good up to ~20 items.
- `_monster-index.html` — **monster index.** Every HTML file in the target folder, grouped into segments, with on-demand iframe loading, a sticky outliner sidebar, and a warn-gate at 20+ simultaneous loads. Good for 100+ items.

Both files are static HTML. No build step, no dependencies, no external libraries. Drop them in a folder, open them in the browser, click around.

---

## Usage

### From zero

```
/iteration-shelf
```

The skill scans the current project for an `iteration-shelf.json` manifest. If it doesn't find one, it offers to generate a draft from a folder scan. Once the manifest is in hand, it generates one or both shelves.

### From an existing manifest

1. Edit `iteration-shelf.json` at the project root.
2. Run `/iteration-shelf`.
3. Both shelves are (re)generated from the manifest. Any hand-edited content in the existing shelves is diffed and flagged for confirmation before overwrite.

### What gets written

| File | When |
|---|---|
| `<target_folder>/_iterations.html` | Always, if the manifest has curated segments |
| `<target_folder>/_monster-index.html` | Always, if iteration count > 20 or explicitly requested |
| `iteration-shelf.json` | Only in init mode, at project root |

---

## The aesthetic

Terminal reviewer — dark, monospace, hairline-bordered. Not a portfolio. The design tokens are hard-coded:

- Background: `#0a0a0a`. Cards: `#141414`. Hairlines: `#222`.
- Mono font stack: SF Mono / Cascadia Mono / Consolas.
- Accent: `#e6c34a` (gold), `#8fc98f` (loaded-green), `#d4a017` (locked-ochre), `#e88` (danger-pink).
- Zero rounded corners beyond 2px. Zero drop shadows beyond the expand backdrop. Zero AI gradients.

The aesthetic is non-negotiable for the shelf chrome. The iterations it indexes are unconstrained.

Full token spec: [`references/design-tokens.md`](references/design-tokens.md)

---

## Manifest schema

Minimal:

```json
{
  "project": "my-project",
  "title": "Iteration Index — My Project",
  "date": "2026-04-14",
  "target_folder": "iterations",
  "segments": [
    {
      "id": "all",
      "title": "All iterations",
      "items": [
        { "id": "v1", "file": "v1.html" },
        { "id": "v2", "file": "v2.html" }
      ]
    }
  ]
}
```

Full spec with all optional fields, tag palette, and banner support: [`references/manifest-schema.md`](references/manifest-schema.md)

Worked example: [`examples/iteration-shelf.json`](examples/iteration-shelf.json)

---

## Interaction model

### Curated shelf
- Every iframe loads on page open.
- `Expand` overlays a card fullscreen. `Esc` collapses.
- `Reload` cache-busts a single iframe. `R` cache-busts all.

### Monster index
- **Placeholders only** until explicit click. `click` loads one card. `shift-click` unloads.
- **Segments** have a smart three-state button: `Load (N)` → `Unload (k/N)` (partial) → `Unload (N)` (full).
- **Sidebar outliner** with per-segment counters and scrollspy. Click to jump+load, shift-click to bulk-load a whole segment.
- **Warn-gate** at 20+ simultaneously loaded iframes.
- **Column switcher** (1× / 2× / 3×) with `localStorage` persistence and keyboard shortcuts `1` / `2` / `3`.
- `E` expand focused, `U` unload all, `R` reload loaded, `Esc` collapse.

Full interaction reference: [`references/interaction-model.md`](references/interaction-model.md)

---

## Integration

### With Superpowers

- **`full-output-enforcement`** — mandatory. Every shelf emits complete output, no placeholders, no skeletons.
- **`design-taste-frontend`** — suppressed for the shelf chrome, free to use on the iterations themselves.
- **`high-end-visual-design`** — explicitly suppressed for the shelf. The terminal aesthetic is deliberate.
- **`redesign-existing-projects`** — if the target folder already has an index file, follow that skill's audit-first pattern before overwriting.

### With the Cabinet plugin

When the Cabinet is active, **Bostrol** owns shelf operations. Generations are announced as one-line Bostrol lines. The operation is session-noted under `## What we did`. New tag slugs are logged as decisions under `decisions/YYYY-MM-DD-shelf-tag-{slug}.md`. Without a vault connection, operates silently.

### Standalone

No Superpowers, no Cabinet, no vault. Works fine. Plain HTML out.

Full matrix: [`references/integration.md`](references/integration.md)

---

## Browser-safety rules

Non-negotiable for the monster index — this is the whole reason it exists:

1. Never auto-load iframes. Placeholders only until user action.
2. `confirm()` prompt before bulk-loading when ≥20 iframes already live.
3. `loading="lazy"` on every injected iframe.
4. Inject iframe on load, `.remove()` on unload. Never `display:none` a live iframe (still holds memory).
5. Cache-bust reloads with `?r=${Date.now()}` so dev-mode iterations reflect instantly.

---

## File layout

```
iteration-shelf/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── iteration-shelf/
│       └── SKILL.md
├── references/
│   ├── design-tokens.md
│   ├── card-anatomy.md
│   ├── interaction-model.md
│   ├── manifest-schema.md
│   └── integration.md
├── templates/
│   ├── curated-shelf.html
│   └── monster-index.html
├── examples/
│   └── iteration-shelf.json
├── CHANGELOG.md
└── README.md        ← you are here
```

---

## Future variations

- **Era layout variant** (`layout: "era"`) — chronological / version-banded grouping. Planned for v0.2.
- **Theme params** — expose `--accent`, `--bg` as manifest-level tokens. Deferred until a reuse project actually needs them.
- **Multi-project aggregator** — an "all-projects shelf" that iframes each project's curated shelf inside segments. Needs vault integration; pinned for future.
- **Auto-manifest command** — `/iteration-shelf init` as a dedicated subcommand that just drafts the manifest without generating. Currently part of the main flow.

---

## Provenance

Extracted from the DutchBC portal project, where the pattern was born in the `_monster-index.html` at commit `54d4957`. Original spec filed by Bostrol, 2026-04-14, under explicit direction from Tom.
