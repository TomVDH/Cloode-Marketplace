#!/usr/bin/env python3
"""Adjudant truth checks — what a file's existence or a date comparison proves.

`check` used to grade shape: 110 frontmatter keys against a schema, producing
99 failures of which 69 came from a folder adjudant does not own. Nobody acted
on any of them, and meanwhile a project's AGENTS.md carried five false
statements, 44 task cards sat open where nobody could see them, and a spec had
been agreed for two months with no card citing it.

Every finding here traces to one of those. Every one is settled mechanically,
in seconds, so the report is safe to run constantly. Reading prose to find what
only comprehension finds is `dream`'s job, and dream is the expensive one.

The output is a read-only report in three bands, ordered by the cost of being
wrong. It never gates anything: a check that refuses a write is a check people
learn to route around.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterator, Optional

from _vault_walk import (
    ALIAS_SEP_RE as _ALIAS_SEP_RE,
    VaultFile,
    build_vault_index,
    is_checkable_wikilink,
    is_unowned,
    resolve_wikilink,
    walk_project,
)

# Ordered by the cost of being wrong. "wrong-now" is a statement the vault
# makes that is false today; "going-stale" is one that is drifting; and
# "worth-a-look" is a judgement call for a person.
BANDS: tuple[str, ...] = ("wrong-now", "going-stale", "worth-a-look")


@dataclass
class Finding:
    band: str
    kind: str
    file: str       # project-relative path, or "" for a project-level finding
    detail: str

    def as_dict(self) -> dict:
        return {"band": self.band, "kind": self.kind,
                "file": self.file, "detail": self.detail}


@dataclass
class _Ctx:
    """Everything a detector may read. Built once, never mutated."""
    project_dir: Path
    slug: str
    vault: Optional[Path]
    code_root: Optional[Path]
    today: date
    files: list           # list[VaultFile]: owned, and not generated
    all_owned: list       # list[VaultFile]: owned, generated pages included
    index: set            # set[str] from build_vault_index
    by_type: dict         # str -> list[VaultFile], built from `files`

    def fields(self, vf: "VaultFile") -> dict:
        return vf.frontmatter.fields

    def rel(self, vf: "VaultFile") -> str:
        return str(vf.rel_path)


def _is_generated(vf: "VaultFile") -> bool:
    """True when another script owns and overwrites this file every run."""
    return bool(vf.frontmatter.fields.get("source"))


def _wikilink_target(value: Any) -> Optional[str]:
    """The full target a frontmatter wikilink value points at, or None.

    `_vault_walk._wikilink_stem` is the older sibling and is no use here: it
    returns the BARE stem, which since v3 resolves against nothing. A path is
    the whole point — `[[demo/specs/spec-018|SPEC-018]]` names one file, and
    `spec-018` names every project's copy of it.

    Both spellings of the field have to read the same. Obsidian's Properties
    editor and a hand-written YAML line produce `spec: [[demo/specs/s-1]]`
    unquoted, which the frontmatter parser reads as a one-item list holding
    `[demo/specs/s-1]`; only the quoted spelling arrives as a plain string.
    Reading the unquoted one literally reported every working link in the
    vault as broken, in the band that costs the most to get wrong.
    """
    if isinstance(value, list):
        # A one-item list is the unquoted `[[…]]` above. A longer one is a
        # genuine YAML list, which this field is not, and an empty one is the
        # template's unfilled `superseded_by:` round-tripped by an editor.
        if len(value) != 1:
            return None
        value = value[0]
    if value is None:
        return None
    target = str(value).strip().strip('"').strip("'").strip()
    target = target.lstrip("[").rstrip("]").strip()
    target = _ALIAS_SEP_RE.split(target, maxsplit=1)[0].strip()
    return target.split("#", 1)[0].strip() or None


# ============================================================
# Band: wrong-now — names something that is not there
# ============================================================


def _check_broken_wikilinks(ctx: _Ctx) -> Iterator[Finding]:
    """733 of 9611 links were broken, at 7.6%.

    Embeds and attachment names are not checkable and never counted. The index
    resolves by path only since v3, so a link that does not say which project
    it means is reported rather than silently matched to an arbitrary file.
    """
    if not ctx.index:
        return
    for vf in ctx.files:
        for wl in vf.wikilinks:
            if not is_checkable_wikilink(wl):
                continue
            if resolve_wikilink(wl.target, ctx.index):
                continue
            yield Finding("wrong-now", "broken-wikilink", ctx.rel(vf),
                          f"line {wl.line}: [[{wl.target}]] resolves to nothing")


def _check_superseded_target_missing(ctx: _Ctx) -> Iterator[Finding]:
    """`superseded_by` is written only when true, and must point at a file."""
    if not ctx.index:
        return
    for vf in ctx.files:
        target = _wikilink_target(ctx.fields(vf).get("superseded_by"))
        if not target:
            continue
        if resolve_wikilink(target, ctx.index):
            continue
        yield Finding("wrong-now", "superseded-target-missing", ctx.rel(vf),
                      f"superseded_by points at {target!r}, which does not exist")


def _check_task_spec_missing(ctx: _Ctx) -> Iterator[Finding]:
    """`spec:` is a wikilink, not a bare code, so this is checkable at all.

    SPEC-012 sat agreed for two months with no card citing it and no way to
    notice; a bare `SPEC-012` string could never have been resolved.
    """
    if not ctx.index:
        return
    for vf in ctx.by_type.get("task", []):
        target = _wikilink_target(ctx.fields(vf).get("spec"))
        if not target:
            continue
        if resolve_wikilink(target, ctx.index):
            continue
        yield Finding("wrong-now", "task-spec-missing", ctx.rel(vf),
                      f"cites spec {target!r}, which was never written")


# The brief's `## Where things are` table. Row one cell is the label, row two
# is the value.
_TABLE_ROW_RE = re.compile(r"^\|([^|]*)\|([^|]*)\|\s*$")


def _is_a_claim_about_this_disk(value: str) -> bool:
    """False when a repo cell says something no stat can settle.

    Three ways it can. `_render.render` leaves an unfilled placeholder as
    `{Its Name}` on purpose, and the brief template ships `{path or url}`, so
    a braced value is a blank waiting to be filled and not a moved repo — the
    unguarded version opened every new project's first report with that lie.
    An elided path (`~/…/HubSpot - Nightly`) is a person shortening a real
    one. And a value that is not absolute after `~` expansion is measured
    against whatever directory the command ran from, which made the same
    brief clean from one shell and wrong from the next; `TomVDH/toolshed` is
    a perfectly good answer to "path or url" and names no directory here.
    """
    if value.startswith("{") and value.endswith("}"):
        return False
    if "…" in value or "..." in value:
        return False
    if "://" in value:
        return False                # a URL is not a path we can stat
    return Path(value).expanduser().is_absolute()


def _brief_repo_path(brief_body: str) -> Optional[str]:
    for line in brief_body.split("\n"):
        m = _TABLE_ROW_RE.match(line.rstrip())
        if not m:
            continue
        if m.group(1).strip().lower() != "repo":
            continue
        value = m.group(2).strip().strip("`")
        return value or None
    return None


def _check_brief_repo_missing(ctx: _Ctx) -> Iterator[Finding]:
    """A brief's repo path that no longer resolves on disk."""
    brief = ctx.project_dir / "brief.md"
    try:
        body = brief.read_text(errors="replace")
    except OSError:
        return
    value = _brief_repo_path(body)
    if not value or not _is_a_claim_about_this_disk(value):
        return
    if Path(value).expanduser().exists():
        return
    yield Finding("wrong-now", "brief-repo-missing", "brief.md",
                  f"repo path {value!r} does not resolve on this machine")


