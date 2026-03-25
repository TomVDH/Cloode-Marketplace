#!/usr/bin/env bash
set -euo pipefail

cleanup() { show_cur; printf "${RESET}\n"; }
trap cleanup EXIT INT TERM

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

# ── Terminal Control ─────────────────────────────────────
cls()      { printf "\033[2J\033[H"; }
hide_cur() { printf "\033[?25l"; }
show_cur() { printf "\033[?25h"; }

# ── Text Helpers ─────────────────────────────────────────
trunc() {
  local str="$1" max="$2"
  if (( ${#str} > max )); then
    printf "%s" "${str:0:$((max-1))}…"
  else
    printf "%-${max}s" "$str"
  fi
}

section() {
  echo ""
  printf "  ${COLOR_TITLE}${BOLD}━━ %s ━━${RESET}\n\n" "$1"
}

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

# ── Spinners ─────────────────────────────────────────────
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

# ── Splash ───────────────────────────────────────────────
splash() {
  echo ""
  printf "${COLOR_TITLE}${BOLD}"
  cat << 'BANNER'
   ██╗  ██╗███████╗ █████╗ ██╗  ████████╗██╗  ██╗
   ██║  ██║██╔════╝██╔══██╗██║  ╚══██╔══╝██║  ██║
   ███████║█████╗  ███████║██║     ██║   ███████║
   ██╔══██║██╔══╝  ██╔══██║██║     ██║   ██╔══██║
   ██║  ██║███████╗██║  ██║███████╗██║   ██║  ██║
   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝   ╚═╝  ╚═╝
BANNER
  printf "${RESET}"
  printf "  ${COLOR_MUTED}Server Health Checker${RESET}\n"
  echo ""

  local bar_width=54
  printf "  ${DIM}[${RESET}"
  for ((i=0; i<bar_width; i++)); do
    printf "${COLOR_SUCCESS}█${RESET}"
    sleep 0.01
  done
  printf "${DIM}]${RESET}  ${COLOR_SUCCESS}✓${RESET}\n\n"
}

# ── Menu Drawing ─────────────────────────────────────────
draw_menu() {
  local sel="$1"
  local opts=("Check Disk Usage" "Check Memory Usage" "Check Network" "Exit")
  for i in "${!opts[@]}"; do
    if [[ $i -eq $sel ]]; then
      printf "  ${TEAL}›› ${BOLD}%s${RESET}\n" "${opts[$i]}"
    else
      printf "  ${COLOR_MUTED}›  %s${RESET}\n" "${opts[$i]}"
    fi
  done
}

# ── Health Check Functions ───────────────────────────────
check_disk() {
  section "Disk Usage"

  spin "Gathering disk information" 2

  echo ""

  # Table headers
  W_MOUNT=20
  W_SIZE=12
  W_USED=12
  W_AVAIL=12
  W_USAGE=8

  printf "  ${BOLD}%-${W_MOUNT}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_SIZE}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_USED}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_AVAIL}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_USAGE}s${RESET}\n" \
    "Mount Point" "Total" "Used" "Available" "Usage"

  hr "${DIM}" "─" "┼" $W_MOUNT $W_SIZE $W_USED $W_AVAIL $W_USAGE

  df -h | tail -n +2 | while read -r line; do
    local mount=$(echo "$line" | awk '{print $NF}')
    local total=$(echo "$line" | awk '{print $2}')
    local used=$(echo "$line" | awk '{print $3}')
    local avail=$(echo "$line" | awk '{print $4}')
    local usage=$(echo "$line" | awk '{print $5}')

    local mount_cell=$(trunc "$mount" "$W_MOUNT")
    local total_cell=$(trunc "$total" "$W_SIZE")
    local used_cell=$(trunc "$used" "$W_USED")
    local avail_cell=$(trunc "$avail" "$W_AVAIL")
    local usage_cell=$(trunc "$usage" "$W_USAGE")

    # Color usage percentage based on threshold
    local usage_pct="${usage%%%}"
    local usage_color="${COLOR_SUCCESS}"
    if (( usage_pct >= 80 )); then
      usage_color="${COLOR_ERROR}"
    elif (( usage_pct >= 60 )); then
      usage_color="${COLOR_WARN}"
    fi

    printf "  %-${W_MOUNT}s ${DIM}│${RESET} %-${W_SIZE}s ${DIM}│${RESET} %-${W_USED}s ${DIM}│${RESET} %-${W_AVAIL}s ${DIM}│${RESET} ${usage_color}%-${W_USAGE}s${RESET}\n" \
      "$mount_cell" "$total_cell" "$used_cell" "$avail_cell" "$usage_cell"
  done

  echo ""
  printf "  ${COLOR_MUTED}Press any key to return to menu...${RESET}"
  read -rsn1
  echo ""
}

check_memory() {
  section "Memory Usage"

  spin "Gathering memory information" 2

  echo ""

  local mem_info=$(free -h)
  local total=$(echo "$mem_info" | grep Mem | awk '{print $2}')
  local used=$(echo "$mem_info" | grep Mem | awk '{print $3}')
  local available=$(echo "$mem_info" | grep Mem | awk '{print $7}')
  local used_pct=$(echo "scale=1; $(echo "$mem_info" | grep Mem | awk '{print $3}' | sed 's/G//') / $(echo "$mem_info" | grep Mem | awk '{print $2}' | sed 's/G//') * 100" | bc 2>/dev/null || echo "0")

  # Table headers
  W_LABEL=16
  W_VALUE=14

  printf "  ${BOLD}%-${W_LABEL}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_VALUE}s${RESET}\n" \
    "Metric" "Value"

  hr "${DIM}" "─" "┼" $W_LABEL $W_VALUE

  # Total Memory
  local label_cell=$(trunc "Total Memory" "$W_LABEL")
  local value_cell=$(trunc "$total" "$W_VALUE")
  printf "  %-${W_LABEL}s ${DIM}│${RESET} %-${W_VALUE}s\n" \
    "$label_cell" "$value_cell"

  # Used Memory
  label_cell=$(trunc "Used" "$W_LABEL")
  value_cell=$(trunc "$used" "$W_VALUE")
  printf "  %-${W_LABEL}s ${DIM}│${RESET} ${COLOR_WARN}%-${W_VALUE}s${RESET}\n" \
    "$label_cell" "$value_cell"

  # Available Memory
  label_cell=$(trunc "Available" "$W_LABEL")
  value_cell=$(trunc "$available" "$W_VALUE")
  printf "  %-${W_LABEL}s ${DIM}│${RESET} ${COLOR_SUCCESS}%-${W_VALUE}s${RESET}\n" \
    "$label_cell" "$value_cell"

  # Usage Percentage
  label_cell=$(trunc "Usage %" "$W_LABEL")
  value_cell=$(trunc "${used_pct}%" "$W_VALUE")

  local pct_color="${COLOR_SUCCESS}"
  if (( ${used_pct%.*} >= 80 )); then
    pct_color="${COLOR_ERROR}"
  elif (( ${used_pct%.*} >= 60 )); then
    pct_color="${COLOR_WARN}"
  fi

  printf "  %-${W_LABEL}s ${DIM}│${RESET} ${pct_color}%-${W_VALUE}s${RESET}\n" \
    "$label_cell" "$value_cell"

  echo ""
  printf "  ${COLOR_MUTED}Press any key to return to menu...${RESET}"
  read -rsn1
  echo ""
}

check_network() {
  section "Network Connectivity"

  spin "Testing connection to google.com" 2

  echo ""

  if ping -c 1 -W 2 google.com &>/dev/null; then
    printf "  ${COLOR_SUCCESS}✓${RESET} Network connectivity to google.com is ${BOLD}OK${RESET}\n"
  else
    printf "  ${COLOR_ERROR}✗${RESET} Network connectivity to google.com is ${BOLD}FAILED${RESET}\n"
  fi

  echo ""
  printf "  ${COLOR_MUTED}Press any key to return to menu...${RESET}"
  read -rsn1
  echo ""
}

dispatch_action() {
  case "$1" in
    0) check_disk ;;
    1) check_memory ;;
    2) check_network ;;
    3) return 0 ;;
  esac
}

