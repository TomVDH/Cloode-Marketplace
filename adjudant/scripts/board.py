#!/usr/bin/env python3
"""Adjudant board — scaffold a self-hosted work-order kanban board for a project.

Generates `board-data.json` (the deck) + a self-contained `board.html`
(drag-to-move, auto-saves to disk via the File System Access API). The deck can
be seeded from the vault project's `tasks/*.md` notes, from an existing
`board-data.json`, or left as an empty 6-stage starter.

The board is a *view*: cards carry short ids and mono `ref` tags that cross-link
your own codes (specs, handoffs, commits). Category colour is data-driven —
names get palette hues by index, or supply explicit `{name: oklch(...)}`.

The board verb is a **standard project surface**: any project adjudant knows
about can have its own board, addressed by slug. Targeting:

    --project-dir PATH   the current breadcrumb-linked project (default)
    --project SLUG       a named project under {vault}/projects/{slug}
    --all                every project in the vault (one board each)

CLI:
    python3 board.py scaffold [--project-dir PATH | --project SLUG | --all]
                              [--vault PATH] [--dest DIR] [--from-tasks]
                              [--data board-data.json] [--title STR] [--force]
    python3 board.py serve --dir DIR [--port 8787] [--open]
    python3 board.py status [--project-dir PATH | --project SLUG | --all]
    python3 board.py --ensure [--project-dir PATH]

`--ensure` is the ambient form (hooks, session-end bridge): birth the board
when the first real task note exists, reseed when tasks changed, write nothing
otherwise. Verdict (created/reseeded/no-tasks/no-change) is the last stdout line.

`scaffold` is idempotent and *refresh-without-clobber*: re-running with
`--from-tasks` against an existing board merges the current task state into the
deck while preserving the columns you dragged cards into (use `--force` for a
full rebuild). `board.html` is always refreshed from the template.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

from _vault_walk import (
    enumerate_projects_all_zones, find_project_dir, parse_frontmatter,
    resolve_vault, smart_project_dir, VaultUnresolvableError,
)

TEMPLATE = Path(__file__).resolve().parent.parent / "skills" / "adjudant" / "templates" / "board.html"
MARK_RE = re.compile(r"/\*BOARD_DATA_START\*/.*?/\*BOARD_DATA_END\*/", re.DOTALL)

DECK_VERSION = 1
DEFAULT_SUBTITLE = "Work-order board"
DEFAULT_CATEGORIES = ["build", "docs", "infra", "chore"]

DEFAULT_COLUMNS = [
    {"id": "backlog", "name": "Backlog"},
    {"id": "next", "name": "Next"},
    {"id": "doing", "name": "Doing"},
    {"id": "review", "name": "Review"},
    {"id": "done", "name": "Done"},
    {"id": "icebox", "name": "Icebox"},
]
# task status (lower-cased) -> board column
STATUS_TO_COLUMN = {
    "backlog": "backlog", "todo": "backlog", "planned": "backlog", "proposed": "backlog",
    "next": "next", "ready": "next", "queued": "next",
    "doing": "doing", "in-progress": "doing", "in_progress": "doing", "active": "doing", "wip": "doing",
    "review": "review", "blocked": "review", "in-review": "review",
    "done": "done", "complete": "done", "completed": "done", "implemented": "done", "shipped": "done", "accepted": "done",
    "icebox": "icebox", "deferred": "icebox", "parked": "icebox", "shelved": "icebox", "someday": "icebox",
}


# A quoted scalar followed by a trailing comment, e.g. `"" # optional: ...`.
_QUOTED_COMMENT_RE = re.compile(r"^(?:\"([^\"]*)\"|'([^']*)')\s*#")


def _clean_scalar(val: Any) -> str:
    """Re-clean a minimal-YAML scalar before it becomes a card field.

    The frontmatter parser keeps a trailing comment on QUOTED value lines
    (`code: ""  # guidance` survives as the raw string, quotes and all), so a
    task note pasted verbatim from a template with inline guidance comments
    would poison card ids, categories, and notes. Recover the quoted part when
    that shape appears; every other value passes through untouched (a `#`
    inside a quoted value without a trailing comment is preserved)."""
    s = str(val if val is not None else "").strip()
    m = _QUOTED_COMMENT_RE.match(s)
    if m:
        return (m.group(1) if m.group(1) is not None else m.group(2)).strip()
    return s


def _first_heading(body: str) -> Optional[str]:
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return None


def _as_list(val: Any) -> list[str]:
    if val is None:
        return []
    items = val if isinstance(val, list) else [val]
    out = []
    for it in items:
        s = str(it).strip()
        # strip wikilink form [[target|alias]] / [[target]] -> alias or target
        m = re.match(r"^\[\[([^\]]+)\]\]$", s)
        if m:
            inner = m.group(1)
            s = inner.split("|", 1)[1] if "|" in inner else inner
        if s:
            out.append(s)
    return out


def _today() -> str:
    return date.today().isoformat()


def cards_from_tasks(project_dir: Path) -> list[dict[str, Any]]:
    """Build cards from `{project}/tasks/*.md` frontmatter + first heading.

    One card per task note. `_index.md` and roadmap/index files (frontmatter
    `type: tasks`) are skipped — they are not per-card task notes.
    """
    tasks = project_dir / "tasks"
    if not tasks.is_dir():
        return []
    cards: list[dict[str, Any]] = []
    seen: dict[str, str] = {}  # card id -> source filename (duplicate detection)
    for f in sorted(tasks.iterdir()):
        if not f.is_file() or f.suffix != ".md" or f.name == "_index.md":
            continue
        fm, body = parse_frontmatter(f.read_text(errors="replace"))
        fields = fm.fields
        if str(fields.get("type", "") or "").strip().lower() == "tasks":
            continue  # roadmap/index file, not a per-card task note
        status = _clean_scalar(fields.get("status")).lower()
        category = _clean_scalar(fields.get("category"))
        if not category:
            tags = _as_list(fields.get("tags"))
            category = next((t for t in tags if t not in ("task", "tasks")), None)
        # Duplicate ids corrupt the merge (last-wins) and the board UI (drag
        # moves the wrong ticket) — disambiguate deterministically and warn.
        cid = _clean_scalar(fields.get("code")) or _clean_scalar(fields.get("id")) or f.stem
        if cid in seen:
            orig = cid
            cid = f.stem
            n = 2
            while cid in seen:
                cid = f"{f.stem}~{n}"
                n += 1
            print(f"[board] warning: duplicate card id '{orig}' in tasks/ "
                  f"({seen[orig]}, {f.name}) — using '{cid}' for {f.name}",
                  file=sys.stderr)
        seen[cid] = f.name
        cards.append({
            "id": cid,
            "title": _clean_scalar(fields.get("title")) or _first_heading(body) or f.stem,
            "column": STATUS_TO_COLUMN.get(status, "backlog"),
            "category": category or "task",
            "related": _as_list(fields.get("related")),
            "notes": _clean_scalar(fields.get("note")),
            "source": "task",  # provenance: merge_deck iceboxes only task-seeded cards
        })
    return cards


def build_deck(
    project_dir: Path,
    *,
    from_tasks: bool,
    title: str,
    subtitle: str = DEFAULT_SUBTITLE,
    board_id: Optional[str] = None,
) -> dict[str, Any]:
    cards = cards_from_tasks(project_dir) if from_tasks else []
    cats: list[str] = []
    for c in cards:
        if c["category"] and c["category"] not in cats:
            cats.append(c["category"])
    if not cats:
        cats = list(DEFAULT_CATEGORIES)
    return {
        "version": DECK_VERSION,
        "boardId": board_id or project_dir.name,
        "title": title,
        "subtitle": subtitle,
        "updated": _today(),
        "columns": DEFAULT_COLUMNS,
        "categories": cats,
        "cards": cards,
    }


def enumerate_projects(vault: Path) -> list[tuple[str, Path]]:
    """Every project across projects/, projects/_fridge/, projects/_archive/.

    Filesystem truth (a dir containing brief.md); the _index.md table is
    never consulted. Sorted by zone order then slug.
    """
    return [(slug, path) for slug, path, _zone in enumerate_projects_all_zones(vault)]


def merge_deck(existing: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    """Refresh-without-clobber merge of a freshly task-seeded deck into the deck
    already on disk.

    Per card id:
      - card present in both → keep the on-disk ``column`` (the user's drag
        state) and a non-empty on-disk ``notes`` (a board-local annotation),
        but re-seed ``title``/``category``/``related`` from the task note.
      - new task card → added in its status-derived column.
      - on-disk TASK-SEEDED card (``source: task``) whose task disappeared →
        moved to ``icebox`` (never deleted).
      - on-disk card WITHOUT task provenance (hand-added via the board UI, or
        from a pre-provenance deck) → kept in its current column untouched.
      - on-disk card with NO id, or the second and later cards sharing one id →
        pass-through survivor, carried verbatim. Only one on-disk card can be
        the merge partner for a fresh card (fresh ids are unique), so these can
        never match, and dropping them is the data loss this rule exists to
        prevent. A repeated id is warned about on stderr, the way
        ``cards_from_tasks`` warns for tasks/.

    Deck-level ``title``/``subtitle`` from disk are preserved (a re-scaffold does
    not rename a board you titled); ``version``/``columns``/``updated``/
    ``boardId`` come from the fresh deck. Categories are the union over the merged
    cards (custom ``{name: colour}`` mappings on disk are preserved).
    """
    # A LIST, never a dict keyed on str(id): two on-disk cards sharing an id,
    # or two id-less ones (both keying to the string "None"), used to collapse
    # to one entry and the losers were silently deleted, against the documented
    # "never deleted" contract. Every on-disk card is accounted for here.
    ex_by_id: dict[str, dict[str, Any]] = {}      # first card per non-empty id
    # (merge key or None, card) in on-disk order. None marks a pass-through.
    ex_ordered: list[tuple[Optional[str], dict[str, Any]]] = []
    dupes: dict[str, int] = {}
    for c in existing.get("cards", []):
        cid = str(c.get("id") or "").strip()
        if not cid:
            ex_ordered.append((None, c))
        elif cid in ex_by_id:
            dupes[cid] = dupes.get(cid, 1) + 1
            ex_ordered.append((None, c))
        else:
            ex_by_id[cid] = c
            ex_ordered.append((cid, c))
    for cid, n in dupes.items():
        print(f"[board] warning: duplicate card id '{cid}' in the on-disk deck "
              f"({n} cards share it): only the first merges with tasks/, the "
              f"rest are carried through unchanged", file=sys.stderr)

    merged: list[dict[str, Any]] = []
    fresh_ids: set[str] = set()
    for fc in fresh.get("cards", []):
        cid = str(fc.get("id"))
        fresh_ids.add(cid)
        ec = ex_by_id.get(cid)
        if ec is not None:
            fc = dict(fc)
            fc["column"] = ec.get("column", fc.get("column"))
            if ec.get("notes"):
                fc["notes"] = ec["notes"]
        merged.append(fc)
    for cid, ec in ex_ordered:
        if cid is None:
            merged.append(ec)          # pass-through survivor, verbatim
        elif cid not in fresh_ids:
            ec = dict(ec)
            if ec.get("source") == "task":
                # Task genuinely disappeared from tasks/ — park it
                ec["column"] = "icebox"
            merged.append(ec)

    cats: list[str] = []
    for c in merged:
        cat = c.get("category")
        if cat and cat not in cats:
            cats.append(cat)
    ex_cats = existing.get("categories")
    categories: Any
    if isinstance(ex_cats, dict):
        categories = {name: ex_cats.get(name) for name in cats}
    else:
        categories = cats or list(DEFAULT_CATEGORIES)

    out = dict(fresh)
    out["cards"] = merged
    out["categories"] = categories
    if existing.get("title"):
        out["title"] = existing["title"]
    if existing.get("subtitle"):
        out["subtitle"] = existing["subtitle"]
    if existing.get("columns"):
        # Columns are user-ownable deck data (added/renamed lanes) — a re-seed
        # must not reset them to the six defaults, or cards dragged into a
        # custom lane vanish from the rendered board.
        out["columns"] = existing["columns"]
    return out


def render_template(deck: dict[str, Any]) -> str:
    """The full board.html text with the deck injected. Raises before any file
    is written when the template is missing/markerless, so a failed render
    can't leave board-data.json and board.html out of sync."""
    if not TEMPLATE.is_file():
        raise FileNotFoundError(f"board template missing: {TEMPLATE}")
    tpl = TEMPLATE.read_text()
    if not MARK_RE.search(tpl):
        raise ValueError("template has no BOARD_DATA markers")
    # Escape every `<` as \u003c — valid JSON *and* JS — so a task title
    # containing `</script>` or `<!--` can't break out of the script block.
    payload_json = json.dumps(deck, indent=2).replace("<", "\\u003c")
    payload = "/*BOARD_DATA_START*/" + payload_json + "/*BOARD_DATA_END*/"
    return MARK_RE.sub(lambda _m: payload, tpl, count=1)


