#!/usr/bin/env bash
# session-start-vault.sh — SessionStart hook for obsidian-bridge
# Discovers vault, detects CLI, injects context. Never blocks startup.
set -euo pipefail

main() {
  local project_dir="${CLAUDE_PROJECT_DIR:-}"
  [ -z "$project_dir" ] && return 0

  local vault_path="" vault_name="" project_slug="" mode="" linked_at=""

  # --- 1. Read breadcrumb ---
  # Prefer .claude/obsidian-bridge (current convention); fall back to
  # .obsidian-bridge at project root (legacy, pre-migration).
  local breadcrumb=""
  for candidate in \
      "$project_dir/.claude/obsidian-bridge" \
      "$project_dir/.obsidian-bridge"; do
    if [ -f "$candidate" ]; then
      breadcrumb="$candidate"
      break
    fi
  done
  if [ -n "$breadcrumb" ]; then
    vault_path=$(grep -E '^vault_path=' "$breadcrumb" 2>/dev/null | head -n1 | cut -d= -f2- || true)
    vault_name=$(grep -E '^vault_name=' "$breadcrumb" 2>/dev/null | head -n1 | cut -d= -f2- || true)
    project_slug=$(grep -E '^project_slug=' "$breadcrumb" 2>/dev/null | head -n1 | cut -d= -f2- || true)
    mode=$(grep -E '^mode=' "$breadcrumb" 2>/dev/null | head -n1 | cut -d= -f2- || true)
  fi

  # --- 2. Fallback: cabinet anchor hint ---
  if [ -z "$vault_path" ]; then
    local hint_file="$project_dir/.cabinet-anchor-hint"
    if [ -f "$hint_file" ]; then
      vault_path=$(grep -E '^vault=' "$hint_file" 2>/dev/null | head -n1 | cut -d= -f2- || true)
      project_slug=$(grep -E '^slug=' "$hint_file" 2>/dev/null | head -n1 | cut -d= -f2- || true)
    fi
  fi

  # --- 3. Fallback: OB_DEFAULT_VAULT env var ---
  if [ -z "$vault_path" ] && [ -n "${OB_DEFAULT_VAULT:-}" ]; then
    vault_path="$OB_DEFAULT_VAULT"
    vault_name=$(basename "$vault_path")
  fi

  # --- 4. Fallback: walk parent dirs for Home.md ---
  if [ -z "$vault_path" ]; then
    local check_dir="$project_dir"
    local depth=0
    while [ "$depth" -lt 5 ] && [ "$check_dir" != "/" ]; do
      if [ -f "$check_dir/Home.md" ]; then
        if grep -qE '^type:\s*(vault-home|cabinet-home)' "$check_dir/Home.md" 2>/dev/null; then
          vault_path="$check_dir"
          vault_name=$(basename "$check_dir")
          break
        fi
      fi
      check_dir=$(dirname "$check_dir")
      depth=$((depth + 1))
    done
  fi

  # --- 5. Detect CLI ---
  local cli_available="no"
  local cli_version=""
  if command -v obsidian >/dev/null 2>&1; then
    cli_version=$(obsidian version 2>/dev/null || true)
    if [ -n "$cli_version" ]; then
      cli_available="yes"
      mode="${mode:-cli}"
    fi
  fi
  mode="${mode:-filesystem}"

  # --- 6. Read project type from brief if slug is known ---
  local project_type="" project_status=""
  if [ -n "$vault_path" ] && [ -n "$project_slug" ]; then
    local brief="$vault_path/projects/$project_slug/brief.md"
    if [ -f "$brief" ]; then
      project_type=$(grep -E '^project_type:\s*' "$brief" 2>/dev/null | head -n1 | sed 's/^project_type:\s*//' || true)
      project_status=$(grep -E '^status:\s*' "$brief" 2>/dev/null | head -n1 | sed 's/^status:\s*//' || true)
    fi
  fi

  # --- 7. Emit context ---
  if [ -n "$vault_path" ] && [ -d "$vault_path" ]; then
    # Vault linked — emit rich context
    local ctx="## Obsidian Bridge\n\n"
    ctx+="- Vault: \`${vault_name:-$(basename "$vault_path")}\` at \`$vault_path\` (CLI: $cli_available)\n"

    if [ -n "$project_slug" ]; then
      local type_info=""
      [ -n "$project_type" ] && type_info=" (type: $project_type)"
      local status_info=""
      [ -n "$project_status" ] && status_info=" — status: $project_status"
      ctx+="- Project: \`$project_slug\`$type_info$status_info\n"
      ctx+="\nDecisions: \`projects/$project_slug/decisions/YYYY-MM-DD-{slug}.md\`\n"
      ctx+="Sessions: \`projects/$project_slug/sessions/YYYY-MM-DD.md\`\n"
    else
      ctx+="- Project: not linked (run \`/vault-bridge link <slug>\` to set)\n"
    fi

    ctx+="Root docs require \`type: doc\` frontmatter.\n"
    ctx+="Standards: invoke the \`obsidian-bridge:vault-standards\` skill for the canonical schema."

    printf '%b' "$ctx"
  else
    # Vault not linked — emit steering context
    printf '## Obsidian Bridge — Not Linked\n\n'
    printf 'No vault linked to this session. Before vault-dependent work, ask the user\n'
    printf 'to run `/vault-bridge connect <path>` or `/vault-bridge create`. Do not\n'
    printf 'fabricate vault paths or invent a layout.'
  fi

  return 0
}

main "$@" 2>/dev/null || true
exit 0
