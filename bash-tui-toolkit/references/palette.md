# Color Palette Reference

Complete ANSI color system for the TUI toolkit. Copy this block into your
`_lib.sh` as the foundation.

## Table of Contents

1. [Raw Tokens](#raw-tokens)
2. [Extended Palette](#extended-palette)
3. [Background Colors](#background-colors)
4. [Semantic Role Tokens](#semantic-role-tokens)
5. [Bar-Specific Tokens](#bar-specific-tokens)
6. [Compatibility Aliases](#compatibility-aliases)
7. [Usage Rules](#usage-rules)

---

## Raw Tokens

Core formatting and standard 16-color:

```bash
# Formatting
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
INVERT='\033[7m'

# Standard 16-color
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
WHITE='\033[1;37m'
```

## Extended Palette

256-color values for richer terminals. These use `\033[38;5;Nm` syntax:

```bash
ORANGE='\033[38;5;208m'
TEAL='\033[38;5;43m'
LIME='\033[38;5;118m'
GOLD='\033[38;5;220m'
VIOLET='\033[38;5;141m'
SKY='\033[38;5;117m'
CORAL='\033[38;5;210m'
SLATE='\033[38;5;244m'
PINK='\033[38;5;213m'
MINT='\033[38;5;121m'
RUBY='\033[38;5;196m'
AMBER='\033[38;5;214m'
INDIGO='\033[38;5;63m'
PEACH='\033[38;5;216m'
AQUA='\033[38;5;87m'
ROSE='\033[38;5;204m'
STEEL='\033[38;5;103m'
SAND='\033[38;5;180m'
FOREST='\033[38;5;22m'
ELECTRIC='\033[38;5;33m'
```

## Background Colors

For highlights and emphasis blocks:

```bash
BG_DARK='\033[48;5;236m'
BG_DARKER='\033[48;5;233m'
```

## Semantic Role Tokens

Map raw colors to meanings. Scripts use these, never raw tokens directly:

```bash
COLOR_TITLE="${CYAN}"
COLOR_ACCENT="${CYAN}"
COLOR_TEXT="${WHITE}"
COLOR_MUTED="${DIM}"
COLOR_SUCCESS="${GREEN}"
COLOR_WARN="${YELLOW}"
COLOR_ERROR="${RED}"
COLOR_ACTIVE="${CYAN}"
COLOR_INFO="${DIM}"
```

## Bar-Specific Tokens

Loading bars and progress indicators get their own semantic layer:

```bash
BAR_RAIL="${DIM}"           # The [ ] container
BAR_FILL="${GREEN}"         # Completed portion (final pass)
BAR_FILL_ACTIVE="${CYAN}"   # Completed portion (intermediate passes)
BAR_HEAD="${WHITE}"         # Leading edge
BAR_PENDING="${DIM}"        # Unfilled portion
BAR_DONE="${GREEN}"         # Completion checkmark
```

## Compatibility Aliases

If you want shorter names in scripts that are purely internal (demos, tests),
create aliases. In production code, prefer the semantic tokens:

```bash
# Only for backward compat / demos
RESET="${MY_PREFIX_RESET}"
BOLD="${MY_PREFIX_BOLD}"
CYAN="${MY_PREFIX_CYAN}"
# etc.
```

## Usage Rules

1. **Always `${RESET}` after every colored segment.** Never rely on the next
   color to override — a missed reset will bleed into the rest of the line.

2. **Semantic tokens in production, raw tokens only in palette definition.**
   Write `${COLOR_SUCCESS}` not `${GREEN}` in tool scripts.

3. **Truncate text before applying color.** ANSI escapes are invisible bytes
   that break `printf` width calculations. Always:
   ```bash
   cell=$(trunc "$raw_text" "$WIDTH")
   printf "${COLOR}%-${WIDTH}s${RESET}" "$cell"
   ```
   Never:
   ```bash
   # WRONG — color applied before truncation, width will be off
   printf "${COLOR}%-${WIDTH}s${RESET}" "$(trunc "$raw_text" "$WIDTH")"
   ```
   (The second form looks similar but if trunc itself emits color codes, the
   width math breaks. Keep color application in the printf, not in the data.)

4. **Two-space indent for all output.** Every line the user sees starts with
   at least two spaces. This provides visual margin and room for status markers:
   ```
     ✓ Contacts         1,234 records
     ✗ Tickets           403 — scope not granted
   ```
