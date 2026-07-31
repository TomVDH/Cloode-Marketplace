# Adjudant repo-target Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend adjudant's `check` / `tidy` / `ramasse` verbs with a `[vault|repo|all]` target so they clean the code repo as well as the vault, via three new repo-side helper modules that mirror the existing vault modules.

**Architecture:** Three new stdlib-only Python helpers in `adjudant/scripts/` mirror the vault trio one-for-one — `repo_walk.py` (primitives, ← `_vault_walk.py`), `repo_scan.py` (drift detectors + `drift_items`, ← `ramasse_scan.py`), `repo_tidy.py` (two-phase preview→apply, ← `tidy.py`). Detection is layered: a general core (context-file presence, stale plans) plus a marketplace layer that auto-activates when `.claude-plugin/marketplace.json` is present (version coherence, symlink integrity, registration). The verbs dispatch by reading their reference docs; no Python router is needed. Version bumps to 0.6.0 across the four version-bearing files keep the existing `version-consistency` validator green.

**Tech Stack:** Python 3 stdlib only (`argparse`, `json`, `re`, `pathlib`, `dataclasses`, `datetime`, `shutil`, `os`, `hashlib`), `unittest` for tests. No third-party deps. Markdown reference docs. Pre-commit runs `adjudant/scripts/validate.py`.

**Repo conventions baked in:**
- Commits go directly to `main` (this repo does not use PRs — see `AGENTS.md`).
- Every commit message ends with the trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` (omitted from the per-task snippets below for brevity).
- Run all adjudant tests with: `python3 -m unittest discover -s adjudant/scripts -p 'test_*.py'`
- Run validators with: `python3 adjudant/scripts/validate.py`
- **Version bump ordering:** `validate.py`'s `version-consistency` check (#10) requires `plugin.json` / `command-metadata.json` / `SKILL.md` / `marketplace.json` to all carry the same adjudant version. Because pre-commit runs `validate.py` on every commit, the four version edits MUST land in a single commit (Task 7). Tasks 1–6 leave all four at `0.5.2` (consistent), so their commits pass.

---

## File structure

| File | New/Modify | Responsibility |
|---|---|---|
| `adjudant/scripts/repo_walk.py` | Create | Repo-side primitives: repo-root + marketplace detection, plugin discovery, symlink-integrity status, context-file status, plan-file ages. Read-only. |
| `adjudant/scripts/repo_scan.py` | Create | Drift detectors + `run_scan()` → JSON with cardinality `drift_items`. Feeds `check repo` + `ramasse repo` analysis. Read-only. |
| `adjudant/scripts/repo_tidy.py` | Create | Two-phase `detect`/`preview`/`apply` for the two safe fixes (version sync, symlink repair). |
| `adjudant/scripts/test_repo_walk.py` | Create | Unit tests for `repo_walk`. |
| `adjudant/scripts/test_repo_scan.py` | Create | Unit tests for `repo_scan`. |
| `adjudant/scripts/test_repo_tidy.py` | Create | Unit tests for `repo_tidy` (preview→apply, idempotency, symlink repair). |
| `adjudant/skills/adjudant/reference/repo-standards.md` | Create | Single source of truth for repo conventions (the detector categories). |
| `adjudant/skills/adjudant/reference/check.md` | Modify | Add `[target]` dimension + `check repo` render section. |
| `adjudant/skills/adjudant/reference/tidy.md` | Modify | Add `[target]` dimension + `tidy repo` run section. |
| `adjudant/skills/adjudant/reference/ramasse.md` | Modify | Add `[target]` dimension + `ramasse repo` chain section. |
| `adjudant/scripts/command-metadata.json` | Modify | `argumentHint` → `[vault\|repo\|all]` for check/tidy/ramasse; version → 0.6.0. |
| `adjudant/skills/adjudant/SKILL.md` | Modify | Router target notes, three-tier targets block, helper table rows, repo-standards pointer; version → 0.6.0. |
| `adjudant/.claude-plugin/plugin.json` | Modify | version → 0.6.0; description note. |
| `.claude-plugin/marketplace.json` | Modify | adjudant entry version → 0.6.0 (gemineye drift left as the Task 9 dogfood). |
| `adjudant/scripts/validate.py` | Modify | Add 5 validators (repo-helper-parity, repo-standards-coverage, repo-tidy preview/backup/gitignore). |
| `.gitignore` | Modify | Add `.adjudant-repo-tidy-preview/` + `.adjudant-repo-tidy-backup/`. |

---

## Task 1: `repo_walk.py` — repo-side primitives

**Files:**
- Create: `adjudant/scripts/repo_walk.py`
- Test: `adjudant/scripts/test_repo_walk.py`

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_repo_walk.py`:

```python
#!/usr/bin/env python3
"""Tests for repo_walk primitives."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_walk as rw


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _make_plugin(root: Path, name: str, version: str, *, adopt: bool = False) -> Path:
    """Create a minimal plugin dir; if adopt=True, lay down the Impeccable
    canonical skills/ dir + the three harness symlinks."""
    pdir = root / name
    _write(pdir / ".claude-plugin" / "plugin.json",
           '{\n  "name": "%s",\n  "version": "%s"\n}\n' % (name, version))
    if adopt:
        canonical = pdir / "skills" / name
        _write(canonical / "SKILL.md", "---\nname: %s\n---\n# %s\n" % (name, name))
        for harness in rw.HARNESS_SUBPATHS:
            link_parent = pdir / harness / "skills"
            link_parent.mkdir(parents=True, exist_ok=True)
            os.symlink("../../skills/" + name, link_parent / name)
    return pdir


def _make_repo(tmp: Path) -> Path:
    """A fake marketplace repo: manifest + two plugins, one adopting."""
    (tmp / ".git").mkdir()
    _write(tmp / ".claude-plugin" / "marketplace.json",
           '{\n  "name": "mk",\n  "version": "1.0.0",\n  "plugins": [\n'
           '    {"name": "alpha", "version": "0.6.0", "source": "./alpha"},\n'
           '    {"name": "beta", "version": "0.3.1", "source": "./beta"}\n'
           '  ]\n}\n')
    _make_plugin(tmp, "alpha", "0.6.0", adopt=True)
    _make_plugin(tmp, "beta", "0.3.2", adopt=False)
    return tmp


class TestRepoRoot(unittest.TestCase):
    def test_find_repo_root_via_marketplace(self):
        with tempfile.TemporaryDirectory() as d:
            root = _make_repo(Path(d))
            nested = root / "alpha" / "skills"
            self.assertEqual(rw.find_repo_root(nested), root.resolve())

    def test_is_marketplace_repo(self):
        with tempfile.TemporaryDirectory() as d:
            root = _make_repo(Path(d))
            self.assertTrue(rw.is_marketplace_repo(root))
            self.assertFalse(rw.is_marketplace_repo(root / "alpha"))


class TestPlugins(unittest.TestCase):
    def test_walk_plugins_discovers_both(self):
        with tempfile.TemporaryDirectory() as d:
            root = _make_repo(Path(d))
            names = [p.name for p in rw.walk_plugins(root)]
            self.assertEqual(names, ["alpha", "beta"])

    def test_versions_and_adoption(self):
        with tempfile.TemporaryDirectory() as d:
            root = _make_repo(Path(d))
            by = {p.name: p for p in rw.walk_plugins(root)}
            self.assertEqual(by["alpha"].version, "0.6.0")
            self.assertTrue(by["alpha"].adopts_impeccable)
            self.assertEqual(by["beta"].version, "0.3.2")
            self.assertFalse(by["beta"].adopts_impeccable)


class TestSymlinks(unittest.TestCase):
    def test_status_ok_when_links_intact(self):
        with tempfile.TemporaryDirectory() as d:
            root = _make_repo(Path(d))
            alpha = {p.name: p for p in rw.walk_plugins(root)}["alpha"]
            statuses = rw.plugin_symlink_status(alpha)
            self.assertEqual(len(statuses), len(rw.HARNESS_SUBPATHS))
            self.assertTrue(all(s.ok for s in statuses))

    def test_status_empty_for_non_adopter(self):
        with tempfile.TemporaryDirectory() as d:
            root = _make_repo(Path(d))
            beta = {p.name: p for p in rw.walk_plugins(root)}["beta"]
            self.assertEqual(rw.plugin_symlink_status(beta), [])

    def test_status_flags_broken_link(self):
        with tempfile.TemporaryDirectory() as d:
            root = _make_repo(Path(d))
            # Remove one harness link to simulate breakage
            (root / "alpha" / ".claude" / "skills" / "alpha").unlink()
            alpha = {p.name: p for p in rw.walk_plugins(root)}["alpha"]
            statuses = rw.plugin_symlink_status(alpha)
            broken = [s for s in statuses if not s.ok]
            self.assertEqual(len(broken), 1)
            self.assertFalse(broken[0].is_symlink)


class TestContextFiles(unittest.TestCase):
    def test_imports_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _write(root / "AGENTS.md", "# A\n")
            _write(root / "CLAUDE.md", "@AGENTS.md\n\n# overrides\n")
            st = rw.context_files_status(root, root)
            self.assertTrue(st.has_agents)
            self.assertTrue(st.has_claude)
            self.assertTrue(st.claude_imports_agents)
            self.assertEqual(st.directory, ".")

    def test_missing_and_non_importing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sub = root / "p"
            _write(sub / "CLAUDE.md", "# no import\n")
            st = rw.context_files_status(sub, root)
            self.assertFalse(st.has_agents)
            self.assertTrue(st.has_claude)
            self.assertFalse(st.claude_imports_agents)
            self.assertEqual(st.directory, "p")


class TestPlanAges(unittest.TestCase):
    def test_age_and_marker(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _write(root / "docs" / "superpowers" / "2026-04-01-old.plan.md", "# old\nwork\n")
            _write(root / "docs" / "superpowers" / "2026-05-01-done.plan.md", "# done\nstatus: complete\n")
            plans = {pf.path.split("/")[-1]: pf for pf in rw.plan_file_ages(root, "2026-06-07")}
            self.assertEqual(plans["2026-04-01-old.plan.md"].age_days, 67)
            self.assertFalse(plans["2026-04-01-old.plan.md"].has_completion_marker)
            self.assertTrue(plans["2026-05-01-done.plan.md"].has_completion_marker)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest adjudant.scripts.test_repo_walk -v` (or `cd adjudant/scripts && python3 -m unittest test_repo_walk -v`)
