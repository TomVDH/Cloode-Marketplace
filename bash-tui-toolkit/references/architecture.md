# Architecture Reference

Project structure, shared library patterns, flag parsing, auth, error handling,
and the paginated export engine.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Shared Library (_lib.sh)](#shared-library)
3. [UI Helpers (_helpers.sh)](#ui-helpers)
4. [Flag Parsing](#flag-parsing)
5. [Usage / Help](#usage--help)
6. [Auth Pattern](#auth-pattern)
7. [Error Handling](#error-handling)
8. [Paginated CSV Export Engine](#paginated-csv-export-engine)
9. [Dry Run Convention](#dry-run-convention)
10. [Script Lifecycle](#script-lifecycle)

---

## Project Structure

```
project-root/
├── launcher.sh                    # Master entry point
├── config.yml                     # Tool configuration (gitignored secrets)
├── .gitignore
└── scripts/
    ├── _lib.sh                    # Core shared library
    ├── _helpers.sh                # Interactive UI helpers (sources _lib.sh)
    ├── .token-file                # API token (gitignored)
    ├── README.md                  # Script documentation
    ├── UI-SPEC.md                 # Terminal UI decisions and rules
    ├── tools/                     # Individual tool scripts
    │   ├── export-contacts.sh
    │   ├── export-companies.sh
    │   ├── export-deals.sh
    │   └── api-test.sh
    ├── data/                      # Static data (column definitions, etc.)
    │   ├── contact-columns.sh
    │   └── company-columns.sh
    └── demos/                     # Visual demos and pickers
        ├── picker-spinners.sh
        ├── picker-loadingbars.sh
        └── stashed/               # Archived experiments (not current)
```

Key conventions:
- `_lib.sh` is the core — palette, auth, flags, utilities
- `_helpers.sh` layers on interactive UI (sources `_lib.sh`)
- Files prefixed with `_` are libraries, not standalone scripts
- `stashed/` directories contain archived experiments, not references
- Token files and config with secrets are `.gitignore`d

---

## Shared Library

The `_lib.sh` pattern. Every script in the project sources this file:

```bash
#!/usr/bin/env bash
# _lib.sh — Shared library for [Project Name]

# Source guard — don't load twice
[[ -n "${_LIB_LOADED:-}" ]] && return 0
_LIB_LOADED=1

# ── Palette ──────────────────────────────────────────────────────────────
# (raw tokens, then semantic roles — see palette.md)

# ── Project paths ────────────────────────────────────────────────────────
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$LIB_DIR")"
EXPORTS_DIR="${PROJECT_DIR}/exports"
TOKEN_FILE="${LIB_DIR}/.token-file"
CONFIG_FILE="${PROJECT_DIR}/config.yml"

# ── Shared state ─────────────────────────────────────────────────────────
DRY_RUN=false
AUTH_TOKEN=""
CLI_OK=false
DEBUG=false
QUIET=false
SHOW_HELP=false
PASSTHROUGH=()

# ── Functions ────────────────────────────────────────────────────────────
# (flag parsing, auth, splash, spinners, export engine, etc.)
```

Paths are resolved relative to `${BASH_SOURCE[0]}` so scripts work regardless
of the caller's working directory.

---

## UI Helpers

The `_helpers.sh` adds interactive-only concerns on top of `_lib.sh`:

```bash
#!/usr/bin/env bash
# _helpers.sh — UI helpers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_lib.sh"

# Terminal control
cls()      { printf "\033[2J\033[H"; }
hide_cur() { printf "\033[?25l"; }
show_cur() { printf "\033[?25h"; }

# Text helpers
trunc() { ... }
hr() { ... }

# Animation helpers
block_run() { ... }
animate_comet_tail() { ... }

# Transitions
transition_pixel_scatter() { ... }
```

Non-interactive tools (exports, diagnostics) source only `_lib.sh`.
Interactive tools (menus, demos) source `_helpers.sh` (which pulls in `_lib.sh`
transitively).

---

## Flag Parsing

Centralized in `_lib.sh`. Common flags are consumed; everything else lands in
a passthrough array for script-specific handling:

```bash
parse_flags() {
  PASSTHROUGH=()
  for arg in "$@"; do
    case "$arg" in
      --dry|--dry-run) DRY_RUN=true ;;
      --debug)         DEBUG=true ;;
      --quiet)         QUIET=true ;;
      --help)          SHOW_HELP=true ;;
      *)               PASSTHROUGH+=("$arg") ;;
    esac
  done
}
```

Scripts call it early:

```bash
source _lib.sh
parse_flags "$@"

if $SHOW_HELP; then
  show_usage "Export contacts to CSV" \
    "--force    Re-export all, ignore cache"
  exit 0
fi
```

---

## Usage / Help

Standardized help output:

```bash
show_usage() {
  local description="$1"
  shift
  echo ""
  printf "  ${BOLD}TOOLNAME${RESET} — %s\n" "$description"
  echo ""
  printf "  Usage:  bash %s [flags]\n" "${BASH_SOURCE[1]:-$0}"
  echo ""
  printf "  ${BOLD}Flags:${RESET}\n"
  printf "    --dry           Run without writing (still pulls data)\n"
  printf "    --debug         Print raw API responses\n"
  printf "    --quiet         Suppress banner and progress output\n"
  printf "    --help          Show this help\n"
  # Script-specific flags
  for line in "$@"; do
    printf "    %s\n" "$line"
  done
  echo ""
}

# Unknown flag error
unknown_flag() {
  local flag="$1"; shift
  printf "\n  ${RED}Error: unknown flag '%s'${RESET}\n" "$flag"
  show_usage "$@"
  exit 1
}
```

---

## Auth Pattern

CLI-first with token-file fallback. Supports multiple auth sources:

```bash
auth_api() {
  AUTH_TOKEN=""
  CLI_OK=false

  # 1. Try CLI tool config
  if command -v toolcli &>/dev/null; then
    local accounts
    accounts=$(toolcli account list 2>&1) || true
    if echo "$accounts" | grep -q "myaccount"; then
      CLI_OK=true
      # Extract token from config file (YAML, JSON, etc.)
      if [[ -f "$CONFIG_FILE" ]]; then
        AUTH_TOKEN=$(extract_token_from_config "$CONFIG_FILE")
      fi
    fi
  fi

  # 2. Fallback to token file
  if [[ -z "$AUTH_TOKEN" ]]; then
    if [[ -f "$TOKEN_FILE" ]] && [[ -s "$TOKEN_FILE" ]]; then
      AUTH_TOKEN=$(tr -d '[:space:]' < "$TOKEN_FILE")
      $QUIET || printf "  ${COLOR_INFO}ℹ  Using token from .token-file${RESET}\n"
    fi
  fi

  # 3. No token — bail
  if [[ -z "$AUTH_TOKEN" ]]; then
    printf "  ${COLOR_ERROR}✗ No API token found.${RESET}\n"
    printf "  ${DIM}Place your token in %s${RESET}\n" "$TOKEN_FILE"
    exit 1
  fi
}
```

---

## Error Handling

Global error trap + per-script cleanup:

```bash
# In _lib.sh
on_error() {
  echo ""
  printf "  ${COLOR_ERROR}✗ An error occurred.${RESET}\n"
  echo "  Press any key to close..."
  read -rsn1
  exit 1
}

# In each script
set -euo pipefail
source _lib.sh
trap 'on_error' ERR

# Interactive scripts add cleanup for cursor/formatting
cleanup() { show_cur; printf "${RESET}\n"; }
trap cleanup EXIT INT TERM
```

`Ctrl+C` during paginated exports keeps the partial file — the user still
gets whatever was fetched before the interrupt.

---

## Paginated CSV Export Engine

Generic engine for API pagination with live progress:

```bash
export_csv() {
  local object_type="$1"
  local output_file="$2"
  local properties="$3"  # Comma-separated API properties
  local columns="$4"     # Header line for CSV
  local page_size=100

  mkdir -p "$(dirname "$output_file")"

  # Dry run — just count
  if $DRY_RUN; then
    local count_response=$(curl -s \
      -H "Authorization: Bearer ${AUTH_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{"filterGroups":[],"limit":1}' \
      "https://api.example.com/objects/${object_type}/search")
    local total=$(echo "$count_response" | python3 -c \
      "import json,sys;print(json.load(sys.stdin).get('total',0))")
    printf "  ${COLOR_SUCCESS}✓${RESET} Would export ${BOLD}%s${RESET} %s records\n" "$total" "$object_type"
    return 0
  fi

  # Write header
  echo "$columns" > "$output_file"

  # Paginate
  local after=""
  local page=0
  local total_fetched=0

  while true; do
    local url="https://api.example.com/objects/${object_type}?limit=${page_size}&properties=${properties}"
    [[ -n "$after" ]] && url="${url}&after=${after}"

    local response=$(curl -s \
      -H "Authorization: Bearer ${AUTH_TOKEN}" \
      "$url")

    # Parse with python3
    local batch=$(echo "$response" | python3 -c "
import json, sys, csv, io
data = json.load(sys.stdin)
results = data.get('results', [])
writer = csv.writer(io.StringIO())
for r in results:
    p = r.get('properties', {})
    # ... extract fields ...
    pass
print(writer.getvalue())
" 2>/dev/null)

    echo "$batch" >> "$output_file"

    local count=$(echo "$response" | python3 -c \
      "import json,sys;print(len(json.load(sys.stdin).get('results',[])))")
    total_fetched=$((total_fetched + count))

    # Progress
    printf "\r  ${COLOR_SUCCESS}✓${RESET} Fetched ${BOLD}%s${RESET} %s" \
      "$total_fetched" "$object_type"

    # Next page
    after=$(echo "$response" | python3 -c \
      "import json,sys;d=json.load(sys.stdin);p=d.get('paging',{}).get('next',{});print(p.get('after',''))" 2>/dev/null)

    if [[ -z "$after" ]] || [[ "$count" -lt "$page_size" ]]; then
      break
    fi
    ((page++))
  done

  printf "\r\033[2K  ${COLOR_SUCCESS}✓${RESET} Exported ${BOLD}%s${RESET} %s → ${DIM}%s${RESET}\n" \
    "$total_fetched" "$object_type" "$output_file"
}
```

---

## Dry Run Convention

Every data-writing script follows this contract:

| In dry run | Behavior |
|-----------|----------|
| Auth | Runs fully (validates token) |
| API reads | Executes (fetches counts) |
| File writes | Skipped |
| Uploads | Skipped |
| Watch/monitor | Not started |
| Summary | Shows what *would* happen |

The banner shows a prominent DRY RUN indicator:

```bash
if $DRY_RUN; then
  printf "  ${COLOR_WARN}${BOLD}DRY RUN${RESET}${DIM} — no data will be written${RESET}\n"
fi
```

---

## Script Lifecycle

The canonical flow for an interactive CLI tool:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Source libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_helpers.sh"

# Cleanup trap
cleanup() { show_cur; printf "${RESET}\n"; }
trap cleanup EXIT INT TERM

# Parse flags
parse_flags "$@"
$SHOW_HELP && { show_usage "My Tool"; exit 0; }

# Boot sequence (optional)
# bash "${SCRIPT_DIR}/bootloader.sh"

# Splash
splash_fancy "My Tool"

# Auth
auth_api

# Diagnostics (optional)
# ... check API access, show record counts ...

# Keypress gate
printf "  ${DIM}Press any key to continue...${RESET}"
read -rsn1; echo ""

# Main menu loop
selected=0
while true; do
  cls; hide_cur
  draw_menu $selected
  # ... arrow key handling, dispatch ...
done

printf "\n  ${DIM}Goodbye.${RESET}\n\n"
```

For non-interactive tools (exports, single-action scripts), skip the menu
loop and go straight to the action after auth.
