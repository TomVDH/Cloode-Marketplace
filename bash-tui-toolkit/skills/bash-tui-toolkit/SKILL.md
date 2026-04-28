---
name: bash-tui-toolkit
description: >
  Build polished, interactive bash CLI tools with rich terminal UI — menus,
  tables, loading bars, spinners, splash screens, transitions, and animated
  effects. Use this skill whenever a user asks to create a bash script,
  shell tool, terminal utility, CLI launcher, or any interactive command-line
  application. Also use when the user mentions "terminal UI", "TUI", "CLI
  menu", "progress bar", "spinner", "splash screen", or wants to add visual
  polish to shell scripts. If someone says "make it look nice in the terminal"
  or wants a retro/hacker/polished CLI aesthetic, this is the skill to reach for.
---

# Bash TUI Toolkit

A pattern library for building professional, interactive bash CLI tools that
feel crafted — not cobbled together. Every script you generate with this
toolkit should look like it came from the same hand: consistent colors,
consistent spacing, consistent motion.

## How to use this skill

1. Read this SKILL.md first — it contains the mandatory checklist and all
   the patterns you need for most scripts.
2. Read `${CLAUDE_PLUGIN_ROOT}/references/components.md` — it has the
   **complete, copy-paste ready** implementations of every UI component.
   Do not improvise your own versions; use the reference implementations.
3. Read `${CLAUDE_PLUGIN_ROOT}/references/palette.md` if you need the full
   extended color palette.
4. Read `${CLAUDE_PLUGIN_ROOT}/references/architecture.md` if scaffolding a
   multi-file project.

---

## Mandatory Checklist

Every script you generate must include these elements. This is what separates
a toolkit script from a generic bash script.

### 1. Strict mode and cleanup (every script, no exceptions)

```bash
#!/usr/bin/env bash
set -euo pipefail

cleanup() { show_cur; printf "${RESET}\n"; }
trap cleanup EXIT INT TERM
```

The trap restores the cursor and resets ANSI state, even on Ctrl+C or errors.
Without this, a crashed script leaves the user with an invisible cursor.

### 2. Color palette with semantic tokens (every script)

Define raw ANSI codes in a palette block, then create semantic aliases.
All output statements use the semantic names — never raw codes.

```bash
# ── Palette ──────────────────────────────────────────────
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'
TEAL='\033[38;5;43m'
SLATE='\033[38;5;244m'

# ── Semantic roles ───────────────────────────────────────
COLOR_TITLE="${CYAN}"
COLOR_SUCCESS="${GREEN}"
COLOR_WARN="${YELLOW}"
COLOR_ERROR="${RED}"
COLOR_MUTED="${DIM}"
COLOR_ACTIVE="${CYAN}"
COLOR_INFO="${DIM}"
```

Why semantic tokens matter: if the user later wants to change the success
color from green to teal, they change one line instead of hunting through
every printf in the script.

### 3. Terminal control functions (every interactive script)

```bash
cls()      { printf "\033[2J\033[H"; }
hide_cur() { printf "\033[?25l"; }
show_cur() { printf "\033[?25h"; }
```

### 4. The trunc() helper (every script that outputs tables or variable-length data)

ANSI escape codes are invisible bytes that break `printf` width calculations.
The only safe approach: truncate the raw text first, then wrap it in color.

```bash
trunc() {
  local str="$1" max="$2"
  if (( ${#str} > max )); then
    printf "%s" "${str:0:$((max-1))}…"
  else
    printf "%-${max}s" "$str"
  fi
}
```

### 5. Two-space indent on all output

Every line the user sees starts with at least two spaces. This creates a
visual margin and room for status markers:

```
  ✓ Contacts         1,234 records
  ✗ Tickets          403 — scope not granted
  ⚠ hs CLI           Not installed
```

### 6. Status markers (every script that reports results)

```bash
printf "  ${COLOR_SUCCESS}✓${RESET} %s\n" "Success"
printf "  ${COLOR_ERROR}✗${RESET} %s\n" "Failure"
printf "  ${COLOR_WARN}⚠${RESET} %s\n" "Warning"
printf "  ${COLOR_INFO}ℹ${RESET}  %s\n" "Info"
```

### 7. Section headers

When a script has distinct phases or sections, use the bar-bracket pattern:

```bash
section() {
  echo ""
  printf "  ${COLOR_TITLE}${BOLD}━━ %s ━━${RESET}\n\n" "$1"
}
```

---

## Core Patterns

### Menus: Always use chevrons and arrow keys

