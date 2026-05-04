#!/usr/bin/env bash
# session-end-handoff.sh — SessionEnd hook for obsidian-bridge
# Opt-in nudge: reminds user to sync remember handoff if stale.
# Enable via OB_SESSION_END_NUDGE=1 env var.
set -euo pipefail

main() {
  # Only run if opted in
  [ "${OB_SESSION_END_NUDGE:-0}" = "1" ] || return 0

  local project_dir="${CLAUDE_PROJECT_DIR:-}"
  [ -z "$project_dir" ] && return 0

  # Canonical anchor only — legacy auto-migrated by SessionStart step 0
  local breadcrumb="$project_dir/.claude/obsidian-bridge"
  [ -f "$breadcrumb" ] || return 0

  local vault_path="" project_slug=""
  vault_path=$(grep -E '^vault_path=' "$breadcrumb" 2>/dev/null | head -n1 | cut -d= -f2- || true)
  project_slug=$(grep -E '^project_slug=' "$breadcrumb" 2>/dev/null | head -n1 | cut -d= -f2- || true)

  [ -z "$vault_path" ] && return 0
  [ -z "$project_slug" ] && return 0

  local remember_file="$project_dir/.remember/remember.md"
  local handoff_file="$vault_path/projects/$project_slug/_handoff.md"

  # Only nudge if remember.md exists
  [ -f "$remember_file" ] || return 0

  # Compare mtimes
  if [ -f "$handoff_file" ]; then
    local remember_mtime handoff_mtime
    # macOS stat
    remember_mtime=$(stat -f %m "$remember_file" 2>/dev/null || stat -c %Y "$remember_file" 2>/dev/null || echo 0)
    handoff_mtime=$(stat -f %m "$handoff_file" 2>/dev/null || stat -c %Y "$handoff_file" 2>/dev/null || echo 0)
    if [ "$remember_mtime" -gt "$handoff_mtime" ]; then
      printf 'remember.md updated since last handoff — run /sync handoff to mirror.'
    fi
  else
    printf 'remember.md exists but no vault handoff yet — run /sync handoff to mirror.'
  fi

  return 0
}

main "$@" 2>/dev/null || true
exit 0
