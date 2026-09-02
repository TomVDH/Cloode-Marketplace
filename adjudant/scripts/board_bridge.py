#!/usr/bin/env python3
"""Adjudant board bridge: vault task notes to board.

The board is a view of `tasks/`. This script ensures the deck and its HTML
exist and match the notes on disk, and nothing else.

Until v3 it also replayed the session task ledger (hooks/scripts/task-ledger.py)
at session end: every id whose latest event was not `TaskCompleted` became
`tasks/{kebab-subject}.md`. Status changes other than completion fire no
events, so abandoned, superseded and merely renamed todos all qualified as
"survivors" and all became permanent vault notes. An id without a
`TaskCompleted` event is an unfinished harness todo, not a work item, and
treating it as one filled `tasks/` with cards nobody wrote. The replay is
gone; the ledger itself stays in $TMPDIR, where the statusline reads it.

CLI:
    python3 board_bridge.py --ensure-only [--project-dir PATH]

`render_task_note` stays: the advisor's `capture-task` verb writes a task note
on an explicit request, which is the supported way one gets created.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

from _vault_walk import VaultUnresolvableError, smart_project_dir
from board import ensure_board

TEMPLATE = Path(__file__).resolve().parent.parent / "skills" / "adjudant" / "templates" / "task.md"

# Inlined equivalent of templates/task.md, used only when the template file
# is unreadable (mid-sync clone): an explicit capture must not lose its note
# over a missing template.
_FALLBACK_TEMPLATE = """---
type: task
status: todo
category: ""
code: ""
related: []
note: ""
tags:
  - task
---

## Task

## Notes
"""

# Vault task filenames are strict ascii kebab ({kebab-title}.md per
# vault-standards §naming); 80 chars keeps sync-hostile paths off the table.
_KEBAB_MAX = 80


def kebab(subject: str) -> str:
    """`Fix the widget` -> `fix-the-widget`. Empty when nothing survives."""
    s = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")
    return s[:_KEBAB_MAX].rstrip("-")


def _strip_frontmatter_comments(text: str) -> str:
    """Drop `# guidance` comments inside the frontmatter block, full-line
    and trailing forms both.

    The template carries them for the human/model author; a mechanical
    writer must emit clean values (the minimal YAML parser keeps trailing
    comments on quoted-value lines like `code: ""  # ...`, which would then
    leak into card ids)."""
    lines = text.split("\n")
    closes = [i for i, ln in enumerate(lines[1:], 1) if ln.rstrip() == "---"]
    if not text.startswith("---") or not closes:
        return text
    out: list[str] = []
    for i, ln in enumerate(lines):
        if 0 < i < closes[0]:
            if ln.lstrip().startswith("#"):
                continue
            ln = re.sub(r"[ \t]+#.*$", "", ln)
        out.append(ln)
    return "\n".join(out)


def render_task_note(slug: str, description: str) -> str:
    """templates/task.md with {slug} filled and the description inserted
    into the ## Task section (left untouched when the description is empty,
    matching the template's own empty shape)."""
    try:
        text = TEMPLATE.read_text()
    except OSError:
        text = _FALLBACK_TEMPLATE
    text = _strip_frontmatter_comments(text).replace("{slug}", slug)
    desc = description.strip()
    if desc:
        marker = "## Task\n"
        idx = text.find(marker)
        if idx != -1:
            at = idx + len(marker)
            text = text[:at] + "\n" + desc + "\n" + text[at:]
    return text


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="board_bridge.py",
        description="Ensure the board deck and HTML exist and match tasks/.")
    p.add_argument("--ensure-only", action="store_true", required=True,
                   help="run board.ensure_board for the project (the only mode since v3)")
    p.add_argument("--project-dir", default=".",
                   help="project root (breadcrumb-resolved; default cwd)")
    args = p.parse_args(argv)

    try:
        project_dir, _vault_hint = smart_project_dir(args.project_dir)
    except VaultUnresolvableError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if not project_dir.is_dir():
        print(f"error: project not found: {project_dir} (run /adjudant connect first)", file=sys.stderr)
        return 1

    try:
        verdict = ensure_board(project_dir)
    except Exception as e:  # a broken template/deck must not traceback at hook time
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
