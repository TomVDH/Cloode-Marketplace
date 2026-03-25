#!/usr/bin/env bash
# csv-watcher.sh — Monitor a directory for new CSV files, count rows, display results

set -euo pipefail

# ── Palette ──────────────────────────────────────────────────────────────────
# Raw ANSI tokens
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
INVERT='\033[7m'

# Standard 16-color
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'

# Extended palette
TEAL='\033[38;5;43m'
SLATE='\033[38;5;244m'

# Semantic role tokens
COLOR_TITLE="${CYAN}"
COLOR_ACCENT="${TEAL}"
COLOR_TEXT="${WHITE}"
COLOR_MUTED="${DIM}"
COLOR_SUCCESS="${GREEN}"
COLOR_WARN="${YELLOW}"
COLOR_ERROR="${RED}"
COLOR_ACTIVE="${CYAN}"

# Bar-specific tokens
BAR_RAIL="${DIM}"
BAR_FILL="${GREEN}"
BAR_HEAD="${WHITE}"
BAR_PENDING="${DIM}"
BAR_DONE="${GREEN}"

# ── Terminal utilities ───────────────────────────────────────────────────────
cls() { printf "\033[2J\033[H"; }
hide_cur() { printf "\033[?25l"; }
show_cur() { printf "\033[?25h"; }

