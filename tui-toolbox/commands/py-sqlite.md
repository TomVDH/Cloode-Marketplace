---
description: Scaffold a Python sqlite reader — connects to a local database, lists tables, and prints a formatted query readout with column alignment and row count.
allowed-tools: Read, Write, Bash
---

Scaffold a Python sqlite reader script using the `python-helper` skill.

Ask the user for:
1. Path to the sqlite database (or a glob pattern if the path is versioned)
2. Which table(s) to query
3. Which columns to show and the display widths
4. Sort column and order, and row limit
5. Whether to support `--json` output mode for piping

Generate the script using the sqlite patterns from
`${CLAUDE_PLUGIN_ROOT}/references/python-helpers.md`:
- Dynamic db-path resolution with `Path.home()` or glob
- `conn.row_factory = sqlite3.Row` for named column access
- `?` placeholders — never f-string values into SQL
- `cell()` truncation for every column
- Emoji section headers: database path, table name, row count summary
- `--limit`, `--dry-run`, and optionally `--json` flags

Save to the current working directory as `<script-name>.py` and make it executable.
