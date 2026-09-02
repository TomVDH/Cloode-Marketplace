#!/usr/bin/env python3
"""Adjudant shelf: project lifecycle manager (verb #11).

list:    read-only status table of every project across zones, with the
         machine suggestion (active/stale axis only) beside the declared state.
preview: plan one transition; writes {vault}/.adjudant-shelf-preview/.
apply:   execute the transition (brief status + dated status-log line +
         zone folder move + vault-wide wikilink prefix rewrite +
         projects/_index.md row refresh). Backs up every modified file first.

CLI:
    python3 shelf.py list    (--project-dir PATH | --vault-dir PATH) [--stale-days N] [--today YYYY-MM-DD]
    python3 shelf.py preview (--project-dir PATH | --vault-dir PATH) --slug SLUG --to STATE [--reason TEXT]
    python3 shelf.py apply   (--project-dir PATH | --vault-dir PATH) --slug SLUG --to STATE [--reason TEXT]

--project-dir points at the code project root (breadcrumb flow); --vault-dir
names the vault directly. Machines never call apply without a prior preview.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from _cost import breadcrumb_int
from _vault_walk import (
    DEFAULT_SKIP,
    DEFAULT_STALE_DAYS,
    ZONE_FOR_STATUS,
    VaultUnresolvableError,
    enumerate_projects_all_zones,
    find_project_dir,
    parse_frontmatter,
    resolve_vault,
    smart_project_dir,
    suggest_status,
    zone_matches_status,
    zone_of,
)
from connect import (
    count_non_index_files,
    newest_session_date,
    upsert_projects_index_row,
)

PREVIEW_DIR = ".adjudant-shelf-preview"
BACKUP_DIR = ".adjudant-shelf-backup"
STATUS_LOG_HEADING = "## Status log"


def _resolve_vault_dir(project_dir_arg: str, vault_dir_arg: Optional[str]) -> Path:
    """Vault root from --vault-dir, the breadcrumb flow, or an upward walk."""
    if vault_dir_arg:
        v = Path(vault_dir_arg).expanduser().resolve()
        if v.is_dir():
            return v
        raise VaultUnresolvableError(f"--vault-dir not found: {v}")
    _scan_dir, hint = smart_project_dir(project_dir_arg)
    if hint:
        return hint
    arg = Path(project_dir_arg).expanduser().resolve()
    v = resolve_vault(arg)
    if v:
        return v
    raise VaultUnresolvableError(
        f"cannot resolve a vault from {project_dir_arg}; pass --vault-dir")


def run_list(vault: Path, stale_days: int, today: date) -> dict[str, Any]:
    """Read-only lifecycle table across all zones."""
    rows: list[dict[str, Any]] = []
    for slug, pdir, zone in enumerate_projects_all_zones(vault):
        fm, _ = parse_frontmatter((pdir / "brief.md").read_text(errors="replace"))
        declared = fm.fields.get("status")
        declared = declared if isinstance(declared, str) else None
        sug = suggest_status(declared, pdir, today, stale_days)
        rows.append({
            "slug": slug,
            "zone": zone,
            "zone_matches": zone_matches_status(declared, zone),
            **sug,
        })
    return {"vault": str(vault), "stale_after_days": stale_days, "projects": rows}


def set_brief_status(text: str, new_status: str, today_str: str) -> str:
    """Rewrite status: and updated: inside the frontmatter block only."""
    fm, body = parse_frontmatter(text)
    lines = fm.raw.split("\n") if fm.has_block else []
    replaced = bumped = False
    for i, ln in enumerate(lines):
        if ln.startswith("status:"):
            lines[i] = f"status: {new_status}"
            replaced = True
        elif ln.startswith("updated:"):
            lines[i] = f"updated: {today_str}"
            bumped = True
    if not replaced:
        lines.append(f"status: {new_status}")
    if not bumped:
        lines.append(f"updated: {today_str}")
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def append_status_log(text: str, from_state: Optional[str], to_state: str,
                      today_str: str, reason: Optional[str]) -> str:
    """Dated transition line under ## Status log (newest first; section
    created at end of file on first transition)."""
    entry = f"- {today_str}: {from_state or 'unset'} → {to_state}"
    if reason:
        entry += f" ({reason})"
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == STATUS_LOG_HEADING:
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            lines.insert(j, entry)
            return "\n".join(lines)
    tail = "" if text.endswith("\n") else "\n"
    return text + tail + f"\n{STATUS_LOG_HEADING}\n\n{entry}\n"


def plan_transition(vault: Path, slug: str, to_state: str,
                    reason: Optional[str], today_str: str) -> dict[str, Any]:
    """Read-only plan: zones, folder move, vault-wide wikilink rewrites."""
    if to_state not in ZONE_FOR_STATUS:
        raise ValueError(
            f"invalid state {to_state!r}; one of: {', '.join(ZONE_FOR_STATUS)}")
    pdir = find_project_dir(vault, slug)
    if pdir is None or not (pdir / "brief.md").is_file():
        raise ValueError(
            f"project {slug!r} not found in projects/, projects/_fridge/, projects/_archive/")
    from_zone = zone_of(pdir)
    to_zone = ZONE_FOR_STATUS[to_state]
    fm, _ = parse_frontmatter((pdir / "brief.md").read_text(errors="replace"))
    from_state = fm.fields.get("status")
    old_prefix = f"[[projects/{from_zone + '/' if from_zone else ''}{slug}/"
    new_prefix = f"[[projects/{to_zone + '/' if to_zone else ''}{slug}/"
    move_required = old_prefix != new_prefix
    to_dir = (vault / "projects" / to_zone / slug) if to_zone else (vault / "projects" / slug)

    link_rewrites: list[dict[str, Any]] = []
    if move_required:
        skip_set = set(DEFAULT_SKIP) | {"_legacy"}
        for f in sorted(vault.rglob("*.md")):
            rel = f.relative_to(vault)
            if any(part in skip_set for part in rel.parts):
                continue
            try:
                n = f.read_text(errors="replace").count(old_prefix)
            except OSError:
                continue
            if n:
                link_rewrites.append({"file": str(rel), "count": n})

    return {
        "slug": slug,
        "reason": reason,
        "from_state": from_state if isinstance(from_state, str) else None,
        "to_state": to_state,
        "from_zone": from_zone,
        "to_zone": to_zone,
        "from_dir": str(pdir.relative_to(vault)),
        "to_dir": str(to_dir.relative_to(vault)),
        "move_required": move_required,
        "old_link_prefix": old_prefix,
        "new_link_prefix": new_prefix,
        "link_rewrites": link_rewrites,
        "today": today_str,
    }


def write_preview(vault: Path, plan: dict[str, Any]) -> Path:
    pdir = vault / PREVIEW_DIR
    if pdir.exists():
        shutil.rmtree(pdir)
    pdir.mkdir(parents=True)
    (pdir / "changes.json").write_text(json.dumps(plan, indent=2))
    (pdir / "summary.md").write_text("\n".join([
        f"# shelf preview: {plan['slug']} to {plan['to_state']}",
        "",
        f"- from: {plan['from_state']} ({plan['from_dir']})",
        f"- to:   {plan['to_state']} ({plan['to_dir']})",
        f"- folder move: {'yes' if plan['move_required'] else 'no'}",
        f"- files with links to rewrite: {len(plan['link_rewrites'])}",
        f"- reason: {plan['reason'] or '(none)'}",
        "",
    ]))
    return pdir


def apply_transition(vault: Path, plan: dict[str, Any]) -> dict[str, Any]:
    """Execute a planned transition. Backup first; abort before any write
    if the move target already exists."""
    slug = plan["slug"]
    from_dir = vault / plan["from_dir"]
    to_dir = vault / plan["to_dir"]
    if plan["move_required"] and to_dir.exists():
        raise RuntimeError(f"target dir already exists: {to_dir}")

    # 1. backup every file that will be modified (rewrites + the brief)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = vault / BACKUP_DIR / ts
    to_back_up = [r["file"] for r in plan["link_rewrites"]]
    brief_rel = f"{plan['from_dir']}/brief.md"
    if brief_rel not in to_back_up:
        to_back_up.append(brief_rel)
    backup_root.mkdir(parents=True)
    for rel in to_back_up:
        src = vault / rel
        dst = backup_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    (backup_root / "manifest.json").write_text(json.dumps(
        {"plan": plan, "backed_up": to_back_up, "timestamp": ts}, indent=2))

    # 2-4 are atomic from the caller's view: any failure restores from the
    # backup taken above (spec: no half-moved project).
    links_rewritten = 0
    skipped_undecodable: list[str] = []
    moved = False
    try:
        # 2. vault-wide wikilink prefix rewrite. STRICT decode: reading with
        # errors="replace" and writing the result back baked a permanent
        # U+FFFD over every undecodable byte (tidy avoids this same trap).
        # An unreadable file is reported and left byte-identical.
        for r in plan["link_rewrites"]:
            f = vault / r["file"]
            try:
                text = f.read_text()
            except (UnicodeDecodeError, OSError):
                skipped_undecodable.append(r["file"])
                continue
            new_text = text.replace(plan["old_link_prefix"], plan["new_link_prefix"])
            if new_text != text:
                f.write_text(new_text)
                links_rewritten += r["count"]

        # 3. zone folder move
        if plan["move_required"]:
            to_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(from_dir), str(to_dir))
            moved = True
        final_dir = to_dir if moved else from_dir

        # 4. brief: status + updated + status log. Strict decode for the
        # same reason: this text is written straight back. Unlike a link
        # rewrite, this one cannot be skipped and carried on from: the brief's
        # `status:` field IS the transition, so a move with an unrewritten
        # brief is the "stuck in _fridge while declaring itself active" state
        # this whole block exists to prevent. Convert to RuntimeError so the
        # rollback below actually runs (UnicodeDecodeError is a ValueError and
        # escaped both this handler and cli_main's).
        brief = final_dir / "brief.md"
        try:
            text = brief.read_text()
        except UnicodeDecodeError as exc:
            raise RuntimeError(
                f"brief.md is not valid UTF-8 so its status could not be "
                f"rewritten ({exc.reason} at byte {exc.start}); fix the file's "
                f"encoding and re-run apply") from exc
        text = set_brief_status(text, plan["to_state"], plan["today"])
        text = append_status_log(text, plan["from_state"], plan["to_state"],
                                 plan["today"], plan["reason"])
        brief.write_text(text)
    # UnicodeDecodeError is listed explicitly: it subclasses ValueError, not
    # OSError, so a strict read added inside the try above would otherwise
    # abort PAST this rollback and leave the project half-moved.
    except (OSError, RuntimeError, UnicodeDecodeError) as exc:
        if moved and to_dir.exists() and not from_dir.exists():
            shutil.move(str(to_dir), str(from_dir))
        for rel in to_back_up:
            src = backup_root / rel
            if src.is_file():
                (vault / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, vault / rel)
        raise RuntimeError(
            f"apply failed and was rolled back from {backup_root.name}: {exc}") from exc

    # 5. projects/_index.md row refresh
    fm, _ = parse_frontmatter(brief.read_text(errors="replace"))
    ptype = fm.fields.get("project_type") or "coding"
    row = upsert_projects_index_row(
        vault, slug, ptype, plan["to_state"],
        count_non_index_files(final_dir / "decisions"),
        count_non_index_files(final_dir / "sessions"),
        newest_session_date(final_dir / "sessions"),
    )

    # 6. clear the consumed preview
    preview = vault / PREVIEW_DIR
    if preview.exists():
        shutil.rmtree(preview)

    return {
        "slug": slug,
        "from_state": plan["from_state"],
        "to_state": plan["to_state"],
        "moved": moved,
        "final_dir": str(final_dir.relative_to(vault)),
        "links_rewritten": links_rewritten,
        "skipped_undecodable": skipped_undecodable,
        "index_row": row,
        "backup": str(backup_root.relative_to(vault)),
    }


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="shelf.py",
        description="Adjudant shelf: project lifecycle (list / preview / apply).")
    parser.add_argument("phase", choices=["list", "preview", "apply"])
    parser.add_argument("--project-dir", default=".",
                        help="Code project root, breadcrumb flow (default: cwd)")
    parser.add_argument("--vault-dir", help="Vault root (bypasses breadcrumb)")
    parser.add_argument("--slug", help="Project slug (preview/apply)")
    parser.add_argument("--to", dest="to_state", help="Target state (preview/apply)")
    parser.add_argument("--reason", help="Optional reason recorded in the status log")
    parser.add_argument("--stale-days", type=int,
                        help="Override stale_after_days (list)")
    parser.add_argument("--today", help="YYYY-MM-DD override (testing/determinism)")
    args = parser.parse_args(argv)

    try:
        vault = _resolve_vault_dir(args.project_dir, args.vault_dir)
    except VaultUnresolvableError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    today = date.fromisoformat(args.today) if args.today else date.today()

    if args.phase == "list":
        stale_days = args.stale_days or breadcrumb_int(
            Path(args.project_dir).expanduser().resolve(),
            "stale_after_days", DEFAULT_STALE_DAYS)
        print(json.dumps(run_list(vault, stale_days, today), indent=2))
        return 0

    if not args.slug or not args.to_state:
        print("error: preview/apply need --slug and --to", file=sys.stderr)
        return 1
    today_str = today.isoformat()
    try:
        plan = plan_transition(vault, args.slug, args.to_state, args.reason, today_str)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.phase == "preview":
        pdir = write_preview(vault, plan)
        print(json.dumps({"preview_dir": str(pdir), "plan": plan}, indent=2))
        return 0

    # apply: require a matching prior preview, then execute the FRESH plan
    changes = vault / PREVIEW_DIR / "changes.json"
    if not changes.is_file():
        print("error: no shelf preview found; run the preview phase first",
              file=sys.stderr)
        return 1
    prior = json.loads(changes.read_text())
    if prior.get("slug") != args.slug or prior.get("to_state") != args.to_state:
        print("error: existing preview is for a different transition; re-run preview",
              file=sys.stderr)
        return 1
    try:
        result = apply_transition(vault, plan)
    except (RuntimeError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if result.get("skipped_undecodable"):
        # Never silent: these files still point at the OLD path.
        print(f"[shelf] {len(result['skipped_undecodable'])} file(s) are not valid "
              f"UTF-8 and were left untouched, so their links still point at the "
              f"old path: {', '.join(result['skipped_undecodable'])}", file=sys.stderr)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
