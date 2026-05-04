#!/usr/bin/env bash
# user-prompt-vault-reminder.sh — UserPromptSubmit hook for obsidian-bridge
#
# Reminds the user to link a vault, but ONLY when their message looks like
# vault-related work. Replaces the previous behavior of firing on every turn
# (which was noisy and ignored).
#
# Suppression rules (any one → silent exit):
#   1. .obsidian-bridge breadcrumb exists in $CLAUDE_PROJECT_DIR
#   2. .cabinet-anchor-hint exists (cabinet plugin can resolve a vault)
#   3. OB_DEFAULT_VAULT env var is set
#   4. The user's prompt contains no vault-related keywords
#   5. OB_REMINDER_DISABLE=1 env var is set (escape hatch)
#
# Otherwise: print the reminder once for this prompt.
set -euo pipefail

main() {
  # Escape hatch
  [ "${OB_REMINDER_DISABLE:-0}" = "1" ] && return 0

  local project_dir="${CLAUDE_PROJECT_DIR:-}"
  [ -z "$project_dir" ] && return 0

  # 1. Breadcrumb exists → vault is linked, no reminder needed
  [ -f "$project_dir/.obsidian-bridge" ] && return 0

  # 2. Cabinet anchor hint → vault discoverable via cabinet plugin
  [ -f "$project_dir/.cabinet-anchor-hint" ] && return 0

  # 3. Default vault env → vault discoverable via fallback
  [ -n "${OB_DEFAULT_VAULT:-}" ] && return 0

  # 4. Read the user's prompt from stdin (JSON payload)
  local input prompt=""
  input=$(cat 2>/dev/null || true)
  if [ -n "$input" ]; then
    if command -v python3 >/dev/null 2>&1; then
      prompt=$(printf '%s' "$input" | python3 -c 'import json,sys
try:
  print(json.load(sys.stdin).get("prompt",""))
except Exception:
  pass' 2>/dev/null || true)
    elif command -v jq >/dev/null 2>&1; then
      prompt=$(printf '%s' "$input" | jq -r '.prompt // empty' 2>/dev/null || true)
    fi
  fi

  # If we could not parse a prompt, fall back to the old "always fire"
  # behavior so we don't silently swallow the reminder when stdin is empty.
  if [ -z "$prompt" ]; then
    printf 'No vault linked. Run /vault-bridge connect or /vault-bridge create before vault-dependent work.'
    return 0
  fi

  # 5. Keyword-gate: only fire on vault-related signals
  # Conservative regex — false positive = one harmless extra reminder.
  local pattern='vault|obsidian|frontmatter|wiki[ -]?link|/vault-bridge|/dream|#ob/|_handoff\.md|_index\.md|brief\.md|\.base\b'
  if printf '%s' "$prompt" | grep -qiE "$pattern"; then
    printf 'No vault linked. Run /vault-bridge connect or /vault-bridge create before vault-dependent work.'
  fi
}

main "$@"
