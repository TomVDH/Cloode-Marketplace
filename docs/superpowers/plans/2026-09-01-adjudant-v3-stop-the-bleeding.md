# Adjudant v3, Plan 1: Stop the Bleeding

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adjudant stops adding files to the vault that nobody asked for.

**Architecture:** Two changes, independent of every later phase. First, every preview and backup directory moves out of the vault into an OS temp path with a retention cap, so a cleanup run stops writing three copies of everything into the thing it is cleaning. Second, the ambient hooks stop writing: a session note appears only when real work lands, unfinished harness todos stop becoming permanent vault notes, and the lifecycle markers that produced 164 dead lines are deleted.

**Tech Stack:** Python 3.9+ stdlib only, bash hooks, `unittest`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-01-adjudant-v3-design.md` (phases 0 and 1)

## Global Constraints

- **Stdlib only.** No new dependencies, in any task.
- **Python 3.9 floor.** No `match`, no `X | Y` unions at runtime in signatures evaluated at import (`from __future__ import annotations` is already in every module and stays).
- **Hooks never fail loudly.** Every hook exits 0 whatever happens. Wrap new I/O in the existing try/except shape and never let an exception escape `main()`.
- **The suite must be green after every task.** Run `python3 -m unittest discover -p 'test_*.py'` from `adjudant/scripts/`. Baseline is 1233 tests passing.
- **Validators must stay green.** Run `python3 adjudant/scripts/validate.py` from the repo root. Baseline is 35 validators passing.
- **Commit style:** Conventional Commits, scope `adjudant`. End every commit message with:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
- **Never write to the real vault during tests.** Every test builds a temp vault. `OB_VAULT` must be popped from the environment; copy the `_EnvHygiene` class from `test_precompact.py:27`.
- **The statusline is an external consumer.** `~/.claude/statusline-v2.sh` (a symlink into iCloud) greps adjudant's file surface. Task 5 updates it. Do not move a file it reads without doing Task 5 in the same session.

## File Structure

| File | Responsibility |
|---|---|
| `adjudant/scripts/_scratch.py` | **New.** Resolves adjudant's out-of-vault scratch root and prunes old backups. Single responsibility, imported by `tidy.py` and `repo_tidy.py`. |
| `adjudant/scripts/test__scratch.py` | **New.** Tests for the above. |
| `adjudant/scripts/_vault_walk.py` | Gains `_describe_vault_root` and `suggest_vault_roots`, back-ported from the twin. |
| `adjudant/scripts/connect.py` | Gains `--suggest-vaults` and `--create-vault`. |
| `adjudant/scripts/tidy.py` | Preview and backup paths move out of the vault. |
| `adjudant/scripts/repo_tidy.py` | Same, for the repo-side preview and backup. |
| `adjudant/scripts/board_bridge.py` | `bridge_ledger` deleted. The bridge stops manufacturing task notes. |
| `adjudant/hooks/scripts/session-start.sh` | Stops creating the session note and stops stamping UUIDs. |
| `adjudant/hooks/scripts/posttooluse-vault-log.py` | Creates the session note on first real write. Stops stamping. |
| `adjudant/hooks/scripts/sessionend.sh` | Stops the end marker and the ledger bridge. Still syncs the handoff. |
| `adjudant/hooks/scripts/precompact.py` | Stops clobbering the handoff at compaction. `--sync-only` still writes it. |
| `adjudant/hooks/scripts/postcompact.py` | Stops appending the compaction gist. |
| `adjudant/skills/adjudant/reference/state-contract.md` | **New.** The files and lines external consumers may depend on. |

---

## Task 1: Back-port the twin's vault-suggestion code

This is first because the twin holds the only copy. Any regeneration before this deletes it.

**Files:**
- Modify: `adjudant/scripts/_vault_walk.py` (insert after `_vault_search_roots`, which ends at line 581)
- Modify: `adjudant/scripts/connect.py:44-53` (import), `:802-831` (argparse and dispatch)
- Modify: `adjudant/skills/adjudant/reference/connect.md` (the runbook, 80 lines in main against 98 in the twin)
- Test: `adjudant/scripts/test__vault_walk.py`, `adjudant/scripts/test_connect.py`

**Interfaces:**
- Consumes: `_vault_search_roots(home: Optional[Path] = None) -> list[Path]`, already in main at `_vault_walk.py:547`, identical signature to the twin's.
- Produces: `suggest_vault_roots() -> list[dict]` where each dict has keys `path` (str), `label` (str), `kind` ("local" | "cloud"), `recommended` (bool). Task 5 does not use it; no later task depends on it.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test__vault_walk.py`:

```python
class TestSuggestVaultRoots(unittest.TestCase):

    def test_returns_only_existing_dirs_with_labels(self):
        import _vault_walk
        roots = _vault_walk.suggest_vault_roots()
        for entry in roots:
            self.assertTrue(Path(entry["path"]).is_dir(), entry["path"])
            self.assertTrue(entry["label"])
            self.assertIn(entry["kind"], ("local", "cloud"))
            self.assertIsInstance(entry["recommended"], bool)

    def test_no_duplicate_paths(self):
        import _vault_walk
        paths = [e["path"] for e in _vault_walk.suggest_vault_roots()]
        self.assertEqual(len(paths), len(set(paths)))

    def test_cloud_roots_are_recommended_and_home_is_not(self):
        import _vault_walk
        home = str(Path.home())
        for entry in _vault_walk.suggest_vault_roots():
            if entry["path"] == home:
                self.assertFalse(entry["recommended"])
                self.assertEqual(entry["kind"], "local")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestSuggestVaultRoots -v`
Expected: FAIL with `AttributeError: module '_vault_walk' has no attribute 'suggest_vault_roots'`

- [ ] **Step 3: Copy the two functions from the twin**

Insert into `adjudant/scripts/_vault_walk.py` immediately after `_vault_search_roots` ends (before `def _candidate_vault_paths`, currently line 583):

```python
def _describe_vault_root(root: Path, home: Path, is_local: bool) -> str:
    """Human label for a vault-root option in the guided 'no vault yet' setup."""
    if root == home:
        return "~ home folder (this machine only)"
    if root == home / "Documents":
        return "~/Documents (this machine only)"
    name = root.name
    if "iCloud~md~obsidian" in root.parts:
        label = "iCloud Drive (Obsidian folder)"
    elif name in ("com~apple~CloudDocs", "iCloudDrive"):
        label = "iCloud Drive"
    else:
        label = f"{name} (cloud sync)"   # OneDrive, OneDrive - <Org>, Dropbox, Google Drive, ...
    if str(root).startswith("/mnt/"):    # WSL: a Windows-owned folder seen from Linux
        label += " [Windows drive]"
    return label


def suggest_vault_roots() -> list[dict]:
    """Existing directories where a NEW vault could live, for the guided
    'no vault yet' setup. Cloud-sync roots (recommended for cross-machine
    continuity) come first, then local-only folders. Only roots that exist on
    THIS machine are returned, across macOS, Windows, and Linux/WSL, so the
    guidance never offers a dead path. Same taxonomy as `_vault_search_roots`."""
    home = Path.home()
    local_roots = {home, home / "Documents"}
    out: list[dict] = []
    seen: set[str] = set()
    for root in _vault_search_roots(home):
        try:
            if not root.is_dir():
                continue
        except OSError:
            continue
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        is_local = root in local_roots
        out.append({
            "path": key,
            "label": _describe_vault_root(root, home, is_local),
            "kind": "local" if is_local else "cloud",
            "recommended": not is_local,
        })
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestSuggestVaultRoots -v`
Expected: PASS, 3 tests

- [ ] **Step 5: Write the failing test for the connect flags**

Append to `adjudant/scripts/test_connect.py`:

```python
class TestGuidedVaultSetup(unittest.TestCase):

    def test_suggest_vaults_prints_json_and_exits_zero(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = connect.cli_main(["--suggest-vaults"])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertIn("vault_roots", payload)
        self.assertIsInstance(payload["vault_roots"], list)

    def test_create_vault_makes_the_dir_and_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "code"
            (project / ".claude").mkdir(parents=True)
            new_vault = Path(tmp) / "fresh-vault"
            connect.cli_main([
                "--project-root", str(project),
                "--vault-path", str(new_vault),
                "--create-vault",
                "--detect-only",
            ])
            self.assertTrue(new_vault.is_dir())
            self.assertTrue((new_vault / "projects").is_dir())
```

Add `import contextlib`, `import io`, `import json`, `import tempfile` to the file's imports if absent.

- [ ] **Step 6: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_connect.TestGuidedVaultSetup -v`
Expected: FAIL with `unrecognized arguments: --suggest-vaults`

- [ ] **Step 7: Wire the flags into connect.py**

In the import block at `adjudant/scripts/connect.py:44-53`, add `suggest_vault_roots,` (keep the list alphabetical: it goes after `resolve_vault,`).

In `cli_main`, after the `--vault-name` argument (line 810), add:

```python
    parser.add_argument("--suggest-vaults", action="store_true",
                        help="Print existing cloud/local vault-location options (JSON) and exit")
    parser.add_argument("--create-vault", action="store_true",
                        help="Create --vault-path (with a projects/ dir) if it does not exist")