Expected: FAIL — `ModuleNotFoundError: No module named 'repo_walk'`

- [ ] **Step 3: Write the module**

Create `adjudant/scripts/repo_walk.py`:

```python
#!/usr/bin/env python3
"""Adjudant repo-walk primitives — repo-side structural inspection.

Mirror of _vault_walk.py for the CODE repo (not the vault). Stdlib-only,
read-only. Consumed by repo_scan.py (check/ramasse repo analysis) and
repo_tidy.py (tidy repo apply).

Public API:
    find_repo_root(start) -> Path
    is_marketplace_repo(repo_root) -> bool
    parse_json_file(path) -> Optional[dict]
    walk_plugins(repo_root) -> list[PluginDir]
    read_marketplace(repo_root) -> Optional[Marketplace]
    plugin_symlink_status(plugin) -> list[SymlinkStatus]
    context_files_status(directory, repo_root) -> ContextStatus
    plan_file_ages(repo_root, today) -> list[PlanFile]

Schema constants:
    HARNESS_SUBPATHS, CONTEXT_FILES, STALE_PLAN_DAYS

CLI smoke-test (read-only):
    python3 repo_walk.py --repo-dir PATH [--today YYYY-MM-DD] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional


HARNESS_SUBPATHS: tuple[str, ...] = ("source", ".claude", ".gemini")
CONTEXT_FILES: tuple[str, ...] = ("AGENTS.md", "CLAUDE.md")
STALE_PLAN_DAYS: int = 30

_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMPLETION_MARKER_RE = re.compile(
    r"(?im)^\s*(?:status\s*:\s*(?:complete|done|shipped|archived|superseded)\b"
    r"|>\s*(?:complete|done|shipped)\b|✅)"
)


# ============================================================
# Dataclasses
# ============================================================


@dataclass
class PluginDir:
    name: str
    path: Path
    plugin_json: Optional[dict]
    version: Optional[str]
    has_skills: bool
    adopts_impeccable: bool


@dataclass
class Marketplace:
    path: Path
    version: str
    plugins: list[dict] = field(default_factory=list)


@dataclass
class SymlinkStatus:
    link: Path            # relative to repo root
    expected_target: str  # relative symlink string, e.g. ../../skills/adjudant
    is_symlink: bool
    resolves_to_canonical: bool

    @property
    def ok(self) -> bool:
        return self.is_symlink and self.resolves_to_canonical


@dataclass
class ContextStatus:
    directory: str        # relative to repo root ('.' for root)
    has_agents: bool
    has_claude: bool
    claude_imports_agents: bool


@dataclass
class PlanFile:
    path: str             # relative to repo root
    date: Optional[str]
    age_days: Optional[int]
    has_completion_marker: bool


# ============================================================
# Repo root + JSON
# ============================================================


def find_repo_root(start: Path) -> Path:
    """Walk up from `start` to the dir holding `.git` or a marketplace manifest.
    Falls back to `start` resolved."""
    cur = start.expanduser().resolve()
    while cur != cur.parent:
        if (cur / ".git").exists() or (cur / ".claude-plugin" / "marketplace.json").is_file():
            return cur
        cur = cur.parent
    return start.expanduser().resolve()


def is_marketplace_repo(repo_root: Path) -> bool:
    return (repo_root / ".claude-plugin" / "marketplace.json").is_file()


def parse_json_file(path: Path) -> Optional[dict]:
    """Read + parse a JSON file. None on missing/unreadable/invalid/non-object."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


# ============================================================
# Plugin discovery
# ============================================================


def walk_plugins(repo_root: Path) -> list[PluginDir]:
    """Every immediate child dir of repo_root carrying
    .claude-plugin/plugin.json, sorted by name."""
    out: list[PluginDir] = []
    for entry in sorted(repo_root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        manifest = entry / ".claude-plugin" / "plugin.json"
        if not manifest.is_file():
            continue
        data = parse_json_file(manifest)
        version = data.get("version") if isinstance(data, dict) else None
        has_skills = (entry / "skills").is_dir()
        adopts = has_skills and any(
            (entry / h / "skills").exists() for h in HARNESS_SUBPATHS
        )
        out.append(PluginDir(
            name=entry.name,
            path=entry,
            plugin_json=data,
            version=version if isinstance(version, str) else None,
            has_skills=has_skills,
            adopts_impeccable=adopts,
        ))
    return out


def read_marketplace(repo_root: Path) -> Optional[Marketplace]:
    data = parse_json_file(repo_root / ".claude-plugin" / "marketplace.json")
    if data is None:
        return None
    plugins = data.get("plugins", [])
    return Marketplace(
        path=repo_root / ".claude-plugin" / "marketplace.json",
        version=str(data.get("version", "")),
        plugins=[p for p in plugins if isinstance(p, dict)],
    )


# ============================================================
# Symlink integrity (Impeccable pattern)
# ============================================================


def _canonical_skill_dirs(plugin: PluginDir) -> list[str]:
    """Names of real (non-symlink) skill dirs under <plugin>/skills/."""
    skills_root = plugin.path / "skills"
    if not skills_root.is_dir():
        return []
    return sorted(
        d.name for d in skills_root.iterdir()
        if d.is_dir() and not d.is_symlink()
    )


def plugin_symlink_status(plugin: PluginDir) -> list[SymlinkStatus]:
    """For a plugin that ADOPTS the Impeccable pattern, return the expected
    harness symlink status for each (harness × canonical skill). Empty list
    when the plugin does not adopt the pattern — that is a ramasse-tier
    migration, not a symlink-integrity defect."""
    if not plugin.adopts_impeccable:
        return []
    out: list[SymlinkStatus] = []
    repo_root = plugin.path.parent
    for skill in _canonical_skill_dirs(plugin):
        canonical = (plugin.path / "skills" / skill).resolve()
        for harness in HARNESS_SUBPATHS:
            link = plugin.path / harness / "skills" / skill
            is_link = link.is_symlink()
            resolves = False
            if is_link:
                try:
                    resolves = link.resolve() == canonical
                except OSError:
                    resolves = False
            out.append(SymlinkStatus(
                link=link.relative_to(repo_root),
                expected_target="../../skills/" + skill,
                is_symlink=is_link,
                resolves_to_canonical=resolves,
            ))
    return out


# ============================================================
# Context files (AGENTS.md / CLAUDE.md)
# ============================================================


def context_files_status(directory: Path, repo_root: Path) -> ContextStatus:
    """Presence of AGENTS.md/CLAUDE.md in `directory`, and whether CLAUDE.md's
    first non-empty line is `@AGENTS.md`."""
    rel = "." if directory.resolve() == repo_root.resolve() else str(directory.resolve().relative_to(repo_root.resolve()))
    claude = directory / "CLAUDE.md"
    imports = False
    if claude.is_file():
        for line in claude.read_text(errors="replace").splitlines():
            if line.strip():
                imports = line.strip() == "@AGENTS.md"
                break
    return ContextStatus(
        directory=rel,
        has_agents=(directory / "AGENTS.md").is_file(),
        has_claude=claude.is_file(),
        claude_imports_agents=imports,
    )


# ============================================================
# Plan-file ages
# ============================================================


def plan_file_ages(repo_root: Path, today: str) -> list[PlanFile]:
    """Scan docs/superpowers/ recursively for `*.plan.md` files; return date,
    age in days vs `today` (YYYY-MM-DD), and completion-marker status each."""
    docs = repo_root / "docs" / "superpowers"
    if not docs.is_dir():
        return []
    try:
        today_d: Optional[date] = date.fromisoformat(today)
    except ValueError:
        today_d = None
    out: list[PlanFile] = []
    for f in sorted(docs.rglob("*.plan.md")):
        m = _DATE_PREFIX_RE.match(f.name)
        d_str = m.group(1) if m else None
        age: Optional[int] = None
        if d_str and today_d:
            try:
                age = (today_d - date.fromisoformat(d_str)).days
            except ValueError:
                age = None
        out.append(PlanFile(
            path=str(f.relative_to(repo_root)),
            date=d_str,
            age_days=age,
            has_completion_marker=bool(_COMPLETION_MARKER_RE.search(f.read_text(errors="replace"))),
        ))
    return out


# ============================================================
# CLI smoke-test (read-only)
# ============================================================


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repo_walk.py",
        description="Repo-walk primitives — read-only smoke test.",
    )
    parser.add_argument("--repo-dir", default=".")
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo_root = find_repo_root(Path(args.repo_dir))
    plugins = walk_plugins(repo_root)
    out: dict[str, Any] = {
        "repo_root": str(repo_root),
        "is_marketplace": is_marketplace_repo(repo_root),
        "plugins": [
            {"name": p.name, "version": p.version, "adopts_impeccable": p.adopts_impeccable}
            for p in plugins
        ],
        "plans": [vars(pf) for pf in plan_file_ages(repo_root, args.today)],
    }
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print(f"repo root:   {repo_root}")
        print(f"marketplace: {out['is_marketplace']}")
        print(f"plugins:     {len(plugins)}")
        for p in plugins:
            print(f"  - {p.name} {p.version} impeccable={p.adopts_impeccable}")
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd adjudant/scripts && python3 -m unittest test_repo_walk -v`
Expected: PASS (all tests OK)

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/repo_walk.py adjudant/scripts/test_repo_walk.py
git commit -m "feat(adjudant): repo_walk.py — repo-side primitives (plugins, symlinks, context files, plan ages)"
```

---

## Task 2: `repo_scan.py` — drift detectors

**Files:**
- Create: `adjudant/scripts/repo_scan.py`
- Test: `adjudant/scripts/test_repo_scan.py`
- Depends on: Task 1

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_repo_scan.py`:

