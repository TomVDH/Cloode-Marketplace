---
description: Create or list visual artefacts — canvases, bases, mermaid diagrams
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Entry point for Obsidian's visual structures. Routes to the right skill based on subverb.

## Usage

```
/draw                          List visual artefacts in current project (canvases, bases, recent mermaid blocks)
/draw canvas <name>            Create or edit a .canvas file (loads canvas skill)
/draw base <name>              Create or edit a .base file (loads bases skill)
/draw diagram [type]           Insert a mermaid diagram into the current note (loads mermaid skill)
                               type optional — flowchart | sequence | class | state | erd |
                                              gantt | mindmap | timeline | gitGraph |
                                              pie | quadrant | journey | C4
```

## Routing

Subverb dispatch (no separate `draw` skill — the command body itself routes):
- `/draw canvas <name>` → loads `obsidian-bridge:canvas` skill, creates/opens `.canvas` file at vault-canonical path (typically `projects/{slug}/canvases/{name}.canvas`).
- `/draw base <name>` → loads `obsidian-bridge:bases` skill, creates/opens `.base` file (typically `projects/{slug}/bases/{name}.base`).
- `/draw diagram [type]` → loads `obsidian-bridge:mermaid` skill, inserts a fenced `mermaid` block into the current note (or asks user where to insert if no note open).
- `/draw` (no subverb) → invokes the `vault-bridge` skill's `draw-list` flow to enumerate visual artefacts in the current project.
