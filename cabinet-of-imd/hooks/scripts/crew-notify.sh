#!/usr/bin/env bash
# crew-notify.sh — Notification hook
# Rewrites generic Claude Code notifications in crew voice.
# Reads stdin, emits rewritten text on stdout. Falls through on unknown patterns.
set -euo pipefail

main() {
  local msg
  msg=$(cat || true)

  # Lowercase for matching but preserve original as fallback
  local lc
  lc=$(echo "$msg" | tr '[:upper:]' '[:lower:]')

  if echo "$lc" | grep -qE 'waiting for input|needs your input'; then
    printf '[Kevijntje]: Tom? You there?\n'
    return 0
  fi

  if echo "$lc" | grep -q 'waiting for permission'; then
    printf '[Poekie]: Tom, we need your nod on this one.\n'
    return 0
  fi

  if echo "$lc" | grep -q 'idle'; then
    printf '[Thieuke]: Still here when you'\''re ready.\n'
    return 0
  fi

  # Fall through unchanged
  printf '%s' "$msg"
  return 0
}

main "$@" 2>/dev/null || cat
exit 0
