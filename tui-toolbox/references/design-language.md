# Design Language

> Both skills inherit this file. `palette.md` holds the raw colors; this file holds the grammar.

The written operating language for agent-built helper CLIs. Every pattern in
this toolkit descends from the rules defined here. Read this before `components.md`
or `palette.md`.

---

## The one principle

Every tool an agent builds must look, feel, and behave as if it came from the
same hand.

- **Visual layer** — shared color roles, two-space margin, Unicode markers; no raw ANSI, no emoji in headers.
- **Interaction layer** — chevron menus with arrow keys; no numbered lists; consistent flag surface (`--dry-run`, `--quiet`, `--help`).
- **Operational layer** — `set -euo pipefail` + `trap cleanup EXIT`; cursor always restored; motion is purposeful, not decorative.

---

## Semantic color roles

All output statements use role names. Never embed raw ANSI codes in a `printf`
directly — assign them to a semantic variable first. Hex/ANSI values live in
`palette.md`; role intent lives here.

| Role | Variable | Intent |
|------|----------|--------|
| TITLE | `COLOR_TITLE` | Section headers, banner text, focus accent |
| SUCCESS | `COLOR_SUCCESS` | Completed actions, passing checks, ✓ markers |
| WARN | `COLOR_WARN` | Degraded state, non-fatal issues, ⚠ markers |
| ERROR | `COLOR_ERROR` | Failures, blocked actions, ✗ markers |
| MUTED / INFO | `COLOR_MUTED` / `COLOR_INFO` | Secondary text, hints, dim status, ℹ markers |
| ACTIVE | `COLOR_ACTIVE` | Spinner frames, focused menu chevron, in-progress state |

Assign roles at the top of every script immediately after the raw palette block:

```bash
# ── Semantic roles ───────────────────────────────────────
COLOR_TITLE="${CYAN}"
COLOR_SUCCESS="${GREEN}"
COLOR_WARN="${YELLOW}"
COLOR_ERROR="${RED}"
COLOR_MUTED="${DIM}"
COLOR_ACTIVE="${CYAN}"
COLOR_INFO="${DIM}"
```

If the tool later needs a different success color, one line changes — not every
`printf` in the file.

---

## The two-space indent law

Every line the user sees starts with at least two spaces. The margin serves two
purposes: visual breathing room, and a reserved slot for status markers.

```
  ✓ Export complete     4,218 records written
  ✗ Permission denied   403 — scope not granted
  ⚠ Vendor CLI          Not on PATH — run installer first
```

The rule applies to section headers, table rows, banners, and inline messages.
The only exception is raw `echo ""` blank lines used for vertical spacing.

---

## Marker vocabulary

Four Unicode markers cover every status state. Use the semantic role color
on the marker character itself; reset before the label.

| Marker | Role | Meaning |
|--------|------|---------|
| `✓` | SUCCESS | Action completed, check passed |
| `✗` | ERROR | Action failed, check blocked |
| `⚠` | WARN | Degraded, partial, or advisory |
| `ℹ` | MUTED / INFO | Neutral information, not actionable |

Standard output pattern:

```bash
printf "  ${COLOR_SUCCESS}✓${RESET} %s\n" "Records exported"
printf "  ${COLOR_ERROR}✗${RESET} %s\n" "Connection refused"
printf "  ${COLOR_WARN}⚠${RESET} %s\n" "Rate limit approaching"
printf "  ${COLOR_INFO}ℹ${RESET}  %s\n" "Dry-run mode active"
```

**No emoji in headers or status output.** `✓ ✗ ⚠ ℹ` are Unicode punctuation,
not emoji — they render consistently in every terminal. Emoji do not.

This no-emoji rule governs **bash** tools. Python helper scripts use an emoji marker set instead (see `python-helpers.md`) — a deliberate, separate aesthetic for the read-and-report tier.

---

## Motion & speed tiers

Motion signals work is happening — but only when something actually is. Animate
loading, ingestion, and transitions. Do not animate idle text or static output.

| Tier | Frame delay | Row delay | Use |
|------|-------------|-----------|-----|
| Slow | 0.08s | 0.15s | Dramatic splash reveals |
| Medium | 0.05s | 0.08s | General-purpose loading |
| **Fast** | **0.02s** | **0.03s** | **Default for all new tools** |

Fast is the default because agents frequently chain tools — a slow per-row
delay across hundreds of records compounds into user friction. Use Slow or
Medium only when the animation itself is the point (splash, first-run ceremony).

---

## Extending the language

New visual patterns enter the language through a four-stage cycle observed in
the gen1 gallery:

1. **Prototype** — build the candidate component as a standalone demo script in
   the project's `demos/` directory (see `architecture.md` → Project Structure).
   Keep it isolated; do not wire it into any live tool yet.
2. **Preview** — add a picker script, `demos/picker-<thing>.sh`, so the variant
   can be compared against the existing language at a glance. Run the picker.
3. **Promote** — if exactly one variant earns its place, copy it into
   `references/components.md` as the canonical implementation. Update this file
   if the addition adds a new role or rule.
4. **Prune** — delete the demo harness and picker. The prototype scaffold does
   not ship.

*Prototype → Preview → Promote → Prune.*

No pattern reaches `components.md` without passing through the picker. No two
canonical implementations of the same component may coexist — promote one,
retire the rest.