# ── Text helpers ─────────────────────────────────────────────────────────────
trunc() {
  local str="$1" max="$2"
  if (( ${#str} > max )); then
    printf "%s" "${str:0:$((max-1))}…"
  else
    printf "%-${max}s" "$str"
  fi
}

# ── Loading bar: animated multi-pass ─────────────────────────────────────────
loading_animated() {
  local bar_width=54 cycles=${1:-5} base_delay=0.025
  for ((c=1; c<=cycles; c++)); do
    local delay=$(python3 -c "print(max(0.005, ${base_delay} - (${c}-1)*0.005))")

    # Draw empty frame
    printf "\r  ${BAR_RAIL}[";
    for ((i=0; i<bar_width; i++)); do printf " "; done;
    printf "]${RESET}"

    # Fill
    printf "\r  ${BAR_RAIL}[${RESET}"
    for ((i=0; i<bar_width; i++)); do
      if ((c == cycles)); then
        printf "${BAR_FILL}█${RESET}"
      else
        printf "${COLOR_ACTIVE}█${RESET}"
      fi
      sleep "$delay"
    done

    # Flash reset between passes
    if ((c < cycles)); then
      printf "\r  ${BAR_RAIL}["
      for ((i=0; i<bar_width; i++)); do printf "${BAR_PENDING}░${RESET}"; done
      printf "${BAR_RAIL}]${RESET}"
      sleep 0.08
    fi
  done

  printf "\r  ${BAR_RAIL}[${RESET}"
  for ((i=0; i<bar_width; i++)); do printf "${BAR_FILL}█${RESET}"; done
  printf "${BAR_RAIL}]${RESET}  ${COLOR_SUCCESS}✓${RESET}\n\n"
}

# ── Comet tail loading animation ─────────────────────────────────────────────
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
    printf "${BAR_PENDING}%s${RESET}" "$(block_run "$trail" "░")"
    printf "${WHITE}%s${RESET}" "$(block_run "$trail" "▒")"
    printf "${WHITE}%s${RESET}" "$(block_run "$(( head_end - head_start ))" "█")"
    printf "%s" "$(block_run "$after" " ")"
    sleep "$delay"
  done
  printf "\r\033[2K"
}

# ── Breathing spinner ────────────────────────────────────────────────────────
breathe() {
  local label="${1:-Watching...}"
  local frames=("░" "▒" "▓" "█" "▓" "▒")
  local colours=("${COLOR_ACTIVE}" "${COLOR_ACTIVE}" "${COLOR_ACTIVE}" "${WHITE}" "${WHITE}" "${COLOR_ACTIVE}")
  local idx=0
  while true; do
    printf "\r  %s%s${RESET} ${COLOR_MUTED}%s${RESET}  " "${colours[$idx]}" "${frames[$idx]}" "$label"
    idx=$(( (idx + 1) % ${#frames[@]} ))
    sleep 0.2
  done
}

# ── Horizontal rule helper ───────────────────────────────────────────────────
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

# ── Format file size in human-readable form ──────────────────────────────────
format_size() {
  local bytes="$1"
  if (( bytes < 1024 )); then
    printf "%dB" "$bytes"
  elif (( bytes < 1024 * 1024 )); then
    printf "%.1fK" "$(echo "scale=1; $bytes / 1024" | bc)"
  else
    printf "%.1fM" "$(echo "scale=1; $bytes / 1024 / 1024" | bc)"
  fi
}

# ── Count CSV rows efficiently ───────────────────────────────────────────────
count_csv_rows() {
  local file="$1"
  # Count lines and subtract 1 for header (minimum 0 data rows)
  local line_count=$(wc -l < "$file" 2>/dev/null || echo "0")
  if (( line_count > 0 )); then
    echo $((line_count - 1))
  else
    echo "0"
  fi
}

# ── Display summary table ────────────────────────────────────────────────────
display_summary() {
  local -a files=("$@")

  if (( ${#files[@]} == 0 )); then
    return
  fi

  # Column widths
  W_NAME=28
  W_ROWS=12
  W_SIZE=10

  echo ""
  printf "  ${COLOR_TITLE}${BOLD}CSV Summary${RESET}\n"
  echo ""

  # Header row
  printf "  ${BOLD}%-${W_NAME}s${RESET} ${COLOR_MUTED}│${RESET} ${BOLD}%-${W_ROWS}s${RESET} ${COLOR_MUTED}│${RESET} ${BOLD}%-${W_SIZE}s${RESET}\n" \
    "Filename" "Row Count" "File Size"

  # Separator
  hr "${COLOR_MUTED}" "─" "┼" "$W_NAME" "$W_ROWS" "$W_SIZE"

  # Data rows
  for file in "${files[@]}"; do
    if [[ -f "$file" ]]; then
      local basename=$(basename "$file")
      local rows=$(count_csv_rows "$file")
      local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")
      local size_fmt=$(format_size "$size")

      name_cell=$(trunc "$basename" "$W_NAME")
      rows_cell=$(trunc "$rows" "$W_ROWS")
      size_cell=$(trunc "$size_fmt" "$W_SIZE")

      printf "  %-${W_NAME}s ${COLOR_MUTED}│${RESET} ${COLOR_SUCCESS}%-${W_ROWS}s${RESET} ${COLOR_MUTED}│${RESET} ${SLATE}%-${W_SIZE}s${RESET}\n" \
        "$name_cell" "$rows_cell" "$size_cell"
    fi
  done

  echo ""
}

# ── Cleanup trap ─────────────────────────────────────────────────────────────
cleanup() {
  show_cur
  printf "${RESET}\n"
}

trap cleanup EXIT INT TERM

# ── Main script ──────────────────────────────────────────────────────────────
main() {
  local watch_dir="${1:-.}"

  # Resolve to absolute path
  watch_dir=$(cd "$watch_dir" && pwd)

  cls
  hide_cur

  echo ""
  printf "  ${COLOR_TITLE}${BOLD}━━ CSV Watcher ━━${RESET}\n"
  printf "  ${COLOR_MUTED}Monitoring: %s${RESET}\n" "$watch_dir"
  echo ""
  printf "  ${COLOR_MUTED}Press Ctrl+C to stop watching${RESET}\n"
  echo ""

  # Track seen files to detect new ones
  declare -A seen_files
  declare -A displayed_files

  while true; do
    local new_files=()
    local all_csv_files=()

    # Find all CSV files in the directory
    while IFS= read -r file; do
      all_csv_files+=("$file")

      # Check if this is a new file
      if [[ -z "${seen_files[$file]:-}" ]]; then
        seen_files[$file]=1
        new_files+=("$file")
      fi
    done < <(find "$watch_dir" -maxdepth 1 -name "*.csv" -type f 2>/dev/null | sort)

    # Process new files found
    for file in "${new_files[@]}"; do
      local basename=$(basename "$file")

      echo ""
      printf "  ${COLOR_ACTIVE}ℹ${RESET}  ${COLOR_MUTED}Processing: %s${RESET}\n" "$basename"

      # Show loading animation while counting rows
      animate_comet_tail 54 "0.015"
      loading_animated 4
    done

    # Display the summary table with all discovered CSV files
    if (( ${#all_csv_files[@]} > 0 )); then
      display_summary "${all_csv_files[@]}"
      displayed_files=()
      for f in "${all_csv_files[@]}"; do
        displayed_files[$f]=1
      done
    fi

    # Sleep before checking again
    sleep 2
  done
}

# Run main with watch directory argument (default: current directory)
main "${1:-.}"
