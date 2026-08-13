#!/usr/bin/env python3
"""Adjudant ramasse_scan — structural drift catalog (ramasse analysis phase).

Scans an adjudant-managed vault project and emits a structured drift
catalog (JSON) for Claude to render or for `/adjudant ramasse` to use
as the analysis phase before planning a deep restructure.

Reports on: folder drift, index gaps, frontmatter drift, tag drift,
type drift, naming violations, wikilink form violations, broken
wikilinks, doc/decision mismatches. Read-only — never writes.

CLI:
    python3 ramasse_scan.py --project-dir PATH [--vault-dir PATH] [--out FILE] [--include-legacy]

NOTE: This module was originally named `dream.py` in v0.3.0. Renamed
in v0.3.1 to align with the locked 3-tier model:
  - tidy    = surface mechanical sweep
  - ramasse = deep structural clean (this scanner is its analysis phase)
  - dream   = content/knowledge/memory refresh (semantic; see dream.py)

See docs/superpowers/2026-05-26-adjudant-tidy-ramasse-log.design.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional

from _cost import cost_block, read_threshold, stat_walk
from _vault_walk import (
    AUTO_CREATED_FOLDERS,
    BUCKET_A_TYPES,
    BUCKET_A_TYPES_PLUS_HOME,
    BUCKET_B_MIGRATIONS,
    DEFAULT_SKIP,
    INDEX_EXEMPT_FOLDERS,
    PROJECT_TYPE_DEFAULT_FOLDERS,
    VaultFile,
    build_vault_index,
    is_bucket_b_migration,
    is_bucket_d_tag,
    is_checkable_wikilink,
    resolve_vault,
    resolve_wikilink,
    smart_project_dir, VaultUnresolvableError,
    resolve_scope,
    scope_rel,
    walk_project,
)


# Doc filename UPPERCASE rule — exceptions
DOC_NAME_EXCEPTIONS = {"brief", "_index", "_handoff"}

# Files at project root that are always OK by name
PROJECT_ROOT_OK_FILES = {"brief.md", "_index.md", "_handoff.md"}

# Date prefix regex (YYYY-MM-DD-anything)
DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-(.*))?$")


def _project_slug(files: list[VaultFile], project_dir: Path) -> Optional[str]:
    """Resolve the project slug from brief.md or fall back to dir name."""
    for f in files:
        if f.rel_path == Path("brief.md"):
            slug = f.frontmatter.fields.get("slug")
            if isinstance(slug, str) and slug:
                return slug
    return project_dir.name


def _project_type(files: list[VaultFile]) -> Optional[str]:
    """Read project_type from brief.md frontmatter."""
    for f in files:
        if f.rel_path == Path("brief.md"):
            pt = f.frontmatter.fields.get("project_type")
            if isinstance(pt, str) and pt:
                return pt
    return None


def _extra_folders(files: list[VaultFile]) -> list[str]:
    """Read extra_folders declared in brief frontmatter."""
    for f in files:
        if f.rel_path == Path("brief.md"):
            ef = f.frontmatter.fields.get("extra_folders")
            if isinstance(ef, list):
                return [str(x) for x in ef if x]
            if isinstance(ef, str) and ef:
                return [ef]
    return []


# ============================================================
# Drift detectors
# ============================================================


def detect_folder_drift(
    project_dir: Path,
    project_type: Optional[str],
    extra_folders: list[str],
) -> list[str]:
    """Folders present at project root that aren't in defaults + extras + auto."""
    if not project_type or project_type not in PROJECT_TYPE_DEFAULT_FOLDERS:
        return []
    defaults = PROJECT_TYPE_DEFAULT_FOLDERS[project_type]
    allowed = set(defaults["with_index"]) | set(defaults["no_index"]) | AUTO_CREATED_FOLDERS | set(extra_folders) | {"_legacy"}
    drift = []
    for entry in sorted(project_dir.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in allowed:
            continue
        drift.append(entry.name)
    return drift


def detect_index_gaps(project_dir: Path, files: list[VaultFile]) -> list[str]:
    """Folders with ≥2 same-type sibling .md files missing _index.md.

    Skips INDEX_EXEMPT_FOLDERS (sessions, images, assets, previews, iterations).
    """
    # Group files by parent folder relative to project
    by_parent: dict[Path, list[VaultFile]] = defaultdict(list)
    for f in files:
        parent = f.rel_path.parent
        if parent == Path("."):
            continue
        by_parent[parent].append(f)

    gaps = []
    for parent, members in by_parent.items():
        # Skip exempt folders (any part of the path)
        if any(p in INDEX_EXEMPT_FOLDERS for p in parent.parts):
            continue
        non_index = [m for m in members if m.rel_path.name != "_index.md"]
        if len(non_index) < 2:
            continue
        has_index = any(m.rel_path.name == "_index.md" for m in members)
        if not has_index:
            gaps.append(str(parent))
    return sorted(gaps)


def detect_frontmatter_drift(files: list[VaultFile]) -> list[dict]:
    """Frontmatter issues per vault-standards §1:
       - null/~ values (should omit key)
       - missing frontmatter entirely
       - parse error
    """
    drift = []
    for f in files:
        rel = str(f.rel_path)
        if not f.frontmatter.has_block:
            drift.append({"file": rel, "issue": "missing frontmatter block"})
            continue
        if f.frontmatter.parse_error:
            drift.append({"file": rel, "issue": f"parse error: {f.frontmatter.parse_error}"})
            continue
        for key, value in f.frontmatter.fields.items():
            if isinstance(value, str) and value.strip().lower() in ("null", "~"):
                drift.append({"file": rel, "issue": f"{key}: {value} (per §1 omit empty keys)"})
    return drift


def detect_tag_drift(files: list[VaultFile], project_slug: Optional[str]) -> dict[str, Any]:
    """Tags violating the locked 2026-05-25 schema.

    Returns categories with counts + sample tag values.
    """
    bucket_d_counter: Counter[str] = Counter()
    bucket_b_counter: Counter[str] = Counter()
    bucket_d_by_category: dict[str, set[str]] = {
        "ob_prefix": set(),
        "cabinet_prefix": set(),  # excluding bucket-B migrations
        "project_slug": set(),
        "vague_topical": set(),
        "crew": set(),
        "type_tag": set(),
    }
    for f in files:
        for t in f.tags:
            if is_bucket_d_tag(t, project_slug=project_slug):
                bucket_d_counter[t] += 1
                if t.startswith("ob/"):
                    bucket_d_by_category["ob_prefix"].add(t)
                elif t.startswith("cabinet/"):
                    bucket_d_by_category["cabinet_prefix"].add(t)
                elif project_slug and (t == project_slug or t.startswith(project_slug + "/") or t.startswith(project_slug + "-")):
                    bucket_d_by_category["project_slug"].add(t)
                elif t.startswith("type/"):
                    bucket_d_by_category["type_tag"].add(t)
                elif t in {"bostrol", "kevijntje", "henske", "jonasty"}:
                    bucket_d_by_category["crew"].add(t)
                else:
                    bucket_d_by_category["vague_topical"].add(t)
            migration = is_bucket_b_migration(t)
            if migration:
                bucket_b_counter[t] += 1
    return {
        "bucket_d_total_occurrences": sum(bucket_d_counter.values()),
        "bucket_d_distinct": len(bucket_d_counter),
        "bucket_d_by_category": {k: sorted(v) for k, v in bucket_d_by_category.items() if v},
        "bucket_d_top": bucket_d_counter.most_common(15),
        "bucket_b_migrations_needed": dict(bucket_b_counter),
    }


def detect_type_drift(files: list[VaultFile]) -> dict[str, Any]:
    """Files with non-canonical `type:` values."""
    counter: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for f in files:
        t = f.file_type
        if not t:
            continue
        if t not in BUCKET_A_TYPES_PLUS_HOME:
            counter[t] += 1
            if len(examples[t]) < 3:
                examples[t].append(str(f.rel_path))
    return {
        "non_canonical_count": sum(counter.values()),
        "values": {t: {"count": n, "examples": examples[t]} for t, n in counter.most_common()},
    }


def detect_naming_violations(files: list[VaultFile]) -> list[dict]:
    """Naming-rule violations per vault-standards §4."""
    out = []
    for f in files:
        # templates/ holds canonical scaffolds (decision.md, doc.md, session.md) —
        # they're named for their type, not for an instance, so the §4 instance
        # naming rules don't apply.
        if "templates" in f.rel_path.parts:
            continue
        name = f.rel_path.name
        stem = name[:-3] if name.endswith(".md") else name
        t = f.file_type

        # type:doc filename must be UPPERCASE (exceptions: brief, _index, _handoff)
        if t == "doc" and stem not in DOC_NAME_EXCEPTIONS:
            if any(c.islower() for c in stem) and not stem.startswith("_"):
                out.append({"file": str(f.rel_path), "issue": "type:doc filename not UPPERCASE (§4)"})

        # Date-prefixed doc — should be decision
        if t == "doc":
            m = DATE_PREFIX_RE.match(stem)
            if m and m.group(2):
                out.append({"file": str(f.rel_path), "issue": "type:doc with date-prefix — should be decision?"})

        # Decision filename must be YYYY-MM-DD-kebab
        if t == "decision":
            m = DATE_PREFIX_RE.match(stem)
            if not m:
                out.append({"file": str(f.rel_path), "issue": "type:decision without YYYY-MM-DD- prefix"})

        # Session filename must be YYYY-MM-DD only (no trailing kebab)
        if t == "session":
            m = DATE_PREFIX_RE.match(stem)
            if not m or m.group(2):
                out.append({"file": str(f.rel_path), "issue": "type:session not in YYYY-MM-DD.md form"})

    return out


KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def detect_artefact_naming(project_dir: Path, include_legacy: bool = False) -> list[dict]:
    """`.canvas`/`.base` filenames must be strict kebab-case (§4 'strict').

    These artefacts aren't markdown, so `walk_project` never sees them — this
    is their dedicated naming pass (draw.md promises a check enforces the rule).
    templates/ scaffolds are exempt, mirroring detect_naming_violations; the
    _legacy skip honors include_legacy, matching walk_project's contract.
    """
    out = []
    skip = set(DEFAULT_SKIP)
    if not include_legacy:
        skip.add("_legacy")
    for ext in ("canvas", "base"):
        for f in sorted(project_dir.rglob(f"*.{ext}")):
            rel = f.relative_to(project_dir)
            if any(part in skip or part == "templates" for part in rel.parts):
                continue
            if not KEBAB_RE.fullmatch(f.stem):
                out.append({"file": str(rel),
                            "issue": f".{ext} filename not strict kebab-case (§4)"})
    return out


def detect_wikilink_form_violations(files: list[VaultFile], vault_index: set[str]) -> list[dict]:
    """`[text](*.md)` markdown-style links pointing at vault .md files.

    Per §6, only count those whose path RESOLVES — external markdown links to
    non-vault paths are valid.
    """
    out = []
    for f in files:
        for text, path, line in f.markdown_md_links:
            # Strip heading anchor for resolution check
            stem = path.split("#", 1)[0]
            # Try a couple of forms
            if resolve_wikilink(stem, vault_index):
                out.append({
                    "file": str(f.rel_path),
                    "line": line,
                    "text": text,
                    "path": path,
                })
    return out


def detect_broken_wikilinks(files: list[VaultFile], vault_index: set[str]) -> dict[str, Any]:
    """Wikilinks whose target doesn't resolve in the vault index."""
    broken: list[tuple[str, int, str]] = []
    total = 0
    for f in files:
        for wl in f.wikilinks:
            # Embeds, same-file heading links, and attachments can't resolve
            # against the index — they are not broken, just uncheckable.
            if not is_checkable_wikilink(wl):
                continue
            total += 1
            if not resolve_wikilink(wl.target, vault_index):
                broken.append((str(f.rel_path), wl.line, wl.target))

    target_counter: Counter[str] = Counter(t for _, _, t in broken)
    sample = [
        {"file": f, "line": ln, "target": t}
        for f, ln, t in broken[:20]
    ]
    return {
        "total_wikilinks": total,
        "broken_count": len(broken),
        "broken_pct": round(100.0 * len(broken) / total, 2) if total else 0.0,
        "top_broken_targets": [{"target": t, "count": n} for t, n in target_counter.most_common(15)],
        "samples": sample,
    }


def detect_doc_decision_flags(files: list[VaultFile]) -> list[dict]:
    """Doc-vs-decision disambiguator findings (per §3 of vault-standards).

    Specifically:
      - type:doc with date-prefix → likely decision
      - type:decision at project root (should be in decisions/)
    """
    out = []
    for f in files:
        t = f.file_type
        rel = f.rel_path
        if t == "decision" and rel.parent == Path(".") and rel.name != "brief.md":
            out.append({"file": str(rel), "issue": "type:decision at project root (should be in decisions/)"})
    return out


# ============================================================
# Top-level scan
# ============================================================


def run_scan(
    project_dir: Path,
    vault_dir: Optional[Path],
    *,
    include_legacy: bool = False,
    scope: Optional[str] = None,
) -> dict[str, Any]:
    """Run all drift detectors. Returns the full JSON report.

    `scope` (a project-relative folder) narrows every per-file detector to
    that subtree — filtered after the walk so rel_paths keep their
    project-root form. Folder drift is a question about the ROOT's shape, so
    a scoped run skips it instead of answering it against a fraction of the
    folders; the report's `scope` field says the run was narrowed.
    """
    files = list(walk_project(project_dir, include_legacy=include_legacy))
    if scope:
        prefix = tuple(Path(scope).parts)
        files = [f for f in files if f.rel_path.parts[:len(prefix)] == prefix]
    slug = _project_slug(files, project_dir)
    proj_type = _project_type(files)
    extras = _extra_folders(files)

    # Wikilink index from vault if provided
    vault_index: set[str] = set()
    if vault_dir and vault_dir.is_dir():
        vault_index = build_vault_index(vault_dir)

    folder_drift = [] if scope else detect_folder_drift(project_dir, proj_type, extras)
    index_gaps = detect_index_gaps(project_dir, files)
    fm_drift = detect_frontmatter_drift(files)
    tag_drift = detect_tag_drift(files, slug)
    type_drift = detect_type_drift(files)
    naming = detect_naming_violations(files) + detect_artefact_naming(project_dir, include_legacy)
    wl_form = detect_wikilink_form_violations(files, vault_index) if vault_index else []
    broken = detect_broken_wikilinks(files, vault_index) if vault_index else {
        "total_wikilinks": 0, "broken_count": 0, "broken_pct": 0.0,
        "top_broken_targets": [], "samples": [],
    }
    doc_decision = detect_doc_decision_flags(files)

    drift_items = (
        len(folder_drift)
        + len(index_gaps)
        + len(fm_drift)
        + tag_drift["bucket_d_distinct"]
        + len(type_drift["values"])
        + len(naming)
        + len(wl_form)
        + broken["broken_count"]
        + len(doc_decision)
    )

    return {
        "scope": scope,
        "meta": {
            "project_dir": str(project_dir),
            "project_slug": slug,
            "project_type": proj_type,
            "vault_dir": str(vault_dir) if vault_dir else None,
            "files_scanned": len(files),
            "include_legacy": include_legacy,
        },
        "summary": {
            "drift_items": drift_items,
            "wikilinks_broken_pct": broken["broken_pct"],
        },
        "folder_drift": folder_drift,
        "index_gaps": index_gaps,
        "frontmatter_drift": fm_drift,
        "tag_drift": tag_drift,
        "type_drift": type_drift,
        "naming_violations": naming,
        "wikilink_form_violations": wl_form,
        "broken_wikilinks": broken,
        "doc_decision_flags": doc_decision,
    }


# ============================================================
# CLI
# ============================================================


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ramasse_scan.py",
        description="Adjudant ramasse_scan — structural drift catalog (read-only).",
    )
    parser.add_argument("--project-dir", help="Project root (default: cwd)", default=".")
    parser.add_argument("--vault-dir", help="Vault root (default: resolved from breadcrumb)")
    parser.add_argument("--out", help="Write JSON to FILE instead of stdout")
    parser.add_argument("--include-legacy", action="store_true", help="Include _legacy/ in scan")
    parser.add_argument("--folder", help="Scope the walk to one project subfolder "
                        "(e.g. 'notes'); the report header states the scope")
    parser.add_argument("--estimate-only", action="store_true",
                        help="Print only the cost block (stat-only walk) and exit")
    args = parser.parse_args(argv)

    try:
        project_dir, vault_hint = smart_project_dir(args.project_dir)
    except VaultUnresolvableError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if not project_dir.is_dir():
        if (Path(args.project_dir).expanduser() / ".claude" / "adjudant").is_file():
            print(
                f"error: breadcrumb at {args.project_dir}/.claude/adjudant points to "
                f"vault project {project_dir} which doesn't exist. Run /adjudant connect first.",
                file=sys.stderr,
            )
        else:
            print(f"error: project-dir not found: {project_dir}", file=sys.stderr)
        return 1

    scope: Optional[str] = None
    scope_dir = project_dir
    if args.folder:
        try:
            scope_dir = resolve_scope(project_dir, args.folder)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        scope = scope_rel(project_dir, scope_dir)

    code_root = Path(args.project_dir).expanduser().resolve()
    # Scoped runs estimate the subtree they will read (same as dream.py).
    files_n, n_bytes = stat_walk(scope_dir)
    cost = cost_block(files_n, n_bytes, read_threshold(code_root))
    if args.estimate_only:
        print(json.dumps({"scope": scope, "cost": cost}, indent=2))
        return 0

    vault_dir: Optional[Path]
    if args.vault_dir:
        vault_dir = Path(args.vault_dir).expanduser().resolve()
    elif vault_hint:
        vault_dir = vault_hint
    else:
        vault_dir = resolve_vault(project_dir)
    if vault_dir and not vault_dir.is_dir():
        print(f"warn: vault-dir not a directory: {vault_dir}", file=sys.stderr)
        vault_dir = None

    report = run_scan(project_dir, vault_dir, include_legacy=args.include_legacy,
                      scope=scope)
    report["cost"] = cost

    payload = json.dumps(report, indent=2, default=str)
    if args.out:
        Path(args.out).expanduser().write_text(payload + "\n")
        print(f"[ramasse_scan] wrote {args.out}", file=sys.stderr)
    else:
        print(payload)

    # Stderr summary
    summary = report["summary"]
    print(
        f"[ramasse_scan] {report['meta']['project_slug']}: "
        f"{report['meta']['files_scanned']} files, "
        f"{summary['drift_items']} drift items, "
        f"{summary['wikilinks_broken_pct']}% broken wikilinks",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
