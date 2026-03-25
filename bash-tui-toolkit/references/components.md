# UI Components Reference

Complete code samples for every visual component in the toolkit.

## Table of Contents

1. [Terminal Utilities](#terminal-utilities)
2. [Menus](#menus)
   - Single Select
   - Boolean Toggle
   - Multi Select
   - Arrow Key Navigation Loop
   - Group Headers and Hints
   - Coming Soon Items
3. [Tables](#tables)
   - Fixed-Width Layout
   - Horizontal Rules
   - Animated Row Ingest
4. [Loading Bars](#loading-bars)
   - Simple Fill
   - Comet Tail (Default)
   - Multi-Pass Animated
   - Tool Discovery Bar
5. [Spinners](#spinners)
   - Braille Spinner
   - Breathing Spinner
6. [Splash Banners](#splash-banners)
   - Simple Static
   - Animated (Ocean Wave → Sunrise)
7. [Screen Transitions](#screen-transitions)
   - Pixel Scatter (Default)
8. [Bootloader](#bootloader)
   - POST-Style with Animated Logo
9. [Status Output](#status-output)

---

## Terminal Utilities

Foundation helpers that every interactive script needs:

```bash
cls()      { printf "\033[2J\033[H"; }
hide_cur() { printf "\033[?25l"; }
show_cur() { printf "\033[?25h"; }

pause() {
  echo ""
  printf "  ${DIM}Press any key...${RESET}"
  read -rsn1
  echo ""
}

section() {
  echo ""
  printf "  ${CYAN}${BOLD}━━ %s ━━${RESET}\n\n" "$1"
}
```

Always restore the cursor in cleanup:

```bash
cleanup() { show_cur; printf "${RESET}\n"; }
trap cleanup EXIT INT TERM
```

---

## Menus

### Single Select

Chevron focus. `››` = focused, `›` = unfocused:

```bash
draw_menu_single() {
  local sel="$1"
  local opts=("Contacts" "Companies" "Deals" "Tickets")
  for i in "${!opts[@]}"; do
    if [[ $i -eq $sel ]]; then
      printf "  ${TEAL}›› ${BOLD}%s${RESET}\n" "${opts[$i]}"
    else
      printf "  ${DIM}›  %s${RESET}\n" "${opts[$i]}"
    fi
  done
}
```

Output:
```
  ›  Contacts
  ›› Companies
  ›  Deals
  ›  Tickets
```

### Boolean Toggle

Chevrons for focus, fillable circles for state:

```bash
draw_menu_toggle() {
  local sel="$1"
  local opts=("Export contacts" "Export companies" "Export deals" "Include archived")
  local states=(true false true false)
  for i in "${!opts[@]}"; do
    local marker="○"
    ${states[$i]} && marker="●"
    if [[ $i -eq $sel ]]; then
      printf "  ${TEAL}››${RESET} ${WHITE}${marker}${RESET} ${BOLD}%s${RESET}\n" "${opts[$i]}"
    else
      printf "  ${DIM}›${RESET}  ${WHITE}${marker}${RESET} ${DIM}%s${RESET}\n" "${opts[$i]}"
    fi
  done
}
```

Output:
```
  ›› ● Export contacts
  ›  ○ Export companies
  ›  ● Export deals
  ›  ○ Include archived
```

### Multi Select

Chevrons for focus, checkboxes for persistent selection:

```bash
draw_menu_multi() {
  local sel="$1"
  local opts=("Contacts" "Companies" "Deals" "Tickets")
  local states=(true false true false)
  for i in "${!opts[@]}"; do
    local marker="[ ]"
    ${states[$i]} && marker="[x]"
    if [[ $i -eq $sel ]]; then
      printf "  ${TEAL}››${RESET} ${CYAN}%s${RESET} ${BOLD}%s${RESET}\n" "$marker" "${opts[$i]}"
    else
      printf "  ${DIM}›${RESET}  ${DIM}%s${RESET} %s\n" "$marker" "${opts[$i]}"
    fi
  done
}
```

### Arrow Key Navigation Loop

The full interactive loop pattern. Works on macOS and Linux:

```bash
selected=0
max=$(( ${#LABELS[@]} - 1 ))

while true; do
  cls; hide_cur
  echo ""
  printf "  ${CYAN}${BOLD}━━ Tool Name ━━${RESET}\n"
  printf "  ${DIM}Select an option${RESET}\n\n"

  draw_menu $selected

  echo ""
  printf "  ${DIM}↑/↓ navigate  •  Enter select  •  q quit${RESET}"

  read -rsn1 key
  case "$key" in
    '') # Enter
      show_cur
      dispatch_action $selected
      hide_cur
      ;;
    q|Q) break ;;
    $'\033') # Escape sequence
      seq1="" seq2=""
      read -rsn1 -t 1 seq1 || true
      read -rsn1 -t 1 seq2 || true
      if [[ "${seq1:-}" == "[" ]]; then
        case "${seq2:-}" in
          A) ((selected > 0)) && selected=$((selected - 1)) ;;
          B) ((selected < max)) && selected=$((selected + 1)) ;;
        esac
      fi
      ;;
  esac
done

printf "\n  ${DIM}Goodbye.${RESET}\n\n"
```

### Group Headers and Hints

Add section headings and parenthetical hints to menu items:

```bash
LABELS=("Watch & upload" "File Manager" "Export contacts" "Export companies" "Exit")
HINTS=("cms-watch" "fm-upload" "export-contacts" "export-companies" "")

# In draw_menu:
# Print group header at specific indices
if [[ $i -eq 0 ]]; then
  printf "  ${BOLD}DESIGN MANAGER${RESET}\n"
elif [[ $i -eq 2 ]]; then
  echo ""
  printf "  ${BOLD}CRM EXPORTS${RESET}\n"
fi

# Append hint if present
local hint=""
[[ -n "${HINTS[$i]}" ]] && hint="  ${DIM}(${HINTS[$i]})${RESET}"
printf "  ${TEAL}›› ${BOLD}%s${RESET}%s\n" "${LABELS[$i]}" "$hint"
```

### Coming Soon Items

Lock unavailable items with dim styling and a badge:

```bash
COMING_SOON=",3,4,"  # Comma-delimited indices

# In draw_menu:
if [[ "$COMING_SOON" == *",$i,"* ]]; then
  printf "    ${DIM}›  %s${RESET}  ${DIM}── COMING SOON${RESET}\n" "${LABELS[$i]}"
else
  # normal focused/unfocused rendering
fi

# In navigation: skip coming-soon items
nsel=$((selected + 1))
while ((nsel <= max)) && [[ "$COMING_SOON" == *",$nsel,"* ]]; do
  nsel=$((nsel + 1))
done
if ((nsel <= max)); then selected=$nsel; fi
```

---

## Tables

### Fixed-Width Layout

The cardinal rule: declare widths, truncate cells, then format. Pipes never
drift regardless of data content.

```bash
W_NAME=16
W_EMAIL=26
W_STATUS=10

# Header
printf "  ${BOLD}%-${W_NAME}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_EMAIL}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_STATUS}s${RESET}\n" \
  "Name" "Email" "Status"

# Separator
printf "  ${DIM}"
for ((i=0; i<W_NAME; i++)); do printf "─"; done
printf "─┼─"
for ((i=0; i<W_EMAIL; i++)); do printf "─"; done
printf "─┼─"
for ((i=0; i<W_STATUS; i++)); do printf "─"; done
printf "${RESET}\n"

# Data row
name_cell=$(trunc "$name" "$W_NAME")
email_cell=$(trunc "$email" "$W_EMAIL")
printf "  %-${W_NAME}s ${DIM}│${RESET} ${SLATE}%-${W_EMAIL}s${RESET} ${DIM}│${RESET} ${GREEN}%-${W_STATUS}s${RESET}\n" \
  "$name_cell" "$email_cell" "$status"
```

### Horizontal Rule Helper

Generate table separators that match column widths:

```bash
hr() {
  local color="$1" char="$2" join="$3"
  shift 3
  local widths=("$@")
  printf "  %s" "$color"
  for ((c=0; c<${#widths[@]}; c++)); do
    local seg_width
    if (( c == 0 || c == ${#widths[@]}-1 )); then
      seg_width=$((widths[c]+1))
    else
      seg_width=$((widths[c]+2))
    fi
    for ((i=0; i<seg_width; i++)); do printf "%s" "$char"; done
    if ((c < ${#widths[@]}-1)); then printf "%s" "$join"; fi
  done
  printf "${RESET}\n"
}

# Usage:
hr "${DIM}" "─" "┼" $W_NAME $W_EMAIL $W_STATUS
```

### Animated Row Ingest (Comet Tail)

When fetching data row by row, animate a comet effect before printing each row:

```bash
block_run() {
  local count="$1" char="$2" out=""
  for ((i=0; i<count; i++)); do out="${out}${char}"; done
  printf "%s" "$out"
}

animate_comet_tail() {
  local total="$1" delay="$2"
  local steps=10
  for ((frame=1; frame<=steps; frame++)); do
    local filled=$(( total * frame / steps ))
    local head_end=$filled
    local head_start=$(( head_end - 2 ))
    (( head_start < 0 )) && head_start=0
    local trail=$(( head_start > 3 ? 3 : head_start ))
    local pre=$(( head_start - trail ))
    (( pre < 0 )) && pre=0
    local after=$(( total - head_end ))
    (( after < 0 )) && after=0

    printf "\r  "
    printf "%s" "$(block_run "$pre" " ")"
    printf "${DIM}%s${RESET}" "$(block_run "$trail" "░")"
    printf "${WHITE}%s${RESET}" "$(block_run "$trail" "▒")"
    printf "${WHITE}%s${RESET}" "$(block_run "$(( head_end - head_start ))" "█")"
    printf "%s" "$(block_run "$after" " ")"
    sleep "$delay"
  done
  printf "\r\033[2K"
}

# Usage: animate before each data row
ROW_WIDTH=$((W_NAME + W_EMAIL + W_STATUS + 6))  # +6 for separators
animate_comet_tail "$ROW_WIDTH" "0.02"
printf "  %-${W_NAME}s ${DIM}│${RESET} ..." "$name_cell"
```

---

## Loading Bars

### Simple Fill

Basic progress bar with `[ ]` container:

```bash
loading_simple() {
  local bar_width=54
  printf "  ${DIM}["
  for ((i=0; i<bar_width; i++)); do printf " "; done
  printf "]${RESET}\r  ${DIM}[${RESET}"

  for ((i=0; i<bar_width; i++)); do
    printf "${GREEN}█${RESET}"
    sleep 0.02
  done
  printf "${DIM}]${RESET}\n\n"
}
```

### Multi-Pass Animated

Fills multiple times with accelerating speed. Cyan for intermediate passes,
green for the final:

```bash
loading_animated() {
  local bar_width=54 cycles=${1:-5} base_delay=0.025
  for ((c=1; c<=cycles; c++)); do
    local delay=$(python3 -c "print(max(0.005, ${base_delay} - (${c}-1)*0.005))")

    # Draw empty frame
    printf "\r  ${DIM}["; for ((i=0;i<bar_width;i++)); do printf " "; done; printf "]${RESET}"

    # Fill
    printf "\r  ${DIM}[${RESET}"
    for ((i=0; i<bar_width; i++)); do
      if ((c == cycles)); then
        printf "${GREEN}█${RESET}"
      else
        printf "${CYAN}█${RESET}"
      fi
      sleep "$delay"
    done

    # Flash reset between passes
    if ((c < cycles)); then
      printf "\r  ${DIM}["
      for ((i=0;i<bar_width;i++)); do printf "${DIM}░${RESET}"; done
      printf "${DIM}]${RESET}"; sleep 0.08
    fi
  done

  printf "\r  ${DIM}[${RESET}"
  for ((i=0;i<bar_width;i++)); do printf "${GREEN}█${RESET}"; done
  printf "${DIM}]${RESET}  ${GREEN}✓${RESET}\n\n"
}
```

### Tool Discovery Bar

Step-by-step progress that checks file existence:

```bash
discover_tools() {
  local entries=("$@")  # "Label:path" pairs
  local total=${#entries[@]} bar_w=54
  local found=0 missing=0

  for ((idx=0; idx<total; idx++)); do
    local label="${entries[$idx]%%:*}"
    local path="${entries[$idx]#*:}"

    # Comet progress bar
    local filled=$(( bar_w * (idx+1) / total ))
    printf "\r   ${DIM}[${RESET}"
    # ... render comet at position ...
    printf "${DIM}]${RESET} ${DIM}%d/%d${RESET}" "$((idx+1))" "$total"

    [[ -f "$path" ]] && ((found++)) || ((missing++))
    sleep 0.06
  done

  # Final green bar
  printf "\r   ${DIM}[${RESET}"
  for ((i=0;i<bar_w;i++)); do printf "${GREEN}█${RESET}"; done
  printf "${DIM}]${RESET}  ${GREEN}✓${RESET}\n\n"

  # Status list
  for ((idx=0; idx<total; idx++)); do
    local label="${entries[$idx]%%:*}"
    local path="${entries[$idx]#*:}"
    if [[ -f "$path" ]]; then
      printf "   ${GREEN}✓${RESET}  %-26s ${DIM}%s${RESET}\n" "$label" "$(basename "$path")"
    else
      printf "   ${RED}✗${RESET}  %-26s ${DIM}%s${RESET} ${RED}missing${RESET}\n" "$label" "$(basename "$path")"
    fi
  done
}
```

---

## Spinners

### Braille Spinner (Short Waits)

Runs for N cycles, then prints ✓:

```bash
spin() {
  local label="$1" cycles="${2:-3}"
  local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
  local cycle=0 idx=0
  while ((cycle < cycles)); do
    printf "\r  ${CYAN}%s${RESET} %s" "${frames[$idx]}" "$label"
    ((idx++))
    if [[ $idx -ge ${#frames[@]} ]]; then idx=0; ((cycle++)); fi
    sleep 0.12
  done
  printf "\r  ${GREEN}✓${RESET} %s\n" "$label"
}
```

### Breathing Spinner (Idle/Watch States)

Infinite loop — run in background, kill when done:

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
kill $SPIN_PID 2>/dev/null
wait $SPIN_PID 2>/dev/null
```

---

## Splash Banners

### Simple Static

ASCII art banner with optional subtitle and loading bar:

```bash
splash_simple() {
  local subtitle="${1:-}"
  $QUIET && return 0
  echo ""
  printf "${COLOR_TITLE}${BOLD}"
  cat << 'BANNER'
   ████████╗ ██████╗  ██████╗ ██╗
   ╚══██╔══╝██╔═══██╗██╔═══██╗██║
      ██║   ██║   ██║██║   ██║██║
      ██║   ██║   ██║██║   ██║██║
      ██║   ╚██████╔╝╚██████╔╝███████╗
      ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
BANNER
  printf "${RESET}"
  [[ -n "$subtitle" ]] && printf "${DIM}  %s${RESET}\n" "$subtitle"
  $DRY_RUN && printf "  ${COLOR_WARN}${BOLD}DRY RUN${RESET}${DIM} — no data will be written${RESET}\n"
  echo ""
  # Loading bar follows
  loading_simple
}
```

### Animated Splash (Ocean Wave → Sunrise)

Three-phase reveal. Store banner lines in an array, sweep color across
character by character:

```bash
splash_fancy() {
  local subtitle="${1:-}"
  $QUIET && { splash_simple "$subtitle"; return 0; }

  local -a LINES=( ... )  # ASCII art lines
  local -a WAVE=("${INDIGO}" "${BLUE}" "${ELECTRIC}" "${CYAN}" "${SKY}" "${AQUA}" "${TEAL}" "${CYAN}")
  local -a SUNRISE=("${GOLD}" "${ORANGE}" "${CORAL}" "${PINK}" "${VIOLET}" "${INDIGO}")

  printf "\033[2J\033[H\033[?25l"  # Clear, home, hide cursor
  # Print empty lines as placeholders
  for line in "${LINES[@]}"; do echo ""; done

  # Phase 1: Ocean Wave — sweep color left to right
  local max_len=${#LINES[0]}
  for ((sweep=0; sweep<max_len; sweep+=4)); do
    for ((l=0; l<${#LINES[@]}; l++)); do
      # Move cursor to line, print each char with wave color based on position
      # Characters behind the sweep get CYAN, ahead get DIM, near the sweep
      # get wave colours from the array based on distance
    done
    sleep 0.02
  done

  # Phase 2: Rapid bright-white flicker (10 cycles, 0.04s/flash)
  for ((f=0; f<10; f++)); do
    _repaint "${WHITE}" "${BOLD}"; sleep 0.04
    _repaint "${CYAN}" "${BOLD}";  sleep 0.04
  done

  # Phase 3: Settle into Sunrise gradient — each line gets its gradient color
  for ((l=0; l<${#LINES[@]}; l++)); do
    # Move to line, print with SUNRISE[$l] color
  done

  echo ""
  printf "   ${DIM}─────────────────────────${RESET}\n"
  printf "   ${DIM}All Rights Reserved (c) 1984${RESET}\n"
}
```

**Rule: Splash always requires human keypress confirmation before proceeding.**

---

## Screen Transitions

### Pixel Scatter (Production Default)

Three-phase transition: sparse scatter → dense fill → solid sweep → clear:

```bash
transition_pixel_scatter() {
  local rows cols
  rows=$(tput lines); cols=$(tput cols)
  hide_cur
  local chars=("█" "▓" "▒" "░")

  # Phase 1 — sparse scatter (mixed density chars)
  for ((i=0; i<60; i++)); do
    for ((b=0; b<12; b++)); do
      local rr=$(( (RANDOM % rows) + 1 ))
      local rc=$(( (RANDOM % cols) + 1 ))
      local ci=$((RANDOM % 4))
      printf "\033[%d;%dH${CYAN}%s${RESET}" "$rr" "$rc" "${chars[$ci]}"
    done
    sleep 0.01
  done

  # Phase 2 — dense fill (solid blocks only)
  for ((i=0; i<80; i++)); do
    for ((b=0; b<20; b++)); do
      local rr=$(( (RANDOM % rows) + 1 ))
      local rc=$(( (RANDOM % cols) + 1 ))
      printf "\033[%d;%dH${CYAN}█${RESET}" "$rr" "$rc"
    done
    sleep 0.005
  done

  # Phase 3 — full fill then clear
  for ((row=1; row<=rows; row++)); do
    printf "\033[%d;1H" "$row"
    for ((col=0; col<cols; col++)); do printf "${CYAN}█${RESET}"; done
  done
  sleep 0.12
  cls; show_cur
}
```

---

## Bootloader

### POST-Style with Animated Logo

A retro BIOS-style boot sequence with a spinning logo and diagnostic lines.
The logo is defined as an array of frame arrays (one per rotation step), and
POST lines appear incrementally during the spin:

```bash
# Define 12 rotation frames as arrays (e.g., BL_F0, BL_F1, ... BL_F11)
# Each frame is 6 lines of exactly 20 display columns

POST_ITEMS=("Memory" "Processor" "Module registry" "API endpoints" "Auth tokens" "CLI version")
POST_VALUES=("256K OK" "1 core OK" "6 modules loaded" "3 endpoints resolved" "valid" "v8.1.0")

# Main sequence:
cls; hide_cur
printf "\n  ${DIM}CompanyName International, Inc.${RESET}\n"
printf "  ${DIM}BIOS v1.84 — 1984${RESET}\n"

# Spin 3 full rotations, interleave POST lines
spin_frames=$((12 * 3))
post_interval=$((spin_frames / ${#POST_ITEMS[@]}))

for ((i=0; i<spin_frames; i++)); do
  draw_frame $((i % 12))
  if (( i > 0 && i % post_interval == 0 )); then
    draw_post_line  # Prints "Label ── value" in green
  fi
  sleep 0.12
done

printf "\n    ${GREEN}${BOLD}All systems ready${RESET}\n"
sleep 0.8
transition_pixel_scatter
```

---

## Status Output

Consistent markers for all informational output:

```bash
# Success
printf "  ${GREEN}✓${RESET} %-14s ${BOLD}%s${RESET} records\n" "Contacts" "1,234"

# Error
printf "  ${RED}✗${RESET} %-14s ${DIM}%s${RESET}\n" "Tickets" "403 — scope not granted"

# Warning
printf "  ${YELLOW}⚠${RESET}  ${BOLD}%d${RESET} of ${BOLD}%d${RESET} tools found  ${DIM}(%d missing)${RESET}\n" 5 6 1

# Info
printf "  ${CYAN}ℹ${RESET}  ${DIM}%s${RESET}\n" "Using token from .token-file"

# Diagnostic with fixed-width label column
printf "  ${GREEN}✓${RESET} %-16s ${DIM}%s${RESET}\n" "Python" "Python 3.12.1"
printf "  ${GREEN}✓${RESET} %-16s ${DIM}%s${RESET}\n" "curl" "curl 8.4.0"
printf "  ${YELLOW}⚠${RESET} %-16s ${DIM}%s${RESET}\n" "hs CLI" "Not installed"
```
