# Manifest schema — iteration-shelf

The `iteration-shelf.json` file is the source of truth for what the shelf renders. Without it, the skill falls back to alphabetical globbing grouped by filename prefix. With it, the shelf has opinion.

---

## 1. Location and naming

| Project layout | Manifest location |
|---|---|
| Iterations in `project/concepts/directions/` | `project/iteration-shelf.json` |
| Iterations in `project/iterations/` | `project/iteration-shelf.json` |
| Iterations in the project root | `project/iteration-shelf.json` |
| User explicitly requests a sibling | `project/concepts/iteration-shelf.json` (or wherever they asked) |

One manifest per project. If the project splits its iterations across multiple folders, the manifest can still reference all of them via per-item `file` paths — do not emit a second manifest.

The filename is **always** `iteration-shelf.json`. Do not use `shelf.json`, `iterations.json`, or `manifest.json` — those collide with other tooling.

---

## 2. Full schema

```json
{
  "project": "dutchbc-portal",
  "title": "Iteration Index — Star Portals — DutchBC",
  "date": "2026-04-14",
  "target_folder": "concepts/directions",
  "output": {
    "curated": "_iterations.html",
    "monster": "_monster-index.html"
  },
  "layout": "family",
  "global_links": [
    { "label": "← top-5 priority grid", "href": "_top-5.html" },
    { "label": "full directions index", "href": "index.html" }
  ],
  "notes": [
    {
      "tone": "warning",
      "title": "Preview origin",
      "body": "These files reference `../../public/images/…` and only resolve when the project root is the server root."
    }
  ],
  "segments": [
    {
      "id": "star",
      "title": "★ Star picks",
      "description": "Max-effort premium builds and locked plates — start here",
      "items": [
        {
          "id": "FC · v2 (locked)",
          "file": "fc-three-doors-v2.html",
          "tag": "locked",
          "quote": "three doors · locked plate champion.",
          "note": "Geometric triptych · paper + cobalt · hover invert"
        }
      ]
    }
  ]
}
```

---

## 3. Top-level fields

| Field | Type | Required | Purpose |
|---|---|---|---|
| `project` | string | yes | Slug used in session notes / cabinet vault paths |
| `title` | string | yes | Rendered in `<title>` and `<h1>` of both shelves |
| `date` | string (YYYY-MM-DD) | yes | Shown in the shelf header, also used for session logging |
| `target_folder` | string | yes | Relative path from the manifest to the iteration folder |
| `output.curated` | string | no | Default: `_iterations.html` |
| `output.monster` | string | no | Default: `_monster-index.html` |
| `layout` | `"family"` \| `"era"` | no | Default: `"family"` — maps to `templates/curated-shelf.html`. `"era"` is reserved for a planned v0.2 era-grouping variant; in v0.1.0, setting it emits a warning and falls back to `"family"`. |
| `global_links` | array of `{label, href}` | no | Link strip in the header. 0..4 links typical. |
| `notes` | array of note objects | no | Top-of-page banners (see § 5) |
| `segments` | array of segment objects | yes | At least one |

`project` **must not** contain spaces or slashes. Use the same kebab-case slug you'd use for a git branch or folder name. Cabinet vault paths are derived directly from this.

`date` is the shelf's canonical date, not "today". When re-generating a shelf, keep the original date unless the user asks for a re-stamp — the date is a reviewer's bookmark.

---

## 4. Segment object

| Field | Type | Required | Purpose |
|---|---|---|---|
| `id` | string (kebab-case) | yes | Used as `seg-{id}` in DOM, as `data-seg` on buttons |
| `title` | string | yes | Displayed in segment header and sidebar |
| `description` | string | no | One-line dim-grey caption right of the title |
| `items` | array of item objects | yes | At least one |

Segment `id` values must be unique within a manifest. Common slugs:

- `star` — shortlist / priority
- Family codes: `fc`, `hc`, `hi`, `fy`, `hr`, `fn`, `fr`
- Typological sweeps: `e`, `f`, `g`, `h`
- Named collections: `premium`, `wild`, `logo`, `foundational`, `gsap`

The order of segments in the manifest is the render order. Star segments first is a convention, not a rule.

---

## 5. Note object (banners)

Optional. Renders as a coloured banner above the segment list.

