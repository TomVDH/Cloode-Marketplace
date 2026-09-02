#!/usr/bin/env python3
"""Adjudant's one reach outside the vault: is AGENTS.md still true?

AGENTS.md is canonical and harness-agnostic, CLAUDE.md imports it, GEMINI.md
does the same for agy, and the vault contains none of them. It is the first
thing every agent reads, and nothing keeps it current.

One project's AGENTS.md carries five false statements: traps about a module
deleted on 2026-08-23, and a rule described as "enforced mechanically" by a
script that does not exist. Three of the five are detectable without adjudant
knowing anything about the project, because they name things that are not
there. This repo's own AGENTS.md is not exempt from the same drift — it is
read exactly as written here, on every run, so a stale claim about this repo
would show up the same way a stale claim about any other project does.

Two checks, both read-only. No frontmatter is added and nothing is rewritten:
the file belongs to the person who wrote it, and a context file adjudant
edits is a context file nobody trusts.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

# A context file unchanged across this many commits has stopped describing the
# code it sits beside. Reported, never enforced.
AGENTS_STALE_COMMITS = 30

# Extensions that make a bare filename a path even with no slash in it.
_PATH_EXTS = (
    ".py", ".sh", ".md", ".json", ".yaml", ".yml", ".toml", ".txt",
    ".js", ".ts", ".html", ".css", ".cfg", ".ini", ".lock",
)

# Characters that mark a token as a pattern, a variable or a placeholder
# rather than a path on this disk.
_NOT_A_PATH = set("<>{}*?|$\"'()[]")

_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_FENCE_RE = re.compile(r"^\s*```")


def _looks_like_a_path(token: str) -> bool:
    """True when a token names something that could exist on this disk."""
    t = token.strip().rstrip(".,;:").rstrip("/")
    if not t or t.startswith("-"):
        return False
    if "://" in t or t in (".", ".."):
        return False
    if any(c in _NOT_A_PATH for c in t):
        return False
    return "/" in t or t.endswith(_PATH_EXTS)


def _clean(token: str) -> str:
    return token.strip().rstrip(".,;:").rstrip("/")


def named_paths(text: str) -> list:
    """Every path-shaped token the text names, as `(line_number, token)`.

    Three sources, and only three, so prose is never mined for filenames:
      - an inline backtick span, taken whole so a path with spaces survives
      - a markdown link target
      - a line inside a fenced block, split on whitespace

    Duplicates on one line are reported once; the same token on two lines is
    reported twice, because both lines make the claim.
    """
    out: list = []
    in_fence = False
    for lineno, line in enumerate(text.split("\n"), start=1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        seen_on_line: set = set()
        candidates: list = []
        if in_fence:
            candidates.extend(line.split())
        else:
            candidates.extend(_BACKTICK_RE.findall(line))
            candidates.extend(_MD_LINK_RE.findall(line))
        for raw in candidates:
            if not _looks_like_a_path(raw):
                continue
            token = _clean(raw)
            if token in seen_on_line:
                continue
            seen_on_line.add(token)
            out.append((lineno, token))
    return out


def _git(code_root: Path, *args: str) -> Optional[str]:
    """One git call, or None. Never raises, never blocks longer than 5s."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(code_root), *args],
            capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def agents_reach(code_root: Path) -> dict:
    """Every path AGENTS.md names, checked, plus commits since it changed.

    `missing` holds the tokens that resolve to nothing. `commits_since_change`
    is None outside a git repository, which is a fact about the environment
    and not a finding.
    """
    agents = code_root / "AGENTS.md"
    try:
        text = agents.read_text(errors="replace")
    except OSError:
        return {"present": False, "missing": [], "checked": 0,
                "last_changed": None, "commits_since_change": None}

    missing: list = []
    tokens = named_paths(text)
    for lineno, token in tokens:
        candidate = Path(token).expanduser()
        if not candidate.is_absolute():
            candidate = code_root / candidate
        if candidate.exists():
            continue
        missing.append({"line": lineno, "token": token})

    last_sha = _git(code_root, "log", "-1", "--format=%H", "--", "AGENTS.md")
    last_changed = _git(code_root, "log", "-1", "--format=%cs", "--", "AGENTS.md")
    commits_since: Optional[int] = None
    if last_sha:
        counted = _git(code_root, "rev-list", "--count", f"{last_sha}..HEAD")
        if counted is not None:
            try:
                commits_since = int(counted)
            except ValueError:
                commits_since = None

    return {
        "present": True,
        "missing": missing,
        "checked": len(tokens),
        "last_changed": last_changed,
        "commits_since_change": commits_since,
    }
