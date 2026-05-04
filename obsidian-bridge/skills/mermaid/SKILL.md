---
name: mermaid
description: Use when authoring or editing Mermaid diagrams in fenced ```mermaid``` code blocks — flowcharts, sequence, ER, class, state, gantt, mindmap, timeline, gitGraph, pie, quadrant, journey, C4 — especially inside Obsidian notes.
allowed-tools: Read, Write, Edit, Glob, Grep
version: 0.1.0
---

# Mermaid

Mermaid renders diagrams from Markdown-inspired text. Obsidian renders ```` ```mermaid ```` fenced blocks natively (no plugin) since v0.13. This skill is the reference for valid syntax across diagram types and the gotchas that bite inside an Obsidian vault.

## When to Use

- The user asks for a flowchart, sequence diagram, ERD, state machine, gantt, mindmap, etc. inside a `.md` note.
- A note already contains a ```` ```mermaid ```` block that needs editing or fixing.
- The model is about to draw an ASCII diagram in a Markdown file → switch to Mermaid instead.
- Producing a diagram for a brief, decision record, or doc inside an `obsidian-bridge` vault.

## Core Rules

- **Always use a fenced block** with `mermaid` as the language: ```` ```mermaid ```` ... ```` ``` ````.
- **Diagram type goes on the first line inside the fence** (`flowchart LR`, `sequenceDiagram`, `erDiagram`, etc.).
- **One diagram per fence.** Multiple fences in the same note is fine.
- **Quote labels with special characters** (colons, parens, `<`, `>`, `#`, `"`): `A["Some: label (v2)"]`.
- **Wikilinks (`[[note]]`) do NOT work inside Mermaid.** Use external URL clicks: `click NodeId "https://..."`.
- **Long labels** — wrap with `<br>` for explicit line breaks. (NOT `<br/>` — XHTML self-closing form is unreliable across Mermaid versions.)
- **Comments** inside Mermaid: `%% this is a comment` (not `//` and not `#`).

## Generation discipline (READ THIS BEFORE GENERATING)

When **producing** new diagrams (not just understanding existing ones), follow the discipline in [`references/GENERATION_RULES.md`](references/GENERATION_RULES.md). Eight rule groups covering:

1. **Topology** — one terminal per path, pure DAGs only, mirror parallel branches, no hub nodes, avoid subgraphs for layout grouping
2. **Label parser safety** — quote always, no markdown-list prefixes, `<br>` not `<br/>`, escape `<>&`
3. **Label visual cleanliness** — uniform width, two-line max, terse edge labels
4. **Direction heuristics** — when `TD` vs `LR` vs `stateDiagram-v2` vs `sequenceDiagram`
5. **Styling** — one `classDef` per role, palette ≤6, role stamped at generation time
6. **Renderer config** — front-matter config preferred over `%%{init}%%`, default Dagre layout
7. **Anti-patterns to refuse** — single End with >2 inbound, hub nodes >5 edges, etc.
8. **Validation** — pre-flight parse + anti-pattern check before write

The base SKILL.md (this file) covers syntax. `GENERATION_RULES.md` covers taste and discipline. Both apply when generating.

## Diagram Types — Quick Reference

### Flowchart (most common)

```mermaid
flowchart LR
  A[Start] --> B{Decision?}
  B -->|yes| C[Do thing]
  B -->|no| D[Skip]
  C --> E([End])
  D --> E
```

Directions: `TB` (top-bottom), `TD` (same), `BT`, `LR` (left-right), `RL`.

Node shapes: `[rect]`, `(round)`, `([stadium])`, `[[subroutine]]`, `[(cylinder)]`, `((circle))`, `>asymmetric]`, `{rhombus}`, `{{hexagon}}`, `[/parallelogram/]`, `[\trapezoid\]`.

Edge styles: `-->` (arrow), `---` (line), `-.->` (dotted), `==>` (thick), `--text-->`, `-->|label|`, `~~~` (invisible link).

Subgraphs:
```mermaid
flowchart LR
  subgraph cluster [Cluster Title]
    A --> B
  end
  B --> C
```

### Sequence Diagram

```mermaid
sequenceDiagram
  participant U as User
  participant S as Server
  U->>S: GET /resource
  S-->>U: 200 OK
  Note over U,S: handshake complete
  U->>+S: POST /thing
  S-->>-U: 201 Created
```

Arrows: `->>` (solid), `-->>` (dashed), `-x` (cross), `--x`, `-)` (open async).
`activate`/`deactivate` (or `+`/`-` shorthand on arrows) shows lifelines.

### Class Diagram

```mermaid
classDiagram
  class Animal {
    +String name
    +int age
    +eat() void
  }
  class Dog
  Animal <|-- Dog : inheritance
  Animal "1" *-- "many" Owner : composition
```

Relations: `<|--` (inherit), `*--` (composition), `o--` (aggregation), `-->` (assoc), `..>` (depend), `..|>` (realize).

### State Diagram

```mermaid
stateDiagram-v2
  [*] --> Idle
  Idle --> Loading : start
  Loading --> Done : ok
  Loading --> Error : fail
  Done --> [*]
  Error --> Idle : retry
```

