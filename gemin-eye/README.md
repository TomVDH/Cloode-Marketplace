# GeminEye

Invoke Gemini as a review and coding partner from inside Claude Code.

GeminEye gives Claude a controlled way to consult Gemini for second
opinions, focused reviews, and reasoning checks — without letting Gemini
sprawl across the project. Context goes in deliberately. Outputs land in
a single, predictable folder. Source files are never written by Gemini
unless Tom explicitly says so.

## Install

This plugin ships as part of the `onnozelaer-claude-marketplace`
marketplace. Once installed, the `gemin-eye` skill activates on phrases
like "ask Gemini", "second opinion", "Gemini review", or the explicit
`/gemin-eye` command.

**Requires:** the `gemini` CLI on `PATH`. Install: <https://github.com/google-gemini/gemini-cli>

**Pairs with (optional but recommended):**
- `vault-bridge` (from `cabinet-of-imd`) — auto-loads project context
  from the Obsidian vault and routes outputs into the project's
  `gemin-eye/` subfolder.
- `cabinet-of-imd` — when active, Bostrol owns indexing of GeminEye
  artefacts as documentation.

## Behaviour at a glance

| Aspect | Default |
|--------|---------|
| Trigger | Explicit phrases or `/gemin-eye` |
| Context source | Claude-prepared bundle, project Markdown, vault if available |
| Source-code reads | Only when explicitly named or *is* the review target |
| Source-code writes | None (use override clause to relax) |
| Output destination | `docs/gemin-eye/` or `${VAULT}/projects/{slug}/gemin-eye/` |
| Persistence | Inline by default; persisted only when worth keeping |

## What it is not

- Not an autonomous agent — every call is initiated in response to a Tom request.
- Not a code generator for the project — Gemini's output never lands in
  source files without Claude's review and Tom's approval.
- Not a project scaffolder — the one allowed scaffold is `docs/gemin-eye/`.

See `skills/gemin-eye/SKILL.md` for full operating protocol and
`references/invocation-patterns.md` for reusable prompt scaffolds.

## Author

Onnozelaer
