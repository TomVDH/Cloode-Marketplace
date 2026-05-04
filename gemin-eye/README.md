# GeminEye

Invoke Gemini as a **sandboxed review partner** from inside Claude Code.

GeminEye gives Claude a controlled way to consult Gemini for second
opinions, focused reviews, and reasoning checks — without letting
Gemini sprawl across the project. Context goes in deliberately.
Every prompt follows a rigid template. Gemini reviews only — Claude
applies any edits.

## Install

Ships as part of the `onnozelaer-claude-marketplace`. Once installed,
the `gemin-eye` skill activates on the `/gemin-eye` command, its
subcommands, or natural-language phrases ("ask Gemini", "second
opinion", "Gemini review").

**Requires:** the `gemini` CLI on `PATH`, recent enough to support
`--sandbox`. Install: <https://github.com/google-gemini/gemini-cli>

**Pairs with (optional but recommended):**
- `obsidian-bridge` — auto-loads project context from the Obsidian
  vault and routes outputs into the project's `gemin-eye/` subfolder.
- `cabinet-of-imd` — when active, Bostrol indexes GeminEye outputs
  as documentation artefacts.

## Subcommands

```
/gemin-eye review <target>              Focused review of one artefact — flash
/gemin-eye megareview <scope>           Broad sweep across module / feature / plugin — pro
/gemin-eye wip                          Review uncommitted + current branch work — flash
/gemin-eye sanity <topic>               Steel-man + failure modes + alternative — flash
/gemin-eye name <thing(s)>              Naming bikeshed — flash
/gemin-eye compare <A> <B> [<C>...]     Head-to-head ranking — flash
/gemin-eye save [topic]                 Persist last in-line review to gemin-eye/ folder
```

## Behaviour at a glance

| Aspect | Default |
|---|---|
| Trigger | Explicit phrases or `/gemin-eye` subcommand |
| Sandbox | Always (`--sandbox`). Folder is not trusted by Gemini |
| Permissions | Review-only. No `--yolo`. No write tools |
| Default model | `gemini-3.5-flash` |
| `megareview` model | `gemini-3.5-pro` |
| Prompt shape | Rigid ROLE / DO / DON'T / SCOPE / OUTPUT / CONTEXT |
| Edits | Returned as elaborate code blocks; Claude applies |
| Context | Claude-prepared bundle, project Markdown, vault if available |
| Source-code reads | Only when explicitly named or *is* the target |
| Output destination | `docs/gemin-eye/` or `${VAULT}/projects/{slug}/gemin-eye/` |
| Persistence | In-line by default; `save` for explicit persist |

## What it is not

- Not an autonomous agent — every call is initiated in response to a Tom request.
- Not a code generator — Gemini's output never lands in source files
  without Claude's review and Tom's approval.
- Not a project scaffolder — the one allowed scaffold is `docs/gemin-eye/`.

See `skills/gemin-eye/SKILL.md` for full operating protocol and
`references/invocation-patterns.md` for filled-in templates per
subcommand.

## Author

Onnozelaer
