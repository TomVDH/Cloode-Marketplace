#!/usr/bin/env bash
# session-close.sh — SessionEnd hook
# Marks the anchor as interrupted if it wasn't formally wrapped,
# and emits a single farewell line from a random crew member.
# Silent exit 0 on any failure.
set -euo pipefail

main() {
  local project_dir="${CLAUDE_PROJECT_DIR:-}"
  local anchor_path=""

  if [ -n "$project_dir" ]; then
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

  if [ -n "$anchor_path" ] && [ -f "$anchor_path" ]; then
    local now_iso
    now_iso=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    if command -v jq >/dev/null 2>&1; then
      local tmp
      tmp=$(mktemp)
      jq --arg ts "$now_iso" '
        if (.status // "") != "wrapped" then
          .status = "interrupted" | .ended_at = $ts
        else . end
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
if data.get("status") != "wrapped":
    data["status"] = "interrupted"
    data["ended_at"] = ts
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
PY
    fi
  fi

  # Pick random crew member from character YAMLs
  local chars_dir="${CLAUDE_PLUGIN_ROOT:-}/references/characters"
  local name="Kevijntje"
  if [ -d "$chars_dir" ]; then
    local picked
    picked=$(find "$chars_dir" -maxdepth 1 -name '*.yaml' -type f 2>/dev/null \
      | awk -F/ '{print $NF}' \
      | sed 's/\.yaml$//' \
      | awk 'BEGIN{srand()} {lines[NR]=$0} END{ if (NR>0) print lines[int(rand()*NR)+1] }')
    if [ -n "$picked" ]; then
      # capitalise first letter
      name="$(echo "$picked" | awk '{ print toupper(substr($0,1,1)) substr($0,2) }')"
    fi
  fi

  printf '[%s]: tot straks.\n' "$name"
  return 0
}

main "$@" 2>/dev/null || true
exit 0
