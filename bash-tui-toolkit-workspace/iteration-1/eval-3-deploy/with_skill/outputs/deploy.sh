#!/bin/bash

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Color Palette & Semantic Tokens
# ─────────────────────────────────────────────────────────────────────────────

RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
TEAL='\033[38;5;43m'
SLATE='\033[38;5;244m'

COLOR_TITLE="${CYAN}"
COLOR_SUCCESS="${GREEN}"
COLOR_ERROR="${RED}"
COLOR_WARN="${YELLOW}"
COLOR_MUTED="${DIM}"
COLOR_ACTIVE="${CYAN}"

# ─────────────────────────────────────────────────────────────────────────────
# Shared State
# ─────────────────────────────────────────────────────────────────────────────

DRY_RUN=false
QUIET=false

# ─────────────────────────────────────────────────────────────────────────────
# Terminal Utilities
# ─────────────────────────────────────────────────────────────────────────────

cls()      { printf "\033[2J\033[H"; }
hide_cur() { printf "\033[?25l"; }
show_cur() { printf "\033[?25h"; }

cleanup() {
  show_cur
  printf "${RESET}\n"
}

trap cleanup EXIT INT TERM

# ─────────────────────────────────────────────────────────────────────────────
# Flag Parsing
# ─────────────────────────────────────────────────────────────────────────────

parse_flags() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run|--dry)
        DRY_RUN=true
        shift
        ;;
      --quiet|-q)
        QUIET=true
        shift
        ;;
      *)
        shift
        ;;
    esac
  done
}

# ─────────────────────────────────────────────────────────────────────────────
# Spinner (Braille)
# ─────────────────────────────────────────────────────────────────────────────

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
  printf "\r\033[2K"  # Clear line
}

# ─────────────────────────────────────────────────────────────────────────────
# Status Markers
# ─────────────────────────────────────────────────────────────────────────────

success() {
  printf "  ${GREEN}✓${RESET} %s\n" "$1"
}

error() {
  printf "  ${RED}✗${RESET} %s\n" "$1"
}

# ─────────────────────────────────────────────────────────────────────────────
# Splash Banner
# ─────────────────────────────────────────────────────────────────────────────

splash() {
  $QUIET && return 0
  cls
  hide_cur
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
  printf "${RESET}\n"
  printf "  ${DIM}Automated deployment pipeline${RESET}\n"
  if $DRY_RUN; then
    printf "  ${COLOR_WARN}${BOLD}DRY RUN${RESET}${DIM} — no changes will be applied${RESET}\n"
  fi
  echo ""
  show_cur
}

# ─────────────────────────────────────────────────────────────────────────────
# Deployment Steps
# ─────────────────────────────────────────────────────────────────────────────

step_git_status() {
  printf "  Step 1: Check git status\n"
  hide_cur
  spin "Checking repository..." 2

  if $DRY_RUN; then
    success "Git status check (dry run)"
    show_cur
    printf "  ${DIM}(would check for uncommitted changes)${RESET}\n"
    return 0
  fi

  if git status --porcelain | grep -q .; then
    show_cur
    error "Uncommitted changes detected"
    printf "  ${DIM}Please commit or stash changes before deploying${RESET}\n"
    return 1
  fi

  success "Repository clean"
  show_cur
  return 0
}

step_run_tests() {
  printf "\n  Step 2: Run tests\n"
  hide_cur
  spin "Running test suite..." 3

  if $DRY_RUN; then
    success "Test suite (dry run)"
    show_cur
    printf "  ${DIM}(would run: npm test)${RESET}\n"
    return 0
  fi

  # Simulate test run with a progress animation
  local bar_width=54
  printf "\r  ${DIM}[${RESET}"
  for ((i=0; i<bar_width; i++)); do
    printf "${GREEN}█${RESET}"
    sleep 0.01
  done
  printf "${DIM}]${RESET}\n"

  success "All tests passed"
  show_cur
  return 0
}

step_build() {
  printf "\n  Step 3: Build application\n"
  hide_cur
  spin "Building project..." 3

  if $DRY_RUN; then
    success "Build process (dry run)"
    show_cur
    printf "  ${DIM}(would run: npm run build)${RESET}\n"
    return 0
  fi

  # Simulate build with progress
  local bar_width=54
  printf "\r  ${DIM}[${RESET}"
  for ((i=0; i<bar_width; i++)); do
    printf "${GREEN}█${RESET}"
    sleep 0.01
  done
  printf "${DIM}]${RESET}\n"

  success "Build completed successfully"
  show_cur
  printf "  ${DIM}Output: dist/bundle.js (2.4MB)${RESET}\n"
  return 0
}

step_upload_artifacts() {
  printf "\n  Step 4: Upload artifacts\n"
  hide_cur
  spin "Uploading to artifact repository..." 3

  if $DRY_RUN; then
    success "Artifact upload (dry run)"
    show_cur
    printf "  ${DIM}(would upload dist/ to S3)${RESET}\n"
    return 0
  fi

  # Simulate upload with progress
  local bar_width=54
  printf "\r  ${DIM}[${RESET}"
  for ((i=0; i<bar_width; i++)); do
    printf "${GREEN}█${RESET}"
    sleep 0.01
  done
  printf "${DIM}]${RESET}\n"

  success "Artifacts uploaded"
  show_cur
  printf "  ${DIM}URL: https://artifacts.example.com/v1.2.3/bundle.js${RESET}\n"
  return 0
}

step_update_config() {
  printf "\n  Step 5: Update deployment config\n"
  hide_cur
  spin "Updating configuration..." 2

  if $DRY_RUN; then
    success "Config update (dry run)"
    show_cur
    printf "  ${DIM}(would update production.yml)${RESET}\n"
    return 0
  fi

  success "Configuration updated"
  show_cur
  printf "  ${DIM}File: deployment/config/production.yml${RESET}\n"
  return 0
}

# ─────────────────────────────────────────────────────────────────────────────
# Main Deployment Sequence
# ─────────────────────────────────────────────────────────────────────────────

main() {
  parse_flags "$@"
  splash

  echo ""
  printf "  ${COLOR_TITLE}${BOLD}━━ Deployment Pipeline ━━${RESET}\n"
  echo ""

  local failed=0

  step_git_status || ((failed++))
  step_run_tests || ((failed++))
  step_build || ((failed++))
  step_upload_artifacts || ((failed++))
  step_update_config || ((failed++))

  echo ""
  if [[ $failed -eq 0 ]]; then
    printf "  ${GREEN}${BOLD}✓ All deployment steps completed${RESET}\n"
    if $DRY_RUN; then
      printf "  ${DIM}(dry run mode — no changes applied)${RESET}\n"
    fi
  else
    printf "  ${RED}${BOLD}✗ Deployment failed${RESET} (${failed} step(s) failed)\n"
    return 1
  fi
  echo ""
}

main "$@"
