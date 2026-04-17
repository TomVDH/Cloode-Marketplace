#!/usr/bin/env bash
# save-anchor.sh — PreCompact hook
# Backs up the anchor and updates the hooks counters before context compaction.
# Emits one chatter line to stdout. Silent exit 0 on any failure.
set -euo pipefail

main() {
  local project_dir="${CLAUDE_PROJECT_DIR:-}"
  [ -z "$project_dir" ] && return 0

  # Resolve anchor path via breadcrumb or env override
  local anchor_path="${CABINET_ANCHOR_PATH:-}"
  if [ -z "$anchor_path" ]; then
    local hint_file="$project_dir/.cabinet-anchor-hint"
    local vault="" slug=""
    if [ -f "$hint_file" ]; then
      vault=$(grep -E '^vault=' "$hint_file" 2>/dev/null | head -n1 | cut -d= -f2- || true)
      slug=$(grep -E '^slug=' "$hint_file" 2>/dev/null | head -n1 | cut -d= -f2- || true)
    fi
    if [ -n "$vault" ] && [ -n "$slug" ]; then
      anchor_path="$vault/projects/$slug/.anchor.json"
    fi
  fi

  [ -z "$anchor_path" ] && return 0
  [ -f "$anchor_path" ] || return 0

  # 1. Pre-compact backup
  cp "$anchor_path" "$anchor_path.pre-compact.bak" 2>/dev/null || true

  # 2. Bump counters
  local now_iso
  now_iso=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  if command -v jq >/dev/null 2>&1; then
    local tmp
    tmp=$(mktemp)
    jq --arg ts "$now_iso" '
      .hooks = (.hooks // {}) |
      .hooks.compaction_saves = (((.hooks.compaction_saves // 0) | tonumber) + 1) |
      .hooks.last_pulse_sync = $ts
    ' "$anchor_path" > "$tmp" 2>/dev/null && mv "$tmp" "$anchor_path" || rm -f "$tmp"
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$anchor_path" "$now_iso" <<'PY' 2>/dev/null || true
import json, sys
path, ts = sys.argv[1], sys.argv[2]
try:
    with open(path) as f:
        data = json.load(f)
except Exception:
    sys.exit(0)
hooks = data.get("hooks") or {}
hooks["compaction_saves"] = int(hooks.get("compaction_saves", 0)) + 1
hooks["last_pulse_sync"] = ts
data["hooks"] = hooks
try:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
except Exception:
    pass
PY
  fi

  printf '[Kevijntje]: Compressing — holding the anchor.\n'
  return 0
}

main "$@" 2>/dev/null || true
exit 0
