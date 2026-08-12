---
description: Scaffold a new Python helper script from the starter template — argparse, die(), section(), cell() table helper, and clean emoji-led output wired up and ready.
allowed-tools: Read, Write, Bash
---

Scaffold a new Python helper script using the `python-helper` skill.

Ask the user for:
1. Script name and one-line description
2. Data source — sqlite database path, JSON file, CSV, API endpoint, or local files
3. What the output should show (table, list, summary stats, etc.)
4. Any flags beyond `--limit` and `--dry-run`

Then generate the full script from the starter template in
`${CLAUDE_PLUGIN_ROOT}/references/python-helpers.md`:
`die()`, `section()`, `cell()`, argparse setup, the appropriate data-reading
block (sqlite / json / csv / file), and clean emoji-led formatted output.

Save to the current working directory as `<script-name>.py` and make it executable.