# ── Main Menu Loop ───────────────────────────────────────
main() {
  local QUIET=false
  for arg in "$@"; do
    case "$arg" in
      --quiet) QUIET=true ;;
      --help)
        echo ""
        printf "  ${BOLD}HEALTH-CHECK${RESET} — Server health monitoring tool\n\n"
        printf "  Usage:  bash %s [flags]\n\n" "$0"
        printf "  ${BOLD}Flags:${RESET}\n"
        printf "    --quiet      Suppress banner and animations\n"
        printf "    --help       Show this help\n\n"
        exit 0 ;;
    esac
  done

  $QUIET || splash

  local selected=0
  local max=3

  while true; do
    cls; hide_cur
    echo ""
    printf "  ${COLOR_TITLE}${BOLD}━━ Server Health Checker ━━${RESET}\n"
    printf "  ${COLOR_MUTED}Select a health check${RESET}\n\n"
    draw_menu $selected
    echo ""
    printf "  ${COLOR_MUTED}↑/↓ navigate  •  Enter select  •  q quit${RESET}"

    read -rsn1 key
    case "$key" in
      '')
        show_cur
        dispatch_action $selected
        if [[ $selected -eq 3 ]]; then
          break
        fi
        hide_cur
        ;;
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
        fi
        ;;
    esac
  done

  printf "\n  ${COLOR_MUTED}Goodbye.${RESET}\n\n"
}

main "$@"