```python
#!/usr/bin/env python3
"""Tests for repo_scan detectors."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_scan as rs
import repo_walk as rw


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _plugin(root: Path, name: str, version: str, *, adopt: bool = False) -> None:
    _write(root / name / ".claude-plugin" / "plugin.json",
           '{\n  "name": "%s",\n  "version": "%s"\n}\n' % (name, version))
    if adopt:
        _write(root / name / "skills" / name / "SKILL.md", "---\nname: %s\n---\n" % name)
        for harness in rw.HARNESS_SUBPATHS:
            lp = root / name / harness / "skills"
            lp.mkdir(parents=True, exist_ok=True)
            os.symlink("../../skills/" + name, lp / name)


def _repo(tmp: Path) -> Path:
    (tmp / ".git").mkdir()
    _write(tmp / ".claude-plugin" / "marketplace.json",
           '{\n  "name": "mk",\n  "version": "1.0.0",\n  "plugins": [\n'
           '    {"name": "alpha", "version": "0.6.0", "source": "./alpha"},\n'
           '    {"name": "beta", "version": "0.3.1", "source": "./beta"}\n'
           '  ]\n}\n')
    _write(tmp / "AGENTS.md", "# repo\n")
    _write(tmp / "CLAUDE.md", "@AGENTS.md\n")
    _plugin(tmp, "alpha", "0.6.0", adopt=True)
    _plugin(tmp, "beta", "0.3.2", adopt=False)   # version drift: mk 0.3.1 != plugin 0.3.2
    return tmp


class TestDetectors(unittest.TestCase):
    def test_version_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            mk = rw.read_marketplace(root)
            plugins = rw.walk_plugins(root)
            drift = rs.detect_version_drift(mk, plugins)
            self.assertEqual(drift, [{"plugin": "beta", "marketplace_version": "0.3.1", "plugin_version": "0.3.2"}])

    def test_symlink_drift_flags_broken_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            (root / "alpha" / ".gemini" / "skills" / "alpha").unlink()
            drift = rs.detect_symlink_drift(rw.walk_plugins(root))
            self.assertEqual(len(drift), 1)
            self.assertEqual(drift[0]["plugin"], "alpha")
            self.assertIn(".gemini", drift[0]["link"])

    def test_context_gaps_flags_plugins_not_root(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            gaps = rs.detect_context_gaps(root, rw.walk_plugins(root))
            dirs = {g["dir"] for g in gaps}
            self.assertNotIn(".", dirs)          # root has AGENTS+CLAUDE importing
            self.assertIn("alpha", dirs)
            self.assertIn("beta", dirs)

    def test_stale_plans(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            _write(root / "docs" / "superpowers" / "2026-01-01-ancient.plan.md", "# x\n")
            _write(root / "docs" / "superpowers" / "2026-06-01-fresh.plan.md", "# x\n")
            stale = rs.detect_stale_plans(root, "2026-06-07")
            files = {s["file"].split("/")[-1] for s in stale}
            self.assertIn("2026-01-01-ancient.plan.md", files)
            self.assertNotIn("2026-06-01-fresh.plan.md", files)

    def test_registration_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            _plugin(root, "gamma", "1.0.0")       # on disk, not registered
            mk = rw.read_marketplace(root)
            gaps = rs.detect_registration_gaps(root, mk, rw.walk_plugins(root))
            self.assertTrue(any(g.get("plugin") == "gamma" for g in gaps))


class TestRunScan(unittest.TestCase):
    def test_drift_items_is_sum_of_cardinalities(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            report = rs.run_scan(root, "2026-06-07")
            expected = (
                len(report["version_drift"])
                + len(report["symlink_drift"])
                + len(report["context_gaps"])
                + len(report["stale_plans"])
                + len(report["registration_gaps"])
            )
            self.assertEqual(report["summary"]["drift_items"], expected)
            self.assertTrue(report["meta"]["is_marketplace"])

    def test_non_marketplace_skips_marketplace_layer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            _plugin(root, "alpha", "0.6.0", adopt=True)
            report = rs.run_scan(root, "2026-06-07")
            self.assertEqual(report["version_drift"], [])
            self.assertEqual(report["registration_gaps"], [])
            self.assertFalse(report["meta"]["is_marketplace"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_repo_scan -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'repo_scan'`

- [ ] **Step 3: Write the module**

Create `adjudant/scripts/repo_scan.py`:

```python
#!/usr/bin/env python3
"""Adjudant repo_scan — repo-side structural drift catalog.

Mirror of ramasse_scan.py for the CODE repo. Scans a repo and emits a
structured drift catalog (JSON) for `/adjudant check repo` to render or
`/adjudant ramasse repo` to use as its analysis phase. Read-only.

Layered:
  - general core: context-file presence, stale plans
  - marketplace layer (auto-activates on marketplace.json): version drift,
    symlink integrity, registration coherence

CLI:
    python3 repo_scan.py --repo-dir PATH [--today YYYY-MM-DD] [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

from repo_walk import (
    STALE_PLAN_DAYS,
    Marketplace,
    PluginDir,
    context_files_status,
    find_repo_root,
    is_marketplace_repo,
    plan_file_ages,
    plugin_symlink_status,
    read_marketplace,
    walk_plugins,
)


# ============================================================
# Detectors
# ============================================================


def detect_version_drift(marketplace: Optional[Marketplace], plugins: list[PluginDir]) -> list[dict]:
    """marketplace.json plugin version != that plugin's own plugin.json version.
    Marketplace layer — empty when no manifest."""
    if marketplace is None:
        return []
    by_name = {p.name: p for p in plugins}
    out: list[dict] = []
    for entry in marketplace.plugins:
        name = entry.get("name")
        mk_version = entry.get("version")
        plugin = by_name.get(name)
        if plugin is None or plugin.version is None:
            continue
        if mk_version != plugin.version:
            out.append({
                "plugin": name,
                "marketplace_version": mk_version,
                "plugin_version": plugin.version,
            })
    return out


def detect_symlink_drift(plugins: list[PluginDir]) -> list[dict]:
    """Broken/missing harness symlinks in plugins that ADOPT the pattern."""
    out: list[dict] = []
    for p in plugins:
        for st in plugin_symlink_status(p):
            if not st.ok:
                out.append({
                    "plugin": p.name,
                    "link": str(st.link),
                    "expected_target": st.expected_target,
                    "issue": "missing symlink" if not st.is_symlink else "wrong target",
                })
    return out


def detect_context_gaps(repo_root: Path, plugins: list[PluginDir]) -> list[dict]:
    """Repo root + each plugin missing AGENTS.md/CLAUDE.md, or CLAUDE not
    importing @AGENTS.md. General core."""
    out: list[dict] = []
    for d in [repo_root] + [p.path for p in plugins]:
        st = context_files_status(d, repo_root)
        problems: list[str] = []
        if not st.has_agents:
            problems.append("missing AGENTS.md")
        if not st.has_claude:
            problems.append("missing CLAUDE.md")
        if st.has_claude and not st.claude_imports_agents:
            problems.append("CLAUDE.md does not import @AGENTS.md")
        if problems:
            out.append({"dir": st.directory, "problems": problems})
    return out


def detect_stale_plans(repo_root: Path, today: str) -> list[dict]:
    """Plan files older than STALE_PLAN_DAYS with no completion marker.
    General core."""
    out: list[dict] = []
    for pf in plan_file_ages(repo_root, today):
        if pf.has_completion_marker:
            continue
        if pf.age_days is not None and pf.age_days > STALE_PLAN_DAYS:
            out.append({"file": pf.path, "age_days": pf.age_days, "date": pf.date})
    return out


def detect_registration_gaps(repo_root: Path, marketplace: Optional[Marketplace], plugins: list[PluginDir]) -> list[dict]:
    """Plugins on disk not registered, and registered sources that don't exist.
    Marketplace layer."""
    if marketplace is None:
        return []
    out: list[dict] = []
    registered = {e.get("name") for e in marketplace.plugins}
    for p in plugins:
        if p.name not in registered:
            out.append({"issue": "unregistered plugin on disk", "plugin": p.name})
    for entry in marketplace.plugins:
        source = entry.get("source", "")
        if source and not (repo_root / source).resolve().is_dir():
            out.append({"issue": "registered source missing", "plugin": entry.get("name"), "source": source})
    return out


# ============================================================
# Top-level scan
# ============================================================


def run_scan(repo_root: Path, today: str) -> dict[str, Any]:
    plugins = walk_plugins(repo_root)
    marketplace = read_marketplace(repo_root)

    version_drift = detect_version_drift(marketplace, plugins)
    symlink_drift = detect_symlink_drift(plugins)
    context_gaps = detect_context_gaps(repo_root, plugins)
    stale_plans = detect_stale_plans(repo_root, today)
    registration_gaps = detect_registration_gaps(repo_root, marketplace, plugins)

    drift_items = (
        len(version_drift)
        + len(symlink_drift)
        + len(context_gaps)
        + len(stale_plans)
        + len(registration_gaps)
    )

    return {
        "meta": {
            "repo_root": str(repo_root),
            "is_marketplace": is_marketplace_repo(repo_root),
            "plugins_scanned": len(plugins),
            "today": today,
        },
        "summary": {"drift_items": drift_items},
        "version_drift": version_drift,
        "symlink_drift": symlink_drift,
        "context_gaps": context_gaps,
        "stale_plans": stale_plans,
        "registration_gaps": registration_gaps,
    }


# ============================================================
# CLI
# ============================================================


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repo_scan.py",
        description="Adjudant repo_scan — repo drift catalog (read-only).",
    )
    parser.add_argument("--repo-dir", default=".")
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    repo_root = find_repo_root(Path(args.repo_dir))
    if not repo_root.is_dir():
        print(f"error: repo-dir not found: {repo_root}", file=sys.stderr)
        return 1

    report = run_scan(repo_root, args.today)
    payload = json.dumps(report, indent=2, default=str)
    if args.out:
        Path(args.out).expanduser().write_text(payload + "\n")
        print(f"[repo_scan] wrote {args.out}", file=sys.stderr)
    else:
        print(payload)
    print(
        f"[repo_scan] {repo_root.name}: {report['meta']['plugins_scanned']} plugins, "
        f"{report['summary']['drift_items']} drift items",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd adjudant/scripts && python3 -m unittest test_repo_scan -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/repo_scan.py adjudant/scripts/test_repo_scan.py
git commit -m "feat(adjudant): repo_scan.py — layered repo drift detectors + drift_items"
```

---

## Task 3: `repo_tidy.py` — two-phase safe fixes

**Files:**
- Create: `adjudant/scripts/repo_tidy.py`
- Test: `adjudant/scripts/test_repo_tidy.py`
- Depends on: Task 1

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_repo_tidy.py`:

```python
#!/usr/bin/env python3
"""Tests for repo_tidy preview/apply."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_tidy as rt
import repo_walk as rw


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _plugin(root: Path, name: str, version: str, *, adopt: bool = False) -> None:
    _write(root / name / ".claude-plugin" / "plugin.json",
           '{\n  "name": "%s",\n  "version": "%s"\n}\n' % (name, version))
    if adopt:
        _write(root / name / "skills" / name / "SKILL.md", "---\nname: %s\n---\n" % name)
        for harness in rw.HARNESS_SUBPATHS:
            lp = root / name / harness / "skills"
            lp.mkdir(parents=True, exist_ok=True)
            os.symlink("../../skills/" + name, lp / name)


def _repo(tmp: Path) -> Path:
    (tmp / ".git").mkdir()
    _write(tmp / ".claude-plugin" / "marketplace.json",
           '{\n  "name": "mk",\n  "version": "1.0.0",\n  "plugins": [\n'
           '    {"name": "alpha", "version": "0.6.0", "source": "./alpha"},\n'
           '    {"name": "beta", "version": "0.3.1", "source": "./beta"}\n'
           '  ]\n}\n')
    _plugin(tmp, "alpha", "0.6.0", adopt=True)
    _plugin(tmp, "beta", "0.3.2", adopt=False)
    return tmp


class TestVersionSync(unittest.TestCase):
    def test_computes_fix_for_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            fix = rt.compute_version_sync(root)
            self.assertIsNotNone(fix)
            self.assertEqual(fix["fixes"], {"beta": "0.3.2"})
            self.assertIn('"name": "beta", "version": "0.3.2"',
                          fix["proposed_content"].replace("\n", " ").replace("  ", " "))

    def test_none_when_clean(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            # Align beta on disk to match the manifest
            _write(root / "beta" / ".claude-plugin" / "plugin.json",
                   '{\n  "name": "beta",\n  "version": "0.3.1"\n}\n')
            self.assertIsNone(rt.compute_version_sync(root))


class TestPreviewApply(unittest.TestCase):
    def test_detect_phases(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            self.assertEqual(rt.detect_phase(root), "fresh")
            rt.write_preview_to_disk(root, rt.build_preview(root))
            self.assertEqual(rt.detect_phase(root), "preview")

    def test_apply_fixes_marketplace_and_backs_up(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            rt.write_preview_to_disk(root, rt.build_preview(root))
            backup = rt.apply_preview(root)
            mk = json.loads((root / ".claude-plugin" / "marketplace.json").read_text())
            beta = next(p for p in mk["plugins"] if p["name"] == "beta")
            self.assertEqual(beta["version"], "0.3.2")
            self.assertTrue((backup / ".claude-plugin" / "marketplace.json.legacy").is_file())
            self.assertFalse((root / rt.PREVIEW_DIR_NAME).exists())

    def test_idempotent_second_preview_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            rt.write_preview_to_disk(root, rt.build_preview(root))
            rt.apply_preview(root)
            cs = rt.build_preview(root)
            self.assertEqual(cs["summary"]["total_changes"], 0)


class TestSymlinkRepair(unittest.TestCase):
    def test_recreates_missing_link(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            broken = root / "alpha" / ".claude" / "skills" / "alpha"
            broken.unlink()
            rt.write_preview_to_disk(root, rt.build_preview(root))
            rt.apply_preview(root)
            self.assertTrue(broken.is_symlink())
            self.assertTrue(broken.resolve() == (root / "alpha" / "skills" / "alpha").resolve())

    def test_apply_skips_blocked_real_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = _repo(Path(d))
            link = root / "alpha" / ".gemini" / "skills" / "alpha"
            link.unlink()
            link.mkdir()                       # a real dir now blocks the link slot
            _write(link / "keep.md", "real\n")
            actions = rt.compute_symlink_repairs(root)
            blocked = [a for a in actions if a["link"].endswith(".gemini/skills/alpha")]
            self.assertTrue(blocked and blocked[0]["prior"].startswith("blocked"))
            rt.write_preview_to_disk(root, rt.build_preview(root))
            rt.apply_preview(root)
            self.assertTrue(link.is_dir() and not link.is_symlink())  # untouched


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_repo_tidy -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'repo_tidy'`

- [ ] **Step 3: Write the module**

Create `adjudant/scripts/repo_tidy.py`:

```python
#!/usr/bin/env python3
"""Adjudant repo_tidy — safe mechanical repo sweep.

