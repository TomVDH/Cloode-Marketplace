#!/usr/bin/env python3
"""Generate the public twin's adjudant from this marketplace's copy.

The twin is `furtive-follies`, a reduced public build. It used to be a
hand-maintained fork, which meant every shared edit had to be made twice and
the trees drifted between edits. v3 moved every legitimate difference into
`adjudant/scripts/build-profile.json` and `command-metadata.json`, so the rest
of the tree can simply be copied.

The twin also held code that existed nowhere else — the guided vault setup —
so the failure this script is built around is a regeneration that drops
something and reports success. Three rules prevent it:

  1. The back-port guard runs first. If any marker in
     `test_backport_guard.BACKPORT_MARKERS` is missing from THIS tree, nothing
     is planned and the run exits 2.
  2. The twin is public, so the leak gate runs next. If
     `test_no_personal_identifiers.leaks()` finds a client, a person or the
     marketplace named in a shared file, nothing is planned and the run exits
     2. Publishing a name is the one mistake here that cannot be taken back.
  3. Every deletion must trace back to data: a file listed by a `full`-audience
     verb, a `full`-audience content reference, the reference doc of a
     capability this build declares, or a path named in RETIRED. A file in the
     twin that the data cannot explain is reported as unexplained and never
     touched, and `--apply` exits 3 rather than proceeding.

Usage:
    python3 scripts/generate_twin.py --twin PATH            # dry run, the default
    python3 scripts/generate_twin.py --twin PATH --apply

Stdlib only. Idempotent: a second `--apply` reports nothing to do.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import sys
from pathlib import Path
from typing import NamedTuple, Optional

MAIN_ROOT = Path(__file__).resolve().parent.parent

# Never copied: it is the file a build is allowed to differ in.
PROFILE_FILE = "scripts/build-profile.json"

# Written by render_verb_surfaces.py inside the twin after the copy, so a
# straight copy of main's version would be wrong for one moment and confusing
# for longer.
GENERATED = frozenset({
    "scripts/command-metadata.json",
    "skills/adjudant/SKILL.md",
    "README.md",
    ".claude-plugin/plugin.json",
})

# Two of the four carry prose the renderer does not own, so rendering alone
# cannot bring them forward: the renderer only rewrites the regions between its
# markers, and the twin's copies were written before the markers existed.
# Leaving them therefore left the twin's SKILL.md routing to sync.md, check.md,
# sitrep.md and tidy.md — four docs this same run deletes. They are seeded with
# main's file first, then rendered down to this build's audience.
#
# The other two have their own sync functions because a plain copy would be
# wrong: plugin.json carries the twin's identity, and command-metadata.json
# carries the twin's version and its audience-filtered verb list.
SEEDED = ("skills/adjudant/SKILL.md", "README.md")

# plugin.json keys that belong to the repo, not to the build.
IDENTITY_KEYS = ("name", "version", "author", "homepage", "repository",
                 "license", "keywords")

# Paths retired from the product, each with the reason. The twin predates v3
# and still carries them; no build ships them again.
#
# This is the third kind of difference, and the plan only knew two. A file the
# twin has and main does not is either audience-gated (`full_only_paths`) or
# something to back-port. These are neither: they belong to four verbs that
# were folded into `status` and `clean`, and to a template set the
# templates-are-the-schema redesign replaced. Nothing wants them back, and no
# verb entry is left to attach them to.
#
# It is a deletion licence, so it is held to the same standard as the rest:
# one line per path, never a pattern, and `_retired()` subtracts anything this
# tree still ships, so a stale tombstone cannot delete live code.
RETIRED = {
    "scripts/check.py": "the check verb, folded into status.compliance",
    "scripts/test_check.py": "its tests, now test_status.py",
    "skills/adjudant/reference/check.md": "its runbook, now reference/status.md",
    "scripts/sitrep.py": "the sitrep verb, folded into status.orientation",
    "scripts/test_sitrep.py": "its tests, now test_status.py",
    "skills/adjudant/reference/sitrep.md": "its runbook, now reference/status.md",
    "scripts/sync.py": "the sync verb, now status's make-current phase",
    "scripts/test_sync.py": "its tests, now test_status.py",
    "skills/adjudant/reference/sync.md": "its runbook, now reference/status.md",
    "scripts/tidy.py": "the tidy verb, folded into clean with ramasse",
    "scripts/test_tidy.py": "its tests, now test_clean.py",
    "skills/adjudant/reference/tidy.md": "its runbook, now reference/clean.md",
    "skills/adjudant/templates/_index-collection.md":
        "folder indexes are gone; _index_gen owns Home.md and {slug}/_index.md",
    "skills/adjudant/templates/_index-projects.md":
        "the projects index is gone; Home.md groups by lifecycle folder",
    "skills/adjudant/templates/dream-report.md": "kind renamed; now dream.md",
    "skills/adjudant/templates/iteration.md": "the iteration kind is not in the fifteen",
    "skills/adjudant/templates/memory.md": "the memory kind is not in the fifteen",
    "skills/adjudant/templates/project-brief-coding.md":
        "the four project-brief shapes are one template now: brief.md",
    "skills/adjudant/templates/project-brief-knowledge.md":
        "the four project-brief shapes are one template now: brief.md",
    "skills/adjudant/templates/project-brief-plugin.md":
        "the four project-brief shapes are one template now: brief.md",
    "skills/adjudant/templates/project-brief-tinkerage.md":
        "the four project-brief shapes are one template now: brief.md",
}

# Hand-written per audience. Named here so they are a decision, not an accident.
AUDIENCE_AUTHORED = frozenset({
    "GUIDE.md",
    "skills/adjudant/reference/internals.md",
})

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}


class GenerateError(RuntimeError):
    """The files copied, and then the twin could not be rendered.

    Worth its own type because of what it leaves behind. The copies and
    deletions have already landed when rendering runs, so a raw traceback here
    hands back a tree that is neither the old twin nor the new one, with no
    instruction on how to get out. `main` turns this into exit 2 and says so.
    """


class Plan(NamedTuple):
    create: list[str]
    update: list[str]
    delete: list[str]
    unexplained: list[str]


def _plugin_files(plugin_root: Path) -> set[str]:
    """Plugin-relative paths of every real file. Symlinks are skipped: the
    harness dirs (source/, .claude/, .gemini/) are symlinks to skills/adjudant
    and copying through them would duplicate the tree four times."""
    out: set[str] = set()
    for path in plugin_root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(plugin_root)
        if SKIP_DIRS & set(rel.parts):
            continue
        out.add(rel.as_posix())
    return out


def missing_backport(plugin_root: Path) -> list[str]:
    """Delegates to the guard so there is one definition of 'the back-port is
    whole'. Imported by path because adjudant/scripts is not a package."""
    sys.path.insert(0, str(plugin_root / "scripts"))
    try:
        import test_backport_guard
        return test_backport_guard.missing_markers(plugin_root)
    finally:
        sys.path.pop(0)