def emit_html(deck: dict[str, Any], dest_html: Path) -> None:
    dest_html.write_text(render_template(deck))


def _resolve_vault_root(args: argparse.Namespace) -> Optional[Path]:
    """Vault root for --project / --all: explicit --vault, else breadcrumb at cwd."""
    if getattr(args, "vault", None):
        p = Path(args.vault).expanduser()
        return p if p.is_dir() else None
    return resolve_vault(Path.cwd())


def scaffold_one(
    project_dir: Path,
    dest: Path,
    *,
    from_tasks: bool,
    data: Optional[str],
    force: bool,
    title: Optional[str],
    board_id: Optional[str],
) -> int:
    """Scaffold a single board into ``dest``. Returns a process exit code."""
    if not project_dir.is_dir():
        print(f"error: project not found: {project_dir} (run /adjudant connect first)", file=sys.stderr)
        return 1
    dest.mkdir(parents=True, exist_ok=True)
    data_path = dest / "board-data.json"
    bid = board_id or project_dir.name
    resolved_title = title or project_dir.name.replace("-", " ").title()

    # `--force` alone over an existing board would rebuild an EMPTY starter
    # deck on top of it — total loss of cards, notes, and drag state. Refuse.
    if force and data_path.is_file() and not from_tasks and not data:
        print("error: --force without --from-tasks (or --data) would overwrite "
              "the existing board with an empty deck — refusing. "
              "Add --from-tasks to rebuild from tasks/.", file=sys.stderr)
        return 1
    # ANY overwrite of an existing deck keeps a one-shot escape hatch, not just
    # --force: `--data foo.json` used to replace a live deck (cards, custom
    # lanes, title) with no backup at all, because both this and the refusal
    # above were gated on `force`. A plain re-seed merges (it never discards),
    # so only the replacing paths need the .bak.
    replaces_deck = force or bool(data)
    if replaces_deck and data_path.is_file():
        try:
            shutil.copy2(data_path, data_path.with_name("board-data.json.bak"))
        except OSError as e:
            print(f"error: could not back up the existing deck before replacing it: {e}",
                  file=sys.stderr)
            return 1

    try:
        if data:
            deck = json.loads(Path(data).expanduser().read_text())
            if not isinstance(deck, dict):
                raise ValueError("deck root must be a JSON object")
        elif data_path.is_file() and not force:
            existing = json.loads(data_path.read_text())
            if not isinstance(existing, dict):
                raise ValueError("deck root must be a JSON object")
        else:
            existing = None
    except (OSError, json.JSONDecodeError, ValueError) as e:
        src = data if data else str(data_path)
        print(f"error: could not read deck {src}: {e}", file=sys.stderr)
        return 1

    if data:
        deck.setdefault("version", DECK_VERSION)
        deck.setdefault("boardId", bid)
        deck.setdefault("subtitle", DEFAULT_SUBTITLE)
        deck.setdefault("columns", DEFAULT_COLUMNS)
        deck.setdefault("categories", list(DEFAULT_CATEGORIES))
        deck.setdefault("cards", [])
        if title:
            deck["title"] = title
    elif data_path.is_file() and not force:
        if from_tasks:
            # refresh-without-clobber: merge current task state into the deck
            fresh = build_deck(project_dir, from_tasks=True, title=resolved_title, board_id=bid)
            deck = merge_deck(existing, fresh)
        else:
            deck = existing            # keep the user's deck untouched
            deck.setdefault("boardId", bid)   # backfill id for pre-0.9 decks
    else:
        deck = build_deck(project_dir, from_tasks=from_tasks, title=resolved_title, board_id=bid)

    # Render FIRST: a missing/markerless template must fail before any write,
    # never leaving board-data.json and board.html out of sync.
    html = render_template(deck)
    data_path.write_text(json.dumps(deck, indent=2) + "\n")
    (dest / "board.html").write_text(html)
    print(f"[board] {dest}/board.html  ({len(deck.get('cards', []))} cards, {len(deck.get('columns', []))} stages)", file=sys.stderr)
    print(str(dest / "board.html"))
    return 0


