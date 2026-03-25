#!/usr/bin/env bash
# health-check.sh — Server health checker with interactive menu
# Features: disk usage, memory usage, network connectivity checks
# Polished terminal UI with colors, banner, and formatted tables

set -euo pipefail

# ── ANSI Color Palette ────────────────────────────────────────────────────────

# Formatting
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# Standard 16-color
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'

# Extended palette
TEAL='\033[38;5;43m'
SLATE='\033[38;5;244m'
CORAL='\033[38;5;210m'
AQUA='\033[38;5;87m'
INDIGO='\033[38;5;63m'
ELECTRIC='\033[38;5;33m'
SKY='\033[38;5;117m'
GOLD='\033[38;5;220m'
ORANGE='\033[38;5;208m'

# Semantic role tokens
COLOR_TITLE="${CYAN}"
COLOR_ACCENT="${CYAN}"
COLOR_TEXT="${WHITE}"
COLOR_MUTED="${DIM}"
COLOR_SUCCESS="${GREEN}"
COLOR_WARN="${YELLOW}"
COLOR_ERROR="${RED}"
COLOR_ACTIVE="${CYAN}"
COLOR_INFO="${DIM}"

# ── Terminal Control ──────────────────────────────────────────────────────────

cls()      { printf "\033[2J\033[H"; }
hide_cur() { printf "\033[?25l"; }
show_cur() { printf "\033[?25h"; }

# ── Text Helpers ──────────────────────────────────────────────────────────────

