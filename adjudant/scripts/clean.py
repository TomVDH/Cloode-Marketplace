#!/usr/bin/env python3
"""Adjudant clean — the cleanup verb, net-subtractive by construction.

`tidy` and `ramasse` were one job split across two verbs and two cadences.
`clean` is the surface sweep; `clean --deep` adds the structural detectors
that were ramasse's analysis phase. Both are read-only until you apply.

The contract, enforced in `_vault_write.VaultWriteGuard` rather than promised
in prose: clean may rewrite a file in place and it may remove one. It may not
create a vault file. Anything it cannot fix by rewriting, it reports.

Surface features:
  1. Rebuild an EXISTING `_index.md` in every project subfolder with >=2
     same-type siblings. A folder with no index is reported as a gap, never
     filled: creating one is the single write that made the old verb add more
     than it removed, and plan 4 owns index generation.
  2. Bump `updated:` frontmatter on touched files (doc, brief, note types)
  3. Rewrite `[text](path.md)` -> `[[path-stem|text]]` when path resolves in vault
  4. Frontmatter schema repair per FIELD_SCHEMA: strip unknown fields, migrate
     the one legacy key with a live target (node_type -> type), and normalise
     decision-status aliases (accepted/locked/current -> active).
     Task-status aliases are accepted input and never rewritten.

Deep pass (`--deep`), read-only, no guard needed:
  folder drift, frontmatter drift, type drift, naming violations, artefact
  naming, wikilink form violations, broken wikilinks, doc/decision mismatches.

Tag normalisation was feature 3 until v3 and is gone with the tag buckets.
A `tags:` block is a field no template declares, so feature 4 strips it as an
ordinary unknown field: the general mechanism rather than a rule of its own.

Idempotent: a second run with no fresh drift = no changes.

Phases:
  detect   — print one of: 'fresh' | 'preview' | 'applied'
  preview  — write the proposed changes to scratch (read-only sweep)
  apply    — backup live files to scratch, then apply preview

Scratch is $TMPDIR/adjudant/{project}/{clean-preview,clean-backup} (see
_scratch.py), never the vault, and backups keep the newest BACKUP_KEEP.

CLI:
    python3 clean.py detect  --project-dir PATH
    python3 clean.py preview --project-dir PATH [--vault-dir PATH] [--deep]
                             [--folder SUBDIR]
    python3 clean.py apply   --project-dir PATH

See docs/superpowers/2026-05-26-adjudant-tidy-ramasse-log.design.md.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from _cost import cost_block, read_threshold, stat_walk
from _scratch import BACKUP_KEEP, prune_backups, scratch_dir
from _vault_walk import (
    FIELD_SCHEMA,
    DECISION_STATUS_ALIASES,
    DEFAULT_SKIP,
    MD_LINK_RE,
    VaultFile,
    build_vault_index,
    is_checkable_wikilink,
    parse_frontmatter,
    resolve_scope,
    resolve_vault,
    resolve_wikilink,
    schema_drift_for_file,
    scope_rel,
    smart_project_dir, VaultUnresolvableError,
    walk_project,
)
from _vault_write import VaultCreateRefused, VaultWriteGuard

# Task-status alias set for feature 5's drift check (same defensive import
# as status.py; aliases are accepted input, never rewritten by clean).
try:
    from board import STATUS_TO_COLUMN
    _TASK_STATUS_ALIASES: set = set(STATUS_TO_COLUMN)
except Exception:  # pragma: no cover - degraded, schema phase still strips
    _TASK_STATUS_ALIASES = set()


# Scratch *kinds*, not directory names: these resolve under $TMPDIR via
# _scratch.scratch_dir, never inside the vault. Renamed with the verb, which
# state-contract.md rule 4 calls out as the unsafe kind of change - the
# statusline probes these two paths, so it moves in the same commit.
PREVIEW_KIND = "clean-preview"
BACKUP_KIND = "clean-backup"


def preview_dir(project_dir: Path) -> Path:
    return scratch_dir(project_dir, PREVIEW_KIND)


def backup_root(project_dir: Path) -> Path:
    return scratch_dir(project_dir, BACKUP_KIND)

DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-(.*))?$")

# Types eligible for `updated:` bump (per spec)
UPDATED_BUMP_TYPES = {"doc", "project", "note"}


# ============================================================
# Detection
# ============================================================


def detect_phase(project_dir: Path) -> str:
    """Return 'preview' if preview dir exists, 'applied' if backup but no preview,
    else 'fresh'."""
    preview = preview_dir(project_dir)
    backup = backup_root(project_dir)
    if preview.is_dir():
        return "preview"
    if backup.is_dir() and any(backup.iterdir()):
        return "applied"
    return "fresh"


# ============================================================
# Wikilink form fix
# ============================================================


# Split-with-capture: odd segments are inline-code spans, left untouched
_INLINE_CODE_SPLIT_RE = re.compile(r"(`[^`\n]+`)")


def fix_wikilink_form(body: str, vault_index: set[str]) -> tuple[str, int]:
    """Rewrite `[text](path.md)` → `[[path|text]]` IFF the path resolves.

    Resolution is BY PATH: the href has to name the file from the vault root,
    or from the project slug down. A href that names only a sibling filename
    is left as a markdown link, because the wikilink it used to become was a
    bare stem — one that matched any file of that name anywhere in the vault,
    and pointed a reader at an arbitrary one. Obsidian resolves the markdown
    form natively, so leaving it alone loses nothing and invents nothing.

    Returns (new_body, fix_count). Skips fenced + 4-space-indented code blocks
    and inline-code spans (mirrors what the detectors count). Preserves heading
    anchors (`[t](n.md#Sec)` → `[[n#Sec|t]]`). Leaves `./`/`../` relative links
    untouched.
    """
    if not vault_index:
        return body, 0
    fixed_count = 0
    out_lines = []
    in_fenced = False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            in_fenced = not in_fenced
            out_lines.append(line)
            continue
        if in_fenced:
            out_lines.append(line)
            continue
        # Indented code block (same heuristic as extract_markdown_md_links)
        if line.startswith("    ") and line.lstrip()[:1] not in ("-", "*", "+", "|", "["):
            out_lines.append(line)
            continue
        def _sub(m):
            nonlocal fixed_count
            text = m.group(1)
            path = m.group(2)
            if path.startswith(("./", "../")):
                return m.group(0)
            stem, _, anchor = path.partition("#")
            if resolve_wikilink(stem, vault_index):
                # Compute display stem without extension
                no_ext = stem[:-3] if stem.endswith(".md") else stem
                target = f"{no_ext}#{anchor}" if anchor else no_ext
                stem_basename = no_ext.split("/")[-1]
                # If display text matches the basename, skip the alias
                if text.strip() == stem_basename or text.strip() == no_ext:
                    fixed_count += 1
                    return f"[[{target}]]"
                fixed_count += 1
                return f"[[{target}|{text}]]"
            return m.group(0)
        segments = _INLINE_CODE_SPLIT_RE.split(line)
        rebuilt = "".join(
            seg if i % 2 else MD_LINK_RE.sub(_sub, seg)
            for i, seg in enumerate(segments)
        )
        out_lines.append(rebuilt)
    return "\n".join(out_lines), fixed_count


# ============================================================
# Index regeneration
# ============================================================


def _capitalize_folder_name(name: str) -> str:
    name = name.replace("-", " ").replace("_", " ")
    return " ".join(w.capitalize() for w in name.split())


def _sort_entries(entries: list[Path]) -> list[Path]:
    """Sort: reverse-chronological for date-prefixed, alphabetical otherwise.
    Mixed sets: date entries first (reverse chrono), then plain alphabetical."""
    dated = []
    plain = []
    for f in entries:
        m = DATE_PREFIX_RE.match(f.stem)
        if m and m.group(1):
            dated.append((m.group(1), f))
        else:
            plain.append(f)
    if dated and not plain:
        return [f for _, f in sorted(dated, key=lambda x: x[0], reverse=True)]
    if not dated and plain:
        return sorted(plain, key=lambda x: x.stem)
    return (
        [f for _, f in sorted(dated, key=lambda x: x[0], reverse=True)]
        + sorted(plain, key=lambda x: x.stem)
    )


# A bullet the rebuild could have produced tells us nothing; one with any other
# alias is a line a human wrote, and the filename cannot reconstruct it.
_CURATED_BULLET_RE = re.compile(r"^\s*-\s+\[\[([^\]|#]+?)(?:#[^\]|]*)?\|(.+?)\]\]\s*$")


def harvest_aliases(section_lines: list[str]) -> dict[str, str]:
    """`{link target: alias}` for every aliased bullet in an Entries section.

    First occurrence wins, matching the rest of clean's duplicate handling.
    """
    found: dict[str, str] = {}
    for ln in section_lines:
        m = _CURATED_BULLET_RE.match(ln)
        if m:
            found.setdefault(m.group(1).strip(), m.group(2).strip())
    return found


def _format_entry_bullet(f: Path, aliases: Optional[dict[str, str]] = None) -> str:
    """One index row. A curated alias for this entry outranks the generated
    one; regenerating over it discards the only authored content an index
    holds, and `stem.replace("-", " ")` cannot get it back."""
    stem = f.stem
    curated = (aliases or {}).get(stem)
    if curated:
        return f"- [[{stem}|{curated}]]"
    m = DATE_PREFIX_RE.match(stem)
    if m and m.group(1) and m.group(2):
        display = f"{m.group(1)} {m.group(2).replace('-', ' ')}"
    else:
        display = stem.replace("-", " ").replace("_", " ")
    return f"- [[{stem}|{display}]]"


_ENTRIES_HEADING_RE = re.compile(r"^##\s+entries\b", re.IGNORECASE)
_NEXT_H2_RE = re.compile(r"^##\s+")
_BULLET_LINK_RE = re.compile(r"^\s*-\s+\[\[")


def _find_entries_section_in_body(body: str) -> Optional[tuple[int, int]]:
    """Locate the `## Entries` section. Returns (content_start, content_end)
    as 0-indexed line bounds (end exclusive). Excludes the heading itself.
    Returns None if no `## Entries` heading exists.
    """
    lines = body.split("\n")
    heading_idx = None
    for i, line in enumerate(lines):
        if _ENTRIES_HEADING_RE.match(line.strip()):
            heading_idx = i
            break
    if heading_idx is None:
        return None
    start = heading_idx + 1
    end = len(lines)
    for i in range(start, len(lines)):
        if _NEXT_H2_RE.match(lines[i]):
            end = i
            break
    return (start, end)


def _section_is_bullet_list(lines: list[str]) -> bool:
    """True if section content is predominantly `- [[wikilink]]` bullets."""
    non_blank = [l for l in lines if l.strip()]
    if not non_blank:
        return True  # empty section — safe to fill
    bullets = [l for l in non_blank if _BULLET_LINK_RE.match(l)]
    return len(bullets) >= max(1, len(non_blank) // 2)


def upsert_index_content(
    existing_text: str,
    folder_name: str,
    entries: list[Path],
) -> tuple[str, str]:
    """Conservatively update an existing `_index.md`.

    Behaviour:
      - Bump `updated:` to today (if field present)
      - If body has `## Entries` heading with bullet-list content: replace bullets,
        keep heading + everything else. mode='upserted'.
      - If body has `## Entries` with non-bullet content (table, prose): leave
        body alone (only frontmatter changes). mode='frontmatter_only'.
      - If no `## Entries` heading: leave body alone. mode='frontmatter_only'.

    Returns (new_text, mode).
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # Frontmatter side: bump updated. An existing `tags:` block is left for
    # feature 4 to strip as an unknown field, on the pass that walks the file.
    new_text = _bump_updated_field(existing_text, today)

    # Body side: try entries upsert
    # Re-parse to get the body AFTER frontmatter changes
    fm2, body2 = parse_frontmatter(new_text)
    section = _find_entries_section_in_body(body2)
    if section is None:
        return new_text, "frontmatter_only"

    start, end = section
    body_lines = body2.split("\n")
    section_lines = body_lines[start:end]
    if not _section_is_bullet_list(section_lines):
        return new_text, "frontmatter_only"

    # Generate new entry bullets, carrying forward any alias a human curated
    # for an entry that still exists.
    sorted_entries = _sort_entries(entries)
    aliases = harvest_aliases(section_lines)
    new_bullets = [_format_entry_bullet(f, aliases) for f in sorted_entries]

    # Replace section content: keep leading/trailing blank lines if any in original style
    # Use one blank before bullets, one trailing blank
    new_section = [""] + new_bullets + [""]
    # Trim trailing blank from input section if we'd duplicate
    while new_section and new_section[-1] == "" and end < len(body_lines) and body_lines[end - 1] == "":
        # already blank-padded
        break

    new_body_lines = body_lines[:start] + new_section + body_lines[end:]
    new_body = "\n".join(new_body_lines)

    # Reassemble: keep frontmatter from new_text, replace body
    new_text = _strip_then_prepend_body(new_text, new_body)
    return new_text, "upserted"


