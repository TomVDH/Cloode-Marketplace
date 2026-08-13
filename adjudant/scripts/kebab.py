#!/usr/bin/env python3
"""Adjudant kebab — put a name on a skewer.

The joke is the name. The work is real: kebab-case IS the vault's naming law
(vault-standards §4), and §4 admits most of it goes unchecked — "the rest are
on you". ramasse checks doc case, the decision date prefix, session filenames
and canvas/base names. Nothing checks the kebab-title portion of a note, a
task, a source, or a decision. This does.

Two modes, both cheap:

    python3 kebab.py <text...>                 -> the slug, for naming a file
    python3 kebab.py --scan [--project-dir P]  -> §4 title violations + fixes

READ-ONLY BY DESIGN. Renaming a file breaks every wikilink pointing at it,
and that repair (rename + rewrite the links + fix the index rows) is
ramasse's, with its preview and its backups. kebab tells you; it does not
reach for the knife.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vault_walk import (  # noqa: E402
    VaultUnresolvableError,
    smart_project_dir,
    walk_project,
)
from board_bridge import kebab as _bridge_kebab  # noqa: E402

# Types whose filename is `{kebab-title}.md` per §4. `doc` is deliberately
# absent: §4 wants docs UPPERCASE, and a kebab rule applied blindly would
# fight the standard it exists to serve.
KEBAB_TITLE_TYPES: frozenset[str] = frozenset({"note", "task", "source"})
# Decisions are `{YYYY-MM-DD}-{kebab-title}.md`: the date is ramasse's to
# check, the title is ours.
DATED_TITLE_TYPES: frozenset[str] = frozenset({"decision"})

# Written for you, or shaped by another rule entirely.
EXEMPT_NAMES: frozenset[str] = frozenset({
    "brief.md", "_handoff.md", "_index.md", "_iteration.md", "MEMORY.md"})
EXEMPT_FOLDERS: frozenset[str] = frozenset({
    "sessions", "dreams", "releases", "templates", "images", "assets",
    "previews", "iterations", "board", "bases", "canvases"})

DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-(.*))?$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(text: str) -> str:
    """`Fix the parser` -> `fix-the-parser`. Empty when nothing survives.

    Delegates to board_bridge.kebab so the plugin has ONE slug rule: a
    captured task and a hand-named note must agree about what the same title
    is called.
    """
    return _bridge_kebab(text)


def kebab_violations(project_dir: Path) -> list[dict[str, Any]]:
    """§4 title violations, newest rule first. Read-only."""
    out: list[dict[str, Any]] = []
    for vf in walk_project(project_dir):
        name = vf.rel_path.name
        if name in EXEMPT_NAMES or name.startswith("_"):
            continue
        if any(p in EXEMPT_FOLDERS for p in vf.rel_path.parts[:-1]):
            continue
        ftype = vf.file_type
        stem = name[:-3] if name.endswith(".md") else name

        if ftype in DATED_TITLE_TYPES:
            m = DATE_PREFIX_RE.match(stem)
            if not m or not m.group(2):
                continue          # the date shape is ramasse's finding, not ours
            date, title = m.group(1), m.group(2)
            if KEBAB_RE.match(title):
                continue
            fixed = slugify(title)
            if not fixed:
                continue
            out.append({"file": str(vf.rel_path), "type": ftype,
                        "suggested": f"{date}-{fixed}.md",
                        "issue": "decision title is not kebab-case (§4)"})
            continue

        if ftype not in KEBAB_TITLE_TYPES:
            continue
        if KEBAB_RE.match(stem):
            continue
        fixed = slugify(stem)
        if not fixed:
            continue
        out.append({"file": str(vf.rel_path), "type": ftype,
                    "suggested": f"{fixed}.md",
                    "issue": f"type:{ftype} filename is not kebab-case (§4)"})
    return out


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Slugify a title, or scan a project for §4 title drift")
    parser.add_argument("text", nargs="*", help="Text to slugify")
    parser.add_argument("--scan", action="store_true",
                        help="Report §4 kebab-title violations (read-only)")
    parser.add_argument("--project-dir", default=".",
                        help="Project root (default: cwd)")
    args = parser.parse_args(argv)

    if args.scan:
        try:
            project_dir, _ = smart_project_dir(args.project_dir)
        except VaultUnresolvableError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        if not project_dir.is_dir():
            print(f"error: project-dir not found: {project_dir}", file=sys.stderr)
            return 1
        violations = kebab_violations(project_dir)
        print(json.dumps({
            "project_dir": str(project_dir),
            "summary": {"violations": len(violations)},
            "violations": violations,
        }, indent=2))
        return 0

    if not args.text:
        print("error: give me some text to skewer, or --scan", file=sys.stderr)
        return 1
    slug = slugify(" ".join(args.text))
    if not slug:
        print("error: nothing survives slugification there; give it at least "
              "one letter or digit", file=sys.stderr)
        return 1
    print(slug)
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
