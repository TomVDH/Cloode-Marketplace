# Adjudant v3, Plan 3: Six Verbs

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thirteen verbs become six, and the cleanup verbs stop adding more than they remove.

**Architecture:** Three moves. `port`, `shelf` and `kebab` are deleted outright. `sync`, `sitrep`, `check` and the advisor pulse collapse into one `status` verb that makes derived state current and then reports on it. `tidy` and `ramasse` merge into `clean`, whose contract is enforced in code: it may delete, merge and rewrite in place, and it may not create a vault file. `dream` keeps its name and is rebuilt for precision, because it is the second most-reached-for verb and it has never produced a true positive.

**Tech Stack:** Python 3.9+ stdlib only, `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-01-adjudant-v3-design.md` (phase 3, plus the "Dream, rebuilt to work" and "The verb surface" sections)

**Assumes:** Plans 1 and 2 have landed. Scratch lives outside the vault, the hooks no longer write unprompted, and `FIELD_SCHEMA` is parsed from the templates.

## Global Constraints

- **Stdlib only. Python 3.9 floor.**
- **The suite must be green after every task.** `python3 -m unittest discover -p 'test_*.py'` from `adjudant/scripts/`.
- **Validators green.** `python3 adjudant/scripts/validate.py`. Plan 2 left the count at 28; this plan removes more and the docstring total must match after every task.
- **The six verbs are fixed:** `connect status clean dream draw board`. Their names appear in five places that must agree, all checked by validator 15 (`verb-surface-parity`): `scripts/command-metadata.json`, `skills/adjudant/SKILL.md` frontmatter and router table, `.claude-plugin/plugin.json`, `README.md`, and the marketplace description in `../.claude-plugin/marketplace.json`.
- **`clean` may not create a vault file.** This is enforced in code, not by discipline, and Task 6 is the test that proves it.
- **The statusline reads dream's report and the verb-in-progress directories.** See `skills/adjudant/reference/state-contract.md` from plan 1. Do not change either shape without updating that document.
- **Commit style:** Conventional Commits, scope `adjudant`, ending with:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`

## File Structure

| File | Responsibility |
|---|---|
| `adjudant/scripts/clean.py` | **New.** `tidy.py` and `ramasse_scan.py` merged, with the net-subtractive contract enforced. |
| `adjudant/scripts/_vault_write.py` | **New.** The single guard that makes creating a vault file impossible from `clean`. |
| `adjudant/scripts/status.py` | **New.** Absorbs `sync.py`, `sitrep.py`, `check.py`, `kebab.py --scan`, `advisor.py pulse`. |
| `adjudant/scripts/dream.py` | Rebuilt: confidence scores, a cap, two bugs fixed, one detector deleted. |
| Deleted | `port.py`, `shelf.py`, `kebab.py`, `tidy.py`, `ramasse_scan.py`, `sync.py`, `sitrep.py`, `check.py`, `advisor.py` and their tests. |

---

## Task 1: Sunset `port`

Its migration is done. It is 965 lines, 63 tests and four validators for a one-shot job.

**Files:**
- Delete: `adjudant/scripts/port.py`, `adjudant/scripts/test_port.py`, `adjudant/skills/adjudant/reference/port.md`
- Modify: `adjudant/scripts/command-metadata.json`, `adjudant/skills/adjudant/SKILL.md`, `adjudant/scripts/validate.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `command-metadata.json` has twelve verbs after this task. The six-verb end state arrives at Task 5.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_validate.py`:

```python
class TestPortIsSunset(unittest.TestCase):

    def test_no_port_source_survives(self):
        scripts = Path(validate.__file__).parent
        for name in ("port.py", "test_port.py"):
            self.assertFalse((scripts / name).exists(), f"{name} survived")

    def test_no_port_verb_registered(self):
        meta = json.loads((Path(validate.__file__).parent / "command-metadata.json").read_text())
        self.assertNotIn("port", [v["name"] for v in meta["verbs"]])

    def test_port_validators_are_gone(self):
        src = Path(validate.__file__).read_text()
        for name in ("port-preview-coherence", "port-backup-integrity",
                     "gitignore-includes-port-dirs"):
            self.assertNotIn(name, src, f"{name} validates a deleted verb")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_validate.TestPortIsSunset -v`
Expected: FAIL — `port.py` exists.

- [ ] **Step 3: Delete it**

```bash
git rm adjudant/scripts/port.py adjudant/scripts/test_port.py \
       adjudant/skills/adjudant/reference/port.md