# ============================================================
# File content rewriter — surgical edit of frontmatter + body wikilinks
# ============================================================


def _bump_updated_field(text: str, today: str) -> str:
    """If frontmatter has `updated:`, set it to today. Does NOT add the field."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return text
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            close_idx = i
            break
    if close_idx is None:
        return text
    for i in range(1, close_idx):
        m = re.match(r"^(updated\s*:\s*).*$", lines[i])
        if m:
            lines[i] = f"{m.group(1)}{today}"
            break
    return "\n".join(lines)


def _frontmatter_close(lines: list[str]) -> Optional[int]:
    """Index of the closing --- line, or None when there is no block."""
    if not lines or lines[0].rstrip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return i
    return None


def _drop_frontmatter_keys(text: str, keys: set[str]) -> str:
    """Drop column-0 frontmatter keys plus their indented continuation lines
    (block lists and nested maps alike). Never touches the body."""
    lines = text.split("\n")
    close = _frontmatter_close(lines)
    if close is None or not keys:
        return text
    out = [lines[0]]
    i = 1
    while i < close:
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:", lines[i])
        if m and m.group(1) in keys:
            i += 1
            while i < close and (lines[i].startswith(" ") or lines[i].startswith("\t")):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out + lines[close:])


def _rename_frontmatter_key(text: str, old: str, new: str) -> str:
    """Rename a column-0 frontmatter key, value untouched."""
    lines = text.split("\n")
    close = _frontmatter_close(lines)
    if close is None:
        return text
    pat = re.compile(rf"^{re.escape(old)}(\s*:)")
    for i in range(1, close):
        if pat.match(lines[i]):
            lines[i] = pat.sub(f"{new}\\1", lines[i], count=1)
            break
    return "\n".join(lines)


def _set_frontmatter_scalar(text: str, key: str, value: str) -> str:
    """Set a scalar frontmatter value, preserving any trailing # comment.
    Narrow use: enum values (status), never quoted strings."""
    lines = text.split("\n")
    close = _frontmatter_close(lines)
    if close is None:
        return text
    for i in range(1, close):
        m = re.match(rf"^({re.escape(key)}\s*:\s*)([^#]*?)(\s*#.*)?$", lines[i])
        if m:
            lines[i] = f"{m.group(1)}{value}{m.group(3) or ''}"
            break
    return "\n".join(lines)


def _uncorroborated_type(file_type: Optional[str], fields: dict[str, Any]) -> Optional[str]:
    """Explain why `type:` is not to be trusted, or None when it is.

    The schema strip is destructive and reads `type:` as ground truth. That
    holds for a file adjudant wrote; it does not hold for a foreign file that
    acquired a colliding `type:` some other way — a Claude Code auto-memory
    note flattened by an external editor arrives as `type: project` carrying
    none of a brief's fields, and every real field it does carry then looks
    "unknown". Corroboration is the required set beyond `type` itself: a
    majority present means the declaration is backed by the file, a minority
    means the file is misclassified and the strip would be the data loss.
    """
    if file_type not in FIELD_SCHEMA:
        return None
    required = set(FIELD_SCHEMA[file_type]["required"]) - {"type"}
    if not required:
        return None
    present = sum(1 for k in required if k in fields)
    if present * 2 > len(required):
        return None
    return (f"type: {file_type} is not corroborated "
            f"({len(required) - present} of {len(required)} required fields missing) "
            f"— left untouched; retype the file or fill it in")


# ============================================================
# Deep pass — structural detectors, moved from ramasse_scan.py
#
# Read-only. They propose nothing and touch nothing, so no guard applies to
# them: a structural finding is a sentence for a human, not a rewrite. They
# run only on `--deep`, which is what "sparing, roughly quarterly" became
# once the two cadences stopped being two verbs.
# ============================================================


# Doc filename UPPERCASE rule — exceptions
DOC_NAME_EXCEPTIONS = {"brief", "_index", "_handoff"}


def _project_type(files: list[VaultFile]) -> Optional[str]:
    """Read project_type from brief.md frontmatter."""
    for f in files:
        if f.rel_path == Path("brief.md"):
            pt = f.frontmatter.fields.get("project_type")
            if isinstance(pt, str) and pt:
                return pt
    return None


# detect_folder_drift and _extra_folders were deleted in v3. Drift was measured
# against PROJECT_TYPE_DEFAULT_FOLDERS, the per-type folder scaffold; with no
# default set there is nothing for a folder to drift from, and the brief's
# `extra_folders:` existed only to excuse a folder from that comparison.

# Folders that never carry an index. Read only by detect_index_gaps below,
# which is the last thing in adjudant that asks the question — it moved here
# from _vault_walk when connect stopped scaffolding indexes.
INDEX_EXEMPT_FOLDERS: frozenset[str] = frozenset({
    "sessions", "images", "assets", "previews", "iterations", "_archive", "templates",
})


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


def detect_type_drift(files: list[VaultFile]) -> dict[str, Any]:
    """Files with a `type:` no template declares.

    The canonical set is the schema's own key set, so a kind stops being
    canonical the moment its template is deleted, with nothing here to edit.
    """
    counter: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for f in files:
        t = f.file_type
        if not t:
            continue
        if t not in FIELD_SCHEMA:
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
    non-vault paths are valid, and so is a href naming a sibling by filename
    alone, which resolves by path nowhere and would only ever have become a
    bare-stem wikilink.
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



def _structural_count(structural: dict[str, Any]) -> int:
    """Drift items across the deep detectors, or 0 when the pass did not run."""
    if not structural:
        return 0
    return (
        len(structural["frontmatter_drift"])
        + len(structural["type_drift"]["values"])
        + len(structural["naming_violations"])
        + len(structural["wikilink_form_violations"])
        + structural["broken_wikilinks"]["broken_count"]
        + len(structural["doc_decision_flags"])
    )


def run_deep_scan(
    project_dir: Path,
    files: list[VaultFile],
    vault_index: set[str],
    *,
    scope: Optional[str] = None,
) -> dict[str, Any]:
    """The structural drift catalog. Read-only; proposes nothing.

    Takes the file list `build_preview` already walked rather than walking
    again — the deep pass is the expensive half, and reading the project twice
    to answer one question was ramasse's own cost problem.
    """
    proj_type = _project_type(files)
    broken = detect_broken_wikilinks(files, vault_index) if vault_index else {
        "total_wikilinks": 0, "broken_count": 0, "broken_pct": 0.0,
        "top_broken_targets": [], "samples": [],
    }
    return {
        "project_type": proj_type,
        "files_scanned": len(files),
        "frontmatter_drift": detect_frontmatter_drift(files),
        "type_drift": detect_type_drift(files),
        "naming_violations": (detect_naming_violations(files)
                              + detect_artefact_naming(project_dir)),
        "wikilink_form_violations": (
            detect_wikilink_form_violations(files, vault_index) if vault_index else []),
        "broken_wikilinks": broken,
        "doc_decision_flags": detect_doc_decision_flags(files),
    }


# ============================================================
# Preview build
# ============================================================


def build_preview(
    project_dir: Path,
    vault_index: set[str],
    project_slug: Optional[str],
    deep: bool = False,
    scope: Optional[str] = None,
) -> dict[str, Any]:
    """Walk project, compute all proposed changes, return a change-set dict
    (not yet written to disk). Caller serialises it.

    The first three parameters are the signature every existing caller uses
    positionally. `deep` appends ramasse's structural detectors, which are
    read-only and propose nothing. `scope` narrows the walk to one project
    subfolder; folder drift is a question about the ROOT's shape, so a scoped
    run skips it rather than answering it against a fraction of the folders.
    """
    files = list(walk_project(project_dir))
    if scope:
        prefix = tuple(Path(scope).parts)
        files = [f for f in files if f.rel_path.parts[:len(prefix)] == prefix]
    today = datetime.now().strftime("%Y-%m-%d")

    # Bucket: per-file proposed full content (only when content changes)
    file_proposals: dict[str, dict[str, Any]] = {}
    # Index proposals — rebuilds of an index that already exists
    index_proposals: dict[str, dict[str, Any]] = {}
    # Folders that want an index and have none. Reported, never filled.
    index_gaps = detect_index_gaps(project_dir, files)

    # --- Feature 1: index rebuilds ---
    by_parent: dict[Path, list[VaultFile]] = defaultdict(list)
    for f in files:
        parent = f.rel_path.parent
        if parent == Path("."):
            continue
        by_parent[parent].append(f)

    for parent, members in by_parent.items():
        # Skip exempt folders
        if any(p in INDEX_EXEMPT_FOLDERS for p in parent.parts):
            continue
        non_index = [m for m in members if m.rel_path.name != "_index.md"]
        if len(non_index) < 2:
            continue
        idx_rel = str(parent / "_index.md")
        existing_path = project_dir / parent / "_index.md"

        if existing_path.is_file():
            try:
                existing = existing_path.read_text()  # strict: never write replaced bytes back
            except UnicodeDecodeError:
                continue
            proposed, mode = upsert_index_content(
                existing,
                folder_name=parent.name,
                entries=[m.rel_path for m in non_index],
            )
            if proposed.strip() != existing.strip():
                index_proposals[idx_rel] = {
                    "folder": str(parent),
                    "had_existing": True,
                    "mode": mode,
                    "entry_count": len(non_index),
                    # Hashed like a file proposal: `proposed` was computed FROM
                    # `existing`, so an edit landing between preview and apply
                    # is genuinely lost, not regenerated. The apply-time guard
                    # needs this to notice.
                    "original_hash": _hash_short(existing),
                    "proposed_content": proposed,
                }
        # A folder with no `_index.md` falls through: creating one was the
        # single write that made a cleanup verb add more than it removed, and
        # `_vault_write.VaultWriteGuard` now refuses it at apply time. It is
        # reported in `index_gaps` instead, and plan 4's generator, which owns
        # index surfaces, fills it.

    # --- Features 2-4: per-file edits ---
    schema_actions: dict[str, dict[str, Any]] = {}
    for f in files:
        try:
            # Strict decode: never round-trip errors="replace" text back to
            # disk — that would silently bake U+FFFD into the vault file.
            original = f.path.read_text()
        except UnicodeDecodeError:
            continue
        modified = original

        # Feature 3: wikilink form fix
        fm, body = parse_frontmatter(modified)
        new_body, wf_count = fix_wikilink_form(body, vault_index)
        if wf_count > 0:
            # Re-assemble: original frontmatter prefix + new body
            modified = _strip_then_prepend_body(modified, new_body)

        # Feature 4: frontmatter schema repair. Legacy-key migrations run on
        # any parse-clean block; unknown-field strips and decision-status
        # normalisation additionally need a canonical type (schema_drift).
        if f.frontmatter.has_block and not f.frontmatter.parse_error:
            fields = f.frontmatter.fields
            renames: list[tuple[str, str]] = []
            drops: set[str] = set()
            status_fix: Optional[tuple[str, str]] = None
            if "node_type" in fields:
                if "type" in fields:
                    drops.add("node_type")
                else:
                    renames.append(("node_type", "type"))
            # originSessionId used to migrate to source_session. Since v3 no
            # template declares source_session, so renaming into it would write
            # a field the next pass strips: it drops as an unknown field now.
            drift = schema_drift_for_file(f, _TASK_STATUS_ALIASES)
            unverified = _uncorroborated_type(f.file_type, fields) if drift else None
            if drift and not unverified:
                for k in drift.get("unknown_fields", ()):
                    if k != "node_type":
                        drops.add(k)
                si = drift.get("status_invalid")
                if si and f.file_type == "decision" and si.get("normalizable"):
                    status_fix = (si["value"], DECISION_STATUS_ALIASES[si["value"]])
            if unverified:
                # Reported, never acted on. The human decides whether the file
                # is mistyped or genuinely half-built; clean is not entitled to
                # strip content on the strength of a `type:` nothing backs up.
                schema_actions[str(f.rel_path)] = {"unverified_type": unverified}
            if renames or drops or status_fix:
                for old, new in renames:
                    modified = _rename_frontmatter_key(modified, old, new)
                if drops:
                    modified = _drop_frontmatter_keys(modified, drops)
                if status_fix:
                    modified = _set_frontmatter_scalar(modified, "status", status_fix[1])
                act: dict[str, Any] = {}
                if drops:
                    act["dropped"] = sorted(drops)
                if renames:
                    act["renamed"] = [f"{o} -> {n}" for o, n in renames]
                if status_fix:
                    act["status"] = f"{status_fix[0]} -> {status_fix[1]}"
                schema_actions[str(f.rel_path)] = act

        # Feature 2: bump updated (only if other changes happened, and only on eligible types)
        if modified != original and f.file_type in UPDATED_BUMP_TYPES:
            modified = _bump_updated_field(modified, today)

        if modified != original:
            rel = str(f.rel_path)
            file_proposals[rel] = {
                "original_hash": _hash_short(original),
                "proposed_hash": _hash_short(modified),
                "proposed_content": modified,
            }

    structural = run_deep_scan(project_dir, files, vault_index,
                               scope=scope) if deep else {}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_dir": str(project_dir),
        "project_slug": project_slug,
        "deep": deep,
        "scope": scope,
        "summary": {
            "files_modified": len(file_proposals),
            "indexes_rebuilt": len(index_proposals),
            "index_gaps": len(index_gaps),
            "schema_files": len(schema_actions),
            "total_changes": len(file_proposals) + len(index_proposals),
            "structural_findings": _structural_count(structural),
        },
        "file_proposals": file_proposals,
        "index_proposals": index_proposals,
        "index_gaps": index_gaps,
        "schema_actions": schema_actions,
        "structural_findings": structural,
    }


def _strip_then_prepend_body(text: str, new_body: str) -> str:
    """Replace the body portion of a file (keeping frontmatter intact)."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return new_body
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            close_idx = i
            break
    if close_idx is None:
        return new_body
    return "\n".join(lines[: close_idx + 1]) + "\n" + new_body


