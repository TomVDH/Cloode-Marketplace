# Remember Plugin Integration

Light, opt-in integration between obsidian-bridge and the `remember` Claude Code plugin. Bridge does not absorb remember's compression pipeline — it only mirrors the output.

## Direction

| Direction | Mechanism | Behavior |
|---|---|---|
| remember → vault | `/vault-bridge handoff sync` | Read `$CLAUDE_PROJECT_DIR/.remember/remember.md`, mirror to `{vault}/projects/{slug}/_handoff.md` with `type: handoff` frontmatter. Single file per project, overwritten each sync. |
| remember → vault (auto) | SessionEnd hook (opt-in) | If `remember.md` mtime > `_handoff.md` mtime + active project breadcrumb, emit one-line nudge. |
| vault → remember | n/a | Bridge never writes to `.remember/`. |

## Handoff File

Lives at `projects/{slug}/_handoff.md`. Underscore prefix pins it at top of folder listing.

```yaml
---
type: handoff
project: "[[projects/{slug}/brief|{slug}]]"
updated: 2026-04-30
source: remember
tags:
  - ob/handoff
---
```

Body: verbatim copy of `remember.md` content, preceded by a header noting source and timestamp.

## Status Surface

`/vault-bridge status` shows: `Remember plugin: detected — last handoff sync: 2026-04-29` when `.remember/` exists in the working directory.

## Enabling Auto-Nudge

Set env var `OB_SESSION_END_NUDGE=1` or configure in Claude Code settings. The SessionEnd hook checks remember.md mtime vs _handoff.md mtime and emits a one-line reminder if the handoff is stale.
