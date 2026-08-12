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
    │   ├── export-records.sh
    │   ├── export-reports.sh
    │   ├── export-snapshots.sh
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
  show_usage "Export records to CSV" \
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

For the interrupt-safe variant (temp-file + atomic `mv`, Ctrl-C never leaves a half-written CSV), see `data-cli.md` → *Paginated fetch → CSV (Ctrl+C-safe)*.

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

---

## Multi-file toolbox layout

As a toolbox grows past five or six tools, a flat `scripts/` directory becomes unwieldy. The pattern that emerges is a deliberate split into concentric layers:

```
project-root/
├── launcher.sh                     # Entry point — menu + dispatch
├── _lib.sh                         # Core: palette, auth, flag parsing, export engine
├── _helpers.sh                     # UI layer: animations, transitions, interactive menus
├── _<domain>-helpers.sh            # Feature-scoped lib: one per major service boundary
├── tools/                          # One file per user-facing verb
│   ├── export-records.sh
│   ├── export-snapshots.sh
│   ├── push-assets.sh
│   ├── run-diagnostics.sh
│   ├── probe-data.sh
│   └── ...
├── _data/                          # Static catalogs: column definitions, enum maps
│   ├── record-columns.sh
│   └── asset-catalog.sh
├── one-shots/                      # Ceremonial / infrequent scripts (setup, migrations)
│   └── README.md
└── .logs/                          # Runtime artefacts (gitignored)
    ├── <tool>.lock                 # PID lock while a writer runs
    ├── <tool>-manifest.txt         # Tracks processed paths across runs
    └── <tool>-YYYY-MM-DD.log       # Append-only run log
```

Layer responsibilities:

| Layer | File(s) | What lives here |
|---|---|---|
| Core | `_lib.sh` | Palette tokens, semantic roles, auth, flag parsing, shared utilities, export engine |
| UI | `_helpers.sh` | Terminal control, animations, transitions, interactive menus — sources `_lib.sh` |
| Feature libs | `_<domain>-helpers.sh` | API wrappers, domain-specific paginators, heavy logic that would bloat core |
| Tools | `tools/<verb>.sh` | One user-facing action each; sources core or UI layer as needed |
| Data | `_data/*.sh` | Sourced-in column definitions, static enum lists — no logic |
| One-shots | `one-shots/*.sh` | Setup, migrations, ceremonies; not registered in the launcher |
| Runtime | `.logs/` | Lock files, manifests, append logs — local-only, gitignored |

Naming conventions:
- Files prefixed with `_` are libraries, not standalone scripts.
- `_data/` files are sourced, never executed.
- `one-shots/` scripts run ad-hoc; they should self-document and be idempotent where possible.
- `.logs/` entries are machine-local artefacts; the pattern (not the contents) is committed.

*seen in the wild: a single `_toolbox/` directory holding `_lib.sh`, `_helpers.sh`, `_export-helpers.sh`, `_crm-helpers.sh`, `_sync-helpers.sh`, `_watch-helpers.sh`, `_logging.sh`, forty-plus tools, and a `one-shots/` subdirectory — a well-structured real-world toolbox.*

---

## Entry-point launcher

A single `launcher.sh` at the project root renders a wheelhouse menu and dispatches to `tools/<verb>.sh`. It accepts global flags (`--dry`, `--quiet`) before the sub-command name, forwards them into every tool invocation, and stays thin — no business logic lives here.

