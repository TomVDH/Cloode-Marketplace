#!/usr/bin/env bash
# boot-flair.sh — SessionStart hook
# Emits up to 3 short flair lines for the crew based on vault history.
# Silently exits 0 on any error. Must never block Claude Code startup.
set -euo pipefail

# Everything is wrapped so any unexpected failure exits 0.
main() {
  local project_dir="${CLAUDE_PROJECT_DIR:-}"
  [ -z "$project_dir" ] && return 0

  # --- Resolve anchor path via breadcrumb ---
  # Preferred: a hint file in the project root telling us which vault/project slug we belong to.
  local hint_file="$project_dir/.cabinet-anchor-hint"
  local vault="" slug="" anchor_path=""

  if [ -f "$hint_file" ]; then
    # Hint file format (simple KEY=VALUE lines):
    #   vault=/absolute/path/to/Claude Cabinet
    #   slug=dashboard-v2
    vault=$(grep -E '^vault=' "$hint_file" 2>/dev/null | head -n1 | cut -d= -f2- || true)
    slug=$(grep -E '^slug=' "$hint_file" 2>/dev/null | head -n1 | cut -d= -f2- || true)
  fi

  # Fallback: look one level above the project dir for a cabinet vault marker.
  if [ -z "$vault" ] && [ -d "$project_dir/.." ]; then
    local parent
    parent=$(cd "$project_dir/.." 2>/dev/null && pwd || true)
    if [ -n "$parent" ] && [ -f "$parent/Home.md" ] && grep -q "type: cabinet-home" "$parent/Home.md" 2>/dev/null; then
      vault="$parent"
    fi
  fi

  [ -z "$vault" ] && return 0
  [ -z "$slug" ] && return 0

  anchor_path="$vault/projects/$slug/.anchor.json"
  [ -f "$anchor_path" ] || return 0

  local today_md today_year
  today_md=$(date +%m-%d)
  today_year=$(date +%Y)

  # --- 1. Historical question — first unchecked 30+ days old ---
  local q_file="$vault/crew/scrapbook/questions.md"
  if [ -f "$q_file" ]; then
    local picked_question=""
    # Loop unchecked items, find one with last_asked >= 30 days ago OR "never"
    while IFS= read -r line; do
      # Expected: - [ ] last_asked: YYYY-MM-DD — question text
      # or     : - [ ] last_asked: never — question text
      if [[ "$line" =~ ^-\ \[\ \]\ last_asked:\ ([0-9-]+|never)\ +—\ +(.+)$ ]]; then
        local la="${BASH_REMATCH[1]}"
        local qt="${BASH_REMATCH[2]}"
        local eligible=0
        if [ "$la" = "never" ]; then
          eligible=1
        else
          # compute days between today and la (GNU/BSD date compatible-ish; best-effort)
          local la_epoch now_epoch diff_days
          la_epoch=$(date -j -f "%Y-%m-%d" "$la" +%s 2>/dev/null || date -d "$la" +%s 2>/dev/null || echo "")
          now_epoch=$(date +%s)
          if [ -n "$la_epoch" ]; then
            diff_days=$(( (now_epoch - la_epoch) / 86400 ))
            [ "$diff_days" -ge 30 ] && eligible=1
          fi
        fi
        if [ "$eligible" -eq 1 ]; then
          picked_question="$qt"
          break
        fi
      fi
    done < "$q_file"
    if [ -n "$picked_question" ]; then
      printf '[cabinet-flair] Question for you: %s\n' "$picked_question"
    fi
  fi

  # --- 2. Anniversary — any brief.md with created: matching today's MM-DD in prior year ---
  if [ -d "$vault/projects" ]; then
    # shellcheck disable=SC2044
    for brief in "$vault"/projects/*/brief.md; do
      [ -f "$brief" ] || continue
      # Look for created: YYYY-MM-DD
      local created_line
      created_line=$(grep -E '^created:\s*[0-9]{4}-[0-9]{2}-[0-9]{2}' "$brief" 2>/dev/null | head -n1 || true)
      [ -z "$created_line" ] && continue
      local created_date
      created_date=$(echo "$created_line" | sed -E 's/^created:\s*([0-9-]+).*/\1/')
      local created_year created_md
      created_year=$(echo "$created_date" | cut -d- -f1)
      created_md=$(echo "$created_date" | cut -d- -f2-)
      if [ "$created_md" = "$today_md" ] && [ "$created_year" != "$today_year" ]; then
        local proj_slug
        proj_slug=$(basename "$(dirname "$brief")")
        printf '[cabinet-flair] Anniversary: %s was created on this day in %s.\n' "$proj_slug" "$created_year"
        break
      fi
    done
  fi

  # --- 3. Session count stats for current slug ---
  local sess_dir="$vault/projects/$slug/sessions"
  if [ -d "$sess_dir" ]; then
    local count
    count=$(find "$sess_dir" -maxdepth 1 -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    if [ -n "$count" ] && [ "$count" -gt 0 ]; then
      # Session #N means this will be the N+1-th, but spec says "#N on {slug}" using prior count.
      local nplus1=$((count + 1))
      printf '[cabinet-flair] Session #%s on %s.\n' "$nplus1" "$slug"
    fi
  fi

  return 0
}

main "$@" 2>/dev/null || true
exit 0
