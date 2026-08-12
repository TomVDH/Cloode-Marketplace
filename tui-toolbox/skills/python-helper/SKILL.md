---
name: python-helper
description: >
  This skill should be used when the user asks to create a Python helper script,
  read-and-report tool, data reader, local data query, or any Python CLI utility
  that fetches and prints structured output. Trigger phrases: "python helper",
  "read local data", "query sqlite", "python script", "sqlite reader", "data
  reporter", "python cli", "parse json", "csv reader". For interactive bash tools
  with menus and animations, use the bash-tui skill instead.
---

# Python Helper Scripts

Clean, stdlib-only Python scripts for reading local data — sqlite databases,
files, JSON, CSV — and printing structured output. Same two-space indent and
emoji marker aesthetic as the bash-tui skill; different purpose: these are
read-and-report tools, not interactive TUI applications.

## When to use this skill (not bash-tui)

- Querying sqlite databases — `sqlite3` module with named column access
- Parsing JSON or CSV — stdlib `json` / `csv`, no `jq` dependency
- Any logic involving string manipulation, date parsing, or arithmetic
- Scripts whose output will be consumed by other tools (piped, JSON mode)

## Scope: human-facing helpers

The operating language covers helpers a person reads: tables, section headers,
emoji markers, truncated cells. Agent-facing JSON emitters, meaning tools whose
output is parsed by an agent rather than read by a human (e.g. the
`adjudant/scripts` helpers in this marketplace), are a different genre with
different rules and are intentionally out of scope. A `--json` flag on a
human-facing helper is fine; a tool that only ever speaks JSON to another
program is not this skill's territory.

## Reference

Load these references before writing any Python helper script:

- `${CLAUDE_PLUGIN_ROOT}/references/design-language.md` — inherit the shared visual language (palette, markers, two-space indent) — python helpers look the same as bash tools.
- `${CLAUDE_PLUGIN_ROOT}/references/python-helpers.md` — python-specific patterns; it contains:

- Emoji section header pattern
- ANSI section header pattern (for structured tools)
- `cell()` table helper (truncate-before-print)
- Full starter template with `die()`, `section()`, argparse, sqlite3
- SQLite patterns: `row_factory`, parameterized queries, epoch conversion
- `--json` output mode for piping
- Rules and what-not-to-do list

Python helpers share the same palette, status markers, and two-space indent law as bash tools — the design-language spine applies to both.

## Core Rules (enforced without reading the reference)

- `#!/usr/bin/env python3` — always
- stdlib only — no `pip install` for simple read scripts
- `from pathlib import Path` — all file paths
- `conn.row_factory = sqlite3.Row` — named columns, always
- `die()` for all fatal errors — consistent exit messaging
- Two-space indent on every output line
- `cell()` helper — truncate before print, never after
- `?` placeholders in SQL — never f-string values into queries
