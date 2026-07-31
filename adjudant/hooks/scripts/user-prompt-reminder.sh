#!/usr/bin/env bash
# user-prompt-reminder.sh — UserPromptSubmit hook for adjudant
# Smart-fire vault reminder when project isn't vault-linked AND prompt mentions vault-y keywords.
# Fires at most ONCE per Claude Code session (marker keyed by session_id).
# Suppression: ADJUDANT_REMINDER_DISABLE=1 turns it off entirely.
set -euo pipefail

main() {
  [ "${ADJUDANT_REMINDER_DISABLE:-0}" = "1" ] && return 0

  local project_dir="${CLAUDE_PROJECT_DIR:-}"
  [ -z "$project_dir" ] && return 0

  # Already linked → silent exit
  [ -f "$project_dir/.claude/adjudant" ] && return 0

  # Hook payloads arrive on stdin; when run manually (a TTY) there is nothing
  # to read — bail instead of blocking on cat until Ctrl-D.
  [ -t 0 ] && return 0

  # Read prompt + session id from stdin JSON
  local input prompt="" session_id=""
  input=$(cat 2>/dev/null || true)
  [ -z "$input" ] && return 0

  if command -v python3 >/dev/null 2>&1; then
    # One line out: "<session_id-or--> <prompt, newlines collapsed>"
    read -r session_id prompt <<< "$(printf '%s' "$input" | python3 -c 'import json,sys
try:
  d = json.load(sys.stdin)
  sid = str(d.get("session_id") or "-")
  prompt = str(d.get("prompt") or "").replace("\n", " ")
  print(sid, prompt)
except Exception:
  pass' 2>/dev/null || true)" || true
  fi
  [ -z "$prompt" ] && return 0

  # Once per session: after the first reminder, stay quiet for this session_id.
  local marker=""
  if [ -n "$session_id" ] && [ "$session_id" != "-" ]; then
    marker="${TMPDIR:-/tmp}/adjudant-reminder-${session_id}"
    [ -f "$marker" ] && return 0
  fi

  # Vault-y keywords → fire reminder. Distinctive words and phrase forms
  # only: bare `brief`/`decision` fired on everyday English like "give me a
  # brief summary" or "good decision" (finding 31) — precision over recall.
  if printf '%s' "$prompt" | grep -qiE '\b(vault|obsidian|handoff|note this|document this|put in vault|record (this|that)|the brief|(this|that) decision)\b'; then
    # Sweep markers from past sessions (they leaked one per session forever),
    # then write this session's. Both best-effort.
    find "${TMPDIR:-/tmp}" -maxdepth 1 -name 'adjudant-reminder-*' -mtime +1 -delete 2>/dev/null || true
    # brace group: silence stderr BEFORE the > open (unwritable TMPDIR)
    if [ -n "$marker" ]; then { : > "$marker"; } 2>/dev/null || true; fi
    printf '[adjudant] Vault not linked for this project. Run `/adjudant connect` to capture this work in the vault.\n'
  fi
}

main "$@" || exit 0