def _hash_short(s: str) -> str:
    """8-char hex content hash (for visual diff confidence in summary)."""
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


# ============================================================
# Preview writer (disk)
# ============================================================


def write_preview_to_disk(project_dir: Path, change_set: dict[str, Any]) -> Path:
    """Write the change_set to the out-of-vault preview dir. Returns its path."""
    preview = preview_dir(project_dir)
    preview.parent.mkdir(parents=True, exist_ok=True)
    if preview.exists():
        shutil.rmtree(preview)
    preview.mkdir(parents=True)

    # changes.json
    (preview / "changes.json").write_text(json.dumps(change_set, indent=2, default=str))

    # files/ tree
    files_root = preview / "files"
    files_root.mkdir()
    for rel, info in change_set["file_proposals"].items():
        target = files_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(info["proposed_content"])
    for rel, info in change_set["index_proposals"].items():
        target = files_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(info["proposed_content"])

    # summary.md
    summary = change_set["summary"]
    scope = change_set.get("scope")
    summary_lines = [
        "# Clean preview" + (" (deep)" if change_set.get("deep") else ""),
        "",
        f"Generated: {change_set['generated_at']}",
        f"Project: {change_set['project_slug']}",
    ]
    if scope:
        summary_lines.append(f"Scope: {scope}")
    summary_lines += [
        "",
        "## Summary",
        "",
        f"- Files to modify: {summary['files_modified']}",
        f"- Indexes to rebuild: {summary['indexes_rebuilt']}",
        f"- Index gaps reported: {summary.get('index_gaps', 0)}",
        f"- Total changes: {summary['total_changes']}",
    ]
    if change_set.get("deep"):
        summary_lines.append(
            f"- Structural findings: {summary.get('structural_findings', 0)}")
    summary_lines += [
        "",
        "## Index rebuilds",
        "",
    ]
    for rel, info in sorted(change_set["index_proposals"].items()):
        if info.get("mode") == "frontmatter_only":
            marker = "frontmatter-only"
        elif info.get("mode") == "upserted":
            marker = "upsert-entries"
        else:
            marker = "rewrite"
        summary_lines.append(f"- {marker}: `{rel}` ({info['entry_count']} entries)")
    if change_set.get("index_gaps"):
        summary_lines.append("")
        summary_lines.append("## Index gaps (reported, not filled)")
        summary_lines.append("")
        summary_lines.append("clean does not create vault files. These folders "
                             "want an `_index.md` and have none:")
        summary_lines.append("")
        for folder in change_set["index_gaps"]:
            summary_lines.append(f"- `{folder}`")
    summary_lines.append("")
    summary_lines.append("## File modifications")
    summary_lines.append("")
    for rel, info in sorted(change_set["file_proposals"].items()):
        summary_lines.append(f"- `{rel}` ({info['original_hash']} → {info['proposed_hash']})")
    if change_set.get("schema_actions"):
        summary_lines.append("")
        summary_lines.append("## Schema")
        summary_lines.append("")
        for rel, act in sorted(change_set["schema_actions"].items()):
            parts = []
            if act.get("renamed"):
                parts.append("rename " + ", ".join(act["renamed"]))
            if act.get("dropped"):
                parts.append("strip " + ", ".join(act["dropped"]))
            if act.get("status"):
                parts.append("status " + act["status"])
            summary_lines.append(f"- `{rel}`: {'; '.join(parts)}")
    structural = change_set.get("structural_findings") or {}
    if structural:
        summary_lines.append("")
        summary_lines.append("## Structural findings (deep pass, reported only)")
        summary_lines.append("")
        for label, key in (
            ("Frontmatter drift", "frontmatter_drift"),
            ("Naming violations", "naming_violations"),
            ("Wikilink form violations", "wikilink_form_violations"),
            ("Doc/decision flags", "doc_decision_flags"),
        ):
            summary_lines.append(f"- {label}: {len(structural[key])}")
        summary_lines.append(
            f"- Non-canonical `type:` values: {len(structural['type_drift']['values'])}")
        summary_lines.append(
            f"- Broken wikilinks: {structural['broken_wikilinks']['broken_count']} "
            f"({structural['broken_wikilinks']['broken_pct']}%)")
        summary_lines.append("")
        summary_lines.append("Full detail is in `changes.json` under "
                             "`structural_findings`. Every one of these needs a "
                             "human decision; none is applied.")
    summary_lines.append("")
    summary_lines.append("## Next steps")
    summary_lines.append("")
    summary_lines.append("- Review the proposed files under `files/`")
    summary_lines.append("- To apply: `python3 clean.py apply --project-dir <PATH>`")
    summary_lines.append(f"- To discard: delete `{preview}`")
    (preview / "summary.md").write_text("\n".join(summary_lines) + "\n")

    return preview