Mirror of tidy.py for the CODE repo. Two safe, idempotent fixes:
  1. Version sync — rewrite marketplace.json plugin versions to match each
     plugin's own plugin.json (surgical per-plugin line edit).
  2. Symlink repair — recreate broken/missing Impeccable harness symlinks in
     plugins that already adopt the pattern.

Never restructures, never deletes, never adopts the pattern for a new plugin
(that is ramasse-tier), never clobbers a real path. Two-phase preview → apply.

Phases:
  detect   — print 'fresh' | 'preview' | 'applied'
  preview  — write .adjudant-repo-tidy-preview/ (read-only sweep)
  apply    — backup live files to .adjudant-repo-tidy-backup/{ts}/, apply preview

CLI:
    python3 repo_tidy.py detect  --repo-dir PATH
    python3 repo_tidy.py preview --repo-dir PATH
    python3 repo_tidy.py apply   --repo-dir PATH
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from repo_walk import (
    find_repo_root,
    plugin_symlink_status,
    read_marketplace,
    walk_plugins,
)


PREVIEW_DIR_NAME = ".adjudant-repo-tidy-preview"
BACKUP_DIR_NAME = ".adjudant-repo-tidy-backup"


def detect_phase(repo_root: Path) -> str:
    preview = repo_root / PREVIEW_DIR_NAME
    backup = repo_root / BACKUP_DIR_NAME
    if preview.is_dir():
        return "preview"
    if backup.is_dir() and any(backup.iterdir()):
        return "applied"
    return "fresh"


def _hash_short(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


# ============================================================
# Fix 1 — marketplace version sync (surgical per-plugin edit)
# ============================================================


def compute_version_sync(repo_root: Path) -> Optional[dict[str, Any]]:
    """If any marketplace.json plugin version drifts from that plugin's own
    plugin.json, return a file proposal for marketplace.json. None when no
    marketplace manifest or no drift.

    Surgical: replaces only the `"version": "..."` value inside each drifting
    plugin's `{ "name": ..., "version": ... }` block — every other byte is
    preserved, so the diff is minimal and the op 'never breaks'."""
    marketplace = read_marketplace(repo_root)
    if marketplace is None:
        return None
    mk_path = repo_root / ".claude-plugin" / "marketplace.json"
    original = mk_path.read_text()
    plugins = {p.name: p for p in walk_plugins(repo_root)}

    fixes: dict[str, str] = {}
    for entry in marketplace.plugins:
        name = entry.get("name")
        plugin = plugins.get(name)
        if plugin and plugin.version and entry.get("version") != plugin.version:
            fixes[name] = plugin.version
    if not fixes:
        return None

    proposed = original
    for name, correct in fixes.items():
        pattern = re.compile(
            r'("name"\s*:\s*"' + re.escape(name) + r'"\s*,\s*"version"\s*:\s*")([^"]*)(")'
        )
        proposed = pattern.sub(lambda m: m.group(1) + correct + m.group(3), proposed, count=1)

    if proposed == original:
        return None

    return {
        "rel": ".claude-plugin/marketplace.json",
        "original_hash": _hash_short(original),
        "proposed_hash": _hash_short(proposed),
        "proposed_content": proposed,
        "fixes": fixes,
    }


# ============================================================
# Fix 2 — symlink repair (adopted plugins only)
# ============================================================


def compute_symlink_repairs(repo_root: Path) -> list[dict[str, Any]]:
    """Planned symlink (re)creations for adopted plugins with broken/missing
    harness links. Each action records link (rel), target (relative symlink
    string), and prior state: 'missing' | 'wrong:<old>' | 'blocked:real-path-present'.
    Blocked actions are recorded for transparency but skipped on apply."""
    actions: list[dict[str, Any]] = []
    for p in walk_plugins(repo_root):
        for st in plugin_symlink_status(p):
            if st.ok:
                continue
            link_abs = repo_root / st.link
            if link_abs.is_symlink():
                try:
                    prior = "wrong:" + os.readlink(link_abs)
                except OSError:
                    prior = "wrong:?"
            elif link_abs.exists():
                prior = "blocked:real-path-present"
            else:
                prior = "missing"
            actions.append({
                "link": str(st.link),
                "target": st.expected_target,
                "prior": prior,
            })
    return actions


# ============================================================
# Preview build
# ============================================================


def build_preview(repo_root: Path) -> dict[str, Any]:
    version_fix = compute_version_sync(repo_root)
    symlink_actions = compute_symlink_repairs(repo_root)
    actionable = [a for a in symlink_actions if not a["prior"].startswith("blocked")]

    file_proposals: dict[str, dict[str, Any]] = {}
    if version_fix:
        file_proposals[version_fix["rel"]] = {
            "original_hash": version_fix["original_hash"],
            "proposed_hash": version_fix["proposed_hash"],
            "proposed_content": version_fix["proposed_content"],
            "fixes": version_fix["fixes"],
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo_dir": str(repo_root),
        "summary": {
            "version_fixes": len(file_proposals),
            "symlink_repairs": len(actionable),
            "total_changes": len(file_proposals) + len(actionable),
        },
        "file_proposals": file_proposals,
        "symlink_actions": symlink_actions,
    }


def write_preview_to_disk(repo_root: Path, change_set: dict[str, Any]) -> Path:
    preview = repo_root / PREVIEW_DIR_NAME
    if preview.exists():
        shutil.rmtree(preview)
    preview.mkdir()

    (preview / "changes.json").write_text(json.dumps(change_set, indent=2, default=str))

    files_root = preview / "files"
    files_root.mkdir()
    for rel, info in change_set["file_proposals"].items():
        target = files_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(info["proposed_content"])

    lines = [
        "# Repo-tidy preview", "",
        f"Generated: {change_set['generated_at']}",
        f"Repo: {change_set['repo_dir']}", "",
        "## Summary", "",
        f"- Version fixes: {change_set['summary']['version_fixes']}",
        f"- Symlink repairs: {change_set['summary']['symlink_repairs']}",
        f"- Total changes: {change_set['summary']['total_changes']}", "",
        "## Version fixes", "",
    ]
    for rel, info in sorted(change_set["file_proposals"].items()):
        for name, ver in sorted(info.get("fixes", {}).items()):
            lines.append(f"- `{name}` → {ver} (in `{rel}`)")
    lines += ["", "## Symlink repairs", ""]
    for a in change_set["symlink_actions"]:
        lines.append(f"- `{a['link']}` → {a['target']} (was: {a['prior']})")
    lines += ["", "## Next steps", "",
              "- Review proposed files under `files/`",
              "- To apply: `python3 repo_tidy.py apply --repo-dir <PATH>`",
              f"- To discard: delete `{PREVIEW_DIR_NAME}/`"]
    (preview / "summary.md").write_text("\n".join(lines) + "\n")
    return preview


# ============================================================
# Apply phase
# ============================================================


def apply_preview(repo_root: Path) -> Path:
    preview = repo_root / PREVIEW_DIR_NAME
    if not preview.is_dir():
        raise RuntimeError(f"no preview at {preview}")
    changes_path = preview / "changes.json"
    if not changes_path.is_file():
        raise RuntimeError(f"corrupt preview: {changes_path} missing")
    change_set = json.loads(changes_path.read_text())

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = repo_root / BACKUP_DIR_NAME / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(changes_path, backup_dir / "changes.json")  # audit trail

    files_root = preview / "files"
    for rel in change_set["file_proposals"].keys():
        live = repo_root / rel
        proposed = files_root / rel
        if not proposed.is_file():
            continue
        if live.is_file():
            backup_target = backup_dir / (rel + ".legacy")
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, backup_target)
        live.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(proposed, live)

    for a in change_set.get("symlink_actions", []):
        if a["prior"].startswith("blocked"):
            continue
        link = repo_root / a["link"]
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() or link.exists():
            try:
                link.unlink()
            except OSError:
                continue
        os.symlink(a["target"], link)

    shutil.rmtree(preview)
    return backup_dir