Never generate numbered menus (`1) Option A  2) Option B`). Always use the
chevron focus pattern with arrow key navigation. This is the single biggest
visual differentiator of the toolkit.

**Single select** — `››` for focused, `›` for unfocused:

```bash
draw_menu() {
  local sel="$1"
  local opts=("Contacts" "Companies" "Deals" "Exit")
  for i in "${!opts[@]}"; do
    if [[ $i -eq $sel ]]; then
      printf "  ${TEAL}›› ${BOLD}%s${RESET}\n" "${opts[$i]}"
    else
      printf "  ${COLOR_MUTED}›  %s${RESET}\n" "${opts[$i]}"
    fi
  done
}
```

**The navigation loop** (use this exact pattern):

```bash
selected=0
max=$(( ${#opts[@]} - 1 ))

while true; do
  cls; hide_cur
  echo ""
  printf "  ${COLOR_TITLE}${BOLD}━━ Tool Name ━━${RESET}\n"
  printf "  ${COLOR_MUTED}Select an option${RESET}\n\n"
  draw_menu $selected
  echo ""
  printf "  ${COLOR_MUTED}↑/↓ navigate  •  Enter select  •  q quit${RESET}"

  read -rsn1 key
  case "$key" in
    '') show_cur; dispatch $selected; hide_cur ;;
    q|Q) break ;;
    $'\033')
      seq1="" seq2=""
      read -rsn1 -t 1 seq1 || true
      read -rsn1 -t 1 seq2 || true
      if [[ "${seq1:-}" == "[" ]]; then
        case "${seq2:-}" in
          A) ((selected > 0)) && selected=$((selected - 1)) ;;
          B) ((selected < max)) && selected=$((selected + 1)) ;;
        esac
      fi ;;
  esac
done
printf "\n  ${COLOR_MUTED}Goodbye.${RESET}\n\n"
```

Also available: **boolean toggle** (`›› ●` / `› ○`) and **multi select**
(`›› [x]` / `› [ ]`). See `${CLAUDE_PLUGIN_ROOT}/references/components.md` for those.

### Tables: Fixed-width columns with dim pipe separators

Declare column widths as variables. Truncate every cell. Use dim `│` pipes:

```bash
W_NAME=16; W_EMAIL=26; W_STATUS=10

# Header
printf "  ${BOLD}%-${W_NAME}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_EMAIL}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_STATUS}s${RESET}\n" \
  "Name" "Email" "Status"

# Separator (use the hr() helper from ${CLAUDE_PLUGIN_ROOT}/references/components.md)
hr "${DIM}" "─" "┼" $W_NAME $W_EMAIL $W_STATUS

# Data row
name_cell=$(trunc "$name" "$W_NAME")
email_cell=$(trunc "$email" "$W_EMAIL")
printf "  %-${W_NAME}s ${DIM}│${RESET} ${SLATE}%-${W_EMAIL}s${RESET} ${DIM}│${RESET} ${COLOR_SUCCESS}%-${W_STATUS}s${RESET}\n" \
  "$name_cell" "$email_cell" "$status"
```

### Splash Banners

Every tool benefits from a splash. Use ASCII block letters (`█` `╗` `═`),
not box-drawing borders or emoji. The banner signals "this is a real tool,
not a script someone threw together."

```bash
splash() {
  echo ""
  printf "${COLOR_TITLE}${BOLD}"
  cat << 'BANNER'
   ████████╗ ██████╗  ██████╗ ██╗
   ╚══██╔══╝██╔═══██╗██╔═══██╗██║
      ██║   ██║   ██║██║   ██║██║
      ██║   ╚██████╔╝╚██████╔╝███████╗
      ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
BANNER
  printf "${RESET}"
  printf "  ${COLOR_MUTED}Subtitle text here${RESET}\n"
  echo ""
}
```

After the banner, show a simple loading bar to give the user a moment:

```bash
local bar_width=54
printf "  ${DIM}[${RESET}"
for ((i=0; i<bar_width; i++)); do
  printf "${COLOR_SUCCESS}█${RESET}"
  sleep 0.01
done
printf "${DIM}]${RESET}  ${COLOR_SUCCESS}✓${RESET}\n\n"
```

### Spinners

**Braille spinner** for operations that take a few seconds:

```bash
spin() {
  local label="$1" cycles="${2:-3}"
  local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
  local cycle=0 idx=0
  while ((cycle < cycles)); do
    printf "\r  ${COLOR_ACTIVE}%s${RESET} %s" "${frames[$idx]}" "$label"
    ((idx++))
    if [[ $idx -ge ${#frames[@]} ]]; then idx=0; ((cycle++)); fi
    sleep 0.12
  done
  printf "\r  ${COLOR_SUCCESS}✓${RESET} %s\n" "$label"
}
```

