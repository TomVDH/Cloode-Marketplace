---
description: Scaffold a Python CSV reader — reads one or more CSV files, prints a summary table, and optionally filters or aggregates rows. Stdlib only.
allowed-tools: Read, Write, Bash
---

Scaffold a Python CSV reader/reporter using the `python-helper` skill.

Ask the user for:
1. CSV file path (or glob pattern for multiple files)
2. Which columns to display and their widths
3. Any filters (e.g. rows where column X equals value Y)
4. Whether to aggregate (count, sum, group-by) or just list rows
5. Whether to support `--json` output mode

Generate the script using the patterns from
`${CLAUDE_PLUGIN_ROOT}/references/python-helpers.md`:
- `csv.DictReader` for named column access
- `pathlib.Path.glob()` if processing multiple files
- `cell()` truncation for every column
- Emoji section headers: file path, row count, any filter summary
- `--limit`, `--filter`, and optionally `--json` flags
- stdlib only — no pandas, no external dependencies

Save to the current working directory as `<script-name>.py` and make it executable.