# ============================================================
# Apply phase
# ============================================================


def _contained(root: Path, rel: str) -> Optional[Path]:
    """`root/rel` resolved, or None when it escapes `root`.

    changes.json is editable by design (the preview window exists so a human
    or agent can review it), so its keys are untrusted input: a tampered
    `../escaped.md` used to be written outside the project, bypassing both the
    backup and the walker's skip set.
    """
    try:
        root_r = root.resolve()
        target = (root_r / rel).resolve()
    except (OSError, ValueError):
        return None
    if target == root_r or root_r not in target.parents:
        return None
    return target


SKIPPED_NOTE_NAME = "SKIPPED-STALE.txt"

# Why a proposal was refused. Four different stories: an edit is not a
# deletion, and neither is a proposal the write guard turned down.
SKIP_REASONS: dict[str, str] = {
    "changed": "edited since preview, applying would eat that edit",
    "vanished": "deleted or renamed since preview, applying would resurrect it",
    "unreadable": "could not be read to compare against the preview",
    "refused": "clean may not create a vault file and nothing was there to rewrite",
}


def _skip_reason(
    live: Path,
    original_hash: Optional[str],
) -> Optional[str]:
    """A SKIP_REASONS key when this proposal must not be applied, else None.

    The proposal was computed FROM the live bytes, so anything that no longer
    matches those bytes means applying it would destroy newer work. A missing
    file counts: a deletion or rename between the two phases is an intentional
    act, and copying the proposal back would silently undo it.

    "refused" is not decided here. It is what the write guard says when a
    proposal names a path holding no file — a stale preview from before clean
    stopped generating indexes, or a tampered `changes.json`.
    """
    if not original_hash:
        return None  # pre-guard preview: nothing recorded to compare against
    if not live.is_file():
        return "vanished"
    try:
        if _hash_short(live.read_text()) != original_hash:
            return "changed"
    except (OSError, UnicodeDecodeError):
        return "unreadable"
    return None