**Breathing spinner** for idle/watch states (run in background, kill when done):

```bash
breathe() {
  local label="${1:-Watching...}"
  local frames=("░" "▒" "▓" "█" "▓" "▒")
  local colours=("${CYAN}" "${CYAN}" "${CYAN}" "${WHITE}" "${WHITE}" "${CYAN}")
  local idx=0
  while true; do
    printf "\r  %s%s${RESET} ${DIM}%s${RESET}  " "${colours[$idx]}" "${frames[$idx]}" "$label"
    idx=$(( (idx + 1) % ${#frames[@]} ))
    sleep 0.2
  done
}

# Usage:
breathe "Watching for changes..." &
SPIN_PID=$!
# ... do work ...
kill $SPIN_PID 2>/dev/null; wait $SPIN_PID 2>/dev/null
```

### Flag Parsing

Every script should accept at least `--help`. Data-writing scripts get
`--dry-run`. Interactive scripts get `--quiet`.

```bash
DRY_RUN=false
QUIET=false

for arg in "$@"; do
  case "$arg" in
    --dry|--dry-run) DRY_RUN=true ;;
    --quiet)         QUIET=true ;;
    --help)
      echo ""
      printf "  ${BOLD}TOOLNAME${RESET} — description\n\n"
      printf "  Usage:  bash %s [flags]\n\n" "$0"
      printf "  ${BOLD}Flags:${RESET}\n"
      printf "    --dry-run    Show what would happen without doing it\n"
      printf "    --quiet      Suppress banner and animations\n"
      printf "    --help       Show this help\n\n"
      exit 0 ;;
  esac
done
```

When `$DRY_RUN` is true, show a prominent banner:
```bash
$DRY_RUN && printf "  ${COLOR_WARN}${BOLD}DRY RUN${RESET}${COLOR_MUTED} — no data will be written${RESET}\n"
```

---

## Animation & Motion

### Speed Tiers

| Tier | Frame delay | Row delay | Use |
|------|------------|-----------|-----|
| Slow | 0.08s | 0.15s | Dramatic reveals |
| Medium | 0.05s | 0.08s | General use |
| **Fast** | **0.02s** | **0.03s** | **Default** |

### Comet Tail (default loading animation)

The full implementation is in `${CLAUDE_PLUGIN_ROOT}/references/components.md`. Use it for:
- Table row ingest (animate before each row appears)
- File processing progress
- Any linear progress indicator

### Screen Transitions

Use the **Pixel Scatter** transition between major UI sections. Full
implementation in `${CLAUDE_PLUGIN_ROOT}/references/components.md`.

### Animated Splash

For tools that want maximum polish: Ocean Wave sweep → bright-white flicker
→ Sunrise gradient. Full implementation in `${CLAUDE_PLUGIN_ROOT}/references/components.md`.
Splash always requires a human keypress before proceeding.

---

## Single-File vs Multi-File

**Single file** (most common for generated scripts): embed the palette,
helpers, and all functions in one script. Use comment section headers to
organize:

```bash
# ── Palette ──────────────────────────────────────────────
# ── Terminal Control ─────────────────────────────────────
# ── Text Helpers ─────────────────────────────────────────
# ── Animations ───────────────────────────────────────────
# ── Splash ───────────────────────────────────────────────
# ── Core Functions ───────────────────────────────────────
# ── Menu ─────────────────────────────────────────────────
# ── Main ─────────────────────────────────────────────────
```

**Multi-file** (for bigger projects): split into `_lib.sh` + `_helpers.sh` +
tool scripts. See `${CLAUDE_PLUGIN_ROOT}/references/architecture.md` for the full pattern.

---

## What NOT to Do

- No `echo -e` for colored output — use `printf` consistently
- No numbered menus (`1) 2) 3)`) — use chevrons with arrow keys
- No emoji in headers or status output — use Unicode markers (✓ ✗ ⚠ ℹ)
- No box-drawing borders for banners — use ASCII block letters
- No raw ANSI codes in output statements — use semantic tokens
- No hardcoded column widths in printf — declare as `W_NAME=16` variables
- No `#!/bin/bash` — use `#!/usr/bin/env bash` for portability
- No missing `set -euo pipefail`

---

## Dependencies

- bash 3.2+ (macOS default is fine)
- curl (for API calls, optional)
- python3 (for JSON parsing, optional)
- No ncurses, no tput for colors, no external TUI frameworks