```bash
#!/usr/bin/env bash
# launcher.sh — Toolbox entry point.
# Usage: bash launcher.sh [--dry] [--quiet] [<tool>] [tool-flags...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_helpers.sh"

parse_flags "$@"
# After parse_flags, $PASSTHROUGH holds the tool name + any tool-specific flags.

# ── Global flag forwarding ────────────────────────────────────────────────
GLOBAL_FLAGS=()
$DRY_RUN && GLOBAL_FLAGS+=(--dry)
$QUIET   && GLOBAL_FLAGS+=(--quiet)

# ── Direct dispatch (non-interactive / automation) ────────────────────────
# If a tool name was passed as the first non-flag arg, skip the menu.
TOOL_NAME="${PASSTHROUGH[0]:-}"
if [[ -n "$TOOL_NAME" ]]; then
  tool_path="${SCRIPT_DIR}/tools/${TOOL_NAME}.sh"
  if [[ -f "$tool_path" ]]; then
    bash "$tool_path" "${GLOBAL_FLAGS[@]}" "${PASSTHROUGH[@]:1}"
    exit $?
  else
    printf "  ${COLOR_ERROR}✗ Unknown tool: %s${RESET}\n" "$TOOL_NAME"
    exit 1
  fi
fi

# ── Interactive wheelhouse menu ───────────────────────────────────────────
# LABELS, HINTS, SCRIPTS parallel arrays — add entries when registering a
# new tool (see "Adding a new tool" below).
LABELS=(
  "Export records"
  "Export snapshots"
  "Push assets"
  "Run diagnostics"
  "Quit"
)
HINTS=(
  "Pull all records to CSV"
  "Archive a point-in-time snapshot"
  "Upload staged assets to the service"
  "Check connectivity and auth"
  ""
)
SCRIPTS=(
  "tools/export-records.sh"
  "tools/export-snapshots.sh"
  "tools/push-assets.sh"
  "tools/run-diagnostics.sh"
  ""
)

selected=0
while true; do
  cls; hide_cur
  draw_menu $selected "${LABELS[@]}"

  read -rsn1 key
  case "$key" in
    $'\x1b')
      read -rsn2 -t 0.1 seq || true
      case "$seq" in
        '[A') ((selected > 0)) && ((selected--)) ;;
        '[B') ((selected < ${#LABELS[@]} - 1)) && ((selected++)) ;;
      esac ;;
    '')
      script="${SCRIPTS[$selected]:-}"
      [[ -z "$script" ]] && { show_cur; printf "\n  Goodbye.\n\n"; exit 0; }
      show_cur
      bash "${SCRIPT_DIR}/${script}" "${GLOBAL_FLAGS[@]}"
      printf "\n  ${DIM}Press any key to return to menu...${RESET}"
      read -rsn1; echo "" ;;
  esac
done
```

Adding a new tool:

1. Drop `tools/<name>.sh` following the tool skeleton below.
2. Append an entry to the `LABELS`, `HINTS`, and `SCRIPTS` arrays in `launcher.sh`.
3. Tools remain directly invokable without the launcher — important for cron jobs and automation pipelines.

---

## The tool skeleton

Every `tools/<verb>.sh` shares the same shape. The skeleton is what makes adding a new tool mechanical: copy, rename, fill in the work block.

```bash
#!/usr/bin/env bash
# tools/export-records.sh — Export all records to CSV.
# Usage: bash tools/export-records.sh [--dry] [--quiet] [--force]

set -euo pipefail

# ── Bootstrap ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/.."

# Non-interactive tools: source _lib.sh.
# Interactive tools that need menus/animations: source _helpers.sh instead.
source "${LIB_DIR}/_lib.sh"

# ── Cleanup ───────────────────────────────────────────────────────────────
cleanup() { release_lock; }
trap cleanup EXIT INT TERM

# ── Flags ────────────────────────────────────────────────────────────────
FORCE=false
parse_flags "$@"

for arg in "${PASSTHROUGH[@]:-}"; do
  case "$arg" in
    --force) FORCE=true ;;
    *)       unknown_flag "$arg" "Export records to CSV" "--force    Re-export all, ignore cache" ;;
  esac
done

if $SHOW_HELP; then
  show_usage "Export records to CSV" \
    "--force    Re-export all, ignore cache"
  exit 0
fi

# ── Banner ────────────────────────────────────────────────────────────────
$QUIET || splash_fancy "Export Records"
$DRY_RUN && printf "  ${COLOR_WARN}${BOLD}DRY RUN${RESET}${DIM} — no files will be written${RESET}\n"

# ── Auth ──────────────────────────────────────────────────────────────────
# Omit this block for tools that don't call a remote service.
auth_api

# ── Lock ──────────────────────────────────────────────────────────────────
# Omit this block for read-only or interactive-only tools.
acquire_lock "export-records"    # fails loud if another instance is running

# ── Work ──────────────────────────────────────────────────────────────────
output_file="${EXPORTS_DIR}/records-$(date +%Y-%m-%d).csv"
export_csv "records" "$output_file" "$RECORD_PROPERTIES" "$RECORD_COLUMNS"

# ── Done ──────────────────────────────────────────────────────────────────
printf "  ${COLOR_SUCCESS}✓${RESET} Done.\n\n"
```

The skeleton has six fixed sections in order: bootstrap, cleanup trap, flag parsing (global + tool-specific), banner, auth (if the tool touches a service), lock acquisition (if the tool writes), work, done. Teams that follow this shape can onboard a new tool by rote: copy skeleton, rename, fill in work block, register in launcher.

*A scaffolder that generates new tools from this skeleton is an obvious next step but is not yet a solved/working tool — this section codifies the skeleton tools already share, not a generator.*

---

## Repo hygiene hooks

