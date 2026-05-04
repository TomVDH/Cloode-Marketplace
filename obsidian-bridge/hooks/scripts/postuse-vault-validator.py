#!/usr/bin/env python3
"""
postuse-vault-validator.py — PostToolUse hook for obsidian-bridge.

Fires after Write/Edit/MultiEdit. If the target file is a `.md` inside the
linked vault, applies universal frontmatter rules from the
`obsidian-bridge:vault-standards` skill:

Auto-fix (rewrites the file in place):
- Bump existing `updated:` field to today's ISO date when an Edit changes
  the file (Write doesn't auto-bump — Write means "first creation" intent).

Warnings (printed to stdout, shown to model — does NOT block):
- File has no YAML frontmatter
- Frontmatter missing required `type:` field
- Frontmatter `tags:` missing or has no `ob/{type}` structural tag
- Body contains `[text](path)` markdown links to other vault files
  (vault convention is wikilinks: `[[...]]`)

Silent if:
- Tool is not Write/Edit/MultiEdit
- Target is not a `.md` file
- No `.obsidian-bridge` breadcrumb (vault not linked)
- Target is not inside the linked vault
- OB_VALIDATOR_DISABLE=1 env (escape hatch)

Type-specific schema enforcement (per-file-type required fields) is
deferred until vault-standards is exposed as schema-as-data, not free-form
markdown.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date


def find_anchor(project_dir: str) -> str:
    """Locate the obsidian-bridge anchor file. Prefer the current
    convention (.claude/obsidian-bridge); fall back to the legacy
    location (.obsidian-bridge at project root)."""
    for candidate in (
        os.path.join(project_dir, ".claude", "obsidian-bridge"),
        os.path.join(project_dir, ".obsidian-bridge"),
    ):
        if os.path.isfile(candidate):
            return candidate
    return ""


def read_breadcrumb_vault(project_dir: str) -> str:
    """Return vault_path from the breadcrumb, or empty string."""
    breadcrumb = find_anchor(project_dir)
    if not breadcrumb:
        return ""
    try:
        with open(breadcrumb, encoding="utf-8") as f:
            for line in f:
                if line.startswith("vault_path="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body) where frontmatter excludes the
    enclosing `---` lines. If no frontmatter, returns ('', original_text)."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return "", text
    # Find closing fence
    m = re.search(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def has_type_field(frontmatter: str) -> bool:
    return bool(re.search(r"^type\s*:", frontmatter, re.MULTILINE))


def has_ob_tag(frontmatter: str) -> bool:
    """True if any tag in `tags:` block starts with `ob/`."""
    # Inline list form: tags: [ob/note, foo]
    inline = re.search(r"^tags\s*:\s*\[([^\]]*)\]", frontmatter, re.MULTILINE)
    if inline and re.search(r"\bob/[\w-]+", inline.group(1)):
        return True
    # Block form: tags:\n  - ob/note
    block = re.search(
        r"^tags\s*:\s*\n((?:\s+-\s+.+\n?)+)", frontmatter, re.MULTILINE
    )
    if block and re.search(r"-\s+ob/[\w-]+", block.group(1)):
        return True
    return False


def find_markdown_links_to_vault_files(body: str) -> list[str]:
    """Return list of `[text](path.md)` matches that look like vault links.
    Excludes external URLs (http(s)://) and anchor-only links (#foo)."""
    out = []
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+\.md(?:#[^)]+)?)\)", body):
        target = m.group(2)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        out.append(m.group(0))
    return out


def bump_updated_field(text: str, today_iso: str) -> tuple[str, bool]:
    """If frontmatter has `updated:` field, rewrite its value to today_iso.
    Returns (new_text, did_change)."""
    fm, body = split_frontmatter(text)
    if not fm:
        return text, False
    pattern = re.compile(r"^(updated\s*:\s*).*$", re.MULTILINE)
    if not pattern.search(fm):
        return text, False
    new_fm, n = pattern.subn(rf"\g<1>{today_iso}", fm, count=1)
    if n == 0 or new_fm == fm:
        return text, False
    new_text = f"---\n{new_fm}\n---\n{body}"
    return new_text, True


def main() -> int:
    if os.environ.get("OB_VALIDATOR_DISABLE") == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path or not file_path.endswith(".md"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return 0

    vault_path = read_breadcrumb_vault(project_dir)
    if not vault_path:
        return 0
    # Normalize trailing slash for prefix check
    if not vault_path.endswith(os.sep):
        vault_path = vault_path + os.sep
    if not os.path.realpath(file_path).startswith(os.path.realpath(vault_path)):
        return 0

    if not os.path.isfile(file_path):
        return 0

    try:
        with open(file_path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return 0

    notes: list[str] = []
    actions: list[str] = []

    # Auto-fix: bump `updated:` on Edit/MultiEdit (not Write)
    if tool_name in ("Edit", "MultiEdit"):
        new_text, changed = bump_updated_field(text, date.today().isoformat())
        if changed:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_text)
                actions.append(f"bumped `updated:` to {date.today().isoformat()}")
                text = new_text
            except OSError:
                pass

    # Warnings
    fm, body = split_frontmatter(text)
    rel_path = file_path
    if file_path.startswith(vault_path):
        rel_path = file_path[len(vault_path):]

    if not fm:
        notes.append(f"no YAML frontmatter — vault rule: every vault file has frontmatter")
    else:
        if not has_type_field(fm):
            notes.append("missing required `type:` field in frontmatter")
        if not has_ob_tag(fm):
            notes.append("no `#ob/{type}` structural tag in `tags:`")

    bad_links = find_markdown_links_to_vault_files(body)
    if bad_links:
        sample = bad_links[0]
        more = f" (+{len(bad_links)-1} more)" if len(bad_links) > 1 else ""
        notes.append(
            f"markdown link `{sample}` inside vault — use `[[wikilink]]` form{more}"
        )

    if not notes and not actions:
        return 0

    print(f"[obsidian-bridge:vault-standards] {rel_path}")
    for a in actions:
        print(f"  ✓ auto-fix: {a}")
    for n in notes:
        print(f"  ⚠ {n}")
    print("  → see `obsidian-bridge:vault-standards` for the canonical schema.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