```

Immediately after `args = parser.parse_args(argv)` (line 822), add:

```python
    if args.suggest_vaults:
        print(json.dumps({"vault_roots": suggest_vault_roots()}, indent=2))
        return 0
```

After the `project_root` existence check (after line 836), add:

```python
    # Create a brand-new vault at an explicit path when asked (guided setup):
    # the user picked a location that does not hold a vault yet.
    if args.create_vault and args.vault_path:
        new_vault = Path(args.vault_path).expanduser()
        if not new_vault.is_dir():
            new_vault.mkdir(parents=True, exist_ok=True)
            (new_vault / "projects").mkdir(exist_ok=True)
```

- [ ] **Step 8: Back-port the runbook, not just the code**

The flags alone are inert: nothing tells the model they exist or when to reach
for them. The twin's `reference/connect.md` carries an 18-line guided-setup
section that main's does not, and it is the half that makes the feature usable.

Copy the twin's `## No vault yet? Guided location setup` section into
`adjudant/skills/adjudant/reference/connect.md`, and update the vault-path
resolution row in its table to end with `→ guided location setup (see below)`.

Source: `furtive-follies/adjudant/skills/adjudant/reference/connect.md`.

Take the section verbatim with two edits: the default vault name stays
`Claude Vault`, and drop the `cost_warn_tokens: 10000` line, which is the
twin's forked threshold rather than main's 30000. Plan 5 un-forks that
constant properly; do not import the fork here.

Verify the section landed:

```bash
grep -c "No vault yet" adjudant/skills/adjudant/reference/connect.md
```

Expected: `1`

- [ ] **Step 9: Run the full suite**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`, 1238 tests

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`. Validator 16 (`reference-doc-links`) checks that every
relative link inside `reference/*.md` resolves, so a bad path in the copied
section fails here.

- [ ] **Step 10: Commit**

```bash
git add adjudant/scripts/_vault_walk.py adjudant/scripts/connect.py adjudant/scripts/test__vault_walk.py adjudant/scripts/test_connect.py adjudant/skills/adjudant/reference/connect.md
git commit -m "feat(adjudant): back-port guided vault setup from the furtive-follies twin

suggest_vault_roots() and --create-vault existed only in the twin and would
have been lost to any regeneration. Same taxonomy as _vault_search_roots.

The runbook comes with it: the twin's connect.md carries an 18-line guided-setup
section main lacks, and without it the flags are inert because nothing tells the
model they exist.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Create the out-of-vault scratch module

**Files:**
- Create: `adjudant/scripts/_scratch.py`
- Test: `adjudant/scripts/test__scratch.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, used by Tasks 3 and 4:
  - `scratch_dir(project_dir: Path, kind: str) -> Path` — returns the scratch directory for a project and a kind (`"tidy-preview"`, `"tidy-backup"`, `"repo-tidy-preview"`, `"repo-tidy-backup"`). Creates nothing.
  - `prune_backups(backup_root: Path, keep: int = BACKUP_KEEP) -> None` — deletes all but the newest `keep` subdirectories. Never raises.
  - `BACKUP_KEEP: int = 5`

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test__scratch.py`:

```python
"""Tests for adjudant/scripts/_scratch.py — the out-of-vault scratch root.

The whole point of this module is that adjudant's working files stop landing
inside the vault it is cleaning. The first test is the one that matters.
"""

import os
import tempfile
import unittest
from pathlib import Path

from _scratch import BACKUP_KEEP, prune_backups, scratch_dir


