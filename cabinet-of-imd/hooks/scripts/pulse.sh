#!/usr/bin/env bash
# pulse.sh — UserPromptSubmit hook
# Silent pulse tracker. Reads user prompt from stdin, increments counters
# in {vault}/crew/pulse.json for crew-name and running-joke mentions.
# No stdout. Silent exit 0 always.
set -euo pipefail

main() {
  local project_dir="${CLAUDE_PROJECT_DIR:-}"
  [ -z "$project_dir" ] && return 0

  # Slurp stdin
  local prompt
  prompt=$(cat || true)
  [ -z "$prompt" ] && return 0

  # Resolve vault path
  local hint_file="$project_dir/.cabinet-anchor-hint"
  local vault=""
  if [ -f "$hint_file" ]; then
    vault=$(grep -E '^vault=' "$hint_file" 2>/dev/null | head -n1 | cut -d= -f2- || true)
  fi
  [ -z "$vault" ] && return 0

  local pulse_path="$vault/crew/pulse.json"
  [ -f "$pulse_path" ] || return 0

  # Lowercase prompt for matching
  local lc_prompt
  lc_prompt=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')

  # Collect matched crew names
  local crew_hits=()
  local names=(thieuke sakke jonasty pitr henske bostrol kevijntje poekie)
  for n in "${names[@]}"; do
    # Whole-word match
    if echo "$lc_prompt" | grep -qE "(^|[^a-z])$n([^a-z]|$)"; then
      crew_hits+=("$n")
    fi
  done

  # Collect matched running jokes
  local joke_hits=()
  local jokes_file="${CLAUDE_PLUGIN_ROOT:-}/hooks/lib/running-jokes.txt"
  if [ -f "$jokes_file" ]; then
    while IFS= read -r kw; do
      [ -z "$kw" ] && continue
      local lc_kw
      lc_kw=$(echo "$kw" | tr '[:upper:]' '[:lower:]')
      if echo "$lc_prompt" | grep -qF "$lc_kw"; then
        joke_hits+=("$kw")
      fi
    done < "$jokes_file"
  fi

  # No hits? done.
  if [ ${#crew_hits[@]} -eq 0 ] && [ ${#joke_hits[@]} -eq 0 ]; then
    return 0
  fi

  local now_iso
  now_iso=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Update pulse.json atomically
  if command -v jq >/dev/null 2>&1; then
    local crew_json joke_json tmp
    crew_json=$(printf '%s\n' "${crew_hits[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]')
    joke_json=$(printf '%s\n' "${joke_hits[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]')
    tmp=$(mktemp)
    jq --argjson crew "$crew_json" --argjson jokes "$joke_json" --arg ts "$now_iso" '
      .invocations = (.invocations // {}) |
      reduce $crew[] as $n (.; .invocations[$n] = (((.invocations[$n] // 0) | tonumber) + 1)) |
      .running_jokes = (.running_jokes // {}) |
      reduce $jokes[] as $j (.; .running_jokes[$j] = (((.running_jokes[$j] // 0) | tonumber) + 1)) |
      .last_updated = $ts
    ' "$pulse_path" > "$tmp" 2>/dev/null && mv "$tmp" "$pulse_path" || rm -f "$tmp"
  elif command -v python3 >/dev/null 2>&1; then
    # Export hits into env for python
    CREW_HITS=$(IFS=,; echo "${crew_hits[*]:-}") \
    JOKE_HITS=$(IFS=$'\x1f'; echo "${joke_hits[*]:-}") \
    TS="$now_iso" \
    python3 - "$pulse_path" <<'PY' 2>/dev/null || true
import json, os, sys, tempfile
path = sys.argv[1]
try:
    with open(path) as f:
        data = json.load(f)
except Exception:
    sys.exit(0)
invocations = data.get("invocations") or {}
for n in [x for x in os.environ.get("CREW_HITS","").split(",") if x]:
    invocations[n] = int(invocations.get(n, 0)) + 1
running = data.get("running_jokes") or {}
for j in [x for x in os.environ.get("JOKE_HITS","").split("\x1f") if x]:
    running[j] = int(running.get(j, 0)) + 1
data["invocations"] = invocations
data["running_jokes"] = running
data["last_updated"] = os.environ.get("TS")
try:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)
except Exception:
    pass
PY
  fi

  return 0
}

main "$@" 2>/dev/null || true
exit 0