trunc() {
  local str="$1" max="$2"
  if (( ${#str} > max )); then
    printf "%s" "${str:0:$((max-1))}…"
  else
    printf "%-${max}s" "$str"
  fi
}

# Generate horizontal rule with pipes
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

# ── Loading Animations ────────────────────────────────────────────────────────

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

# ── Splash Banner ─────────────────────────────────────────────────────────────

splash() {
  cls; hide_cur
  echo ""
  printf "${COLOR_TITLE}${BOLD}"
  cat << 'BANNER'
   ██╗  ██╗███████╗ █████╗ ██╗  ████████╗██╗  ██╗
   ██║  ██║██╔════╝██╔══██╗██║  ╚══██╔══╝██║  ██║
   ███████║█████╗  ███████║██║     ██║   ███████║
   ██╔══██║██╔══╝  ██╔══██║██║     ██║   ██╔══██║
   ██║  ██║███████╗██║  ██║██║     ██║   ██║  ██║
   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝   ╚═╝  ╚═╝
BANNER
  printf "${RESET}"
  printf "  ${DIM}Real-time server diagnostics${RESET}\n"
  echo ""

  # Simple loading bar
  local bar_width=54
  printf "  ${DIM}[${RESET}"
  for ((i=0; i<bar_width; i++)); do
    printf "${COLOR_SUCCESS}█${RESET}"
    sleep 0.01
  done
  printf "${DIM}]${RESET}  ${COLOR_SUCCESS}✓${RESET}\n\n"
}

# ── Cleanup Handler ───────────────────────────────────────────────────────────

cleanup() {
  show_cur
  printf "${RESET}\n"
}

trap cleanup EXIT INT TERM

# ── Health Check Functions ────────────────────────────────────────────────────

check_disk_usage() {
  echo ""
  printf "  ${COLOR_TITLE}${BOLD}━━ Disk Usage ━━${RESET}\n"
  echo ""

  # Animate loading
  local row_width=66
  animate_comet_tail "$row_width" "0.02"

  # Column widths
  W_MOUNT=18
  W_SIZE=12
  W_USED=12
  W_AVAIL=12
  W_USAGE=8

  # Header
  printf "  ${BOLD}%-${W_MOUNT}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_SIZE}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_USED}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_AVAIL}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_USAGE}s${RESET}\n" \
    "Mount" "Size" "Used" "Available" "Usage"
  hr "${DIM}" "─" "┼" "$W_MOUNT" "$W_SIZE" "$W_USED" "$W_AVAIL" "$W_USAGE"

  # Get disk info using df
  local count=0
  while IFS=' ' read -r device size used avail usage mount; do
    [[ "$mount" == "Mounted"* ]] && continue
    [[ -z "$mount" ]] && continue

    # Truncate cells
    local mount_cell=$(trunc "$mount" "$W_MOUNT")
    local size_cell=$(trunc "$size" "$W_SIZE")
    local used_cell=$(trunc "$used" "$W_USED")
    local avail_cell=$(trunc "$avail" "$W_AVAIL")

    # Determine color based on usage percentage
    local usage_pct="${usage%\%}"
    local usage_color="${COLOR_SUCCESS}"
    if (( usage_pct > 80 )); then
      usage_color="${COLOR_ERROR}"
    elif (( usage_pct > 60 )); then
      usage_color="${COLOR_WARN}"
    fi

    # Animate before row
    animate_comet_tail "$row_width" "0.02"

    printf "  %-${W_MOUNT}s ${DIM}│${RESET} ${SLATE}%-${W_SIZE}s${RESET} ${DIM}│${RESET} ${SLATE}%-${W_USED}s${RESET} ${DIM}│${RESET} ${SLATE}%-${W_AVAIL}s${RESET} ${DIM}│${RESET} ${usage_color}%-${W_USAGE}s${RESET}\n" \
      "$mount_cell" "$size_cell" "$used_cell" "$avail_cell" "${usage}"

    ((count++))
  done < <(df -h | tail -n +2)

  if [[ $count -eq 0 ]]; then
    printf "  ${COLOR_MUTED}(no filesystems)${RESET}\n"
  fi

  echo ""
  pause
}

check_memory_usage() {
  echo ""
  printf "  ${COLOR_TITLE}${BOLD}━━ Memory Usage ━━${RESET}\n"
  echo ""

  # Animate loading
  local row_width=60
  animate_comet_tail "$row_width" "0.02"

  # Get memory info
  local total_mem used_mem avail_mem
  if [[ -f /proc/meminfo ]]; then
    # Linux
    local mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local mem_avail=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
    mem_total=$((mem_total / 1024))  # Convert to MB
    mem_avail=$((mem_avail / 1024))  # Convert to MB
    local mem_used=$((mem_total - mem_avail))
    local mem_usage=$((mem_used * 100 / mem_total))

    total_mem="${mem_total}M"
    used_mem="${mem_used}M"
    avail_mem="${mem_avail}M"
  else
    # macOS
    local page_size=$(vm_stat | grep "page size" | awk '{print $8}')
    local pages_used=$(vm_stat | grep "Pages active\|Pages wired" | awk '{sum+=$3} END {print sum}')
    local pages_total=$(vm_stat | grep "Pages free\|Pages active\|Pages inactive" | awk '{sum+=$3} END {print sum}')
    mem_used=$((pages_used * page_size / 1024 / 1024))
    mem_total=$((pages_total * page_size / 1024 / 1024))
    mem_avail=$((mem_total - mem_used))
    mem_usage=$((mem_used * 100 / mem_total))

    total_mem="${mem_total}M"
    used_mem="${mem_used}M"
    avail_mem="${mem_avail}M"
  fi

  # Column widths
  W_LABEL=12
  W_VALUE=14

  # Header
  printf "  ${BOLD}%-${W_LABEL}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_VALUE}s${RESET}\n" "Type" "Amount"
  hr "${DIM}" "─" "┼" "$W_LABEL" "$W_VALUE"

  # Determine color based on usage percentage
  local mem_color="${COLOR_SUCCESS}"
  if (( mem_usage > 80 )); then
    mem_color="${COLOR_ERROR}"
  elif (( mem_usage > 60 )); then
    mem_color="${COLOR_WARN}"
  fi

  # Animate before each row
  animate_comet_tail "$row_width" "0.02"
  printf "  %-${W_LABEL}s ${DIM}│${RESET} ${SLATE}%-${W_VALUE}s${RESET}\n" "Total" "$total_mem"

  animate_comet_tail "$row_width" "0.02"
  printf "  %-${W_LABEL}s ${DIM}│${RESET} ${mem_color}%-${W_VALUE}s${RESET}\n" "Used" "$used_mem"

  animate_comet_tail "$row_width" "0.02"
  printf "  %-${W_LABEL}s ${DIM}│${RESET} ${COLOR_SUCCESS}%-${W_VALUE}s${RESET}\n" "Available" "$avail_mem"

  animate_comet_tail "$row_width" "0.02"
  printf "  %-${W_LABEL}s ${DIM}│${RESET} ${mem_color}%-${W_VALUE}s${RESET}\n" "Usage %" "${mem_usage}%"

  echo ""
  pause
}

check_network() {
  echo ""
  printf "  ${COLOR_TITLE}${BOLD}━━ Network Connectivity ━━${RESET}\n"
  echo ""

  # Animate ping check with spinner
  spin "Pinging google.com" 2
  echo ""

  # Column widths
  W_TEST=16
  W_RESULT=30

  # Header
  printf "  ${BOLD}%-${W_TEST}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_RESULT}s${RESET}\n" "Test" "Result"
  hr "${DIM}" "─" "┼" "$W_TEST" "$W_RESULT"

  # Test ping to google.com
  local ping_result
  if ping -c 1 -W 2 google.com &>/dev/null 2>&1; then
    ping_result="✓ Connected"
    local ping_color="${COLOR_SUCCESS}"
  else
    ping_result="✗ No response"
    local ping_color="${COLOR_ERROR}"
  fi

  printf "  %-${W_TEST}s ${DIM}│${RESET} ${ping_color}%-${W_RESULT}s${RESET}\n" "google.com" "$ping_result"

  # Test DNS resolution
  local dns_result
  if command -v nslookup &>/dev/null; then
    if nslookup google.com &>/dev/null 2>&1; then
      dns_result="✓ Resolves"
      local dns_color="${COLOR_SUCCESS}"
    else
      dns_result="✗ Failed"
      local dns_color="${COLOR_ERROR}"
    fi
  else
    dns_result="⚠ nslookup not available"
    local dns_color="${COLOR_WARN}"
  fi

  printf "  %-${W_TEST}s ${DIM}│${RESET} ${dns_color}%-${W_RESULT}s${RESET}\n" "DNS" "$dns_result"

  # Test localhost
  local localhost_result
  if ping -c 1 -W 1 127.0.0.1 &>/dev/null 2>&1; then
    localhost_result="✓ OK"
    local localhost_color="${COLOR_SUCCESS}"
  else
    localhost_result="✗ Failed"
    local localhost_color="${COLOR_ERROR}"
  fi

  printf "  %-${W_TEST}s ${DIM}│${RESET} ${localhost_color}%-${W_RESULT}s${RESET}\n" "Localhost" "$localhost_result"

  echo ""
  pause
}

pause() {
  echo ""
  printf "  ${COLOR_MUTED}Press any key to continue...${RESET}"
  read -rsn1
  echo ""
}

# ── Menu Navigation ──────────────────────────────────────────────────────────

draw_menu() {
  local sel="$1"
  local opts=("Disk Usage" "Memory Usage" "Network Check" "Exit")
  for i in "${!opts[@]}"; do
    if [[ $i -eq $sel ]]; then
      printf "  ${TEAL}›› ${BOLD}%s${RESET}\n" "${opts[$i]}"
    else
      printf "  ${COLOR_MUTED}›  %s${RESET}\n" "${opts[$i]}"
    fi
  done
}

dispatch_action() {
  local sel="$1"
  case $sel in
    0) check_disk_usage ;;
    1) check_memory_usage ;;
    2) check_network ;;
    3) return 1 ;;  # Exit signal
  esac
}

# ── Main Loop ─────────────────────────────────────────────────────────────────

main() {
  splash
  pause

  local selected=0
  local max=3  # Number of menu items minus 1

  while true; do
    cls; hide_cur
    echo ""
    printf "  ${COLOR_TITLE}${BOLD}━━ Server Health Check ━━${RESET}\n"
    printf "  ${COLOR_MUTED}Select a diagnostic test${RESET}\n\n"

    draw_menu "$selected"

    echo ""
    printf "  ${COLOR_MUTED}↑/↓ navigate  •  Enter select  •  q quit${RESET}"

    read -rsn1 key
    case "$key" in
      '') # Enter
        show_cur
        if ! dispatch_action "$selected"; then
          break
        fi
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

  show_cur
  echo ""
  printf "  ${COLOR_MUTED}Goodbye.${RESET}\n\n"
}

# Run the script
main