# ============================================================
# CLI
# ============================================================


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repo_tidy.py",
        description="Adjudant repo_tidy — safe mechanical repo sweep (preview/apply).",
    )
    parser.add_argument("phase", choices=["detect", "preview", "apply"])
    parser.add_argument("--repo-dir", default=".")
    args = parser.parse_args(argv)

    repo_root = find_repo_root(Path(args.repo_dir))
    if not repo_root.is_dir():
        print(f"error: repo-dir not found: {repo_root}", file=sys.stderr)
        return 1

    if args.phase == "detect":
        print(detect_phase(repo_root))
        return 0

    if args.phase == "preview":
        if detect_phase(repo_root) == "preview":
            print(f"error: preview already exists at {repo_root / PREVIEW_DIR_NAME}", file=sys.stderr)
            print("delete it or run 'apply' to commit it", file=sys.stderr)
            return 1
        change_set = build_preview(repo_root)
        preview = write_preview_to_disk(repo_root, change_set)
        print(f"[repo_tidy] preview written to {preview}", file=sys.stderr)
        print(json.dumps(change_set["summary"]))
        return 0

    if args.phase == "apply":
        if detect_phase(repo_root) != "preview":
            print(f"error: no preview at {repo_root / PREVIEW_DIR_NAME}; run 'preview' first", file=sys.stderr)
            return 1
        backup_dir = apply_preview(repo_root)
        print(f"[repo_tidy] applied; backup at {backup_dir}", file=sys.stderr)
        print(json.dumps({"backup_dir": str(backup_dir)}))
        return 0

    return 2  # unreachable


