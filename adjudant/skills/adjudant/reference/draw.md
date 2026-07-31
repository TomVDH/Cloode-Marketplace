# /adjudant draw

Create visual artefacts in the vault. Sub-verb router for canvas / base / diagram.

## The 3 features (locked spec)

1. `/adjudant draw canvas <name>` — create or open `{vault}/projects/{slug}/canvases/{kebab-name}.canvas`. Loads `reference/content-canvas.md`.
2. `/adjudant draw base <name>` — create or open `{vault}/projects/{slug}/bases/{kebab-name}.base`. Loads `reference/content-bases.md`.
3. `/adjudant draw diagram [type]` — insert a fenced `mermaid` block into the current note. `type` optional: `flowchart | sequence | class | state | erd | gantt | mindmap | timeline | gitGraph | pie | quadrant | journey | C4`. Loads `reference/content-mermaid.md` + `reference/mermaid-generation-rules.md`.

## Inputs

```
/adjudant draw canvas user-flow          # creates user-flow.canvas
/adjudant draw base research-targets     # creates research-targets.base
/adjudant draw diagram flowchart         # inserts a flowchart mermaid block
/adjudant draw diagram                   # asks for type, then inserts
```

## Diagram type → mermaid keyword

The `type` tokens map to these first-line keywords (see `content-mermaid.md` for full syntax):

| Use case | `type` token | First line inside the fence |
|---|---|---|
| Process / pipeline | `flowchart` | `flowchart LR` (or `TD` for deep trees) |
| Actor message passing | `sequence` | `sequenceDiagram` |
| Object model | `class` | `classDiagram` |
| Lifecycle with loops/retries | `state` | `stateDiagram-v2` |
| Data model | `erd` | `erDiagram` |
| Schedule | `gantt` | `gantt` |
| Idea tree | `mindmap` | `mindmap` |
| Chronology | `timeline` | `timeline` |
| Branch/merge history | `gitGraph` | `gitGraph` |
| Proportions | `pie` | `pie` |
| Effort/impact sort | `quadrant` | `quadrantChart` |
| User-flow stages | `journey` | `journey` |
| System architecture | `C4` | `C4Context` / `C4Container` / `C4Component` |

## Generated diagrams (helper-backed)

For diagrams **derived from vault data**, don't hand-draw — `scripts/graph.py`
(read-only, node-capped, labels quoted + role classDefs per the generation
rules) emits a paste-ready fence. Review its topology against rules §1/§7
(cycles, hub nodes) before pasting:

```bash
python3 .../scripts/graph.py --project-dir "$PROJECT_ROOT" --mode relations   # wikilink graph of the project
python3 .../scripts/graph.py --project-dir "$PROJECT_ROOT" --mode board      # kanban snapshot of board-data.json
python3 .../scripts/graph.py --mode tiers                                    # the tidy→ramasse→dream model
```

Generating a *scaffold* from mechanical vault data is scaffolding, not content
authoring — the "no content generation" rule below is about prose/design inside
canvases and bases, which stays the user's job.

### `--out`, the one write graph.py makes

Default to stdout and paste. `--out FILE` captures the fence to a file instead,
and it is the only write the helper performs, so it is gated:

- **Contained.** The path must resolve inside the vault project or inside
  `--project-dir`. Anywhere else is refused and nothing is written. Symlinks
  are resolved first, so a link pointing out of the project does not slip past.
- **No silent clobber.** An existing file is refused. `--force` replaces it and
  copies the current contents to a dot-prefixed, timestamped sibling first
  (`.brief.md.20260731-120000.bak`), invisible to Obsidian and to the vault
  walkers. A backup that fails cancels the write.
- **Atomic.** A run that fails part way leaves the target byte for byte as it
  was.

`--out` is for capturing a fence, not for authoring vault notes. A bare fence
has no frontmatter, so an `.md` written straight into the vault this way is a
schema-less note that `check` will report. Paste into a real note instead.

## Diagram embed points

Two places a generated fence earns its keep (check topology against the
generation rules before pasting):

1. **Session note, board snapshot**: `graph.py --mode board` appended to today's
   session note is a point-in-time record of the kanban state (what was open the
   day a decision landed). Not auto-regenerated; each paste is a dated snapshot.
2. **Briefs and docs, tiers fence**: `graph.py --mode tiers` renders the
   tidy/ramasse/dream cleanup model for a brief or doc that explains the
   maintenance story.

## Naming

Per `reference/vault-standards.md`: `.canvas` and `.base` files use **strict kebab-case**
(`my-cool-canvas.canvas` ✓ — `MyCoolCanvas.canvas` ✗). `ramasse` flags violations
(`detect_artefact_naming` in `ramasse_scan.py`).

## Folders

`canvases/` and `bases/` are **auto-created on first invocation** — they're in
`AUTO_CREATED_FOLDERS` (vault-standards §5), so no `extra_folders` declaration in
the brief is needed and `ramasse` never flags them as drift. Reserve the brief's
`extra_folders` for genuinely custom subfolders.

## Fail conditions

- No breadcrumb at cwd → exit non-zero with "run `/adjudant connect` first"
- File already exists at target path → open for editing, don't recreate
- `graph.py --out` resolving outside the project and outside `--project-dir` →
  exit non-zero, nothing written
- `graph.py --out` at a path that already exists, without `--force` → exit
  non-zero, nothing written and no backup spent

## What draw does NOT do

- No design/layout intelligence (that's the user's job)
- No prose/content generation inside canvases or bases (only scaffolds the file;
  mechanical `graph.py` scaffolds are the deliberate exception for mermaid)