def _write_skipped_note(backup_dir: Path, skipped: list[tuple[str, str]]) -> None:
    """Record refused proposals. Body lines are `reason<TAB>path` so that
    `read_skipped_note` reads back exactly what was written."""
    legend = "\n".join(f"  {key}: {why}" for key, why in SKIP_REASONS.items())
    body = "\n".join(f"{reason}\t{rel}" for rel, reason in sorted(skipped))
    (backup_dir / SKIPPED_NOTE_NAME).write_text(
        "These paths no longer match what the preview was built from, so they\n"
        "were left alone. Re-run `clean preview` to fold the current state in.\n\n"
        f"{legend}\n\n{body}\n"
    )


def read_skipped_note(backup_dir: Path) -> list[dict[str, str]]:
    """Parse a SKIPPED-STALE.txt back into [{'path': ..., 'reason': ...}].

    Empty list when nothing was skipped. Only tab-bearing lines are entries,
    which keeps the prose header and the reason legend out of the result.
    """
    note = backup_dir / SKIPPED_NOTE_NAME
    if not note.is_file():
        return []
    entries: list[dict[str, str]] = []
    for line in note.read_text().splitlines():
        if "\t" not in line:
            continue
        reason, _, rel = line.partition("\t")
        entries.append({"path": rel, "reason": reason})
    return entries