if __name__ == "__main__":
    sys.exit(cli_main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd adjudant/scripts && python3 -m unittest test_repo_tidy -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/repo_tidy.py adjudant/scripts/test_repo_tidy.py
git commit -m "feat(adjudant): repo_tidy.py — two-phase version-sync + symlink-repair sweep"
```

---

## Task 4: `repo-standards.md` — single source of truth

**Files:**
- Create: `adjudant/skills/adjudant/reference/repo-standards.md`

- [ ] **Step 1: Write the reference doc**

Create `adjudant/skills/adjudant/reference/repo-standards.md`:

```markdown
# Repo standards — single source of truth

Authoritative spec for repo-side structural conventions. `repo_scan.py` detects
drift against these; `repo_tidy.py` fixes the safe ones; `ramasse repo` plans the
structural ones. The build's `validate.py` enforces this doc's coverage.

Layered, mirroring how the vault verbs degrade gracefully:
- **General core** — runs on any connected repo.
- **Marketplace layer** — auto-activates only when `.claude-plugin/marketplace.json` is present.

## Detector categories

### Version coherence (marketplace layer)
Each plugin's version in `.claude-plugin/marketplace.json` must equal the
`version` in that plugin's own `.claude-plugin/plugin.json`. Drift is a
`tidy repo` fix (safe, surgical line edit).

### Symlink integrity / Impeccable pattern (marketplace layer)
A plugin that adopts the pattern keeps its skill canonical under
`skills/<skill>/` and mirrors it with three harness symlinks —
`source/skills/<skill>`, `.claude/skills/<skill>`, `.gemini/skills/<skill>` —
each pointing at `../../skills/<skill>`. **Repairing** a broken/missing link in
an adopted plugin is a `tidy repo` fix. **Adopting** the pattern for a plugin
that lacks it entirely is `ramasse repo` (structural, can-break).

### Context-file presence (general core)
The repo root and every plugin should carry `AGENTS.md` and `CLAUDE.md`, and
`CLAUDE.md`'s first non-empty line must be `@AGENTS.md`. Scaffolding missing
files is `ramasse repo`.

### Plan-file age (general core)
Plan files under `docs/superpowers/` (`*.plan.md`) older than 30 days with no
completion marker (`status: complete|done|shipped|archived|superseded`, a
`> COMPLETE` line, or ✅) are flagged stale. Archiving them is `ramasse repo`.

### Registration coherence (marketplace layer)
Every plugin directory on disk must be registered in `marketplace.json`, and
every registered `source` path must exist. Reconciling is `ramasse repo`.

## Tier mapping

```
check repo   = read-only audit of all categories above
tidy repo    = safe fixes: version coherence + symlink repair
ramasse repo = structural: pattern adoption, context scaffolding, plan archival, registration
```

## See also
- `reference/vault-standards.md` — the vault-side counterpart
- `scripts/repo_scan.py` — detectors (analysis)
- `scripts/repo_tidy.py` — safe fixes (preview → apply)
```

- [ ] **Step 2: Commit**

```bash
git add adjudant/skills/adjudant/reference/repo-standards.md
git commit -m "docs(adjudant): repo-standards.md — SSOT for repo-side detector categories"
```

---

## Task 5: Extend the verb reference docs with the `[target]` dimension

**Files:**
- Modify: `adjudant/skills/adjudant/reference/check.md`
- Modify: `adjudant/skills/adjudant/reference/tidy.md`
- Modify: `adjudant/skills/adjudant/reference/ramasse.md`

- [ ] **Step 1: Add the repo section to `check.md`**

In `adjudant/skills/adjudant/reference/check.md`, change the title line and opening so the verb is target-aware, then append a repo section before `## See also`.

Replace the first line:

```markdown
# /adjudant check
```
with:
```markdown
# /adjudant check [vault|repo|all]

**Target** — `vault` (default), `repo`, or `all`. `vault` is everything below; `repo` runs the repo audit; `all` renders both.
```

Append before `## See also`:

```markdown
## check repo

Read-only repo audit. Runs `repo_scan.py` and renders its JSON. Never writes.

```bash
python3 "$(dirname "$0")/../../../scripts/repo_scan.py" --repo-dir "$REPO_ROOT"
```

JSON top-level keys: `meta` (repo_root, is_marketplace, plugins_scanned), `summary.drift_items`, `version_drift`, `symlink_drift`, `context_gaps`, `stale_plans`, `registration_gaps`. Render a compact table per non-empty category plus the `drift_items` headline. Categories are defined in `reference/repo-standards.md`.
```

- [ ] **Step 2: Add the repo section to `tidy.md`**

In `adjudant/skills/adjudant/reference/tidy.md`, change the title line:

```markdown
# /adjudant tidy [vault|repo|all]
```

Append before `## See also`:

```markdown
## tidy repo

Safe mechanical repo sweep — **version coherence** (sync `marketplace.json` to each `plugin.json`) and **symlink repair** (recreate broken Impeccable harness links in plugins that already adopt the pattern). Two-phase preview → apply, mirroring vault tidy. Never adopts the pattern for a new plugin, never deletes, never clobbers a real path (those are `ramasse repo`).

```bash
# Phase 1 — preview (writes .adjudant-repo-tidy-preview/, never touches live files)
python3 "$(dirname "$0")/../../../scripts/repo_tidy.py" preview --repo-dir "$REPO_ROOT"

# Phase 2 — apply (creates .adjudant-repo-tidy-backup/{timestamp}/, then writes live)
python3 "$(dirname "$0")/../../../scripts/repo_tidy.py" apply --repo-dir "$REPO_ROOT"
```

Idempotent: a second preview with no fresh drift reports `total_changes: 0`.
```

- [ ] **Step 3: Add the repo section to `ramasse.md`**

In `adjudant/skills/adjudant/reference/ramasse.md`, change the title line:

```markdown
# /adjudant ramasse [vault|repo|all]
```

Append before `## See also`:

```markdown
## ramasse repo

Deep STRUCTURAL repo clean — the can-break work `tidy repo` refuses:
- **Adopt the Impeccable pattern** for a plugin that lacks it (canonical `skills/<skill>/` + the three harness symlinks).
- **Scaffold missing `AGENTS.md`/`CLAUDE.md`** per plugin (CLAUDE imports AGENTS).
- **Archive stale plan files** flagged by the scanner.
- **Reconcile registration** between disk and `marketplace.json`.

Same 5-phase superpowers chain as the vault side. Phase 1 analysis runs the repo scanner:

```bash
python3 "$(dirname "$0")/../../../scripts/repo_scan.py" --repo-dir "$REPO_ROOT" --out /tmp/repo-ramasse-scan.json
```

For mechanical sub-steps (version sync, symlink repair), call `repo_tidy.py preview` then `apply` inside phase 5, exactly as vault ramasse calls `tidy.py`. Categories and tier boundaries are defined in `reference/repo-standards.md`.
```

- [ ] **Step 4: Commit**

```bash
git add adjudant/skills/adjudant/reference/check.md adjudant/skills/adjudant/reference/tidy.md adjudant/skills/adjudant/reference/ramasse.md
git commit -m "docs(adjudant): add [vault|repo|all] target sections to check/tidy/ramasse references"
```

---

## Task 6: Update `command-metadata.json` argument hints (no version bump yet)

**Files:**
- Modify: `adjudant/scripts/command-metadata.json`

> Note: this task does NOT bump the version (that is Task 7, atomic across all four files). Editing only `argumentHint`/`description` keeps `command-metadata.json` at `0.5.2`, matching the other three files, so `version-consistency` stays green at commit time. The verb NAMES are unchanged, so `command-metadata-coherence` stays green too.

- [ ] **Step 1: Edit the three cleanup verbs' argument hints**

In `adjudant/scripts/command-metadata.json`:

Change the `check` entry's `argumentHint` from `"(no args)"` to `"[vault|repo|all]"` and append to its description: ` Target [vault|repo|all] (default vault); repo audit via repo_scan.py.`

Change the `tidy` entry's `argumentHint` from `"(no args)"` to `"[vault|repo|all]"` and append to its description: ` Target [vault|repo|all] (default vault); repo sweep via repo_tidy.py.`

Change the `ramasse` entry's `argumentHint` from `"(no args)"` to `"[vault|repo|all]"` and append to its description: ` Target [vault|repo|all] (default vault); repo analysis via repo_scan.py.`

- [ ] **Step 2: Verify JSON is valid + validators still green**

Run: `python3 -c "import json; json.load(open('adjudant/scripts/command-metadata.json'))" && python3 adjudant/scripts/validate.py`
Expected: no JSON error; validators report PASS (versions still all `0.5.2`).

- [ ] **Step 3: Commit**

```bash
git add adjudant/scripts/command-metadata.json
git commit -m "feat(adjudant): command-metadata — [vault|repo|all] argument hints for check/tidy/ramasse"
```

---

## Task 7: Version bump to 0.6.0 (atomic across all four files) + SKILL.md routing

**Files:**
- Modify: `adjudant/.claude-plugin/plugin.json`
- Modify: `adjudant/scripts/command-metadata.json`
- Modify: `adjudant/skills/adjudant/SKILL.md`
- Modify: `.claude-plugin/marketplace.json`

> All four version edits land in ONE commit so `version-consistency` (#10) never sees a mismatch. The gemineye drift in `marketplace.json` is deliberately left for the Task 9 dogfood.

- [ ] **Step 1: Bump `plugin.json`**

In `adjudant/.claude-plugin/plugin.json`, change `"version": "0.5.2"` to `"version": "0.6.0"`. Append to the description: ` v0.6.0 adds the [vault|repo|all] target to check/tidy/ramasse — adjudant now cleans the code repo (version coherence, symlink integrity, context-file presence, stale plans, registration) as well as the vault, via repo_walk.py/repo_scan.py/repo_tidy.py.`

- [ ] **Step 2: Bump `command-metadata.json`**

In `adjudant/scripts/command-metadata.json`, change `"version": "0.5.2"` to `"version": "0.6.0"`.

- [ ] **Step 3: Bump + route `SKILL.md`**

In `adjudant/skills/adjudant/SKILL.md`:

Change `version: 0.5.2` to `version: 0.6.0`.

In the verb-router table, replace the `check`, `tidy`, and `ramasse` rows' Purpose column (keep columns 1–2 byte-for-byte so `command-metadata-coherence`'s regex still matches) — append ` **Target `[vault|repo|all]`** (default vault).` to each of those three Purpose cells.

After the locked-three-tier code block, add this block:

```markdown
## Cleanup targets (v0.6.0)

Each cleanup tier takes a `[vault|repo|all]` target (default `vault`). The tier is the *risk level*; the target is *what it points at*.

| | vault | repo |
|---|---|---|
| `check` | project + vault snapshot (`check.py`) | repo drift audit (`repo_scan.py`) |
| `tidy` | indexes, tags, wikilink form (`tidy.py`) | version coherence + symlink repair (`repo_tidy.py`) |
| `ramasse` | folders, schema, naming (`ramasse_scan.py`) | pattern adoption, context scaffolding, plan archival (`repo_scan.py`) |

Repo conventions are specified in `reference/repo-standards.md`. `dream` stays vault-only.
```

In the "Python helper layer" table, add three rows:

```markdown
| `check repo` | `repo_scan.py` + `repo_walk.py` | JSON repo drift catalog |
| `tidy repo` | `repo_tidy.py` + `repo_walk.py` | preview/apply (version sync + symlink repair) |
| `ramasse repo` | `repo_scan.py` + `repo_walk.py` | JSON drift catalog (analysis); planning + execute via superpowers |
```

In the "Vault standards" section, add a sentence: `Repo-side conventions live in `reference/repo-standards.md` (the repo counterpart).`

- [ ] **Step 4: Bump adjudant in `marketplace.json`**

In `.claude-plugin/marketplace.json`, in the adjudant plugin entry, change `"version": "0.5.2"` to `"version": "0.6.0"`. Append to adjudant's description: ` v0.6.0: check/tidy/ramasse gain a [vault|repo|all] target — adjudant now cleans the code repo as well as the vault.` **Leave the gemineye entry at `0.3.1`** (the Task 9 dogfood fixes it).

- [ ] **Step 5: Verify version consistency**

Run: `python3 adjudant/scripts/validate.py`
Expected: PASS — `version-consistency` sees `0.6.0` in plugin.json / command-metadata.json / SKILL.md / marketplace.json. `command-metadata-coherence` still green (verb names unchanged).

- [ ] **Step 6: Commit**

```bash
git add adjudant/.claude-plugin/plugin.json adjudant/scripts/command-metadata.json adjudant/skills/adjudant/SKILL.md .claude-plugin/marketplace.json
git commit -m "release(adjudant): v0.6.0 — repo as a second cleanup target (check/tidy/ramasse [vault|repo|all])"
```

---

## Task 8: Add repo validators + gitignore entries

**Files:**
- Modify: `adjudant/scripts/validate.py`
- Modify: `.gitignore`

- [ ] **Step 1: Add the gitignore entries**

In `.gitignore`, under the `# Adjudant verb working dirs (port + tidy preview/apply state)` block, add two lines after `.adjudant-tidy-backup/`:

```
.adjudant-repo-tidy-preview/
.adjudant-repo-tidy-backup/
```

- [ ] **Step 2: Add five validators to `validate.py`**

In `adjudant/scripts/validate.py`, add these functions before `def main()`:

```python
REPO_HELPERS = ["repo_walk.py", "repo_scan.py", "repo_tidy.py"]
REPO_STANDARDS_CATEGORIES = [
    "Version coherence",
    "Symlink integrity",
    "Context-file presence",
    "Plan-file age",
    "Registration coherence",
]


def validate_repo_helper_parity(r: Result) -> None:
    name = "repo-helper-parity"
    scripts = ROOT / "scripts"
    missing: list[str] = []
    for helper in REPO_HELPERS:
        if not (scripts / helper).is_file():
            missing.append(helper)
        test_name = "test_" + helper
        if not (scripts / test_name).is_file():
            missing.append(test_name)
    if missing:
        r.add_fail(name, f"missing repo helper/test files: {missing}")
        return
    r.add_pass(name)


def validate_repo_standards_coverage(r: Result) -> None:
    name = "repo-standards-coverage"
    doc = REFERENCE / "repo-standards.md"
    if not doc.is_file():
        r.add_fail(name, "reference/repo-standards.md missing")
        return
    text = doc.read_text()
    missing = [c for c in REPO_STANDARDS_CATEGORIES if c not in text]
    if missing:
        r.add_fail(name, f"repo-standards.md missing category headings: {missing}")
        return
    r.add_pass(name)


def validate_repo_tidy_preview_coherence(r: Result) -> None:
    name = "repo-tidy-preview-coherence"
    preview = ROOT / ".adjudant-repo-tidy-preview"
    if not preview.is_dir():
        r.add_pass(name)
        return
    missing = [f for f in TIDY_PREVIEW_REQUIRED if not (preview / f).is_file()]
    if missing:
        r.add_fail(name, f"repo-tidy preview dir missing required files: {missing}")
        return
    if not (preview / "files").is_dir():
        r.add_fail(name, "repo-tidy preview dir missing files/ subdir")
        return
    r.add_pass(name)


def validate_repo_tidy_backup_integrity(r: Result) -> None:
    name = "repo-tidy-backup-integrity"
    backup_root = ROOT / ".adjudant-repo-tidy-backup"
    if not backup_root.is_dir():
        r.add_pass(name)
        return
    # Each timestamp dir must carry the audit manifest (changes.json).
    for subdir in backup_root.iterdir():
        if subdir.is_dir() and any(subdir.iterdir()):
            if not (subdir / "changes.json").is_file():
                r.add_fail(name, f"repo-tidy backup {subdir.name} missing changes.json manifest")
                return
    r.add_pass(name)


def validate_gitignore_includes_repo_tidy_dirs(r: Result) -> None:
    name = "gitignore-includes-repo-tidy-dirs"
    preview = ROOT / ".adjudant-repo-tidy-preview"
    backup = ROOT / ".adjudant-repo-tidy-backup"
    if not preview.is_dir() and not backup.is_dir():
        r.add_pass(name)
        return
    gi = ROOT / ".gitignore"
    if not gi.is_file():
        gi = ROOT.parent / ".gitignore"
    if not gi.is_file():
        r.add_fail(name, "repo-tidy directories exist but .gitignore is missing")
        return
    text = gi.read_text()
    required = []
    if preview.is_dir():
        required.append(".adjudant-repo-tidy-preview/")
    if backup.is_dir():
        required.append(".adjudant-repo-tidy-backup/")
    missing = [e for e in required if e not in text]
    if missing:
        r.add_fail(name, f".gitignore missing entries: {missing}")
        return
    r.add_pass(name)
```

Then register them in `main()` after `validate_gitignore_includes_tidy_dirs(r)`:

```python
    validate_repo_helper_parity(r)
    validate_repo_standards_coverage(r)
    validate_repo_tidy_preview_coherence(r)
    validate_repo_tidy_backup_integrity(r)
    validate_gitignore_includes_repo_tidy_dirs(r)
```

Also extend the module docstring's numbered validator list with entries 14–18 (repo-helper-parity, repo-standards-coverage, repo-tidy-preview-coherence, repo-tidy-backup-integrity, gitignore-includes-repo-tidy-dirs).

- [ ] **Step 3: Run validators**

Run: `python3 adjudant/scripts/validate.py`
Expected: PASS — now 18 validators green (repo-helper-parity finds the three helpers + tests from Tasks 1–3; repo-standards-coverage finds the doc from Task 4).

- [ ] **Step 4: Commit**

```bash
git add adjudant/scripts/validate.py .gitignore
git commit -m "feat(adjudant): 5 repo validators (helper parity, repo-standards coverage, repo-tidy preview/backup/gitignore)"
```

---

## Task 9: Full verification + live dogfood

**Files:** none (verification only; the dogfood mutates `.claude-plugin/marketplace.json`)

- [ ] **Step 1: Full test suite green**

Run: `python3 -m unittest discover -s adjudant/scripts -p 'test_*.py'`
Expected: OK — all existing tests (216) plus the new `test_repo_walk` / `test_repo_scan` / `test_repo_tidy` pass.

- [ ] **Step 2: Validators green**

Run: `python3 adjudant/scripts/validate.py`
Expected: `PASS — 18 validator(s) green`

- [ ] **Step 3: Scan finds the live drift**

Run: `python3 adjudant/scripts/repo_scan.py --repo-dir . --today 2026-06-07 --json`
Expected (on this repo): JSON with `version_drift` containing `{"plugin": "gemineye", "marketplace_version": "0.3.1", "plugin_version": "0.3.2"}`; `context_gaps` listing the plugins lacking AGENTS/CLAUDE; `stale_plans` listing plan files >30 days old; `symlink_drift` empty (adjudant's links are intact); `summary.drift_items` > 0.

- [ ] **Step 4: Dogfood — preview the repo tidy**

Run: `python3 adjudant/scripts/repo_tidy.py preview --repo-dir .`
Expected: stderr `[repo_tidy] preview written to .../.adjudant-repo-tidy-preview`; stdout summary JSON with `version_fixes: 1` (gemineye). Inspect `.adjudant-repo-tidy-preview/summary.md` — it should list `` `gemineye` → 0.3.2 ``.

- [ ] **Step 5: Dogfood — apply, then confirm the fix**

Run: `python3 adjudant/scripts/repo_tidy.py apply --repo-dir .`
Then: `python3 -c "import json; print([p['version'] for p in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if p['name']=='gemineye'])"`
Expected: `['0.3.2']`. The backup dir `.adjudant-repo-tidy-backup/{ts}/.claude-plugin/marketplace.json.legacy` holds the pre-fix file.

- [ ] **Step 6: Idempotency**

Run: `python3 adjudant/scripts/repo_tidy.py preview --repo-dir .`
Expected: error `preview already exists` (from step 4's dir not yet cleaned) OR, after deleting `.adjudant-repo-tidy-preview/`, a fresh preview with `version_fixes: 0`. To confirm idempotency cleanly: `rm -rf .adjudant-repo-tidy-preview && python3 adjudant/scripts/repo_tidy.py preview --repo-dir .` → summary `total_changes: 0` for version (symlink_repairs also 0 on this repo).

- [ ] **Step 7: Re-run validators after the dogfood mutation**

Run: `python3 adjudant/scripts/validate.py`
Expected: PASS. (`version-consistency` only checks adjudant; the gemineye fix doesn't affect it. `repo-tidy-backup-integrity` confirms the backup carries `changes.json`. `gitignore-includes-repo-tidy-dirs` confirms the backup dir is gitignored.)

- [ ] **Step 8: Commit the dogfood result**

```bash
git add .claude-plugin/marketplace.json
git commit -m "fix(marketplace): sync gemineye 0.3.1 → 0.3.2 via adjudant tidy repo (dogfood)"
```

---

## Self-Review

**1. Spec coverage** — every spec section maps to a task:
- Surface `[vault|repo|all]` → Tasks 6 (hints), 7 (SKILL routing), 5 (reference docs).
- `check repo` / `tidy repo` / `ramasse repo` behaviour → Tasks 2, 3, 5.
- Layered detectors (general core + marketplace layer) → Task 2 (`repo_scan` detectors, `is_marketplace_repo` gating).
- New modules mirroring existing ones → Tasks 1–3.
- `repo-standards.md` SSOT → Task 4.
- I/O contract + cardinality `drift_items` → Task 2 (`run_scan`).
- Validators → Task 8. `.gitignore` → Task 8.
- Versioning 0.6.0 across four files → Task 7. Dogfood (gemineye) → Task 9.
- Default target `vault` / back-compat → no change to existing helpers; the target is a doc-level dispatch (Task 5/7), existing `check.py`/`tidy.py`/`ramasse_scan.py` untouched.

**2. Placeholder scan** — no TBD/TODO; every code step contains complete, runnable code; every command has expected output.

**3. Type consistency** — names are consistent across tasks: `find_repo_root`, `walk_plugins`, `is_marketplace_repo`, `read_marketplace`, `plugin_symlink_status`, `context_files_status`, `plan_file_ages`, `PluginDir.adopts_impeccable`, `SymlinkStatus.ok`, `HARNESS_SUBPATHS`, `STALE_PLAN_DAYS` (defined Task 1; imported in Tasks 2–3). `run_scan(repo_root, today)`, detector names, and `drift_items` keys match between `repo_scan.py` and its tests. `PREVIEW_DIR_NAME`/`BACKUP_DIR_NAME`, `compute_version_sync`, `compute_symlink_repairs`, `build_preview`, `write_preview_to_disk`, `apply_preview`, `detect_phase` match between `repo_tidy.py` and its tests. Validator helper constants (`TIDY_PREVIEW_REQUIRED`, `REFERENCE`, `ROOT`) referenced in Task 8 already exist in `validate.py`.

**Known acceptable risks:**
- `repo_scan` uses `--repo-dir` (not `--project-dir`) to make explicit that repo ops do NOT follow the vault breadcrumb. This is intentional divergence from `check.py`/`tidy.py`, documented in each new module's header and the reference docs.
- `context_gaps` will flag all current plugins (none ship per-plugin AGENTS/CLAUDE today). That is correct reporting; only version coherence is auto-fixed by `tidy repo`. Scaffolding is `ramasse repo` and is not executed by this plan.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-07-adjudant-repo-target.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
