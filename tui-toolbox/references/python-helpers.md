# Python Helper Script Patterns

Simple, clean Python scripts for reading local data — sqlite databases, files,
APIs. Same two-space indent and emoji marker aesthetic as the bash toolkit,
different purpose: these are read-and-report tools, not interactive TUI apps.

**Rule:** stdlib only. `argparse`, `sqlite3`, `sys`, `pathlib`, `json`, `csv`,
`datetime`. No `pip install` for simple helper scripts.

---

## Visual Style

### Emoji Section Headers

Use emoji-led headers for a clean, scannable readout:

```python
print(f"\n📂  Source: {path}")
print(f"🗄️   Tables: {', '.join(tables)}")
print(f"📬  Mailboxes ({len(rows)} found):")
print(f"📧  10 most recent messages:")
print(f"✅  Done — {count} rows\n")
```

Two-space indent on every output line. Emoji + two spaces + content.

### ANSI Section Headers (for structured tools)

When a script has multiple distinct phases, use a named section break:

```python
BOLD  = "\033[1m"
RESET = "\033[0m"
DIM   = "\033[2m"
CYAN  = "\033[0;36m"

def section(title: str) -> None:
    print(f"\n  {CYAN}{BOLD}━━ {title} ━━{RESET}\n")
```

### Status Markers

```python
def ok(msg):   print(f"  ✅  {msg}")
def warn(msg): print(f"  ⚠️   {msg}")
def err(msg):  print(f"  ❌  {msg}", file=sys.stderr)
def info(msg): print(f"  ℹ️   {msg}")
```

### Table Formatting (pure stdlib)

Declare column widths as variables. Truncate every cell before printing —
never let long values break alignment.

```python
W_NAME   = 24
W_EMAIL  = 32
W_STATUS = 10

def cell(val, width: int) -> str:
    s = str(val) if val is not None else ""
    return (s[:width - 1] + "…") if len(s) > width else s.ljust(width)

# Header
print(f"  {'Name'.ljust(W_NAME)}  {'Email'.ljust(W_EMAIL)}  {'Status'}")
print(f"  {'─' * W_NAME}  {'─' * W_EMAIL}  {'─' * W_STATUS}")

# Rows
for row in rows:
    print(f"  {cell(row['name'], W_NAME)}  {cell(row['email'], W_EMAIL)}  {cell(row['status'], W_STATUS)}")
```

---

## Full Starter Template

```python
#!/usr/bin/env python3
"""
tool-name — one-line description of what this script does.
Usage: python3 tool-name.py [--limit N] [--dry-run]
"""
import argparse
import sqlite3
import sys
from pathlib import Path


# ── Output helpers ────────────────────────────────────────────────────────────

def die(msg: str) -> None:
    """Print error and exit non-zero."""
    print(f"  ❌  {msg}", file=sys.stderr)
    sys.exit(1)


def section(title: str) -> None:
    print(f"\n  \033[1m{title}\033[0m")
    print(f"  {'─' * len(title)}")


def cell(val, width: int) -> str:
    """Truncate and left-pad a table cell."""
    s = str(val) if val is not None else ""
    return (s[:width - 1] + "…") if len(s) > width else s.ljust(width)


# ── Core logic ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--limit",   type=int, default=10, help="Max rows to show (default: 10)")
    parser.add_argument("--dry-run", action="store_true",  help="Show what would happen without writing")
    args = parser.parse_args()

    # ── Locate data ───────────────────────────────────────────────────────────
    db_path = Path.home() / "path" / "to" / "data.db"
    if not db_path.exists():
        die(f"Database not found: {db_path}")

    print(f"\n📂  Source: {db_path}")

    if args.dry_run:
        print(f"  ⚠️   DRY RUN — no writes will occur")

    # ── Query ─────────────────────────────────────────────────────────────────
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # access columns by name, not index
    try:
        rows = conn.execute(
            "SELECT col1, col2, col3 FROM table_name ORDER BY col1 DESC LIMIT ?",
            (args.limit,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        print("  ⚠️   No results found.\n")
        return

    # ── Output ────────────────────────────────────────────────────────────────
    section(f"Results ({len(rows)} rows)")

    W1, W2, W3 = 20, 30, 12
    print(f"\n  {'Col1'.ljust(W1)}  {'Col2'.ljust(W2)}  {'Col3'.ljust(W3)}")
    print(f"  {'─' * W1}  {'─' * W2}  {'─' * W3}")

    for row in rows:
        print(f"  {cell(row['col1'], W1)}  {cell(row['col2'], W2)}  {cell(row['col3'], W3)}")

    print(f"\n  ✅  {len(rows)} rows\n")


if __name__ == "__main__":
    main()
```