def _same_deck(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Deck equality with the `updated` date stamp ignored."""
    return ({k: v for k, v in a.items() if k != "updated"}
            == {k: v for k, v in b.items() if k != "updated"})


def ensure_board(project_dir: Path, vault_dir: Optional[Path] = None) -> str:
    """Board birth + reseed for ambient callers (hooks, session-end bridge).

    A thin composition of the existing scaffold machinery, no new write path:

      - no real task notes (only ``_index.md`` / ``type: tasks`` roadmaps):
        ``"no-tasks"``, nothing written. Projects that never grow tasks never
        grow board files.
      - task notes exist, no ``board/board-data.json`` yet: scaffold via
        ``scaffold_one`` and return ``"created"``.
      - board exists: the clobber-safe ``--from-tasks`` merge (dragged columns
        always survive), ``"reseeded"`` when the deck actually changed,
        ``"no-change"`` otherwise. On no-change the deck file is left
        untouched, mtime included, so frequent ambient calls never churn a
        synced vault.

    ``vault_dir`` is accepted for callers that already resolved the vault; the
    composition itself only needs the resolved project dir. Raises on a failed
    write (RuntimeError wrapping scaffold_one's exit code), so no caller can
    claim an effect that did not happen.
    """
    if not cards_from_tasks(project_dir):
        return "no-tasks"
    dest = project_dir / "board"
    data_path = dest / "board-data.json"
    if not data_path.is_file():
        rc = scaffold_one(project_dir, dest, from_tasks=True, data=None,
                          force=False, title=None, board_id=None)
        if rc != 0:
            raise RuntimeError(f"board scaffold failed for {project_dir} (rc {rc})")
        return "created"
    # Reseed path: compute the would-be merge first and skip the write when it
    # changes nothing. An unreadable deck falls through to scaffold_one, whose
    # friendly error becomes the raised RuntimeError.
    try:
        existing = json.loads(data_path.read_text())
        if not isinstance(existing, dict):
            existing = None
    except (OSError, json.JSONDecodeError):
        existing = None
    if existing is not None:
        # Mirror scaffold_one's title/board_id defaults exactly.
        fresh = build_deck(project_dir, from_tasks=True,
                           title=project_dir.name.replace("-", " ").title(),
                           board_id=project_dir.name)
        if _same_deck(merge_deck(existing, fresh), existing):
            return "no-change"
    rc = scaffold_one(project_dir, dest, from_tasks=True, data=None,
                      force=False, title=None, board_id=None)
    if rc != 0:
        raise RuntimeError(f"board reseed failed for {project_dir} (rc {rc})")
    return "reseeded"


def _serve_hint(dest: Path) -> None:
    print(f"[board] serve: python3 {Path(__file__).name} serve --dir \"{dest}\"  → http://localhost:8787/board.html", file=sys.stderr)


def cmd_scaffold(args: argparse.Namespace) -> int:
    # ── Mode: --all / --project both operate at the vault level ──
    if args.all or args.project:
        vault = _resolve_vault_root(args)
        if vault is None:
            print("error: no vault resolved; pass --vault PATH or run from a connected project", file=sys.stderr)
            return 1

    if args.all:
        if args.dest or args.data:
            print("error: --dest/--data cannot be combined with --all (each board goes to {project}/board/)", file=sys.stderr)
            return 1
        if args.title:
            print("warning: --title ignored with --all (each board self-titles from its slug)", file=sys.stderr)
        projects = enumerate_projects(vault)
        if not projects:
            print(f"error: no projects found under {vault}/projects", file=sys.stderr)
            return 1
        rc, ok = 0, 0
        for slug, pdir in projects:
            try:
                if scaffold_one(pdir, pdir / "board", from_tasks=args.from_tasks,
                                data=None, force=args.force, title=None, board_id=slug) == 0:
                    ok += 1
                else:
                    rc = 1
            except Exception as e:  # one bad project must not abort the batch
                print(f"error: board for '{slug}' failed: {e}", file=sys.stderr)
                rc = 1
        print(f"[board] scaffolded {ok}/{len(projects)} project boards under {vault}/projects", file=sys.stderr)
        return rc

    if args.project:
        pdir = find_project_dir(vault, args.project) or (vault / "projects" / args.project)
        if not pdir.is_dir():
            have = ", ".join(s for s, _ in enumerate_projects(vault)) or "(none)"
            print(f"error: project '{args.project}' not found under {vault}/projects (have: {have})", file=sys.stderr)
            return 1
        dest = Path(args.dest).expanduser() if args.dest else (pdir / "board")
        rc = scaffold_one(pdir, dest, from_tasks=args.from_tasks, data=args.data,
                          force=args.force, title=args.title, board_id=args.project)
        if rc == 0:
            _serve_hint(dest)
        return rc

    # ── Default: --project-dir (the current breadcrumb-linked project) ──
    try:
        project_dir, _hint = smart_project_dir(args.project_dir)
    except VaultUnresolvableError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    dest = Path(args.dest).expanduser() if args.dest else (project_dir / "board")
    rc = scaffold_one(project_dir, dest, from_tasks=args.from_tasks, data=args.data,
                      force=args.force, title=args.title, board_id=None)
    if rc == 0:
        _serve_hint(dest)
    return rc


def cmd_serve(args: argparse.Namespace) -> int:
    import errno
    import functools
    import http.server
    import socketserver
    directory = str(Path(args.dir).expanduser())

    class _ReuseServer(socketserver.TCPServer):
        # Survive TIME_WAIT restarts instead of dying with a raw traceback.
        allow_reuse_address = True

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    try:
        httpd = _ReuseServer(("127.0.0.1", args.port), handler)
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print(f"error: port {args.port} is already in use — pass --port N "
                  f"(or --port 0 for a free one)", file=sys.stderr)
            return 1
        raise
    with httpd:
        port = httpd.server_address[1]  # the REAL port (matters with --port 0)
        url = f"http://localhost:{port}/board.html"
        print(f"[board] serving {directory} at {url} (Ctrl-C to stop)", file=sys.stderr)
        if getattr(args, "open", False):
            import webbrowser
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[board] stopped", file=sys.stderr)
    return 0


def _status_line(slug: str, board_dir: Path) -> tuple[str, bool]:
    """One status line for a project's board. Returns (line, ok)."""
    data_path = board_dir / "board-data.json"
    if not data_path.is_file():
        return f"{slug:24s} (no board — run scaffold)", False
    try:
        deck = json.loads(data_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return f"{slug:24s} (unreadable board-data.json: {e})", False
    columns = deck.get("columns") or []
    cards = deck.get("cards") or []
    known = {c.get("id") for c in columns}
    counts = {c.get("id"): 0 for c in columns}
    unknown: dict[str, int] = {}
    for card in cards:
        col = card.get("column")
        if col in known:
            counts[col] += 1
        else:
            unknown[str(col)] = unknown.get(str(col), 0) + 1
    cols = " ".join(f"{cid}:{n}" for cid, n in counts.items())
    line = f"{slug:24s} {cols}  ({len(cards)} cards, updated {deck.get('updated') or '—'})"
    for col, n in sorted(unknown.items()):
        line += f"\n{'':24s} warning: {n} card(s) in unknown column '{col}'"
    return line, True


def cmd_status(args: argparse.Namespace) -> int:
    """Terminal column counts — see the board without opening a browser."""
    if args.all or args.project:
        vault = _resolve_vault_root(args)
        if vault is None:
            print("error: no vault resolved; pass --vault PATH or run from a connected project", file=sys.stderr)
            return 1

    if args.all:
        if args.dest:
            print("error: --dest cannot be combined with --all (each board lives at {project}/board/)", file=sys.stderr)
            return 1
        projects = enumerate_projects(vault)
        if not projects:
            print(f"error: no projects found under {vault}/projects", file=sys.stderr)
            return 1
        rc = 0
        for slug, pdir in projects:
            line, ok = _status_line(slug, pdir / "board")
            print(line)
            if not ok:
                rc = 1
        return rc

    if args.project:
        pdir = find_project_dir(vault, args.project) or (vault / "projects" / args.project)
        if not pdir.is_dir():
            have = ", ".join(s for s, _ in enumerate_projects(vault)) or "(none)"
            print(f"error: project '{args.project}' not found under {vault}/projects (have: {have})", file=sys.stderr)
            return 1
        line, ok = _status_line(args.project, Path(args.dest).expanduser() if args.dest else pdir / "board")
        print(line)
        return 0 if ok else 1

    try:
        project_dir, _hint = smart_project_dir(args.project_dir)
    except VaultUnresolvableError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    board_dir = Path(args.dest).expanduser() if args.dest else project_dir / "board"
    line, ok = _status_line(project_dir.name, board_dir)
    print(line)
    return 0 if ok else 1


def cmd_ensure(argv: list[str]) -> int:
    """The `--ensure` flag form (no subcommand), one line for hook callers:
    `python3 board.py --ensure --project-dir X`. Verdict on the last stdout
    line; exit 0 on every verdict, 1 on a failed resolve or write."""
    p = argparse.ArgumentParser(
        prog="board.py --ensure",
        description="Birth/reseed the project board from tasks/ (verdict on the last stdout line).")
    p.add_argument("--ensure", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--project-dir", default=".", help="project root (breadcrumb-resolved; default cwd)")
    args = p.parse_args(argv)
    try:
        project_dir, vault_hint = smart_project_dir(args.project_dir)
    except VaultUnresolvableError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    try:
        verdict = ensure_board(project_dir, vault_hint)
    except Exception as e:  # a broken template/deck must not traceback at hook time
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(verdict)
    return 0


def cli_main(argv: Optional[list[str]] = None) -> int:
    args_in = sys.argv[1:] if argv is None else argv
    if "--ensure" in args_in:
        return cmd_ensure(args_in)
    parser = argparse.ArgumentParser(prog="board.py", description="Adjudant board — scaffold/serve a work-order kanban board.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scaffold", help="write board-data.json + a self-contained board.html")
    mode = sc.add_mutually_exclusive_group()
    mode.add_argument("--project", help="target a named project by slug under {vault}/projects (takes precedence over --project-dir)")
    mode.add_argument("--all", action="store_true", help="scaffold a board for every project in the vault")
    sc.add_argument("--project-dir", default=".", help="project root (breadcrumb-resolved; default cwd)")
    sc.add_argument("--vault", help="vault root for --project/--all (default: resolve from cwd breadcrumb)")
    sc.add_argument("--dest", help="output dir (default: {project}/board); not allowed with --all")
    sc.add_argument("--from-tasks", action="store_true", help="seed cards from {project}/tasks/*.md")
    sc.add_argument("--data", help="use this board-data.json as the deck (verbatim); not allowed with --all")
    sc.add_argument("--title", help="board title")
    sc.add_argument("--force", action="store_true", help="rebuild from tasks, discarding dragged card state")
    sc.set_defaults(func=cmd_scaffold)

    sv = sub.add_parser("serve", help="serve a board dir over localhost (so disk-save works)")
    sv.add_argument("--dir", required=True, help="board dir to serve")
    sv.add_argument("--port", type=int, default=8787, help="port (0 picks a free one)")
    sv.add_argument("--open", action="store_true", help="open the board in the default browser")
    sv.set_defaults(func=cmd_serve)

    st = sub.add_parser("status", help="print per-column card counts without opening a browser")
    st_mode = st.add_mutually_exclusive_group()
    st_mode.add_argument("--project", help="target a named project by slug under {vault}/projects")
    st_mode.add_argument("--all", action="store_true", help="status for every project in the vault")
    st.add_argument("--project-dir", default=".", help="project root (breadcrumb-resolved; default cwd)")
    st.add_argument("--vault", help="vault root for --project/--all (default: resolve from cwd breadcrumb)")
    st.add_argument("--dest", help="board dir (default: {project}/board)")
    st.set_defaults(func=cmd_status)

    args = parser.parse_args(args_in)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(cli_main())