```json
{ "tone": "warning", "title": "Preview origin", "body": "These files reference ../../public/images/..." }
```

| Field | Type | Values |
|---|---|---|
| `tone` | string | `"info"` \| `"warning"` \| `"success"` \| `"danger"` |
| `title` | string | UPPERCASE in render |
| `body` | string | Plain text with optional `<code>` spans |

Colour mapping:

| Tone | Border | Background | Text |
|---|---|---|---|
| `info` | `#2a2a3a` | `#0a0d12` | `#adf` |
| `warning` | `#3a2a10` | `#120d05` | `#e6c34a` |
| `success` | `#2a3a1a` | `#0d120a` | `#9bd663` |
| `danger` | `#3a1a1a` | `#120808` | `#e88` |

Banners are optional and rarely used — only when there's a non-obvious caveat the reviewer needs to see before clicking anything (e.g. "server-root assumption" or "branch note").

---

## 6. Item object

| Field | Type | Required | Purpose |
|---|---|---|---|
| `id` | string | yes | Display label, shown in card header and sidebar |
| `file` | string | yes | Path relative to the shelf's output location |
| `tag` | string | no | One of the tag slugs (see `card-anatomy.md § 3`). Defaults to `original` |
| `star` | boolean | no | Shortcut for `tag: "star"`. If both `tag` and `star: true` are set, `tag` wins. |
| `quote` | string | no | Single italic line, lowercase, `<40 chars` |
| `note` | string | no | Comma-separated technical summary, rendered UPPERCASE |

**Rules of thumb:**

- `id`: keep ≤ 40 chars. The sidebar truncates with ellipsis.
- `file`: relative path. If the iteration lives in the same folder as the shelf, just the filename. If not, use `../` as needed.
- `quote`: reserved for the star/locked cards where one poetic line sells the idea.
- `note`: comma-separated clauses, each ~2–4 words. The shelf renders it uppercase — write it in lowercase and let CSS transform.

### Auto-mapping from file names

The init subflow (see `SKILL.md § 3`) auto-generates items with this heuristic:

```js
function auto_item(filename) {
  const base = filename.replace(/\.html$/, '');
  // Strip trailing version: 'hc-kinetic-typography-v18' → 'hc-kinetic-typography'
  const unversioned = base.replace(/-v\d+$/, '');
  // First token is family: 'hc'
  // Remainder becomes ID suffix
  const parts = base.split('-');
  const version_match = base.match(/-v(\d+)$/);
  const id = version_match
    ? `${parts[0].toUpperCase()} · v${version_match[1]}`
    : base.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  return { id, file: filename };
}
```

This is a starting point, not a final answer. The init output is handed back to the user for refinement before any shelf is generated.

---

## 7. Minimal valid manifest

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

This produces a functional curated shelf with two eager-loaded cards. Everything else (notes, tags, quotes) is opinion on top.

---

## 8. Validation rules

Before generating, validate:

- Required fields present (`project`, `title`, `date`, `target_folder`, `segments`).
- `segments` non-empty, every segment has non-empty `items`.
- Every item has `id` and `file`.
- Every referenced `file` exists on disk. Missing files get flagged in the report but do **not** block generation — the card renders with a broken placeholder, which is often what the reviewer wants to see.
- `tag` values (if set) are one of the known slugs. Unknown slugs get flagged and fall back to `original`.
- `layout` value (if set) is `"family"` or `"era"`. Unknown values fall back to `"family"`. In v0.1.0, `"era"` also falls back with a one-line warning — the era template ships in v0.2.
- Segment IDs are unique and kebab-case.

Report validation warnings before generation. Do not silently coerce — the user should know what was missing.

---

## 9. Re-generation and diffing

When re-generating over an existing shelf:

1. Read the existing `_iterations.html` (or `_monster-index.html`).
2. Extract any hand-edited banners, custom JS, or manifest-external modifications from the existing file.
3. Compare the rendered-from-manifest output against the existing file. If they differ **only** in the `SEGMENTS` payload, overwrite silently.
4. If they differ in structure (banners, custom notes, added scripts), present the diff to the user and ask whether to overwrite, keep the existing, or merge.

The shelf is a reviewer's tool — their modifications outrank the machine's.
