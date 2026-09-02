#!/usr/bin/env python3
"""Adjudant advisor — the v2 proactive layer's toggle and pulse.

The advisor itself is not code: it is a standing contract
(reference/advisor.md) the model follows when the mode is on. What needs
code is the STATE - visible, deliberate, in sync across its two surfaces:

  1. `advisor: on` in `.claude/adjudant` - machine-read by SessionStart
     (which then emits the awareness banner), synced across machines
     because the breadcrumb is repo-committed.
  2. A marker line in AGENTS.md - read into every session's context by the
     harness itself and by any human opening the repo. The mode is never
     a hidden setting someone has to remember exists.

This helper owns both, so they cannot drift apart. `pulse` (the
context-integrity check) rides the same file.

CLI:
    python3 advisor.py on      [--project-dir PATH]
    python3 advisor.py off     [--project-dir PATH]
    python3 advisor.py status  [--project-dir PATH]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vault_walk import (  # noqa: E402
    VaultUnresolvableError,
    atomic_write_text,
    file_lock,
    smart_project_dir,
    walk_project,
)
from _handoff_freshness import parse_next_line  # noqa: E402

# One line, greppable, self-documenting. `off` removes it entirely: a
# lingering marker would keep telling every session the advisor is watching
# when it is not.
AGENTS_MARKER_PREFIX = "**Adjudant advisor: on**"
AGENTS_MARKER = (
    f"{AGENTS_MARKER_PREFIX} — this project has opted into proactive "
    "observations (tasks, gaps, gaffes, stale context). Contract: the "
    "adjudant skill's `reference/advisor.md`. Toggle: `/adjudant advisor off`."
)

_KNOB_RE = re.compile(r"^advisor[:=][ \t]*\S+[ \t]*$", re.MULTILINE)


def _breadcrumb(project_dir: Path) -> Path:
    return project_dir / ".claude" / "adjudant"


def read_state(project_dir: Path) -> Optional[str]:
    """'on' | 'off' | None (no breadcrumb)."""
    bc = _breadcrumb(project_dir)
    try:
        text = bc.read_text()
    except OSError:
        return None
    m = re.search(r"^advisor[:=][ \t]*(\S+)", text, re.MULTILINE)
    if not m:
        return "off"
    return "on" if m.group(1).strip().lower() in ("on", "true", "1", "yes") else "off"


def _set_knob(project_dir: Path, state: str) -> None:
    """Set `advisor: <state>` in the breadcrumb, touching nothing else.

    Line-surgical for the same reason tidy's frontmatter edits are: the
    breadcrumb is repo-committed and hand-readable, and a wholesale rewrite
    would eat comments and keys this helper does not know about.
    """
    bc = _breadcrumb(project_dir)
    text = bc.read_text()
    line = f"advisor: {state}"
    if _KNOB_RE.search(text):
        new = _KNOB_RE.sub(line, text, count=1)
    else:
        new = text if text.endswith("\n") else text + "\n"
        new += line + "\n"
    with file_lock(bc):
        atomic_write_text(bc, new)


def _stamp_agents(project_dir: Path) -> bool:
    """Append the marker to AGENTS.md (idempotent). False when there is no
    AGENTS.md to stamp - the toggle still succeeds, degraded like every
    other ambient surface."""
    agents = project_dir / "AGENTS.md"
    if not agents.is_file():
        return False
    text = agents.read_text()
    if AGENTS_MARKER_PREFIX in text:
        return True
    new = text if text.endswith("\n") else text + "\n"
    new += "\n" + AGENTS_MARKER + "\n"
    with file_lock(agents):
        atomic_write_text(agents, new)
    return True


def _unstamp_agents(project_dir: Path) -> None:
    """Remove the marker line (and the blank line the stamp added)."""
    agents = project_dir / "AGENTS.md"
    if not agents.is_file():
        return
    text = agents.read_text()
    if AGENTS_MARKER_PREFIX not in text:
        return
    lines = [ln for ln in text.split("\n") if AGENTS_MARKER_PREFIX not in ln]
    new = "\n".join(lines)
    # collapse the trailing blank the stamp introduced
    while new.endswith("\n\n"):
        new = new[:-1]
    if not new.endswith("\n"):
        new += "\n"
    with file_lock(agents):
        atomic_write_text(agents, new)


def run_pulse(project_dir: Path, today: _dt.date) -> dict[str, Any]:
    """Does the working context still hold? Read-only, composed from sensors
    that already exist: the handoff NEXT and dream's dangling-scope detector.
    Adds nothing clever - the pulse's one original contribution is the `quiet`
    verdict, because the advisor's contract is silence when nothing is
    flagged, and a pulse that always finds something to say trains the user to
    skip it.

    The declared truth-lifetime sensor is gone with the epistemic fields it
    read: no template declares them, so no file legally carries one.
    """
    # Local import: dream pulls its full detector suite in; the toggle path
    # (on/off/status) must not pay for it.
    from dream import detect_dangling_scopes

    files = list(walk_project(project_dir))
    dangling = detect_dangling_scopes(files, today)

    next_step: Optional[str] = None
    handoff = project_dir / "_handoff.md"
    if handoff.is_file():
        try:
            next_step = parse_next_line(handoff.read_text(errors="replace"))
        except OSError:
            pass

    decisions = sorted(
        (f for f in files if f.rel_path.parts[:1] == ("decisions",)
         and f.rel_path.name != "_index.md"),
        key=lambda f: f.rel_path.name, reverse=True)[:5]
    recent = [{
        "file": str(f.rel_path),
        "status": f.frontmatter.fields.get("status"),
        "excerpt": next((ln.strip() for ln in f.body.split("\n")
                         if ln.strip() and not ln.strip().startswith("#")), "")[:160],
    } for f in decisions]

    return {
        "today": str(today),
        "quiet": not dangling,
        "next_step": next_step,
        "dangling_scopes": dangling,
        "recent_decisions": recent,
    }


def capture_task(project_dir: Path, title: str, note: str = "") -> tuple[int, str]:
    """Land an approved suggestion as a task note through the existing rail.

    (exit code, message). Writes tasks/{slug}.md from templates/task.md and
    lets board.ensure_board seed the card - the same path the session-end
    bridge uses, so a captured task is indistinguishable from any other.
    Dedup by slug is the advisor's raise-once rule enforced at the disk
    layer: a re-capture never clobbers a note someone has since edited.
    """
    from board import ensure_board
    from board_bridge import kebab, render_task_note

    slug = kebab(title)
    if not slug:
        return 1, "error: --title kebabs to nothing; give it at least one word"
    tasks = project_dir / "tasks"
    note_path = tasks / f"{slug}.md"
    if note_path.is_file():
        return 0, f"tasks/{slug}.md already exists; not touching it"
    tasks.mkdir(parents=True, exist_ok=True)
    body = render_task_note(slug, note or title)
    with file_lock(note_path):
        atomic_write_text(note_path, body)
    try:
        verdict = ensure_board(project_dir)
    except Exception as e:  # the note landed; the board can catch up next hook
        return 0, f"wrote tasks/{slug}.md (board reseed failed: {e})"
    return 0, f"wrote tasks/{slug}.md; board: {verdict}"


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Adjudant advisor toggle + pulse")
    parser.add_argument("action", choices=("on", "off", "status", "pulse", "capture-task"))
    parser.add_argument("--project-dir", default=".",
                        help="Code project root (where .claude/adjudant lives)")
    parser.add_argument("--today", help="Override 'today' (YYYY-MM-DD) for age math")
    parser.add_argument("--title", help="capture-task: the task's one-line title")
    parser.add_argument("--note", default="",
                        help="capture-task: the observation, lands in ## Notes")
    args = parser.parse_args(argv)

    if args.action == "capture-task":
        if not args.title:
            print("error: capture-task needs --title", file=sys.stderr)
            return 1
        try:
            vault_project, _ = smart_project_dir(args.project_dir)
        except VaultUnresolvableError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        rc, msg = capture_task(vault_project, args.title, args.note)
        print(msg, file=sys.stderr if rc else sys.stdout)
        return rc

    if args.action == "pulse":
        today = _dt.date.today()
        if args.today:
            try:
                today = _dt.date.fromisoformat(args.today)
            except ValueError:
                print(f"error: --today not a valid YYYY-MM-DD: {args.today}",
                      file=sys.stderr)
                return 1
        try:
            vault_project, _ = smart_project_dir(args.project_dir)
        except VaultUnresolvableError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        if not vault_project.is_dir():
            print(f"error: project not found: {vault_project}", file=sys.stderr)
            return 1
        print(json.dumps(run_pulse(vault_project, today), indent=2, default=str))
        return 0

    project_dir = Path(args.project_dir).expanduser().resolve()
    state = read_state(project_dir)
    if state is None:
        print("error: no .claude/adjudant breadcrumb here - run /adjudant "
              "connect first; the advisor needs a linked project.",
              file=sys.stderr)
        return 1

    if args.action == "status":
        print(f"advisor: {state}")
        return 0

    if args.action == "on":
        _set_knob(project_dir, "on")
        stamped = _stamp_agents(project_dir)
        print("advisor: on — the next session start makes it live.")
        if not stamped:
            print("note: no AGENTS.md to stamp; the breadcrumb knob is set, "
                  "but the project-root marker is missing until connect "
                  "provisions AGENTS.md.", file=sys.stderr)
        return 0

    _set_knob(project_dir, "off")
    _unstamp_agents(project_dir)
    print("advisor: off — banner and marker removed.")
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
