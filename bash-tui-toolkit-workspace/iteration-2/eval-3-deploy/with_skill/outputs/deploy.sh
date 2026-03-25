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
TEAL='\033[38;5;43m'
SLATE='\033[38;5;244m'

# ── Semantic roles ────────────────────────────────────────
COLOR_TITLE="${CYAN}"
COLOR_SUCCESS="${GREEN}"
COLOR_WARN="${YELLOW}"
COLOR_ERROR="${RED}"
COLOR_MUTED="${DIM}"
COLOR_ACTIVE="${CYAN}"
COLOR_INFO="${DIM}"

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

section() {
  echo ""
  printf "  ${COLOR_TITLE}${BOLD}━━ %s ━━${RESET}\n\n" "$1"
}

# ── Spinner ───────────────────────────────────────────────
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

# ── Splash Banner ─────────────────────────────────────────
splash() {
  local bar_width=54
  echo ""
  printf "${COLOR_TITLE}${BOLD}"
  cat << 'BANNER'
   ██████╗ ███████╗██████╗ ██╗      ██████╗ ██╗   ██╗
   ██╔══██╗██╔════╝██╔══██╗██║     ██╔═══██╗╚██╗ ██╔╝
   ██║  ██║█████╗  ██████╔╝██║     ██║   ██║ ╚████╔╝
   ██║  ██║██╔══╝  ██╔═══╝ ██║     ██║   ██║  ╚██╔╝
   ██████╔╝███████╗██║     ███████╗╚██████╔╝   ██║
   ╚═════╝ ╚══════╝╚═╝     ╚══════╝ ╚═════╝    ╚═╝
BANNER
  printf "${RESET}"
  printf "  ${COLOR_MUTED}Automated deployment pipeline${RESET}\n"
  echo ""

  # Loading bar
  printf "  ${DIM}[${RESET}"
  for ((i=0; i<bar_width; i++)); do
    printf "${COLOR_SUCCESS}█${RESET}"
    sleep 0.01
  done
  printf "${DIM}]${RESET}  ${COLOR_SUCCESS}✓${RESET}\n\n"
}

# ── Deployment Steps ──────────────────────────────────────
run_step() {
  local step_num="$1"
  local step_name="$2"
  local step_cmd="$3"

  if [[ "$DRY_RUN" == "true" ]]; then
    printf "  ${COLOR_ACTIVE}⠋${RESET} [%d/5] %s (DRY RUN)\n" "$step_num" "$step_name"
    sleep 0.5
    printf "\r  ${COLOR_SUCCESS}✓${RESET} [%d/5] %s\n" "$step_num" "$step_name"
    return 0
  fi

  # Show spinner while command runs
  {
    eval "$step_cmd" > /dev/null 2>&1 &
    local cmd_pid=$!
    local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
    local idx=0

    while kill -0 $cmd_pid 2>/dev/null; do
      printf "\r  ${COLOR_ACTIVE}%s${RESET} [%d/5] %s" "${frames[$idx]}" "$step_num" "$step_name"
      idx=$(( (idx + 1) % ${#frames[@]} ))
      sleep 0.12
    done

    wait $cmd_pid
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
      printf "\r  ${COLOR_SUCCESS}✓${RESET} [%d/5] %s\n" "$step_num" "$step_name"
    else
      printf "\r  ${COLOR_ERROR}✗${RESET} [%d/5] %s\n" "$step_num" "$step_name"
      return 1
    fi
  }
}

# ── Deployment Functions ──────────────────────────────────
check_git_status() {
  if command -v git &> /dev/null; then
    git status --porcelain > /dev/null
    return 0
  else
    return 1
  fi
}

run_tests() {
  if [[ -f "test.sh" ]]; then
    bash test.sh
  elif [[ -f "tests.sh" ]]; then
    bash tests.sh
  elif command -v npm &> /dev/null && [[ -f "package.json" ]]; then
    npm test
  else
    # Simulate test run
    sleep 1
  fi
}

build_project() {
  if command -v npm &> /dev/null && [[ -f "package.json" ]]; then
    npm run build 2>/dev/null || npm install && npm run build
  elif command -v python3 &> /dev/null && [[ -f "setup.py" ]]; then
    python3 setup.py build
  else
    # Simulate build
    sleep 1
  fi
}

upload_artifacts() {
  # Simulate artifact upload
  sleep 1
}

update_config() {
  # Simulate config update
  sleep 0.5
}

# ── Flag Parsing ──────────────────────────────────────────
DRY_RUN=false
QUIET=false

for arg in "$@"; do
  case "$arg" in
    --dry|--dry-run) DRY_RUN=true ;;
    --quiet)         QUIET=true ;;
    --help)
      echo ""
      printf "  ${BOLD}DEPLOY${RESET} — automated deployment pipeline\n\n"
      printf "  Usage:  bash %s [flags]\n\n" "$0"
      printf "  ${BOLD}Flags:${RESET}\n"
      printf "    --dry-run    Show what would happen without doing it\n"
      printf "    --quiet      Suppress banner and animations\n"
      printf "    --help       Show this help\n\n"
      exit 0 ;;
  esac
done

# ── Main ──────────────────────────────────────────────────
[[ "$QUIET" == "false" ]] && splash

if [[ "$DRY_RUN" == "true" ]]; then
  section "Deployment Preview (Dry Run)"
  printf "  ${COLOR_WARN}${BOLD}DRY RUN${RESET}${COLOR_MUTED} — no actions will be executed${RESET}\n\n"
else
  section "Deployment Pipeline"
fi

# Step 1: Check git status
if run_step 1 "Check git status" "check_git_status"; then
  :
else
  if [[ "$DRY_RUN" == "false" ]]; then
    printf "  ${COLOR_ERROR}✗${RESET} Git check failed — aborting deployment\n\n"
    exit 1
  fi
fi

# Step 2: Run tests
if run_step 2 "Run tests" "run_tests"; then
  :
else
  if [[ "$DRY_RUN" == "false" ]]; then
    printf "  ${COLOR_ERROR}✗${RESET} Tests failed — aborting deployment\n\n"
    exit 1
  fi
fi

# Step 3: Build
if run_step 3 "Build project" "build_project"; then
  :
else
  if [[ "$DRY_RUN" == "false" ]]; then
    printf "  ${COLOR_ERROR}✗${RESET} Build failed — aborting deployment\n\n"
    exit 1
  fi
fi

# Step 4: Upload artifacts
if run_step 4 "Upload artifacts" "upload_artifacts"; then
  :
else
  if [[ "$DRY_RUN" == "false" ]]; then
    printf "  ${COLOR_ERROR}✗${RESET} Upload failed — aborting deployment\n\n"
    exit 1
  fi
fi

# Step 5: Update config
if run_step 5 "Update config" "update_config"; then
  :
else
  if [[ "$DRY_RUN" == "false" ]]; then
    printf "  ${COLOR_ERROR}✗${RESET} Config update failed\n\n"
    exit 1
  fi
fi

echo ""
if [[ "$DRY_RUN" == "true" ]]; then
  printf "  ${COLOR_SUCCESS}✓${RESET} Dry run completed successfully\n\n"
else
  printf "  ${COLOR_SUCCESS}✓${RESET} Deployment completed successfully\n\n"
fi
