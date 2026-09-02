# Adjudant v3, Plan 4: Structure and Truth

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The vault becomes navigable by path alone, and `status` stops grading shape and starts checking truth.

**Architecture:** Four named lifecycle folders replace the three-zone `("", "_fridge", "_archive")` scheme, and links stop carrying the lifecycle folder so a project move rewrites nothing. Every placement decision collapses into one `place()` and every link into one `link()`, both in a new `_place.py`. Folders appear when something goes in them, so the empty-index class of file cannot be born. Two generated surfaces, `Home.md` and `{slug}/_index.md`, replace 141 hand-rotting index files. And a new `truth.py` replaces check's schema grading with findings that trace to a real failure, ordered by the cost of being wrong.

**Tech Stack:** Python 3.9+ stdlib only, bash hooks, `unittest`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-01-adjudant-v3-design.md` — phase 4, plus the settled sections "Folder structure, naming and links", "The repo side", and "What `check` does".

## Inbound state: plans 1, 2 and 3 have landed

This plan is written against the end state of the three plans before it. An
executor who finds otherwise must stop and say so rather than adapt.

| Assumed | Consequence for this plan |
|---|---|
| Plan 1 landed | Scratch lives at `$TMPDIR/adjudant/{project}/{kind}` via `_scratch.py`. `adjudant/skills/adjudant/reference/state-contract.md` exists and Task 2 extends it. The session-log hook already writes `[[{slug}/…]]`, not `[[projects/{slug}/…]]`. |
| Plan 2 landed | The fifteen templates in `adjudant/skills/adjudant/templates/` are the only declaration of a kind's shape; `FIELD_SCHEMA` is parsed from them. `brief.md` frontmatter is `type`, `updated`, `verified` only — **no `status:` field**. `verified:` and `verified_by:` exist. Task statuses are the seven with no aliases; decision statuses are three; spec statuses are three. |
| Plan 3 landed | Six verbs. `check.py` is folded into **`status.py`**, whose `run_status(project_dir, code_root=None, today=None) -> dict` is the descendant of `check.run_check`, tested in **`test_status.py`**. `tidy.py` and `ramasse_scan.py` are merged into **`clean.py`**, tested in **`test_clean.py`**; `build_preview(project_dir, vault_index, project_slug) -> dict` keeps its signature. `port.py`, `shelf.py`, `sitrep.py`, `sync.py`, `kebab.py` and `advisor.py` are deleted. |

Files that **no plan before this one modifies** are cited by `file:line`, verified
against the tree at commit `9b1ac00`. Files that plans 2 and 3 rewrite
(`status.py`, `clean.py`) are cited **by symbol only**, because a line number
through a rename is a lie.

## Global Constraints

- **Stdlib only.** No new dependencies, in any task.
- **Python 3.9 floor.** No `match`, no `X | Y` unions at runtime in signatures evaluated at import (`from __future__ import annotations` is already in every module and stays).
- **Hooks never fail loudly.** Every hook exits 0 whatever happens. Wrap new I/O in the existing try/except shape and never let an exception escape `main()`.
- **The suite must be green after every task.** Run `python3 -m unittest discover -p 'test_*.py'` from `adjudant/scripts/`. The pre-v3 baseline was 1233 tests; plans 1 to 3 moved it, so assert `OK`, never a count.
- **Validators must stay green.** Run `python3 adjudant/scripts/validate.py` from the repo root. The pre-v3 baseline was 35 validators; plan 3 deleted the four `port` validators.
- **Never write to the real vault during tests.** Every test builds a temp vault and pops `OB_VAULT` from the environment.
- **Links never carry the lifecycle folder.** `[[hubspot-nightly/decisions/2026-08-12-branch-track|branch track]]`, never `[[projects/active/hubspot-nightly/…]]`. Enforced in code by `link()` raising, not by review.
- **`status` never writes and never gates.** The truth report is read-only output. It orders findings by the cost of being wrong; it refuses nothing.
- **Adjudant stays out of generated files.** Any file carrying `source:` in its frontmatter is never cleaned, never indexed, and never nagged about.
- **Filenames are kebab-case everywhere.** Dated kinds keep the date prefix, numbered kinds keep the number.
- **Commit style:** Conventional Commits, scope `adjudant`. End every commit message with:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
- **The statusline is an external consumer.** `~/.claude/statusline-v2.sh` (a symlink into iCloud) walks the zone list at lines 605-620 and renders the zone at line 861. Task 2 updates it. Do not land Task 1 without Task 2 in the same session.

## File Structure

| File | Responsibility |
|---|---|
| `adjudant/scripts/_place.py` | **New.** `place()`, `link()`, `project_rel()`. The single owner of where a file goes and how it is linked. Imported by the hooks, `connect.py`, `clean.py` and `_index_gen.py`. |
| `adjudant/scripts/test__place.py` | **New.** Tests for the above. |
| `adjudant/scripts/_lifecycle.py` | **New.** `triage_plan()` (read-only) and `apply_move()` (one project, on confirmation). The guided triage, and nothing else. |
| `adjudant/scripts/test__lifecycle.py` | **New.** Tests for the above. |
| `adjudant/scripts/_index_gen.py` | **New.** Renders and writes the two surviving index surfaces, and prunes the rest. |
| `adjudant/scripts/test__index_gen.py` | **New.** Tests for the above. |
| `adjudant/scripts/truth.py` | **New.** The truth checks: a `Finding` record, one detector per spec item, banded output. |
| `adjudant/scripts/test_truth.py` | **New.** Tests for the above, one per detector. |
| `adjudant/scripts/_agents_reach.py` | **New.** The one check that reaches outside the vault: every path AGENTS.md names, and commits since it changed. |
| `adjudant/scripts/test__agents_reach.py` | **New.** Tests for the above. |
| `adjudant/scripts/_vault_walk.py` | Zone constants become four named folders. `build_vault_index` and `resolve_wikilink` stop matching bare stems. `schema_drift` exempts `memory/`. |
| `adjudant/scripts/connect.py` | Stops scaffolding folders and empty indexes. Stops writing `projects/_index.md`. |
| `adjudant/scripts/clean.py` | Loses every index writer. Gains the `references/` split. |
| `adjudant/scripts/status.py` | Reports the truth findings and the triage prompt in place of schema drift. |
| `adjudant/hooks/scripts/session-start.sh` | `zone_project_dir` walks the four folders. |
| `adjudant/hooks/scripts/sessionend.sh` | Same. |
| `adjudant/hooks/scripts/posttooluse-vault-log.py` | Fallback resolver walks four folders; the log line goes through `link()`. |
| `adjudant/hooks/scripts/posttooluse-commit-log.py` | Fallback resolver walks four folders. |
| `adjudant/scripts/validate.py` | Validator 30's zone list follows. New validator: no module writes a wikilink except `_place.link`. |
| `adjudant/skills/adjudant/reference/vault-standards.md` | Rewritten: structure, naming, links, markdown elements. Links to templates instead of restating them. |
| `adjudant/skills/adjudant/reference/content-markdown.md` | Rewritten to stop contradicting the above. |
| `adjudant/skills/adjudant/reference/state-contract.md` | Gains the four-folder zone walk and the generated surfaces. |
| `~/.claude/statusline-v2.sh` | Zone walk and zone label follow. Outside this repo. |

---

## Task 1: Four lifecycle folders

`projects/` grows four named folders and loses the unnamed default. The old
scheme put the live zone at `projects/{slug}` with no folder at all, which is
why the constant's first element is an empty string and why every consumer
carries a `if zone else` branch.

**Files:**
- Modify: `adjudant/scripts/_vault_walk.py:900-907` (the zone block, under the existing `# Project status lifecycle + zones` header), `:1481-1493` (`find_project_dir`), `:1496-1499` (`zone_of`), `:1502-1510` (`zone_matches_status`, deleted), `:1513-1530` (`enumerate_projects_all_zones`)
- Test: `adjudant/scripts/test__vault_walk.py:888-899` (`TestStatusVocabulary`) and `:986-1027` (`TestZones`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, all in `_vault_walk`:
  - `PROJECT_ZONES: tuple[str, ...] = ("active", "paused", "finished", "archive")`
  - `LEGACY_ZONES: tuple[str, ...] = ("", "_fridge", "_archive")`
  - `LEGACY_ZONE_ALIAS: dict[str, str] = {"": "active", "_fridge": "paused", "_archive": "archive"}`
  - `ZONE_FOR_STATUS: dict[str, str]` — the migration map from the retired six-value project status onto the four folders. Read-side only; nothing writes a project `status:` after plan 2.
  - `zone_dir(vault: Path, zone: str) -> Path` — `{vault}/projects/{zone}`.
  - `find_project_dir(vault: Path, slug: str) -> Optional[Path]` — unchanged signature, searches the four folders then the three legacy shapes.
  - `zone_of(project_dir: Path) -> str` — now returns a **normalised** zone name from `PROJECT_ZONES`, never `""`.
  - `enumerate_projects_all_zones(vault: Path) -> list[tuple[str, Path, str]]` — unchanged signature; the third element is now a normalised zone.
  - `zone_matches_status` is **deleted**. Step 6 of this task removes its one non-test caller.

- [ ] **Step 1: Write the failing test**

Replace the `TestStatusVocabulary` and `TestZones` classes in `adjudant/scripts/test__vault_walk.py` (lines 888-899 and 986-1027; the `from _vault_walk import (` block at line 1030 is a different section and stays) with:

```python
class TestLifecycleFolders(unittest.TestCase):

    def test_four_named_folders(self):
        self.assertEqual(PROJECT_ZONES,
                         ("active", "paused", "finished", "archive"))
        self.assertNotIn("", PROJECT_ZONES,
                         "the live zone is a named folder now, not the absence of one")

    def test_legacy_shapes_map_onto_the_four(self):
        self.assertEqual(LEGACY_ZONES, ("", "_fridge", "_archive"))
        self.assertEqual(set(LEGACY_ZONE_ALIAS.values()) - set(PROJECT_ZONES), set())
        self.assertEqual(LEGACY_ZONE_ALIAS[""], "active")
        self.assertEqual(LEGACY_ZONE_ALIAS["_fridge"], "paused")
        self.assertEqual(LEGACY_ZONE_ALIAS["_archive"], "archive")

    def test_status_migration_map_lands_in_the_four(self):
        # The retired project status vocabulary still sits in briefs written
        # before v3. It is read to SUGGEST a folder during triage, never to
        # grade one.
        self.assertEqual(set(ZONE_FOR_STATUS.values()) - set(PROJECT_ZONES), set())
        self.assertEqual(ZONE_FOR_STATUS["active"], "active")
        self.assertEqual(ZONE_FOR_STATUS["stale"], "active")
        self.assertEqual(ZONE_FOR_STATUS["seed"], "active")
        self.assertEqual(ZONE_FOR_STATUS["fridge"], "paused")
        self.assertEqual(ZONE_FOR_STATUS["done"], "finished")
        self.assertEqual(ZONE_FOR_STATUS["dead"], "archive")

    def test_zone_dir(self):
        self.assertEqual(zone_dir(Path("/v"), "paused"),
                         Path("/v/projects/paused"))


class TestZones(unittest.TestCase):

    def test_find_project_dir_across_the_four(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            for zone in ("active", "paused", "finished", "archive"):
                _mk_project(vault, f"p-{zone}", zone=zone)
            for zone in ("active", "paused", "finished", "archive"):
                found = find_project_dir(vault, f"p-{zone}")
                self.assertEqual(zone_of(found), zone)
            self.assertIsNone(find_project_dir(vault, "nope"))

    def test_find_project_dir_still_finds_an_unmigrated_project(self):
        # A vault that has not been triaged yet must keep working: every hook
        # and every verb resolves through this one function.
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "bare", zone="")
            _mk_project(vault, "cold", zone="_fridge")
            _mk_project(vault, "gone", zone="_archive")
            self.assertEqual(find_project_dir(vault, "bare"),
                             vault / "projects" / "bare")
            self.assertEqual(zone_of(find_project_dir(vault, "bare")), "active")
            self.assertEqual(zone_of(find_project_dir(vault, "cold")), "paused")
            self.assertEqual(zone_of(find_project_dir(vault, "gone")), "archive")

    def test_named_folder_beats_a_legacy_twin(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "p", zone="")
            _mk_project(vault, "p", zone="active")
            self.assertEqual(find_project_dir(vault, "p"),
                             vault / "projects" / "active" / "p")

    def test_enumerate_normalises_the_zone(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "a", zone="active")
            _mk_project(vault, "b", zone="_fridge")
            (vault / "projects" / "_index.md").write_text("idx")
            rows = enumerate_projects_all_zones(vault)
            self.assertEqual([(s, z) for s, _p, z in rows],
                             [("a", "active"), ("b", "paused")])

    def test_zone_matches_status_is_gone(self):
        import _vault_walk
        self.assertFalse(hasattr(_vault_walk, "zone_matches_status"),
                         "the folder IS the lifecycle state; nothing grades it "
                         "against a field the brief no longer carries")
```

In the same file, update the import block at lines 860-871 to read:

```python
from _vault_walk import (
    DEFAULT_STALE_DAYS,
    LEGACY_ZONES,
    LEGACY_ZONE_ALIAS,
    PROJECT_STATUS_VALUES,
    PROJECT_ZONES,
    ZONE_FOR_STATUS,
    enumerate_projects_all_zones,
    find_project_dir,
    newest_dated_stem,
    resolve_project_from_cwd,
    suggest_status,
    zone_dir,
    zone_of,
)
```

and change `_mk_project` (line 875) so a `zone` of `""` still means `projects/{slug}`, which it already does — no edit needed there. Delete
`test_resolve_project_from_cwd_finds_archived`'s assertion on the literal
`_archive` path and replace its final assertion with:

```python
            self.assertEqual(ctx.vault_project_dir,
                             vault / "projects" / "_archive" / "proj")
            self.assertEqual(zone_of(ctx.vault_project_dir), "archive")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestLifecycleFolders test__vault_walk.TestZones -v`
Expected: FAIL with `ImportError: cannot import name 'LEGACY_ZONES' from '_vault_walk'`

- [ ] **Step 3: Rewrite the zone block**

Replace `adjudant/scripts/_vault_walk.py:900-907` with (the section header two lines above it stays):

```python
# The lifecycle is the FOLDER, and there are four of them. Before v3 the live
# zone was the absence of a folder (`projects/{slug}`), which is why every
# consumer carried an `if zone else` branch and why the constant's first
# element was the empty string. A named folder costs one path segment and
# removes that branch everywhere.
PROJECT_ZONES: tuple[str, ...] = ("active", "paused", "finished", "archive")

# The pre-v3 shapes, still on disk until triage runs. Read-side only: nothing
# writes these, and find_project_dir searches them after the named four so a
# migrated project always wins over an abandoned twin.
LEGACY_ZONES: tuple[str, ...] = ("", "_fridge", "_archive")
LEGACY_ZONE_ALIAS: dict[str, str] = {
    "": "active", "_fridge": "paused", "_archive": "archive",
}

# The retired six-value project status, kept only to READ a pre-v3 brief and
# suggest a destination folder during triage. v3 briefs carry no `status:`
# field at all: a fourth hand-written answer to "where is this project" is a
# fourth thing that can disagree with the other three.
PROJECT_STATUS_VALUES: tuple[str, ...] = ("active", "stale", "fridge", "done", "dead", "seed")
ZONE_FOR_STATUS: dict[str, str] = {
    "active": "active", "stale": "active", "seed": "active",
    "fridge": "paused", "done": "finished", "dead": "archive",
}
DEFAULT_STALE_DAYS = 30
FRIDGE_NUDGE_DAYS = 180


def zone_dir(vault: Path, zone: str) -> Path:
    """`{vault}/projects/{zone}`. A legacy zone of "" collapses to projects/."""
    base = vault / "projects"
    return (base / zone) if zone else base
```

- [ ] **Step 4: Rewrite the three zone-walking functions**

Replace `adjudant/scripts/_vault_walk.py:1481-1530` (from `def find_project_dir` through the end of `enumerate_projects_all_zones`) with:

```python
def _project_candidates(vault: Path, slug: str) -> list[Path]:
    """Every path a project called `slug` could occupy, best shape first.

    The four named folders come first, so a migrated project always beats an
    unmigrated twin left behind by an interrupted move.
    """
    out = [zone_dir(vault, z) / slug for z in PROJECT_ZONES]
    out += [zone_dir(vault, z) / slug for z in LEGACY_ZONES]
    return out


def find_project_dir(vault: Path, slug: str) -> Optional[Path]:
    """Locate a project across lifecycle folders. Prefers a dir with brief.md."""
    candidates = _project_candidates(vault, slug)
    for c in candidates:
        if (c / "brief.md").is_file():
            return c
    for c in candidates:
        if c.is_dir():
            return c
    return None


def zone_of(project_dir: Path) -> str:
    """The lifecycle folder a project sits in, always one of PROJECT_ZONES.

    A pre-v3 path normalises: `projects/{slug}` reads as "active",
    `_fridge` as "paused", `_archive` as "archive". Callers get a name they
    can render and compare; nothing outside this module handles "".
    """
    parent = project_dir.parent.name
    if parent in PROJECT_ZONES:
        return parent
    if parent in LEGACY_ZONE_ALIAS:
        return LEGACY_ZONE_ALIAS[parent]
    return "active"


def enumerate_projects_all_zones(vault: Path) -> list[tuple[str, Path, str]]:
    """Every project (slug, dir, normalised zone) across all lifecycle folders.

    A project is a directory containing brief.md. Leading-underscore and dot
    dirs are skipped inside each folder, which is also what keeps a legacy
    `_fridge/` from being read as a project when scanning `projects/` itself.
    A slug found in more than one place is reported once, from the first
    folder in PROJECT_ZONES order, then legacy order.
    """
    out: list[tuple[str, Path, str]] = []
    seen: set[str] = set()
    base = vault / "projects"
    for zone in PROJECT_ZONES + LEGACY_ZONES:
        zdir = zone_dir(vault, zone)
        if not zdir.is_dir():
            continue
        for d in sorted(zdir.iterdir(), key=lambda p: p.name):
            if not d.is_dir() or d.name.startswith("_") or d.name.startswith("."):
                continue
            if d.name in PROJECT_ZONES and d.parent == base:
                continue            # a lifecycle folder is not a project
            if d.name in seen:
                continue
            if (d / "brief.md").is_file():
                seen.add(d.name)
                out.append((d.name, d, zone_of(d)))
    return out
```

- [ ] **Step 5: Run the new tests**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestLifecycleFolders test__vault_walk.TestZones -v`
Expected: PASS, 9 tests

- [ ] **Step 6: Fix the callers the deletion breaks**

`zone_matches_status` had exactly one non-test caller. In `status.py` (plan 3's
descendant of `check.py`, where the pre-v3 lines were `check.py:252-254`), the
status block reads:

```python
    zone = zone_of(project_dir)
    status = {**sug, "zone": zone,
              "zone_matches": zone_matches_status(brief.get("status"), zone)}
```

Replace it with:

```python
    status = {**sug, "zone": zone_of(project_dir)}
```

and drop `zone_matches_status` from that module's `_vault_walk` import list.
Delete any assertion on `report["status"]["zone_matches"]` in `test_status.py`.

- [ ] **Step 7: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`. Validator 23 (`status-vocabulary`) asserts `PROJECT_STATUS_VALUES` against the six-state vocabulary and the brief templates. The constant is unchanged, so it stays green; if plan 2 already retired it, delete validator 23 and decrement the count in `validate.py`'s docstring.

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 8: Commit**

```bash
git add adjudant/scripts/_vault_walk.py adjudant/scripts/status.py adjudant/scripts/test__vault_walk.py adjudant/scripts/test_status.py
git commit -m "feat(adjudant): four named lifecycle folders under projects/

active, paused, finished, archive replace the ('', '_fridge', '_archive')
scheme where the live zone was the absence of a folder. zone_of now
normalises: every caller gets a name from PROJECT_ZONES and nothing outside
_vault_walk handles the empty string. Legacy shapes still resolve, so an
untriaged vault keeps working.

zone_matches_status is deleted. The folder IS the lifecycle state; grading it
against a brief field that v3 no longer writes was the fourth answer to a
question that already had three.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: The hooks, the validator and the statusline follow the folders

Four consumers hardcode the three-zone list outside `_vault_walk`. Two are bash,
two are Python import-failure fallbacks, and one lives in iCloud.

**Files:**
- Modify: `adjudant/hooks/scripts/session-start.sh:20-31`, `adjudant/hooks/scripts/sessionend.sh:13-24`
- Modify: `adjudant/hooks/scripts/posttooluse-vault-log.py:77-87`, `adjudant/hooks/scripts/posttooluse-commit-log.py:46-56`
- Modify: `adjudant/scripts/validate.py` (validator 30, `hook-zone-awareness`)
- Modify: `~/Library/Mobile Documents/com~apple~CloudDocs/Projects/IDE/claude/statusline-v2.sh:605-620` and `:861`
- Modify: `adjudant/skills/adjudant/reference/state-contract.md`
- Test: `adjudant/scripts/test_hook_shell.py`

**Interfaces:**
- Consumes: `PROJECT_ZONES`, `LEGACY_ZONES` from Task 1.
- Produces: nothing new. The bash `zone_project_dir(vault, slug)` keeps its contract exactly: prints the project dir and returns 0, or returns 1 when the project exists in no folder.

- [ ] **Step 1: Write the failing shell test**

Append to `adjudant/scripts/test_hook_shell.py`:

```python
class TestZoneWalkCoversTheFourFolders(unittest.TestCase):
    """Both shell hooks carry their own copy of find_project_dir, because a
    python shim would cost a subprocess on a hook that fires every session.
    Two copies drift, so this test reads both."""

    HOOKS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"

    def test_both_hooks_list_all_four_folders(self):
        for name in ("session-start.sh", "sessionend.sh"):
            text = (self.HOOKS / name).read_text()
            self.assertIn('local zones="active paused finished archive"', text,
                          f"{name} does not probe the four lifecycle folders")

    def test_both_hooks_still_probe_the_legacy_shapes(self):
        for name in ("session-start.sh", "sessionend.sh"):
            text = (self.HOOKS / name).read_text()
            self.assertIn('local legacy="_fridge _archive"', text, name)
            self.assertIn('cands="$cands $vault/projects/$slug"', text,
                          f"{name} dropped the untriaged shape")

    def test_the_bare_shape_is_probed_after_the_named_folders(self):
        # A migrated project must beat a twin left behind by an interrupted
        # move, so order in the candidate list is load-bearing.
        for name in ("session-start.sh", "sessionend.sh"):
            text = (self.HOOKS / name).read_text()
            self.assertLess(text.index('for c in $zones;'),
                            text.index('cands="$cands $vault/projects/$slug"'),
                            name)

    def test_python_hook_fallbacks_list_all_four_folders(self):
        for name in ("posttooluse-vault-log.py", "posttooluse-commit-log.py"):
            text = (self.HOOKS / name).read_text()
            self.assertIn('"projects" / "paused"', text,
                          f"{name}'s degraded resolver misses paused/")
            self.assertIn('"projects" / "finished"', text, name)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_hook_shell.TestZoneWalkCoversTheFourFolders -v`
Expected: FAIL — `session-start.sh does not probe the four lifecycle folders`

- [ ] **Step 3: Rewrite both bash copies**

Replace `adjudant/hooks/scripts/session-start.sh:20-31` and
`adjudant/hooks/scripts/sessionend.sh:13-24` — the two bodies are byte-identical
apart from their preceding comment — with:

```bash
zone_project_dir() {
  local vault="$1" slug="$2" c
  local zones="active paused finished archive"
  local legacy="_fridge _archive"
  local cands=""
  for c in $zones; do cands="$cands $vault/projects/$c/$slug"; done
  cands="$cands $vault/projects/$slug"
  for c in $legacy; do cands="$cands $vault/projects/$c/$slug"; done
  for c in $cands; do
    if [ -f "$c/brief.md" ]; then printf '%s' "$c"; return 0; fi
  done
  for c in $cands; do
    if [ -d "$c" ]; then printf '%s' "$c"; return 0; fi
  done
  return 1
}
```

Keep each file's existing comment above the function, and add one line to both:
`# Four named folders first, then the pre-v3 shapes, so a migrated project`
`# always beats a twin left behind by an interrupted move.`

Note the word-split loop is safe here because zone names are literals with no
spaces; `$slug` and `$vault` are only ever interpolated into a quoted path
inside the loop body.

- [ ] **Step 4: Rewrite both Python fallbacks**

In `adjudant/hooks/scripts/posttooluse-vault-log.py:77-87` and
`adjudant/hooks/scripts/posttooluse-commit-log.py:46-56`, replace the `cands`
list in each degraded `find_project_dir` with:

```python
        def find_project_dir(vault, slug):  # type: ignore
            cands = [vault / "projects" / z / slug
                     for z in ("active", "paused", "finished", "archive")]
            cands.append(vault / "projects" / slug)
            cands += [vault / "projects" / z / slug
                      for z in ("_fridge", "_archive")]
            for c in cands:
                if (c / "brief.md").is_file():
                    return c
            for c in cands:
                if c.is_dir():
                    return c
            return None
```

`posttooluse-commit-log.py`'s copy sits at module level rather than inside a
function, so it is indented four spaces, not eight; keep its existing
indentation and change only the body.

- [ ] **Step 5: Update validator 30**

In `adjudant/scripts/validate.py`, validator 30 (`hook-zone-awareness`, the
function whose docstring begins `30. hook-zone-awareness`) scans
`hooks/scripts/*` for a hardcoded `projects/<slug>`. Its rejection pattern must
not fire on the new literal folder names. Add, immediately before the offender
loop:

```python
    # v3: the four lifecycle folder names are literals in every resolver by
    # design. Only an UNQUALIFIED projects/{slug} outside a resolver is drift.
    _ZONE_LITERAL_RE = re.compile(
        r"projects/(?:active|paused|finished|archive|_fridge|_archive)/")
```

and skip any line `_ZONE_LITERAL_RE.search(line)` matches before applying the
existing offender test. Update the validator's docstring to say four folders
plus two legacy shapes.

- [ ] **Step 6: Run the hook tests**

Run: `cd adjudant/scripts && python3 -m unittest test_hook_shell test_posttooluse_vault_log test_posttooluse_tasks test_commit_log -v 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 7: Update the statusline zone walk**

Replace lines 605-620 of `~/.claude/statusline-v2.sh` — the `Zone-aware project
resolution` block — with:

```bash
  # Zone-aware project resolution. Since adjudant v3 the lifecycle is four
  # NAMED folders under projects/; the pre-v3 shapes (bare, _fridge, _archive)
  # are probed after them so an untriaged vault still renders. Prefer the
  # candidate that actually holds a brief.md.
  proj_vault=""; zone=""
  if [ -n "$vault_path" ] && [ -n "$slug" ]; then
    for z in active paused finished archive "" _fridge _archive; do
      cand="${vault_path}/projects${z:+/${z}}/${slug}"
      if [ -f "${cand}/brief.md" ]; then proj_vault="$cand"; zone="$z"; break; fi
    done
    if [ -z "$proj_vault" ]; then
      for z in active paused finished archive "" _fridge _archive; do
        cand="${vault_path}/projects${z:+/${z}}/${slug}"
        if [ -d "$cand" ]; then proj_vault="$cand"; zone="$z"; break; fi
      done
    fi
    case "$zone" in
      ""|active) zone="" ;;     # the working folder is the default; no badge
      _fridge)   zone="paused" ;;
      _archive)  zone="archive" ;;
    esac
  fi
