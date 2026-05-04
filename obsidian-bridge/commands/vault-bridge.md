---
description: Vault operations — create, connect, scaffold, sync, status, housekeeping, migrate, iterations, handoff.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Obsidian vault management. Dispatches to the `vault-bridge` skill.

## Subcommands

```
/vault-bridge create [path]                     Scaffold new v3 vault
/vault-bridge connect <path>                    Connect to existing vault
/vault-bridge link <slug>                       Switch project in current directory
/vault-bridge create-project <slug> <type>      Scaffold type-shaped project
/vault-bridge add-collection <name>             Add sub-collection folder + _index.md
/vault-bridge sync                              Write/update current project's brief
/vault-bridge status                            Vault summary + per-project counts
/vault-bridge archive <slug>                    Move project → archive/
/vault-bridge unarchive <slug>                  Restore archive/ → projects/
/vault-bridge reindex                           Rebuild all _index.md files
/vault-bridge housekeeping                      Full consistency check
/vault-bridge migrate                           v2 → v3 walkthrough
/vault-bridge migrate-anchor                    Move legacy .obsidian-bridge → .claude/obsidian-bridge
/vault-bridge handoff sync                      Mirror .remember/remember.md → _handoff.md
/vault-bridge handoff status                    Show last sync time
/vault-bridge set-type <slug> <type>            Change project type
/vault-bridge templates [list|print <name>]     List/print templates

Iterations:
/vault-bridge add-iteration <id> <slug> [--track <name>] [--with-folder]
/vault-bridge add-iteration-artefact <iter-id> <file>
/vault-bridge iterations [<slug>] [--tree]
/vault-bridge iteration-set-status <iter-id> <status>
```

Parse the user's subcommand and arguments, then invoke the `vault-bridge` skill with the appropriate action.
