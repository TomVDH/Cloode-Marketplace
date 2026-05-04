#!/usr/bin/env python3
"""
precompact-handoff-sync.py — PreCompact hook for obsidian-bridge.

Before context compaction, mirror `.remember/remember.md` into the linked
project's vault handoff at `{vault}/projects/{slug}/_handoff.md` so the
next session starts with the latest state in the vault — not lost in
the compacted context.

Operation:
- Read .obsidian-bridge breadcrumb → vault_path + project_slug.
- Read $CLAUDE_PROJECT_DIR/.remember/remember.md.
- Write _handoff.md with canonical frontmatter (type: handoff,
  project: piped wikilink, updated: today, source: remember,
  tags: [ob/handoff]) + remember body.
- If existing _handoff.md has body content predating any auto-import
  marker, preserve it above the marker. (Simple convention: everything
  below the line `<!-- BEGIN remember import -->` is overwritten;
  everything above is preserved.)

Silent if:
- No .obsidian-bridge breadcrumb (vault not linked)
- vault_path or project_slug missing in breadcrumb
- No .remember/remember.md to mirror
- OB_PRECOMPACT_DISABLE=1 env (escape hatch)

Output (when sync happens):
- One line confirming the file path written.
"""
from __future__ import annotations

import os
import sys
from datetime import date

REMEMBER_MARKER = "<!-- BEGIN remember import -->"


def read_breadcrumb_kv(project_dir: str) -> dict[str, str]:
    out: dict[str, str] = {}
    breadcrumb = os.path.join(project_dir, ".obsidian-bridge")
    if not os.path.isfile(breadcrumb):
        return out
    try:
        with open(breadcrumb, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def split_at_marker(text: str) -> tuple[str, str]:
    """Return (above_marker, below_marker_inclusive). If marker absent,
    treat whole text as above (preserve nothing below)."""
    if REMEMBER_MARKER not in text:
        return text, ""
    idx = text.index(REMEMBER_MARKER)
    return text[:idx], text[idx:]


def split_frontmatter(text: str) -> tuple[str, str]:
    if not (text.startswith("---\n") or text.startswith("---\r\n")):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[:end + 5], text[end + 5:]


def main() -> int:
    if os.environ.get("OB_PRECOMPACT_DISABLE") == "1":
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return 0

    kv = read_breadcrumb_kv(project_dir)
    vault_path = kv.get("vault_path", "")
    project_slug = kv.get("project_slug", "")
    if not vault_path or not project_slug:
        return 0

    remember_path = os.path.join(project_dir, ".remember", "remember.md")
    if not os.path.isfile(remember_path):
        return 0

    remember_body = read_text(remember_path).rstrip() + "\n"
    if not remember_body.strip():
        return 0

    handoff_path = os.path.join(
        vault_path, "projects", project_slug, "_handoff.md"
    )
    handoff_dir = os.path.dirname(handoff_path)
    try:
        os.makedirs(handoff_dir, exist_ok=True)
    except OSError:
        return 0

    today_iso = date.today().isoformat()
    new_frontmatter = (
        "---\n"
        "type: handoff\n"
        f'project: "[[projects/{project_slug}/brief|{project_slug}]]"\n'
        f"updated: {today_iso}\n"
        "source: remember\n"
        "tags:\n"
        "  - ob/handoff\n"
        "---\n"
    )

    # Preserve any human-edited content above the marker in existing handoff
    existing = read_text(handoff_path)
    if existing:
        _, existing_body = split_frontmatter(existing)
        above, _ = split_at_marker(existing_body)
        above = above.strip()
        preserved = (above + "\n\n") if above else ""
    else:
        preserved = ""

    new_body = (
        f"{preserved}"
        f"{REMEMBER_MARKER}\n"
        f"<!-- Auto-imported from .remember/remember.md at PreCompact, {today_iso}. "
        f"Edits below this marker are overwritten on the next compaction. -->\n\n"
        f"{remember_body}"
    )

    out = new_frontmatter + "\n" + new_body
    try:
        with open(handoff_path, "w", encoding="utf-8") as f:
            f.write(out)
    except OSError as e:
        print(f"[obsidian-bridge:precompact] failed to write {handoff_path}: {e}")
        return 0

    rel = os.path.relpath(handoff_path, vault_path)
    print(
        f"[obsidian-bridge:precompact] synced .remember/remember.md → {rel} "
        f"(updated: {today_iso})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