def leaking_identifiers(plugin_root: Path) -> list[str]:
    """Personal identifiers in the tree about to be published.

    Task 4 made the shared fixtures neutral so both builds could ship the same
    files. This charges that check before anything is copied rather than after,
    because the twin is a public repository and a published name stays
    published. PLUGIN_ROOT is repointed for the call: the gate reads it as a
    module global, and this process asks about a tree that is not its own.
    """
    sys.path.insert(0, str(plugin_root / "scripts"))
    try:
        import test_no_personal_identifiers as gate
        was = gate.PLUGIN_ROOT
        gate.PLUGIN_ROOT = plugin_root
        try:
            return gate.leaks()
        finally:
            gate.PLUGIN_ROOT = was
    finally:
        sys.path.pop(0)


def _deletable(plugin_root: Path) -> set[str]:
    """Paths a public build must not carry, derived from the metadata and the
    capability registry. This set is the ONLY licence to delete.

    `full_only_paths` reads the capability registry through `_profile`'s module
    global, and one process here reads two profiles from that one module, so
    the global is repointed at the tree being asked about. Without it the
    allowlist is whichever profile this process imported first, which is a set
    of files the generator would then delete.
    """
    sys.path.insert(0, str(plugin_root / "scripts"))
    try:
        import _profile
        import render_verb_surfaces
        was = _profile.PROFILE_PATH
        _profile.PROFILE_PATH = plugin_root / PROFILE_FILE
        _profile.load.cache_clear()
        try:
            meta = render_verb_surfaces.load_metadata(plugin_root)
            return set(render_verb_surfaces.full_only_paths(meta))
        finally:
            _profile.PROFILE_PATH = was
            _profile.load.cache_clear()
    finally:
        sys.path.pop(0)