class TestScratchDir(unittest.TestCase):

    def test_scratch_is_never_inside_the_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "vault" / "projects" / "demo"
            project.mkdir(parents=True)
            for kind in ("tidy-preview", "tidy-backup"):
                got = scratch_dir(project, kind)
                self.assertNotIn(project, got.parents)
                self.assertNotEqual(got, project)

    def test_honours_TMPDIR(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            project.mkdir()
            old = os.environ.get("TMPDIR")
            os.environ["TMPDIR"] = tmp
            try:
                got = scratch_dir(project, "tidy-preview")
                self.assertTrue(str(got).startswith(tmp))
            finally:
                if old is None:
                    os.environ.pop("TMPDIR", None)
                else:
                    os.environ["TMPDIR"] = old

    def test_different_kinds_do_not_collide(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            project.mkdir()
            a = scratch_dir(project, "tidy-preview")
            b = scratch_dir(project, "tidy-backup")
            self.assertNotEqual(a, b)

    def test_hostile_project_name_cannot_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "a b/../../etc"
            got = scratch_dir(project, "tidy-preview")
            self.assertNotIn("..", got.parts)

    def test_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            project.mkdir()
            got = scratch_dir(project, "tidy-preview")
            self.assertFalse(got.exists())


class TestPruneBackups(unittest.TestCase):

    def _make(self, root: Path, n: int) -> list[Path]:
        made = []
        for i in range(n):
            d = root / f"2026090{i}T000000Z-x"
            d.mkdir(parents=True)
            (d / "f.txt").write_text("x")
            made.append(d)
        return made

    def test_keeps_newest_and_removes_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "backups"
            made = self._make(root, 8)
            prune_backups(root, keep=3)
            left = sorted(d.name for d in root.iterdir())
            self.assertEqual(len(left), 3)
            self.assertEqual(left, sorted(d.name for d in made[-3:]))

    def test_under_the_cap_removes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "backups"
            self._make(root, 2)
            prune_backups(root, keep=5)
            self.assertEqual(len(list(root.iterdir())), 2)

    def test_missing_root_is_benign(self):
        with tempfile.TemporaryDirectory() as tmp:
            prune_backups(Path(tmp) / "nope", keep=5)  # must not raise

    def test_default_cap_is_five(self):
        self.assertEqual(BACKUP_KEEP, 5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__scratch -v`
Expected: FAIL with `ModuleNotFoundError: No module named '_scratch'`

- [ ] **Step 3: Write the implementation**

Create `adjudant/scripts/_scratch.py`:

```python
#!/usr/bin/env python3
"""Adjudant scratch space — preview and backup directories, OUTSIDE the vault.

Every preview and backup adjudant wrote used to land inside the vault project
it was operating on, unbounded and never reaped: a tidy run whose whole benefit
was dropping three tags from twelve notes wrote roughly 25 files and 3x the
touched bytes into the vault, permanently. A cleanup tool that adds more than
it removes is not a cleanup tool.

Scratch now lives under $TMPDIR, keyed by project, and backups rotate. The
rotation is modelled on board.py's BACKUP_KEEP, which was the only backup path
in the plugin that ever pruned itself.

Nothing here creates a directory: callers mkdir when they are ready to write,
so a read-only run leaves no trace at all.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

# Newest N backup directories kept per project per kind. Mirrors board.py:69.
BACKUP_KEEP = 5

# A project directory name reaches us from the filesystem, so it is not
# trusted to be a safe path segment. Anything outside this class collapses to
# a hyphen, which makes traversal impossible by construction rather than by
# a check that could be forgotten.
_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]")


def _tmp_root() -> Path:
    """$TMPDIR when set, else the platform default. Mirrors task-ledger.py."""
    return Path(os.environ.get("TMPDIR") or tempfile.gettempdir())


def scratch_dir(project_dir: Path, kind: str) -> Path:
    """Where `kind` scratch for `project_dir` belongs. Creates nothing.

    `kind` is a short slug such as "tidy-preview" or "tidy-backup". The result
    is never inside `project_dir`, which is the entire point of this module.
    """
    key = _UNSAFE.sub("-", project_dir.name).strip("-") or "project"
    safe_kind = _UNSAFE.sub("-", kind).strip("-") or "scratch"
    return _tmp_root() / "adjudant" / key / safe_kind


def prune_backups(backup_root: Path, keep: int = BACKUP_KEEP) -> None:
    """Keep the newest `keep` subdirectories of `backup_root`, delete the rest.

    Timestamped names sort lexically by time, so a plain sort is chronological.
    Housekeeping only: every failure is swallowed, because failing to prune
    must never fail the operation that just succeeded.
    """
    try:
        existing = sorted(d for d in backup_root.iterdir() if d.is_dir())
    except OSError:
        return
    for stale in existing[:max(0, len(existing) - keep)]:
        shutil.rmtree(stale, ignore_errors=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd adjudant/scripts && python3 -m unittest test__scratch -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/_scratch.py adjudant/scripts/test__scratch.py
git commit -m "feat(adjudant): _scratch module - preview and backup paths outside the vault

Scratch keyed by project under \$TMPDIR, with board.py's rotation applied to
backups. Creates nothing; callers mkdir when they write.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Move tidy's preview and backup out of the vault

**Files:**
- Modify: `adjudant/scripts/tidy.py:83-84` (constants), `:97-107` (`detect_phase`), `:775-781` (`write_preview_to_disk`), `:949-975` (`apply_preview`), `:846` (summary text)
- Test: `adjudant/scripts/test_tidy.py`

**Interfaces:**
- Consumes: `scratch_dir`, `prune_backups`, `BACKUP_KEEP` from `_scratch` (Task 2).
- Produces: `detect_phase`, `write_preview_to_disk`, `apply_preview` keep their current signatures. Only the directories they use change.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_tidy.py`:

```python
class TestScratchIsOutsideTheVault(unittest.TestCase):
    """The defect this whole plan exists for: tidy wrote its working copies
    into the vault it was cleaning, and nothing ever reaped them."""

    def _project(self, tmp: Path) -> Path:
        project = tmp / "vault" / "projects" / "demo"
        (project / "notes").mkdir(parents=True)
        _w(project / "notes" / "a.md",
           "---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\ntags:\n  - ob/note\n---\n\n# A\n")
        _w(project / "notes" / "b.md",
           "---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\ntags:\n  - ob/note\n---\n\n# B\n")
        return project

    def test_preview_writes_nothing_into_the_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            before = {p for p in project.rglob("*")}
            change_set = build_preview(project)
            write_preview_to_disk(project, change_set)
            after = {p for p in project.rglob("*")}
            self.assertEqual(before, after,
                             "tidy preview created files inside the vault project")

    def test_apply_writes_no_backup_into_the_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            change_set = build_preview(project)
            write_preview_to_disk(project, change_set)
            apply_preview(project)
            stray = [p for p in project.rglob(".adjudant-*")]
            self.assertEqual(stray, [],
                             f"tidy apply left scratch in the vault: {stray}")

    def test_detect_phase_reads_the_scratch_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            self.assertEqual(detect_phase(project), "fresh")
            change_set = build_preview(project)
            write_preview_to_disk(project, change_set)
            self.assertEqual(detect_phase(project), "preview")
            apply_preview(project)
            self.assertEqual(detect_phase(project), "applied")

    def test_backups_rotate(self):
        from _scratch import BACKUP_KEEP, scratch_dir
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            for i in range(BACKUP_KEEP + 3):
                _w(project / "notes" / f"n{i}.md",
                   "---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\ntags:\n  - ob/note\n---\n\n# N\n")
                change_set = build_preview(project)
                write_preview_to_disk(project, change_set)
                apply_preview(project)
            root = scratch_dir(project, "tidy-backup")
            kept = [d for d in root.iterdir() if d.is_dir()]
            self.assertLessEqual(len(kept), BACKUP_KEEP)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_tidy.TestScratchIsOutsideTheVault -v`
Expected: FAIL on `test_preview_writes_nothing_into_the_project` — the preview directory appears inside the project.

- [ ] **Step 3: Point tidy at the scratch module**

In `adjudant/scripts/tidy.py`, add to the imports beside the other local imports (after line 41, `from _cost import ...`):

```python
from _scratch import BACKUP_KEEP, prune_backups, scratch_dir
```

Replace lines 83-84:

```python
PREVIEW_DIR_NAME = ".adjudant-tidy-preview"
BACKUP_DIR_NAME = ".adjudant-tidy-backup"
```

with:

```python
# Kept as scratch *kinds*, not directory names: since v3 these resolve under
# $TMPDIR via _scratch.scratch_dir, never inside the vault. The names are
# unchanged so a reader grepping for the old dirs lands here.
PREVIEW_KIND = "tidy-preview"
BACKUP_KIND = "tidy-backup"


def preview_dir(project_dir: Path) -> Path:
    return scratch_dir(project_dir, PREVIEW_KIND)


def backup_root(project_dir: Path) -> Path:
    return scratch_dir(project_dir, BACKUP_KIND)
```

In `detect_phase` (line 97), replace the two path lines:

```python
    preview = preview_dir(project_dir)
    backup = backup_root(project_dir)
```

In `write_preview_to_disk` (line 777), replace:

```python
    preview = project_dir / PREVIEW_DIR_NAME
```

with:

```python
    preview = preview_dir(project_dir)
    preview.parent.mkdir(parents=True, exist_ok=True)
```

and change `preview.mkdir()` on the next line to `preview.mkdir(parents=True)`.

At line 846, change the discard hint to name the real path:

```python
    summary_lines.append(f"- To discard: delete `{preview}`")
```

In `apply_preview` (line 949), replace the preview lookup at the top of the function body (`preview = project_dir / PREVIEW_DIR_NAME`) with `preview = preview_dir(project_dir)`, and replace the backup block at lines 969-972:

```python
    backup_root_dir = backup_root(project_dir)
    backup_root_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(tempfile.mkdtemp(prefix=f"{timestamp}-", dir=backup_root_dir))
```

At the end of `apply_preview`, immediately before `return backup_dir`, add:

```python
    prune_backups(backup_root_dir, BACKUP_KEEP)
```

- [ ] **Step 4: Run the new tests**

Run: `cd adjudant/scripts && python3 -m unittest test_tidy.TestScratchIsOutsideTheVault -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Fix the existing tests that import the old names**

`test_tidy.py` imports `PREVIEW_DIR_NAME` and `BACKUP_DIR_NAME` at its top. Replace those two import lines with `preview_dir, backup_root,` and update every use: a test asserting `project / PREVIEW_DIR_NAME` becomes `preview_dir(project)`, and `project / BACKUP_DIR_NAME` becomes `backup_root(project)`.

Run: `cd adjudant/scripts && python3 -m unittest test_tidy -v 2>&1 | tail -5`
Expected: `OK`

- [ ] **Step 6: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`. If validators 9, 13 or 22 fail, they are the ones that check the code repo's `.gitignore` lists these directories. The directories no longer exist, so delete those three validators and the `.gitignore` entries they guard, and update the validator count in `validate.py`'s docstring.

- [ ] **Step 7: Commit**

```bash
git add adjudant/scripts/tidy.py adjudant/scripts/test_tidy.py adjudant/scripts/validate.py .gitignore
git commit -m "fix(adjudant): tidy scratch moves out of the vault, with rotation

Preview and backup landed inside the vault project and were never reaped: a
run that dropped three tags from twelve notes wrote ~25 files and 3x the
touched bytes, permanently. Both now resolve under \$TMPDIR and backups keep
the newest 5.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Move repo_tidy's preview and backup out of the repo

**Files:**
- Modify: `adjudant/scripts/repo_tidy.py:55-70` (`write_preview`), `:72-125` (`apply_preview`)
- Test: `adjudant/scripts/test_repo_tidy.py`

**Interfaces:**
- Consumes: `scratch_dir`, `prune_backups`, `BACKUP_KEEP` from `_scratch` (Task 2).
- Produces: `write_preview(root, repairs) -> Path` and `apply_preview(root) -> Path` keep their signatures.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_repo_tidy.py`:

```python
class TestRepoScratchIsOutsideTheRepo(unittest.TestCase):

    def test_preview_and_backup_land_outside(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            plugin = root / "demo"
            (plugin / "skills" / "demo").mkdir(parents=True)
            (plugin / ".claude").mkdir(parents=True)
            repairs = repo_tidy.detect(root)
            repo_tidy.write_preview(root, repairs)
            self.assertEqual(list(root.rglob(".adjudant-repo-tidy-*")), [])
            repo_tidy.apply_preview(root)
            self.assertEqual(list(root.rglob(".adjudant-repo-tidy-*")), [])
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_repo_tidy.TestRepoScratchIsOutsideTheRepo -v`
Expected: FAIL — the preview directory appears under `root`.

- [ ] **Step 3: Point repo_tidy at the scratch module**

Add to the imports in `adjudant/scripts/repo_tidy.py`:

```python
from _scratch import BACKUP_KEEP, prune_backups, scratch_dir
```

In `write_preview`, replace `preview = root / PREVIEW_DIR_NAME` with:

```python
    preview = scratch_dir(root, "repo-tidy-preview")
    preview.parent.mkdir(parents=True, exist_ok=True)
```

In `apply_preview`, replace `preview = root / PREVIEW_DIR_NAME` with `preview = scratch_dir(root, "repo-tidy-preview")`, and replace the backup line:

```python
    backup_parent = scratch_dir(root, "repo-tidy-backup")
    backup_dir = backup_parent / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
```

Before `return backup_dir` at the end, add:

```python
    prune_backups(backup_parent, BACKUP_KEEP)
```

Delete the now-unused `PREVIEW_DIR_NAME` and `BACKUP_DIR_NAME` constants and fix any remaining references.

- [ ] **Step 4: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_repo_tidy -v 2>&1 | tail -3`
Expected: `OK`, 9 tests

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/repo_tidy.py adjudant/scripts/test_repo_tidy.py
git commit -m "fix(adjudant): repo-tidy scratch moves out of the repo, with rotation

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Update the statusline and write the state contract

The statusline lives outside this repo and reads adjudant's file surface directly. Tasks 3 and 4 just moved two things it greps.

**Files:**
- Modify: `~/Library/Mobile Documents/com~apple~CloudDocs/Projects/IDE/claude/statusline-v2.sh` (lines 585-593, the verb-state block)
- Create: `adjudant/skills/adjudant/reference/state-contract.md`

**Interfaces:**
- Consumes: `scratch_dir`'s layout from Task 2 — `$TMPDIR/adjudant/{project-name}/{kind}`.
- Produces: nothing code-level. The contract document is read by later plans.

- [ ] **Step 1: Read the current block to confirm it is unchanged**

Run: `sed -n '583,596p' "$HOME/.claude/statusline-v2.sh"`
Expected: the `if`/`elif` chain testing `${proj_dir}/.adjudant-tidy-preview` and friends.

- [ ] **Step 2: Replace the verb-state block**

Replace lines 585 to 593 of `~/.claude/statusline-v2.sh` with:

```bash
  # -- Verb state. Gerund = a preview is pending review. Since adjudant v3 the
  #    previews live under $TMPDIR, not in the vault: a cleanup tool must not
  #    write into the thing it is cleaning. The "tidied"/"ported" past-tense
  #    states are gone with them — they only ever said "a backup directory
  #    exists", which is now true after every run and so carries no signal.
  _adj_scratch="${TMPDIR:-/tmp}/adjudant/$(basename "$proj_dir")"
  if   [ -d "${_adj_scratch}/tidy-preview" ];      then state="tidying";      scol="$VAULT_STALE"
  elif [ -d "${_adj_scratch}/repo-tidy-preview" ]; then state="repo-tidying"; scol="$VAULT_STALE"
  else                                                  state="fresh";       scol="$VAULT_OK"
  fi
```

Note the scratch key is the basename of the *vault project* directory for tidy, and of the *repo root* for repo-tidy. Where the statusline has both, prefer `proj_vault` for the tidy test if it is set by that point in the script; otherwise leave `proj_dir` and record the limitation in the contract.

- [ ] **Step 3: Verify the statusline still renders**

Run:

```bash
echo '{"session_id":"test","model":{"display_name":"Test"},"workspace":{"current_dir":"."}}' | bash "$HOME/.claude/statusline-v2.sh"
```

Expected: a rendered status line, no bash errors on stderr.

- [ ] **Step 4: Write the state contract**

Create `adjudant/skills/adjudant/reference/state-contract.md`:

```markdown
# State contract

Files and lines outside adjudant that read adjudant's output. Anything listed
here is a published interface: moving or reformatting it silently breaks a
consumer that has no test in this repo.

## Consumer: the statusline

`~/.claude/statusline-v2.sh`, a symlink into
`~/Library/Mobile Documents/com~apple~CloudDocs/Projects/IDE/claude/`. It lives
in iCloud and syncs to both machines, so it is edited once and lands on both.

| It reads | For |
|---|---|
| `.claude/adjudant` breadcrumb, `vault_path` and `slug` | vault location, project name |
| `$TMPDIR/adjudant/{project}/tidy-preview` (dir exists) | "tidying" state |
| `$TMPDIR/adjudant/{project}/repo-tidy-preview` (dir exists) | "repo-tidying" state |
| `projects/{zone}/{slug}/brief.md`, `status:` | lifecycle drift |
| `_handoff.md`, the line matching `(🔴\|🟡\|🟢).*handoff age` | freshness, and `🔴 **STALE**` |
| `board/board-data.json`, card count by column | open count and direction |
| `tasks/*.md` mtimes against the deck's | board lag |
| newest `dreams/{YYYY-MM-DD}.md`, first line matching a finding count | dream age |
| `$TMPDIR/adjudant-task-ledger-{session_id}.jsonl` | in-flight task count |

## Rules

1. The handoff traffic-light line keeps its exact format. It is the one place
   emoji are load-bearing rather than decorative.
2. The dream report keeps a machine-readable finding count on its first content
   line.
3. The task ledger keeps its `$TMPDIR` path and JSONL shape. Only its replay
   into vault task notes was removed.
4. Scratch is `$TMPDIR/adjudant/{project}/{kind}`. Adding a kind is safe;
   renaming one is not.
5. Anything added to this table needs the statusline updated in the same
   change.
```

- [ ] **Step 5: Commit**

```bash
git add adjudant/skills/adjudant/reference/state-contract.md
git commit -m "docs(adjudant): state contract - what external consumers read

The statusline greps adjudant's file surface and lives outside this repo, so
nothing here could catch a break. Records the published surface and the rules
that protect it.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Session notes are created on first real write, not on session open

This is the single change that removes 76 empty session notes and 164 dead resume markers.

**Files:**
- Modify: `adjudant/hooks/scripts/session-start.sh:245-294` (creation and resume blocks)
- Modify: `adjudant/hooks/scripts/posttooluse-vault-log.py:210-243` (create before appending)
- Test: `adjudant/scripts/test_hook_shell.py`, `adjudant/scripts/test_posttooluse_vault_log.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `ensure_session_note(sessions_dir: Path, today: str) -> Path` in `posttooluse-vault-log.py`, creating the note with the v3 shape when absent and returning its path. The caller already holds `ts` and writes the log line itself. Task 7 and Task 9 both rely on the note being absent until a real write happens.

- [ ] **Step 1: Write the failing shell test**

Append to `adjudant/scripts/test_hook_shell.py`, inside `TestSessionStartHook`:

```python
    def test_session_start_creates_no_note(self):
        # v3: a session that does no vault work leaves no trace. 76 of 261
        # notes in the real vault were start/end markers and nothing else.
        with tempfile.TemporaryDirectory() as tmp:
            project, home = self._project(
                Path(tmp), "vault_path: {vault}\nvault_name: vault\nslug: demo\n")
            r = _run("session-start.sh", project, home,
                     stdin=json.dumps({"session_id": "s1", "source": "startup"}))
            self.assertEqual(r.returncode, 0)
            notes = list((home / "vault" / "projects" / "demo" / "sessions").glob("*.md"))
            self.assertEqual(notes, [], f"session-start created {notes}")

    def test_session_start_appends_no_resume_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, home = self._project(
                Path(tmp), "vault_path: {vault}\nvault_name: vault\nslug: demo\n")
            sessions = home / "vault" / "projects" / "demo" / "sessions"
            sessions.mkdir(parents=True, exist_ok=True)
            note = sessions / f"{date.today().isoformat()}.md"
            note.write_text("---\ntype: session\n---\n\n## Log\n\n- 09:00 · a.md written\n")
            before = note.read_text()
            _run("session-start.sh", project, home,
                 stdin=json.dumps({"session_id": "s2", "source": "resume"}))
            self.assertEqual(note.read_text(), before,
                             "session-start still writes into the note")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_hook_shell.TestSessionStartHook.test_session_start_creates_no_note test_hook_shell.TestSessionStartHook.test_session_start_appends_no_resume_marker -v`
Expected: FAIL — a note is created, and the resume marker is appended.

- [ ] **Step 3: Strip creation and stamping from session-start.sh**

In `adjudant/hooks/scripts/session-start.sh`, delete the whole block from line 236 (`# Render the session_id block:`) through line 294 (`# else: write failed and no file exists — stay silent, claim nothing.`), and replace it with:

```bash
  # v3: the session note is created by the first real vault write, not here.
  # This hook used to create one on every open and append a resume marker on
  # every reopen, which produced 76 empty notes and 164 markers followed by
  # nothing. It also stamped a conversation UUID per resume, stacking 18 into
  # one note. Provenance now rides on the artefacts themselves.
  if [ -f "$session_file" ]; then
    printf -- '- Session note: `%s/sessions/%s.md`\n' "$rel_project" "$today"
  fi
```

- [ ] **Step 4: Run the shell tests**

Run: `cd adjudant/scripts && python3 -m unittest test_hook_shell -v 2>&1 | tail -3`
Expected: `OK`. Tests asserting the old creation behaviour will fail; delete those tests, since the behaviour they protect is the defect being removed. Name them in the commit message.

- [ ] **Step 5: Write the failing test for lazy creation**

Append to `adjudant/scripts/test_posttooluse_vault_log.py`. It subclasses the
file's existing `_HookHarness` (line 35), whose helpers are `self._fixture(tmp)`
returning `(project, project_root)`, `self._note(proot, rel)`,
`self._payload(path)` and `self._run(project, payload)`:

```python
class TestLazySessionNote(_HookHarness):

    def test_first_write_creates_the_note(self):
        # The note appears exactly when there is something to record in it.
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            self.assertFalse((proot / "sessions").exists())
            note_path = self._note(proot, "notes/a.md")
            rc = self._run(project, self._payload(note_path))
            self.assertEqual(rc, 0)
            session = proot / "sessions" / f"{date.today().isoformat()}.md"
            self.assertTrue(session.is_file())
            text = session.read_text()
            self.assertIn("type: session", text)
            self.assertIn("## Log", text)
            self.assertIn("a.md", text)

    def test_second_write_appends_and_does_not_recreate(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            for name in ("notes/a.md", "notes/b.md"):
                self._run(project, self._payload(self._note(proot, name)))
            session = proot / "sessions" / f"{date.today().isoformat()}.md"
            text = session.read_text()
            self.assertEqual(text.count("type: session"), 1)
            self.assertIn("a.md", text)
            self.assertIn("b.md", text)
```

Add `from datetime import date` to the file's imports if absent. Confirm
`_fixture`'s exact return tuple by reading line 46 before writing the test.

- [ ] **Step 6: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_posttooluse_vault_log.TestLazySessionNote -v`
Expected: FAIL — no note is created, because the hook only appends to an existing one.

- [ ] **Step 7: Create the note in the vault-log hook**

In `adjudant/hooks/scripts/posttooluse-vault-log.py`, add above `main()`:

```python
_SESSION_NOTE = """---
type: session
created: {today}
updated: {today}
---

## Log

"""


def ensure_session_note(sessions_dir: Path, today: str) -> Path:
    """Today's session note, created if this is the first real write.

    v3 moved creation here from SessionStart: a note that exists only because
    a session opened records nothing, and 29% of the vault's notes were exactly
    that. Created with noclobber semantics so two async hooks racing on the
    first write of the day cannot truncate each other.
    """
    note = sessions_dir / f"{today}.md"
    if note.exists():
        return note
    try:
        sessions_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(note, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return note                      # the other hook won; append to theirs
    except OSError:
        return note                      # read-only vault: caller's append no-ops
    try:
        with os.fdopen(fd, "w") as f:
            f.write(_SESSION_NOTE.format(today=today))
    except OSError:
        pass
    return note
```

Add `import os` to the imports if absent.

In `main()`, replace the Job 1 block at lines 234-243 with:

```python
    # --- Job 1: append a session-log entry, creating the note if this is the
    # first real write of the day ---
    is_decision = parts[0] == "decisions"
    label = "Decision" if is_decision else "Added"
    link = f"[[{slug}/{'/'.join(parts)}]]"
    session_file = ensure_session_note(project_root / "sessions", today)
    try:
        with session_file.open("a") as f:
            f.write(f"- {ts} · {label}: {link}\n")
    except OSError:
        pass  # log-write failure must not block job 2
```

Note the link form drops the `projects/` prefix, per the spec's zone-less link rule. Later plans complete that change; this is the one writer touched here.

- [ ] **Step 8: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_posttooluse_vault_log -v 2>&1 | tail -3`
Expected: `OK`. Tests asserting the old `[[projects/{slug}/...]]` link form need their expected string updated; `test_nested_path_link_keeps_full_relative_path` is one.

- [ ] **Step 9: Run the full suite**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 10: Commit**

```bash
git add adjudant/hooks/scripts/session-start.sh adjudant/hooks/scripts/posttooluse-vault-log.py adjudant/scripts/test_hook_shell.py adjudant/scripts/test_posttooluse_vault_log.py
git commit -m "feat(adjudant): session notes are created by the first real write

SessionStart created a note on every open and a resume marker on every reopen:
76 of 261 notes in the real vault held nothing but markers, and 164 resume
markers were followed by nothing at all. It also stamped a conversation UUID
per resume, stacking 18 into a single note.

Creation moves to the vault-log hook, so a note exists exactly when there is
something in it.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Stop manufacturing task notes from the harness todo list

The single largest contributor of unrequested vault files.

**Files:**
- Modify: `adjudant/scripts/board_bridge.py:142-166` (delete `bridge_ledger`), `:169-202` (drop `--bridge`)
- Modify: `adjudant/hooks/scripts/sessionend.sh:127-142` (drop the bridge call)
- Test: `adjudant/scripts/test_board_bridge.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `board_bridge.main` keeps only `--ensure-only` and `--project-dir`. `bridge_ledger`, `render_task_note`, `read_ledger` and `_FALLBACK_TEMPLATE` are deleted. The `$TMPDIR` ledger written by `task-ledger.py` is untouched; the statusline still reads it.

- [ ] **Step 1: Write the failing test**

Replace the `TestBridgeSurvivors` class in `adjudant/scripts/test_board_bridge.py` with:

```python
class TestLedgerNeverBecomesVaultNotes(_BridgeCase):
    """v3: an unfinished harness todo is not a vault note. Every todo that
    never emitted a completion event used to become a permanent markdown file
    at session end, which is why tasks/ accumulated without limit."""

    def test_bridge_flag_is_gone(self):
        ledger = self._write_ledger([_entry("T-1", "Fix the widget")])
        with self.assertRaises(SystemExit):
            self._main(["--bridge", str(ledger), "--project-dir", str(self.project)])

    def test_ensure_only_writes_no_task_notes(self):
        (self.project / "tasks").mkdir(parents=True, exist_ok=True)
        rc, _ = self._main(["--ensure-only", "--project-dir", str(self.project)])
        self.assertEqual(rc, 0)
        self.assertEqual(list((self.project / "tasks").glob("*.md")), [])

    def test_ensure_only_still_births_the_board_from_existing_tasks(self):
        tasks = self.project / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "real-card.md").write_text(
            "---\ntype: task\nstatus: doing\ncreated: 2026-09-01\nupdated: 2026-09-01\n---\n\n# Real card\n")
        rc, _ = self._main(["--ensure-only", "--project-dir", str(self.project)])
        self.assertEqual(rc, 0)
        self.assertTrue((self.project / "board" / "board-data.json").is_file())
        ids = [c["id"] for c in self._deck()["cards"]]
        self.assertIn("real-card", ids)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_board_bridge.TestLedgerNeverBecomesVaultNotes -v`
Expected: FAIL on `test_bridge_flag_is_gone` — `--bridge` is still accepted.

- [ ] **Step 3: Delete the manufacturing code**

In `adjudant/scripts/board_bridge.py`:

Delete `bridge_ledger` (lines 142-166), `render_task_note` (lines 123-139), `_strip_frontmatter_comments`, `read_ledger`, `_FALLBACK_TEMPLATE` and the `TEMPLATE` constant, plus any now-unused imports (`kebab`, `parse_frontmatter`, `json` if unused).

Replace the argparse block in `main` (lines 170-180) with:

```python
    p = argparse.ArgumentParser(
        prog="board_bridge.py",
        description="Ensure the board deck and HTML exist and match tasks/.")
    p.add_argument("--ensure-only", action="store_true", required=True,
                   help="run board.ensure_board for the project (the only mode since v3)")
    p.add_argument("--project-dir", default=".",
                   help="project root (breadcrumb-resolved; default cwd)")
    args = p.parse_args(argv)
```

Delete the `if args.bridge:` block (lines 191-194).

Update the module docstring to record why: an id without a `TaskCompleted` event is an abandoned or renamed todo, not a work item, and treating it as one filled `tasks/` with cards nobody wrote.

- [ ] **Step 4: Drop the bridge call from sessionend.sh**

In `adjudant/hooks/scripts/sessionend.sh`, replace lines 127-142 with:

```bash
  # Board reseed only. The ledger replay that turned every uncompleted harness
  # todo into a permanent vault note was removed in v3: an id with no
  # TaskCompleted event is an abandoned or renamed todo, not a work item. The
  # ledger itself stays in $TMPDIR, where the statusline reads it.
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$CLAUDE_PLUGIN_ROOT/scripts/board_bridge.py" ] \
     && command -v python3 >/dev/null 2>&1 \
     && [ -f "$vault_project/board/board-data.json" ]; then
    python3 "$CLAUDE_PLUGIN_ROOT/scripts/board_bridge.py" --ensure-only \
      --project-dir "$vault_project" >/dev/null 2>&1 || true
  fi
```

- [ ] **Step 5: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_board_bridge -v 2>&1 | tail -3`
Expected: `OK`. Delete the obsolete tests: `test_survivor_bridged`, `test_completed_skipped`, `test_slug_dedup`, `test_bridge_triggers_board_creation`, `test_malformed_ledger_line_skipped`, `test_unsluggable_subject_skipped`, `test_missing_ledger_is_benign`, and the `kebab` tests if `kebab` is no longer imported here. Keep every `task-ledger.py` test: that hook is unchanged.

- [ ] **Step 6: Run the full suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 7: Commit**

```bash
git add adjudant/scripts/board_bridge.py adjudant/hooks/scripts/sessionend.sh adjudant/scripts/test_board_bridge.py
git commit -m "fix(adjudant): stop turning unfinished harness todos into vault notes

At session end every todo without a TaskCompleted event became a permanent
markdown file. Status changes other than completion fire no events, so
abandoned, superseded and merely renamed todos all qualified. This was the
largest single source of unrequested vault files.

The \$TMPDIR ledger stays; only its replay into tasks/ is removed.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Delete the compaction and session-end markers

**Files:**
- Modify: `adjudant/hooks/scripts/postcompact.py:140-181` (drop the gist append)
- Modify: `adjudant/hooks/scripts/precompact.py:188-205` (delete `append_pause_marker`) and its call site in `main`
- Modify: `adjudant/hooks/scripts/sessionend.sh:105-119` (drop the end marker)
- Test: `test_postcompact.py`, `test_precompact.py`, `test_hook_shell.py`

**Interfaces:**
- Consumes: Task 6's guarantee that a note exists only when work happened.
- Produces: `postcompact.main()` becomes a no-op returning 0. `precompact.append_pause_marker` is deleted; `mirror_handoff` is untouched by this task and changes in Task 9.

- [ ] **Step 1: Write the failing tests**

In `test_postcompact.py`, replace the class body of the append tests with:

It subclasses the file's existing `_HookHarness` (line 36), whose helpers are
`self._fixture(tmp)` returning `(project, project_root)` and
`self._run_main(project, payload)`:

```python
class TestNoCompactionMarkers(_HookHarness):

    def test_compaction_appends_nothing(self):
        # 34 files in the real vault carry truncated model reasoning from this
        # hook ("· compacted: <analysis> Let me chronologically work through…").
        # A compaction is not project work.
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            note = proot / "sessions" / f"{date.today().isoformat()}.md"
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text("---\ntype: session\n---\n\n## Log\n\n- 09:00 · a.md written\n")
            before = note.read_text()
            rc = self._run_main(project, {"summary": "a long compaction summary"})
            self.assertEqual(rc, 0)
            self.assertEqual(note.read_text(), before)
```

In `test_hook_shell.py`, add to the session-end tests:

```python
    def test_session_end_appends_no_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, home = self._project(
                Path(tmp), "vault_path: {vault}\nvault_name: vault\nslug: demo\n")
            sessions = home / "vault" / "projects" / "demo" / "sessions"
            sessions.mkdir(parents=True, exist_ok=True)
            note = sessions / f"{date.today().isoformat()}.md"
            note.write_text("---\ntype: session\n---\n\n## Log\n\n- 09:00 · a.md written\n")
            before = note.read_text()
            _run("sessionend.sh", project, home,
                 stdin=json.dumps({"session_id": "s1"}))
            self.assertEqual(note.read_text(), before)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd adjudant/scripts && python3 -m unittest test_postcompact.TestNoCompactionMarkers test_hook_shell.TestSessionEndHook.test_session_end_appends_no_marker -v`
Expected: FAIL — both still append.

- [ ] **Step 3: Gut postcompact.py**

Replace the body of `main()` in `adjudant/hooks/scripts/postcompact.py` with:

```python
def main() -> int:
    # v3: this hook writes nothing. It appended a "compacted: {gist}" line to
    # the session note, and the gist was the harness summary truncated
    # mid-sentence — 34 files in the real vault carry a fragment of raw model
    # reasoning because of it, several as exact consecutive duplicates. A
    # compaction is a harness event, not project work.
    #
    # The hook stays registered so stdin is drained: an unread PostCompact
    # payload EPIPEs the harness writer when this process exits.
    try:
        if not sys.stdin.isatty():
            sys.stdin.read()
    except Exception:
        pass
    return 0
```

Delete the now-unused helpers (`_gist`, the session-file lookup, the fallback-keys logic) and their imports.

- [ ] **Step 4: Delete the pause marker from precompact.py**

Delete `append_pause_marker` (lines 188-205) and its call in `main()`. Leave `mirror_handoff` in place; Task 9 changes when it runs.

- [ ] **Step 5: Drop the end marker from sessionend.sh**

Replace lines 105-119 of `adjudant/hooks/scripts/sessionend.sh` with:

```bash
  # v3: no end marker. Together with the start, resume and pause markers this
  # produced 164 "session resumed" lines followed by nothing, and a guard that
  # suppressed exactly one of the four when the tail was already a marker.
  # A session note records work, and the absence of a note records its absence.
  :
```

- [ ] **Step 6: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_postcompact test_precompact test_hook_shell -v 2>&1 | tail -3`
Expected: `OK`. Delete the obsolete tests that asserted the markers existed: in `test_postcompact.py` those are `test_appends_gist_line`, `test_fallback_keys_tried_in_order`, `test_gist_single_line`, `test_gist_clipped_to_160_chars`, `test_gist_lands_in_latest_note`, `test_gist_skips_future_dated_note`, `test_gist_lands_in_shelved_project`; in `test_precompact.py`, `test_pause_tombstone_uses_middle_dot_next_separator` and `test_midnight_straddle_pause_marker_lands_in_latest_note`. Keep every fail-closed and traversal test in both files.

- [ ] **Step 7: Run the full suite**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add adjudant/hooks/scripts/postcompact.py adjudant/hooks/scripts/precompact.py adjudant/hooks/scripts/sessionend.sh adjudant/scripts/test_postcompact.py adjudant/scripts/test_precompact.py adjudant/scripts/test_hook_shell.py
git commit -m "fix(adjudant): delete the session lifecycle markers

started, resumed, paused, ended and compacted produced 164 resume markers
followed by nothing and 34 files carrying truncated model reasoning. A session
note records work; the absence of a note records the absence of work.

postcompact keeps its registration to drain stdin, and writes nothing.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: The handoff is written once, and adjudant declares its dependency on remember

**Files:**
- Modify: `adjudant/hooks/scripts/precompact.py` (`main`, `--sync-only` path)
- Modify: `adjudant/scripts/sync.py:103` and `adjudant/hooks/scripts/precompact.py:138` (two copies of `find_remember_source`, one taking `project_root` and one `project_dir`)
- Modify: `adjudant/scripts/_handoff_freshness.py` (gains the shared picker and a presence probe)
- Modify: `adjudant/scripts/check.py` (reports the probe)
- Test: `test_precompact.py`, `test_handoff_freshness.py`, `test_check.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, in `_handoff_freshness.py`:
  - `find_remember_source(project_dir: Path) -> Optional[Path]` — the single copy, replacing the two that share a name but not a parameter name.
  - `remember_status(project_dir: Path) -> dict` — `{"present": bool, "source": Optional[str], "empty": bool}`, shaped like `check.py`'s existing `_suitcase_status()`.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_handoff_freshness.py`:

```python
The file already imports the module as `pc` (`import _handoff_freshness as pc`):

```python
class TestRememberProbe(unittest.TestCase):

    def test_absent_remember_is_reported_not_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "code"
            project.mkdir()
            st = pc.remember_status(project)
            self.assertFalse(st["present"])
            self.assertIsNone(st["source"])

    def test_present_but_empty_is_distinguished(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "code"
            (project / ".remember").mkdir(parents=True)
            (project / ".remember" / "remember.md").write_text("")
            st = pc.remember_status(project)
            self.assertTrue(st["present"])
            self.assertTrue(st["empty"])

    def test_present_with_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "code"
            (project / ".remember").mkdir(parents=True)
            (project / ".remember" / "remember.md").write_text("## State\nwork\n")
            st = pc.remember_status(project)
            self.assertTrue(st["present"])
            self.assertFalse(st["empty"])
            self.assertTrue(st["source"].endswith("remember.md"))

    def test_one_picker_only(self):
        # The picker existed twice, in sync.py and precompact.py, and had
        # already drifted. _handoff_freshness exists to stop exactly that.
        import precompact
        import sync
        self.assertIs(precompact.find_remember_source, pc.find_remember_source)
        self.assertIs(sync.find_remember_source, pc.find_remember_source)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_handoff_freshness.TestRememberProbe -v`
Expected: FAIL with `AttributeError: module '_handoff_freshness' has no attribute 'remember_status'`

- [ ] **Step 3: Move the picker and add the probe**

In `adjudant/scripts/_handoff_freshness.py`, add:

```python
# The handoff body's source, when the remember plugin is installed. This lived
# in two near-identical copies (sync.py and precompact.py) that had already
# drifted; this module exists to hold exactly this kind of shared primitive.
_REMEMBER_CANDIDATES = ("remember.md", "now.md")


def find_remember_source(project_dir: Path) -> Optional[Path]:
    """`.remember/remember.md`, falling back to `.remember/now.md`. None when
    the remember plugin is not installed for this project."""
    base = project_dir / ".remember"
    for name in _REMEMBER_CANDIDATES:
        candidate = base / name
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def remember_status(project_dir: Path) -> dict:
    """Whether the remember plugin is usable here, for `check` to report.

    Adjudant read `.remember/` as the handoff's source and said nothing when it
    was missing or empty: 7 of 12 handoffs in the real vault were a banner and
    an empty body, because an empty source mirrored to an empty handoff. A
    dependency that fails silently is worse than one that is absent.
    """
    source = find_remember_source(project_dir)
    if source is None:
        return {"present": False, "source": None, "empty": True}
    try:
        empty = not source.read_text(errors="replace").strip()
    except OSError:
        empty = True
    return {"present": True, "source": str(source), "empty": empty}
```

In both `sync.py` and `precompact.py`, delete the local `find_remember_source` definition (`sync.py:103`, `precompact.py:138` — same name, one takes `project_root` and the other `project_dir`, which is the drift) and import the shared one:

```python
from _handoff_freshness import find_remember_source
```

- [ ] **Step 4: Stop precompact writing the handoff**

In `precompact.py`'s `main()`, call `mirror_handoff` only when invoked with `--sync-only`. Without the flag the hook drains stdin and returns 0. A session that compacts three times used to rewrite `_handoff.md` three times, plus once more at session end.

Record the tradeoff in the docstring: a session that dies before SessionEnd leaves the previous handoff in place, and its own STALE flag surfaces that.

- [ ] **Step 5: Report the probe in check**

In `check.py`, beside the existing `_suitcase_status()` call, add `remember_status(project_root)` to the report payload under key `remember`, and render a line when `present` is false or `empty` is true:

```
remember: not detected — the handoff is written from session context only
remember: present but empty — the handoff carries no mirrored body
```

- [ ] **Step 6: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_handoff_freshness test_precompact test_check test_sync -v 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 7: Run the full suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 8: Commit**

```bash
git add adjudant/scripts/_handoff_freshness.py adjudant/scripts/sync.py adjudant/scripts/check.py adjudant/hooks/scripts/precompact.py adjudant/scripts/test_handoff_freshness.py adjudant/scripts/test_check.py
git commit -m "fix(adjudant): handoff written once, and the remember dependency declared

_handoff.md was clobbered at every compaction and again at session end. The
source picker existed twice and had drifted. And when remember was absent or
empty adjudant wrote an empty handoff and said nothing: 7 of 12 handoffs in
the real vault are a banner with no body.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: The no-crud acceptance test

The plan's headline claim, asserted rather than believed.

**Files:**
- Create: `adjudant/scripts/test_no_crud.py`

**Interfaces:**
- Consumes: every change in Tasks 3 through 9.
- Produces: nothing. This is the gate.

- [ ] **Step 1: Write the test**

Create `adjudant/scripts/test_no_crud.py`:

```python
"""Acceptance test for adjudant v3 plan 1: a working session leaves no crud.

Before this plan, one ordinary session produced eight unrequested vault files,
eleven whole-file rewrites and fourteen log lines against six intentional
writes — better than three to one, machine to human. This test fails if any of
that comes back.
"""

import json
import os
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent


class TestSessionLeavesNoCrud(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.home = tmp / "home"
        self.project = tmp / "code"
        self.vault = self.home / "vault"
        self.vp = self.vault / "projects" / "demo"
        (self.vp / "notes").mkdir(parents=True)
        (self.project / ".claude").mkdir(parents=True)
        (self.project / ".claude" / "adjudant").write_text(
            f"vault_path: {self.vault}\nvault_name: vault\nslug: demo\nmode: project\n")
        self._ob = os.environ.pop("OB_VAULT", None)

    def tearDown(self):
        if self._ob is not None:
            os.environ["OB_VAULT"] = self._ob
        self._tmp.cleanup()

    def _env(self):
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(self.project)
        env["HOME"] = str(self.home)
        env["TMPDIR"] = str(self.home / "tmp")
        env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
        env.pop("OB_VAULT", None)
        (self.home / "tmp").mkdir(exist_ok=True)
        return env

    def _hook(self, script: str, payload: dict):
        runner = ["bash"] if script.endswith(".sh") else ["python3"]
        subprocess.run(runner + [str(HOOKS / script)], env=self._env(),
                       input=json.dumps(payload), capture_output=True,
                       text=True, timeout=20)

    def test_one_session_writes_only_what_was_asked_for(self):
        sid = "s-accept-1"
        # Session opens, twice (a resume), then compacts once.
        self._hook("session-start.sh", {"session_id": sid, "source": "startup"})
        self._hook("session-start.sh", {"session_id": sid, "source": "resume"})

        # Six intentional writes.
        written = []
        for i in range(6):
            note = self.vp / "notes" / f"n{i}.md"
            note.write_text(
                f"---\ntype: note\ncreated: 2026-09-01\nupdated: 2026-09-01\n---\n\n# N{i}\n")
            written.append(note)
            self._hook("posttooluse-vault-log.py", {
                "tool_name": "Write",
                "tool_input": {"file_path": str(note)},
                "session_id": sid,
            })

        self._hook("precompact.py", {"session_id": sid})
        self._hook("postcompact.py", {"session_id": sid, "summary": "did things"})
        self._hook("sessionend.sh", {"session_id": sid})

        today = date.today().isoformat()
        session_note = self.vp / "sessions" / f"{today}.md"

        # Exactly one file exists that nobody explicitly asked for: the session
        # note, and only because six real writes happened.
        allowed = set(written) | {session_note, self.vp / "_handoff.md"}
        actual = {p for p in self.vp.rglob("*") if p.is_file()}
        extra = actual - allowed
        self.assertEqual(extra, set(), f"unrequested vault files: {sorted(extra)}")

        # The session note holds one line per real write and no lifecycle noise.
        log = session_note.read_text()
        for marker in ("session started", "session resumed", "session ended",
                       "paused (compaction)", "compacted:"):
            self.assertNotIn(marker, log, f"lifecycle marker survived: {marker}")
        self.assertEqual(log.count("· Added:"), 6)

        # No scratch anywhere in the vault.
        self.assertEqual(list(self.vault.rglob(".adjudant-*")), [])

    def test_a_session_with_no_writes_leaves_nothing(self):
        sid = "s-accept-2"
        self._hook("session-start.sh", {"session_id": sid, "source": "startup"})
        self._hook("sessionend.sh", {"session_id": sid})
        self.assertFalse((self.vp / "sessions").exists(),
                         "a session that did nothing still created a note")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it**

Run: `cd adjudant/scripts && python3 -m unittest test_no_crud -v`
Expected: PASS, 2 tests. A failure here names the exact file that leaked; fix the responsible hook rather than relaxing the assertion.

- [ ] **Step 3: Run the full suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 4: Update the test count in the README**

`adjudant/README.md:66` states the test count. Update it to the new total from the suite output.

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/test_no_crud.py adjudant/README.md
git commit -m "test(adjudant): acceptance test - a working session leaves no crud

Six intentional writes, one resume, one compaction. Asserts exactly one
unrequested file (the session note, earned by real work), no lifecycle
markers, and no scratch anywhere in the vault. Baseline before this plan was
eight unrequested files.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: The drift canary

Every other check in this repo asks whether a file is still true. This one asks whether the agent is, which is the failure that produces untrue files.

**Files:**
- Create: `adjudant/hooks/scripts/stop-canary.py`, `adjudant/scripts/test_canary.py`
- Modify: `adjudant/hooks/hooks.json` (new `Stop` entry), `adjudant/hooks/scripts/session-start.sh` (state it once), `adjudant/hooks/scripts/user-prompt-reminder.sh` (report a lapse)

**Interfaces:**
- Consumes: nothing from earlier tasks. Task 6 also edits `session-start.sh`, so run this task after Task 6 and edit the result rather than the original.
- Produces:
  - `canary_path(session_id: str) -> str` — `$TMPDIR/adjudant-canary-{session_id}.json`, same shape and same filename guard as `task-ledger.py:39`.
  - The state file: `{"word": str, "turns": int, "hits": int, "misses": int, "blocked": bool}`.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_canary.py`:

```python
"""Tests for the drift canary.

A codeword is stated once at session start and printed at the end of every
reply. When it stops appearing, the model has stopped honouring an instruction
it was given minutes ago, and nothing else in the session is trustworthy.

The rule the design rests on is that the word is NEVER restated. A per-turn
re-assertion would keep the model printing it and the canary would measure
nothing.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"


def _run(payload: dict, home: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["TMPDIR"] = str(home)
    env.pop("OB_VAULT", None)
    return subprocess.run(
        ["python3", str(HOOKS / "stop-canary.py")],
        env=env, input=json.dumps(payload),
        capture_output=True, text=True, timeout=15)


class TestCanary(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _state(self, sid: str, **fields) -> Path:
        p = self.home / f"adjudant-canary-{sid}.json"
        base = {"word": "GRAMERCY", "turns": 0, "hits": 0,
                "misses": 0, "blocked": False}
        base.update(fields)
        p.write_text(json.dumps(base))
        return p

    def test_word_present_records_a_hit(self):
        p = self._state("s1")
        r = _run({"session_id": "s1",
                  "last_assistant_message": "Did the thing.\n\nGRAMERCY"}, self.home)
        self.assertEqual(r.returncode, 0)
        st = json.loads(p.read_text())
        self.assertEqual(st["hits"], 1)
        self.assertEqual(st["misses"], 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_first_miss_blocks(self):
        p = self._state("s2")
        r = _run({"session_id": "s2",
                  "last_assistant_message": "Did the thing."}, self.home)
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertIn("GRAMERCY", out["reason"])
        st = json.loads(p.read_text())
        self.assertEqual(st["misses"], 1)
        self.assertTrue(st["blocked"])

    def test_the_miss_survives_a_successful_block(self):
        # The signal must survive coercion. If a block makes the retry succeed
        # and the miss were then forgotten, the counter would read clean
        # through exactly the degradation it exists to catch.
        p = self._state("s3")
        _run({"session_id": "s3", "last_assistant_message": "no word"}, self.home)
        _run({"session_id": "s3", "last_assistant_message": "ok GRAMERCY"}, self.home)
        st = json.loads(p.read_text())
        self.assertEqual(st["misses"], 1)
        self.assertEqual(st["hits"], 1)

    def test_second_miss_reports_and_does_not_block(self):
        p = self._state("s4", blocked=True, misses=1)
        r = _run({"session_id": "s4", "last_assistant_message": "still no word"},
                 self.home)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")
        st = json.loads(p.read_text())
        self.assertEqual(st["misses"], 2)

    def test_the_word_must_be_near_the_end(self):
        # Quoting the instruction mid-message is not compliance.
        self._state("s5")
        r = _run({"session_id": "s5",
                  "last_assistant_message":
                      "I was told to end with GRAMERCY.\n\n" + ("filler line\n" * 40)},
                 self.home)
        self.assertEqual(json.loads(r.stdout)["decision"], "block")

    def test_no_state_file_is_a_noop(self):
        r = _run({"session_id": "unknown", "last_assistant_message": "hi"}, self.home)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_hostile_session_id_writes_nothing(self):
        r = _run({"session_id": "../escape", "last_assistant_message": "hi"}, self.home)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(list(self.home.glob("**/*escape*")), [])

    def test_malformed_stdin_exits_zero(self):
        env = dict(os.environ)
        env["TMPDIR"] = str(self.home)
        r = subprocess.run(["python3", str(HOOKS / "stop-canary.py")],
                           env=env, input="not json",
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0)


class TestTheWordIsStatedOnce(unittest.TestCase):

    def test_the_per_turn_hook_never_names_the_word(self):
        # The rule the whole design rests on. A re-assertion keeps the model
        # printing the word and the canary measures nothing.
        src = (HOOKS / "user-prompt-reminder.sh").read_text()
        self.assertNotIn("CANARY_WORDS", src)
        self.assertNotIn("canary word", src.lower())

    def test_session_start_emits_the_word_once(self):
        src = (HOOKS / "session-start.sh").read_text()
        self.assertEqual(src.count('"$canary_word"'), 1,
                         "the word reaches the context block more than once")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_canary -v`
Expected: FAIL — `stop-canary.py` does not exist.

- [ ] **Step 3: Write the hook**

Create `adjudant/hooks/scripts/stop-canary.py`:

```python
#!/usr/bin/env python3
"""Drift canary - has the model stopped following its standing instructions?

SessionStart states one rule: end every message with a codeword. This hook
reads `last_assistant_message` on Stop and records whether it did.

The value is that the rule is trivial. A model that stops honouring a one-word
instruction it was given minutes ago has stopped honouring instructions
generally, and everything else it says this session is worth less. That is the
moment to start fresh, and nothing else tells you it has arrived.

Block once, then report. The first miss blocks and asks the model to re-read
its instructions; every later miss is only recorded, because coercing
compliance past that point manufactures the appearance of health. The miss is
counted either way: if a block makes the retry succeed and the miss were
forgotten, the counter would read clean through the degradation it exists to
catch.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile

# The session_id becomes a filename component: only filename-safe ids may
# steer the path (mirrors task-ledger.py:35).
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# How much of the tail counts as "the end". A word quoted mid-message is not
# compliance: the instruction says to end with it.
_TAIL_CHARS = 240


def canary_path(session_id: str) -> str:
    root = os.environ.get("TMPDIR") or tempfile.gettempdir()
    return os.path.join(root, f"adjudant-canary-{session_id}.json")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    sid = str(payload.get("session_id") or "")
    if not sid or not _SESSION_ID_RE.match(sid):
        return 0

    path = canary_path(sid)
    try:
        with open(path) as f:
            state = json.load(f)
    except Exception:
        return 0                       # no canary for this session: nothing to do
    if not isinstance(state, dict) or not state.get("word"):
        return 0

    word = str(state["word"])
    message = str(payload.get("last_assistant_message") or "")
    present = word in message[-_TAIL_CHARS:]

    state["turns"] = int(state.get("turns", 0)) + 1
    if present:
        state["hits"] = int(state.get("hits", 0)) + 1
    else:
        state["misses"] = int(state.get("misses", 0)) + 1

    should_block = (not present) and not state.get("blocked")
    if should_block:
        state["blocked"] = True

    try:
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f)
        os.replace(tmp, path)
    except OSError:
        pass                           # a full TMPDIR must not surface as a failure

    if should_block:
        print(json.dumps({
            "decision": "block",
            "reason": (f"The session canary {word} was missing from that reply. "
                       "Re-read your standing instructions and end every message "
                       f"with {word} on its own line. This is said once: a later "
                       "lapse is recorded, not corrected."),
        }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                  # pragma: no cover - last-resort guard
        sys.exit(0)
```

- [ ] **Step 4: Run the hook tests**

Run: `cd adjudant/scripts && python3 -m unittest test_canary.TestCanary -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Pick the word and state it once, at session start**

In `adjudant/hooks/scripts/session-start.sh`, add beside the other helper functions:

```bash
# Rare nouns that do not occur in technical prose. ELLIPSIS and its kind are
# excluded deliberately: a word that can appear naturally would mask a real
# lapse, which is the one thing this must never do.
CANARY_WORDS="GRAMERCY QUINCUNX SPANDREL COLOPHON TREBUCHET PALIMPSEST ORRERY CLEPSYDRA CARTOUCHE SCRIPTORIUM INCUNABULA MARGINALIA PORTCULLIS BARBICAN ASTROLABE THEODOLITE VELLUM FIRKIN GAMBREL SALTIRE ZEUGMA MANTICORE"

canary_start() {
  local session_id="$1" tmp="${TMPDIR:-/tmp}"
  [ -n "$session_id" ] || return 0
  case "$session_id" in *[!A-Za-z0-9._-]*) return 0 ;; esac
  local state="$tmp/adjudant-canary-${session_id}.json"
  # One word per session. A resume or a compaction must not re-roll it, or the
  # streak resets exactly when drift is most likely.
  if [ -f "$state" ]; then
    python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["word"])' "$state" 2>/dev/null || true
    return 0
  fi
  # Chosen from the session id, so a resume picks the same word without
  # needing to have stored it first.
  local n word idx
  set -- $CANARY_WORDS
  idx=$(printf '%s' "$session_id" | cksum | cut -d' ' -f1)
  n=$(( idx % $# + 1 ))
  eval "word=\${$n}"
  printf '{"word":"%s","turns":0,"hits":0,"misses":0,"blocked":false}\n' "$word" > "$state" 2>/dev/null || return 0
  find "$tmp" -maxdepth 1 -name 'adjudant-canary-*.json' -mtime +1 -delete 2>/dev/null || true
  printf '%s' "$word"
}
```

In `main`, after the voice directive and before the vault lines, emit the rule exactly once:

```bash
  canary_word=$(canary_start "$session_id")
  if [ -n "$canary_word" ]; then
    printf -- '- Session canary: end every message with `%s` on its own line. It is a drift check, so do not explain it or mention it otherwise.\n' "$canary_word"
  fi
```

- [ ] **Step 6: Report a lapse in the per-turn hook, and never restate the word**

In `adjudant/hooks/scripts/user-prompt-reminder.sh`, add a function that reads the state file and prints only when a miss has occurred. **It must not print the word.** Naming it here would restate the instruction and the canary would stop measuring anything, which is what `TestTheWordIsStatedOnce` asserts.

Write it with a quoted heredoc delimiter that does not collide with any other in the file:

```bash
canary_report() {
  local session_id="$1" tmp="${TMPDIR:-/tmp}"
  [ -n "$session_id" ] || return 0
  case "$session_id" in *[!A-Za-z0-9._-]*) return 0 ;; esac
  local state="$tmp/adjudant-canary-${session_id}.json"
  [ -f "$state" ] || return 0
  python3 - "$state" <<'CANARY_PY' 2>/dev/null || true
import json, sys
try:
    s = json.load(open(sys.argv[1]))
except Exception:
    raise SystemExit(0)
misses, turns = int(s.get("misses", 0)), int(s.get("turns", 0))
if misses:
    print(f"[adjudant] Session canary missed {misses} of {turns} turns. "
          "Standing instructions are lapsing: wrap up, then start a fresh "
          "session rather than pushing this one further.")
CANARY_PY
}
```

Call it from `main` on every turn, before the existing intent nudge. It is silent while healthy, which is the rule the statusline applies to its own segments: a signal that never varies carries no information.

- [ ] **Step 7: Register the Stop hook**

In `adjudant/hooks/hooks.json`, add beside the existing entries:

```json
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/stop-canary.py\"",
        "timeout": 5
      }]
    }]
```

Validator 27 (`hooks-wiring`) checks that every command resolves to an existing file under `hooks/scripts/`, so a typo fails the build.

- [ ] **Step 8: Run the suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest test_canary -v`
Expected: `OK`, 10 tests

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 9: Commit**

```bash
git add adjudant/hooks/scripts/stop-canary.py adjudant/hooks/hooks.json adjudant/hooks/scripts/session-start.sh adjudant/hooks/scripts/user-prompt-reminder.sh adjudant/scripts/test_canary.py
git commit -m "feat(adjudant): drift canary, a check on the agent rather than the files

A codeword stated once at session start and printed at the end of every reply.
The Stop hook reads last_assistant_message and records a hit or a miss. When it
lapses, the model has stopped honouring a one-word instruction it was given
minutes ago, and nothing else it says this session is worth as much.

Block once, then report: coercing compliance past the first miss manufactures
the appearance of health. The miss is recorded either way, so a block that
works cannot erase the evidence.

The word is stated exactly once. A per-turn re-assertion would keep the model
printing it and the canary would measure nothing, which is why the tests assert
the per-turn hook never names it.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Done when

- `python3 -m unittest discover -p 'test_*.py'` from `adjudant/scripts/` reports `OK`.
- `python3 adjudant/scripts/validate.py` reports `PASS`.
- `test_no_crud.py` passes both tests.
- No file under a vault project matches `.adjudant-*` after a tidy preview and apply.
- The statusline renders with no stderr output against a fixture breadcrumb.
- `suggest_vault_roots` exists in `adjudant/scripts/_vault_walk.py` and `connect.py --suggest-vaults` prints JSON.
- The `Stop` hook is registered, `test_canary.py` passes, and the per-turn hook never names the codeword.

## Not in this plan

Templates, the schema, the verb surface, lifecycle folders, link form, the truth checks, and twin generation are plans 2 through 5. The one forward-looking change here is the session log's link form, which drops the `projects/` prefix in Task 6 because that writer was already being edited.
