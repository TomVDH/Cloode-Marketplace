#!/usr/bin/env bash
set -euo pipefail

# ── Cleanup ───────────────────────────────────────────────
cleanup() { show_cur; printf "${RESET}\n"; }
trap cleanup EXIT INT TERM

# ── Palette ───────────────────────────────────────────────
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'
SLATE='\033[38;5;244m'
TEAL='\033[38;5;43m'

# ── Semantic roles ─────────────────────────────────────
COLOR_TITLE="${CYAN}"
COLOR_SUCCESS="${GREEN}"
COLOR_WARN="${YELLOW}"
COLOR_ERROR="${RED}"
COLOR_MUTED="${DIM}"
COLOR_ACTIVE="${CYAN}"

# ── Terminal Control ──────────────────────────────────────
cls()      { printf "\033[2J\033[H"; }
hide_cur() { printf "\033[?25l"; }
show_cur() { printf "\033[?25h"; }

# ── Text Helpers ──────────────────────────────────────────
trunc() {
  local str="$1" max="$2"
  if (( ${#str} > max )); then
    printf "%s" "${str:0:$((max-1))}…"
  else
    printf "%-${max}s" "$str"
  fi
}

# ── Loading Bar (Comet Tail) ──────────────────────────────
block_run() {
  local count="$1" char="$2" out=""
  for ((i=0; i<count; i++)); do out="${out}${char}"; done
  printf "%s" "$out"
}

animate_comet_tail() {
  local total="$1" delay="$2"
  local steps=12
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

# ── Horizontal Rule Helper ────────────────────────────────
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

# ── Splash Banner ─────────────────────────────────────────
splash() {
  echo ""
  printf "${COLOR_TITLE}${BOLD}"
  cat << 'BANNER'
   ██████╗███████╗██╗   ██╗    ██╗    ██╗ █████╗ ████████╗ ██████╗██╗  ██╗███████╗██████╗
  ██╔════╝██╔════╝██║   ██║    ██║    ██║██╔══██╗╚══██╔══╝██╔════╝██║  ██║██╔════╝██╔══██╗
  ██║     ███████╗██║   ██║    ██║ █╗ ██║███████║   ██║   ██║     ███████║█████╗  ██████╔╝
  ██║     ╚════██║╚██╗ ██╔╝    ██║███╗██║██╔══██║   ██║   ██║     ██╔══██║██╔══╝  ██╔══██╗
  ╚██████╗███████║ ╚████╔╝     ╚███╔███╔╝██║  ██║   ██║   ╚██████╗██║  ██║███████╗██║  ██║
   ╚═════╝╚══════╝  ╚═══╝       ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
BANNER
  printf "${RESET}"
  printf "  ${COLOR_MUTED}Monitor CSV files in real-time with animated progress${RESET}\n"
  echo ""
}

# ── Core Functions ────────────────────────────────────────
count_csv_rows() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "0"
    return
  fi
  wc -l < "$file" 2>/dev/null || echo "0"
}

format_file_size() {
  local size="$1"
  if (( size < 1024 )); then
    printf "%d B" "$size"
  elif (( size < 1024 * 1024 )); then
    printf "%.1f KB" "$(echo "scale=1; $size / 1024" | bc 2>/dev/null || echo "$size")"
  else
    printf "%.1f MB" "$(echo "scale=1; $size / (1024 * 1024)" | bc 2>/dev/null || echo "$size")"
  fi
}

process_csv_file() {
  local csv_file="$1"
  local filename=$(basename "$csv_file")

  echo ""
  printf "  ${COLOR_ACTIVE}ℹ${RESET}  Processing ${BOLD}%s${RESET}\n" "$filename"
  echo ""

  # Animate counting rows
  animate_comet_tail 30 0.02

  # Count rows
  local row_count=$(count_csv_rows "$csv_file")

  # Get file size
  local file_size=$(stat --format=%s "$csv_file" 2>/dev/null || stat -f %z "$csv_file" 2>/dev/null || echo "0")

  echo ""
  printf "  ${COLOR_SUCCESS}✓${RESET} Counted ${BOLD}%s${RESET} rows\n" "$row_count"
  echo ""
}

display_summary_table() {
  local -n files_array=$1

  if (( ${#files_array[@]} == 0 )); then
    return
  fi

  echo ""
  printf "  ${COLOR_TITLE}${BOLD}━━ Summary ━━${RESET}\n\n"

  # Column widths
  W_FILENAME=28
  W_ROWS=12
  W_SIZE=12

  # Header
  printf "  ${BOLD}%-${W_FILENAME}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_ROWS}s${RESET} ${DIM}│${RESET} ${BOLD}%-${W_SIZE}s${RESET}\n" \
    "Filename" "Rows" "Size"

  # Separator
  hr "${DIM}" "─" "┼" $W_FILENAME $W_ROWS $W_SIZE

  # Data rows
  for csv_file in "${files_array[@]}"; do
    if [[ ! -f "$csv_file" ]]; then
      continue
    fi

    local filename=$(basename "$csv_file")
    local row_count=$(count_csv_rows "$csv_file")
    local file_size=$(stat --format=%s "$csv_file" 2>/dev/null || stat -f %z "$csv_file" 2>/dev/null || echo "0")
    local formatted_size=$(format_file_size "$file_size")

    local filename_cell=$(trunc "$filename" "$W_FILENAME")
    local rows_cell=$(trunc "$row_count" "$W_ROWS")
    local size_cell=$(trunc "$formatted_size" "$W_SIZE")

    printf "  %-${W_FILENAME}s ${DIM}│${RESET} ${COLOR_SUCCESS}%-${W_ROWS}s${RESET} ${DIM}│${RESET} ${SLATE}%-${W_SIZE}s${RESET}\n" \
      "$filename_cell" "$rows_cell" "$size_cell"
  done

  echo ""
}

# ── Main Watch Loop ───────────────────────────────────────
main() {
  # Flag parsing
  local target_dir="."
  for arg in "$@"; do
    case "$arg" in
      --help)
        echo ""
        printf "  ${BOLD}csv-watcher${RESET} — Monitor a directory for new CSV files\n\n"
        printf "  Usage:  bash %s [directory] [flags]\n\n" "$(basename "$0")"
        printf "  ${BOLD}Arguments:${RESET}\n"
        printf "    directory    Directory to watch (default: current directory)\n\n"
        printf "  ${BOLD}Flags:${RESET}\n"
        printf "    --help       Show this help\n\n"
        exit 0 ;;
      *)
        if [[ ! "$arg" =~ ^-- ]]; then
          target_dir="$arg"
        fi
        ;;
    esac
  done

  # Verify directory exists
  if [[ ! -d "$target_dir" ]]; then
    printf "  ${COLOR_ERROR}✗${RESET} Directory not found: ${BOLD}%s${RESET}\n\n" "$target_dir"
    exit 1
  fi

  cls; hide_cur
  splash

  printf "  ${COLOR_MUTED}Watching directory:${RESET} ${BOLD}%s${RESET}\n" "$target_dir"
  printf "  ${COLOR_MUTED}Press ${BOLD}Ctrl+C${COLOR_MUTED} to stop${RESET}\n"
  echo ""
  printf "  ${COLOR_ACTIVE}█${RESET} ${COLOR_MUTED}Scanning for CSV files...${RESET}\n"

  local -a processed_files
  local last_summary_time=0
  local summary_interval=5

  while true; do
    # Find all CSV files
    local -a current_files=()
    while IFS= read -r -d '' file; do
      current_files+=("$file")
    done < <(find "$target_dir" -maxdepth 1 -name "*.csv" -type f -print0 2>/dev/null)

    # Check for new files
    local new_found=false
    for csv_file in "${current_files[@]}"; do
      local found=false
      for pfile in "${processed_files[@]}"; do
        if [[ "$csv_file" == "$pfile" ]]; then
          found=true
          break
        fi
      done

      if [[ "$found" == false ]]; then
        new_found=true
        processed_files+=("$csv_file")
        process_csv_file "$csv_file"
      fi
    done

    # Display summary every N seconds
    local current_time=$(date +%s)
    if (( current_time - last_summary_time >= summary_interval )) && (( ${#processed_files[@]} > 0 )); then
      display_summary_table processed_files
      last_summary_time=$current_time
    fi

    # Brief pause before next scan
    sleep 1
  done
}

# ── Entry Point ───────────────────────────────────────────
main "$@"