Tracked hooks in `git-hooks/` + an install script let the repo enforce local lint and smoke rules before any push reaches the remote. The hooks live in the working tree (tracked, reviewed, versioned); an install script copies or symlinks them into the local `.git/hooks/` directory on each machine.

### Directory layout

```
git-hooks/
└── pre-push            # Blocked on: lint failures, smoke test failures

tools/
└── install-git-hooks.sh   # Per-machine onboarding step (idempotent)
```

### `git-hooks/pre-push` pattern

```bash
#!/usr/bin/env bash
# pre-push — run lint and smoke checks before any push.
#
# git invokes pre-push with:
#   $1 = remote name
#   $2 = remote URL
#   stdin: "<local_ref> <local_sha> <remote_ref> <remote_sha>" per line
#
# Bypass (document why in the commit body):
#   git push --no-verify
#
# Source of truth: git-hooks/pre-push (tracked).
# Installed via:   bash tools/install-git-hooks.sh

set -u

ZERO="0000000000000000000000000000000000000000"

# Read refs from stdin
i=0
while IFS=' ' read -r lref lsha rref rsha; do
  [ -z "${lref:-}" ] && continue
  eval "local_sha_$i=\"\$lsha\""
  eval "local_ref_$i=\"\$lref\""
  eval "remote_sha_$i=\"\$rsha\""
  i=$((i + 1))
done
total=$i
[ "$total" -eq 0 ] && exit 0

# Per-ref checks
n=0; errors=0
while [ "$n" -lt "$total" ]; do
  eval "lsha=\$local_sha_$n"
  eval "lref=\$local_ref_$n"

  # Skip deletions
  [ "$lsha" = "$ZERO" ] && { n=$((n+1)); continue; }

  # ── Your checks here ────────────────────────────────────────────────────
  # e.g. shellcheck, bats smoke test, YAML lint, secret scan
  # Exit 1 with a clear message if a check fails.
  # ────────────────────────────────────────────────────────────────────────

  n=$((n + 1))
done

[ "$errors" -gt 0 ] && exit 1
exit 0
```

Useful checks to wire in: `shellcheck` on all `*.sh` files, a single fast smoke-test invocation (e.g., `bash tools/run-diagnostics.sh --dry --quiet`), a secret-pattern scan, or a YAML/JSON schema validation. Keep the hook fast — anything over ~5 seconds will be skipped with `--no-verify` in practice.

### `tools/install-git-hooks.sh` pattern

```bash
#!/usr/bin/env bash
# install-git-hooks.sh — install tracked hooks into the local git store.
# Idempotent. Run once per clone, and again after adding new hooks.
#
# Usage:
#   bash tools/install-git-hooks.sh           # skip identical files
#   bash tools/install-git-hooks.sh --force   # overwrite hand-modified hooks

set -euo pipefail

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_SRC="$(cd "$TOOL_DIR/../git-hooks" && pwd)"
GIT_HOOKS_DIR="$(git rev-parse --git-path hooks)"
[ -d "$GIT_HOOKS_DIR" ] || mkdir -p "$GIT_HOOKS_DIR"

[ -d "$HOOKS_SRC" ] || { echo "✗ git-hooks/ directory not found at $HOOKS_SRC" >&2; exit 1; }

installed=0; skipped=0; errors=0

for src in "$HOOKS_SRC"/*; do
  [ -e "$src" ] || continue
  name="$(basename "$src")"
  case "$name" in *.sample|*.md|README*) continue;; esac

  dest="$GIT_HOOKS_DIR/$name"

  if [ -e "$dest" ] && [ "$FORCE" -eq 0 ]; then
    if cmp -s "$src" "$dest" 2>/dev/null; then
      echo "= $name (up to date)"; skipped=$((skipped+1)); continue
    fi
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
      echo "= $name (symlinked)"; skipped=$((skipped+1)); continue
    fi
    echo "! $name — local version differs; re-run with --force to overwrite" >&2
    errors=$((errors+1)); continue
  fi

  rm -f "$dest"
  if ln -s "$src" "$dest" 2>/dev/null; then
    echo "+ $name (symlinked)"
  else
    cp "$src" "$dest"; chmod +x "$dest"
    echo "+ $name (copied)"
  fi
  installed=$((installed+1))
done

echo
echo "Hooks dir: $GIT_HOOKS_DIR"
echo "Installed: $installed  · Skipped: $skipped  · Errors: $errors"
[ "$errors" -gt 0 ] && exit 1
exit 0
```

The install script prefers symlinking (so the tracked source stays in sync automatically on subsequent updates) and falls back to a plain copy when symlinks aren't supported. It is idempotent: re-running it after a hook update installs the new version without touching unrelated hooks.