```

Remove the `port` object from `scripts/command-metadata.json`. Remove its router row and its name from the pipe-lists in `SKILL.md`'s `description` and `argument-hint`. Remove validators 7, 8 and 9 (`port-preview-coherence`, `port-backup-integrity`, `gitignore-includes-port-dirs`) from `validate.py` and renumber the docstring registry.

Remove `.adjudant-port-preview` and `.adjudant-port-backup` from `_vault_walk.py`'s skip-dir tuple (around line 331) and from the repo `.gitignore`.

- [ ] **Step 4: Run the suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add -A adjudant/ .gitignore
git commit -m "feat(adjudant)!: sunset port

965 lines, 63 tests and three validators for a one-shot migration off
obsidian-bridge that completed. One recorded user invocation.

BREAKING CHANGE: /adjudant port is removed. A future legacy vault is migrated
by hand.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Sunset `shelf`, and with it the vault-wide link rewrite

`shelf` moved a project between zones and rewrote every wikilink pointing into it. Plan 4's zone-less link form makes the rewrite unnecessary, and `connect` and `status` do the asking.

**Files:**
- Delete: `adjudant/scripts/shelf.py`, `adjudant/scripts/test_shelf.py`, `adjudant/skills/adjudant/reference/shelf.md`
- Modify: `command-metadata.json`, `SKILL.md`, `_vault_walk.py` skip-dirs

**Interfaces:**
- Consumes: nothing.
- Produces: the lifecycle move has no verb. Plan 4 adds the prompt to `connect` and the 30-day nudge to `status`.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_validate.py`:

```python
class TestShelfIsSunset(unittest.TestCase):

    def test_no_shelf_source_survives(self):
        scripts = Path(validate.__file__).parent
        for name in ("shelf.py", "test_shelf.py"):
            self.assertFalse((scripts / name).exists(), f"{name} survived")

    def test_no_vault_wide_link_rewrite_remains(self):
        # 380 lines whose only job was repairing the decision to put the
        # lifecycle folder in every link. Plan 4 takes it out of the links.
        scripts = Path(validate.__file__).parent
        for py in scripts.glob("*.py"):
            if py.name.startswith("test_"):
                continue
            self.assertNotIn("rewrite_wikilink_prefix", py.read_text(),
                             f"{py.name} still rewrites links vault-wide")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_validate.TestShelfIsSunset -v`
Expected: FAIL — `shelf.py` exists.

- [ ] **Step 3: Delete it**

```bash
git rm adjudant/scripts/shelf.py adjudant/scripts/test_shelf.py \
       adjudant/skills/adjudant/reference/shelf.md
```

Remove the `shelf` entry from `command-metadata.json` and `SKILL.md`. Remove `.adjudant-shelf-preview` and `.adjudant-shelf-backup` from the skip-dir tuple in `_vault_walk.py`.

Any caller importing from `shelf` (grep for `from shelf import` and `import shelf`) loses that import. `check.py` and `sitrep.py` may reference zone helpers that lived there; those move to `_vault_walk.py` unchanged rather than being deleted, since plan 4 needs them for the four-folder move.

- [ ] **Step 4: Run the suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add -A adjudant/
git commit -m "feat(adjudant)!: sunset shelf

One recorded invocation in a year, because nothing ever asked. The lifecycle
move becomes a question connect asks on first link and status offers after 30
days of silence.

Its 380-line vault-wide wikilink rewrite goes too: it existed only to repair
the decision to put the lifecycle folder in every link, which plan 4 reverses.

BREAKING CHANGE: /adjudant shelf is removed.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Merge `tidy` and `ramasse` into `clean`, with the contract in code

