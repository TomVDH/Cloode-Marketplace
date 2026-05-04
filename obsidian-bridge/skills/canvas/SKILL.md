---
name: canvas
description: Use when creating, editing, or programmatically writing Obsidian `.canvas` files — visual note-taking on infinite 2D space using the open JSON Canvas format.
allowed-tools: Read, Write, Edit, Glob, Grep
version: 0.1.0
source: "https://help.obsidian.md/plugins/canvas"
upstream_redistribution: "Obsidian Help vault (CC BY 4.0)"
---

# Canvas

Canvas is Obsidian's visual note-taking surface — infinite 2D space where notes, files, web pages, and free-text cards can be arranged, connected, and grouped. Every canvas is stored as a `.canvas` file using the open [JSON Canvas](https://jsoncanvas.org/) format, so canvases can be created, edited, and queried programmatically without going through the Obsidian UI.

> **`obsidian-bridge` vault?** Canvases live alongside notes; their parent folder follows the same structural rules. Canvas filenames follow vault naming (kebab-case, no date prefix unless time-relevant). Frontmatter does not apply to `.canvas` files (they are JSON, not Markdown) — but their containing folder may need an `_index.md` per `obsidian-bridge:vault-standards`.

## When to Use

- Authoring or editing a `.canvas` file directly (filesystem write).
- Generating a canvas programmatically — e.g. visualising a graph of notes, a roadmap, an architecture diagram.
- Migrating brainstorm material into a structured canvas.
- Inspecting an existing canvas to understand its node/edge graph.

## File format — JSON Canvas v1

A `.canvas` file is a single JSON object with two arrays: `nodes` and `edges`. Spec: <https://jsoncanvas.org/spec/1.0/>.

```json
{
  "nodes": [
    {
      "id": "abc123",
      "type": "text",
      "x": 0,
      "y": 0,
      "width": 250,
      "height": 60,
      "text": "Hello"
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "fromNode": "abc123",
      "fromSide": "right",
      "toNode": "def456",
      "toSide": "left",
      "label": "leads to"
    }
  ]
}
```

### Node fields (all node types)

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Unique within the canvas. Random short alphanumerics work fine. |
| `type` | string | yes | `text`, `file`, `link`, or `group`. |
| `x` | number | yes | Top-left X coordinate (pixels, can be negative). |
| `y` | number | yes | Top-left Y coordinate. |
| `width` | number | yes | Width in pixels. |
| `height` | number | yes | Height in pixels. |
| `color` | string | no | `"1"`–`"6"` (preset accents) or `"#RRGGBB"`. |

### Type-specific fields

| Type | Extra fields |
|---|---|
| `text` | `text` (Markdown — wikilinks, callouts, code blocks all render) |
| `file` | `file` (vault-relative path, e.g. `"projects/foo/brief.md"`), optional `subpath` (e.g. `"#heading"` or `"#^block-id"`) |
| `link` | `url` |
| `group` | `label` (group title), optional `background` (image path), `backgroundStyle` (`"cover"` / `"ratio"` / `"repeat"`) |

### Edge fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Unique within the canvas. |
| `fromNode` | string | yes | `id` of source node. |
| `toNode` | string | yes | `id` of target node. |
| `fromSide` | string | no | `top` / `right` / `bottom` / `left`. Default: auto. |
| `toSide` | string | no | Same options. |
| `fromEnd` | string | no | `none` (default) or `arrow`. |
| `toEnd` | string | no | `none` or `arrow` (default). |
| `color` | string | no | Same palette as nodes. |
| `label` | string | no | Plain-text label rendered on the edge. |

### Color palette (preset values)

| Value | Meaning (Obsidian default theme) |
|---|---|
| `"1"` | red |
| `"2"` | orange |
| `"3"` | yellow |
| `"4"` | green |
| `"5"` | cyan |
| `"6"` | purple |

Or supply any `#RRGGBB` hex string for full control.

## Common patterns

### Skeleton with text card and file card connected