Composite states with `state X { ... }`. Forks/joins via `<<fork>>`, `<<join>>`.

### Entity-Relationship (ERD)

```mermaid
erDiagram
  CUSTOMER ||--o{ ORDER : places
  ORDER ||--|{ LINE-ITEM : contains
  CUSTOMER {
    string name
    string email PK
  }
  ORDER {
    int id PK
    date created
  }
```

Cardinality glyphs: `|o` (zero or one), `||` (exactly one), `}o` (zero or many), `}|` (one or many). Mirror on each side.

### Gantt

```mermaid
gantt
  title Release plan
  dateFormat YYYY-MM-DD
  section Build
    Spec        :a1, 2026-05-01, 5d
    Implement   :after a1, 10d
  section Ship
    QA          :2026-05-20, 3d
    Release     :milestone, 2026-05-25, 0d
```

### Mindmap

```mermaid
mindmap
  root((central))
    Branch A
      leaf 1
      leaf 2
    Branch B
      leaf 3
```

Two-space indentation defines hierarchy. Root shapes: `(round)`, `((circle))`, `))cloud((`, `)bang(`.

### Timeline

```mermaid
timeline
  title Vault history
  2024 : v1 launched
  2025 : v2 schema rewrite
       : cabinet integration
  2026 : v3 — bridge plugin extracted
```

### Git Graph

```mermaid
gitGraph
  commit
  branch feature
  checkout feature
  commit
  checkout main
  merge feature
```

### Pie

```mermaid
pie title Time per task
  "Coding"     : 45
  "Reviewing"  : 25
  "Meetings"   : 30
```

### Quadrant Chart

```mermaid
quadrantChart
  title Effort vs Impact
  x-axis Low Effort --> High Effort
  y-axis Low Impact --> High Impact
  quadrant-1 Quick wins
  quadrant-2 Major projects
  quadrant-3 Fill-ins
  quadrant-4 Thankless
  Refactor auth: [0.4, 0.7]
  Rename folder: [0.1, 0.2]
```

### User Journey

```mermaid
journey
  title Onboarding flow
  section Signup
    Land on page: 5: User
    Fill form:    3: User
  section First use
    Create vault: 4: User
    Hit error:    1: User, System
```

Score scale 0–5 per actor; multiple actors comma-separated.

### C4 (Context / Container / Component)

```mermaid
C4Context
  Person(user, "User")
  System(app, "App")
  Rel(user, app, "uses")
```

Variants: `C4Context`, `C4Container`, `C4Component`, `C4Dynamic`. Useful pair with the plugin's existing `c4-container` / `c4-component` skills.

## Obsidian-Specific Notes

- **Native rendering, no plugin needed.** Works in reading view, live preview, and exported PDFs.
- **Theme follows Obsidian theme.** Light/dark switches automatically. Per-diagram theme overrides via `%%{init: {...}}%%` directive at the top of the fence (advanced — usually leave alone for vault consistency).
- **Wikilinks are NOT parsed inside Mermaid.** If a node should link to another vault note, prefer a separate Markdown wikilink under the diagram, or use `click NodeId "obsidian://open?vault=...&file=..."`.
- **Embedded diagrams (`![[other-note]]`)** that contain Mermaid will render in the embedding note.
- **Inside callouts** Mermaid still renders, but indentation must be preserved per callout block.

## Common Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Diagram shows as raw text | Wrong fence language tag | Must be exactly `mermaid`, lowercase |
| `Syntax error in graph` at first line | Diagram-type keyword missing or misspelled | First line inside fence is `flowchart LR` (etc.) |
| Labels with `:` or `()` break parsing | Unquoted special chars | Wrap in `"..."`: `A["Label: with colon"]` |
| Edge label disappears | Wrong syntax | Use `-->|label|` not `-- label -->` for flowchart |
| Wikilink renders as literal text | Not supported | Use external URL via `click`, or external Markdown link below the diagram |
| Sequence diagram lifelines don't show | Missing `activate`/`+` | Use `->>+ S` and `-->>- U` shorthand |
| ERD cardinality wrong | Glyph mirrored incorrectly | Left of `--` = left entity's perspective |
| Gantt `dateFormat` mismatch | Format string doesn't match dates | Default is `YYYY-MM-DD`; set explicitly if other |
| Mindmap nodes flatten | Inconsistent indentation | Use exactly 2 spaces per level, no tabs |
| Theme variables ignored | `%%{init}%%` syntax wrong | Must be the very first line, valid JSON5 |

## When NOT to Use Mermaid

- One-node "diagrams" — use a sentence.
- Free-form sketches, illustrations — use an image (`![[diagram.png]]`).
- Real architecture diagrams meant for stakeholders — consider a dedicated tool (Excalidraw, Draw.io) and embed the result.
- Anything where layout precision matters — Mermaid is auto-laid-out; you cannot pin positions in most diagram types.

## Cross-References

- Obsidian rendering specifics: see `obsidian-bridge:markdown` for the broader Obsidian-flavored Markdown context.
- C4-shaped architecture diagrams: pair with skills `c4-context`, `c4-container`, `c4-component`, `c4-code` (separate plugins) when modelling systems.
- Upstream syntax canon: <https://mermaid.js.org/intro/>.