```

At line 861 the badge is rendered as `${zone#_}`, which stripped the leading
underscore of the old names. The names no longer carry one, so replace that
line with:

```bash
  [ -n "$zone" ] && s2_col+="${VAULT_STALE} (${zone})${R}"
```

- [ ] **Step 8: Verify the statusline still renders**

Run:

```bash
echo '{"session_id":"test","model":{"display_name":"Test"},"workspace":{"current_dir":"."}}' | bash "$HOME/.claude/statusline-v2.sh"
```

Expected: a rendered status line, no bash errors on stderr.

- [ ] **Step 9: Extend the state contract**

In `adjudant/skills/adjudant/reference/state-contract.md`, replace the table row
that reads `projects/{zone}/{slug}/brief.md`, `status:` | lifecycle drift with
these two rows:

```markdown
| `projects/{active\|paused\|finished\|archive}/{slug}/` (dir exists) | lifecycle folder, rendered as a badge for anything but `active` |
| `projects/{slug}/`, `projects/_fridge/{slug}/`, `projects/_archive/{slug}/` | pre-v3 shapes, probed after the four; `_fridge` reads as paused, `_archive` as archive |
```

Add to the Rules list:

```markdown
6. The lifecycle folder is the project's lifecycle state. `brief.md` carries no
   `status:` field since v3, so nothing may read one. A project's folder and the
   newest file in its `sessions/` are the two inputs to lifecycle drift.
```

- [ ] **Step 10: Commit**

```bash
git add adjudant/hooks/scripts/session-start.sh adjudant/hooks/scripts/sessionend.sh adjudant/hooks/scripts/posttooluse-vault-log.py adjudant/hooks/scripts/posttooluse-commit-log.py adjudant/scripts/validate.py adjudant/scripts/test_hook_shell.py adjudant/skills/adjudant/reference/state-contract.md
git commit -m "feat(adjudant): hooks, validator and statusline walk the four folders

Four consumers carried their own copy of the zone list: two bash resolvers,
two python import-failure fallbacks, and the statusline in iCloud. All four
now probe active/paused/finished/archive first and the pre-v3 shapes after,
so an untriaged vault keeps resolving.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `_place.py` — one placement decision, one link

Three different hardcoded link shapes exist today:
`posttooluse-vault-log.py:238` writes `[[projects/{slug}/…]]`, `connect.py:643`
writes `[[{slug}/brief\|{slug}]]`, and `tidy.py:268` and `:274` write a bare
`[[{stem}|{display}]]`. None of them agree, and the middle one is the only shape
that survives a project move.

**Files:**
- Create: `adjudant/scripts/_place.py`
- Test: `adjudant/scripts/test__place.py`

**Interfaces:**
- Consumes: `PROJECT_ZONES` from Task 1.
- Produces, used by Tasks 4, 5, 7, 8, 13:
  - `KIND_FOLDER: dict[str, str]` — the fifteen kinds to their folder. A kind that lives at the project root maps to `""`.
  - `DATED_KINDS: frozenset[str]` — kinds whose filename starts with an ISO date.
  - `place(note_type: str, project_dir: Path, hints: Optional[dict] = None) -> Path` — the absolute path a file of `note_type` belongs at, with its folder chain created. `hints` accepts `slug` (str, the kebab stem), `date` (str, `YYYY-MM-DD`), `group` (str, the one legal level of grouping). Raises `ValueError` on an unknown kind, a missing required hint, a non-kebab slug, or a `group` on a kind that does not take one.
  - `project_rel(path: Path, project_dir: Path) -> str` — `{slug}/{rel}` with no lifecycle folder and no `.md`, for feeding to `link`.
  - `link(target_rel: str, alias: Optional[str] = None, *, in_table: bool = False) -> str` — the only wikilink writer. Raises `ValueError` when the target names a lifecycle folder or starts with `projects/`.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test__place.py`:

```python
"""Tests for adjudant/scripts/_place.py — the single owner of where a file
goes and how it is linked.

Before v3 three writers each had their own link shape and none agreed. Two of
the three embedded the lifecycle folder, so moving a project between active/
and paused/ broke every link into it — which is what shelf.py's 380-line
vault-wide link rewrite existed to repair.
"""

import tempfile
import unittest
from pathlib import Path

from _place import (
    DATED_KINDS,
    KIND_FOLDER,
    link,
    place,
    project_rel,
)


class TestKindTable(unittest.TestCase):

    def test_fifteen_kinds(self):
        self.assertEqual(len(KIND_FOLDER), 15)

    def test_the_settled_folders(self):
        self.assertEqual(KIND_FOLDER["session"], "sessions")
        self.assertEqual(KIND_FOLDER["decision"], "decisions")
        self.assertEqual(KIND_FOLDER["task"], "tasks")
        self.assertEqual(KIND_FOLDER["note"], "notes")
        self.assertEqual(KIND_FOLDER["doc"], "docs")
        self.assertEqual(KIND_FOLDER["spec"], "specs")
        self.assertEqual(KIND_FOLDER["component"], "components")
        self.assertEqual(KIND_FOLDER["api"], "api")
        self.assertEqual(KIND_FOLDER["schema"], "schemas")
        self.assertEqual(KIND_FOLDER["source"], "sources")
        self.assertEqual(KIND_FOLDER["release"], "releases")
        self.assertEqual(KIND_FOLDER["dream"], "dreams")

    def test_root_kinds_have_no_folder(self):
        for kind in ("project", "handoff", "index"):
            self.assertEqual(KIND_FOLDER[kind], "", kind)

    def test_dated_kinds(self):
        self.assertEqual(DATED_KINDS, frozenset({"session", "decision", "dream"}))


class TestPlace(unittest.TestCase):

    def _project(self, tmp: Path) -> Path:
        p = tmp / "vault" / "projects" / "active" / "demo"
        p.mkdir(parents=True)
        return p

    def test_undated_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            got = place("note", proj, {"slug": "cold-cache-quadratic"})
            self.assertEqual(got, proj / "notes" / "cold-cache-quadratic.md")

    def test_dated_kind_takes_the_date_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            got = place("decision", proj,
                        {"slug": "drop-bucket-a-tags", "date": "2026-09-01"})
            self.assertEqual(
                got, proj / "decisions" / "2026-09-01-drop-bucket-a-tags.md")

    def test_session_is_dated_with_no_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            got = place("session", proj, {"date": "2026-09-01"})
            self.assertEqual(got, proj / "sessions" / "2026-09-01.md")

    def test_root_kinds(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            self.assertEqual(place("project", proj), proj / "brief.md")
            self.assertEqual(place("handoff", proj), proj / "_handoff.md")
            self.assertEqual(place("index", proj), proj / "_index.md")

    def test_one_level_of_grouping_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            got = place("component", proj, {"slug": "button", "group": "modules"})
            self.assertEqual(got, proj / "components" / "modules" / "button.md")
            with self.assertRaises(ValueError):
                place("component", proj, {"slug": "b", "group": "a/b"})
            with self.assertRaises(ValueError):
                place("note", proj, {"slug": "n", "group": "deep"})

    def test_creates_the_folder_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            got = place("note", proj, {"slug": "a"})
            self.assertTrue(got.parent.is_dir())
            self.assertFalse(got.exists(), "place() must not create the file")
            self.assertEqual(sorted(p.name for p in proj.iterdir()), ["notes"],
                             "place() created a folder nobody asked for")

    def test_unknown_kind_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            with self.assertRaises(ValueError):
                place("iteration", proj, {"slug": "x"})

    def test_non_kebab_slug_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            for bad in ("Upper", "with space", "with.dot", "../escape", ""):
                with self.assertRaises(ValueError, msg=bad):
                    place("note", proj, {"slug": bad})

    def test_missing_date_on_a_dated_kind_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            with self.assertRaises(ValueError):
                place("dream", proj, {})

    def test_malformed_date_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            with self.assertRaises(ValueError):
                place("session", proj, {"date": "2026-9-1"})


class TestProjectRel(unittest.TestCase):

    def test_drops_the_lifecycle_folder_and_the_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "vault" / "projects" / "active" / "demo"
            (proj / "decisions").mkdir(parents=True)
            f = proj / "decisions" / "2026-09-01-x.md"
            self.assertEqual(project_rel(f, proj), "demo/decisions/2026-09-01-x")

    def test_project_root_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "vault" / "projects" / "paused" / "demo"
            proj.mkdir(parents=True)
            self.assertEqual(project_rel(proj / "brief.md", proj), "demo/brief")

    def test_a_legacy_project_path_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "vault" / "projects" / "demo"
            (proj / "notes").mkdir(parents=True)
            self.assertEqual(project_rel(proj / "notes" / "a.md", proj),
                             "demo/notes/a")

    def test_a_file_outside_the_project_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "p"
            proj.mkdir()
            with self.assertRaises(ValueError):
                project_rel(Path(tmp) / "elsewhere.md", proj)


class TestLink(unittest.TestCase):

    def test_the_settled_shape(self):
        self.assertEqual(
            link("hubspot-nightly/decisions/2026-08-12-branch-track",
                 "branch track"),
            "[[hubspot-nightly/decisions/2026-08-12-branch-track|branch track]]")

    def test_no_alias(self):
        self.assertEqual(link("demo/notes/a"), "[[demo/notes/a]]")

    def test_extension_is_stripped(self):
        self.assertEqual(link("demo/notes/a.md"), "[[demo/notes/a]]")

    def test_table_cells_escape_the_separator(self):
        self.assertEqual(link("demo/brief", "demo", in_table=True),
                         "[[demo/brief\\|demo]]")

    def test_a_lifecycle_folder_in_the_target_is_loud(self):
        for zone in ("active", "paused", "finished", "archive"):
            with self.assertRaises(ValueError, msg=zone):
                link(f"{zone}/demo/notes/a")

    def test_a_projects_prefix_is_loud(self):
        with self.assertRaises(ValueError):
            link("projects/demo/notes/a")

    def test_an_empty_target_is_loud(self):
        with self.assertRaises(ValueError):
            link("")

    def test_an_alias_pipe_is_loud(self):
        # An alias carrying a pipe would silently truncate the link.
        with self.assertRaises(ValueError):
            link("demo/notes/a", "a|b")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__place -v`
Expected: FAIL with `ModuleNotFoundError: No module named '_place'`

- [ ] **Step 3: Write the implementation**

Create `adjudant/scripts/_place.py`:

```python
#!/usr/bin/env python3
"""Adjudant placement — where a file goes, and how it is linked.

Two decisions used to be spread across every writer. Placement was a folder
name typed at each call site, which is how `references/` ended up holding six
unrelated kinds. Linking had three shapes: the session-log hook wrote
`[[projects/{slug}/…]]`, connect wrote `[[{slug}/brief\\|{slug}]]`, and the
index generator wrote a bare `[[{stem}|{display}]]`. Two of the three embedded
the lifecycle folder, so a project moving between active/ and paused/ broke
every link into it — which is the only thing the deleted 380-line vault-wide
link rewrite ever did.

Obsidian resolves a wikilink by matching the END of a path, so
`[[hubspot-nightly/decisions/2026-08-12-branch-track]]` finds the file under
any lifecycle folder. Omitting the folder is therefore not a compromise: it is
the form that stays true.

Every rule here fails loudly. A silent coercion is how `obsolete` became
invisible work and how 45 type values grew out of five.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

# The fifteen kinds and the one folder each lives in. "" means the project
# root. Nothing else may name a project subfolder.
KIND_FOLDER: dict[str, str] = {
    "project": "",          # brief.md
    "handoff": "",          # _handoff.md
    "index": "",            # _index.md
    "session": "sessions",
    "decision": "decisions",
    "task": "tasks",
    "note": "notes",
    "doc": "docs",
    "spec": "specs",
    "component": "components",
    "api": "api",
    "schema": "schemas",
    "source": "sources",
    "release": "releases",
    "dream": "dreams",
}

# Kinds whose filename carries an ISO date prefix. `created:` is derived from
# it at write time, so the two can never disagree.
DATED_KINDS: frozenset[str] = frozenset({"session", "decision", "dream"})

# The fixed filenames of the three root kinds.
_ROOT_FILENAME: dict[str, str] = {
    "project": "brief.md",
    "handoff": "_handoff.md",
    "index": "_index.md",
}

# Kinds that may take ONE level of grouping. 225 component pages need
# components/modules/ and components/templates/. Nothing needs to go deeper.
_GROUPABLE: frozenset[str] = frozenset({"component"})

# The four lifecycle folders, duplicated here rather than imported so this
# module stays importable by a hook running in degraded mode. Task 1 owns the
# authoritative copy in _vault_walk.PROJECT_ZONES; validator 30's sibling
# keeps them in step.
_LIFECYCLE_FOLDERS: frozenset[str] = frozenset(
    {"active", "paused", "finished", "archive"})

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _require_kebab(value: str, what: str) -> str:
    if not isinstance(value, str) or not _KEBAB_RE.match(value):
        raise ValueError(f"{what} must be kebab-case, got {value!r}")
    return value


def place(note_type: str, project_dir: Path,
          hints: Optional[dict] = None) -> Path:
    """Where a file of `note_type` belongs, with its folder chain created.

    `hints`: `slug` (kebab stem), `date` (YYYY-MM-DD, required for a dated
    kind), `group` (one kebab segment, only for a groupable kind).

    Creates the folder, never the file, so a caller that decides not to write
    leaves nothing behind. This is the whole fix for the fifteen index files
    with a body under 25 bytes: a folder now exists because something is in it.
    """
    hints = hints or {}
    if note_type not in KIND_FOLDER:
        raise ValueError(
            f"unknown kind {note_type!r}; the fifteen are "
            f"{', '.join(sorted(KIND_FOLDER))}")

    group = hints.get("group")
    if group is not None:
        if note_type not in _GROUPABLE:
            raise ValueError(f"{note_type} takes no grouping folder")
        _require_kebab(group, "group")

    if note_type in _ROOT_FILENAME:
        return project_dir / _ROOT_FILENAME[note_type]

    folder = project_dir / KIND_FOLDER[note_type]
    if group is not None:
        folder = folder / group

    if note_type in DATED_KINDS:
        date = hints.get("date")
        if not isinstance(date, str) or not _ISO_DATE_RE.match(date):
            raise ValueError(
                f"{note_type} needs a YYYY-MM-DD date hint, got {date!r}")
        slug = hints.get("slug")
        stem = f"{date}-{_require_kebab(slug, 'slug')}" if slug else date
    else:
        stem = _require_kebab(hints.get("slug"), "slug")

    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{stem}.md"


def project_rel(path: Path, project_dir: Path) -> str:
    """`{slug}/{path relative to the project}`, extension stripped.

    The lifecycle folder is dropped on purpose: this is the link target form,
    and it must survive the project moving between folders.
    """
    try:
        rel = path.resolve().relative_to(project_dir.resolve())
    except ValueError as e:
        raise ValueError(f"{path} is not inside {project_dir}") from e
    parts = list(rel.parts)
    if parts and parts[-1].endswith(".md"):
        parts[-1] = parts[-1][:-3]
    return "/".join([project_dir.name] + parts)


def link(target_rel: str, alias: Optional[str] = None, *,
         in_table: bool = False) -> str:
    """The only wikilink adjudant writes.

    `target_rel` is `{slug}/{path}` with no lifecycle folder and no `projects/`
    prefix. `in_table` escapes the alias separator, which a markdown table cell
    needs and nothing else does.
    """
    if not isinstance(target_rel, str) or not target_rel.strip():
        raise ValueError("link target must be a non-empty string")
    target = target_rel.strip().replace("\\", "/").strip("/")
    if target.endswith(".md"):
        target = target[:-3]
    head = target.split("/", 1)[0]
    if head == "projects":
        raise ValueError(
            f"link target {target_rel!r} carries the projects/ prefix; "
            "targets start at the project slug")
    if head in _LIFECYCLE_FOLDERS:
        raise ValueError(
            f"link target {target_rel!r} names the lifecycle folder {head!r}; "
            "a link that carries it breaks the moment the project moves")
    if alias is None:
        return f"[[{target}]]"
    if not isinstance(alias, str) or "|" in alias or "]]" in alias:
        raise ValueError(f"alias {alias!r} would truncate the link")
    sep = "\\|" if in_table else "|"
    return f"[[{target}{sep}{alias}]]"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd adjudant/scripts && python3 -m unittest test__place -v`
Expected: PASS, 21 tests

- [ ] **Step 5: Add the validator that keeps the two zone lists in step**

`_place.py` duplicates the four folder names so a degraded hook can import it
without `_vault_walk`. Two copies drift. Add to `adjudant/scripts/validate.py`,
beside the other validators:

```python
def check_place_zone_parity(r: "Result") -> None:
    """36. place-zone-parity — _place's lifecycle folder set matches _vault_walk.

    _place.py duplicates the four folder names on purpose: a hook in degraded
    mode imports it without _vault_walk. Every duplicate drifts unless
    something compares them, which is the lesson the 110-key frontmatter
    taught.
    """
    name = "place-zone-parity"
    from _place import _LIFECYCLE_FOLDERS
    if set(_LIFECYCLE_FOLDERS) != set(PROJECT_ZONES):
        r.add_fail(name, f"_place {sorted(_LIFECYCLE_FOLDERS)} vs "
                         f"_vault_walk {sorted(PROJECT_ZONES)}")
    r.add_pass(name)
```

Add `PROJECT_ZONES` to the `_vault_walk` import block at `validate.py:55-61`,
register the function in the runner list beside the other checks, add the line
`36. place-zone-parity          : _place's lifecycle folder set matches _vault_walk.PROJECT_ZONES`
to the module docstring, and bump the `N validators total.` line.

- [ ] **Step 6: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 7: Commit**

```bash
git add adjudant/scripts/_place.py adjudant/scripts/test__place.py adjudant/scripts/validate.py
git commit -m "feat(adjudant): _place - one placement decision, one link shape

Placement was a folder name typed at each call site, which is how references/
came to hold api pages, schemas, specs, component inventories and imported
wiki pages at once. Linking had three shapes and none agreed; two embedded the
lifecycle folder, so a project move broke every link into it.

link() omits the lifecycle folder and raises when a caller puts one back.
Obsidian matches the end of a path, so the shorter form is the one that stays
true across a move.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Folders are created on demand, never scaffolded

`connect.py:435-463` creates four to seven folders up front and drops an empty
`_index.md` into each. That is where the fifteen index files with a body under
25 bytes came from.

**Files:**
- Modify: `adjudant/scripts/connect.py:388-465` (`scaffold_vault_project`), `:44-53` (imports), `:768-770` (call site)
- Modify: `adjudant/scripts/_vault_walk.py:869-893` (`PROJECT_TYPE_DEFAULT_FOLDERS`, `AUTO_CREATED_FOLDERS`, `INDEX_EXEMPT_FOLDERS`, all deleted)
- Test: `adjudant/scripts/test_connect.py:219-260` (`TestScaffoldVaultProject`)

**Interfaces:**
- Consumes: `place` from Task 3.
- Produces: `scaffold_vault_project(vault_path, slug, project_type, project_name, today, initial_status="active", purpose=None, proj_dir=None) -> dict[str, list[str]]` keeps its signature and its `{"created": [...], "preserved": [...]}` return. It now creates the project directory and `brief.md`, and nothing else.

- [ ] **Step 1: Write the failing test**

Replace `TestScaffoldVaultProject` in `adjudant/scripts/test_connect.py` (lines 219-260) with:

```python
class TestScaffoldVaultProject(unittest.TestCase):
    """v3: a folder exists when something is in it. connect used to create
    four to seven folders up front and drop an empty _index.md into each,
    which produced fifteen index files with a body under 25 bytes."""

    def test_creates_the_project_dir_and_the_brief_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            scaffold_vault_project(vault, "my-slug", "coding", "My Slug", "2026-05-27")
            proj_dir = vault / "projects" / "active" / "my-slug"
            self.assertTrue((proj_dir / "brief.md").is_file())
            self.assertEqual([p.name for p in proj_dir.iterdir()], ["brief.md"])

    def test_no_index_file_is_written_anywhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            scaffold_vault_project(vault, "p", "plugin", "P", "2026-05-27")
            self.assertEqual(list(vault.rglob("_index.md")), [])

    def test_new_projects_land_in_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            scaffold_vault_project(vault, "p", "coding", "P", "2026-05-27")
            self.assertTrue((vault / "projects" / "active" / "p" / "brief.md").is_file())
            self.assertFalse((vault / "projects" / "p").exists())

    def test_brief_has_slug_and_date_substituted(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            scaffold_vault_project(vault, "abc", "coding", "Abc Project", "2026-05-27")
            brief = (vault / "projects" / "active" / "abc" / "brief.md").read_text()
            self.assertIn("2026-05-27", brief)
            self.assertIn("# Abc Project", brief)
            self.assertNotIn("{kebab-slug}", brief)
            self.assertNotIn("{YYYY-MM-DD}", brief)

    def test_idempotent_preserves_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            scaffold_vault_project(vault, "abc", "coding", "Abc", "2026-05-27")
            brief_path = vault / "projects" / "active" / "abc" / "brief.md"
            brief_path.write_text("USER EDITED")
            scaffold_vault_project(vault, "abc", "coding", "Abc 2", "2026-05-28")
            self.assertEqual(brief_path.read_text(), "USER EDITED")

    def test_reconnect_fills_no_folders_into_a_paused_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            proj_dir = vault / "projects" / "paused" / "p"
            scaffold_vault_project(vault, "p", "coding", "P", "2026-05-27",
                                   proj_dir=proj_dir)
            self.assertEqual([x.name for x in proj_dir.iterdir()], ["brief.md"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_connect.TestScaffoldVaultProject -v`
Expected: FAIL — the project lands at `projects/my-slug` and carries six folders.

- [ ] **Step 3: Strip the scaffold**

In `adjudant/scripts/connect.py`, replace the default-path line at `:407-408`:

```python
    if proj_dir is None:
        proj_dir = vault_path / "projects" / slug
```

with:

```python
    if proj_dir is None:
        # New projects land in active/. A project moves out of it through the
        # guided triage in `status`, never through a scaffold.
        proj_dir = vault_path / "projects" / "active" / slug
```

Delete lines 435-463 in full — the `# Subfolders + per-folder indexes` comment
through `created.append(f"{sub}/_index.md")` — and replace them with:

```python
    # v3: no subfolders and no indexes. A folder exists when something is in
    # it; `_place.place()` creates the one it needs at write time. connect
    # used to make four to seven folders and drop an empty `_index.md` into
    # each, which is where the fifteen indexes with a body under 25 bytes
    # came from — and a scratchpad project got six folders it never used.
```

Remove `INDEX_EXEMPT_FOLDERS` and `PROJECT_TYPE_DEFAULT_FOLDERS` from the
`_vault_walk` import block at `connect.py:44-53`.

- [ ] **Step 4: Delete the folder-default constants**

Delete `adjudant/scripts/_vault_walk.py:869-893` — `PROJECT_TYPE_DEFAULT_FOLDERS`,
`AUTO_CREATED_FOLDERS` and `INDEX_EXEMPT_FOLDERS` together, plus the comment
above the first. Replace with:

```python
# PROJECT_TYPE_DEFAULT_FOLDERS, AUTO_CREATED_FOLDERS and INDEX_EXEMPT_FOLDERS
# were deleted in v3. Folder layout is now one table, KIND_FOLDER in
# _place.py, and a folder is created by the write that puts something in it.
# The three constants existed to answer "which folders does a coding project
# get" and "which of them skip an index" — questions that only had answers
# because connect scaffolded folders nobody had asked for.
```

Fix the remaining importers: `grep -rn "PROJECT_TYPE_DEFAULT_FOLDERS\|AUTO_CREATED_FOLDERS\|INDEX_EXEMPT_FOLDERS" adjudant/` and delete each use. In `clean.py` (plan 3's merge of `tidy.py` and `ramasse_scan.py`) the folder-drift detector `detect_folder_drift`, inherited from `ramasse_scan.py:104`, compares a project's folders against the per-type default; delete that detector, its report key, and its tests, because with no default there is no drift to detect.

- [ ] **Step 5: Run the connect tests**

Run: `cd adjudant/scripts && python3 -m unittest test_connect -v 2>&1 | tail -5`
Expected: `OK`. Tests asserting the old scaffold behaviour fail; delete them, naming them in the commit. `test_plugin_project_includes_releases` and `test_coding_project_creates_default_folders` are the two that assert the defect directly.

- [ ] **Step 6: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 7: Commit**

```bash
git add adjudant/scripts/connect.py adjudant/scripts/_vault_walk.py adjudant/scripts/clean.py adjudant/scripts/test_connect.py adjudant/scripts/test_clean.py
git commit -m "feat(adjudant): folders are created on demand, never scaffolded

connect made four to seven folders per project and dropped an empty _index.md
into each. Fifteen index files in the real vault have a body under 25 bytes,
and a scratchpad project carried six folders it never used.

A folder now exists because a write put something in it. New projects land in
projects/active/.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Wikilinks resolve by path, never by bare stem

`build_vault_index` at `_vault_walk.py:417-438` adds four keys per file,
including the bare stem, and `resolve_wikilink` at `:441-461` accepts a basename
match anywhere in the vault. That is why a link can "resolve" to a file in an
unrelated project, and why the 733 broken links were never trustworthy either
way.

**Files:**
- Modify: `adjudant/scripts/_vault_walk.py:417-461` (`build_vault_index`, `resolve_wikilink`), `:14-20` (the module docstring's function list)
- Modify: `adjudant/hooks/scripts/posttooluse-vault-log.py` (the Job 1 link line)
- Test: `adjudant/scripts/test__vault_walk.py:301-325` (`TestVaultIndex`), `adjudant/scripts/test_posttooluse_vault_log.py`

**Interfaces:**
- Consumes: `link`, `project_rel` from Task 3.
- Produces: `build_vault_index(vault_root: Path) -> set[str]` and `resolve_wikilink(target: str, index: set[str]) -> bool` keep their signatures. The index now holds, per file: the vault-relative path with and without extension, and — for a file under `projects/{zone}/{slug}/` — the same two with the `projects/{zone}/` prefix stripped. Nothing else.

- [ ] **Step 1: Write the failing test**

Replace `TestVaultIndex` in `adjudant/scripts/test__vault_walk.py` (lines 301-325) with:

```python
class TestVaultIndex(unittest.TestCase):

    def _vault(self, tmp: Path) -> Path:
        vault = tmp / "v"
        p = vault / "projects" / "active" / "demo" / "decisions"
        p.mkdir(parents=True)
        (p / "2026-08-12-branch-track.md").write_text("# d")
        (vault / "projects" / "active" / "demo" / "brief.md").write_text("# b")
        return vault

    def test_the_zone_less_form_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            idx = build_vault_index(self._vault(Path(tmp)))
            self.assertTrue(resolve_wikilink(
                "demo/decisions/2026-08-12-branch-track", idx))
            self.assertTrue(resolve_wikilink(
                "demo/decisions/2026-08-12-branch-track.md", idx))
            self.assertTrue(resolve_wikilink("demo/brief", idx))

    def test_the_full_vault_path_still_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            idx = build_vault_index(self._vault(Path(tmp)))
            self.assertTrue(resolve_wikilink(
                "projects/active/demo/brief", idx))
            self.assertTrue(resolve_wikilink(
                "projects/active/demo/brief.md", idx))

    def test_a_bare_stem_no_longer_resolves(self):
        # Obsidian's default resolution matches any `brief.md` anywhere. In a
        # vault with 27 projects that is 27 files answering to one name, and
        # adjudant reported such a link as healthy.
        with tempfile.TemporaryDirectory() as tmp:
            idx = build_vault_index(self._vault(Path(tmp)))
            self.assertFalse(resolve_wikilink("brief", idx))
            self.assertFalse(resolve_wikilink("brief.md", idx))
            self.assertFalse(resolve_wikilink("2026-08-12-branch-track", idx))

    def test_a_wrong_project_does_not_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            idx = build_vault_index(self._vault(Path(tmp)))
            self.assertFalse(resolve_wikilink("other/brief", idx))

    def test_non_existent(self):
        with tempfile.TemporaryDirectory() as tmp:
            idx = build_vault_index(self._vault(Path(tmp)))
            self.assertFalse(resolve_wikilink("does/not/exist", idx))

    def test_canvas_and_base_indexed_by_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "v"
            (vault / "projects" / "active" / "demo" / "canvases").mkdir(parents=True)
            (vault / "projects" / "active" / "demo" / "canvases" / "art.canvas").write_text("{}")
            idx = build_vault_index(vault)
            self.assertTrue(resolve_wikilink("demo/canvases/art.canvas", idx))
            self.assertTrue(resolve_wikilink("demo/canvases/art", idx))
            self.assertFalse(resolve_wikilink("art", idx))

    def test_a_vault_root_file_resolves_by_its_own_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "v"
            vault.mkdir()
            (vault / "Home.md").write_text("# h")
            idx = build_vault_index(vault)
            self.assertTrue(resolve_wikilink("Home", idx))
            self.assertTrue(resolve_wikilink("Home.md", idx))
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestVaultIndex -v`
Expected: FAIL on `test_a_bare_stem_no_longer_resolves` — `resolve_wikilink("brief", idx)` is True.

- [ ] **Step 3: Rewrite the index and the resolver**

Replace `adjudant/scripts/_vault_walk.py:417-461` with:

```python
def build_vault_index(vault_root: Path) -> set[str]:
    """Every resolvable wikilink target form across the vault.

    Per file, exactly two or four forms:
      - the vault-relative path, with and without its extension
      - for a file under `projects/{zone}/{slug}/`, the same two with the
        `projects/{zone}/` prefix stripped, which is the form adjudant writes

    The bare basename is NOT indexed. Obsidian's default resolution matches
    `[[brief]]` against any `brief.md` in the vault; with 27 projects that is
    27 files answering to one name, and adjudant reported every one of those
    links as healthy while a reader following it landed somewhere arbitrary.
    A link that does not say which project it means is a broken link with a
    good disguise.

    Spans .md, .canvas, .base.
    """
    index: set[str] = set()
    zones = set(PROJECT_ZONES) | (set(LEGACY_ZONES) - {""})
    for ext in ("md", "canvas", "base"):
        for f in vault_root.rglob(f"*.{ext}"):
            try:
                rel = f.relative_to(vault_root)
            except ValueError:
                continue
            forms = [rel.as_posix()]
            parts = rel.parts
            # projects/{zone}/{slug}/... -> {slug}/...
            if len(parts) > 3 and parts[0] == "projects" and parts[1] in zones:
                forms.append("/".join(parts[2:]))
            # projects/{slug}/... (pre-v3, no lifecycle folder) -> {slug}/...
            elif len(parts) > 2 and parts[0] == "projects":
                forms.append("/".join(parts[1:]))
            for s in forms:
                index.add(s)
                index.add(s[: -(len(ext) + 1)])  # strip `.ext`
    return index


def resolve_wikilink(target: str, index: set[str]) -> bool:
    """True if target resolves in the vault index.

    Tries the target as written, then with `.md` appended. There is no
    basename fallback: see build_vault_index.
    """
    if not target:
        return False
    cleaned = target.replace("\\", "/").strip().strip("/")
    if not cleaned:
        return False
    return cleaned in index or (cleaned + ".md") in index
```

Update the module docstring's function list at `_vault_walk.py:17-18` to read:

```python
    build_vault_index(vault_root) -> set[str]   # path forms only, no bare stems
    resolve_wikilink(target, index) -> bool
```

- [ ] **Step 4: Run the index tests**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestVaultIndex -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Route the session-log hook through `link()`**

Plan 1 already changed this hook's link to `[[{slug}/{'/'.join(parts)}]]`, built
by hand. Replace that line in `adjudant/hooks/scripts/posttooluse-vault-log.py`'s
Job 1 block with a call into `_place`, keeping the hook's never-fail contract:

```python
    is_decision = parts[0] == "decisions"
    label = "Decision" if is_decision else "Added"
    try:
        from _place import link as _link
        entry = _link(f"{slug}/{'/'.join(parts)}")
    except Exception:
        # Degraded mode: _place is unimportable, or the path shape is one it
        # refuses. Write the bare target rather than nothing — the hook must
        # not fail, and a target with no brackets is visibly not a link.
        entry = f"{slug}/{'/'.join(parts)}"
```

and use `entry` where the old `link` local was used in the append. Rename the
local so it no longer shadows the imported function.

- [ ] **Step 6: Repair the two stem-based callers**

`clean.py` (plan 3's merge) carries two calls that pass a bare stem to
`resolve_wikilink`, inherited from `tidy.py:191` and `ramasse_scan.py:312`.
Both now always return False, which is silently wrong rather than loudly wrong.

In `fix_wikilink_form`, the markdown-link rewriter resolves `stem` — the link's
own href — which is already a path, so it is correct as written and needs only
its docstring updated to say resolution is by path.

In the orphan detector inherited from `ramasse_scan.py:312`, delete the check
outright along with its report key and tests. The spec settles it: "Orphans are
not a note problem. An orphan is an Obsidian graph concept; an agent finds a
note by its folder path."

- [ ] **Step 7: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`. Tests that asserted a bare stem resolves must be deleted, not relaxed.

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 8: Commit**

```bash
git add adjudant/scripts/_vault_walk.py adjudant/scripts/clean.py adjudant/hooks/scripts/posttooluse-vault-log.py adjudant/scripts/test__vault_walk.py adjudant/scripts/test_clean.py adjudant/scripts/test_posttooluse_vault_log.py
git commit -m "fix(adjudant): wikilinks resolve by path, never by bare stem

build_vault_index added four keys per file including the bare stem, and
resolve_wikilink accepted a basename match anywhere in the vault. With 27
projects, [[brief]] matched 27 files and adjudant called it healthy.

The index now holds the vault-relative path and the zone-less project form,
which is the shape link() writes and the shape that survives a project move.
The orphan detector goes with it: an orphan is an Obsidian graph concept, and
an agent finds a note by its folder path.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Guided triage

Twenty-seven projects sit flat with no lifecycle grouping. `shelf` went unused
for a year because nothing ever asked. Triage asks once per project, and moves
nothing until a move is confirmed.

**Files:**
- Create: `adjudant/scripts/_lifecycle.py`
- Test: `adjudant/scripts/test__lifecycle.py`
- Modify: `adjudant/scripts/status.py` (a `--triage` report mode and a `--move` action)

**Interfaces:**
- Consumes: `PROJECT_ZONES`, `ZONE_FOR_STATUS`, `enumerate_projects_all_zones`, `zone_of`, `zone_dir`, `newest_dated_stem`, `DEFAULT_STALE_DAYS` from Task 1 and `_vault_walk`.
- Produces, used by Task 11 and Task 15:
  - `TriageEntry` — a dataclass with fields `slug: str`, `path: Path`, `zone: str`, `suggested: str`, `reason: str`, `last_session: Optional[str]`, `days_quiet: Optional[int]`.
  - `triage_plan(vault: Path, today: date, stale_after_days: int = DEFAULT_STALE_DAYS) -> list[TriageEntry]` — one entry per project, always, even when no move is suggested. Never writes.
  - `apply_move(vault: Path, slug: str, to_zone: str) -> Path` — moves one project, returns its new path. Raises `ValueError` on an unknown zone, a missing project, or an occupied destination.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test__lifecycle.py`:

```python
"""Tests for adjudant/scripts/_lifecycle.py — the guided triage.

27 projects sit flat. The verb that moved them went unused for a year because
nothing ever asked. This asks once per project and moves nothing on its own.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from _lifecycle import TriageEntry, apply_move, triage_plan


def _mk(vault: Path, slug: str, zone: str = "active", status: str = None,
        sessions=()) -> Path:
    pdir = (vault / "projects" / zone / slug) if zone else (vault / "projects" / slug)
    pdir.mkdir(parents=True, exist_ok=True)
    fm = "---\ntype: project\nupdated: 2026-09-01\n"
    if status:
        fm += f"status: {status}\n"
    (pdir / "brief.md").write_text(fm + f"---\n\n# {slug}\n")
    if sessions:
        (pdir / "sessions").mkdir(exist_ok=True)
        for d in sessions:
            (pdir / "sessions" / f"{d}.md").write_text("---\ntype: session\n---\n")
    return pdir


class TestTriagePlan(unittest.TestCase):

    def test_one_entry_per_project_and_nothing_moves(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            for i in range(27):
                _mk(vault, f"p{i:02d}", sessions=["2026-08-30"])
            before = sorted(str(p) for p in (vault / "projects").rglob("brief.md"))
            plan = triage_plan(vault, date(2026, 9, 1))
            self.assertEqual(len(plan), 27)
            after = sorted(str(p) for p in (vault / "projects").rglob("brief.md"))
            self.assertEqual(before, after, "triage moved something")

    def test_entry_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "p", sessions=["2026-08-30"])
            entry = triage_plan(vault, date(2026, 9, 1))[0]
            self.assertIsInstance(entry, TriageEntry)
            self.assertEqual(entry.slug, "p")
            self.assertEqual(entry.zone, "active")
            self.assertEqual(entry.suggested, "active")
            self.assertEqual(entry.last_session, "2026-08-30")
            self.assertEqual(entry.days_quiet, 2)

    def test_quiet_active_project_is_suggested_paused(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "p", sessions=["2026-06-01"])
            entry = triage_plan(vault, date(2026, 9, 1))[0]
            self.assertEqual(entry.suggested, "paused")
            self.assertIn("92 days", entry.reason)

    def test_boundary_at_thirty_days_suggests_paused(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "p", sessions=["2026-08-02"])
            entry = triage_plan(vault, date(2026, 9, 1))[0]
            self.assertEqual(entry.days_quiet, 30)
            self.assertEqual(entry.suggested, "paused")

    def test_a_project_with_no_sessions_gets_a_prompt_and_no_suggestion(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "p")
            entry = triage_plan(vault, date(2026, 9, 1))[0]
            self.assertIsNone(entry.days_quiet)
            self.assertEqual(entry.suggested, "active")
            self.assertIn("no session", entry.reason)

    def test_an_unmigrated_project_is_suggested_its_mapped_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "cold", zone="_fridge", status="fridge",
                sessions=["2026-08-30"])
            _mk(vault, "shipped", zone="_archive", status="done",
                sessions=["2026-08-30"])
            _mk(vault, "bare", zone="", status="active", sessions=["2026-08-30"])
            by_slug = {e.slug: e for e in triage_plan(vault, date(2026, 9, 1))}
            self.assertEqual(by_slug["cold"].suggested, "paused")
            self.assertEqual(by_slug["shipped"].suggested, "finished")
            self.assertEqual(by_slug["bare"].suggested, "active")
            for e in by_slug.values():
                self.assertIn("not in a lifecycle folder", e.reason)

    def test_a_legacy_status_outranks_the_folder_alias(self):
        # projects/{slug} with `status: done` belongs in finished/, not active/.
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "p", zone="", status="done", sessions=["2026-08-30"])
            self.assertEqual(triage_plan(vault, date(2026, 9, 1))[0].suggested,
                             "finished")

    def test_quiet_paused_and_finished_projects_are_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "a", zone="paused", sessions=["2024-01-01"])
            _mk(vault, "b", zone="finished", sessions=["2024-01-01"])
            _mk(vault, "c", zone="archive", sessions=["2024-01-01"])
            for e in triage_plan(vault, date(2026, 9, 1)):
                self.assertEqual(e.suggested, e.zone, e.slug)

    def test_sorted_by_zone_then_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "z", zone="active")
            _mk(vault, "a", zone="active")
            _mk(vault, "m", zone="archive")
            self.assertEqual([e.slug for e in triage_plan(vault, date(2026, 9, 1))],
                             ["a", "z", "m"])


class TestApplyMove(unittest.TestCase):

    def test_moves_one_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "p", sessions=["2026-06-01"])
            new = apply_move(vault, "p", "paused")
            self.assertEqual(new, vault / "projects" / "paused" / "p")
            self.assertTrue((new / "brief.md").is_file())
            self.assertFalse((vault / "projects" / "active" / "p").exists())

    def test_moves_an_unmigrated_project_into_a_named_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "p", zone="_fridge")
            new = apply_move(vault, "p", "paused")
            self.assertEqual(new, vault / "projects" / "paused" / "p")
            self.assertFalse((vault / "projects" / "_fridge" / "p").exists())

    def test_links_into_the_project_still_resolve_after_a_move(self):
        from _vault_walk import build_vault_index, resolve_wikilink
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            pdir = _mk(vault, "p")
            (pdir / "notes").mkdir()
            (pdir / "notes" / "a.md").write_text("---\ntype: note\n---\n\n# A\n")
            self.assertTrue(resolve_wikilink("p/notes/a", build_vault_index(vault)))
            apply_move(vault, "p", "archive")
            self.assertTrue(resolve_wikilink("p/notes/a", build_vault_index(vault)))

    def test_unknown_zone_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "p")
            with self.assertRaises(ValueError):
                apply_move(vault, "p", "_fridge")

    def test_missing_project_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                apply_move(Path(tmp), "nope", "paused")

    def test_occupied_destination_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "p", zone="active")
            _mk(vault, "p", zone="paused")
            with self.assertRaises(ValueError):
                apply_move(vault, "p", "paused")

    def test_a_move_to_the_current_zone_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            pdir = _mk(vault, "p", zone="paused")
            self.assertEqual(apply_move(vault, "p", "paused"), pdir)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__lifecycle -v`
Expected: FAIL with `ModuleNotFoundError: No module named '_lifecycle'`

- [ ] **Step 3: Write the implementation**

Create `adjudant/scripts/_lifecycle.py`:

```python
#!/usr/bin/env python3
"""Adjudant lifecycle — the guided triage across every project in the vault.

Lifecycle moves have no verb since v3. `shelf` existed for a year and was used
once, because nothing ever asked; a verb you have to remember to run is a verb
that does not run. `status` now offers a move when it sees one worth making,
and `connect` asks on first link.

Two functions, and the split between them is the whole design: `triage_plan`
reads and suggests, `apply_move` writes one project. Nothing moves until a
person says so, project by project. A sweep that moved 97 cards and closed
zero is the failure this shape prevents.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from _vault_walk import (
    DEFAULT_STALE_DAYS,
    PROJECT_ZONES,
    ZONE_FOR_STATUS,
    enumerate_projects_all_zones,
    newest_dated_stem,
    parse_frontmatter,
    zone_of,
)

# Folders whose occupants are there on purpose. Silence in paused/, finished/
# or archive/ is the point of those folders, so it is never a finding.
_QUIET_IS_FINE: frozenset[str] = frozenset({"paused", "finished", "archive"})


@dataclass
class TriageEntry:
    """One project, one prompt. `suggested == zone` means no move is offered."""
    slug: str
    path: Path
    zone: str
    suggested: str
    reason: str
    last_session: Optional[str]
    days_quiet: Optional[int]


def _legacy_status(project_dir: Path) -> Optional[str]:
    """A pre-v3 brief's `status:`, or None. v3 briefs carry no status field."""
    brief = project_dir / "brief.md"
    try:
        fm, _ = parse_frontmatter(brief.read_text(errors="replace"))
    except OSError:
        return None
    value = fm.fields.get("status")
    return value if isinstance(value, str) and value.strip() else None


def triage_plan(vault: Path, today: date,
                stale_after_days: int = DEFAULT_STALE_DAYS) -> list[TriageEntry]:
    """One entry per project in the vault. Reads only.

    An entry is produced for every project, including the ones with nothing to
    do, so the caller can walk the whole vault once and the operator sees the
    full list rather than a filtered one they have to trust.
    """
    today_s = today.strftime("%Y-%m-%d")
    out: list[TriageEntry] = []
    for slug, pdir, zone in enumerate_projects_all_zones(vault):
        last = newest_dated_stem(pdir / "sessions", not_after=today_s)
        days_quiet: Optional[int] = None
        if last:
            days_quiet = (today - datetime.strptime(last, "%Y-%m-%d").date()).days

        in_named_folder = pdir.parent.name in PROJECT_ZONES
        if not in_named_folder:
            status = _legacy_status(pdir)
            suggested = ZONE_FOR_STATUS.get(status or "", zone)
            reason = (f"not in a lifecycle folder; sits at "
                      f"{pdir.parent.name or 'projects'}/")
        elif zone in _QUIET_IS_FINE:
            suggested = zone
            reason = f"in {zone}/ on purpose"
        elif days_quiet is None:
            suggested = zone
            reason = "in active/ with no session recorded yet"
        elif days_quiet >= stale_after_days:
            suggested = "paused"
            reason = f"in active/ with no session for {days_quiet} days"
        else:
            suggested = zone
            reason = f"in active/, last session {days_quiet} days ago"

        out.append(TriageEntry(slug=slug, path=pdir, zone=zone,
                               suggested=suggested, reason=reason,
                               last_session=last, days_quiet=days_quiet))

    order = {z: i for i, z in enumerate(PROJECT_ZONES)}
    out.sort(key=lambda e: (order.get(e.zone, len(order)), e.slug))
    return out


def apply_move(vault: Path, slug: str, to_zone: str) -> Path:
    """Move one project into `to_zone`. Returns its new path.

    Refuses an unknown folder, a project it cannot find, and an occupied
    destination. Links into the project keep resolving because they never
    carried the lifecycle folder — that is the whole reason the link form
    changed first.
    """
    if to_zone not in PROJECT_ZONES:
        raise ValueError(
            f"unknown lifecycle folder {to_zone!r}; one of "
            f"{', '.join(PROJECT_ZONES)}")
    src: Optional[Path] = None
    for found_slug, pdir, _zone in enumerate_projects_all_zones(vault):
        if found_slug == slug:
            src = pdir
            break
    if src is None:
        raise ValueError(f"no project {slug!r} in {vault}")
    dest = vault / "projects" / to_zone / slug
    if src.resolve() == dest.resolve():
        return src
    if dest.exists():
        raise ValueError(
            f"{dest} already exists; two projects share the slug {slug!r}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    return dest
```

- [ ] **Step 4: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test__lifecycle -v`
Expected: PASS, 15 tests

- [ ] **Step 5: Wire triage into `status`**

In `adjudant/scripts/status.py` (plan 3's descendant of `check.py`), add two
arguments beside the existing `--project-dir` and `--vault-dir`:

```python
    parser.add_argument("--triage", action="store_true",
                        help="Print one lifecycle prompt per project in the vault "
                             "(JSON). Read-only: moves nothing.")
    parser.add_argument("--move", nargs=2, metavar=("SLUG", "ZONE"),
                        help="Move one project into a lifecycle folder "
                             "(active|paused|finished|archive). One project per "
                             "call, only after the operator confirms.")
```

Immediately after `args = parser.parse_args(argv)`, add:

```python
    if args.triage or args.move:
        try:
            vault = resolve_vault(Path(args.project_dir).expanduser(),
                                  os.environ.get("OB_VAULT"))
        except VaultUnresolvableError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        if vault is None:
            print("error: no vault resolved", file=sys.stderr)
            return 1
        if args.move:
            slug, zone = args.move
            try:
                dest = apply_move(vault, slug, zone)
            except ValueError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1
            print(json.dumps({"moved": slug, "to": zone, "path": str(dest)}))
            return 0
        plan = triage_plan(vault, date.today())
        print(json.dumps({"triage": [
            {"slug": e.slug, "zone": e.zone, "suggested": e.suggested,
             "reason": e.reason, "last_session": e.last_session,
             "days_quiet": e.days_quiet, "move": e.suggested != e.zone}
            for e in plan]}, indent=2))
        return 0
```

Add `from _lifecycle import apply_move, triage_plan` and `import os` to that
module's imports if absent.

- [ ] **Step 6: Write the failing test for the CLI surface**

Append to `adjudant/scripts/test_status.py`:

```python
class TestTriageCli(unittest.TestCase):

    def _vault(self, tmp: Path) -> tuple:
        vault = tmp / "vault"
        for slug, zone, sess in (("a", "active", "2026-08-30"),
                                 ("b", "active", "2025-01-01")):
            pdir = vault / "projects" / zone / slug
            (pdir / "sessions").mkdir(parents=True)
            (pdir / "brief.md").write_text(
                "---\ntype: project\nupdated: 2026-09-01\n---\n\n# x\n")
            (pdir / "sessions" / f"{sess}.md").write_text("---\ntype: session\n---\n")
        code = tmp / "code"
        (code / ".claude").mkdir(parents=True)
        (code / ".claude" / "adjudant").write_text(
            f"vault_path: {vault}\nvault_name: vault\nslug: a\nmode: project\n")
        return vault, code

    def test_triage_lists_every_project_and_moves_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault, code = self._vault(Path(tmp))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = status_cli(["--project-dir", str(code), "--triage"])
            self.assertEqual(rc, 0)
            rows = _json.loads(out.getvalue())["triage"]
            self.assertEqual([r["slug"] for r in rows], ["a", "b"])
            self.assertFalse(rows[0]["move"])
            self.assertTrue(rows[1]["move"])
            self.assertEqual(rows[1]["suggested"], "paused")
            self.assertTrue((vault / "projects" / "active" / "b").is_dir())

    def test_move_moves_exactly_one_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault, code = self._vault(Path(tmp))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = status_cli(["--project-dir", str(code), "--move", "b", "paused"])
            self.assertEqual(rc, 0)
            self.assertTrue((vault / "projects" / "paused" / "b").is_dir())
            self.assertTrue((vault / "projects" / "active" / "a").is_dir())

    def test_move_to_a_bad_zone_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            _vault, code = self._vault(Path(tmp))
            with contextlib.redirect_stderr(io.StringIO()):
                rc = status_cli(["--project-dir", str(code), "--move", "b", "_fridge"])
            self.assertEqual(rc, 1)
```

`test_status.py` inherits `test_check.py`'s imports; it already has
`contextlib`, `io`, `json as _json`, `tempfile` and `Path`, and imports the CLI
entry point as `status_cli`.

- [ ] **Step 7: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test__lifecycle test_status -v 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 8: Document the triage in the status reference**

In `adjudant/skills/adjudant/reference/`, the doc plan 3 wrote for `status` gains
a `## Lifecycle triage` section stating the contract in four lines: `--triage`
prints one prompt per project and moves nothing; the model asks per project;
each confirmed move is one `--move SLUG ZONE` call; a project in `active/` with
no session for 30 days is the prompt that makes triage happen at all.

- [ ] **Step 9: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 10: Commit**

```bash
git add adjudant/scripts/_lifecycle.py adjudant/scripts/test__lifecycle.py adjudant/scripts/status.py adjudant/scripts/test_status.py adjudant/skills/adjudant/reference/
git commit -m "feat(adjudant): guided lifecycle triage, one prompt per project

triage_plan reads and suggests; apply_move writes one project. Nothing moves
until a person confirms it, project by project. The verb that used to do this
was invoked once in a year, because nothing ever asked.

A project in active/ with no session for 30 days is the prompt that makes
triage happen instead of never happening.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Generate `Home.md` and `{slug}/_index.md`

Two surfaces survive, both generated. Home carries 39 project links against 27
projects; `projects/_index.md` has 28 rows with two duplicated and malformed
table pipes. Only 4 of 27 projects have a contents page.

**Files:**
- Create: `adjudant/scripts/_index_gen.py`
- Test: `adjudant/scripts/test__index_gen.py`

**Interfaces:**
- Consumes: `link` from Task 3; `enumerate_projects_all_zones`, `zone_of`, `newest_dated_stem`, `parse_frontmatter`, `PROJECT_ZONES` from Tasks 1 and `_vault_walk`.
- Produces, used by Task 8 and Task 15:
  - `render_home(vault: Path, today: date) -> str`
  - `write_home(vault: Path, today: date) -> Path`
  - `render_project_index(project_dir: Path, today: date) -> str`
  - `write_project_index(project_dir: Path, today: date) -> Path`

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test__index_gen.py`:

```python
"""Tests for adjudant/scripts/_index_gen.py — the two generated surfaces.

Home carries 39 project links against 27 projects. projects/_index.md has 28
rows, two of them duplicated, with malformed table pipes. Both were
hand-maintained, and a hand-maintained list of a directory is stale the moment
anything changes.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from _index_gen import (
    render_home,
    render_project_index,
    write_home,
    write_project_index,
)
from _vault_walk import build_vault_index, parse_frontmatter, resolve_wikilink


def _mk(vault: Path, slug: str, zone: str = "active", sessions=()) -> Path:
    pdir = vault / "projects" / zone / slug
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "brief.md").write_text(
        "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-08-13\n---\n\n"
        f"# {slug.title()}\n\nWhat this project is.\n")
    if sessions:
        (pdir / "sessions").mkdir(exist_ok=True)
        for d in sessions:
            (pdir / "sessions" / f"{d}.md").write_text("---\ntype: session\n---\n")
    return pdir


class TestHome(unittest.TestCase):

    def test_grouped_by_lifecycle_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "alpha", "active", ["2026-08-30"])
            _mk(vault, "beta", "paused", ["2026-01-02"])
            _mk(vault, "gamma", "finished")
            text = render_home(vault, date(2026, 9, 1))
            self.assertIn("## Active", text)
            self.assertIn("## Paused", text)
            self.assertIn("## Finished", text)
            self.assertNotIn("## Archive", text,
                             "an empty lifecycle folder gets no heading")
            self.assertLess(text.index("## Active"), text.index("## Paused"))

    def test_one_row_per_project_with_its_last_active_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "alpha", "active", ["2026-08-30"])
            text = render_home(vault, date(2026, 9, 1))
            self.assertEqual(text.count("[[alpha/brief"), 1)
            self.assertIn("2026-08-30", text)

    def test_a_project_with_no_sessions_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "alpha", "active")
            self.assertIn("never", render_home(vault, date(2026, 9, 1)))

    def test_links_omit_the_lifecycle_folder_and_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "alpha", "paused", ["2026-08-30"])
            text = render_home(vault, date(2026, 9, 1))
            self.assertNotIn("projects/", text)
            self.assertNotIn("[[paused/", text)
            self.assertTrue(resolve_wikilink("alpha/brief", build_vault_index(vault)))

    def test_home_keeps_the_type_the_resolver_looks_for(self):
        # _vault_walk resolves a vault by finding Home.md with type: vault-home.
        # Writing any other type would make the vault unresolvable.
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "alpha", "active")
            fm, _ = parse_frontmatter(render_home(vault, date(2026, 9, 1)))
            self.assertEqual(fm.fields["type"], "vault-home")
            self.assertEqual(fm.fields["updated"], "2026-09-01")

    def test_write_home_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk(vault, "alpha", "active", ["2026-08-30"])
            p1 = write_home(vault, date(2026, 9, 1))
            first = p1.read_text()
            p2 = write_home(vault, date(2026, 9, 1))
            self.assertEqual(p1, p2)
            self.assertEqual(p1, vault / "Home.md")
            self.assertEqual(first, p2.read_text())

    def test_an_empty_vault_renders(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "projects").mkdir()
            text = render_home(vault, date(2026, 9, 1))
            self.assertIn("No projects yet", text)


class TestProjectIndex(unittest.TestCase):

    def _full(self, tmp: Path) -> Path:
        pdir = _mk(tmp, "demo", "active", ["2026-08-30", "2026-08-31"])
        (pdir / "_handoff.md").write_text("---\ntype: handoff\n---\n\n# Handoff\n")
        for folder, names in (
            ("decisions", ["2026-08-12-branch-track.md"]),
            ("specs", ["spec-018-page-spinup.md"]),
            ("notes", ["cold-cache.md", "warm-cache.md"]),
        ):
            (pdir / folder).mkdir()
            for n in names:
                (pdir / folder / n).write_text(
                    f"---\ntype: {folder[:-1]}\nupdated: 2026-08-12\n---\n\n# {n}\n")
        return pdir

    def test_start_here_names_the_brief_the_handoff_and_the_newest_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._full(Path(tmp))
            text = render_project_index(pdir, date(2026, 9, 1))
            self.assertIn("## Start here", text)
            self.assertIn("[[demo/brief|", text)
            self.assertIn("[[demo/_handoff|", text)
            self.assertIn("[[demo/sessions/2026-08-31|", text)

    def test_specs_are_surfaced_near_the_top(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._full(Path(tmp))
            text = render_project_index(pdir, date(2026, 9, 1))
            self.assertIn("## Specs", text)
            self.assertIn("[[demo/specs/spec-018-page-spinup|", text)
            self.assertLess(text.index("## Specs"), text.index("## Contents"))

    def test_contents_carries_counts_and_the_newest_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._full(Path(tmp))
            text = render_project_index(pdir, date(2026, 9, 1))
            self.assertIn("| notes | 2 |", text)
            self.assertIn("| decisions | 1 |", text)
            self.assertIn("[[demo/notes/warm-cache|", text)

    def test_an_empty_folder_is_not_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._full(Path(tmp))
            (pdir / "tasks").mkdir()
            self.assertNotIn("| tasks |",
                             render_project_index(pdir, date(2026, 9, 1)))

    def test_the_index_never_lists_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._full(Path(tmp))
            write_project_index(pdir, date(2026, 9, 1))
            text = render_project_index(pdir, date(2026, 9, 1))
            self.assertNotIn("[[demo/_index", text)

    def test_a_generated_page_is_never_listed(self):
        # "Adjudant stays out of generated files": a page carrying source: is
        # rewritten by its own script every run.
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._full(Path(tmp))
            (pdir / "components").mkdir()
            (pdir / "components" / "gen.md").write_text(
                "---\ntype: component\nupdated: 2026-09-01\n"
                "source: build-module-inventory.py\n---\n\n# gen\n")
            (pdir / "components" / "hand.md").write_text(
                "---\ntype: component\nupdated: 2026-09-01\n---\n\n# hand\n")
            text = render_project_index(pdir, date(2026, 9, 1))
            self.assertIn("| components | 1 |", text)
            self.assertIn("[[demo/components/hand|", text)
            self.assertNotIn("[[demo/components/gen", text)

    def test_write_lands_at_the_project_root_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._full(Path(tmp))
            p1 = write_project_index(pdir, date(2026, 9, 1))
            self.assertEqual(p1, pdir / "_index.md")
            first = p1.read_text()
            self.assertEqual(write_project_index(pdir, date(2026, 9, 1)).read_text(),
                             first)

    def test_every_link_it_writes_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            pdir = self._full(vault)
            write_project_index(pdir, date(2026, 9, 1))
            idx = build_vault_index(vault)
            from _vault_walk import extract_wikilinks
            body = (pdir / "_index.md").read_text()
            links = extract_wikilinks(body)
            self.assertTrue(links)
            for wl in links:
                self.assertTrue(resolve_wikilink(wl.target, idx), wl.target)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__index_gen -v`
Expected: FAIL with `ModuleNotFoundError: No module named '_index_gen'`

- [ ] **Step 3: Write the implementation**

Create `adjudant/scripts/_index_gen.py`:

```python
#!/usr/bin/env python3
"""Adjudant index generation — the two surfaces that survive.

Folder indexes are gone, all 139 of them. For an agent they are worth nothing:
listing a directory gives the true current contents in one call, while a
markdown copy is stale the moment anything changes. 24 were already staler
than their own folder and 15 had a body under 25 bytes.

What is left is two generated files, and neither is a listing:

  Home.md            every project grouped by lifecycle folder, last active
  {slug}/_index.md   a project contents page: where to start, the specs, then
                     counts and the newest entry per folder

Both are rewritten whole from the filesystem, so neither can drift. Both link
through _place.link, so neither carries a lifecycle folder.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

from _place import link
from _vault_walk import (
    PROJECT_ZONES,
    enumerate_projects_all_zones,
    newest_dated_stem,
    parse_frontmatter,
)

# Folders the contents table lists, in reading order. A folder with nothing in
# it does not appear: an empty row is the same lie as an empty index file.
_CONTENTS_ORDER: tuple[str, ...] = (
    "sessions", "decisions", "tasks", "notes", "docs", "specs",
    "components", "api", "schemas", "sources", "releases", "dreams",
)

_ZONE_HEADING: dict[str, str] = {
    "active": "Active", "paused": "Paused",
    "finished": "Finished", "archive": "Archive",
}


def _fields(path: Path) -> dict:
    try:
        fm, _ = parse_frontmatter(path.read_text(errors="replace"))
    except OSError:
        return {}
    return fm.fields


def _is_generated(path: Path) -> bool:
    """True when another script owns this file.

    A page carrying `source:` is overwritten by its generator every run.
    Adjudant does not clean, index or nag about one — the rule that stops it
    writing an index into a directory whose own docstring says it is
    regenerated.
    """
    return bool(_fields(path).get("source"))


def _listable(folder: Path) -> list[Path]:
    """Content files in one folder: .md, not an index, not generated.

    One level deep only. 225 component pages need components/modules/ and
    components/templates/; nothing needs to go deeper, so nothing is looked
    for deeper.
    """
    if not folder.is_dir():
        return []
    out: list[Path] = []
    for f in sorted(folder.rglob("*.md")):
        rel = f.relative_to(folder)
        if len(rel.parts) > 2 or f.name.startswith("_"):
            continue
        if _is_generated(f):
            continue
        out.append(f)
    return out


def _rel(path: Path, project_dir: Path) -> str:
    parts = list(path.relative_to(project_dir).parts)
    parts[-1] = parts[-1][:-3] if parts[-1].endswith(".md") else parts[-1]
    return "/".join([project_dir.name] + parts)


def _title(path: Path) -> str:
    """The file's H1, else its stem with hyphens read as spaces."""
    try:
        _fm, body = parse_frontmatter(path.read_text(errors="replace"))
    except OSError:
        body = ""
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return path.stem.replace("-", " ")


# ============================================================
# Home.md
# ============================================================


def render_home(vault: Path, today: date) -> str:
    """Every project, grouped by lifecycle folder, with its last active date.

    `type: vault-home` is load-bearing: resolve_vault finds the vault by
    reading this file's frontmatter, so any other value makes the vault
    unresolvable from a subdirectory.
    """
    today_s = today.strftime("%Y-%m-%d")
    rows: dict[str, list[str]] = {z: [] for z in PROJECT_ZONES}
    for slug, pdir, zone in enumerate_projects_all_zones(vault):
        last = newest_dated_stem(pdir / "sessions", not_after=today_s)
        when = last or "never"
        rows.setdefault(zone, []).append(
            f"- {link(f'{slug}/brief', slug)} · last active {when}")

    parts = [
        "---",
        "type: vault-home",
        f"updated: {today_s}",
        "---",
        "",
        "# Vault",
        "",
        "Every project, grouped by lifecycle folder. This file is generated:",
        "edits are overwritten.",
        "",
    ]
    any_rows = False
    for zone in PROJECT_ZONES:
        if not rows.get(zone):
            continue
        any_rows = True
        parts.append(f"## {_ZONE_HEADING[zone]}")
        parts.append("")
        parts.extend(sorted(rows[zone]))
        parts.append("")
    if not any_rows:
        parts.append("No projects yet. Run `/adjudant connect` to link one.")
        parts.append("")
    return "\n".join(parts)


def write_home(vault: Path, today: date) -> Path:
    """Rewrite `{vault}/Home.md` whole. Returns its path."""
    path = vault / "Home.md"
    path.write_text(render_home(vault, today))
    return path


# ============================================================
# {slug}/_index.md
# ============================================================


def render_project_index(project_dir: Path, today: date) -> str:
    """A project's contents page: a synthesis, not a listing.

    Start here, then specs as onboarding context, then per-folder counts with
    the newest entry. Two of the four hand-written examples in the real vault
    are genuinely good documents, which says the surface is worth having and
    too much work to keep by hand.
    """
    slug = project_dir.name
    today_s = today.strftime("%Y-%m-%d")
    parts = [
        "---",
        "type: index",
        f"updated: {today_s}",
        "---",
        "",
        f"# {slug}",
        "",
        "Generated contents page. Edits are overwritten.",
        "",
        "## Start here",
        "",
    ]

    start_rows: list[str] = []
    if (project_dir / "brief.md").is_file():
        start_rows.append(
            f"- {link(f'{slug}/brief', 'brief')} · what this project is")
    if (project_dir / "_handoff.md").is_file():
        start_rows.append(
            f"- {link(f'{slug}/_handoff', 'handoff')} · where it was left")
    newest_session = newest_dated_stem(project_dir / "sessions", not_after=today_s)
    if newest_session:
        start_rows.append(
            f"- {link(f'{slug}/sessions/{newest_session}', newest_session)} "
            "· newest session")
    parts.extend(start_rows or ["- Nothing recorded yet."])
    parts.append("")

    specs = _listable(project_dir / "specs")
    if specs:
        parts.append("## Specs")
        parts.append("")
        for f in specs:
            status = _fields(f).get("status") or "unstated"
            parts.append(
                f"- {link(_rel(f, project_dir), _title(f))} · {status}")
        parts.append("")

    body_rows: list[str] = []
    for folder in _CONTENTS_ORDER:
        files = _listable(project_dir / folder)
        if not files:
            continue
        newest = max(files, key=lambda p: p.name)
        body_rows.append(
            f"| {folder} | {len(files)} | "
            f"{link(_rel(newest, project_dir), _title(newest), in_table=True)} |")
    if body_rows:
        parts.append("## Contents")
        parts.append("")
        parts.append("| Folder | Files | Newest |")
        parts.append("|---|---|---|")
        parts.extend(body_rows)
        parts.append("")
    return "\n".join(parts)


def write_project_index(project_dir: Path, today: date) -> Path:
    """Rewrite `{project}/_index.md` whole. Returns its path."""
    path = project_dir / "_index.md"
    path.write_text(render_project_index(project_dir, today))
    return path
```

- [ ] **Step 4: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test__index_gen -v`
Expected: PASS, 15 tests

- [ ] **Step 5: Run the full suite**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add adjudant/scripts/_index_gen.py adjudant/scripts/test__index_gen.py
git commit -m "feat(adjudant): generate Home.md and {slug}/_index.md

Two surfaces, both rewritten whole from the filesystem, so neither can drift.
Home groups every project by lifecycle folder with its last active date; the
project index is a synthesis - where to start, the specs, then counts and the
newest entry per folder.

Home keeps type: vault-home, which resolve_vault reads to find the vault at
all. Every link goes through _place.link, so none carries a lifecycle folder.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Delete every other index file, and the code that wrote them

141 index files exist. Two surfaces survive. The other 113 go, along with every
writer that made one.

**Files:**
- Modify: `adjudant/scripts/clean.py` (`generate_index_content`, `upsert_index_content`, `_format_entry_bullet`, `harvest_aliases`, `_find_entries_section_in_body`, `_section_is_bullet_list`, `_capitalize_folder_name`, `_sort_entries` and feature 1 of `build_preview` — all deleted; inherited from `tidy.py:212-403` and `:586-647`)
- Modify: `adjudant/scripts/connect.py:632-680` (`upsert_projects_index_row`, deleted), `:783-796` (its call site)
- Delete: `adjudant/skills/adjudant/templates/_index-collection.md`, `adjudant/skills/adjudant/templates/_index-projects.md`
- Modify: `adjudant/skills/adjudant/templates/home.md`
- Test: `adjudant/scripts/test_clean.py`, `adjudant/scripts/test_connect.py:320-469`, `adjudant/scripts/test__index_gen.py`

**Interfaces:**
- Consumes: `write_home`, `write_project_index` from Task 7.
- Produces: `prune_index_files(vault: Path) -> list[Path]` in `_index_gen`, returning the paths it deleted, newest surface preserved. `regenerate(vault: Path, today: date) -> dict` in `_index_gen`, writing `Home.md` and every `{slug}/_index.md` and returning `{"home": str, "projects": [str], "deleted": [str]}`.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test__index_gen.py`:

```python
class TestPruneAndRegenerate(unittest.TestCase):

    def _vault(self, tmp: Path) -> Path:
        vault = tmp / "v"
        pdir = _mk(vault, "demo", "active", ["2026-08-30"])
        for folder in ("decisions", "notes", "tasks"):
            (pdir / folder).mkdir()
            (pdir / folder / "_index.md").write_text(
                "---\ntype: index\n---\n\n# X\n\n## Entries\n")
            (pdir / folder / "real.md").write_text(
                "---\ntype: note\nupdated: 2026-08-01\n---\n\n# real\n")
        (pdir / "_index.md").write_text("hand written, will be overwritten")
        (vault / "projects" / "_index.md").write_text(
            "---\ntype: index\n---\n\n# All Projects\n")
        return vault

    def test_prune_removes_folder_indexes_and_the_projects_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(Path(tmp))
            deleted = prune_index_files(vault)
            names = sorted(str(p.relative_to(vault)) for p in deleted)
            self.assertEqual(len(names), 4)
            self.assertIn("projects/_index.md", names)
            for folder in ("decisions", "notes", "tasks"):
                self.assertIn(f"projects/active/demo/{folder}/_index.md", names)

    def test_prune_keeps_the_project_contents_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(Path(tmp))
            prune_index_files(vault)
            self.assertTrue(
                (vault / "projects" / "active" / "demo" / "_index.md").is_file())

    def test_prune_keeps_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(Path(tmp))
            (vault / "Home.md").write_text("---\ntype: vault-home\n---\n# Vault\n")
            prune_index_files(vault)
            self.assertTrue((vault / "Home.md").is_file())

    def test_prune_touches_no_content_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(Path(tmp))
            prune_index_files(vault)
            self.assertEqual(
                len(list((vault / "projects").rglob("real.md"))), 3)

    def test_prune_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(Path(tmp))
            prune_index_files(vault)
            self.assertEqual(prune_index_files(vault), [])

    def test_regenerate_writes_both_surfaces_and_prunes(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(Path(tmp))
            out = regenerate(vault, date(2026, 9, 1))
            self.assertEqual(out["home"], str(vault / "Home.md"))
            self.assertEqual(
                out["projects"],
                [str(vault / "projects" / "active" / "demo" / "_index.md")])
            self.assertEqual(len(out["deleted"]), 4)
            survivors = sorted(
                str(p.relative_to(vault)) for p in vault.rglob("_index.md"))
            self.assertEqual(survivors, ["projects/active/demo/_index.md"])
```

Add `prune_index_files` and `regenerate` to the `_index_gen` import block at the
top of the file.

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__index_gen.TestPruneAndRegenerate -v`
Expected: FAIL with `ImportError: cannot import name 'prune_index_files' from '_index_gen'`

- [ ] **Step 3: Add the pruner and the regenerator**

Append to `adjudant/scripts/_index_gen.py`:

```python
# ============================================================
# Retiring the other 139
# ============================================================


def prune_index_files(vault: Path) -> list[Path]:
    """Delete every `_index.md` that is not a project contents page.

    139 folder indexes existed. For an agent they are worth nothing: a
    directory listing is the true current contents, a markdown copy is stale
    the moment anything changes, 24 were already staler than their own folder
    and 15 had a body under 25 bytes. `projects/_index.md` goes with them:
    Home groups by lifecycle folder now, and a second list of the same
    projects adds nothing but a second thing to disagree.

    Returns what it deleted, so a caller can report it.
    """
    keep = {pdir / "_index.md"
            for _slug, pdir, _zone in enumerate_projects_all_zones(vault)}
    deleted: list[Path] = []
    base = vault / "projects"
    if not base.is_dir():
        return deleted
    for f in sorted(base.rglob("_index.md")):
        if f in keep:
            continue
        try:
            f.unlink()
        except OSError:
            continue
        deleted.append(f)
    return deleted


def regenerate(vault: Path, today: date) -> dict:
    """Rewrite both surfaces and retire every other index. Returns a receipt."""
    deleted = prune_index_files(vault)
    projects = [str(write_project_index(pdir, today))
                for _slug, pdir, _zone in enumerate_projects_all_zones(vault)]
    return {
        "home": str(write_home(vault, today)),
        "projects": projects,
        "deleted": [str(p) for p in deleted],
    }
```

- [ ] **Step 4: Run the new tests**

Run: `cd adjudant/scripts && python3 -m unittest test__index_gen -v`
Expected: PASS, 21 tests

- [ ] **Step 5: Delete every index writer**

In `adjudant/scripts/clean.py`, delete the whole index-regeneration section
inherited from `tidy.py:212-403`: `_capitalize_folder_name`, `_sort_entries`,
`harvest_aliases`, `_format_entry_bullet`, `generate_index_content`,
`_find_entries_section_in_body`, `_section_is_bullet_list` and
`upsert_index_content`. Delete feature 1 of `build_preview` — the `index_proposals`
declaration, the `by_parent` grouping and the whole index loop, inherited from
`tidy.py:586-647` and ending at the `# --- Features 2-5: per-file edits ---`
comment — along with the `index_proposals` key in the change-set,
its rendering in the preview summary, and its branch in `apply_preview`.
Replace the section header comment with:

```python
# Index regeneration lived here. It is gone: `clean` never creates a vault
# file, and the only two index surfaces left are generated whole by
# _index_gen from the filesystem. An index that is upserted in place is an
# index that can be stale, which 24 of 139 already were.
```

In `adjudant/scripts/connect.py`, delete `upsert_projects_index_row`
(`:632-680`), and the block above it holding `_CANONICAL_INDEX_HEADER_RE`,
`_TABLE_SEPARATOR_RE` and `_canonical_table_body` (`:598-629`, starting at the
comment `# The canonical 6-column projects-index header`), and the Step 6 block
at `:783-796` that calls it. Replace the Step 6 block with:

```python
    # Step 6 wrote a row into projects/_index.md. That file is retired: Home
    # groups every project by lifecycle folder and is generated whole, so a
    # hand-upserted second list could only disagree with it. 28 rows, two
    # duplicated, with malformed table pipes, is what it disagreed by.
```

Delete `count_non_index_files`, `newest_session_date` and `parse_frontmatter`
from `connect.py` if the deletion leaves them with no caller; run
`grep -n "count_non_index_files\|newest_session_date" adjudant/scripts/*.py`
before removing either.

- [ ] **Step 6: Retire the index templates**

```bash
git rm adjudant/skills/adjudant/templates/_index-collection.md adjudant/skills/adjudant/templates/_index-projects.md
```

Replace `adjudant/skills/adjudant/templates/home.md` in full with:

```markdown
---
type: vault-home
updated: {YYYY-MM-DD}
---

# Vault

Every project, grouped by lifecycle folder. This file is generated: edits are
overwritten.

## Active

No projects yet. Run `/adjudant connect` to link one.
```

The template is the seed for a brand-new vault only; `_index_gen.render_home`
writes every subsequent version. `type: vault-home` is load-bearing —
`_vault_walk.resolve_vault` finds the vault by reading it.

Validator 4 (`template-coverage`) asserts a template per file type.
`FILE_TYPES_REQUIRING_TEMPLATE` (at `validate.py:75` in the pre-v3 tree, where
it lists eleven types plus four project-brief variants) is rewritten by plan 2
to the fifteen kinds. Remove `index` from whatever plan 2 left, and from the
standards list: the two index surfaces are generated by code and have no
template to drift from.

- [ ] **Step 7: Run the affected tests**

Run: `cd adjudant/scripts && python3 -m unittest test_connect test_clean test__index_gen -v 2>&1 | tail -5`
Expected: `OK`. Delete the tests that asserted the deleted writers: in `test_connect.py`, `TestUpsertProjectsIndexRow` (line 320) and `TestUpsertReplacementIsConfinedToTheCanonicalTable` (line 387) in full; in `test_clean.py`, the two classes inherited from `test_tidy.py` that exercise the deleted writers: `TestUpsertIndexContent` (`test_tidy.py:244-353`) and `TestGenerateIndexContent` (`:354-390`). `harvest_aliases` has no test of its own; it was only ever reached through `upsert_index_content`. Name them in the commit.

- [ ] **Step 8: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 9: Commit**

```bash
git add -A adjudant/scripts adjudant/skills/adjudant/templates
git commit -m "feat(adjudant): retire 139 index files and every writer that made one

Two generated surfaces replace 141 hand-rotting files. 24 of 139 folder
indexes were already staler than their own folder and 15 had a body under 25
bytes. projects/_index.md goes too: Home groups by lifecycle folder, so a
second list of the same projects could only disagree - which it did, with 28
rows, two duplicated, and malformed table pipes.

clean loses its index feature entirely. connect loses its index row. An index
upserted in place is an index that can be stale.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Exempt the memory folder from schema grading

`memory/` holds Claude Code auto-memory notes, whose shape is `name`,
`description` and a nested `metadata.type`. Adjudant does not own that format
and cannot fix it. Grading it produced 69 of check's 99 failures.

**Files:**
- Modify: `adjudant/scripts/_vault_walk.py:1380-1406` (`schema_drift`), `:1268-1305` (`freshness_report`)
- Test: `adjudant/scripts/test__vault_walk.py:1684-1730` (`TestMemoryType`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `UNOWNED_FOLDERS: frozenset[str] = frozenset({"memory"})` in `_vault_walk`, used by Task 11.
  - `is_unowned(rel_path) -> bool` in `_vault_walk`, true when the first path segment is an unowned folder.
  - `schema_drift(files, aliases=None) -> dict[str, Any]` keeps its signature and gains an `"exempt"` count beside `"checked"` and `"unchecked"`.

- [ ] **Step 1: Write the failing test**

Append to `TestMemoryType` in `adjudant/scripts/test__vault_walk.py`:

```python
    def test_memory_folder_is_never_schema_graded(self):
        # 69 of check's 99 failures came from grading memory/ against a schema
        # adjudant does not own. A Claude Code auto-memory note is name /
        # description / metadata.type; Obsidian's Properties editor flattens
        # metadata.type to a top-level type:, and adjudant then read the file
        # as whatever type: claimed and proposed stripping the rest.
        from _vault_walk import schema_drift, walk_project
        with tempfile.TemporaryDirectory() as tmp:
            proot = Path(tmp)
            (proot / "memory").mkdir()
            (proot / "memory" / "flattened.md").write_text(
                "---\nname: prefers-agents-md\ndescription: a preference\n"
                "type: project\n---\n\nbody\n")
            (proot / "notes").mkdir()
            (proot / "notes" / "ours.md").write_text(
                "---\ntype: note\n---\n\nbody\n")
            report = schema_drift(list(walk_project(proot)))
            self.assertEqual(report["flagged"], 0,
                             "memory/ was graded against a schema we do not own")
            self.assertEqual(report["exempt"], 1)
            self.assertEqual(report["checked"] + report["unchecked"], 1)

    def test_memory_folder_is_never_freshness_graded(self):
        from datetime import date
        from _vault_walk import freshness_report, walk_project
        with tempfile.TemporaryDirectory() as tmp:
            proot = Path(tmp)
            (proot / "memory").mkdir()
            (proot / "memory" / "old.md").write_text(
                "---\ntype: doc\nfreshness: dated\n---\n\nbody\n")
            rep = freshness_report(list(walk_project(proot)), date(2026, 9, 1))
            self.assertEqual(rep["dated_unbounded"], [])

    def test_the_unowned_set_is_named_and_narrow(self):
        from _vault_walk import UNOWNED_FOLDERS, is_unowned
        self.assertEqual(UNOWNED_FOLDERS, frozenset({"memory"}))
        self.assertTrue(is_unowned(Path("memory/a.md")))
        self.assertTrue(is_unowned("memory/deep/a.md"))
        self.assertFalse(is_unowned(Path("notes/memory.md")))
        self.assertFalse(is_unowned(Path("MEMORY.md")))
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestMemoryType -v`
Expected: FAIL with `ImportError: cannot import name 'UNOWNED_FOLDERS' from '_vault_walk'`

- [ ] **Step 3: Add the exemption**

Insert into `adjudant/scripts/_vault_walk.py` immediately above `freshness_report`
(before line 1268):

```python
# Folders whose file format another tool owns. Adjudant reads them, walks past
# them, and never grades them. `memory/` holds Claude Code auto-memory notes,
# whose shape is name / description / metadata.type; Obsidian's Properties
# editor flattens the nested key to a top-level `type:`, and adjudant then read
# the file as whatever that claimed. Grading it produced 69 of check's 99
# failures, none of them actionable.
#
# `MEMORY.md` at the project root is NOT in here: that file is adjudant's own
# perma-memory and stays graded.
UNOWNED_FOLDERS: frozenset[str] = frozenset({"memory"})


def is_unowned(rel_path) -> bool:
    """True when a project-relative path sits under a folder we do not own."""
    parts = Path(rel_path).parts
    return bool(parts) and parts[0] in UNOWNED_FOLDERS
```

In `freshness_report` (now below the insert), add immediately after
`for vf in files:`:

```python
        if is_unowned(vf.rel_path):
            continue
```

In `schema_drift` (line 1380 before the insert), replace the loop and the
return with:

```python
def schema_drift(files: list["VaultFile"], aliases: Optional[set] = None) -> dict[str, Any]:
    """Aggregate schema drift across walked files: counts + capped samples.

    Files under UNOWNED_FOLDERS are counted as exempt and never graded.
    """
    flagged: list[dict] = []
    checked = 0
    unchecked = 0
    exempt = 0
    for vf in files:
        if is_unowned(vf.rel_path):
            exempt += 1
            continue
        fm = vf.frontmatter
        if not fm.has_block or fm.parse_error or vf.file_type not in FIELD_SCHEMA:
            unchecked += 1
            continue
        checked += 1
        d = schema_drift_for_file(vf, aliases)
        if d:
            flagged.append(d)
    return {
        "checked": checked,
        "unchecked": unchecked,
        "exempt": exempt,
        "flagged": len(flagged),
        "counts": {
            "missing_required": sum(1 for d in flagged if "missing_required" in d),
            "unknown_fields": sum(1 for d in flagged if "unknown_fields" in d),
            "status_invalid": sum(1 for d in flagged if "status_invalid" in d),
            "type_conflict": sum(1 for d in flagged if "type_conflict" in d),
            "epistemic_invalid": sum(1 for d in flagged if "epistemic_invalid" in d),
        },
        "samples": flagged[:20],
    }
```

- [ ] **Step 4: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestMemoryType -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add adjudant/scripts/_vault_walk.py adjudant/scripts/test__vault_walk.py
git commit -m "fix(adjudant): stop grading the memory folder against a schema we do not own

A Claude Code auto-memory note is name / description / metadata.type. Obsidian
flattens the nested key to a top-level type:, and adjudant then read the file
as whatever that claimed - proposing to strip name: and description: as
unknown fields. It produced 69 of check's 99 failures and not one was
actionable.

MEMORY.md at the project root stays graded: that one is ours.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: `truth.py` — the finding model, and "names something that is not there"

Check graded shape: 110 frontmatter keys against a schema, which is how it
produced 99 failures nobody acted on. The replacement checks what a file's
existence or a date comparison proves.

**Files:**
- Create: `adjudant/scripts/truth.py`
- Test: `adjudant/scripts/test_truth.py`

**Interfaces:**
- Consumes: `is_unowned` from Task 9; `walk_project`, `build_vault_index`, `resolve_wikilink`, `is_checkable_wikilink`, `_wikilink_stem`, `parse_frontmatter` from `_vault_walk`.
- Produces, used by Tasks 11, 12 and 15:
  - `BANDS: tuple[str, ...] = ("wrong-now", "going-stale", "worth-a-look")`
  - `Finding` — a dataclass with `band: str`, `kind: str`, `file: str`, `detail: str`.
  - `_Ctx` — the shared read-only context every detector takes. Fields: `project_dir: Path`, `slug: str`, `vault: Optional[Path]`, `code_root: Optional[Path]`, `today: date`, `files: list`, `all_owned: list`, `index: set`, `by_type: dict`, plus the helpers `fields(vf) -> dict` and `rel(vf) -> str`. `files` excludes generated pages; `all_owned` includes them, for the one detector that is about them.
  - `_DETECTORS: tuple` — the detector list Task 11 and Task 12 append to.
  - `truth_report(project_dir: Path, *, vault: Optional[Path] = None, code_root: Optional[Path] = None, today: Optional[date] = None) -> dict` returning `{"findings": [dict], "counts": {band: int}, "checked": int}`.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_truth.py`:

```python
"""Tests for adjudant/scripts/truth.py.

Check used to grade shape: 110 frontmatter keys against a schema, 99 failures,
69 of them in a folder adjudant does not own, and nobody acted on any of it.
Every finding here traces to a real failure in the audited vault, and every
one is settled by a file's existence or a date comparison.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from truth import BANDS, Finding, truth_report


def _w(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def _project(tmp: Path, slug: str = "demo") -> Path:
    pdir = tmp / "vault" / "projects" / "active" / slug
    _w(pdir / "brief.md",
       "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n"
       "# Demo\n\nWhat this project is.\n\n"
       "## Where things are\n| | |\n|---|---|\n")
    _w(pdir / "sessions" / "2026-09-01.md", "---\ntype: session\n---\n\n## Log\n")
    return pdir


def _kinds(report) -> list:
    return [f["kind"] for f in report["findings"]]


class TestReportShape(unittest.TestCase):

    def test_bands_are_ordered_by_cost_of_being_wrong(self):
        self.assertEqual(BANDS, ("wrong-now", "going-stale", "worth-a-look"))

    def test_a_clean_project_reports_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertEqual(report["findings"], [])
            self.assertEqual(report["counts"],
                             {"wrong-now": 0, "going-stale": 0, "worth-a-look": 0})
            self.assertGreater(report["checked"], 0)

    def test_findings_are_json_shaped_and_sorted_by_band(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "notes" / "a.md",
               "---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\n"
               "See [[demo/notes/ghost]].\n")
            _w(pdir / "docs" / "old.md",
               "---\ntype: doc\nupdated: 2026-01-01\nverified: 2026-01-01\n---\n\n"
               "# Old\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertTrue(report["findings"])
            for f in report["findings"]:
                self.assertEqual(set(f), {"band", "kind", "file", "detail"})
                self.assertIn(f["band"], BANDS)
            order = [BANDS.index(f["band"]) for f in report["findings"]]
            self.assertEqual(order, sorted(order))

    def test_the_memory_folder_is_never_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "memory" / "flat.md",
               "---\nname: x\ndescription: y\ntype: project\n---\n\n"
               "See [[nowhere-at-all]].\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertEqual(report["findings"], [])

    def test_a_generated_page_is_never_nagged_about(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "components" / "gen.md",
               "---\ntype: component\nupdated: 2026-01-01\n"
               "source: build-module-inventory.py\n---\n\n"
               "See [[demo/notes/ghost]].\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("broken-wikilink", _kinds(report))


class TestNamesSomethingThatIsNotThere(unittest.TestCase):

    def test_broken_wikilink(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "notes" / "a.md",
               "---\ntype: note\ncreated: 2026-09-01\nupdated: 2026-09-01\n---\n\n"
               "Real: [[demo/brief]]. Ghost: [[demo/notes/ghost]].\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            broken = [f for f in report["findings"] if f["kind"] == "broken-wikilink"]
            self.assertEqual(len(broken), 1)
            self.assertEqual(broken[0]["file"], "notes/a.md")
            self.assertEqual(broken[0]["band"], "wrong-now")
            self.assertIn("demo/notes/ghost", broken[0]["detail"])

    def test_an_embed_is_not_a_broken_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "notes" / "a.md",
               "---\ntype: note\ncreated: 2026-09-01\nupdated: 2026-09-01\n---\n\n"
               "![[diagram.png]]\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("broken-wikilink", _kinds(report))

    def test_superseded_by_pointing_at_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "decisions" / "2026-08-01-a.md",
               "---\ntype: decision\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: superseded\nsuperseded_by: \"[[demo/decisions/nope]]\"\n---\n\n"
               "# A\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "superseded-target-missing"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["file"], "decisions/2026-08-01-a.md")

    def test_a_card_citing_a_spec_that_was_never_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "specs" / "spec-018-page-spinup.md",
               "---\ntype: spec\nstatus: agreed\ncreated: 2026-08-01\n"
               "updated: 2026-08-30\nverified: 2026-08-30\n---\n\n# SPEC-018\n")
            _w(pdir / "tasks" / "real.md",
               "---\ntype: task\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: doing\nspec: \"[[demo/specs/spec-018-page-spinup|SPEC-018]]\"\n"
               "---\n\n# Real\n")
            _w(pdir / "tasks" / "phantom.md",
               "---\ntype: task\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: doing\nspec: \"[[demo/specs/spec-999-nope|SPEC-999]]\"\n"
               "---\n\n# Phantom\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"] if f["kind"] == "task-spec-missing"]
            self.assertEqual([h["file"] for h in hits], ["tasks/phantom.md"])

    def test_a_brief_repo_path_that_no_longer_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            real = root / "code"
            real.mkdir()
            _w(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n"
               "# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n"
               f"| Repo | {real} |\n| Deploy | https://example.test |\n")
            self.assertEqual(
                [f["kind"] for f in truth_report(
                    pdir, vault=root / "vault", today=date(2026, 9, 1))["findings"]],
                [])
            _w(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n"
               "# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n"
               f"| Repo | {root / 'moved-away'} |\n")
            report = truth_report(pdir, vault=root / "vault", today=date(2026, 9, 1))
            hits = [f for f in report["findings"] if f["kind"] == "brief-repo-missing"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["band"], "wrong-now")

    def test_an_elided_repo_path_is_not_a_finding(self):
        # The brief template's own example writes `~/…/HubSpot - Nightly`.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            _w(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n"
               "# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n"
               "| Repo | ~/…/HubSpot - Nightly |\n")
            report = truth_report(pdir, vault=root / "vault", today=date(2026, 9, 1))
            self.assertNotIn("brief-repo-missing", _kinds(report))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_truth -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'truth'`

- [ ] **Step 3: Write the module**

Create `adjudant/scripts/truth.py`:

```python
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
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from _vault_walk import (
    VaultFile,
    _wikilink_stem,
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
        value = ctx.fields(vf).get("superseded_by")
        if value is None:
            continue
        target = str(value).strip().strip('"').strip("'").strip()
        if target.startswith("[[") and target.endswith("]]"):
            target = target[2:-2].split("|", 1)[0].strip()
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
        value = ctx.fields(vf).get("spec")
        if value is None:
            continue
        target = str(value).strip().strip('"').strip("'").strip()
        if target.startswith("[[") and target.endswith("]]"):
            target = target[2:-2].split("|", 1)[0].strip()
        if not target:
            continue
        if resolve_wikilink(target, ctx.index):
            continue
        yield Finding("wrong-now", "task-spec-missing", ctx.rel(vf),
                      f"cites spec {target!r}, which was never written")


# The brief's `## Where things are` table. Row one cell is the label, row two
# is the value. The template's own example elides with `…`, so a value holding
# one is a placeholder and not a claim about the disk.
_TABLE_ROW_RE = re.compile(r"^\|([^|]*)\|([^|]*)\|\s*$")


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
    if not value or "…" in value or "..." in value:
        return
    if "://" in value:
        return                      # a URL is not a path we can stat
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
```

- [ ] **Step 4: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_truth -v`
Expected: PASS, 11 tests

- [ ] **Step 5: Run the full suite**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add adjudant/scripts/truth.py adjudant/scripts/test_truth.py
git commit -m "feat(adjudant): truth.py - findings that name something not there

The finding model plus the first band: broken wikilinks (733 of 9611), a
superseded_by pointing at nothing, a card citing a spec that was never
written, and a brief repo path that no longer resolves.

memory/ is excluded outright and generated pages are excluded from every
detector that is not about them.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: "Nobody has checked it lately"

`verified:` is the field that makes this checkable at all, and plan 2 added it.
Without it `updated:` was the only clock, and `updated:` only says the text
changed.

**Files:**
- Modify: `adjudant/scripts/truth.py` (three detectors, appended to `_DETECTORS`)
- Test: `adjudant/scripts/test_truth.py`

**Interfaces:**
- Consumes: `Finding`, `_Ctx`, `_DETECTORS`, `BANDS` from Task 10; `FIELD_SCHEMA` from `_vault_walk`.
- Produces:
  - `VERIFIED_STALE_DAYS: int = 90`
  - `verified_kinds() -> frozenset[str]` — the kinds whose template makes `verified` required. Derived from `FIELD_SCHEMA`, never listed a second time.
  - Detector kinds `verified-stale`, `verified-missing`, `verified-docs-only`.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_truth.py`:

```python
class TestNobodyHasCheckedItLately(unittest.TestCase):

    def test_the_verified_kinds_come_from_the_templates(self):
        from truth import verified_kinds
        kinds = verified_kinds()
        self.assertIn("doc", kinds)
        self.assertIn("spec", kinds)
        # verified: is the only thing dividing a doc from a note. A note is a
        # thought and cannot be wrong in that way.
        self.assertNotIn("note", kinds)
        self.assertNotIn("session", kinds)

    def test_verified_over_ninety_days_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "docs" / "fresh.md",
               "---\ntype: doc\nupdated: 2026-09-01\nverified: 2026-08-01\n---\n\n# F\n")
            _w(pdir / "docs" / "stale.md",
               "---\ntype: doc\nupdated: 2026-09-01\nverified: 2026-05-01\n---\n\n# S\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"] if f["kind"] == "verified-stale"]
            self.assertEqual([h["file"] for h in hits], ["docs/stale.md"])
            self.assertEqual(hits[0]["band"], "going-stale")
            self.assertIn("123 days", hits[0]["detail"])

    def test_exactly_ninety_days_is_the_edge_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "docs" / "edge.md",
               "---\ntype: doc\nupdated: 2026-09-01\nverified: 2026-06-03\n---\n\n# E\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertIn("verified-stale", _kinds(report))

    def test_a_page_with_no_verified_at_all(self):
        # 71 component sidecars carry none. The generated half of the pair
        # carries source: and is exempt; the hand-written half is not.
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "docs" / "unchecked.md",
               "---\ntype: doc\nupdated: 2026-09-01\n---\n\n# U\n")
            _w(pdir / "notes" / "thought.md",
               "---\ntype: note\ncreated: 2026-09-01\nupdated: 2026-09-01\n---\n\n# T\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"] if f["kind"] == "verified-missing"]
            self.assertEqual([h["file"] for h in hits], ["docs/unchecked.md"])
            self.assertEqual(hits[0]["band"], "going-stale")

    def test_a_malformed_verified_date_is_reported_not_swallowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "docs" / "bad.md",
               "---\ntype: doc\nupdated: 2026-09-01\nverified: last tuesday\n---\n\n# B\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"] if f["kind"] == "verified-missing"]
            self.assertEqual(len(hits), 1)
            self.assertIn("last tuesday", hits[0]["detail"])

    def test_verified_by_docs_only(self):
        # A bare date throws away the difference between a live probe and a
        # skim of vendor documentation.
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "api" / "contacts.md",
               "---\ntype: api\nupdated: 2026-09-01\nverified: 2026-08-30\n"
               "verified_by: docs\n---\n\n# Contacts\n")
            _w(pdir / "api" / "objects.md",
               "---\ntype: api\nupdated: 2026-09-01\nverified: 2026-08-30\n"
               "verified_by: tested\n---\n\n# Objects\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "verified-docs-only"]
            self.assertEqual([h["file"] for h in hits], ["api/contacts.md"])
            self.assertEqual(hits[0]["band"], "worth-a-look")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_truth.TestNobodyHasCheckedItLately -v`
Expected: FAIL with `ImportError: cannot import name 'verified_kinds' from 'truth'`

- [ ] **Step 3: Add the three detectors**

Add `FIELD_SCHEMA` to `truth.py`'s `_vault_walk` import list, and insert before
the `_DETECTORS` tuple:

```python
# ============================================================
# Band: going-stale — nobody has checked it lately
# ============================================================

# `verified:` says a human confirmed the file against reality. `updated:` only
# says the text changed. Ninety days is the interval past which "someone
# checked" stops meaning anything.
VERIFIED_STALE_DAYS = 90

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def verified_kinds() -> frozenset[str]:
    """Kinds whose template makes `verified` required.

    Derived from FIELD_SCHEMA, which since v3 is parsed out of the template
    files. Listing them here as well would be the second declaration this
    whole design exists to remove: deleting `verified:` from a template must
    change what is checked, with no Python edit.
    """
    return frozenset(
        t for t, schema in FIELD_SCHEMA.items()
        if "verified" in schema.get("required", frozenset()))


def _as_date(value: Any) -> Optional[date]:
    """A frontmatter value as a date, or None when it is not one."""
    text = str(value).strip().strip('"').strip("'")
    if not _ISO_DATE_RE.match(text):
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _check_verified_stale(ctx: _Ctx) -> Iterator[Finding]:
    """`verified:` older than 90 days."""
    for vf in ctx.files:
        stamped = _as_date(ctx.fields(vf).get("verified"))
        if stamped is None:
            continue
        age = (ctx.today - stamped).days
        if age < VERIFIED_STALE_DAYS:
            continue
        yield Finding("going-stale", "verified-stale", ctx.rel(vf),
                      f"last verified {stamped.isoformat()}, {age} days ago")


def _check_verified_missing(ctx: _Ctx) -> Iterator[Finding]:
    """A kind that must carry `verified:` and does not, or carries junk.

    71 component sidecars in the real vault have none. The generated half of
    each component pair carries `source:` and never reaches this detector.
    """
    required = verified_kinds()
    for vf in ctx.files:
        if (vf.file_type or "") not in required:
            continue
        raw = ctx.fields(vf).get("verified")
        if raw is None:
            yield Finding("going-stale", "verified-missing", ctx.rel(vf),
                          f"a {vf.file_type} with no verified: date; nobody has "
                          "confirmed it against reality")
            continue
        if _as_date(raw) is None:
            yield Finding("going-stale", "verified-missing", ctx.rel(vf),
                          f"verified: {raw!r} is not a YYYY-MM-DD date")


def _check_verified_docs_only(ctx: _Ctx) -> Iterator[Finding]:
    """Pages only ever `verified_by: docs`, never tested.

    tested means someone ran it against the live thing, read means someone
    read the code it describes, docs means someone took a vendor's word for
    it. A bare date throws that difference away.
    """
    for vf in ctx.files:
        value = ctx.fields(vf).get("verified_by")
        if not isinstance(value, str) or value.strip() != "docs":
            continue
        yield Finding("worth-a-look", "verified-docs-only", ctx.rel(vf),
                      "verified_by: docs — a vendor's word, never a live probe")
```

Extend the `_DETECTORS` tuple with the three new names:

```python
_DETECTORS: tuple = (
    _check_broken_wikilinks,
    _check_superseded_target_missing,
    _check_task_spec_missing,
    _check_brief_repo_missing,
    _check_verified_stale,
    _check_verified_missing,
    _check_verified_docs_only,
)
```

- [ ] **Step 4: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_truth -v`
Expected: PASS, 17 tests

- [ ] **Step 5: Run the full suite**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add adjudant/scripts/truth.py adjudant/scripts/test_truth.py
git commit -m "feat(adjudant): truth checks - nobody has checked it lately

verified: over 90 days, a kind that must carry one and does not (71 component
sidecars), and pages verified_by docs and never tested.

verified_kinds() is derived from FIELD_SCHEMA, which is parsed from the
templates. Deleting verified: from a template changes what is checked with no
Python edit, which is the whole point of template-as-schema.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: "Work nobody can see"

Forty-four cards sat open inside an archive folder because a sweep moved 97
cards and closed zero. SPEC-012 was agreed for two months with no card citing
it. These are the findings that would have caught both.

**Files:**
- Modify: `adjudant/scripts/truth.py` (four detectors, appended to `_DETECTORS`)
- Test: `adjudant/scripts/test_truth.py`

**Interfaces:**
- Consumes: `Finding`, `_Ctx`, `_DETECTORS`, `verified_kinds`, `_as_date` from Tasks 10 and 11.
- Produces:
  - `SPEC_UNBUILT_DAYS: int = 60`
  - `OPEN_TASK_STATUSES: frozenset[str]` — every task status that is not `done` or `dropped`.
  - Detector kinds `open-card-in-archive`, `bug-entry-uncited`, `spec-agreed-unbuilt`, `decision-consequence-uncarded`.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_truth.py`:

```python
class TestWorkNobodyCanSee(unittest.TestCase):

    def test_an_open_card_in_the_archive(self):
        # The 17 August sweep moved 97 cards and closed zero. 44 of them still
        # read open from inside tasks/_archive/.
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "tasks" / "_archive" / "closed.md",
               "---\ntype: task\ncreated: 2026-01-01\nupdated: 2026-02-01\n"
               "status: done\n---\n\n# Closed\n")
            _w(pdir / "tasks" / "_archive" / "dropped.md",
               "---\ntype: task\ncreated: 2026-01-01\nupdated: 2026-02-01\n"
               "status: dropped\n---\n\n# Dropped\n")
            _w(pdir / "tasks" / "_archive" / "alive.md",
               "---\ntype: task\ncreated: 2026-01-01\nupdated: 2026-02-01\n"
               "status: doing\n---\n\n# Alive\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "open-card-in-archive"]
            self.assertEqual([h["file"] for h in hits],
                             ["tasks/_archive/alive.md"])
            self.assertEqual(hits[0]["band"], "wrong-now")
            self.assertIn("doing", hits[0]["detail"])

    def test_a_bug_entry_with_no_card_citing_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "docs" / "bug-log.md",
               "---\ntype: doc\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n"
               "# Bug log\n\n"
               "## BUG-001 cold cache\nstatus: closed\nfixed on 2026-08-01.\n\n"
               "## BUG-002 warm cache\nSomething is wrong.\n\n"
               "## BUG-003 hot cache\nSomething else is wrong.\n")
            _w(pdir / "tasks" / "fix-warm.md",
               "---\ntype: task\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
               "status: doing\n---\n\n# Fix warm\n\nCloses BUG-002.\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "bug-entry-uncited"]
            self.assertEqual(len(hits), 1)
            self.assertIn("BUG-003", hits[0]["detail"])
            self.assertEqual(hits[0]["file"], "docs/bug-log.md")

    def test_a_spec_agreed_with_no_cards_and_no_verification(self):
        # SPEC-012 exactly.
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "specs" / "spec-012-campaign-factory.md",
               "---\ntype: spec\nstatus: agreed\ncreated: 2026-06-01\n"
               "updated: 2026-06-01\n---\n\n# SPEC-012\n\n## Goal\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "spec-agreed-unbuilt"]
            self.assertEqual(len(hits), 1)
            self.assertIn("92 days", hits[0]["detail"])
            self.assertEqual(hits[0]["band"], "wrong-now")

    def test_a_cited_spec_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "specs" / "spec-012-campaign-factory.md",
               "---\ntype: spec\nstatus: agreed\ncreated: 2026-06-01\n"
               "updated: 2026-06-01\n---\n\n# SPEC-012\n\n## Goal\n")
            _w(pdir / "tasks" / "build-it.md",
               "---\ntype: task\ncreated: 2026-06-02\nupdated: 2026-06-02\n"
               "status: doing\n"
               "spec: \"[[demo/specs/spec-012-campaign-factory|SPEC-012]]\"\n"
               "---\n\n# Build it\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("spec-agreed-unbuilt", _kinds(report))

    def test_a_verified_spec_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "specs" / "spec-012-campaign-factory.md",
               "---\ntype: spec\nstatus: agreed\ncreated: 2026-06-01\n"
               "updated: 2026-06-01\nverified: 2026-08-30\n---\n\n# SPEC-012\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("spec-agreed-unbuilt", _kinds(report))

    def test_a_draft_spec_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "specs" / "spec-013-idea.md",
               "---\ntype: spec\nstatus: draft\ncreated: 2026-01-01\n"
               "updated: 2026-01-01\n---\n\n# SPEC-013\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("spec-agreed-unbuilt", _kinds(report))

    def test_a_decision_whose_consequence_names_work_with_no_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "tasks" / "strip-bucket-a-tags.md",
               "---\ntype: task\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
               "status: doing\n---\n\n# Strip\n")
            _w(pdir / "decisions" / "2026-09-01-carded.md",
               "---\ntype: decision\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
               "status: active\n---\n\n# Carded\n\n## Consequence\n"
               "Work: [[demo/tasks/strip-bucket-a-tags]]\n")
            _w(pdir / "decisions" / "2026-09-01-uncarded.md",
               "---\ntype: decision\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
               "status: active\n---\n\n# Uncarded\n\n## Consequence\n"
               "Work: someone has to rewrite the branch tracker.\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "decision-consequence-uncarded"]
            self.assertEqual([h["file"] for h in hits],
                             ["decisions/2026-09-01-uncarded.md"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_truth.TestWorkNobodyCanSee -v`
Expected: FAIL — none of the four kinds appear in any report.

- [ ] **Step 3: Add the four detectors**

Insert into `adjudant/scripts/truth.py` before the `_DETECTORS` tuple:

```python
# ============================================================
# Band: wrong-now — work nobody can see
# ============================================================

# A spec agreed this long with no card and no verification is intent that
# never became work. SPEC-012 sat at 60+ days.
SPEC_UNBUILT_DAYS = 60

# Archiving is derived from status, never manual: `clean` moves only done and
# dropped cards. Anything else in the archive is work that was hidden rather
# than finished.
_CLOSED_TASK_STATUSES: frozenset[str] = frozenset({"done", "dropped"})

_BUG_HEADING_RE = re.compile(r"^#{2,3}\s+(BUG-\d+)\b", re.MULTILINE)
_BUG_CLOSED_RE = re.compile(r"^\s*status\s*:\s*(closed|fixed|dropped)\s*$",
                            re.IGNORECASE | re.MULTILINE)
_CONSEQUENCE_RE = re.compile(
    r"^##\s+Consequence\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)
_WORK_LINE_RE = re.compile(r"^\s*Work\s*:\s*(.+)$", re.MULTILINE)


def _check_open_card_in_archive(ctx: _Ctx) -> Iterator[Finding]:
    """A card in `tasks/_archive/` that still reads open. The 44."""
    for vf in ctx.by_type.get("task", []):
        parts = vf.rel_path.parts
        if "_archive" not in parts:
            continue
        status = ctx.fields(vf).get("status")
        text = str(status).strip() if status is not None else ""
        if text in _CLOSED_TASK_STATUSES:
            continue
        yield Finding("wrong-now", "open-card-in-archive", ctx.rel(vf),
                      f"status {text or 'unset'!r} inside tasks/_archive/; "
                      "only done and dropped cards belong there")


def _check_bug_entry_uncited(ctx: _Ctx) -> Iterator[Finding]:
    """A bug entry still open with no task card citing it.

    The bug log is one document on purpose: three of its sixteen entries
    turned out to be the same defect class on different surfaces, which only
    became visible once they sat in one list. Splitting it into sixteen files
    would destroy the one thing it is for, so the only mechanism it needs is
    this: what never got picked up.
    """
    logs = [vf for vf in ctx.files if vf.path.stem == "bug-log"]
    if not logs:
        return
    cited: set[str] = set()
    for vf in ctx.by_type.get("task", []):
        # A card cites a bug by naming its id anywhere in its body. The vault
        # runs four number registries at once (BUG-NNN, T<N>, harness numbers,
        # GitHub numbers) under a standing rule never to cite a bare number,
        # so the prefix is what makes this unambiguous.
        cited.update(re.findall(r"\bBUG-\d+\b", vf.body))
    for log in logs:
        body = log.body
        headings = list(_BUG_HEADING_RE.finditer(body))
        for i, m in enumerate(headings):
            bug_id = m.group(1)
            end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
            section = body[m.end():end]
            if _BUG_CLOSED_RE.search(section):
                continue
            if bug_id in cited:
                continue
            yield Finding("wrong-now", "bug-entry-uncited", ctx.rel(log),
                          f"{bug_id} reads open and no task card cites it")


def _check_spec_agreed_unbuilt(ctx: _Ctx) -> Iterator[Finding]:
    """A spec agreed 60 days, zero cards citing it, never verified.

    How much is built is the status of the cards citing it. No cards and no
    `verified:` means the intent was recorded and the work never started, and
    nothing said so.
    """
    cited: set[str] = set()
    for vf in ctx.by_type.get("task", []):
        value = ctx.fields(vf).get("spec")
        if value is None:
            continue
        stem = _wikilink_stem(value)
        if stem:
            cited.add(stem)
    for vf in ctx.by_type.get("spec", []):
        fields = ctx.fields(vf)
        if str(fields.get("status", "")).strip() != "agreed":
            continue
        if fields.get("verified") is not None:
            continue
        if vf.path.stem in cited:
            continue
        agreed_on = _as_date(fields.get("updated")) or _as_date(fields.get("created"))
        if agreed_on is None:
            continue
        age = (ctx.today - agreed_on).days
        if age < SPEC_UNBUILT_DAYS:
            continue
        yield Finding("wrong-now", "spec-agreed-unbuilt", ctx.rel(vf),
                      f"agreed {age} days ago, no card cites it, never verified")


def _check_decision_consequence_uncarded(ctx: _Ctx) -> Iterator[Finding]:
    """A decision whose `## Consequence` names work with no card.

    One axis only: `status:` says whether a decision is in force, and whether
    it was carried out is a card. A `Work:` line with no link is a job that
    exists in prose and nowhere a board can see it.
    """
    for vf in ctx.by_type.get("decision", []):
        m = _CONSEQUENCE_RE.search(vf.body)
        if not m:
            continue
        section = m.group(1)
        for work in _WORK_LINE_RE.finditer(section):
            if "[[" in work.group(1):
                continue
            yield Finding("wrong-now", "decision-consequence-uncarded",
                          ctx.rel(vf),
                          f"Consequence names work with no card: "
                          f"{work.group(1).strip()[:60]!r}")
```

Extend `_DETECTORS`:

```python
_DETECTORS: tuple = (
    _check_broken_wikilinks,
    _check_superseded_target_missing,
    _check_task_spec_missing,
    _check_brief_repo_missing,
    _check_open_card_in_archive,
    _check_bug_entry_uncited,
    _check_spec_agreed_unbuilt,
    _check_decision_consequence_uncarded,
    _check_verified_stale,
    _check_verified_missing,
    _check_verified_docs_only,
)
```

- [ ] **Step 4: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_truth -v`
Expected: PASS, 24 tests

- [ ] **Step 5: Run the full suite**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add adjudant/scripts/truth.py adjudant/scripts/test_truth.py
git commit -m "feat(adjudant): truth checks - work nobody can see

An open card inside tasks/_archive (the 44 a sweep hid), a bug entry still
open with no card citing it, a spec agreed 60 days with zero cards and no
verification (SPEC-012 exactly), and a decision whose Consequence names work
in prose with no card.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: "Records that disagree", "went stale quietly", and the wrong folder

The last eight detectors, and the wiring that puts the whole report into
`status` in place of the shape grading.

**Files:**
- Modify: `adjudant/scripts/truth.py` (eight detectors, appended to `_DETECTORS`)
- Modify: `adjudant/scripts/status.py` (`run_status` gains a `truth` section; the schema section loses its unknown-field count)
- Modify: `adjudant/scripts/_vault_walk.py:1380-1406` (`schema_drift`, the `unknown_fields` count)
- Test: `adjudant/scripts/test_truth.py`, `adjudant/scripts/test_status.py`, `adjudant/scripts/test__vault_walk.py`

**Interfaces:**
- Consumes: `Finding`, `_Ctx`, `_DETECTORS`, `_as_date` from Tasks 10 and 11; `STATUS_VALUES_FOR_TYPE`, `newest_dated_stem`, `zone_of` from `_vault_walk`.
- Produces:
  - `BRIEF_STALE_DAYS: int = 90`, `ZONE_DRIFT_DAYS: int = 30`
  - Detector kinds `superseded-without-target`, `status-off-vocabulary`, `created-filename-mismatch`, `version-filename-mismatch`, `brief-stale`, `handoff-behind-session`, `generated-page-stale`, `project-zone-drift`.
  - `run_status(...)["truth"]` — the report dict from `truth_report`.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_truth.py`:

```python
class TestRecordsThatDisagree(unittest.TestCase):

    def test_superseded_with_no_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "decisions" / "2026-08-01-a.md",
               "---\ntype: decision\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: superseded\n---\n\n# A\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "superseded-without-target"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["band"], "wrong-now")

    def test_an_empty_superseded_by_is_the_same_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "decisions" / "2026-08-01-a.md",
               "---\ntype: decision\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: superseded\nsuperseded_by: \"\"\n---\n\n# A\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertIn("superseded-without-target", _kinds(report))

    def test_an_off_vocabulary_status_is_reported_never_coerced(self):
        # board.py silently refiled anything unrecognised as backlog, which is
        # how `obsolete` became invisible work.
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "tasks" / "odd.md",
               "---\ntype: task\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
               "status: obsolete\n---\n\n# Odd\n")
            _w(pdir / "tasks" / "blocked.md",
               "---\ntype: task\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
               "status: blocked\n---\n\n# Blocked\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "status-off-vocabulary"]
            self.assertEqual([h["file"] for h in hits], ["tasks/odd.md"])
            self.assertIn("obsolete", hits[0]["detail"])

    def test_a_created_date_disagreeing_with_its_own_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "decisions" / "2026-08-01-a.md",
               "---\ntype: decision\ncreated: 2026-07-14\nupdated: 2026-08-01\n"
               "status: active\n---\n\n# A\n")
            _w(pdir / "decisions" / "2026-08-02-b.md",
               "---\ntype: decision\ncreated: 2026-08-02\nupdated: 2026-08-02\n"
               "status: active\n---\n\n# B\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "created-filename-mismatch"]
            self.assertEqual([h["file"] for h in hits], ["decisions/2026-08-01-a.md"])
            self.assertIn("2026-07-14", hits[0]["detail"])

    def test_a_release_version_disagreeing_with_its_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "releases" / "v2.1.0.md",
               "---\ntype: release\nversion: 2.0.9\ncreated: 2026-09-01\n"
               "updated: 2026-09-01\n---\n\n# v2.1.0\n")
            _w(pdir / "releases" / "v2.2.0.md",
               "---\ntype: release\nversion: v2.2.0\ncreated: 2026-09-01\n"
               "updated: 2026-09-01\n---\n\n# v2.2.0\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "version-filename-mismatch"]
            self.assertEqual([h["file"] for h in hits], ["releases/v2.1.0.md"])


class TestWentStaleQuietly(unittest.TestCase):

    def test_a_brief_untouched_while_sessions_kept_landing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-01-01\nverified: 2026-09-01\n"
               "---\n\n# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"] if f["kind"] == "brief-stale"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["band"], "going-stale")
            self.assertIn("2026-09-01", hits[0]["detail"])

    def test_a_quiet_project_with_an_old_brief_is_not_a_brief_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            (pdir / "sessions" / "2026-09-01.md").unlink()
            _w(pdir / "sessions" / "2025-01-01.md", "---\ntype: session\n---\n")
            _w(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-01-01\nverified: 2026-09-01\n"
               "---\n\n# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("brief-stale", _kinds(report))

    def test_a_handoff_older_than_the_newest_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "_handoff.md",
               "---\ntype: handoff\nupdated: 2026-08-01\n---\n\n# Handoff\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "handoff-behind-session"]
            self.assertEqual(len(hits), 1)
            self.assertIn("2026-09-01", hits[0]["detail"])

    def test_a_current_handoff_is_not_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "_handoff.md",
               "---\ntype: handoff\nupdated: 2026-09-01\n---\n\n# Handoff\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("handoff-behind-session", _kinds(report))

    def test_a_generated_page_older_than_its_own_script(self):
        import os
        import time
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            code = root / "code"
            script = _w(code / "build-module-inventory.py", "print('x')\n")
            page = _w(pdir / "components" / "gen.md",
                      "---\ntype: component\nupdated: 2026-09-01\n"
                      "source: build-module-inventory.py\n---\n\n# gen\n")
            old = time.time() - 86400
            os.utime(page, (old, old))
            report = truth_report(pdir, vault=root / "vault", code_root=code,
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "generated-page-stale"]
            self.assertEqual([h["file"] for h in hits], ["components/gen.md"])
            self.assertIn("build-module-inventory.py", hits[0]["detail"])
            self.assertEqual(script.name, "build-module-inventory.py")

    def test_a_source_naming_a_system_is_not_a_stale_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            _w(pdir / "sources" / "wiki.md",
               "---\ntype: source\nupdated: 2026-09-01\nverified: 2026-08-30\n"
               "source: confluence\n---\n\n# Wiki\n")
            report = truth_report(pdir, vault=root / "vault",
                                  code_root=root / "code",
                                  today=date(2026, 9, 1))
            self.assertNotIn("generated-page-stale", _kinds(report))


class TestWrongFolder(unittest.TestCase):

    def test_active_with_no_session_for_thirty_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            (pdir / "sessions" / "2026-09-01.md").unlink()
            _w(pdir / "sessions" / "2026-07-01.md", "---\ntype: session\n---\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "project-zone-drift"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["band"], "worth-a-look")
            self.assertEqual(hits[0]["file"], "")
            self.assertIn("62 days", hits[0]["detail"])

    def test_a_paused_project_is_quiet_on_purpose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = root / "vault" / "projects" / "paused" / "demo"
            _w(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n"
               "---\n\n# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n")
            _w(pdir / "sessions" / "2025-01-01.md", "---\ntype: session\n---\n")
            report = truth_report(pdir, vault=root / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("project-zone-drift", _kinds(report))
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_truth.TestRecordsThatDisagree test_truth.TestWentStaleQuietly test_truth.TestWrongFolder -v`
Expected: FAIL — none of the eight kinds appear in any report.

- [ ] **Step 3: Add the eight detectors**

Add `STATUS_VALUES_FOR_TYPE`, `newest_dated_stem` and `zone_of` to `truth.py`'s
`_vault_walk` import list, and insert before the `_DETECTORS` tuple:

```python
# ============================================================
# Band: wrong-now — records that disagree
# ============================================================

# `blocked` stays an alias of `review`, and is the only alias that survives.
# The other ~25 board aliases were deleted: an alias is a second name for a
# state, and a second name is how `obsolete` got silently refiled as backlog.
_STATUS_ALIASES: dict[str, frozenset[str]] = {"task": frozenset({"blocked"})}

_DATED_STEM_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_VERSION_STEM_RE = re.compile(r"^v?(\d+\.\d+\.\d+)$")


def _check_superseded_without_target(ctx: _Ctx) -> Iterator[Finding]:
    """`status: superseded` with no `superseded_by`.

    The field is written only when true, never as an empty string, so its
    absence beside a superseded status is a record that contradicts itself.
    """
    for vf in ctx.files:
        fields = ctx.fields(vf)
        if str(fields.get("status", "")).strip() != "superseded":
            continue
        raw = fields.get("superseded_by")
        target = str(raw).strip().strip('"').strip("'").strip() if raw is not None else ""
        if target:
            continue
        yield Finding("wrong-now", "superseded-without-target", ctx.rel(vf),
                      "status is superseded and nothing says what replaced it")


def _check_status_off_vocabulary(ctx: _Ctx) -> Iterator[Finding]:
    """A `status:` outside its type's vocabulary. Reported, never coerced."""
    for vf in ctx.files:
        ftype = vf.file_type or ""
        legal = STATUS_VALUES_FOR_TYPE.get(ftype)
        if not legal:
            continue
        raw = ctx.fields(vf).get("status")
        if raw is None:
            continue
        value = str(raw).strip()
        if value in legal or value in _STATUS_ALIASES.get(ftype, frozenset()):
            continue
        yield Finding("wrong-now", "status-off-vocabulary", ctx.rel(vf),
                      f"status {value!r} is not one of "
                      f"{' | '.join(legal)} for a {ftype}")


def _check_created_filename_mismatch(ctx: _Ctx) -> Iterator[Finding]:
    """A `created:` date disagreeing with the date in its own filename.

    Where the filename carries a date, `created:` is derived from it at write
    time, so the two cannot disagree unless one was edited by hand.
    """
    for vf in ctx.files:
        m = _DATED_STEM_PREFIX_RE.match(vf.path.stem)
        if not m:
            continue
        raw = ctx.fields(vf).get("created")
        if raw is None:
            continue
        value = str(raw).strip().strip('"').strip("'")
        if value == m.group(1):
            continue
        yield Finding("wrong-now", "created-filename-mismatch", ctx.rel(vf),
                      f"created: {value} against a filename dated {m.group(1)}")


def _check_version_filename_mismatch(ctx: _Ctx) -> Iterator[Finding]:
    """A release note's `version:` disagreeing with its filename.

    `version:` is derived from the filename and machine-written, by the same
    rule as dates. A leading `v` on either side is not a disagreement.
    """
    for vf in ctx.by_type.get("release", []):
        m = _VERSION_STEM_RE.match(vf.path.stem)
        if not m:
            continue
        raw = ctx.fields(vf).get("version")
        if raw is None:
            continue
        value = str(raw).strip().strip('"').strip("'").lstrip("v")
        if value == m.group(1):
            continue
        yield Finding("wrong-now", "version-filename-mismatch", ctx.rel(vf),
                      f"version: {raw} against a filename naming {m.group(1)}")


# ============================================================
# Band: going-stale — went stale quietly
# ============================================================

# A brief this old, while sessions kept landing, describes a project that has
# moved on without it.
BRIEF_STALE_DAYS = 90

# The interval after which a project in active/ is offered a move. This is the
# prompt that makes lifecycle triage happen instead of never happening.
ZONE_DRIFT_DAYS = 30


def _newest_session(ctx: _Ctx) -> Optional[str]:
    return newest_dated_stem(ctx.project_dir / "sessions",
                             not_after=ctx.today.strftime("%Y-%m-%d"))


def _check_brief_stale(ctx: _Ctx) -> Iterator[Finding]:
    """A brief untouched for 90 days while sessions kept landing."""
    newest = _newest_session(ctx)
    if newest is None:
        return
    last = datetime.strptime(newest, "%Y-%m-%d").date()
    if (ctx.today - last).days >= BRIEF_STALE_DAYS:
        return                      # the project is quiet; that is triage's finding
    brief = ctx.project_dir / "brief.md"
    try:
        fm, _body = parse_frontmatter(brief.read_text(errors="replace"))
    except OSError:
        return
    updated = _as_date(fm.fields.get("updated"))
    if updated is None:
        return
    age = (ctx.today - updated).days
    if age < BRIEF_STALE_DAYS:
        return
    yield Finding("going-stale", "brief-stale", "brief.md",
                  f"brief last updated {updated.isoformat()} ({age} days) "
                  f"while sessions kept landing, newest {newest}")


def _check_handoff_behind_session(ctx: _Ctx) -> Iterator[Finding]:
    """A handoff older than the newest session.

    The handoff is written once, at session end. One older than the newest
    session note is describing a session that has since been superseded.
    """
    newest = _newest_session(ctx)
    if newest is None:
        return
    handoff = ctx.project_dir / "_handoff.md"
    try:
        fm, _body = parse_frontmatter(handoff.read_text(errors="replace"))
    except OSError:
        return
    updated = _as_date(fm.fields.get("updated"))
    if updated is None or updated.isoformat() >= newest:
        return
    yield Finding("going-stale", "handoff-behind-session", "_handoff.md",
                  f"handoff dated {updated.isoformat()}, newest session {newest}")


def _check_generated_page_stale(ctx: _Ctx) -> Iterator[Finding]:
    """A generated page older than the script named in its `source:`.

    This is the one detector that looks at generated files, because it is
    about them. A `source:` that names a system rather than a path (
    `confluence`) resolves to nothing and is skipped: it is provenance, not a
    generator.
    """
    for vf in ctx.all_owned:
        raw = vf.frontmatter.fields.get("source")
        if raw is None:
            continue
        value = str(raw).strip().strip('"').strip("'")
        if not value or "://" in value:
            continue
        script: Optional[Path] = None
        for base in (ctx.code_root, ctx.project_dir):
            if base is None:
                continue
            cand = (base / value).expanduser()
            if cand.is_file():
                script = cand
                break
        if script is None:
            continue
        try:
            if vf.path.stat().st_mtime >= script.stat().st_mtime:
                continue
        except OSError:
            continue
        yield Finding("going-stale", "generated-page-stale", str(vf.rel_path),
                      f"older than {value}, the script that writes it")


# ============================================================
# Band: worth-a-look — a project in the wrong folder
# ============================================================


def _check_project_zone_drift(ctx: _Ctx) -> Iterator[Finding]:
    """A project in `active/` with no session for 30 days."""
    if zone_of(ctx.project_dir) != "active":
        return
    newest = _newest_session(ctx)
    if newest is None:
        return
    days = (ctx.today - datetime.strptime(newest, "%Y-%m-%d").date()).days
    if days < ZONE_DRIFT_DAYS:
        return
    yield Finding("worth-a-look", "project-zone-drift", "",
                  f"in active/ with no session for {days} days; "
                  f"`/adjudant status --move {ctx.slug} paused` moves it")
```

Add `parse_frontmatter` to `truth.py`'s `_vault_walk` import list — Task 10 did
not need it — and extend `_DETECTORS` to its final form:

```python
_DETECTORS: tuple = (
    _check_broken_wikilinks,
    _check_superseded_target_missing,
    _check_task_spec_missing,
    _check_brief_repo_missing,
    _check_open_card_in_archive,
    _check_bug_entry_uncited,
    _check_spec_agreed_unbuilt,
    _check_decision_consequence_uncarded,
    _check_superseded_without_target,
    _check_status_off_vocabulary,
    _check_created_filename_mismatch,
    _check_version_filename_mismatch,
    _check_verified_stale,
    _check_verified_missing,
    _check_verified_docs_only,
    _check_brief_stale,
    _check_handoff_behind_session,
    _check_generated_page_stale,
    _check_project_zone_drift,
)
```

- [ ] **Step 4: Run the truth tests**

Run: `cd adjudant/scripts && python3 -m unittest test_truth -v`
Expected: PASS, 37 tests

- [ ] **Step 5: Write the failing test for the status wiring**

Append to `adjudant/scripts/test_status.py`:

```python
class TestTruthSection(unittest.TestCase):

    def _project(self, tmp: Path) -> Path:
        pdir = tmp / "vault" / "projects" / "active" / "demo"
        _write(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n"
               "---\n\n# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n")
        _write(pdir / "sessions" / "2026-09-01.md", "---\ntype: session\n---\n")
        return pdir

    def test_run_status_carries_a_truth_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._project(Path(tmp))
            _write(pdir / "decisions" / "2026-08-01-a.md",
                   "---\ntype: decision\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
                   "status: superseded\n---\n\n# A\n")
            report = run_status(pdir, today=date(2026, 9, 1))
            self.assertIn("truth", report)
            kinds = [f["kind"] for f in report["truth"]["findings"]]
            self.assertIn("superseded-without-target", kinds)
            self.assertEqual(set(report["truth"]["counts"]),
                             {"wrong-now", "going-stale", "worth-a-look"})

    def test_the_schema_section_no_longer_counts_unknown_fields(self):
        # With five field names, an unknown one is a typo or a real need.
        # Reporting it produced noise and taught nobody anything.
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._project(Path(tmp))
            report = run_status(pdir, today=date(2026, 9, 1))
            self.assertNotIn("unknown_fields", report["schema"]["counts"])

    def test_the_truth_report_writes_nothing(self):
        # status makes derived state current before reporting, so it may write.
        # The truth report itself never does, and that is what is asserted.
        from truth import truth_report
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._project(Path(tmp))
            before = sorted(str(p) for p in pdir.rglob("*"))
            truth_report(pdir, vault=Path(tmp) / "vault", today=date(2026, 9, 1))
            self.assertEqual(sorted(str(p) for p in pdir.rglob("*")), before)
```

`test_status.py` inherits `test_check.py`'s `_write` helper (line 15) and its
`run_check` import, renamed to `run_status` by plan 3. Add `from datetime import date`
to the file's imports if absent.

- [ ] **Step 6: Wire truth into `status` and drop the unknown-field count**

In `adjudant/scripts/status.py`, add `from truth import truth_report` to the
imports, and in `run_status`'s return dict add, beside the existing `schema`
and `freshness` entries:

```python
        "truth": truth_report(project_dir, vault=vault_root,
                              code_root=code_root, today=today or date.today()),
```

`vault_root` is the vault the project sits in: derive it once above the return
with `vault_root = project_dir.parent.parent.parent if project_dir.parent.parent.name == "projects" else project_dir.parent.parent`, which covers both the four-folder shape (`projects/{zone}/{slug}`) and the pre-v3 shape (`projects/{slug}`).

In `adjudant/scripts/_vault_walk.py`'s `schema_drift` (rewritten in Task 9),
delete the `"unknown_fields"` entry from the `counts` dict. Leave
`schema_drift_for_file` and `schema_drift_for_text` untouched: the PreToolUse
write gate still needs them, and an unknown key on a proposed write is worth
refusing even when it is not worth reporting across a whole vault.

Update `adjudant/skills/adjudant/reference/` — the doc plan 3 wrote for
`status` — with a `## Truth checks` section listing the nineteen kinds by their
machine id, their band, and the real failure each traces to. Render the report
in the three bands, in `BANDS` order, and say plainly that it gates nothing.

- [ ] **Step 7: Run the affected tests**

Run: `cd adjudant/scripts && python3 -m unittest test_truth test_status test__vault_walk -v 2>&1 | tail -3`
Expected: `OK`. Delete the `unknown_fields` assertions in `test__vault_walk.py`'s `TestSchemaDrift` (line 1275) and in `test_status.py`.

- [ ] **Step 8: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 9: Commit**

```bash
git add adjudant/scripts/truth.py adjudant/scripts/status.py adjudant/scripts/_vault_walk.py adjudant/scripts/test_truth.py adjudant/scripts/test_status.py adjudant/scripts/test__vault_walk.py adjudant/skills/adjudant/reference/
git commit -m "feat(adjudant): the remaining truth checks, wired into status

Records that disagree: superseded with no target, an off-vocabulary status
reported and never refiled as backlog, a created date against its own filename,
a release version against its own filename.

Went stale quietly: a brief untouched while sessions kept landing, a handoff
behind the newest session, a generated page older than the script that writes
it. And one for a person: a project in active/ with no session for 30 days.

status stops counting unknown frontmatter keys. With five field names an
unknown one is a typo or a real need, and neither is news. The write gate
keeps the check.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: The AGENTS.md reach

The one deliberate reach outside the vault. AGENTS.md is the first thing every
agent reads and nothing keeps it true: HubSpot Nightly's carries five false
statements, including traps about a module deleted on 2026-08-23 and a rule
described as "enforced mechanically" by a script that does not exist. This
repo's own says adjudant has eleven verbs; it has thirteen.

**Files:**
- Create: `adjudant/scripts/_agents_reach.py`
- Test: `adjudant/scripts/test__agents_reach.py`
- Modify: `adjudant/scripts/truth.py` (one detector, appended to `_DETECTORS`)
- Test: `adjudant/scripts/test_truth.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `AGENTS_STALE_COMMITS: int = 30`
  - `named_paths(text: str) -> list[tuple[int, str]]` — every path-shaped token AGENTS.md names, with its line number.
  - `agents_reach(code_root: Path) -> dict` returning `{"present": bool, "missing": [{"line": int, "token": str}], "checked": int, "last_changed": Optional[str], "commits_since_change": Optional[int]}`.
  - Detector kinds `agents-missing-path` (band `wrong-now`) and `agents-unchanged` (band `going-stale`). Both report with `file=""`; the repo file is named in `detail`, so `file` stays a project-relative path exactly as Task 10 defines it.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test__agents_reach.py`:

```python
"""Tests for adjudant/scripts/_agents_reach.py.

AGENTS.md is the first thing every agent reads and nothing keeps it true. Of
five false statements in one project's file, three were detectable without
adjudant knowing anything about the project: they named things that are not
there.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from _agents_reach import AGENTS_STALE_COMMITS, agents_reach, named_paths


class TestNamedPaths(unittest.TestCase):

    def test_backticked_paths(self):
        text = "Run `scripts/validate.py` and read `docs/plan.md`.\n"
        self.assertEqual([t for _n, t in named_paths(text)],
                         ["scripts/validate.py", "docs/plan.md"])

    def test_a_backticked_path_with_spaces_survives_whole(self):
        text = "Rules live in `~/Library/Mobile Documents/claude/hookify/`.\n"
        self.assertEqual([t for _n, t in named_paths(text)],
                         ["~/Library/Mobile Documents/claude/hookify"])

    def test_markdown_link_targets(self):
        text = "See [the spec](docs/specs/thing.md).\n"
        self.assertEqual([t for _n, t in named_paths(text)],
                         ["docs/specs/thing.md"])

    def test_fenced_code_is_tokenised_on_whitespace(self):
        text = "```bash\npython3 adjudant/scripts/validate.py --all\n```\n"
        self.assertEqual([t for _n, t in named_paths(text)],
                         ["adjudant/scripts/validate.py"])

    def test_urls_placeholders_and_globs_are_not_paths(self):
        text = ("`https://example.test/a.md` `<plugin-name>/plugin.json` "
                "`{slug}/brief.md` `hooks/*.py` `$HOME/x.sh` `--flag`\n")
        self.assertEqual(named_paths(text), [])

    def test_bare_words_are_not_paths(self):
        text = "Install `pre-commit`, then run `make`.\n"
        self.assertEqual(named_paths(text), [])

    def test_a_bare_filename_with_a_known_extension_counts(self):
        self.assertEqual([t for _n, t in named_paths("Read `AGENTS.md`.\n")],
                         ["AGENTS.md"])

    def test_line_numbers_are_reported(self):
        text = "intro\n\nRun `scripts/go.sh`.\n"
        self.assertEqual(named_paths(text), [(3, "scripts/go.sh")])

    def test_each_token_is_reported_once_per_line(self):
        text = "`a/b.py` and `a/b.py` again\n"
        self.assertEqual(named_paths(text), [(1, "a/b.py")])


class TestAgentsReach(unittest.TestCase):

    def test_absent_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = agents_reach(Path(tmp))
            self.assertFalse(out["present"])
            self.assertEqual(out["missing"], [])
            self.assertEqual(out["checked"], 0)

    def test_reports_only_what_is_not_there(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "real.py").write_text("x")
            (root / "AGENTS.md").write_text(
                "Run `scripts/real.py`.\n\n"
                "Enforced mechanically by `scripts/enforce-branch-rule.sh`.\n")
            out = agents_reach(root)
            self.assertTrue(out["present"])
            self.assertEqual(out["checked"], 2)
            self.assertEqual([m["token"] for m in out["missing"]],
                             ["scripts/enforce-branch-rule.sh"])
            self.assertEqual(out["missing"][0]["line"], 3)

    def test_a_named_directory_counts_as_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "adjudant").mkdir()
            (root / "AGENTS.md").write_text("The plugin lives in `adjudant/`.\n")
            self.assertEqual(agents_reach(root)["missing"], [])

    def test_an_absolute_path_is_checked_as_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                f"Rules live in `{root}/nowhere/rules.sh`.\n")
            self.assertEqual([m["token"] for m in agents_reach(root)["missing"]],
                             [f"{root}/nowhere/rules.sh"])

    def test_commit_count_in_a_real_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.test",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.test",
                   "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(root)}

            def git(*args):
                subprocess.run(["git", "-C", str(root), *args],
                               env=env, capture_output=True, check=True)

            git("init", "-q", "-b", "main")
            (root / "AGENTS.md").write_text("Read `AGENTS.md`.\n")
            git("add", "AGENTS.md")
            git("commit", "-q", "-m", "a")
            for i in range(3):
                (root / f"f{i}.txt").write_text("x")
                git("add", f"f{i}.txt")
                git("commit", "-q", "-m", f"f{i}")
            out = agents_reach(root)
            self.assertEqual(out["commits_since_change"], 3)
            self.assertRegex(out["last_changed"], r"^\d{4}-\d{2}-\d{2}$")

    def test_outside_a_repo_the_commit_count_is_none_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("Read `AGENTS.md`.\n")
            out = agents_reach(root)
            self.assertIsNone(out["commits_since_change"])
            self.assertIsNone(out["last_changed"])

    def test_nothing_is_written_to_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = "Run `scripts/gone.py`.\n"
            (root / "AGENTS.md").write_text(original)
            agents_reach(root)
            self.assertEqual((root / "AGENTS.md").read_text(), original)

    def test_the_stale_threshold_is_named(self):
        self.assertEqual(AGENTS_STALE_COMMITS, 30)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__agents_reach -v`
Expected: FAIL with `ModuleNotFoundError: No module named '_agents_reach'`

- [ ] **Step 3: Write the module**

Create `adjudant/scripts/_agents_reach.py`:

```python
#!/usr/bin/env python3
"""Adjudant's one reach outside the vault: is AGENTS.md still true?

AGENTS.md is canonical and harness-agnostic, CLAUDE.md imports it, GEMINI.md
does the same for agy, and the vault contains none of them. It is the first
thing every agent reads, and nothing keeps it current.

One project's AGENTS.md carries five false statements: traps about a module
deleted on 2026-08-23, and a rule described as "enforced mechanically" by a
script that does not exist. Three of the five are detectable without adjudant
knowing anything about the project, because they name things that are not
there. This repo's own AGENTS.md says adjudant has eleven verbs; it has
thirteen. That is the same failure at home.

Two checks, both read-only. No frontmatter is added and nothing is rewritten:
the file belongs to the person who wrote it, and a context file adjudant
edits is a context file nobody trusts.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

# A context file unchanged across this many commits has stopped describing the
# code it sits beside. Reported, never enforced.
AGENTS_STALE_COMMITS = 30

# Extensions that make a bare filename a path even with no slash in it.
_PATH_EXTS = (
    ".py", ".sh", ".md", ".json", ".yaml", ".yml", ".toml", ".txt",
    ".js", ".ts", ".html", ".css", ".cfg", ".ini", ".lock",
)

# Characters that mark a token as a pattern, a variable or a placeholder
# rather than a path on this disk.
_NOT_A_PATH = set("<>{}*?|$\"'()[]")

_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_FENCE_RE = re.compile(r"^\s*```")


def _looks_like_a_path(token: str) -> bool:
    """True when a token names something that could exist on this disk."""
    t = token.strip().rstrip(".,;:").rstrip("/")
    if not t or t.startswith("-"):
        return False
    if "://" in t or t in (".", ".."):
        return False
    if any(c in _NOT_A_PATH for c in t):
        return False
    return "/" in t or t.endswith(_PATH_EXTS)


def _clean(token: str) -> str:
    return token.strip().rstrip(".,;:").rstrip("/")


def named_paths(text: str) -> list:
    """Every path-shaped token the text names, as `(line_number, token)`.

    Three sources, and only three, so prose is never mined for filenames:
      - an inline backtick span, taken whole so a path with spaces survives
      - a markdown link target
      - a line inside a fenced block, split on whitespace

    Duplicates on one line are reported once; the same token on two lines is
    reported twice, because both lines make the claim.
    """
    out: list = []
    in_fence = False
    for lineno, line in enumerate(text.split("\n"), start=1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        seen_on_line: set = set()
        candidates: list = []
        if in_fence:
            candidates.extend(line.split())
        else:
            candidates.extend(_BACKTICK_RE.findall(line))
            candidates.extend(_MD_LINK_RE.findall(line))
        for raw in candidates:
            if not _looks_like_a_path(raw):
                continue
            token = _clean(raw)
            if token in seen_on_line:
                continue
            seen_on_line.add(token)
            out.append((lineno, token))
    return out


def _git(code_root: Path, *args: str) -> Optional[str]:
    """One git call, or None. Never raises, never blocks longer than 5s."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(code_root), *args],
            capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def agents_reach(code_root: Path) -> dict:
    """Every path AGENTS.md names, checked, plus commits since it changed.

    `missing` holds the tokens that resolve to nothing. `commits_since_change`
    is None outside a git repository, which is a fact about the environment
    and not a finding.
    """
    agents = code_root / "AGENTS.md"
    try:
        text = agents.read_text(errors="replace")
    except OSError:
        return {"present": False, "missing": [], "checked": 0,
                "last_changed": None, "commits_since_change": None}

    missing: list = []
    tokens = named_paths(text)
    for lineno, token in tokens:
        candidate = Path(token).expanduser()
        if not candidate.is_absolute():
            candidate = code_root / candidate
        if candidate.exists():
            continue
        missing.append({"line": lineno, "token": token})

    last_sha = _git(code_root, "log", "-1", "--format=%H", "--", "AGENTS.md")
    last_changed = _git(code_root, "log", "-1", "--format=%cs", "--", "AGENTS.md")
    commits_since: Optional[int] = None
    if last_sha:
        counted = _git(code_root, "rev-list", "--count", f"{last_sha}..HEAD")
        if counted is not None:
            try:
                commits_since = int(counted)
            except ValueError:
                commits_since = None

    return {
        "present": True,
        "missing": missing,
        "checked": len(tokens),
        "last_changed": last_changed,
        "commits_since_change": commits_since,
    }
```

- [ ] **Step 4: Run the module tests**

Run: `cd adjudant/scripts && python3 -m unittest test__agents_reach -v`
Expected: PASS, 17 tests

- [ ] **Step 5: Write the failing test for the detector**

Append to `adjudant/scripts/test_truth.py`:

```python
class TestAgentsReachDetector(unittest.TestCase):

    def test_a_named_script_that_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            code = root / "code"
            code.mkdir()
            _w(code / "AGENTS.md",
               "Enforced mechanically by `scripts/enforce-branch-rule.sh`.\n")
            report = truth_report(pdir, vault=root / "vault", code_root=code,
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "agents-missing-path"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["band"], "wrong-now")
            self.assertEqual(hits[0]["file"], "",
                             "the repo file is named in the detail, so `file` "
                             "stays a project-relative path")
            self.assertIn("AGENTS.md", hits[0]["detail"])
            self.assertIn("scripts/enforce-branch-rule.sh", hits[0]["detail"])

    def test_no_code_root_means_no_reach(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("agents-missing-path", _kinds(report))
            self.assertNotIn("agents-unchanged", _kinds(report))

    def test_an_agents_file_that_names_only_real_things_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            code = root / "code"
            (code / "scripts").mkdir(parents=True)
            _w(code / "scripts" / "real.sh", "#!/bin/sh\n")
            _w(code / "AGENTS.md", "Run `scripts/real.sh`.\n")
            report = truth_report(pdir, vault=root / "vault", code_root=code,
                                  today=date(2026, 9, 1))
            self.assertNotIn("agents-missing-path", _kinds(report))
```

- [ ] **Step 6: Add the detector**

Insert into `adjudant/scripts/truth.py` before the `_DETECTORS` tuple:

```python
# ============================================================
# The reach outside the vault
# ============================================================


def _check_agents_reach(ctx: _Ctx) -> Iterator[Finding]:
    """AGENTS.md: what it names that is not there, and how long since it moved.

    The one detector that reads a file outside the vault. `file` stays empty,
    as the Finding contract says: AGENTS.md is not a project-relative vault
    path, so it is named in the detail instead.

    Nothing is written. A context file adjudant edits is a context file nobody
    trusts, which is why three writers under three contradictory policies were
    collapsed to one rule: connect provisions once if missing, and adjudant
    never overwrites.
    """
    if ctx.code_root is None:
        return
    reach = agents_reach(ctx.code_root)
    if not reach["present"]:
        return
    for miss in reach["missing"]:
        yield Finding("wrong-now", "agents-missing-path", "",
                      f"AGENTS.md line {miss['line']} names "
                      f"{miss['token']!r}, which is not there")
    n = reach["commits_since_change"]
    if n is not None and n >= AGENTS_STALE_COMMITS:
        changed = reach["last_changed"] or "an unknown date"
        yield Finding("going-stale", "agents-unchanged", "",
                      f"AGENTS.md last changed {changed}, {n} commits ago")
```

Add to `truth.py`'s imports:

```python
from _agents_reach import AGENTS_STALE_COMMITS, agents_reach
```

and add `_check_agents_reach` to `_DETECTORS`, immediately after
`_check_brief_repo_missing`.

- [ ] **Step 7: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test__agents_reach test_truth -v 2>&1 | tail -3`
Expected: `OK`, 57 tests across the two files

- [ ] **Step 8: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 9: Commit**

```bash
git add adjudant/scripts/_agents_reach.py adjudant/scripts/test__agents_reach.py adjudant/scripts/truth.py adjudant/scripts/test_truth.py
git commit -m "feat(adjudant): the AGENTS.md reach - every path it names, checked

AGENTS.md is the first thing every agent reads and nothing kept it true. One
project's carries five false statements, three of them detectable without
knowing anything about the project: they name things that are not there. This
repo's own says eleven verbs against thirteen.

Paths come from backtick spans, markdown link targets and fenced code lines,
so prose is never mined for filenames. Commits since it last changed come from
git and degrade to None outside a repo. Nothing is written to the file.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 15: The acceptance tests

The plan's three headline claims, asserted rather than believed. Modelled on
`test_no_crud.py` from plan 1.

**Files:**
- Create: `adjudant/scripts/test_structure_acceptance.py`

**Interfaces:**
- Consumes: every change in Tasks 1 through 14.
- Produces: nothing. This is the gate.

- [ ] **Step 1: Write the test**

Create `adjudant/scripts/test_structure_acceptance.py`:

```python
"""Acceptance tests for adjudant v3 plan 4: structure and truth.

Three claims, asserted:

  The truth test. Seed a project where AGENTS.md names a missing script, a
  card sits open in an archive, a decision is superseded with no target, and a
  page is 100 days unverified. All four appear, ranked, in one status run.

  Link round-trip. One file of every kind, every link resolving by path with
  no full-vault scan, and every link still resolving after the project moves
  between lifecycle folders.

  Triage dry-run. One prompt per project across 27 projects, and nothing moves.
"""

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from _index_gen import regenerate
from _lifecycle import apply_move, triage_plan
from _place import KIND_FOLDER, link, place, project_rel
from _vault_walk import build_vault_index, extract_wikilinks, resolve_wikilink
from status import run_status


def _w(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


class TestTheTruthTest(unittest.TestCase):
    """All four seeded failures must appear, ranked, in one status run."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.vault = root / "vault"
        self.code = root / "code"
        self.pdir = self.vault / "projects" / "active" / "demo"
        self._ob = os.environ.pop("OB_VAULT", None)

        # 1. AGENTS.md names a script that is not there.
        _w(self.code / "AGENTS.md",
           "Branch rules are enforced mechanically by "
           "`scripts/enforce-branch-rule.sh`.\n")

        _w(self.pdir / "brief.md",
           "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n"
           "---\n\n# Demo\n\nWhat this project is.\n\n"
           "## Where things are\n| | |\n|---|---|\n")
        _w(self.pdir / "sessions" / "2026-09-01.md",
           "---\ntype: session\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
           "---\n\n## Log\n")

        # 2. A card sits open inside the archive.
        _w(self.pdir / "tasks" / "_archive" / "still-open.md",
           "---\ntype: task\ncreated: 2026-01-01\nupdated: 2026-02-01\n"
           "status: doing\n---\n\n# Still open\n\n## Done when\nIt is done.\n")

        # 3. A decision is superseded with no target.
        _w(self.pdir / "decisions" / "2026-08-01-orphaned.md",
           "---\ntype: decision\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
           "status: superseded\n---\n\n# Orphaned\n")

        # 4. A page is 100 days unverified.
        _w(self.pdir / "docs" / "cache.md",
           "---\ntype: doc\nupdated: 2026-09-01\nverified: 2026-05-24\n"
           "---\n\n# Cache\n")

    def tearDown(self):
        if self._ob is not None:
            os.environ["OB_VAULT"] = self._ob
        self._tmp.cleanup()

    def test_all_four_appear_ranked_in_one_status_run(self):
        report = run_status(self.pdir, code_root=self.code,
                            today=date(2026, 9, 1))
        findings = report["truth"]["findings"]
        kinds = [f["kind"] for f in findings]
        for expected in ("agents-missing-path", "open-card-in-archive",
                         "superseded-without-target", "verified-stale"):
            self.assertIn(expected, kinds, f"{expected} was not found")

        bands = [f["band"] for f in findings]
        rank = {"wrong-now": 0, "going-stale": 1, "worth-a-look": 2}
        self.assertEqual([rank[b] for b in bands],
                         sorted(rank[b] for b in bands),
                         "findings are not ordered by cost of being wrong")

        by_kind = {f["kind"]: f for f in findings}
        self.assertEqual(by_kind["agents-missing-path"]["band"], "wrong-now")
        self.assertEqual(by_kind["open-card-in-archive"]["band"], "wrong-now")
        self.assertEqual(by_kind["superseded-without-target"]["band"], "wrong-now")
        self.assertEqual(by_kind["verified-stale"]["band"], "going-stale")
        self.assertIn("100 days", by_kind["verified-stale"]["detail"])
        self.assertEqual(report["truth"]["counts"]["wrong-now"], 3)

    def test_the_truth_report_writes_nothing_at_all(self):
        # status makes derived state current before reporting, so it may write
        # Home.md and the project index. The truth report never writes.
        from truth import truth_report
        before = sorted(str(p) for p in self.vault.rglob("*"))
        truth_report(self.pdir, vault=self.vault, code_root=self.code,
                     today=date(2026, 9, 1))
        self.assertEqual(sorted(str(p) for p in self.vault.rglob("*")), before)

    def test_agents_md_is_never_rewritten(self):
        original = (self.code / "AGENTS.md").read_text()
        run_status(self.pdir, code_root=self.code, today=date(2026, 9, 1))
        self.assertEqual((self.code / "AGENTS.md").read_text(), original)


class TestLinkRoundTrip(unittest.TestCase):
    """One file of every kind, every link resolving by path, and every link
    still resolving after the project moves between lifecycle folders."""

    KIND_HINTS = {
        "session": {"date": "2026-09-01"},
        "decision": {"date": "2026-09-01", "slug": "drop-bucket-a-tags"},
        "dream": {"date": "2026-09-01"},
        "component": {"slug": "button", "group": "modules"},
    }

    def _one_of_every_kind(self, pdir: Path) -> list:
        made = []
        for kind in sorted(KIND_FOLDER):
            hints = dict(self.KIND_HINTS.get(kind, {"slug": kind.replace("_", "-")}))
            path = place(kind, pdir, hints)
            _w(path, f"---\ntype: {kind}\nupdated: 2026-09-01\n---\n\n# {kind}\n")
            made.append(path)
        return made

    def test_every_link_resolves_before_and_after_a_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            pdir = vault / "projects" / "active" / "demo"
            pdir.mkdir(parents=True)
            made = self._one_of_every_kind(pdir)
            self.assertEqual(len(made), 15)

            # An index of links, one per file, written into a note.
            body = "\n".join(
                f"- {link(project_rel(p, pdir), p.stem)}" for p in made)
            note = pdir / "notes" / "link-index.md"
            _w(note, f"---\ntype: note\nupdated: 2026-09-01\n---\n\n{body}\n")

            targets = [wl.target for wl in extract_wikilinks(note.read_text())]
            self.assertEqual(len(targets), 15)
            for t in targets:
                self.assertFalse(t.startswith("projects/"), t)
                self.assertFalse(t.split("/", 1)[0] in
                                 ("active", "paused", "finished", "archive"), t)

            idx = build_vault_index(vault)
            for t in targets:
                self.assertTrue(resolve_wikilink(t, idx), f"before move: {t}")

            apply_move(vault, "demo", "finished")

            idx = build_vault_index(vault)
            for t in targets:
                self.assertTrue(resolve_wikilink(t, idx), f"after move: {t}")

    def test_a_link_that_names_the_lifecycle_folder_is_refused(self):
        with self.assertRaises(ValueError):
            link("active/demo/notes/a")
        with self.assertRaises(ValueError):
            link("projects/demo/notes/a")


class TestTriageDryRun(unittest.TestCase):
    """27 projects, 27 prompts, and nothing moves."""

    def test_twenty_seven_prompts_and_no_moves(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            for i in range(27):
                zone = ("active", "paused", "finished", "archive")[i % 4]
                pdir = vault / "projects" / zone / f"p{i:02d}"
                _w(pdir / "brief.md",
                   "---\ntype: project\nupdated: 2026-09-01\n"
                   "verified: 2026-09-01\n---\n\n# P\n")
                _w(pdir / "sessions" / "2026-08-30.md",
                   "---\ntype: session\n---\n")
            before = sorted(str(p.relative_to(vault))
                            for p in vault.rglob("brief.md"))
            plan = triage_plan(vault, date(2026, 9, 1))
            self.assertEqual(len(plan), 27)
            after = sorted(str(p.relative_to(vault))
                           for p in vault.rglob("brief.md"))
            self.assertEqual(before, after)

    def test_regenerating_the_indexes_leaves_exactly_one_per_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            for i in range(27):
                pdir = vault / "projects" / "active" / f"p{i:02d}"
                _w(pdir / "brief.md",
                   "---\ntype: project\nupdated: 2026-09-01\n"
                   "verified: 2026-09-01\n---\n\n# P\n")
                _w(pdir / "notes" / "_index.md", "---\ntype: index\n---\n\n# N\n")
            out = regenerate(vault, date(2026, 9, 1))
            self.assertEqual(len(out["deleted"]), 27)
            self.assertEqual(len(out["projects"]), 27)
            survivors = list(vault.rglob("_index.md"))
            self.assertEqual(len(survivors), 27)
            self.assertTrue((vault / "Home.md").is_file())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it**

Run: `cd adjudant/scripts && python3 -m unittest test_structure_acceptance -v`
Expected: PASS, 7 tests. A failure names the exact claim that broke; fix the responsible module rather than relaxing the assertion.

If `TestTheTruthTest.test_all_four_appear_ranked_in_one_status_run` reports more
than three `wrong-now` findings, read them before changing the count: an extra
finding is either a real defect in the fixture or a detector firing where it
should not, and both are worth knowing.

- [ ] **Step 3: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 4: Update the test count in the README**

`adjudant/README.md:66` reads `| Tests | 1176; ... |`. Replace the number with
the new total from the suite output. Line 65 states the validator count; update
that too, from `validate.py`'s own PASS line.

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/test_structure_acceptance.py adjudant/README.md
git commit -m "test(adjudant): acceptance - the truth test, link round-trip, triage dry-run

Four seeded failures - AGENTS.md naming a missing script, a card open in an
archive, a decision superseded with no target, a page 100 days unverified -
must all appear, ranked into three bands, in one status run.

One file of every kind, every link resolving by path, and every link still
resolving after the project moves between lifecycle folders. 27 projects, 27
triage prompts, nothing moved.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 16: Rewrite the standards docs and add the register reminder

The written surface has to say what the code now does. `vault-standards.md` is
84 lines describing a structure that no longer exists, and
`content-markdown.md` is 207 lines that contradict it in places.

**Files:**
- Rewrite: `adjudant/skills/adjudant/reference/vault-standards.md`
- Rewrite: `adjudant/skills/adjudant/reference/content-markdown.md`
- Modify: `adjudant/hooks/scripts/session-start.sh`, `adjudant/hooks/scripts/user-prompt-reminder.sh`
- Modify: `adjudant/scripts/validate.py`
- Test: `adjudant/scripts/test_validate.py`, `adjudant/scripts/test_hook_shell.py`

**Interfaces:**
- Consumes: `KIND_FOLDER` from Task 3; `PROJECT_ZONES` from Task 1; `BANDS` from Task 10.
- Produces: validator 37, `standards-structure-parity`, asserting the standards doc names every folder in `KIND_FOLDER` and every folder in `PROJECT_ZONES`.

- [ ] **Step 1: Write the failing validator test**

Append to `adjudant/scripts/test_validate.py`:

```python
class TestStandardsStructureParity(unittest.TestCase):
    """The standards doc restated every rule in prose, and prose drifts. It
    now links to templates instead, and this holds the one thing it still has
    to state itself: the folder layout."""

    def test_the_standards_doc_names_every_folder(self):
        from _place import KIND_FOLDER
        from _vault_walk import PROJECT_ZONES
        text = (Path(__file__).resolve().parent.parent / "skills" / "adjudant"
                / "reference" / "vault-standards.md").read_text()
        for folder in sorted(set(KIND_FOLDER.values()) - {""}):
            self.assertIn(f"{folder}/", text, f"vault-standards omits {folder}/")
        for zone in PROJECT_ZONES:
            self.assertIn(f"{zone}/", text, f"vault-standards omits {zone}/")

    def test_the_standards_doc_does_not_restate_a_template(self):
        text = (Path(__file__).resolve().parent.parent / "skills" / "adjudant"
                / "reference" / "vault-standards.md").read_text()
        self.assertNotIn("required:", text,
                         "a field table here is a second declaration; link to "
                         "the template instead")

    def test_the_markdown_doc_states_one_rule_per_element(self):
        text = (Path(__file__).resolve().parent.parent / "skills" / "adjudant"
                / "reference" / "content-markdown.md").read_text()
        for element in ("Headings", "Lists", "Emphasis", "Code", "Tables",
                        "Callouts", "Links", "Mermaid", "Emoji", "Register"):
            self.assertIn(f"## {element}", text, f"no rule for {element}")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_validate.TestStandardsStructureParity -v`
Expected: FAIL — `vault-standards omits docs/`

- [ ] **Step 3: Rewrite `vault-standards.md`**

Replace `adjudant/skills/adjudant/reference/vault-standards.md` in full with a
document of four sections and no field tables:

```markdown
# Vault standards

Structure, naming and links. Field shapes are not here: the template file is
the only declaration of a kind's shape, and this document links to it rather
than restating it. Every rule stated twice is a rule that drifts.

## 1. Structure

    {vault}/
      Home.md                      generated
      projects/
        active/ paused/ finished/ archive/
          {slug}/
            brief.md  _handoff.md  _index.md
            sessions/     2026-09-01.md
            decisions/    2026-09-01-drop-bucket-a-tags.md
            tasks/        rebuild-board-deck.md
            notes/        cold-cache-quadratic.md
            docs/         cache.md  bug-log.md  glossary.md
            specs/        spec-018-page-spinup.md
            components/   modules/button.md
            api/          contacts.md
            schemas/      ep-object.md
            sources/      attribution-test-runbook.md
            releases/     v2.1.0.md
            dreams/       2026-09-01.md
            images/

A folder exists when something is in it. One level of grouping inside a
folder, never two. The folder for each kind is `KIND_FOLDER` in
`scripts/_place.py`, and `place()` is the only thing that decides a path.

## 2. Lifecycle

Four folders: `active/`, `paused/`, `finished/`, `archive/`. The folder is the
project's lifecycle state, and there is no `status:` field on a brief. Moves
happen through the guided triage in `/adjudant status`, one project at a time.

## 3. Naming

Kebab-case everywhere, no exceptions. Dated kinds keep the date prefix;
numbered kinds keep the number. Where a filename carries a date, `created:` is
derived from it at write time and `status` asserts the two match.

## 4. Links

Wikilinks with the project-relative path and a display alias for anything in
the vault; markdown links for anything outside it. The lifecycle folder is
omitted:

    [[hubspot-nightly/decisions/2026-08-12-branch-track|branch track]]

Obsidian resolves by matching the end of a path, so a project moving between
folders breaks nothing. `link()` in `scripts/_place.py` is the only thing that
writes one, and it refuses a target that names a lifecycle folder.

## 5. The kinds

Fifteen. Each one's shape is declared by its template and nowhere else:

    project   session   decision  task     note
    doc       source    spec      handoff  index
    release   dream     component api      schema

See `../templates/`. A runbook, a glossary, a standard and a bug log are all
written as a `doc`: a thing gets its own kind only when it needs a line at the
top that a plain page does not have.

## 6. Markdown elements

One rule per element, in `content-markdown.md`.
```

- [ ] **Step 4: Rewrite `content-markdown.md`**

Replace `adjudant/skills/adjudant/reference/content-markdown.md` in full with
one rule per element, each as an `## ` heading, in the spec's order: Headings,
Lists, Emphasis, Code, Tables, Callouts, Links, Mermaid, Emoji, Register.
Copy the rules verbatim from the spec's "Markdown element standards" section —
one H1 and only where a document needs one, `-` for bullets and `1.` for
ordered, `*italic*` and `**bold**` and never the underscore forms, fenced code
with a language tag and never four-space indentation, tables for three or more
parallel attributes with pipes escaped, `> [!note]` and `> [!warning]` only,
wikilinks per `vault-standards.md` section 4, mermaid for flow and sequence and
state only, no emoji as semantic markup with the handoff traffic light as the
one documented exception, and ASD-STE100 across every write.

Delete every paragraph that describes folder structure, frontmatter fields or
index files: `vault-standards.md` owns the first, the templates own the second,
and the third no longer exists.

- [ ] **Step 5: Add the register reminder**

In `adjudant/hooks/scripts/session-start.sh`, inside the block that already
prints the vault breadcrumb line, add one line:

```bash
  printf -- '- Register: ASD-STE100 for vault writes. One instruction per sentence, active voice, present tense, under twenty words.\n'
```

In `adjudant/hooks/scripts/user-prompt-reminder.sh`, the `intent_nag` function
fires at most once per session from the second prompt on. Leave it alone and
add nothing: the register reminder belongs at session start, where it is read
once, and a per-turn copy is the ceremony this whole plan removes.

Append to `adjudant/scripts/test_hook_shell.py`:

```python
    def test_session_start_states_the_register_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, home = self._project(
                Path(tmp), "vault_path: {vault}\nvault_name: vault\nslug: demo\n")
            r = _run("session-start.sh", project, home,
                     stdin=json.dumps({"session_id": "s1", "source": "startup"}))
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.count("ASD-STE100"), 1)
```

- [ ] **Step 6: Extend the validator over templates and reference docs**

Add to `adjudant/scripts/validate.py`:

```python
def check_standards_structure_parity(r: "Result") -> None:
    """37. standards-structure-parity — the standards doc names every folder.

    The doc used to restate every field rule in prose, which made it a second
    declaration that drifted from the templates. It now links to them, so the
    one thing it still states alone is the folder layout — and that is what
    this holds.
    """
    name = "standards-structure-parity"
    from _place import KIND_FOLDER
    doc = REFERENCE / "vault-standards.md"
    if not doc.is_file():
        r.add_fail(name, "reference/vault-standards.md missing")
        return
    text = doc.read_text(errors="replace")
    missing = [f"{f}/" for f in sorted(set(KIND_FOLDER.values()) - {""})
               if f"{f}/" not in text]
    missing += [f"{z}/" for z in PROJECT_ZONES if f"{z}/" not in text]
    if missing:
        r.add_fail(name, "vault-standards.md omits: " + ", ".join(missing))
        return
    if "required:" in text:
        r.add_fail(name, "vault-standards.md restates a template's field set")
        return
    r.add_pass(name)
```

Register it, add
`37. standards-structure-parity  : reference/vault-standards.md names every folder in KIND_FOLDER and PROJECT_ZONES`
to the module docstring, and bump the total.

Validator 24 (`voice-lexicon`) already scans `templates/` and `reference/` for
banned terms and em dashes; the two rewritten documents go through it
unchanged, so run it before committing.

- [ ] **Step 7: Run the tests and the validators**

Run: `cd adjudant/scripts && python3 -m unittest test_validate test_hook_shell -v 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`. Validator 16 (`reference-doc-links`) checks that every relative markdown link inside `reference/*.md` resolves; the rewritten documents link to `../templates/` and `content-markdown.md`, both of which exist.

- [ ] **Step 8: Run the full suite**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 9: Commit**

```bash
git add adjudant/skills/adjudant/reference/vault-standards.md adjudant/skills/adjudant/reference/content-markdown.md adjudant/hooks/scripts/session-start.sh adjudant/scripts/validate.py adjudant/scripts/test_validate.py adjudant/scripts/test_hook_shell.py
git commit -m "docs(adjudant): standards docs describe the v3 structure, and stop restating templates

vault-standards.md is now structure, lifecycle, naming and links, and links to
the templates rather than repeating their field sets - the second declaration
that drifted. content-markdown.md is one rule per element and nothing else.

The ASD-STE100 register is stated once at session start, not per turn: a
reminder that fires every turn is the ceremony this plan removes.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 17: `clean` offers the `references/` split

`references/` holds six unrelated things: api pages, schemas, specs, sections,
component inventories and imported wiki pages. Each now has a folder that names
it. This is the last consumer of `place()`, and the only one that moves files
that already exist.

**Files:**
- Modify: `adjudant/scripts/clean.py` (a new detector and its preview entry)
- Test: `adjudant/scripts/test_clean.py`

**Interfaces:**
- Consumes: `place`, `project_rel`, `KIND_FOLDER` from Task 3; `build_vault_index`, `resolve_wikilink` from Task 5.
- Produces:
  - `plan_references_split(project_dir: Path) -> list[dict]` in `clean.py`, each entry `{"from": str, "to": str, "type": str}` with project-relative paths. Reads only.
  - `apply_references_split(project_dir: Path, moves: list[dict]) -> list[dict]` moving the files and rewriting every link that named the old path, returning `{"from", "to", "links_repointed"}` per move.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_clean.py`:

```python
class TestReferencesSplit(unittest.TestCase):
    """references/ held api pages, schemas, specs, sections, component
    inventories and imported wiki pages at once. Each now has a folder that
    names it, and clean offers the move rather than making it."""

    def _project(self, tmp: Path) -> Path:
        pdir = tmp / "vault" / "projects" / "active" / "demo"
        (pdir / "references").mkdir(parents=True)
        _w(pdir / "brief.md",
           "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n# D\n")
        for name, kind in (("contacts.md", "api"), ("ep-object.md", "schema"),
                           ("spec-018-page-spinup.md", "spec"),
                           ("button.md", "component"),
                           ("wiki-runbook.md", "source")):
            _w(pdir / "references" / name,
               f"---\ntype: {kind}\nupdated: 2026-09-01\n---\n\n# {name}\n")
        return pdir

    def test_the_plan_routes_each_file_by_its_own_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._project(Path(tmp))
            plan = {m["from"]: m["to"] for m in plan_references_split(pdir)}
            self.assertEqual(plan["references/contacts.md"], "api/contacts.md")
            self.assertEqual(plan["references/ep-object.md"],
                             "schemas/ep-object.md")
            self.assertEqual(plan["references/spec-018-page-spinup.md"],
                             "specs/spec-018-page-spinup.md")
            self.assertEqual(plan["references/button.md"],
                             "components/button.md")
            self.assertEqual(plan["references/wiki-runbook.md"],
                             "sources/wiki-runbook.md")

    def test_the_plan_moves_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._project(Path(tmp))
            before = sorted(str(p) for p in pdir.rglob("*"))
            plan_references_split(pdir)
            self.assertEqual(sorted(str(p) for p in pdir.rglob("*")), before)

    def test_a_file_with_no_home_is_left_where_it_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._project(Path(tmp))
            _w(pdir / "references" / "loose.md",
               "---\ntype: note\nupdated: 2026-09-01\n---\n\n# Loose\n")
            froms = [m["from"] for m in plan_references_split(pdir)]
            self.assertNotIn("references/loose.md", froms)

    def test_apply_moves_the_files_and_repoints_the_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = self._project(root)
            _w(pdir / "notes" / "uses.md",
               "---\ntype: note\nupdated: 2026-09-01\n---\n\n"
               "See [[demo/references/contacts|contacts]] and "
               "[[demo/references/ep-object]].\n")
            moves = plan_references_split(pdir)
            receipts = apply_references_split(pdir, moves)
            self.assertTrue((pdir / "api" / "contacts.md").is_file())
            self.assertFalse((pdir / "references" / "contacts.md").exists())
            body = (pdir / "notes" / "uses.md").read_text()
            self.assertIn("[[demo/api/contacts|contacts]]", body)
            self.assertIn("[[demo/schemas/ep-object]]", body)
            self.assertNotIn("demo/references/", body)
            repointed = {r["from"]: r["links_repointed"] for r in receipts}
            self.assertEqual(repointed["references/contacts.md"], 1)

    def test_every_link_still_resolves_after_the_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            pdir = self._project(root)
            _w(pdir / "notes" / "uses.md",
               "---\ntype: note\nupdated: 2026-09-01\n---\n\n"
               "See [[demo/references/contacts|contacts]].\n")
            apply_references_split(pdir, plan_references_split(pdir))
            idx = build_vault_index(vault)
            for wl in extract_wikilinks((pdir / "notes" / "uses.md").read_text()):
                self.assertTrue(resolve_wikilink(wl.target, idx), wl.target)

    def test_the_split_creates_no_new_vault_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = self._project(Path(tmp))
            before = len([p for p in pdir.rglob("*") if p.is_file()])
            apply_references_split(pdir, plan_references_split(pdir))
            after = len([p for p in pdir.rglob("*") if p.is_file()])
            self.assertEqual(after, before, "clean must never add a vault file")
```

Add `plan_references_split`, `apply_references_split` to the `clean` import
block at the top of `test_clean.py`, and
`from _vault_walk import build_vault_index, extract_wikilinks, resolve_wikilink`
if the file does not already carry them.

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_clean.TestReferencesSplit -v`
Expected: FAIL with `ImportError: cannot import name 'plan_references_split' from 'clean'`

- [ ] **Step 3: Write the split**

Add to `adjudant/scripts/clean.py`:

```python
# ============================================================
# The references/ split
# ============================================================
#
# `references/` held six unrelated things at once: api pages, schemas, specs,
# sections, component inventories and imported wiki pages. Each of the six now
# has a folder that names it, and a file's own `type:` says which. A move is
# not a create, so this stays inside clean's contract: it may delete, merge
# and rewrite in place, and may not add a vault file.


def plan_references_split(project_dir: Path) -> list[dict[str, str]]:
    """Where each file in `references/` belongs, by its own `type:`.

    Reads only. A file whose type has no folder of its own is left where it
    is and reported nowhere: guessing is what produced `references/` in the
    first place.
    """
    src = project_dir / "references"
    if not src.is_dir():
        return []
    out: list[dict[str, str]] = []
    for f in sorted(src.rglob("*.md")):
        if f.name.startswith("_"):
            continue
        try:
            fm, _body = parse_frontmatter(f.read_text(errors="replace"))
        except OSError:
            continue
        ftype = fm.fields.get("type")
        if not isinstance(ftype, str):
            continue
        folder = KIND_FOLDER.get(ftype)
        if not folder or folder == "references":
            continue
        out.append({
            "from": f.relative_to(project_dir).as_posix(),
            "to": f"{folder}/{f.name}",
            "type": ftype,
        })
    return out


def apply_references_split(project_dir: Path,
                           moves: list[dict[str, str]]) -> list[dict]:
    """Move each file and repoint every link that named its old path.

    The link rewrite is a project-local string substitution on the zone-less
    form `{slug}/references/{stem}`, which is the only form v3 writes. It runs
    over every markdown file in the project, including the ones being moved.
    """
    slug = project_dir.name
    receipts: list[dict] = []
    for move in moves:
        src = project_dir / move["from"]
        dest = project_dir / move["to"]
        if not src.is_file() or dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)
        old_target = f"{slug}/{move['from'][:-3]}"
        new_target = f"{slug}/{move['to'][:-3]}"
        repointed = 0
        for f in sorted(project_dir.rglob("*.md")):
            try:
                text = f.read_text(errors="replace")
            except OSError:
                continue
            if old_target not in text:
                continue
            repointed += text.count(old_target)
            f.write_text(text.replace(old_target, new_target))
        receipts.append({"from": move["from"], "to": move["to"],
                         "links_repointed": repointed})
    try:
        (project_dir / "references").rmdir()   # only when it is now empty
    except OSError:
        pass
    return receipts
```

Add `from _place import KIND_FOLDER` to `clean.py`'s imports. `parse_frontmatter`
is already imported there (it was at `tidy.py:53` and survives Task 8's
deletions, which leave its uses at `tidy.py:667` and `:1079` in place).

- [ ] **Step 4: Wire the split into the preview**

In `clean.py`'s `build_preview`, add a `references_split` key to the change-set
built from `plan_references_split(project_dir)`, render it in the preview
summary as one line per move, and call `apply_references_split` from
`apply_preview` when the change-set carries it. The split is offered, never
forced: an empty list means the project has no `references/` and the key is
absent from the summary entirely.

- [ ] **Step 5: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test_clean -v 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 6: Run the full suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 7: Commit**

```bash
git add adjudant/scripts/clean.py adjudant/scripts/test_clean.py
git commit -m "feat(adjudant): clean offers the references/ split, and repoints the links

references/ held api pages, schemas, specs, sections, component inventories
and imported wiki pages at once. Each of the six now has a folder that names
it, and a file's own type: says which. Files with no home stay put: guessing
is what produced references/ in the first place.

A move is not a create, so this stays inside clean's contract - it may delete,
merge and rewrite in place, and may not add a vault file.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Done when

- `python3 -m unittest discover -p 'test_*.py'` from `adjudant/scripts/` reports `OK`.
- `python3 adjudant/scripts/validate.py` from the repo root reports `PASS`.
- `test_structure_acceptance.py` passes all seven tests.
- `projects/` holds four named folders, and `grep -rn '"_fridge"' adjudant/scripts/*.py adjudant/hooks/scripts/*` returns only the legacy-read constants in `_vault_walk.py` and the two hook fallbacks.
- `_place.link` is the only thing in the tree that emits `[[`: `grep -rn '\[\[' adjudant/scripts/*.py adjudant/hooks/scripts/*.py` returns only `_place.py`, the parsers in `_vault_walk.py`, and test fixtures.
- A fresh `connect` leaves exactly two files in the vault project: `brief.md` and the breadcrumb's session note when a write happens.
- `resolve_wikilink("brief", build_vault_index(vault))` is `False` for any vault with a project in it.
- One `_index.md` exists per project and one `Home.md` per vault, and nothing else matches `_index.md` under `projects/`.
- `Home.md` carries `type: vault-home`, so `resolve_vault` finds the vault from a subdirectory. This closes the spec's loose end where the file said `cabinet-home` and the resolver looked for `vault-home`.
- `status --triage` prints one row per project and the vault is byte-identical afterwards.
- `run_status(...)["truth"]["findings"]` is ordered by band, and `counts` has exactly the three `BANDS` keys.
- `~/.claude/statusline-v2.sh` renders against a fixture breadcrumb with no stderr, and shows a folder badge for a paused project.

## Not in this plan

- **Templates and the schema** are plan 2: the fifteen template files, parsing `FIELD_SCHEMA` out of them, deleting the four inline fallbacks, routing every machine writer through one `render(template, fields)`, and the vocabulary migrations. This plan assumes all of it has landed and reads `FIELD_SCHEMA` as the template-derived truth — `verified_kinds()` in Task 11 is the direct dependency.
- **The verb surface** is plan 3: sunsetting `port`, merging `tidy` and `ramasse` into `clean`, folding `sync`, `sitrep`, `check`, `kebab` and `advisor` into `status`, deleting `shelf.py` including its 380-line vault-wide link rewrite, rebuilding `dream` for precision, and the bare-`/adjudant` menu. This plan writes against `status.py` and `clean.py` as plan 3 leaves them.
- **Twin generation** is plan 5: moving forked constants out of `_vault_walk.py` into a data file, capability-gating the environment probes, the audience field per verb, generating the router table and README verb table, and wiring the twin's validators to pre-commit.
- **The net-subtractive test** — `clean` on a copied project must reduce both file count and byte count — belongs with plan 3, which builds `clean`. Task 17 here asserts only the half this plan creates: the `references/` split adds no vault file.
- **HubSpot Nightly's own remediation** is a separate session by explicit decision. Its findings drove this design and are cited throughout, but no task here touches that vault.