# Tasks 11 to 14 append to this tuple. Order inside a band is the order
# findings are reported in, so keep the most concrete first.
#
# There is deliberately NO naming-convention detector. Two consecutive dream
# reports dismissed the `_archive/` naming finding in identical words, which
# is the tool spending the same hour twice. A convention is either enforced by
# `place()` at write time or it is not enforced, and reporting one nobody
# asked about is how a report becomes something people stop reading.
_DETECTORS: tuple = (
    _check_broken_wikilinks,
    _check_superseded_target_missing,
    _check_task_spec_missing,
    _check_brief_repo_missing,
)


# ============================================================
# Entry point
# ============================================================


def truth_report(project_dir: Path, *, vault: Optional[Path] = None,
                 code_root: Optional[Path] = None,
                 today: Optional[date] = None) -> dict[str, Any]:
    """Every truth finding for one project, banded and ordered. Reads only.

    Files under an unowned folder are excluded outright: adjudant does not own
    `memory/`'s format and cannot fix what it finds there. Generated pages —
    the ones carrying `source:` — are excluded from every detector except the
    one that is about them, because their script rewrites them every run and
    nagging about the output is nagging about the wrong file.
    """
    today = today or date.today()
    owned = [vf for vf in walk_project(project_dir)
             if not is_unowned(vf.rel_path)]
    checkable = [vf for vf in owned if not _is_generated(vf)]
    by_type: dict[str, list] = {}
    for vf in checkable:
        by_type.setdefault(vf.file_type or "", []).append(vf)

    ctx = _Ctx(
        project_dir=project_dir,
        slug=project_dir.name,
        vault=vault,
        code_root=code_root,
        today=today,
        files=checkable,
        all_owned=owned,
        index=build_vault_index(vault) if vault and vault.is_dir() else set(),
        by_type=by_type,
    )

    findings: list[Finding] = []
    for detector in _DETECTORS:
        findings.extend(detector(ctx))

    band_rank = {b: i for i, b in enumerate(BANDS)}
    findings.sort(key=lambda f: (band_rank.get(f.band, len(BANDS)),
                                 f.kind, f.file, f.detail))
    counts = {b: 0 for b in BANDS}
    for f in findings:
        counts[f.band] = counts.get(f.band, 0) + 1
    return {
        "findings": [f.as_dict() for f in findings],
        "counts": counts,
        "checked": len(owned),
    }