def _retired(main_plugin: Path) -> set[str]:
    """RETIRED, minus anything this tree still ships.

    A tombstone naming a live file is not a retirement, and honouring one would
    delete the twin's copy of code main still has — the exact failure the
    unexplained gate exists to prevent, arriving through the gate's own
    allowlist. The subtraction makes it impossible rather than merely tested;
    test_generate_twin still fails loudly so the stale line gets removed
    instead of silently ignored.
    """
    return {rel for rel in RETIRED if not (main_plugin / rel).exists()}


def plan(main_root: Path, twin_root: Path) -> Plan:
    main_plugin = main_root / "adjudant"
    twin_plugin = twin_root / "adjudant"
    ours = _plugin_files(main_plugin)
    theirs = _plugin_files(twin_plugin)
    deletable = _deletable(main_plugin) | _retired(main_plugin)
    fixed = {PROFILE_FILE} | GENERATED | AUDIENCE_AUTHORED

    create, update = [], []
    for rel in sorted(ours - deletable):
        if rel in fixed:
            continue
        target = twin_plugin / rel
        if not target.exists():
            create.append(rel)
        elif not filecmp.cmp(main_plugin / rel, target, shallow=False):
            update.append(rel)

    delete, unexplained = [], []
    for rel in sorted(theirs - ours):
        (delete if rel in deletable else unexplained).append(rel)
    for rel in sorted(theirs & deletable):
        delete.append(rel)

    return Plan(create=create, update=update, delete=sorted(set(delete)),
                unexplained=unexplained)


def _sync_plugin_json(main_plugin: Path, twin_plugin: Path) -> None:
    """Give the twin main's plugin.json, then put the twin's identity back.

    Description is rewritten by the renderer afterwards; everything in
    IDENTITY_KEYS is the repo's, not the build's, and must survive.
    """
    src = main_plugin / ".claude-plugin" / "plugin.json"
    dst = twin_plugin / ".claude-plugin" / "plugin.json"
    if not dst.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    theirs = json.loads(dst.read_text())
    merged = json.loads(src.read_text())
    for key in IDENTITY_KEYS:
        if key in theirs:
            merged[key] = theirs[key]
    dst.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")


def _sync_metadata(main_plugin: Path, twin_plugin: Path) -> None:
    """The twin's command-metadata is main's, filtered to its audience, with the
    twin's own version kept so the version-consistency validator stays green.

    The audience is read straight out of the twin's profile file rather than
    through _profile, because _profile caches per path and this process has
    already loaded main's.
    """
    audience = json.loads(
        (twin_plugin / PROFILE_FILE).read_text())["audience"]
    src = json.loads((main_plugin / "scripts" / "command-metadata.json").read_text())
    dst_path = twin_plugin / "scripts" / "command-metadata.json"
    version = src["version"]
    if dst_path.is_file():
        version = json.loads(dst_path.read_text()).get("version", version)
    out = dict(src)
    out["version"] = version
    out["verbs"] = [v for v in src["verbs"]
                    if v["audience"] == "all" or audience == "full"]
    out["content_references"] = [c for c in src["content_references"]
                                 if c["audience"] == "all" or audience == "full"]
    dst_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")