def apply_preview(project_dir: Path) -> Path:
    """Apply the scratch preview to live files. Returns backup dir path.

    Every proposal is gated five ways before it can touch a live file: the
    target must stay inside the project, the path must not have been applied
    already in this same run, the live file must still match what the proposal
    was computed from (see `_skip_reason`), the pre-change copy must land in a
    backup dir that no concurrent or retried apply can overwrite, and the
    write itself goes through `VaultWriteGuard`, which refuses any path not
    already holding a file. The last one is the contract: clean rewrites and
    removes, and cannot add.
    """
    preview = preview_dir(project_dir)
    if not preview.is_dir():
        raise RuntimeError(f"no preview at {preview}")
    changes_path = preview / "changes.json"
    if not changes_path.is_file():
        raise RuntimeError(f"corrupt preview: {changes_path} missing")
    change_set = json.loads(changes_path.read_text())

    # Unique per apply: second-granularity dirs with exist_ok=True let a retry
    # inside the same second overwrite the ONLY pre-change backup with
    # already-cleaned content, making the original unrecoverable.
    backup_root_dir = backup_root(project_dir)
    backup_root_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(tempfile.mkdtemp(prefix=f"{timestamp}-", dir=backup_root_dir))

    files_root = preview / "files"
    skipped: list[tuple[str, str]] = []
    handled: set[str] = set()

    # Backup + apply. Every live write in this loop goes through the guard.
    guard = VaultWriteGuard(project_dir)
    for rel_set in (change_set["file_proposals"], change_set["index_proposals"]):
        for rel, info in rel_set.items():
            live = _contained(project_dir, rel)
            proposed = _contained(files_root, rel)
            if live is None or proposed is None or not proposed.is_file():
                continue
            # `write_preview_to_disk` collapses both proposal dicts into one
            # `files/<rel>`, so a path in both (an `_index.md` that also needs
            # a schema fix) has exactly ONE proposed body and must be
            # applied exactly once. A second pass would compare the live file
            # against a hash this run just invalidated (a false stale report)
            # and overwrite the pre-change backup with already-cleaned content.
            if rel in handled:
                continue
            handled.add(rel)
            # changes.json is editable by design, so `info` is untrusted too.
            info = info if isinstance(info, dict) else {}
            reason = _skip_reason(live, info.get("original_hash"))
            if reason:
                skipped.append((rel, reason))
                continue
            try:
                body = proposed.read_text()
            except (OSError, UnicodeDecodeError):
                skipped.append((rel, "unreadable"))
                continue
            # Backup live (if exists)
            if live.is_file():
                backup_target = backup_dir / (rel + ".legacy")
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(live, backup_target)
            # Apply. No mkdir for the parent: a proposal whose folder does not
            # exist can only be a create, which the guard refuses anyway.
            try:
                guard.rewrite(live, body)
            except VaultCreateRefused:
                skipped.append((rel, "refused"))

    if skipped:
        _write_skipped_note(backup_dir, skipped)

    # Clean up preview
    shutil.rmtree(preview)
    prune_backups(backup_root_dir, BACKUP_KEEP)
    return backup_dir


