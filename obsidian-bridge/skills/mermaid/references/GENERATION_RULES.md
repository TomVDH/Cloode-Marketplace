# Mermaid generation rules

Reference for **generating** Mermaid diagrams (not just understanding existing ones). Encoded as a punch-list of rules organised by the failure modes they prevent. Apply these whenever the model is producing new ```` ```mermaid ```` content — flowcharts especially, but most apply to other diagram types too.

The base SKILL.md covers syntax. This file covers *taste and discipline*.

---

## 1. Topology rules (the biggest lever)

These shape how Dagre lays the graph out. Get them wrong and no amount of styling rescues the diagram.

- **One terminal per path.** Never converge multiple branches into a single shared "End" node. Generate `END_a`, `END_b`, `END_c` ... — duplicates are free; edge crossings are not.
- **Pure DAGs only.** No back-edges, no cycles. If the source data has a loop, **break it** (e.g. annotate the loop edge as a label `"on retry"` and stop the line at a re-entry marker; don't actually draw the back-edge).
- **Mirror parallel branches.** When N branches do similar things, make them isomorphic: same node count, same depth, same shape. Dagre aligns them onto matching layers and the grid emerges automatically.
- **No cross-branch edges.** If branch A's middle step needs to talk to branch C's middle step, the diagram is wrong — emit two diagrams or rethink the abstraction.
- **Avoid hub nodes.** A node with >5 incoming or >5 outgoing edges is a layout disaster. Split into multiple nodes or change the representation.
- **Avoid `subgraph` blocks for layout grouping.** Use color (`classDef`) instead. Subgraphs constrain Dagre and usually make things worse, not better.

---

## 2. Label rules — parser safety

These cause silent rendering failures or "unsupported markdown" errors:

- **Never start a label with a markdown-list pattern:** `1. `, `- `, `* `, `+ `, `# `, `> `. If the source has step numbers, render as `"1 — Foo"` (em-dash) or `"Step 1: Foo"`, not `"1. Foo"`.
- **Use `<br>`, not `<br/>`.** XHTML self-closing form is unreliable across Mermaid versions.
- **Always quote labels:** `A["text"]`, never `A[text]`. Cheap, prevents 90% of parser surprises.
- **Avoid `==x==` patterns.** Markdown-string mode interprets these as highlights. For comparison ops, prefer `is`, `equals`, or just `=`.
- **Escape or substitute literal `<`, `>`, `&` in label content** (`&lt;`, `&gt;`, `&amp;`).
- **No backticks in labels** unless you actually want markdown-string mode.

---

## 3. Label rules — visual cleanliness

- **Keep label width uniform.** Wildly varying widths force uneven row heights and the grid breaks. Cap labels at ~30 chars per line; wrap with `<br>`.
- **Two-line labels max.** Line 1 = action verb + role. Line 2 = detail. Three+ lines starts to push neighbours.
- **Edge labels: 1–2 words.** `true`, `false`, `retry`, `step 3`. Long edge labels shove nodes apart asymmetrically.
- **Don't repeat noise across labels.** If every node says `"Action — ..."`, drop `"Action —"`. The shape conveys role; the label conveys specifics.

---

## 4. Direction heuristics

| Shape | Direction |
|---|---|
| Decision tree, fan-out, workflow with branches | `TD` (default) |
| Linear pipeline ≤7 steps | `LR` |
| Linear pipeline >7 steps | `TD` (LR will overflow horizontally) |
| State machine with bidirectional transitions | `stateDiagram-v2`, not `flowchart` |
| Sequence of interactions between actors | `sequenceDiagram`, not `flowchart` |

**Default to `TD` when uncertain.** `LR` only when the diagram is genuinely linear.

---

## 5. Styling system

- **One `classDef` per semantic role, applied uniformly.** Don't use inline style `A fill:...` — it doesn't scale.
- **Encode role in the node-generation step, not at render time.** Know "this is a delay" / "this is a decision" / "this is a terminal" and stamp the class accordingly.
- **Set `fill`, `stroke`, AND text color explicitly.** Defaults render badly on dark themes.
- **Stroke-width 1px standard, 1.5–2px for emphasis** (e.g. the terminal write that flips a flag).
- **Bound the palette to ~6 classes max.** More colors = noise. Suggested base set:
  - `delay` — cool blue
  - `decision` / `branch` — amber
  - `action` / `edit` — orange
  - `terminal` — red (final write, the action that flips a flag)
  - `send` / `output` — green
  - `endNode` — gray

---

## 6. Renderer config

- **Use the default Dagre layout for flowcharts.** Don't enable `elk` for fan-outs — it tends to over-compact.
- **`flowchart.htmlLabels: true`** (it's the default) so `<br>` works.
- **`securityLevel: 'loose'`** only if you need clickable nodes; otherwise leave default.
- **Front-matter config is more portable than `%%{init}%%` blocks:**

  ```yaml
  ---
  config:
    theme: default
    flowchart:
      curve: basis
  ---
  ```

  Place this at the very top of the diagram body (before the `flowchart TD` / `flowchart LR` line).

---

## 7. Anti-patterns to refuse

The model should refuse to emit any of these — fix the diagram instead:

- A single `End` node with >2 inbound edges
- Any node with >5 inbound or >5 outbound edges
- Labels matching `^\s*\d+\.\s` (numbered-list trigger)
- `<br/>` in labels
- Mixed quote styles (some labels quoted, others not)
- More than 6 distinct fill colors
- `subgraph` containing >10 nodes

---

## 8. Validation step before render

Before writing the diagram to the note, run a pre-flight pass:

- **Parse it through Mermaid's parser headlessly** if available; catch errors before write.
- **Check the anti-patterns above** with a quick regex/count sweep.
- **Optional:** render to SVG, count edge crossings (Dagre exposes this), warn if >N for diagram size.

---

## See also

- `obsidian-bridge:mermaid` (parent SKILL.md) — syntax reference for each diagram type
- `obsidian-bridge:vault-standards` — where in the vault diagrams should live (notes, briefs, decisions, dream reports)
- Spec: <https://mermaid.js.org/intro/>