def _render_in_twin(twin_plugin: Path) -> list[str]:
    """Render the twin's surfaces with the twin's own profile.

    `_profile.load` is memoised, and this process has already read main's
    profile through the same module, so the cache is cleared and PROFILE_PATH
    is repointed for the duration.
    """
    sys.path.insert(0, str(twin_plugin / "scripts"))
    try:
        import _profile
        import render_verb_surfaces
        was = _profile.PROFILE_PATH
        _profile.PROFILE_PATH = twin_plugin / PROFILE_FILE
        _profile.load.cache_clear()
        try:
            return render_verb_surfaces.apply(twin_plugin)
        finally:
            _profile.PROFILE_PATH = was
            _profile.load.cache_clear()
    finally:
        sys.path.pop(0)


def apply_plan(main_root: Path, twin_root: Path, p: Plan) -> list[str]:
    main_plugin = main_root / "adjudant"
    twin_plugin = twin_root / "adjudant"
    done: list[str] = []
    for rel in p.create + p.update:
        src, dst = main_plugin / rel, twin_plugin / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        done.append(f"copied {rel}")
    for rel in p.delete:
        target = twin_plugin / rel
        if target.is_file():
            target.unlink()
            done.append(f"deleted {rel}")
    for rel in SEEDED:
        src, dst = main_plugin / rel, twin_plugin / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        done.append(f"seeded {rel}")
    # Broad on purpose, and narrow in scope: three known calls, and the reason
    # to catch is not the error but the state it leaves behind.
    try:
        _sync_plugin_json(main_plugin, twin_plugin)
        _sync_metadata(main_plugin, twin_plugin)
        for path in _render_in_twin(twin_plugin):
            done.append(f"rendered {path}")
    except Exception as exc:
        raise GenerateError(
            f"the copy landed but the twin could not be rendered: {exc}") from exc
    return done


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="generate_twin.py",
        description="Generate the public twin's adjudant from this one.")
    ap.add_argument("--twin", required=True, help="the twin repository root")
    ap.add_argument("--main-root", default=str(MAIN_ROOT),
                    help="this repository root (default: the script's own)")
    ap.add_argument("--apply", action="store_true",
                    help="write the plan; without it nothing is touched")
    args = ap.parse_args(argv)

    main_root = Path(args.main_root).expanduser().resolve()
    twin_root = Path(args.twin).expanduser().resolve()
    if not (twin_root / "adjudant").is_dir():
        print(f"error: no adjudant/ under {twin_root}", file=sys.stderr)
        return 2

    gone = missing_backport(main_root / "adjudant")
    if gone:
        print("error: the twin's back-ported code is missing from this tree:",
              file=sys.stderr)
        for line in gone:
            print(f"  {line}", file=sys.stderr)
        print("regenerating now would delete it. See plan 5, task 1.", file=sys.stderr)
        return 2

    leaked = leaking_identifiers(main_root / "adjudant")
    if leaked:
        print("error: shared files name a person, a client, or the marketplace:",
              file=sys.stderr)
        for line in leaked[:20]:
            print(f"  {line}", file=sys.stderr)
        if len(leaked) > 20:
            print(f"  and {len(leaked) - 20} more", file=sys.stderr)
        print("the twin is public. See plan 5, task 4.", file=sys.stderr)
        return 2

    p = plan(main_root, twin_root)
    for label, items in (("create", p.create), ("update", p.update),
                         ("delete", p.delete)):
        for rel in items:
            print(f"  {label} {rel}")
    if p.unexplained:
        print("\nerror: files exist in the twin that this build cannot explain.",
              file=sys.stderr)
        print("Nothing was deleted. Either back-port them, add them to a verb's "
              "`files` list in command-metadata.json, or — if no build ships "
              "them any more — name each one in generate_twin.RETIRED.",
              file=sys.stderr)
        for rel in p.unexplained:
            print(f"  unexplained {rel}", file=sys.stderr)
        return 3
    if not args.apply:
        pending = len(p.create) + len(p.update) + len(p.delete)
        print(f"\ndry run: {pending} change(s) pending; re-run with --apply")
        return 1 if pending else 0
    try:
        lines = apply_plan(main_root, twin_root, p)
    except GenerateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("the twin is half-generated: the copies landed and the surfaces "
              "did not. Restore it with `git -C <twin> checkout -- adjudant`, "
              "fix the cause, and run again.", file=sys.stderr)
        return 2
    for line in lines:
        print(f"  {line}")
    print("\ntwin regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