# ============================================================
# CLI
# ============================================================


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="clean.py",
        description="Adjudant clean — cleanup sweep (preview / apply).",
    )
    parser.add_argument("phase", choices=["detect", "preview", "apply"])
    parser.add_argument("--project-dir", default=".", help="Project root (default: cwd)")
    parser.add_argument("--vault-dir", help="Vault root (default: resolved from breadcrumb)")
    parser.add_argument("--deep", action="store_true",
                        help="Add the structural detectors (was /adjudant ramasse). "
                             "Read-only: they report, they never propose a write")
    parser.add_argument("--folder", help="Scope the walk to one project subfolder "
                        "(e.g. 'notes'); the preview header states the scope")
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
    # A scoped run estimates the subtree it will read (same as dream.py).
    files_n, n_bytes = stat_walk(scope_dir)
    cost = cost_block(files_n, n_bytes, read_threshold(code_root))
    if args.estimate_only:
        print(json.dumps({"scope": scope, "cost": cost}, indent=2))
        return 0

    if args.phase == "detect":
        print(json.dumps({"state": detect_phase(project_dir), "cost": cost}, indent=2))
        return 0

    # Resolve vault for both preview + apply (preview needs index for feature 4;
    # apply just needs project_dir but we keep the same flag for parity).
    vault_dir: Optional[Path]
    if args.vault_dir:
        vault_dir = Path(args.vault_dir).expanduser().resolve()
    elif vault_hint:
        vault_dir = vault_hint
    else:
        vault_dir = resolve_vault(project_dir)

    # Project slug: from brief.md
    slug: Optional[str] = None
    brief = project_dir / "brief.md"
    if brief.is_file():
        fm, _ = parse_frontmatter(brief.read_text(errors="replace"))
        s = fm.fields.get("slug")
        if isinstance(s, str):
            slug = s

    if args.phase == "preview":
        if detect_phase(project_dir) == "preview":
            print(f"error: preview already exists at {preview_dir(project_dir)}", file=sys.stderr)
            print("delete it or run 'apply' to commit it", file=sys.stderr)
            return 1
        vault_index = build_vault_index(vault_dir) if vault_dir and vault_dir.is_dir() else set()
        change_set = build_preview(project_dir, vault_index, slug,
                                   deep=args.deep, scope=scope)
        preview = write_preview_to_disk(project_dir, change_set)
        print(f"[clean] preview written to {preview}", file=sys.stderr)
        summary = change_set["summary"]
        print(
            f"[clean] {summary['total_changes']} changes "
            f"({summary['files_modified']} files, {summary['indexes_rebuilt']} indexes)",
            file=sys.stderr,
        )
        if summary.get("index_gaps"):
            print(f"[clean] {summary['index_gaps']} folder(s) want an index and "
                  f"have none; clean reports them and does not create files",
                  file=sys.stderr)
        if args.deep:
            print(f"[clean] deep pass: {summary.get('structural_findings', 0)} "
                  f"structural finding(s), reported only", file=sys.stderr)
        # Stdout: compact JSON of the summary block for Claude
        print(json.dumps({**summary, "scope": scope, "cost": cost}))
        return 0

    if args.phase == "apply":
        if detect_phase(project_dir) != "preview":
            print(f"error: no preview at {preview_dir(project_dir)}; run 'preview' first", file=sys.stderr)
            return 1
        backup_dir = apply_preview(project_dir)
        skipped = read_skipped_note(backup_dir)
        print(f"[clean] applied; backup at {backup_dir}", file=sys.stderr)
        if skipped:
            # Never let a skip be silent: the user asked for these changes.
            print(f"[clean] {len(skipped)} path(s) LEFT ALONE, they no longer match "
                  f"the preview:", file=sys.stderr)
            for item in skipped:
                print(f"[clean]   {item['path']}: "
                      f"{SKIP_REASONS.get(item['reason'], item['reason'])}",
                      file=sys.stderr)
            print("[clean] re-run preview to fold the current state in", file=sys.stderr)
        print(json.dumps({"backup_dir": str(backup_dir), "skipped_stale": skipped}))
        return 0

    return 2  # unreachable


if __name__ == "__main__":
    sys.exit(cli_main())
