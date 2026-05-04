---
description: Sandboxed Gemini review partner — review, megareview, wip, sanity, name, compare, save.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Gemini review and second-opinion partner. Dispatches to the `gemin-eye` skill.

## Subcommands

```
/gemin-eye review <target>              Focused review of one artefact (code, doc, prompt) — flash
/gemin-eye megareview <scope>           Broad sweep across module / feature / plugin — pro
/gemin-eye wip                          Review uncommitted + current branch work in flight — flash
/gemin-eye sanity <topic>               Steel-man + failure modes + alternative — flash
/gemin-eye name <thing(s)>              Naming bikeshed (one or related set) — flash
/gemin-eye compare <A> <B> [<C>...]     Head-to-head ranking of options — flash
/gemin-eye save [topic]                 Persist last in-line review to gemin-eye/ folder
```

**Defaults:** sandboxed (`--sandbox`), review-only (no `--yolo`),
model `gemini-3.5-flash` except `megareview` which uses `gemini-3.5-pro`.

Every Gemini call wraps the prompt in the rigid ROLE / DO / DON'T /
SCOPE — IN / SCOPE — OUT / OUTPUT / CONTEXT template defined in
`${CLAUDE_PLUGIN_ROOT}/references/invocation-patterns.md`. Edits
return as elaborate code blocks; Claude applies them.

Parse the user's subcommand and arguments, then invoke the
`gemin-eye` skill with the appropriate action.