**Files:**
- Create: `adjudant/scripts/_vault_write.py`, `adjudant/scripts/test__vault_write.py`
- Create: `adjudant/scripts/clean.py` (from `tidy.py` plus `ramasse_scan.py`'s detectors)
- Delete: `adjudant/scripts/{tidy,ramasse_scan}.py` and their tests, `reference/{tidy,ramasse}.md`
- Create: `adjudant/skills/adjudant/reference/clean.md`

**Interfaces:**
- Consumes: `scratch_dir`, `prune_backups` from `_scratch` (plan 1 Task 2).
- Produces:
  - `_vault_write.VaultWriteGuard` — a context manager. Inside it, `guard.rewrite(path, text)` and `guard.remove(path)` are allowed; `guard.create(path, text)` raises `VaultCreateRefused`. Every `clean` write goes through it.
  - `clean.build_preview(project_dir, deep: bool = False) -> dict` — `deep=True` adds the structural detectors that were `ramasse`'s.
  - `clean.apply_preview(project_dir) -> Path` — returns the backup directory.

- [ ] **Step 1: Write the failing test for the guard**

Create `adjudant/scripts/test__vault_write.py`:

```python
"""Tests for _vault_write.py — the guard that makes clean net-subtractive.

The design defect this closes: every cleanup run wrote more into the vault
than it removed, and nothing in the code could tell the difference between
removing a tag and creating a report note. Now it can.
"""

import tempfile
import unittest
from pathlib import Path

from _vault_write import VaultCreateRefused, VaultWriteGuard


class TestGuard(unittest.TestCase):

    def test_rewrite_of_an_existing_file_is_allowed(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "a.md"
            p.write_text("old")
            with VaultWriteGuard(Path(t)) as g:
                g.rewrite(p, "new")
            self.assertEqual(p.read_text(), "new")

    def test_remove_is_allowed(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "a.md"
            p.write_text("x")
            with VaultWriteGuard(Path(t)) as g:
                g.remove(p)
            self.assertFalse(p.exists())

    def test_creating_a_new_vault_file_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            with VaultWriteGuard(Path(t)) as g:
                with self.assertRaises(VaultCreateRefused):
                    g.rewrite(Path(t) / "new.md", "content")

    def test_rewrite_outside_the_root_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            outside = Path(t).parent / "escape.md"
            with VaultWriteGuard(Path(t)) as g:
                with self.assertRaises(VaultCreateRefused):
                    g.rewrite(outside, "x")

    def test_the_guard_counts_what_it_did(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t) / "a.md", Path(t) / "b.md"
            a.write_text("x")
            b.write_text("y")
            with VaultWriteGuard(Path(t)) as g:
                g.rewrite(a, "z")
                g.remove(b)
            self.assertEqual(g.rewritten, 1)
            self.assertEqual(g.removed, 1)
            self.assertEqual(g.created, 0)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_write -v`
Expected: FAIL with `ModuleNotFoundError: No module named '_vault_write'`

- [ ] **Step 3: Write the guard**

Create `adjudant/scripts/_vault_write.py`:

```python
#!/usr/bin/env python3
"""The net-subtractive contract, enforced.

`clean` may delete, merge and rewrite in place. It may not create a vault
file. That was previously a promise in a reference doc — `reference/tidy.md`
line 120 read "No new file creation beyond _index.md regenerations" — and it
was false: the preview and backup trees alone wrote roughly 25 files per run
into the vault they were cleaning.

A promise in prose cannot be tested. This can.
"""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Optional


class VaultCreateRefused(RuntimeError):
    """A caller tried to create a vault file inside a net-subtractive pass."""


class VaultWriteGuard:
    """Context manager permitting only in-place rewrites and removals.

    Every write `clean` makes goes through `rewrite` or `remove`. A path that
    does not already exist, or that resolves outside `root`, is refused rather
    than created — so "clean must not add files" is a property of the code
    rather than a rule someone has to remember.
    """

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.rewritten = 0
        self.removed = 0
        self.created = 0          # stays 0; a non-zero value is a bug

    def __enter__(self) -> "VaultWriteGuard":
        return self

    def __exit__(self, exc_type: Optional[type], exc: Optional[BaseException],
                 tb: Optional[TracebackType]) -> None:
        return None

    def _contained(self, path: Path) -> Path:
        resolved = path.resolve()
        if self.root not in resolved.parents and resolved != self.root:
            raise VaultCreateRefused(f"{path} is outside {self.root}")
        return resolved

    def rewrite(self, path: Path, text: str) -> None:
        """Replace the content of a file that already exists."""
        target = self._contained(path)
        if not target.is_file():
            raise VaultCreateRefused(
                f"clean may not create {path}: it rewrites and removes only")
        target.write_text(text)
        self.rewritten += 1

    def remove(self, path: Path) -> None:
        """Delete a file that already exists. Absent is not an error."""
        target = self._contained(path)
        if not target.exists():
            return
        target.unlink()
        self.removed += 1
```

- [ ] **Step 4: Run the guard tests**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_write -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Create `clean.py`**

```bash
git mv adjudant/scripts/tidy.py adjudant/scripts/clean.py
git mv adjudant/scripts/test_tidy.py adjudant/scripts/test_clean.py
```

In `clean.py`:

- Rename `PREVIEW_KIND` / `BACKUP_KIND` values to `"clean-preview"` and `"clean-backup"`, and the helper functions to `preview_dir` and `backup_root` (plan 1 already introduced both).
- Import `VaultWriteGuard` and route every live write in `apply_preview` through it. The index-creation feature (`tidy.py:598-647` before the rename) must now go through `guard.rewrite`, which refuses to create a new `_index.md`. That is correct: plan 4 generates the two surviving index surfaces, and `clean` stops generating any.
- Fold in `ramasse_scan.py`'s structural detectors behind a `deep: bool = False` parameter on `build_preview`. They are read-only detectors and need no guard.
- Delete the tag feature if plan 2 Task 9 has not already removed it.

```bash
git rm adjudant/scripts/ramasse_scan.py adjudant/scripts/test_ramasse_scan.py
```

- [ ] **Step 6: Write the reference doc**

Create `adjudant/skills/adjudant/reference/clean.md`, and delete `reference/tidy.md` and `reference/ramasse.md`. The new doc states the contract in its first paragraph and, critically, contains no instruction to write an iteration folder, a workspace directory or a backup tree into the vault. The old `ramasse.md` lines 71 and 85 and `dream.md` lines 98 and 106 each mandated exactly that.

```bash
git rm adjudant/skills/adjudant/reference/tidy.md adjudant/skills/adjudant/reference/ramasse.md
```

- [ ] **Step 7: Run the suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`. Tests naming `tidy` need their imports updated; tests asserting `_index.md` creation are now asserting the defect and should be deleted with a note in the commit.

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`. Validators 11, 12 and 13 name tidy directories; rename or delete them.

- [ ] **Step 8: Commit**

```bash
git add -A adjudant/
git commit -m "feat(adjudant)!: tidy and ramasse become clean, net-subtractive in code

reference/tidy.md line 120 claimed 'no new file creation' while the preview
and backup trees wrote ~25 files per run into the vault. A promise in prose
cannot be tested; VaultWriteGuard can. clean may rewrite and remove. It cannot
create.

Index generation moves to plan 4, which generates two surfaces instead of 141.

BREAKING CHANGE: /adjudant tidy and /adjudant ramasse become /adjudant clean
and /adjudant clean --deep.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Rebuild `dream` for precision

The 13 August run turned 602 files into 602 candidates, of which 463 were contradictions and none were real, at 918,000 read tokens.

**Files:**
- Modify: `adjudant/scripts/dream.py` — delete `detect_contradiction_candidates` (line 367), fix `detect_supersession_signals` (line 340), fix `detect_unacted_decisions` (line 593), add scoring and a cap
- Modify: `adjudant/skills/adjudant/reference/dream.md`
- Test: `adjudant/scripts/test_dream.py`

**Interfaces:**
- Consumes: `STATUS_VALUES_FOR_TYPE` from plan 2's derived schema.
- Produces: the report JSON gains `confidence` (a float, 0 to 1) on every candidate and is capped at twenty entries, ordered by confidence descending. `meta.summary` keeps its per-category counts so nothing downstream breaks.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_dream.py`:

The class reads `dream.__file__`, so `from pathlib import Path` and `import dream`
must be present at the top of `test_dream.py`; add them if absent.

```python
class TestPrecisionRebuild(unittest.TestCase):

    def test_the_contradiction_detector_is_gone(self):
        # 463 candidates, 23 sampled, zero real. It fired on any two files
        # sharing vocabulary where one contained a negation cue, which in a
        # vault of decisions that say "we switched from X to Y" is every pair.
        import dream
        self.assertFalse(hasattr(dream, "detect_contradiction_candidates"))
        self.assertNotIn("contradiction", dream.__doc__ or "")

    def test_supersession_reads_the_real_field_name(self):
        # dream.py:340 tested for a key named `superseded`. The schema field
        # is `superseded_by`, so the frontmatter half of that test could never
        # pass and only the prose regex ever fired.
        src = Path(dream.__file__).read_text()
        self.assertNotIn('"superseded" in older.frontmatter.fields', src)
        self.assertIn('"superseded_by" in older.frontmatter.fields', src)

    def test_a_session_link_no_longer_proves_closure(self):
        # dream.py:593 skipped any decision a session linked to. Adjudant tells
        # you to link decisions from sessions, so this excluded 47 of 55 active
        # decisions — the only verb auditing them, defeated by its own
        # convention.
        src = Path(dream.__file__).read_text()
        self.assertNotIn("a session points at it", src)

    def test_every_candidate_carries_a_confidence(self):
        with tempfile.TemporaryDirectory() as t:
            project = self._project(Path(t))          # existing helper
            report = dream.build_report(project)
            for key, entries in report.items():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    self.assertIn("confidence", entry, f"{key} entry has no score")
                    self.assertGreaterEqual(entry["confidence"], 0.0)
                    self.assertLessEqual(entry["confidence"], 1.0)

    def test_the_catalog_is_capped(self):
        with tempfile.TemporaryDirectory() as t:
            project = self._noisy_project(Path(t), notes=200)
            report = dream.build_report(project)
            total = sum(len(v) for v in report.values() if isinstance(v, list))
            self.assertLessEqual(total, 20,
                                 "the catalog is a shortlist, not a census")

    def test_dismissals_suppress_a_repeat(self):
        # Two consecutive real reports dismissed the _archive/ naming finding
        # in identical words.
        with tempfile.TemporaryDirectory() as t:
            project = self._project(Path(t))
            dreams = project / "dreams"
            dreams.mkdir(parents=True, exist_ok=True)
            (dreams / "2026-08-01.md").write_text(
                "---\ntype: dream\ncreated: 2026-08-01\nupdated: 2026-08-01\n---\n\n"
                "# Dream 2026-08-01\n\n1 findings, 0 acted on, 1 dismissed.\n\n"
                "## Dismissed\n\n| Finding | Why | Suppress until |\n|---|---|---|\n"
                "| notes/a.md orphaned | intentional | the file changes |\n")
            report = dream.build_report(project)
            flagged = [e["file"] for v in report.values() if isinstance(v, list)
                       for e in v if "file" in e]
            self.assertNotIn("notes/a.md", flagged)
```

Read `test_dream.py`'s existing fixture helpers before writing this and substitute the real names for `self._project` and `self._noisy_project`; add `_noisy_project` if the file has no equivalent.

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_dream.TestPrecisionRebuild -v`
Expected: FAIL — the contradiction detector still exists.

- [ ] **Step 3: Delete the zero-precision detector**

Remove `detect_contradiction_candidates` (line 367) entirely, its call in the report builder, its `contradiction_pairs` key and its `summary.contradiction` count. Update the module docstring's catalog list.

- [ ] **Step 4: Fix the two bugs**

At line 340, change:

```python
                "superseded" in older.frontmatter.fields
```

to:

```python
                "superseded_by" in older.frontmatter.fields
```

At lines 591-593 in `detect_unacted_decisions`, delete the session-link skip:

```python
        stem = f.rel_path.name[:-3] if f.rel_path.name.endswith(".md") else f.rel_path.name
        rel_no_ext = str(f.rel_path)[:-3] if str(f.rel_path).endswith(".md") else str(f.rel_path)
        if stem in session_targets or rel_no_ext in session_targets or str(f.rel_path) in session_targets:
            continue  # a session points at it → likely acted on
```

Replace it with the count as evidence rather than as an exclusion, so a heavily-referenced decision scores lower instead of vanishing:

```python
        # A session link is weak evidence of action, not proof: adjudant tells
        # you to link decisions from sessions, so this test excluded 47 of 55
        # active decisions in the real vault — the only audit of them, defeated
        # by adjudant's own convention. It now lowers the score instead.
        stem = f.rel_path.stem
        rel_no_ext = str(f.rel_path)[:-3] if str(f.rel_path).endswith(".md") else str(f.rel_path)
        refs = sum(1 for key in (stem, rel_no_ext, str(f.rel_path))
                   if key in session_targets)
```

and pass `refs` into the entry as `inbound_session_refs`, which the existing entry already has a slot for.

- [ ] **Step 5: Add scoring and the cap**

Add to `dream.py`:

```python
# A candidate's score is the detector's own confidence, damped by evidence
# that the thing was already handled. The catalog is a shortlist a human
# reads, not a census: the 2026-08-13 run produced 602 candidates and a
# sampled review found zero real, which is what "deliberately generous"
# bought. Twenty is a number someone will actually read.
CATALOG_CAP = 20

# Per-detector base confidence, from the one review with measured outcomes.
_BASE_CONFIDENCE = {
    "supersession_signals": 0.8,   # a real, checkable relationship
    "stale_refs": 0.7,             # resolves but points at an archive
    "orphan_questions": 0.6,       # an open marker with a date
    "unacted_decisions": 0.5,      # judgement, but a real question
    "staleness_candidates": 0.4,   # old is not the same as wrong
    "redundancy_clusters": 0.3,    # a documentation convention reads as this
    "orphan_threads": 0.3,
    "documentation_gaps": 0.3,
    "dangling_scopes": 0.3,
}


def _score(category: str, entry: dict) -> float:
    base = _BASE_CONFIDENCE.get(category, 0.3)
    if entry.get("inbound_session_refs"):
        base -= 0.15 * min(entry["inbound_session_refs"], 2)
    if entry.get("older_has_superseded_marker"):
        base -= 0.5          # already marked: this is the convention working
    return max(0.0, min(1.0, round(base, 2)))


def _cap(report: dict, cap: int = CATALOG_CAP) -> dict:
    """Keep the highest-scoring `cap` candidates across every category."""
    scored = [(cat, e) for cat, entries in report.items()
              if isinstance(entries, list) for e in entries]
    scored.sort(key=lambda pair: pair[1].get("confidence", 0.0), reverse=True)
    keep = scored[:cap]
    out = {cat: [] for cat, _ in scored}
    for cat, entry in keep:
        out[cat].append(entry)
    return out
```

Apply `_score` to every entry as it is built, then `_cap` before the report is returned.

- [ ] **Step 6: Add dismissal suppression**

```python
_DISMISS_ROW_RE = re.compile(r"^\|\s*(?P<finding>[^|]+?)\s*\|[^|]*\|[^|]*\|\s*$")


def read_dismissals(project_dir: Path) -> set[str]:
    """Findings a previous dream report dismissed, keyed by the file they name.

    Two consecutive reports in the real vault dismissed the same `_archive/`
    naming finding in identical words. A dismissal that does not persist is an
    invitation to waste the same hour again.
    """
    out: set[str] = set()
    dreams = project_dir / "dreams"
    if not dreams.is_dir():
        return out
    for report in sorted(dreams.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")):
        try:
            text = report.read_text(errors="replace")
        except OSError:
            continue
        if "## Dismissed" not in text:
            continue
        section = text.split("## Dismissed", 1)[1].split("\n## ", 1)[0]
        for line in section.splitlines():
            m = _DISMISS_ROW_RE.match(line.strip())
            if m and not m.group("finding").startswith(("Finding", "---")):
                out.add(m.group("finding").split()[0])
    return out
```

Filter every candidate whose `file` appears in `read_dismissals(project_dir)`, unless the file's mtime is newer than the report that dismissed it.

- [ ] **Step 7: Rewrite the reference doc**

In `adjudant/skills/adjudant/reference/dream.md`, delete line 98 (the iteration-folder mandate) and line 106 (the workspace and backup-tree mandate). Replace phase 5 with: apply through `clean`'s primitives, back up to the scratch path, and write exactly one report.

Delete the sentence "The catalog is deliberately generous" at line 86. That doctrine is the defect.

- [ ] **Step 8: Run the tests and validators**

Run: `cd adjudant/scripts && python3 -m unittest test_dream -v 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 9: Commit**

```bash
git add adjudant/scripts/dream.py adjudant/scripts/test_dream.py adjudant/skills/adjudant/reference/dream.md
git commit -m "fix(adjudant): rebuild dream for precision

602 files became 602 candidates; 463 were contradictions and a sampled review
found zero real, at 918k read tokens. Three causes, all fixed:

- the contradiction detector fired on any two files sharing vocabulary where
  one contained a negation cue. Deleted.
- supersession tested for a key named 'superseded'; the field is
  'superseded_by', so that half never passed.
- unacted-decisions skipped any decision a session linked to, excluding 47 of
  55 active decisions. A link now lowers the score instead of excluding.

Candidates carry a confidence and the catalog caps at 20. Dismissals persist,
because two reports dismissed the same finding in identical words.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Fold five verbs into `status`

**Files:**
- Create: `adjudant/scripts/status.py`, `adjudant/skills/adjudant/reference/status.md`
- Delete: `adjudant/scripts/{sync,sitrep,check,kebab,advisor}.py` and their tests, and their reference docs
- Modify: `command-metadata.json`, `SKILL.md`, `plugin.json`, `README.md`, `../.claude-plugin/marketplace.json`

**Interfaces:**
- Consumes: `remember_status` from `_handoff_freshness` (plan 1 Task 9).
- Produces: `status.run(project_dir, vault_dir) -> dict` with keys `synced` (what it made current), `wrong_now`, `going_stale`, `worth_a_look`. Plan 4 fills the three report bands with the truth checks; this task establishes the verb and moves the existing signals into it.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_status.py`:

```python
"""Tests for status.py — sync, sitrep, check, kebab --scan and advisor pulse,
merged into one verb that makes derived state current and then reports."""

import tempfile
import unittest
from pathlib import Path

import status


class TestStatusAbsorbs(unittest.TestCase):

    def test_the_absorbed_modules_are_gone(self):
        scripts = Path(status.__file__).parent
        for name in ("sync.py", "sitrep.py", "check.py", "kebab.py", "advisor.py"):
            self.assertFalse((scripts / name).exists(), f"{name} survived")

    def test_report_has_three_bands(self):
        with tempfile.TemporaryDirectory() as t:
            project = Path(t) / "vault" / "projects" / "demo"
            project.mkdir(parents=True)
            (project / "brief.md").write_text(
                "---\ntype: project\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
                "verified: 2026-09-01\nverified_by: read\n---\n\n# Demo\n\nA project.\n")
            report = status.run(project, project.parent.parent)
            for band in ("wrong_now", "going_stale", "worth_a_look"):
                self.assertIn(band, report)
                self.assertIsInstance(report[band], list)

    def test_it_reports_what_it_made_current(self):
        with tempfile.TemporaryDirectory() as t:
            project = Path(t) / "vault" / "projects" / "demo"
            project.mkdir(parents=True)
            (project / "brief.md").write_text(
                "---\ntype: project\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
                "verified: 2026-09-01\nverified_by: read\n---\n\n# Demo\n\nA project.\n")
            report = status.run(project, project.parent.parent)
            self.assertIn("synced", report)

    def test_naming_scan_is_absorbed(self):
        # kebab --scan was a whole verb for a string check. It is a signal.
        with tempfile.TemporaryDirectory() as t:
            project = Path(t) / "vault" / "projects" / "demo"
            (project / "notes").mkdir(parents=True)
            (project / "notes" / "Not Kebab Case.md").write_text(
                "---\ntype: note\ncreated: 2026-09-01\nupdated: 2026-09-01\n---\n\n# X\n")
            report = status.run(project, project.parent.parent)
            findings = " ".join(str(x) for band in ("wrong_now", "going_stale",
                                                    "worth_a_look")
                                for x in report[band])
            self.assertIn("Not Kebab Case", findings)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_status -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'status'`

- [ ] **Step 3: Build `status.py`**

Create it by moving, not rewriting:

- `sync.py`'s brief-date bump and index-row update become the `synced` phase. The handoff mirror is already gone (plan 1 Task 9 moved handoff authorship to session end).
- `check.py`'s report becomes the three bands.
- `sitrep.py`'s orientation prose becomes the report's header.
- `kebab.py`'s `--scan` becomes one signal. Keep its `kebab()` slugify function as a helper in `_vault_walk.py`, since `board` and plan 4's `place()` both need it.
- `advisor.py`'s `run_pulse` merges into the report; its `on`/`off` writes one breadcrumb line, which becomes a `connect` question in plan 4.

```bash
git rm adjudant/scripts/sync.py adjudant/scripts/test_sync.py \
       adjudant/scripts/sitrep.py adjudant/scripts/test_sitrep.py \
       adjudant/scripts/check.py adjudant/scripts/test_check.py \
       adjudant/scripts/kebab.py adjudant/scripts/test_kebab.py \
       adjudant/scripts/advisor.py adjudant/scripts/test_advisor.py \
       adjudant/skills/adjudant/reference/sync.md \
       adjudant/skills/adjudant/reference/sitrep.md \
       adjudant/skills/adjudant/reference/check.md \
       adjudant/skills/adjudant/reference/kebab.md \
       adjudant/skills/adjudant/reference/advisor.md
```

Preserve the tests worth keeping by moving their cases into `test_status.py`: every fail-closed test, every traversal and slug-guard test, and the zone-awareness tests. Those protect behaviour, not structure.

- [ ] **Step 4: Update the five verb surfaces**

Set the verb list to exactly `connect status clean dream draw board` in:

1. `adjudant/scripts/command-metadata.json`
2. `adjudant/skills/adjudant/SKILL.md` — frontmatter `description`, `argument-hint`, the "thirteen verbs" prose, and the router table
3. `adjudant/.claude-plugin/plugin.json` description
4. `adjudant/README.md`
5. `.claude-plugin/marketplace.json` description

Validator 15 (`verb-surface-parity`) checks all five agree and that spelled-out counts match, so "thirteen verbs" must become "six verbs" everywhere.

- [ ] **Step 5: Run the suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add -A adjudant/ .claude-plugin/marketplace.json
git commit -m "feat(adjudant)!: sync, sitrep, check, kebab and advisor become status

Five read-mostly verbs answering one question. sync alone bumped a date,
mirrored a handoff the hooks now write, and updated an index row plan 4
generates. kebab was a whole verb for a string transform, and its own
docstring conceded the joke was the name.

status makes derived state current, then reports in three bands ordered by
cost of being wrong.

BREAKING CHANGE: /adjudant sync, sitrep, check, kebab and advisor are removed.
Thirteen verbs become six.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: The net-subtractive acceptance test

**Files:**
- Create: `adjudant/scripts/test_net_subtractive.py`

**Interfaces:**
- Consumes: Tasks 3 and 4.
- Produces: the gate.

- [ ] **Step 1: Write the test**

Create `adjudant/scripts/test_net_subtractive.py`:

```python
"""Acceptance test for plan 3: clean removes more than it adds, always.

The complaint this plan answers, verbatim: the cleanup tier "fills SO much
more crud than it actually cleans". This test makes the opposite a property
of the code.
"""

import tempfile
import unittest
from pathlib import Path

import clean


class TestCleanIsNetSubtractive(unittest.TestCase):

    def _project(self, tmp: Path, notes: int = 12) -> Path:
        project = tmp / "vault" / "projects" / "demo"
        (project / "notes").mkdir(parents=True)
        for i in range(notes):
            (project / "notes" / f"n{i}.md").write_text(
                "---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
                "tags:\n  - note\n---\n\n# N\n\nbody\n")
        return project

    def _count(self, root: Path) -> tuple[int, int]:
        files = [p for p in root.rglob("*") if p.is_file()]
        return len(files), sum(p.stat().st_size for p in files)

    def test_file_count_and_bytes_do_not_grow(self):
        with tempfile.TemporaryDirectory() as t:
            project = self._project(Path(t))
            before_n, before_b = self._count(project)
            clean.write_preview_to_disk(project, clean.build_preview(project))
            clean.apply_preview(project)
            after_n, after_b = self._count(project)
            self.assertLessEqual(after_n, before_n,
                                 "clean added files to the vault")
            self.assertLessEqual(after_b, before_b,
                                 "clean added bytes to the vault")

    def test_nothing_is_created_inside_the_vault(self):
        with tempfile.TemporaryDirectory() as t:
            project = self._project(Path(t))
            before = {p.relative_to(project) for p in project.rglob("*")}
            clean.write_preview_to_disk(project, clean.build_preview(project))
            clean.apply_preview(project)
            after = {p.relative_to(project) for p in project.rglob("*")}
            self.assertEqual(after - before, set(),
                             f"clean created: {sorted(after - before)}")

    def test_deep_pass_is_also_net_subtractive(self):
        with tempfile.TemporaryDirectory() as t:
            project = self._project(Path(t))
            before_n, _ = self._count(project)
            clean.write_preview_to_disk(project, clean.build_preview(project, deep=True))
            clean.apply_preview(project)
            after_n, _ = self._count(project)
            self.assertLessEqual(after_n, before_n)

    def test_the_guard_refuses_a_create(self):
        from _vault_write import VaultCreateRefused, VaultWriteGuard
        with tempfile.TemporaryDirectory() as t:
            project = self._project(Path(t))
            with VaultWriteGuard(project) as g:
                with self.assertRaises(VaultCreateRefused):
                    g.rewrite(project / "notes" / "_index.md", "# Notes\n")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it**

Run: `cd adjudant/scripts && python3 -m unittest test_net_subtractive -v`
Expected: PASS, 4 tests. A failure names the file that leaked; fix `clean`, never the assertion.

- [ ] **Step 3: Run the full suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 4: Update the README counts and bump the version**

`adjudant/README.md` carries the test count and the verb count. Update both.

Run, from the repo root: `python3 scripts/bump_plugin_version.py adjudant 3.0.0`

This writes all four version files atomically. Do not hand-edit them; the `version-consistency` validator enforces the lockstep.

- [ ] **Step 5: Commit**

```bash
git add -A adjudant/ .claude-plugin/marketplace.json
git commit -m "test(adjudant): acceptance test - clean is net-subtractive

Asserts file count and byte count never grow, that nothing appears inside the
vault that was not there before, and that the guard refuses a create. The
complaint this closes: the cleanup tier filled more than it cleaned.

Bumps to 3.0.0: six verbs, fifteen kinds, five fields.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Done when

- `python3 -m unittest discover -p 'test_*.py'` reports `OK`.
- `python3 adjudant/scripts/validate.py` reports `PASS`.
- `test_net_subtractive.py` passes all four tests.
- `command-metadata.json` lists exactly `connect status clean dream draw board`.
- `dream` on a real decisions folder returns at most twenty candidates.
- No file named `port.py`, `shelf.py`, `kebab.py`, `tidy.py`, `ramasse_scan.py`, `sync.py`, `sitrep.py`, `check.py` or `advisor.py` exists.

## Not in this plan

The lifecycle folders, the link form, index generation and the truth checks that fill `status`'s three bands are plan 4. Twin generation is plan 5.

`status` ships in this plan with the signals the five absorbed verbs already had. Plan 4 replaces those with the truth checks, which is where the verb earns its place.