```json
{
  "nodes": [
    {"id": "n1", "type": "text", "x": -200, "y": 0, "width": 240, "height": 80, "text": "## Idea\nstart here"},
    {"id": "n2", "type": "file", "x": 100,  "y": 0, "width": 320, "height": 200, "file": "projects/foo/brief.md"}
  ],
  "edges": [
    {"id": "e1", "fromNode": "n1", "fromSide": "right", "toNode": "n2", "toSide": "left", "label": "expands into"}
  ]
}
```

### Group containing several nodes

A `group` node is just a positioned rectangle with a label. Other nodes are **not** children of it in the JSON — grouping is positional. To "put nodes in a group," position them inside the group's bounding box.

```json
{
  "nodes": [
    {"id": "g1", "type": "group", "x": -300, "y": -100, "width": 700, "height": 400, "label": "Backlog", "color": "3"},
    {"id": "n1", "type": "text",  "x": -250, "y": 0,    "width": 200, "height": 60, "text": "task 1"},
    {"id": "n2", "type": "text",  "x":   30, "y": 0,    "width": 200, "height": 60, "text": "task 2"}
  ],
  "edges": []
}
```

### File node embedding a specific heading or block

```json
{"id": "n3", "type": "file", "x": 0, "y": 0, "width": 300, "height": 180, "file": "notes/research.md", "subpath": "#Findings"}
```

The `subpath` works like Obsidian wikilink anchors: `#Heading` for a section, `#^block-id` for a block reference.

## Creating canvases programmatically — workflow

1. **Choose a target path** following vault conventions (e.g. `projects/{slug}/canvases/{kebab-name}.canvas`).
2. **Plan the layout in coordinates first** — give every node `x`, `y`, `width`, `height`. Use a grid (e.g. 320 px wide × 200 px tall, 60 px gutter) to keep things tidy.
3. **Generate stable, short `id`s** — random 6-char alphanumerics are fine; they only need to be unique within the file.
4. **Write the JSON** with `Write` tool. Validate with `python3 -c "import json; json.load(open('x.canvas'))"`.
5. **Open in Obsidian** to verify rendering — coordinates that look right in JSON sometimes overlap when rendered.

## Coordinate conventions

- Origin `(0, 0)` is wherever Obsidian opens the canvas — there is no absolute "centre."
- X increases right, Y increases **down** (standard screen coordinates, NOT mathematical).
- Negative coordinates are fine — useful for placing nodes to the left of/above your "main flow."
- Snap-to-grid in the Obsidian UI is 20 px; choose dimensions that are multiples of 20 for clean visual alignment.

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Canvas opens blank | `nodes`/`edges` missing or invalid JSON | Ensure both arrays present (even if empty) and JSON is valid |
| Edge does not render | `fromNode` / `toNode` references a missing `id` | IDs must match exactly (case-sensitive) |
| File card shows "File not found" | `file:` path is absolute or wrong-cased | Use vault-relative path; case-sensitive on macOS HFS+ and Linux |
| Group does not visually contain its members | Group is just a rectangle — placement is positional | Reposition member nodes to fall inside the group's `x`/`y`/`width`/`height` |
| Wikilinks inside `text` nodes do not work | Actually they DO — `text` field renders as Markdown | If broken, check the wikilink path is vault-relative |
| Subpath embed shows whole file | `#heading` not found in target file | Heading match is by exact text, case-sensitive |
| Colors look wrong | Mixed string vs number | `color` must be a string: `"1"`, not `1` |

## Cross-references

- For Markdown that goes inside `text` nodes (wikilinks, callouts, embeds): see `obsidian-bridge:markdown`.
- For diagrams that would be better as Mermaid than as a hand-laid-out canvas: see `obsidian-bridge:mermaid`.
- For vault structural rules around where canvases should live and how to name them: see `obsidian-bridge:vault-standards`.
- Spec: <https://jsoncanvas.org/spec/1.0/>
- Obsidian Canvas docs: <https://help.obsidian.md/plugins/canvas>
