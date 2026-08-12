---
description: Scaffold a new polished bash TUI script using the bash-tui skill — strict mode, semantic palette, cleanup trap, chevron menu, and section headers wired up and ready.
allowed-tools: Read, Write, Bash
---

Scaffold a new bash TUI script using the `bash-tui` skill.

Ask the user for:
1. Script name and one-line description
2. Whether it needs a menu (and what the menu options are), or just a linear run
3. Whether it calls any external tools (curl, sqlite3, etc.)

Then generate the full script using the mandatory checklist from the `bash-tui` skill:
strict mode + cleanup trap, semantic palette, terminal control functions, `trunc()` helper,
two-space indent, status markers, and section headers. Wire in a splash banner and the
appropriate component (menu loop or linear flow) based on user input.

Save to the current working directory as `<script-name>.sh` and make it executable.