---

## SQLite Patterns

### Connect with named-column access

Always set `row_factory`. Access columns by name — indexes break silently
when queries change.

```python
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
```

### Parameterized queries

Always use `?` placeholders — never f-string values into SQL:

```python
# ✅ correct
rows = conn.execute("SELECT * FROM t WHERE id = ?", (user_id,)).fetchall()

# ❌ wrong — SQL injection risk
rows = conn.execute(f"SELECT * FROM t WHERE id = {user_id}").fetchall()
```

### List tables

```python
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()]
print(f"🗄️   Tables: {', '.join(tables)}")
```

### Date formatting from Unix timestamps

Apple and many apps store dates as seconds since 2001-01-01 (CoreData epoch)
or 1970-01-01 (Unix). Convert explicitly:

```python
from datetime import datetime, timezone

# Unix epoch (1970)
dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

# CoreData / Apple epoch (2001) — add 978307200 seconds offset
dt = datetime.fromtimestamp(ts + 978307200, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
```

---

## Argument Patterns

### Standard flags every helper should support

```python
parser.add_argument("--limit",   type=int, default=10)   # rows / results cap
parser.add_argument("--dry-run", action="store_true")     # skip writes
parser.add_argument("--json",    action="store_true")     # machine-readable output
```

### JSON output mode

When `--json` is passed, skip all pretty-printing and emit raw JSON for piping:

```python
if args.json:
    import json
    print(json.dumps([dict(r) for r in rows], default=str))
    return
```

---

## Rules

- `#!/usr/bin/env python3` — always
- `from pathlib import Path` — all file paths, never `os.path.join()`
- `conn.row_factory = sqlite3.Row` — named columns, always
- `die()` for all fatal errors — consistent exit messaging
- Two-space indent on every output line
- `cell()` helper — truncate before print, never after
- Docstring at module level — appears in `--help`
- stdlib only — no `pip install` for simple read scripts

## What NOT to Do

- No raw ANSI codes scattered in `print()` calls — define color constants at top or use emoji-only style
- No hardcoded absolute paths — `Path.home() / "..."` or `argparse` input
- No `except: pass` — catch specifically, print clearly, `sys.exit(1)`
- No `os.path` — use `pathlib` exclusively
- No f-strings with SQL values — always `?` placeholders

---

## python3 as a JSON-parse sidecar for bash

When a bash tool must parse API JSON without `jq`, pipe the response to a
one-line `python3 -c` that reads `sys.stdin`, walks the structure, and prints
tab- or CSV-ready rows — one row per object, ready for `while IFS=$'\t' read`
in the calling script.

**stdlib only** — `json` module, nothing else required.

### Concrete example

Suppose an API returns a list of objects, each with `id`, `name`, and `status`
fields. Extract those three fields, one tab-separated row per object:

```bash
curl -s "$API_URL/items" | python3 -c "
import json, sys
for item in json.load(sys.stdin):
    print(item['id'], item.get('name', ''), item.get('status', ''), sep='\t')
"
```

Consume in bash:

```bash
while IFS=$'\t' read -r id name status; do
    echo "  $id  $name  [$status]"
done < <(curl -s "$API_URL/items" | python3 -c "
import json, sys
for item in json.load(sys.stdin):
    print(item['id'], item.get('name', ''), item.get('status', ''), sep='\t')
")
```

For nested values, chain attribute access normally:

```bash
python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data['results']:
    owner = item.get('owner', {}).get('email', '')
    print(item['id'], item['label'], owner, sep='\t')
"
```

### Single-quote caveat

The `-c` literal sits inside bash single-quotes — **never interpolate shell
variables directly into it**. Shell expansion does not happen inside `'...'`,
so this is a non-issue for the Python code itself; but if you need to pass a
runtime value from bash into the Python one-liner, use `sys.argv` or an
environment variable instead of string-building the `-c` argument:

```bash
# ✅ safe — value passed via argv, not spliced into the Python source
python3 -c "
import json, sys
target = sys.argv[1]
for item in json.load(sys.stdin):
    if item.get('type') == target:
        print(item['id'], item['name'], sep='\t')
" "$FILTER_TYPE"

# ❌ unsafe — injecting an untrusted shell value into the -c literal
python3 -c "
for item in ...:
    if item['type'] == '$FILTER_TYPE':   # shell expands here — injection risk
        ...
"
```

The safe pattern works for any scalar: pass it as a positional arg (`sys.argv[N]`)
or export it as an env var and read with `os.environ['VAR']`.
