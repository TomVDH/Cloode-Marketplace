#!/usr/bin/env bash
# banter-roll.sh — Stop hook
# Rolls 1-in-5. On win, scans the transcript for recent crew-voice lines,
# scores them, and appends the best 1-3 to {vault}/crew/best-lines.md.
# No stdout. Silent exit 0.
set -euo pipefail

main() {
  # Roll
  if [ $(( RANDOM % 5 )) -ne 0 ]; then
    return 0
  fi

  local project_dir="${CLAUDE_PROJECT_DIR:-}"
  [ -z "$project_dir" ] && return 0

  # Resolve vault + slug
  local hint_file="$project_dir/.cabinet-anchor-hint"
  local vault="" slug=""
  if [ -f "$hint_file" ]; then
    vault=$(grep -E '^vault=' "$hint_file" 2>/dev/null | head -n1 | cut -d= -f2- || true)
    slug=$(grep -E '^slug=' "$hint_file" 2>/dev/null | head -n1 | cut -d= -f2- || true)
  fi
  [ -z "$vault" ] && return 0
  [ -z "$slug" ] && slug="unknown"

  # Find transcript
  local transcript="${CLAUDE_TRANSCRIPT_PATH:-}"
  [ -z "$transcript" ] && return 0
  [ -f "$transcript" ] || return 0

  # Pull last ~400 lines (cheaper than whole file), then filter to crew-voice
  # matching `[Name]:` openings for the 8 full crew members.
  local names='Thieuke|Sakke|Jonasty|Pitr|Henske|Bostrol|Kevijntje|Poekie'

  # Candidates: last 20 matching lines
  local candidates
  candidates=$(tail -n 400 "$transcript" 2>/dev/null \
    | grep -E "^\[($names)\]:" 2>/dev/null \
    | tail -n 20 || true)

  [ -z "$candidates" ] && return 0

  # Filter + score in awk: length 15-120, no triple-backticks, score = word_count + punctuation_hits
  local scored
  scored=$(echo "$candidates" | awk '
    {
      line = $0
      if (index(line, "```") > 0) next
      if (length(line) < 15 || length(line) > 120) next
      # word count (crude)
      n = split(line, a, /[[:space:]]+/)
      # punctuation score
      p = gsub(/[.,!?;:—-]/, "&", line)
      score = n + p
      printf "%d\t%s\n", score, $0
    }
  ' 2>/dev/null | sort -rn -t$'\t' -k1,1 | head -n 3)

  [ -z "$scored" ] && return 0

  # Ensure target dir exists
  local best_file="$vault/crew/best-lines.md"
  mkdir -p "$(dirname "$best_file")" 2>/dev/null || true

  local today
  today=$(date +%Y-%m-%d)

  {
    printf '\n### %s — %s\n' "$today" "$slug"
    echo "$scored" | awk -F'\t' '{ print "- " $2 }'
  } >> "$best_file" 2>/dev/null || true

  return 0
}

main "$@" 2>/dev/null || true
exit 0
