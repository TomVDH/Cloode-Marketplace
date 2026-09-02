#!/usr/bin/env python3
"""Adjudant graph — generate mermaid diagram scaffolds from vault data.

READ-ONLY. Backs the `/adjudant draw diagram` flow with *mechanically derived*
diagrams so Claude pastes a correct fence instead of hand-drawing one. Three
modes, all emitting a paste-ready ```mermaid fenced block to stdout (or --out):

  relations   flowchart of the project's wikilink graph — one node per vault
              file, one edge per resolving wikilink between project files.
              sessions/ and dreams/ collapse into single group nodes; the
              graph is capped (default 30 nodes, lowest-degree leaves dropped
              first) per the size discipline in
              reference/mermaid-generation-rules.md.
  board       kanban snapshot of {project}/board/board-data.json — one
              subgraph per column, one node per card. Suitable for pasting
              into a session note as a point-in-time record.
  tiers       the static cleanup model (clean → clean --deep → dream)
              as a stateDiagram-v2 — for briefs/docs that explain the model.

CLI:
    python3 graph.py --project-dir PATH [--mode relations|board|tiers]
                     [--max-nodes N] [--board-data FILE] [--out FILE] [--force]
                     [--include-legacy]

Follows the `.claude/adjudant` breadcrumb like every other helper: pass the
CODE project root and it resolves to the vault project.

Reads the vault, never mutates it. The one and only write is the optional
`--out` file, and it is gated: contained to the invocation root or the resolved
vault project, refused over an existing file unless `--force`, backed up before
any replace, and written atomically. See the `--out` section below.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from _vault_walk import (
    atomic_write_text, smart_project_dir, VaultFile, VaultUnresolvableError, walk_project,
)

DEFAULT_MAX_NODES = 30
# Backups of an `--out` target live beside it, newest BACKUP_KEEP per target.
# Mirrors board.py's constant of the same name rather than importing it, the
# same way `_is_inside` is twinned: neither module depends on the other.
BACKUP_KEEP = 5
# One classDef per file role, palette ≤ 6 (generation-rules discipline)
CLASS_DEFS = {
    "project": "fill:#efe7ff,stroke:#7c5cff,color:#1d1633",
    "decision": "fill:#e8f6ec,stroke:#2f9e57,color:#0f2b1a",
    "doc": "fill:#e9f1fb,stroke:#3b7dd8,color:#122238",
    "note": "fill:#fdf3e3,stroke:#d9962e,color:#33250f",
    "group": "fill:#f0f0f2,stroke:#8a8a94,color:#26262c",
    "other": "fill:#f7f7f8,stroke:#b5b5bd,color:#33333a",
}
GROUP_FOLDERS = ("sessions", "dreams")

# Board mode's own palette. A deck can carry any number of lanes, but
# mermaid-generation-rules §5 caps a diagram at 6 colours, so the lane role
# cycles: column N takes `lane{N % 5}`. Orphans get the sixth, distinct, so a
# card in a lane that no longer exists is visibly not in a lane.
LANE_CLASS_DEFS = (
    "fill:#e9f1fb,stroke:#3b7dd8,color:#122238",
    "fill:#fdf3e3,stroke:#d9962e,color:#33250f",
    "fill:#efe7ff,stroke:#7c5cff,color:#1d1633",
    "fill:#e8f6ec,stroke:#2f9e57,color:#0f2b1a",
    "fill:#f0f0f2,stroke:#8a8a94,color:#26262c",
)
ORPHAN_ROLE = "orphan"
BOARD_CLASS_DEFS = {f"lane{i}": v for i, v in enumerate(LANE_CLASS_DEFS)}
BOARD_CLASS_DEFS[ORPHAN_ROLE] = "fill:#fdeaea,stroke:#c9424a,color:#3a1315"


EMPTY_LABEL = "(untitled)"


def _q(label: str) -> str:
    """Mermaid-safe quoted label. Four separate hazards, one choke point:

      &, <, >  entity-escaped per mermaid-generation-rules §2. Mermaid renders
               flowchart labels as HTML (`flowchart.htmlLabels` defaults to
               true and Obsidian keeps the default), so a card titled
               `fix <br> handling` is not displayed — the renderer eats the
               tag and the label reads `fix  handling` with a stray break.
               `&` goes first or `<` would come back out as `&amp;lt;`.
               board.py:495 escapes `<` for the same class of reason.
      "        downgraded to `'`; a raw one closes the quoted label early.
      \\r \\n    collapsed to a space. A card title is user-typed in
               board.html, and a newline splits one node across two lines,
               which terminates the surrounding ```mermaid fence early.
      empty    replaced by a placeholder. Mermaid REFUSES to parse `n0[""]`,
               and one empty label anywhere kills the whole fence, not just
               its own node — so an empty column name or a card with no id
               and no title takes the entire diagram down.
    """
    clean = (label
             .replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "'")
             .replace("\r\n", " ")
             .replace("\n", " ")
             .replace("\r", " ")
             .strip())
    return f'"{clean or EMPTY_LABEL}"'


def _role(vf: VaultFile) -> str:
    t = (vf.file_type or "").strip().lower()
    if t == "project":
        return "project"
    if t in ("decision", "doc", "note"):
        return t
    return "other"


def relations_graph(
    project_dir: Path,
    *,
    max_nodes: int = DEFAULT_MAX_NODES,
    include_legacy: bool = False,
    stats: Optional[dict[str, int]] = None,
) -> str:
    """Wikilink adjacency of the vault project as a flowchart LR.

    `stats`, when passed, is filled with `{"total": n, "omitted": n}` so the
    CALLER can report truncation somewhere a human will see it. The in-fence
    `%%` note alone is not enough: mermaid strips comments at render time.
    """
    if stats is not None:
        stats.update(total=0, omitted=0)
    files = list(walk_project(project_dir, include_legacy=include_legacy))
    if not files:
        return "flowchart LR\n  empty[\"(no vault files found)\"]\n"

    # Node key per file: rel path. Group folder members collapse onto one key.
    def node_key(vf: VaultFile) -> str:
        top = vf.rel_path.parts[0] if len(vf.rel_path.parts) > 1 else ""
        if top in GROUP_FOLDERS:
            return f"__group__{top}"
        return str(vf.rel_path)

    # Wikilink resolution INSIDE the project: stem / rel-without-ext / rel.
    # A real file always beats a group node for the same alias — otherwise a
    # dreams/2026-01-01-review.md would absorb links meant for
    # notes/2026-01-01-review.md just by walk order.
    resolve: dict[str, str] = {}
    group_counts: dict[str, int] = {}
    labels: dict[str, str] = {}
    roles: dict[str, str] = {}
    for vf in files:
        key = node_key(vf)
        if key.startswith("__group__"):
            top = key.removeprefix("__group__")
            group_counts[key] = group_counts.get(key, 0) + 1
            labels[key] = f"{top}/"
            roles[key] = "group"
        else:
            labels[key] = vf.path.stem
            roles[key] = _role(vf)
        rel = str(vf.rel_path)
        for alias in (vf.path.stem, rel, rel[: -len(vf.path.suffix)] if vf.path.suffix else rel):
            prev = resolve.get(alias)
            if prev is None or (prev.startswith("__group__") and not key.startswith("__group__")):
                resolve[alias] = key

    # Duplicate stem labels get a parent-folder prefix so two nodes never
    # render indistinguishably.
    by_label: dict[str, list[str]] = {}
    for k, lb in labels.items():
        by_label.setdefault(lb, []).append(k)
    for lb, ks in by_label.items():
        if len(ks) > 1:
            for k in ks:
                if not k.startswith("__group__") and "/" in k:
                    labels[k] = f"{k.rsplit('/', 1)[0]}/{lb}"

    # Since v3 the session log writes zone-less links — [[{slug}/notes/a.md]],
    # not [[projects/{slug}/notes/a.md]] — so a zone move cannot break them.
    # The project folder's own name is not part of a project-relative path.
    project_prefix = f"{project_dir.name}/"

    edges: set[tuple[str, str]] = set()
    for vf in files:
        src = node_key(vf)
        for wl in vf.wikilinks:
            target = (wl.target or "").strip()
            if not target:
                continue
            norm = target.replace("\\", "/").rstrip("/")
            dst = resolve.get(norm)
            if dst is None and norm.startswith(project_prefix):
                # Strip the project's own prefix and resolve EXACTLY. Never
                # fall through to the basename guess below: [[demo/archive/x]]
                # is as broken here as [[archive/x]] is.
                dst = resolve.get(norm[len(project_prefix):])
            elif dst is None:
                # Basename fallback ONLY for bare targets ([[note]]) and
                # vault-rooted paths (projects/{slug}/…). A path-qualified
                # link that doesn't resolve is broken in Obsidian too —
                # inventing an edge to a same-named file elsewhere would
                # draw confident nonsense.
                base = norm.split("/")[-1]
                if "/" not in norm or norm.startswith("projects/"):
                    dst = resolve.get(base)
            if dst and dst != src:
                edges.add((src, dst))

    # Cap: drop lowest-degree non-group leaves until at max_nodes.
    degree: dict[str, int] = {k: 0 for k in labels}
    for a, b in edges:
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
    keys = list(labels)
    dropped = 0
    if len(keys) > max_nodes:
        droppable = sorted(
            (k for k in keys if roles[k] != "project" and not k.startswith("__group__")),
            key=lambda k: (degree.get(k, 0), k),
        )
        while len(keys) > max_nodes and droppable:
            victim = droppable.pop(0)
            keys.remove(victim)
            dropped += 1
        edges = {(a, b) for a, b in edges if a in keys and b in keys}

    if stats is not None:
        stats.update(total=len(labels), omitted=dropped)

    ids = {k: f"n{i}" for i, k in enumerate(sorted(keys))}
    lines = ["flowchart LR"]
    if dropped:
        lines.append(f"  %% {dropped} low-degree file(s) omitted (--max-nodes {max_nodes})")
    for k in sorted(keys):
        label = labels[k]
        if k in group_counts:
            label = f"{label} ({group_counts[k]} notes)"
        lines.append(f"  {ids[k]}[{_q(label)}]")
    for a, b in sorted(edges):
        lines.append(f"  {ids[a]} --> {ids[b]}")
    used_roles = {roles[k] for k in keys}
    for role in sorted(used_roles):
        lines.append(f"  classDef {role} {CLASS_DEFS[role]}")
    for k in sorted(keys):
        lines.append(f"  class {ids[k]} {roles[k]}")
    return "\n".join(lines) + "\n"


def board_graph(
    project_dir: Path,
    board_data: Optional[str] = None,
    *,
    max_nodes: int = DEFAULT_MAX_NODES,
    stats: Optional[dict[str, int]] = None,
) -> str:
    """Kanban snapshot of board-data.json as a flowchart with column subgraphs.

    Node-capped and classDef-styled, like relations_graph. Three reference
    files promise BOTH disciplines for graph.py output (draw.md, the
    generated-diagrams note in content-mermaid.md, mermaid-generation-rules
    §5/§7); board mode used to implement neither, and `--max-nodes` was
    accepted and silently ignored here. A 200-card deck came back as a
    205-line fence with no classDef and nothing on stderr, which is well past
    the ~30-node ceiling §7 tells the model to refuse.
    """
    if stats is not None:
        stats.update(total=0, omitted=0)
    data_path = Path(board_data).expanduser() if board_data else project_dir / "board" / "board-data.json"
    if not data_path.is_file():
        raise FileNotFoundError(
            f"no deck at {data_path} — run `board.py scaffold` first (or pass --board-data)")
    # Shape-check before touching the deck. reference/board.md invites
    # hand-editing board-data.json, so a wrong SHAPE (valid JSON, wrong type)
    # is a reachable input, and it used to escape as a raw `'list' object has
    # no attribute 'get'` traceback rather than the `error: ...` line the CLI
    # emits everywhere else. ValueError, so the CLI's one handler covers it
    # alongside JSONDecodeError.
    deck: Any = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(deck, dict):
        raise ValueError(
            f"deck root must be a JSON object, not {type(deck).__name__}: {data_path}")
    columns = deck.get("columns") or []
    cards = deck.get("cards") or []
    if not isinstance(columns, list) or not isinstance(cards, list):
        raise ValueError(f"deck 'columns' and 'cards' must be JSON arrays: {data_path}")
    if not all(isinstance(x, dict) for x in (*columns, *cards)):
        raise ValueError(
            f"every column and card must be a JSON object: {data_path}")
    # Group the cards BEFORE emitting anything: the cap has to be sized against
    # the number of groups, and the total omission count belongs at the top of
    # the fence, not discovered on the way down.
    # str() both sides throughout: a hand-edited deck with integer ids must
    # still match.
    col_ids = [str(col.get("id", i)) for i, col in enumerate(columns)]
    known_ids = set(col_ids)
    grouped = [[c for c in cards if str(c.get("column")) == cid] for cid in col_ids]
    # A point-in-time record must not under-report: cards whose column matches
    # no lane get their own subgraph instead of vanishing (mirrors board.py
    # status's orphan accounting and board.html's UNFILED lane).
    orphans = [c for c in cards if str(c.get("column")) not in known_ids]

    # An empty deck is named, not drawn blank. `{"columns": [], "cards": []}`
    # is legal and reachable (reference/board.md invites hand-editing), and it
    # used to leave a bare `flowchart LR` — which mermaid accepts and Obsidian
    # renders as an empty box with nothing to say why. relations_graph names
    # its own empty case; this says it the same way. It also means the lane
    # count below is never zero, so the cap can divide by it safely.
    if not columns and not orphans:
        return "flowchart LR\n  empty[\"(empty deck: no columns, no cards)\"]\n"

    # PER-GROUP cap, not a running total. A cap that simply stopped at N cards
    # would empty the terminal lane completely, and the terminal lane is what a
    # snapshot is usually read for. Every lane keeps at least one card: without
    # that floor, a deck with more lanes than `max_nodes` reports every card as
    # omitted and draws a full board as an empty one.
    n_groups = len(grouped) + (1 if orphans else 0)
    per_group = max(1, max_nodes // n_groups)
    omitted = sum(max(0, len(g) - per_group) for g in (*grouped, orphans))
    if stats is not None:
        stats.update(total=len(cards), omitted=omitted)

    lines = ["flowchart LR"]
    if omitted:
        lines.append(f"  %% {omitted} card(s) omitted (--max-nodes {max_nodes})")
    card_i = 0
    classes: list[str] = []
    used_roles: set[str] = set()

    def _emit_group(group: list[dict[str, Any]], role: str) -> None:
        nonlocal card_i
        for c in group[:per_group]:
            card_id = str(c.get("id", card_i))
            title = str(c.get("title", ""))[:40]
            label = f"{card_id} · {title}" if title else card_id
            lines.append(f"    c{card_i}[{_q(label)}]")
            classes.append(f"  class c{card_i} {role}")
            used_roles.add(role)
            card_i += 1
        cut = len(group) - per_group
        if cut > 0:
            lines.append(f"    %% {cut} more card(s) omitted (--max-nodes {max_nodes})")

    for col_i, col in enumerate(columns):
        col_name = str(col.get("name", col_ids[col_i]))
        lines.append(f"  subgraph col{col_i}[{_q(col_name)}]")
        if not grouped[col_i]:
            lines.append(f"    col{col_i}e[{_q('—')}]")
        _emit_group(grouped[col_i], f"lane{col_i % len(LANE_CLASS_DEFS)}")
        lines.append("  end")
    if orphans:
        lines.append(f"  subgraph orphaned[{_q('orphaned (unknown column)')}]")
        _emit_group(orphans, ORPHAN_ROLE)
        lines.append("  end")

    # Role styling, generation-rules §5: one classDef per role, stamped at
    # generation time, only for roles actually used.
    for role in sorted(used_roles):
        lines.append(f"  classDef {role} {BOARD_CLASS_DEFS[role]}")
    lines.extend(classes)
    return "\n".join(lines) + "\n"


def tiers_graph() -> str:
    """The locked cleanup model as a stateDiagram-v2.

    Two verbs since v3, not three: ramasse became `clean --deep`, so the
    middle tier is a flag on the first rather than a verb of its own.
    """
    return (
        "stateDiagram-v2\n"
        "  [*] --> clean\n"
        "  clean: clean — surface mechanical (routine)\n"
        "  deep: clean --deep — structural findings (sparing, reports only)\n"
        "  dream: dream — semantic content refresh (judgment-heavy)\n"
        "  clean --> deep: structural drift found\n"
        "  deep --> dream: content drift suspected\n"
        "  dream --> clean: refreshed — routine resumes\n"
    )


def fenced(mermaid: str) -> str:
    return f"```mermaid\n{mermaid}```\n"


def report_truncation(stats: dict[str, int], max_nodes: int, unit: str) -> None:
    """Say on stderr that the diagram is partial. No-op when nothing was cut.

    The in-fence `%% N omitted` note is a mermaid COMMENT, stripped at render
    time, so a reader of the pasted diagram sees a confident, complete looking
    graph with nothing to say that most of the project was cut. With `--out`
    the operator never reads the fence text at all. stderr is the only channel
    that reaches a human, so the fact goes to both.
    """
    omitted = stats.get("omitted", 0)
    if not omitted:
        return
    total = stats.get("total", omitted)
    print(f"[graph] TRUNCATED: {omitted} of {total} {unit}(s) omitted at "
          f"--max-nodes {max_nodes}. The diagram is partial.", file=sys.stderr)


# ============================================================
#  --out: the module's only write
# ============================================================
# graph.py reads the vault and prints. `--out` is the single exception, and it
# used to be `Path(args.out).expanduser().write_text(block)` — no containment,
# no existing-file guard, no backup, no atomicity. `--out ~/.zshrc`, `--out
# ../../anything` and `--out {project}/brief.md` were all accepted, destroyed
# the target, printed "wrote" and exited 0.
#
# Three guards now, in order, and the write itself goes through the shared
# durable-write primitive board.py uses:
#
#   1. CONTAINMENT. The resolved path must sit inside a root the operator
#      named: `--project-dir` (the invocation root, which defaults to cwd) or
#      the vault project the breadcrumb resolves to. Same shape as board.py's
#      `--dest` exemption — a destination is legal because the operator
#      pointed at it, not because the string looked harmless.
#   2. NO SILENT CLOBBER. An existing target is refused; `--force` replaces it
#      but takes a backup first, and a failed backup refuses the write.
#   3. ATOMICITY. `atomic_write_text`, so a reader never lands on a truncated
#      middle.
#
# No `file_lock`: the lock primitive exists for read-modify-write cycles (the
# deck has three concurrent writers). `--out` is a pure replace, so atomicity
# alone is the whole guarantee, and a permanent `.{name}.lock` sidecar beside
# every --out target would be litter in the user's repo for nothing.


def _is_inside(child: Path, parent: Path) -> bool:
    """True when `child` is `parent` or sits under it, symlinks resolved.
    Neither path needs to exist.

    Twin of board.py's `_is_inside`; kept private in both so neither module
    has to import the other. Change them together. Resolution matters: a
    string check passes a `{project}/link -> /etc` symlink.
    """
    try:
        c, p = Path(child).expanduser().resolve(), Path(parent).expanduser().resolve()
    except (OSError, ValueError):
        return False
    return c == p or p in c.parents


def backup_out(path: Path, keep: int = BACKUP_KEEP) -> Path:
    """Copy an `--out` target about to be replaced to a timestamped sibling.

    Never a fixed `{name}.bak`: that fixed name was the v0.19.0 board bug,
    where a second run overwrote the only copy of the user's real file with
    the already-destroyed one. The guard against that is the collision loop —
    a backup NEVER lands on a path that already exists. The timestamp is
    legibility (which copy is which), not the safety property.

    Dot-prefixed and not `.md`, so the vault walkers (`rglob("*.md")`) never
    index it, Obsidian never lists it, and `check`/`clean` never report it
    as a schema-less note.

    Rotated, newest ``keep`` per target. This lands inside a vault project,
    which v3 named as one of two deliberate exceptions to "scratch leaves the
    vault" (reference/state-contract.md). An exception has to be bounded to be
    defensible, and this path was the unbounded one: board.py's twin has
    rotated since v0.19.0 while every `draw --out --force` here left another
    copy beside the target forever. Pruning is per target, by name prefix, so
    two `--out` files in one folder each keep their own history.

    Raises OSError; callers refuse the write rather than proceed unbacked.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f".{path.name}.{stamp}.bak")
    n = 2
    while target.exists():                       # two --force runs in one second
        target = path.with_name(f".{path.name}.{stamp}-{n}.bak")
        n += 1
    shutil.copy2(path, target)
    prefix = f".{path.name}."
    mine = []
    for sib in target.parent.iterdir():
        if not (sib.name.startswith(prefix) and sib.name.endswith(".bak")):
            continue
        try:
            mine.append((sib.stat().st_mtime, sib.name, sib))
        except OSError:
            continue                             # vanished under us; nothing to prune
    # mtime first, name second: within one second the collision suffix (`-2`)
    # sorts BEFORE the plain stamp by name alone, which would prune the newer
    # copy. copy2 carries the SOURCE mtime, so ties are broken by name only
    # when two backups really are the same age.
    mine.sort()
    for _, _, stale in mine[:max(0, len(mine) - keep)]:
        try:
            stale.unlink()
        except OSError:
            pass                                 # rotation is housekeeping, never fatal
    return target


def write_out(block: str, raw_out: str, roots: list[Path], *, force: bool) -> int:
    """Write `block` to `raw_out` if every guard allows it. Returns an exit code."""
    out = Path(raw_out).expanduser()
    # Containment decides on the RESOLVED path (inside `_is_inside`); every
    # later filesystem call here follows symlinks to the same inode anyway, so
    # `out` itself stays as typed and the error messages echo what the operator
    # wrote rather than a path they never named.
    if not any(_is_inside(out, r) for r in roots):
        allowed = " or ".join(str(r) for r in roots)
        print(f"error: --out {out} resolves outside {allowed} — refusing to write "
              f"there. Point --out inside the project (or inside --project-dir).",
              file=sys.stderr)
        return 1
    if out.is_dir():
        print(f"error: --out {out} is a directory.", file=sys.stderr)
        return 1
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"error: could not create {out.parent}: {e}", file=sys.stderr)
        return 1
    if out.exists():
        if not force:
            print(f"error: --out {out} already exists — refusing to overwrite it. "
                  f"Pass --force to replace it (the current contents are backed up "
                  f"first), or choose a path that does not exist yet.", file=sys.stderr)
            return 1
        try:
            bak = backup_out(out)
        except OSError as e:
            print(f"error: could not back up {out} before replacing it: {e}", file=sys.stderr)
            return 1
        print(f"[graph] backed up {out.name} -> {bak.name}", file=sys.stderr)
    try:
        # ValueError as well as OSError: a lone surrogate anywhere in the block
        # (a hand-edited deck reaches this) raises UnicodeEncodeError. With a
        # bare write_text that error arrives AFTER the destination has already
        # been truncated; atomic_write_text leaves it byte-identical.
        atomic_write_text(out, block)
    except (OSError, ValueError) as e:
        print(f"error: could not write {out}: {e}", file=sys.stderr)
        return 1
    print(f"[graph] wrote {out}", file=sys.stderr)
    return 0


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="graph.py", description="Adjudant graph — mermaid scaffolds from vault data (read-only).")
    parser.add_argument("--project-dir", default=".", help="project root (breadcrumb-resolved; default cwd)")
    parser.add_argument("--mode", choices=["relations", "board", "tiers"], default="relations")
    parser.add_argument("--max-nodes", type=int, default=DEFAULT_MAX_NODES,
                        help=f"relations/board: node cap (default {DEFAULT_MAX_NODES})")
    parser.add_argument("--board-data", help="board: explicit board-data.json path")
    parser.add_argument("--out", help="write the fenced block here instead of stdout "
                                      "(inside the project or --project-dir)")
    parser.add_argument("--force", action="store_true",
                        help="--out: replace an existing file (backed up first)")
    parser.add_argument("--include-legacy", action="store_true", help="relations: include _legacy/ files")
    args = parser.parse_args(argv)

    project_dir: Optional[Path] = None
    if args.mode == "tiers":
        block = fenced(tiers_graph())
        if args.out:
            # tiers needs no project — that is documented, and resolution
            # failure must stay non-fatal here. But when one DOES resolve it is
            # a legitimate --out destination (draw.md: the tiers fence belongs
            # in a brief or doc), so resolve best-effort to widen containment.
            try:
                project_dir, _hint = smart_project_dir(args.project_dir)
            except (VaultUnresolvableError, OSError, ValueError):
                project_dir = None
    else:
        try:
            project_dir, _hint = smart_project_dir(args.project_dir)
        except VaultUnresolvableError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        stats: dict[str, int] = {}
        try:
            if args.mode == "relations":
                block = fenced(relations_graph(
                    project_dir, max_nodes=args.max_nodes,
                    include_legacy=args.include_legacy, stats=stats))
                unit = "file"
            else:
                block = fenced(board_graph(
                    project_dir, args.board_data, max_nodes=args.max_nodes, stats=stats))
                unit = "card"
        # Wide on purpose. OSError covers FileNotFoundError; ValueError covers
        # JSONDecodeError, UnicodeDecodeError and the deck shape checks;
        # TypeError/AttributeError catch the remaining ways a hand-edited deck
        # or a half-written vault file reaches an attribute that isn't there.
        # A helper the skill shells out to must hand back a message the model
        # can relay, never a traceback it has to interpret.
        except (OSError, ValueError, TypeError, AttributeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        report_truncation(stats, args.max_nodes, unit)

    if args.out:
        roots = [Path(args.project_dir).expanduser().resolve()]
        if project_dir is not None:
            roots.append(Path(project_dir).resolve())
        return write_out(block, args.out, roots, force=args.force)
    print(block, end="")
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
