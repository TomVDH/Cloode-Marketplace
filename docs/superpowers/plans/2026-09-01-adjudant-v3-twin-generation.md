# Adjudant v3, Plan 5: Twin Generation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The public twin in `furtive-follies` stops being a hand-maintained fork and becomes generated from one source, with no line of code that exists in only one tree.

**Architecture:** Everything that legitimately differs between the two builds moves into a single data file per tree, `adjudant/scripts/build-profile.json`: the cost threshold, the tag rules, the environment capabilities, and which audience the build serves. Everything derived from the verb list — ten hand-edited doc surfaces across four files in two repos — is rendered from `scripts/command-metadata.json` by one script and enforced by one validator. A generator then copies the shared tree across, and refuses to delete anything it cannot name a reason for.

**Tech Stack:** Python 3.9+ stdlib only, bash hooks, `unittest`, `pre-commit`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-01-adjudant-v3-design.md` (settled decision 9, phase 5, and the execution split that flags this plan as the irreversible one)

**Assumes:** Plans 1 through 4 have landed. That means the guided-vault-setup back-port (plan 1 task 1), the out-of-vault scratch path, the hook diet, template-as-schema, the six-verb surface with `port`/`shelf`/`kebab`/`ramasse`/`advisor` sunset, and the lifecycle folders are all in `main`. This plan is the last of the five and the only one that writes into a second repository.

## Context: the twin is not a subset of main

**Read this before touching anything.**

The twin contains net-new code that exists nowhere else. Before plan 1, `suggest_vault_roots()` and `_describe_vault_root()` lived only in `furtive-follies/adjudant/scripts/_vault_walk.py:571-616`, and `--suggest-vaults` / `--create-vault` lived only in `furtive-follies/adjudant/scripts/connect.py:812-845`. Plan 1 task 1 back-ports the Python. **It does not back-port the prose**: the twin's `skills/adjudant/reference/connect.md` carries an 18-line section, "No vault yet? Guided location setup", that main has never had, and it is the runbook the model follows to actually use those flags.

That guided flow is the centrepiece of the twin's `GETTING-STARTED.md` section 4 and of the field guide's "Where your vault should live". A regeneration that runs before the back-port is complete deletes the entire guided-onboarding story and looks like a clean success while doing it. Task 1 exists solely to make that impossible, and it fails loudly rather than warning.

Nothing in tasks 2 through 10 may run until task 1 is green.

### Drift found by inspection, beyond what the spec names

A full `diff -rq` between the two `adjudant/` trees (excluding `__pycache__`) turned up four categories the spec's phase 5 does not mention. All four are handled here.

| Drift | Where | Handled by |
|---|---|---|
| The cost threshold is forked in **two** places, not one | `_cost.py:27` (30000 / 10000) **and** `connect.py:286`, the breadcrumb default written at connect time | Task 2 |
| The threshold is also stated in prose in two docs | `SKILL.md:54` ("30000 estimated read tokens") and `reference/connect.md:27` (`cost_warn_tokens: 30000`) | Task 2 |
| The twin **sanitises test fixtures**: `hubspot-nightly` → `acme-web`, `nightly` → `acme`, `ob/cabinet` → `ob/legacy`, "Tom" → "we"/"a real vault", across `test__vault_walk.py`, `test_tidy.py`, `test_renest_memory.py` | six files | Task 4 |
| `validate.py`'s deprecated-tag patterns are forked (`#ob/` + `#cabinet/` in main, `#ob/` alone in the twin), and `reference/internals.md` cites validator numbers that follow from the roster length (main "24 + 33 / 34", twin "21 + 30 / 31") | `validate.py:100-105`, `internals.md:44-46` | Tasks 2 and 8 |

Two more findings that need no code, only awareness:

- **The twin's checked-out branch is `onboarding`, 37 commits ahead of `master`, and `origin/HEAD` points at `master`.** A marketplace install pulls the default branch. Generating onto `onboarding` publishes nothing. Task 9 step 1 blocks on this.
- **The twin's own `README.md:45-58` still advertises the suitcase onboarding kit** while its `check.py` and `sitrep.py` have had the suitcase probe stripped out. The capability registry in task 3 makes that a data choice rather than a code fork, so the twin can advertise the kit and probe for it, or neither, without a second copy of the code.

### The `resolve_vault` fork, and the ruling

`resolve_vault` has five resolution steps in main (`_vault_walk.py:596-660`) and four in the twin (`:619`). Main's extra step 4 reads a legacy `.claude/obsidian-bridge` breadcrumb — the retired predecessor plugin's file.

**Ruling: the generated twin gets the twin's four-step semantics, and main narrows to match.** The evidence:

1. The only other consumer of that breadcrumb was `port.py`, which **plan 3 deletes**. After plan 3 a resolved legacy breadcrumb has nowhere to go: adjudant would quietly work from a stale path with no migration path offered.
2. It is already untested in main. Every `obsidian-bridge` test lives in `test_port.py`, which plan 3 also deletes. Keeping step 4 would leave untested, unmigratable code in the one module every verb imports.
3. Silently resolving it is the exact behaviour the spec forbids elsewhere: "an off-vocabulary value is reported, never coerced".

Task 5 removes the step from the shared source and replaces it with a `status` finding that names the situation out loud, so the user is told to run `/adjudant connect` instead of being served a stale path they never see.

## Global Constraints

- **Stdlib only.** No new dependencies, in any task, in either repo.
- **Python 3.9 floor.** No `match`, no runtime `X | Y` unions. `from __future__ import annotations` is in every module and stays, so annotations are never evaluated.
- **Test suite:** `python3 -m unittest discover -p 'test_*.py'` from `adjudant/scripts/` in each repo. Verified baselines on 2026-09-01, before plans 1-4: **main 1233 tests, twin 995**, both `OK`. Plans 1-4 move both numbers; use the number the suite prints, never a remembered one.
- **Validators:** `python3 adjudant/scripts/validate.py` from each repo root. Verified baselines: **main 35 green, twin 31 green**. After this plan the two rosters are byte-identical, so the counts are equal by construction.
- **The twin path** is `$ADJUDANT_TWIN`, defaulting to the sibling directory `../furtive-follies`. Never hard-code an absolute path in committed code.
- **No file in `adjudant/` may differ between the trees** except the seven named in `EXPECTED_DIVERGENCE` (task 9). Every other difference is a bug this plan exists to remove.
- **Never write to the real vault during tests.** Every test builds a temp tree and pops `OB_VAULT` from the environment.
- **`render-voice` (validator 34) scans every string literal in `adjudant/scripts/*.py`** that is not a `test_*` file, `_voice.py`, or `validate.py`. The new modules are scanned. Keep their prose free of the banned lexicon (`leverage`, `seamless`, `unlock`, `journey`, `empower`, `deep dive`, `delve`, `elevate`, `game-changer`, `cutting-edge`, `circle back`, `synergy`, `at the end of the day`, `forward-thinking`, `load-bearing`, `hand-wave`, `double-click`). Em dashes are legal in helper strings; they are banned only in `templates/`.
- **Commit style:** Conventional Commits, scope `adjudant` or `marketplace`. End every commit message with:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
- **Two repositories, two commits.** A change that touches both trees is committed in each, with the same subject line. Never leave one tree committed and the other dirty.

## File Structure

| File | Responsibility |
|---|---|
| `adjudant/scripts/build-profile.json` | **New, one per tree.** The only file a build is allowed to differ in: `audience`, `description_suffix`, `cost_warn_tokens`, the four tag rules, and the capability registry. |
| `adjudant/scripts/_profile.py` | **New.** Loads and types `build-profile.json`. No fallback: a missing profile raises. Also the CLI the SessionStart hook calls for capability banners. |
| `adjudant/scripts/test__profile.py` | **New.** Tests for the above. |
| `adjudant/scripts/render_verb_surfaces.py` | **New.** Renders the ten verb-derived doc surfaces from `command-metadata.json` filtered by the profile's audience. `--check` mode for the validator. |
| `adjudant/scripts/test_render_verb_surfaces.py` | **New.** Tests for the above. |
| `adjudant/scripts/test_no_personal_identifiers.py` | **New.** Fails if any file under `adjudant/` outside the profile names the author's projects, crew, or marketplace. |
| `adjudant/scripts/test_twin_parity.py` | **New.** Byte-compares the two trees and requires every difference to be named. Skips when the twin is absent. |
| `adjudant/scripts/_vault_walk.py` | Tag constants come from the profile. `resolve_vault` drops its legacy-breadcrumb step. |
| `adjudant/scripts/_cost.py` | `DEFAULT_WARN_TOKENS` comes from the profile. |
| `adjudant/scripts/connect.py` | The breadcrumb's `cost_warn_tokens` default comes from `_cost`, not a literal. |
| `adjudant/scripts/status.py` | The capability probe becomes a registry lookup. (Was `check.py` + `sitrep.py` before plan 3 folded them.) |
| `adjudant/scripts/validate.py` | Deprecated-tag patterns come from the profile. Gains `verb-surfaces-generated`. |
| `adjudant/hooks/scripts/session-start.sh` | The suitcase pointer becomes one call into `_profile.py --session-banner`. |
| `adjudant/skills/adjudant/SKILL.md` | Four generated regions plus two generated frontmatter fields. |
| `adjudant/README.md` | One generated region. |
| `adjudant/skills/adjudant/reference/connect.md` | Gains the twin's guided-setup section (task 1). Stops naming the threshold number (task 2). |
| `adjudant/skills/adjudant/reference/internals.md` | The suitcase section becomes an audience-neutral capability section. |
| `scripts/generate_twin.py` | **New, main repo root.** Copies the shared tree, writes the twin's profile and metadata, and refuses any deletion it cannot justify from data. |
| `scripts/test_generate_twin.py` | **New, main repo root.** Tests for the above. |
| `<twin>/.pre-commit-config.yaml` | **New.** The twin gets the gate it has never had. |
| `<twin>/scripts/bump_plugin_version.py` | **New.** Byte-identical copy of main's, with its test. |
| `<twin>/RELEASING.md` | **New.** The field guide's regeneration rule, and nothing else. |

---

## Task 1: Prove plan 1's back-port landed, and finish it

Nothing else in this plan may run until this task is green. Plan 1 back-ported the Python; the runbook that drives it is still only in the twin.

**Files:**
- Create: `adjudant/scripts/test_backport_guard.py`
- Modify: `adjudant/skills/adjudant/reference/connect.md` (insert after the resolution-order table, currently ending at line 51)
- Test: the new file is the test

**Interfaces:**
- Consumes: `suggest_vault_roots() -> list[dict]` and `_describe_vault_root(root: Path, home: Path, is_local: bool) -> str` in `adjudant/scripts/_vault_walk.py`, plus `--suggest-vaults` and `--create-vault` on `connect.cli_main`, all from plan 1 task 1.
- Produces: nothing importable. Tasks 8 and 9 import `test_backport_guard.BACKPORT_MARKERS` to gate the generator.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_backport_guard.py`:

```python
"""The twin's guided vault setup must exist in main before any regeneration.

Before v3 the twin held the only copy of suggest_vault_roots(), --create-vault,
and the runbook that drives them. Plan 1 back-ported the Python. This module is
the standing proof that all four pieces are here, because a regeneration that
runs without them deletes the twin's whole onboarding story and reports success.

BACKPORT_MARKERS is the machine-readable form: scripts/generate_twin.py refuses
to run when any entry is missing.
"""

import inspect
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# path relative to the plugin root -> substring that proves the back-port
BACKPORT_MARKERS = {
    "scripts/_vault_walk.py": "def suggest_vault_roots(",
    "scripts/connect.py": "--suggest-vaults",
    "skills/adjudant/reference/connect.md": "No vault yet? Guided location setup",
}


def missing_markers(plugin_root: Path = PLUGIN_ROOT) -> list[str]:
    """Which back-port markers are absent. Empty means the back-port is whole."""
    gone = []
    for rel, marker in sorted(BACKPORT_MARKERS.items()):
        path = plugin_root / rel
        try:
            text = path.read_text()
        except OSError:
            gone.append(f"{rel}: unreadable")
            continue
        if marker not in text:
            gone.append(f"{rel}: missing {marker!r}")
    return gone


class TestBackportIsWhole(unittest.TestCase):

    def test_every_marker_present(self):
        self.assertEqual(missing_markers(), [],
                         "plan 1's back-port is incomplete; do not regenerate the twin")

    def test_suggest_vault_roots_returns_the_documented_shape(self):
        from _vault_walk import suggest_vault_roots
        for entry in suggest_vault_roots():
            self.assertTrue(Path(entry["path"]).is_dir(), entry["path"])
            self.assertTrue(entry["label"])
            self.assertIn(entry["kind"], ("local", "cloud"))
            self.assertIsInstance(entry["recommended"], bool)

    def test_describe_vault_root_takes_three_arguments(self):
        from _vault_walk import _describe_vault_root
        params = list(inspect.signature(_describe_vault_root).parameters)
        self.assertEqual(params, ["root", "home", "is_local"])

    def test_connect_accepts_both_guided_flags(self):
        import connect
        source = Path(inspect.getsourcefile(connect)).read_text()
        self.assertIn("--suggest-vaults", source)
        self.assertIn("--create-vault", source)

    def test_the_runbook_names_the_flags_it_drives(self):
        # A doc that says "guided setup" without naming the flags cannot be
        # followed. This is the half plan 1 did not back-port.
        doc = (PLUGIN_ROOT / "skills" / "adjudant" / "reference" / "connect.md").read_text()
        self.assertIn("--suggest-vaults", doc)
        self.assertIn("--create-vault", doc)
        self.assertIn("cloud-sync", doc)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to see which half is missing**

Run: `cd adjudant/scripts && python3 -m unittest test_backport_guard -v`
Expected: FAIL on `test_every_marker_present` and `test_the_runbook_names_the_flags_it_drives`, both naming `skills/adjudant/reference/connect.md`. The three Python tests pass, because plan 1 landed the code.

If `test_suggest_vault_roots_returns_the_documented_shape` or `test_connect_accepts_both_guided_flags` fails instead, **plan 1 task 1 did not land. Stop. Do not continue this plan.** Report which marker is missing and go back to plan 1.

- [ ] **Step 3: Back-port the runbook**

Insert into `adjudant/skills/adjudant/reference/connect.md` immediately after the resolution-order table (after the `| Project display name | prompt once if creating new |` row, currently line 51) and before `## Idempotent behavior`:

```markdown
## No vault yet? Guided location setup

People keep their notes in different places, and many will not have a vault at all. When the vault cannot be resolved (no `OB_VAULT`, no breadcrumb, no `Home.md` up the tree), do NOT guess a path. Walk the user through choosing one:

1. Run `connect.py --suggest-vaults`. It prints the vault-location options that exist on THIS machine as JSON: cloud-sync roots first (`recommended: true`), then local-only folders.
2. Present them as a short numbered list. Recommend a **cloud-sync** root (iCloud Drive, OneDrive, Google Drive, Dropbox) so the vault follows the user across machines; note that a **local** folder (`~/Documents`) is fine for a single machine. The user may also type any absolute path.
3. Ask for a vault name (default `Claude Vault`). The vault will live at `<chosen root>/<vault name>`.
4. Create and scaffold it in one step:

   ```
   connect.py --project-root {code root} --vault-path "<root>/<vault name>" --create-vault --purpose "..." [flags]
   ```

   `--create-vault` makes the directory (and its `projects/` folder) when it does not exist; connect then scaffolds the project inside it as usual, and writes the breadcrumb so later sessions resolve it silently.

If a vault already resolves, skip all of this: connect uses it without asking.
```

Then update the resolution-order table's `Vault path` row so its last step names the new section instead of a bare prompt:

```markdown
| Vault path | `--vault-path` arg → `OB_VAULT` env var → `--vault-name` arg → existing breadcrumb → walk parent dirs for `Home.md` with `type: vault-home` → guided location setup (see below) |
```

- [ ] **Step 4: Run the guard and the doc-link validator**

Run: `cd adjudant/scripts && python3 -m unittest test_backport_guard -v`
Expected: PASS, 5 tests.

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`. The `reference-doc-links` validator walks every relative link in `reference/*.md`; the new section adds no links, so it stays green.

- [ ] **Step 5: Run the full suite**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | grep -E "^Ran |^OK|^FAILED"`
Expected: `OK`, five more tests than the plan-4 baseline.

- [ ] **Step 6: Commit**

```bash
git add adjudant/scripts/test_backport_guard.py adjudant/skills/adjudant/reference/connect.md
git commit -m "feat(adjudant): back-port the guided-setup runbook, and guard the whole back-port

Plan 1 back-ported suggest_vault_roots() and --create-vault but not the
reference/connect.md section that tells the model how to use them, so the twin
still held the only copy of the runbook. Both halves are here now, and
test_backport_guard is the standing proof: generate_twin.py reads
BACKPORT_MARKERS and refuses to run when any of the three is missing.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: The build profile, and the end of forked constants

**Files:**
- Create: `adjudant/scripts/build-profile.json`, `adjudant/scripts/_profile.py`, `adjudant/scripts/test__profile.py`
- Modify: `adjudant/scripts/_vault_walk.py:836-868` (the tag-constant block, `# Bucket B` comment through `_BUCKET_B_KEYS`) and `:1533-1552` (`is_bucket_d_tag`)
- Modify: `adjudant/scripts/_cost.py:14` (docstring), `:27` (`DEFAULT_WARN_TOKENS = 30000`)
- Modify: `adjudant/scripts/connect.py:286` (the breadcrumb default)
- Modify: `adjudant/scripts/validate.py:100-105` (`DEPRECATED_TAG_PATTERNS`), `:8` (roster line 2)
- Modify: `adjudant/skills/adjudant/SKILL.md:54`, `adjudant/skills/adjudant/reference/connect.md:27`
- Test: `adjudant/scripts/test__profile.py`, `adjudant/scripts/test__vault_walk.py` (class `TestBucketDClassification`, line 375), `adjudant/scripts/test_cost.py`, `adjudant/scripts/test_connect.py`

Line numbers are as of 2026-09-01, before plans 1-4 shifted them. The symbol names are authoritative; locate with `grep -n`.

**Interfaces:**
- Consumes: nothing from task 1.
- Produces, used by tasks 3, 5, 6, 8 and 9:
  - `_profile.PROFILE_PATH: Path` — `scripts/build-profile.json` beside the module.
  - `_profile.ProfileError(RuntimeError)`
  - `_profile.load(path: Optional[Path] = None) -> dict` — cached per resolved path.
  - `_profile.audience() -> str` — `"full"` or `"public"`.
  - `_profile.description_suffix() -> str`
  - `_profile.cost_warn_tokens() -> int`
  - `_profile.tag_rules() -> TagRules` — a `NamedTuple` with fields `bucket_b_migrations: dict[str, str]`, `bucket_b_prefixes: tuple[str, ...]`, `bucket_d_tag_prefixes: tuple[str, ...]`, `vague_topical_tags: frozenset[str]`, `crew_names: frozenset[str]`.
  - `_profile.capabilities() -> list[dict]` (task 3 uses this)
  - `_vault_walk.BUCKET_B_MIGRATIONS`, `BUCKET_D_TAG_PREFIXES`, `VAGUE_TOPICAL_TAGS`, `CREW_NAMES`, `BUCKET_D_TAG_EXACT` keep their exact current names and types, so every importer is untouched. `_BUCKET_B_KEYS` is deleted.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test__profile.py`:

```python
"""Tests for adjudant/scripts/_profile.py — the one file a build may differ in.

The profile exists because the twin used to fork source files to carry four
differences: a token threshold, four tag constants, a PATH probe, and a verb
list. Every shared edit then had to be made twice. The tests that matter here
are the ones that prove there is no second declaration to drift against: a
missing profile must raise, never fall back.
"""

import json
import tempfile
import unittest
from pathlib import Path

import _profile


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


MINIMAL = {
    "audience": "public",
    "description_suffix": "",
    "cost_warn_tokens": 10000,
    "tags": {
        "bucket_b_migrations": {},
        "bucket_b_prefixes": [],
        "bucket_d_tag_prefixes": ["ob/"],
        "vague_topical_tags": ["frontend", "backend"],
        "crew_names": [],
    },
    "capabilities": [],
}


class TestLoad(unittest.TestCase):

    def setUp(self):
        _profile.load.cache_clear()

    def tearDown(self):
        _profile.load.cache_clear()

    def test_missing_profile_raises_rather_than_defaulting(self):
        # The whole point: an inline default is a second declaration.
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(_profile.ProfileError):
                _profile.load(Path(tmp) / "nope.json")

    def test_malformed_profile_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "build-profile.json"
            bad.write_text("{ not json")
            with self.assertRaises(_profile.ProfileError):
                _profile.load(bad)

    def test_unknown_audience_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = dict(MINIMAL, audience="staging")
            with self.assertRaises(_profile.ProfileError):
                _profile.load(_write(Path(tmp) / "p.json", payload))

    def test_missing_required_key_raises_and_names_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = {k: v for k, v in MINIMAL.items() if k != "cost_warn_tokens"}
            with self.assertRaises(_profile.ProfileError) as ctx:
                _profile.load(_write(Path(tmp) / "p.json", payload))
            self.assertIn("cost_warn_tokens", str(ctx.exception))

    def test_load_is_cached_per_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _write(Path(tmp) / "p.json", MINIMAL)
            first = _profile.load(p)
            self.assertIs(_profile.load(p), first)


class TestShippedProfile(unittest.TestCase):
    """The real file in this tree, whichever build it is."""

    def test_audience_is_one_of_two(self):
        self.assertIn(_profile.audience(), ("full", "public"))

    def test_threshold_is_a_positive_int(self):
        self.assertIsInstance(_profile.cost_warn_tokens(), int)
        self.assertGreater(_profile.cost_warn_tokens(), 0)

    def test_tag_rules_have_the_documented_types(self):
        rules = _profile.tag_rules()
        self.assertIsInstance(rules.bucket_b_migrations, dict)
        self.assertIsInstance(rules.bucket_b_prefixes, tuple)
        self.assertIsInstance(rules.bucket_d_tag_prefixes, tuple)
        self.assertIsInstance(rules.vague_topical_tags, frozenset)
        self.assertIsInstance(rules.crew_names, frozenset)

    def test_every_bucket_b_source_sits_under_a_bucket_b_prefix(self):
        # A migration source outside the prefixes is unreachable: is_bucket_d_tag
        # would never consult the map for it.
        rules = _profile.tag_rules()
        for source in rules.bucket_b_migrations:
            self.assertTrue(
                any(source.startswith(p) for p in rules.bucket_b_prefixes),
                f"{source!r} is not under any bucket_b_prefix")

    def test_capabilities_carry_every_field_the_consumers_read(self):
        for cap in _profile.capabilities():
            for field in ("id", "probe", "reference", "check_line",
                          "sitrep_line", "session_banner"):
                self.assertIn(field, cap)
                self.assertTrue(cap[field], f"{cap.get('id')}.{field} is empty")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__profile -v`
Expected: FAIL with `ModuleNotFoundError: No module named '_profile'`

- [ ] **Step 3: Write the profile data file**

Create `adjudant/scripts/build-profile.json` with main's current values, lifted verbatim from `_cost.py:27` and `_vault_walk.py:836-863`:

```json
{
  "audience": "full",
  "description_suffix": " Pairs with hookify.",
  "cost_warn_tokens": 30000,
  "tags": {
    "bucket_b_migrations": {
      "cabinet/recon": "recon-item",
      "cabinet/portal-concept": "portal-concept",
      "cabinet/preview": "preview",
      "cabinet/asset-index": "index",
      "cabinet/dev-doc": "doc",
      "cabinet/decision": "decision"
    },
    "bucket_b_prefixes": ["cabinet/"],
    "bucket_d_tag_prefixes": ["ob/"],
    "vague_topical_tags": [
      "architecture",
      "architecture-lockin",
      "architecture-source",
      "frontend",
      "cms",
      "moc",
      "toolbox",
      "scheduler",
      "campaign-request",
      "flow-c",
      "nightly",
      "hubspot",
      "reconciler"
    ],
    "crew_names": ["bostrol", "kevijntje", "henske", "jonasty"]
  },
  "capabilities": []
}
```

`capabilities` stays empty here; task 3 fills it and its test covers the shape.

- [ ] **Step 4: Write the loader**

Create `adjudant/scripts/_profile.py`:

```python
#!/usr/bin/env python3
"""Adjudant build profile — the one file that differs between builds.

Adjudant ships twice: the full build in this marketplace, and a reduced public
build in the furtive-follies twin. Until v3 the difference was carried by
forking source files. A token threshold lived in `_cost.py` and again in
`connect.py`; four tag constants lived in `_vault_walk.py`; a PATH probe lived
in three places. Every edit to a shared file had to be made twice, and between
edits the trees drifted.

Everything that legitimately differs now lives in `build-profile.json` beside
this module. The Python is identical in both trees; only the data changes.

There is no fallback and there is no default. A missing or malformed profile
raises ProfileError and the caller dies. An inline default would be a second
declaration of the same fact, which is the drift this module ends.

Public API:
    PROFILE_PATH: Path
    ProfileError
    load(path=None) -> dict            # cached per resolved path
    audience() -> str                  # "full" | "public"
    description_suffix() -> str
    cost_warn_tokens() -> int
    tag_rules() -> TagRules
    capabilities() -> list[dict]
    present_capabilities() -> list[dict]

CLI, called by the SessionStart hook:
    python3 _profile.py --session-banner
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, NamedTuple, Optional

PROFILE_PATH = Path(__file__).resolve().parent / "build-profile.json"

AUDIENCES = ("full", "public")
REQUIRED_KEYS = ("audience", "description_suffix", "cost_warn_tokens",
                 "tags", "capabilities")
REQUIRED_TAG_KEYS = ("bucket_b_migrations", "bucket_b_prefixes",
                     "bucket_d_tag_prefixes", "vague_topical_tags",
                     "crew_names")
CAPABILITY_KEYS = ("id", "probe", "reference", "check_line",
                   "sitrep_line", "session_banner")


class ProfileError(RuntimeError):
    """The build profile is absent, unreadable, or does not declare a build."""


class TagRules(NamedTuple):
    bucket_b_migrations: dict[str, str]
    bucket_b_prefixes: tuple[str, ...]
    bucket_d_tag_prefixes: tuple[str, ...]
    vague_topical_tags: frozenset[str]
    crew_names: frozenset[str]


@lru_cache(maxsize=None)
def load(path: Optional[Path] = None) -> dict[str, Any]:
    """Parse and validate the build profile. Cached per resolved path."""
    target = Path(path) if path is not None else PROFILE_PATH
    try:
        raw = target.read_text()
    except OSError as exc:
        raise ProfileError(f"no build profile at {target}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProfileError(f"{target} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"{target} must hold a JSON object")
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ProfileError(f"{target} is missing: {', '.join(missing)}")
    if data["audience"] not in AUDIENCES:
        raise ProfileError(
            f"{target}: audience {data['audience']!r} is not one of {AUDIENCES}")
    tags = data["tags"]
    if not isinstance(tags, dict):
        raise ProfileError(f"{target}: tags must be an object")
    missing_tags = [k for k in REQUIRED_TAG_KEYS if k not in tags]
    if missing_tags:
        raise ProfileError(f"{target}: tags is missing: {', '.join(missing_tags)}")
    for cap in data["capabilities"]:
        absent = [k for k in CAPABILITY_KEYS if k not in cap]
        if absent:
            raise ProfileError(
                f"{target}: capability {cap.get('id', '?')!r} is missing: "
                f"{', '.join(absent)}")
    return data


def audience() -> str:
    return str(load()["audience"])


def description_suffix() -> str:
    return str(load()["description_suffix"])


def cost_warn_tokens() -> int:
    return int(load()["cost_warn_tokens"])


def tag_rules() -> TagRules:
    tags = load()["tags"]
    return TagRules(
        bucket_b_migrations=dict(tags["bucket_b_migrations"]),
        bucket_b_prefixes=tuple(tags["bucket_b_prefixes"]),
        bucket_d_tag_prefixes=tuple(tags["bucket_d_tag_prefixes"]),
        vague_topical_tags=frozenset(tags["vague_topical_tags"]),
        crew_names=frozenset(tags["crew_names"]),
    )


def capabilities() -> list[dict[str, Any]]:
    return list(load()["capabilities"])


def present_capabilities() -> list[dict[str, Any]]:
    """Declared capabilities whose probe resolves on THIS machine's PATH.

    A probe only. The executable is never run: adjudant reports that an
    environment is there, it does not drive it.
    """
    return [c for c in capabilities() if shutil.which(c["probe"]) is not None]


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="_profile.py",
        description="Report this build's profile.")
    p.add_argument("--session-banner", action="store_true",
                   help="print one banner line per present capability")
    p.add_argument("--json", action="store_true",
                   help="print the whole profile as JSON")
    args = p.parse_args(argv)
    try:
        if args.json:
            print(json.dumps(load(), indent=2))
            return 0
        if args.session_banner:
            for cap in present_capabilities():
                print(cap["session_banner"])
            return 0
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the loader tests**

Run: `cd adjudant/scripts && python3 -m unittest test__profile -v`
Expected: PASS, 9 tests. `test_capabilities_carry_every_field_the_consumers_read` passes vacuously until task 3.

- [ ] **Step 6: Point the tag constants at the profile**

In `adjudant/scripts/_vault_walk.py`, add `import _profile` beside the other local imports, then replace the whole block from `# Bucket B — custom file types migrated from cabinet/*` (line 836) through `_BUCKET_B_KEYS = frozenset(BUCKET_B_MIGRATIONS.keys())` (line 868) with:

```python
# Tag rules come from the build profile: the full build and the public build
# legitimately drop different tags, and carrying that in two copies of this
# file is how the trees drifted. The names below are unchanged, so every
# importer is untouched.
_TAGS = _profile.tag_rules()

# Bucket B — custom file types migrated to a canonical type
BUCKET_B_MIGRATIONS: dict[str, str] = _TAGS.bucket_b_migrations
# Prefixes whose tags migrate when listed in BUCKET_B_MIGRATIONS and drop otherwise
BUCKET_B_PREFIXES: tuple[str, ...] = _TAGS.bucket_b_prefixes

# Bucket D — tags to drop entirely
BUCKET_D_TAG_PREFIXES: tuple[str, ...] = _TAGS.bucket_d_tag_prefixes
VAGUE_TOPICAL_TAGS: frozenset[str] = _TAGS.vague_topical_tags
CREW_NAMES: frozenset[str] = _TAGS.crew_names

# Project-type tag form is forbidden — it lives in frontmatter `project_type:`
PROJECT_TYPE_TAGS: frozenset[str] = frozenset({
    "type/coding", "type/knowledge", "type/plugin", "type/tinkerage",
})

BUCKET_D_TAG_EXACT: frozenset[str] = VAGUE_TOPICAL_TAGS | CREW_NAMES | PROJECT_TYPE_TAGS
```

Then replace the first two branches of `is_bucket_d_tag` (currently lines 1535-1540, the `# ob/* prefix` comment through the second `return True`) with:

```python
    # Configured drop-prefixes
    if any(tag.startswith(p) for p in BUCKET_D_TAG_PREFIXES):
        return True
    # A migration prefix drops unless this exact tag has a migration target
    if (any(tag.startswith(p) for p in BUCKET_B_PREFIXES)
            and tag not in BUCKET_B_MIGRATIONS):
        return True
```

Add `BUCKET_B_MIGRATIONS, BUCKET_D_TAG_PREFIXES, BUCKET_B_PREFIXES` to the "Schema constants" list in the module docstring (currently line 29).

- [ ] **Step 7: Point the threshold at the profile**

In `adjudant/scripts/_cost.py`, add `import _profile` beside `from _vault_walk import ...`, replace line 27:

```python
DEFAULT_WARN_TOKENS = _profile.cost_warn_tokens()
```

and change the docstring line 14 to:

```
    read_threshold(code_root) -> int          # breadcrumb cost_warn_tokens, else the build profile's
```

In `adjudant/scripts/connect.py`, add `from _cost import DEFAULT_WARN_TOKENS` beside the other local imports and replace line 286:

```python
    cwt = existing.get("cost_warn_tokens", str(DEFAULT_WARN_TOKENS))
```

That closes the second copy of the threshold: `connect.py` wrote `"30000"` as a literal while `_cost.py` held `30000` as an int, and only the twin's fork ever noticed they were the same number.

- [ ] **Step 8: Point the deprecated-tag patterns at the profile**

In `adjudant/scripts/validate.py`, add `import _profile` beside the other imports and replace `DEPRECATED_TAG_PATTERNS` (currently lines 100-105) with:

```python
def _deprecated_tag_patterns() -> list["re.Pattern[str]"]:
    """Tag prefixes this build has retired, as inline (`#ob/`) and list
    (`- ob/`) forms. Built from the profile so the two builds can retire
    different prefixes without forking this file."""
    rules = _profile.tag_rules()
    pats: list[re.Pattern[str]] = []
    for prefix in rules.bucket_d_tag_prefixes + rules.bucket_b_prefixes:
        esc = re.escape(prefix)
        pats.append(re.compile(rf"#{esc}"))
        pats.append(re.compile(rf"^\s*-\s+{esc}", re.MULTILINE))
    return pats


DEPRECATED_TAG_PATTERNS = _deprecated_tag_patterns()
```

Change the roster's line 2 (currently line 8) to stop naming specific prefixes:

```
  2. templates-tag-schema   — no profile-retired tag prefixes in any template
```

- [ ] **Step 9: Make the tag tests read the profile instead of hard-coding it**

In `adjudant/scripts/test__vault_walk.py`, class `TestBucketDClassification` (line 375), replace `test_cabinet_prefix_drops_unless_bucket_b`, `test_crew_names_dropped` and `test_bucket_b_migration_lookup` with:

```python
    def test_migration_prefix_drops_unless_the_tag_has_a_target(self):
        # Which prefixes migrate is a build choice; the RULE is not.
        from _vault_walk import BUCKET_B_PREFIXES
        for prefix in BUCKET_B_PREFIXES:
            self.assertTrue(is_bucket_d_tag(prefix + "no-such-target"))
        for source in BUCKET_B_MIGRATIONS:
            self.assertFalse(is_bucket_d_tag(source), source)

    def test_crew_names_dropped(self):
        from _vault_walk import CREW_NAMES
        for name in CREW_NAMES:
            self.assertTrue(is_bucket_d_tag(name), name)

    def test_bucket_b_migration_lookup(self):
        for source, target in BUCKET_B_MIGRATIONS.items():
            self.assertEqual(is_bucket_b_migration(source), target)
        self.assertIsNone(is_bucket_b_migration("project"))
```

In `adjudant/scripts/test_tidy.py`, replace `test_migrates_bucket_b` (line 81) with:

```python
    def test_migrates_bucket_b(self):
        from _vault_walk import BUCKET_B_MIGRATIONS
        if not BUCKET_B_MIGRATIONS:
            self.skipTest("this build declares no bucket-B migrations")
        source, target = next(iter(sorted(BUCKET_B_MIGRATIONS.items())))
        new, dropped = normalize_tags([source], project_slug="x")
        self.assertEqual(new, [target])
        self.assertEqual(dropped, [f"{source} → {target}"])
```

`adjudant/scripts/test_cost.py` needs no change: it already imports `DEFAULT_WARN_TOKENS` (line 9) and asserts against the constant at lines 72, 75 and 90. Its remaining `30000` literals, at lines 104-112, are threshold *arguments* to `cost_block` and are not the default. Verify with `grep -n "30000\|DEFAULT_WARN" test_cost.py` and leave them alone.

In `adjudant/scripts/test_connect.py`, the two breadcrumb assertions at lines 644 and 658 read `cost_warn_tokens: 30000`. Change both to build the string from the constant:

```python
            self.assertIn(f"cost_warn_tokens: {DEFAULT_WARN_TOKENS}", bc)
```

and add `from _cost import DEFAULT_WARN_TOKENS` to the file's imports. In the second test the literal is also used as a replacement source, so use the same f-string there.

- [ ] **Step 10: Stop the docs naming the number**

In `adjudant/skills/adjudant/SKILL.md`, replace line 54:

```markdown
- Threshold default is the build profile's `cost_warn_tokens` (`scripts/build-profile.json`); per-project override via `cost_warn_tokens:` in `.claude/adjudant`.
```

In `adjudant/skills/adjudant/reference/connect.md`, replace the `cost_warn_tokens: 30000` in line 27 with:

```markdown
`cost_warn_tokens` (the build profile's default), `stale_after_days: 30`. Existing overrides survive re-connect,
```

Both lines were forked purely because they restated a number that already lives in one place.

- [ ] **Step 11: Run the suite and the validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | grep -E "^Ran |^OK|^FAILED"`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 12: Commit**

```bash
git add adjudant/scripts/build-profile.json adjudant/scripts/_profile.py \
  adjudant/scripts/test__profile.py adjudant/scripts/_vault_walk.py \
  adjudant/scripts/_cost.py adjudant/scripts/connect.py adjudant/scripts/validate.py \
  adjudant/scripts/test__vault_walk.py adjudant/scripts/test_tidy.py \
  adjudant/scripts/test_cost.py adjudant/scripts/test_connect.py \
  adjudant/skills/adjudant/SKILL.md adjudant/skills/adjudant/reference/connect.md
git commit -m "feat(adjudant): build profile - the one file a build may differ in

The twin carried its differences by forking source: the cost threshold in
_cost.py AND again as a literal in connect.py, four tag constants in
_vault_walk.py, the deprecated-tag patterns in validate.py, and the threshold
restated in two docs. Six declarations of four facts, in two trees.

All of it moves to scripts/build-profile.json. The Python is now identical in
both builds. A missing profile raises rather than defaulting: an inline default
is the second declaration this removes.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Capabilities, so an absent environment is data rather than a fork

Main probes for the `suitcase-brief` CLI in three places and documents it in a fourth. The twin deleted all four. Neither is wrong; carrying it as code is.

**Files:**
- Modify: `adjudant/scripts/build-profile.json` (fill `capabilities`)
- Modify: `adjudant/scripts/status.py` — delete `_suitcase_status` and `_suitcase_brief`, add one registry lookup. Before plan 3 these lived at `check.py:178-185` and `sitrep.py:49-59`.
- Modify: `adjudant/hooks/scripts/session-start.sh:214-219` (the suitcase pointer block)
- Modify: `adjudant/skills/adjudant/reference/internals.md:8-15`, `reference/check.md:62-64`, `reference/sitrep.md:71-73`
- Test: `adjudant/scripts/test_status.py` (was `test_check.py` class `TestSuitcaseStatus` at line 274 and `test_sitrep.py` class `TestSuitcaseBrief` at line 216), `adjudant/scripts/test_hook_shell.py` (`test_sessionstart_suitcase_pointer_startup_only`), `adjudant/scripts/test__profile.py`

**Interfaces:**
- Consumes: `_profile.capabilities()`, `_profile.present_capabilities()` from task 2.
- Produces: the report payload's existing `environment` dict gains one boolean per declared capability, keyed by its `id`. `_suitcase_status()` and `_suitcase_brief()` are deleted; nothing else imports them.

- [ ] **Step 1: Locate the report module**

Run: `cd adjudant/scripts && ls status.py check.py sitrep.py 2>&1`
Expected: `status.py` exists and `check.py`/`sitrep.py` do not. Plan 3 folded `sync`, `sitrep`, `check`, `kebab --scan` and `advisor pulse` into `status`.

If `check.py` and `sitrep.py` still exist, plan 3 has not landed. **Stop and say so** — this plan assumes plans 1-4.

Run: `grep -n "_suitcase_status\|_suitcase_brief\|\"environment\"" status.py`
Expected: three or four hits. Those are the edit sites for steps 4 and 5.

- [ ] **Step 2: Write the failing tests**

Append to `adjudant/scripts/test__profile.py`:

```python
class TestCapabilityProbing(unittest.TestCase):

    def setUp(self):
        _profile.load.cache_clear()
        self._path = os.environ.get("PATH", "")

    def tearDown(self):
        os.environ["PATH"] = self._path
        _profile.load.cache_clear()

    def _profile_with(self, tmp: Path, caps: list) -> Path:
        return _write(tmp / "p.json", dict(MINIMAL, capabilities=caps))

    CAP = {
        "id": "widget",
        "probe": "widget-brief",
        "reference": "reference/widget.md",
        "check_line": "Widget: present (widget-brief for orientation)",
        "sitrep_line": "Widget environment on this machine: run widget-brief",
        "session_banner": "- Widget detected: run widget-brief for orientation",
    }

    def test_absent_probe_yields_no_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.environ["PATH"] = str(root / "empty")
            orig = _profile.PROFILE_PATH
            _profile.PROFILE_PATH = self._profile_with(root, [self.CAP])
            try:
                self.assertEqual(_profile.present_capabilities(), [])
            finally:
                _profile.PROFILE_PATH = orig

    def test_present_probe_yields_the_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binpath = root / "bin"
            binpath.mkdir()
            fake = binpath / "widget-brief"
            fake.write_text("#!/bin/sh\nexit 0\n")
            fake.chmod(0o755)
            os.environ["PATH"] = str(binpath)
            orig = _profile.PROFILE_PATH
            _profile.PROFILE_PATH = self._profile_with(root, [self.CAP])
            try:
                got = _profile.present_capabilities()
                self.assertEqual([c["id"] for c in got], ["widget"])
            finally:
                _profile.PROFILE_PATH = orig

    def test_empty_registry_never_probes(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig = _profile.PROFILE_PATH
            _profile.PROFILE_PATH = self._profile_with(Path(tmp), [])
            try:
                self.assertEqual(_profile.present_capabilities(), [])
            finally:
                _profile.PROFILE_PATH = orig
```

Add `import os` to the file's imports.

Append to `adjudant/scripts/test_status.py`:

```python
class TestCapabilityReporting(unittest.TestCase):
    """A capability the build does not declare must be invisible, not false.

    Before v3 the suitcase probe was three copies of `shutil.which` plus a
    fourth mention in the docs, and the public build carried none of them —
    which is why check.py, sitrep.py and session-start.sh were all forked.
    """

    def test_environment_carries_one_key_per_declared_capability(self):
        import _profile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", _CLEAN_BRIEF)
            report = run_status(root)
            for cap in _profile.capabilities():
                self.assertIn(cap["id"], report["environment"])
                self.assertIsInstance(report["environment"][cap["id"]], bool)

    def test_environment_carries_nothing_for_undeclared_capabilities(self):
        import _profile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", _CLEAN_BRIEF)
            report = run_status(root)
            declared = {c["id"] for c in _profile.capabilities()}
            extra = set(report["environment"]) - declared - {"obsidian_cli"}
            self.assertEqual(extra, set())
```

`_write` and `_CLEAN_BRIEF` already exist in that module (they were `test_check.py`'s helpers at lines 12 and 296). Confirm the report entry point's name with `grep -n "def run_status\|def run_check" status.py` before writing, and use the name on disk.

- [ ] **Step 3: Run to verify they fail**

Run: `cd adjudant/scripts && python3 -m unittest test__profile.TestCapabilityProbing test_status.TestCapabilityReporting -v`
Expected: FAIL. The profile declares no capabilities yet, so `TestCapabilityProbing` fails on the fake-probe case and `TestCapabilityReporting` fails on the missing `environment` keys.

- [ ] **Step 4: Declare the suitcase capability**

In `adjudant/scripts/build-profile.json`, replace `"capabilities": []` with:

```json
  "capabilities": [
    {
      "id": "suitcase",
      "probe": "suitcase-brief",
      "reference": "reference/suitcase.md",
      "check_line": "Suitcase: present (suitcase-brief for orientation)",
      "sitrep_line": "Suitcase environment on this machine: run suitcase-brief for orientation",
      "session_banner": "- Suitcase detected: run suitcase-brief for orientation (vault is canonical; writes via adjudant)"
    }
  ]
```

- [ ] **Step 5: Replace the three probes with one lookup**

In `adjudant/scripts/status.py`, delete `_suitcase_status()` and `_suitcase_brief()` entirely, along with the `"suitcase": _suitcase_status()` and `"suitcase": _suitcase_brief()` entries in the report payload. Add `import _profile` beside the other local imports and add above the payload builder:

```python
def _environment(project_dir: Path) -> dict[str, Any]:
    """Capability probes, keyed by id. Presence only: nothing here is executed.

    A capability this build does not declare produces no key at all, so a
    reduced build renders nothing rather than rendering "absent" — the
    difference that used to be carried by forking this file.
    """
    env: dict[str, Any] = {"obsidian_cli": obsidian_cli_path() is not None}
    present = {c["id"] for c in _profile.present_capabilities()}
    for cap in _profile.capabilities():
        env[cap["id"]] = cap["id"] in present
    return env
```

Replace the payload's `"environment": {"obsidian_cli": obsidian_cli_path() is not None},` with `"environment": _environment(project_dir),`. Remove `import shutil` if nothing else in the module uses it (check with `grep -n "shutil\." status.py`).

- [ ] **Step 6: Replace the hook's probe with the registry CLI**

In `adjudant/hooks/scripts/session-start.sh`, replace the suitcase pointer block (currently lines 214-219) with:

```bash
  # Environment capabilities: probes declared in scripts/build-profile.json,
  # rendered by _profile.py. Fresh startups only, never resume/compact/clear.
  # A build whose registry is empty prints nothing, which is why this hook is
  # now one file across both builds instead of two. The scripts dir is found
  # from this script's own path, so it works with no CLAUDE_PLUGIN_ROOT set.
  if [ "$start_source" = "startup" ]; then
    _adj_scripts=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../scripts" 2>/dev/null && pwd || true)
    if [ -n "$_adj_scripts" ] && [ -f "$_adj_scripts/_profile.py" ] \
       && command -v python3 >/dev/null 2>&1; then
      python3 "$_adj_scripts/_profile.py" --session-banner 2>/dev/null || true
    fi
  fi
```

The existing `test_sessionstart_suitcase_pointer_startup_only` in `test_hook_shell.py` scrubs `PATH` to `/usr/bin:/bin` for its negative case. `python3` resolves there on macOS and Linux, so the block still runs and prints nothing, which is what the test asserts. Leave that test unchanged: it now covers the registry path end to end.

- [ ] **Step 7: Make the docs audience-neutral**

In `adjudant/skills/adjudant/reference/internals.md`, replace the `## Environment awareness` section (currently lines 8-15) with:

```markdown
## Environment awareness

Adjudant probes for optional environments and never drives them. Each is
declared once in `scripts/build-profile.json` under `capabilities`: an `id`, a
`probe` executable looked up on PATH, a reference doc, and the three lines the
consumers render (`status`, its briefing, and the SessionStart banner). A build
that declares none prints nothing and loads nothing. Nothing here executes the
probe; presence is the whole signal. Load a capability's reference doc only
when its territory comes up.
```

In `adjudant/skills/adjudant/reference/check.md`, replace the three suitcase lines (currently 62-64) with:

```markdown
- `environment`: one boolean per capability the build declares (`scripts/build-profile.json`),
  plus `obsidian_cli`. Render the capability's `check_line` only when its value is true;
  render nothing when false, and nothing at all for a capability this build does not declare
```

In `adjudant/skills/adjudant/reference/sitrep.md`, replace the three suitcase lines (currently 71-73) with:

```markdown
- OPTIONAL capability lines, one per declared capability whose `environment` value is true
  (they do not count against the four labeled lines): render the capability's `sitrep_line`
  verbatim, above the board line. Skip every false one; details in the capability's own reference
```

- [ ] **Step 8: Run the tests and the validators**

Run: `cd adjudant/scripts && python3 -m unittest test__profile test_status test_hook_shell -v 2>&1 | grep -E "^Ran |^OK|^FAILED"`
Expected: `OK`

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | grep -E "^Ran |^OK|^FAILED"`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`. The `reference-doc-links` validator no longer sees a link to `reference/suitcase.md` from `internals.md`; the doc stays on disk and is now named by the profile instead, which is what makes it a nameable deletion in task 8.

- [ ] **Step 9: Commit**

```bash
git add adjudant/scripts/build-profile.json adjudant/scripts/status.py \
  adjudant/scripts/test__profile.py adjudant/scripts/test_status.py \
  adjudant/hooks/scripts/session-start.sh \
  adjudant/skills/adjudant/reference/internals.md \
  adjudant/skills/adjudant/reference/check.md \
  adjudant/skills/adjudant/reference/sitrep.md
git commit -m "feat(adjudant): capability registry - an absent environment is data, not a fork

The suitcase probe was four declarations: shutil.which in check.py, again in
sitrep.py, a bash command -v in session-start.sh, and a paragraph in
internals.md. The public build deleted all four, which is why those three files
could never be shared.

Capabilities are declared once in build-profile.json. A build that declares
none renders nothing and the same three files ship unchanged.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Neutral fixtures, so the public tree carries nothing personal

The twin does not only drop code. It rewrites test fixtures: `hubspot-nightly` becomes `acme-web`, `ob/cabinet` becomes `ob/legacy`, "Tom's vault" becomes "a real vault". A generator that copies main's tests verbatim would push the author's client and project names into a public repository. Sanitising inside the generator would mean generated files are no longer byte-identical, and the parity gate in task 9 depends on byte identity. So main is normalised instead, once.

**Files:**
- Create: `adjudant/scripts/test_no_personal_identifiers.py`
- Modify: whatever that test names. As of 2026-09-01 and after plan 3's deletions, that is `scripts/test__vault_walk.py`, `scripts/test_tidy.py`, `scripts/test_renest_memory.py`, `scripts/tidy.py`, `hooks/scripts/session-start.sh`, `skills/adjudant/reference/tidy.md`, `skills/adjudant/reference/vault-standards.md`.

**Interfaces:**
- Consumes: `_profile.tag_rules()` from task 2, to allowlist the profile itself.
- Produces: nothing importable. Task 9's parity gate relies on the trees being byte-identical here.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_no_personal_identifiers.py`:

```python
"""The full build and the public build ship the same files, so the shared
files must name nobody.

The twin used to rewrite fixtures on the way out: hubspot-nightly to acme-web,
ob/cabinet to ob/legacy, "Tom's vault" to "a real vault". That rewrite is why
six test files could not be shared, and skipping it would publish a client name
and four crew nicknames to a public repository.

The names that ARE the author's data — the vague topicals and crew names the
full build drops — belong in scripts/build-profile.json, which is the one file
a build is allowed to differ in. Everywhere else is neutral.
"""

import re
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# Identifiers that must not appear outside the allowlist. Kept as fragments so
# a compound (hubspot-nightly, ob/cabinet) is caught by its root.
FORBIDDEN = (
    "hubspot", "nightly", "cabinet",
    "bostrol", "kevijntje", "henske", "jonasty",
    "onnozelaer",
)
# "Tom" as a word, not as a substring (custom, atom, bottom all contain it).
FORBIDDEN_WORDS = ("Tom",)

# Files where these names are the point, not a leak.
ALLOWLIST = {
    "scripts/build-profile.json",       # the author's tag rules ARE this data
    "scripts/test_no_personal_identifiers.py",
    ".claude-plugin/plugin.json",       # author and repository identity
}

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}
TEXT_SUFFIXES = {".py", ".sh", ".md", ".json", ".html", ".yaml", ".yml", ".txt"}


def _files() -> list[Path]:
    out = []
    for path in sorted(PLUGIN_ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if SKIP_DIRS & set(path.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        if path.relative_to(PLUGIN_ROOT).as_posix() in ALLOWLIST:
            continue
        out.append(path)
    return out


def leaks() -> list[str]:
    """Every forbidden identifier outside the allowlist, as path:line: term."""
    found: list[str] = []
    word_res = [(w, re.compile(rf"\b{re.escape(w)}\b")) for w in FORBIDDEN_WORDS]
    for path in _files():
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        rel = path.relative_to(PLUGIN_ROOT).as_posix()
        for n, line in enumerate(lines, 1):
            low = line.lower()
            for term in FORBIDDEN:
                if term in low:
                    found.append(f"{rel}:{n}: {term}")
            for word, rx in word_res:
                if rx.search(line):
                    found.append(f"{rel}:{n}: {word}")
    return found


class TestNoPersonalIdentifiers(unittest.TestCase):

    def test_shared_files_name_nobody(self):
        found = leaks()
        self.assertEqual(found, [], "personal identifiers in shared files:\n  "
                                    + "\n  ".join(found))

    def test_the_allowlist_still_points_at_real_files(self):
        for rel in sorted(ALLOWLIST):
            self.assertTrue((PLUGIN_ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and read the list**

Run: `cd adjudant/scripts && python3 -m unittest test_no_personal_identifiers -v`
Expected: FAIL, listing roughly a dozen `path:line: term` entries. As of 2026-09-01, before plans 1-4, the list is:

```
hooks/scripts/session-start.sh:146: Tom
scripts/test__vault_walk.py:95: hubspot
scripts/test__vault_walk.py:95: nightly
scripts/test__vault_walk.py:97: hubspot
scripts/test__vault_walk.py:97: nightly
scripts/test__vault_walk.py:1090: hubspot
scripts/test_renest_memory.py:5: Tom
scripts/test_renest_memory.py:28: Tom
scripts/test_renest_memory.py:38: Tom
scripts/test_tidy.py:87: hubspot
scripts/test_tidy.py:325: Nightly
scripts/test_tidy.py:331: nightly
scripts/test_tidy.py:442: cabinet
scripts/test_tidy.py:610: cabinet
scripts/tidy.py:123: cabinet
skills/adjudant/reference/tidy.md:43: cabinet
skills/adjudant/reference/vault-standards.md:31: cabinet
```

Plans 2-4 move these lines and may have removed some. Use the list the test prints, not this one.

- [ ] **Step 3: Rename the fixture identifiers**

Apply, from `adjudant/`. The `-i ''` is BSD `sed`, which is what macOS ships; on GNU `sed` drop the empty argument.

```bash
# Project slug fixtures: the author's client becomes a neutral demo name.
sed -i '' 's/hubspot-nightly/acme-web/g' scripts/test__vault_walk.py scripts/test_tidy.py
sed -i '' 's/# Nightly/# Acme/; s/"nightly"/"acme"/' scripts/test_tidy.py
# Retired-tag fixtures: `ob/cabinet` names a sunset plugin, `ob/legacy` names
# the class the test is actually about.
sed -i '' 's|ob/cabinet|ob/legacy|g' scripts/test_tidy.py
```

Then fix by hand the two that `sed` must not touch:

- `scripts/tidy.py:123` — change the comment `# Bucket B migration first (cabinet/*)` to `# Bucket B migration first (profile-declared prefixes)`.
- `hooks/scripts/session-start.sh:146` — in the advisor banner comment, change `The banner is the acute awareness Tom asked for - the model` to `The banner is acute awareness by design: the model`.

- [ ] **Step 4: Generalise the two docs**

In `adjudant/skills/adjudant/reference/tidy.md`, replace the Bucket B clause in the tag-normalisation step (line 43):

```markdown
3. **Normalise tags** per the schema in `reference/vault-standards.md` §2 — drop Bucket D (retired prefixes, vague topicals, project-slug self-tags, crew names, `type/*` tags), migrate Bucket B (a declared prefix whose exact tag has a migration target). Both sets come from `scripts/build-profile.json`. Leave Bucket A and Bucket C untouched.
```

In `adjudant/skills/adjudant/reference/vault-standards.md`, replace the Bucket sentence (line 31):

```markdown
Bare tags only, no prefix. Every file carries exactly one file-type tag matching its `type:`; `Home.md` is the lone exception (`type: vault-home`, no tag). **Bucket A** (the file-type tags), **B** (declared prefixes that migrate to a canonical type) and **D** (retired prefixes, project-slug tags, vague topicals, crew names, `type/*` tags) are declared in `scripts/build-profile.json`, typed by `_profile.tag_rules()`, and applied by `tidy.normalize_tags`.
```

- [ ] **Step 5: Run the scanner and the suite**

Run: `cd adjudant/scripts && python3 -m unittest test_no_personal_identifiers -v`
Expected: PASS, 2 tests. If a hit remains, fix the file rather than widening `ALLOWLIST`: the allowlist has exactly three entries and each is justified in the module docstring.

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | grep -E "^Ran |^OK|^FAILED"`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add adjudant/scripts/test_no_personal_identifiers.py adjudant/scripts/test__vault_walk.py \
  adjudant/scripts/test_tidy.py adjudant/scripts/test_renest_memory.py adjudant/scripts/tidy.py \
  adjudant/hooks/scripts/session-start.sh \
  adjudant/skills/adjudant/reference/tidy.md adjudant/skills/adjudant/reference/vault-standards.md
git commit -m "refactor(adjudant): neutral fixtures, so both builds can ship the same tests

The twin rewrote fixtures on the way out - hubspot-nightly to acme-web,
ob/cabinet to ob/legacy, Tom to a third person - which is why six test files
could never be shared. Copying them verbatim instead would publish a client
name and four crew nicknames.

Main is normalised once. The names that ARE the author's data stay in
build-profile.json, and test_no_personal_identifiers keeps them from coming
back anywhere else.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: One resolver, and the legacy breadcrumb reported instead of resolved

The last behaviour fork. `resolve_vault` has five steps in main and four in the twin, and until it is settled the two trees can never ship the same `_vault_walk.py`. The ruling and its evidence are in this plan's Context section; this task carries it out.

**Files:**
- Modify: `adjudant/scripts/_vault_walk.py:600-605` (the docstring's step list), `:635-643` (the legacy block)
- Modify: `adjudant/scripts/status.py` — one new finding
- Test: `adjudant/scripts/test__vault_walk.py` (new class beside `TestVaultNameResolution`, line 831), `adjudant/scripts/test_status.py`

**Interfaces:**
- Consumes: nothing from tasks 1-4.
- Produces: `resolve_vault(project_root: Path, env_vault: Optional[str] = None) -> Optional[Path]` keeps its signature and loses one resolution step. `status`'s report payload gains `project["legacy_breadcrumb"]: bool` — true when `.claude/obsidian-bridge` exists and `.claude/adjudant` does not.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test__vault_walk.py`:

```python
class TestLegacyBreadcrumbIsNotResolved(unittest.TestCase):
    """The retired obsidian-bridge breadcrumb stops being a resolution step.

    Its only migration partner was port.py, deleted in v3, so a resolved legacy
    path led nowhere: adjudant would quietly work from a stale vault the user
    was never told about. Reporting it is strictly more useful than silently
    honouring it, and it is the last thing keeping this module forked between
    the two builds.
    """

    def _legacy_project(self, tmp: Path) -> tuple[Path, Path]:
        vault = tmp / "OldVault"
        (vault / "projects").mkdir(parents=True)
        (vault / "Home.md").write_text("---\ntype: vault-home\n---\n\n# Home\n")
        project = tmp / "code"
        (project / ".claude").mkdir(parents=True)
        (project / ".claude" / "obsidian-bridge").write_text(
            f"vault: {vault}\nslug: legacy-proj\n")
        return project, vault

    def test_legacy_breadcrumb_alone_resolves_to_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, _vault = self._legacy_project(Path(tmp))
            self.assertIsNone(resolve_vault(project))

    def test_an_adjudant_breadcrumb_still_wins_normally(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, _old = self._legacy_project(root)
            new_vault = root / "NewVault"
            (new_vault / "projects").mkdir(parents=True)
            (new_vault / "Home.md").write_text("---\ntype: vault-home\n---\n\n# Home\n")
            (project / ".claude" / "adjudant").write_text(
                f"vault_path: {new_vault}\nvault_name: NewVault\nslug: demo\n")
            self.assertEqual(resolve_vault(project), new_vault)

    def test_the_docstring_declares_four_steps(self):
        # The docstring is the contract readers trust; a five-step docstring
        # over a four-step function is the drift this whole plan removes.
        self.assertIn("4-step resolution:", resolve_vault.__doc__)
        self.assertNotIn("obsidian-bridge", resolve_vault.__doc__)
```

Append to `adjudant/scripts/test_status.py`:

```python
class TestLegacyBreadcrumbIsReported(unittest.TestCase):

    def test_legacy_breadcrumb_without_an_adjudant_one_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", _CLEAN_BRIEF)
            code = root / "code"
            (code / ".claude").mkdir(parents=True)
            (code / ".claude" / "obsidian-bridge").write_text("vault: /nope\n")
            report = run_status(root, code_root=code)
            self.assertTrue(report["project"]["legacy_breadcrumb"])

    def test_no_legacy_breadcrumb_is_false_not_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", _CLEAN_BRIEF)
            code = root / "code"
            (code / ".claude").mkdir(parents=True)
            (code / ".claude" / "adjudant").write_text("slug: demo\n")
            report = run_status(root, code_root=code)
            self.assertFalse(report["project"]["legacy_breadcrumb"])
```

Confirm the report entry point's parameter name with `grep -n "def run_status" -A6 status.py` before writing, and use the keyword on disk (it was `code_root` in `check.run_check`).

- [ ] **Step 2: Run to verify they fail**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestLegacyBreadcrumbIsNotResolved test_status.TestLegacyBreadcrumbIsReported -v`
Expected: FAIL. `test_legacy_breadcrumb_alone_resolves_to_nothing` returns the old vault, `test_the_docstring_declares_four_steps` finds "5-step resolution:", and both status tests raise `KeyError: 'legacy_breadcrumb'`.

- [ ] **Step 3: Delete the resolution step**

In `adjudant/scripts/_vault_walk.py`, replace the `resolve_vault` docstring's step list (currently lines 600-605) with:

```python
    """4-step resolution:
      1. env var override (OB_VAULT or passed env_vault)
      2. .claude/adjudant breadcrumb `vault_path` field (absolute, current machine)
      3. .claude/adjudant breadcrumb `vault_name` field → standard locations
         under THIS machine's $HOME (cross-machine portability)
      4. walk up parents for `Home.md` with `type: vault-home`

    A retired `.claude/obsidian-bridge` breadcrumb is NOT a resolution step.
    Its only migration partner was `port`, sunset in v3, so honouring it meant
    working from a stale path with no way to migrate off it and nothing said.
    `status` reports its presence instead: see project.legacy_breadcrumb.
    """
```

Delete the whole legacy block (currently lines 635-643, from `# 4. legacy OB breadcrumb` through the inner `return p`) and renumber the walk-up comment:

```python
    # 4. Walk up for Home.md. The type must come from parsed FRONTMATTER —
```

Check whether `re` is still used elsewhere in the module (`grep -c "re\." _vault_walk.py`); it is, so the import stays.

- [ ] **Step 4: Report it in status**

In `adjudant/scripts/status.py`, add above the report payload builder:

```python
def _legacy_breadcrumb(code_root: Optional[Path]) -> bool:
    """A retired `.claude/obsidian-bridge` file with no `.claude/adjudant`.

    v3 stopped resolving it (see _vault_walk.resolve_vault). Reporting it is
    the replacement: the project was never connected, and the fix is one
    command, so say that rather than quietly serving a stale path.
    """
    if code_root is None:
        return False
    claude = Path(code_root) / ".claude"
    return (claude / "obsidian-bridge").is_file() and not (claude / "adjudant").is_file()
```

and add `"legacy_breadcrumb": _legacy_breadcrumb(code_root),` to the `project` dict in the payload.

In `adjudant/skills/adjudant/reference/check.md`, add one bullet to the `project` field list:

```markdown
- `legacy_breadcrumb`: true when `.claude/obsidian-bridge` exists and `.claude/adjudant` does not.
  Report it in the "wrong now" band as one line: `.claude/obsidian-bridge is a retired breadcrumb — run /adjudant connect`
```

- [ ] **Step 5: Run the tests**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk.TestLegacyBreadcrumbIsNotResolved test_status.TestLegacyBreadcrumbIsReported -v`
Expected: PASS, 5 tests.

- [ ] **Step 6: Run the full suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | grep -E "^Ran |^OK|^FAILED"`
Expected: `OK`. Any surviving test that seeded an `obsidian-bridge` file to reach a vault is asserting the behaviour just removed; delete it and name it in the commit message. As of 2026-09-01 the only such tests were in `test_port.py`, which plan 3 deleted.

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 7: Commit**

```bash
git add adjudant/scripts/_vault_walk.py adjudant/scripts/status.py \
  adjudant/scripts/test__vault_walk.py adjudant/scripts/test_status.py \
  adjudant/skills/adjudant/reference/check.md
git commit -m "fix(adjudant): stop resolving the retired obsidian-bridge breadcrumb

Main resolved it as step 4 and the public build never did, which is the last
thing keeping _vault_walk.py forked. The step's only migration partner was
port.py, sunset in v3, and its only tests lived in test_port.py, deleted with
it: honouring it meant working from a stale path with no way off it and nothing
said.

status reports project.legacy_breadcrumb instead, so the user is told to run
connect rather than being served a vault they cannot see.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Audience, and the renderer that ends ten hand-edited surfaces

Ten places spell out the verb list by hand, across four files in two repositories. Validator 15 exists only because they kept disagreeing: the repo's own `AGENTS.md` says adjudant has eleven verbs when it had thirteen, and nothing caught it.

**Files:**
- Modify: `adjudant/scripts/command-metadata.json` — `audience`, `blurb` and `files` per verb, plus a top-level `content_references` list
- Create: `adjudant/scripts/render_verb_surfaces.py`, `adjudant/scripts/test_render_verb_surfaces.py`
- Modify: `adjudant/skills/adjudant/SKILL.md` — four marker regions, two generated frontmatter fields
- Modify: `adjudant/README.md:23-39` — one marker region (heading at 23, table rows 25-39)
- Modify (written by the renderer, not by hand): `adjudant/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, `description` only
- Modify: `adjudant/scripts/validate.py:474-517` (`validate_verb_surface_parity`), `:467-471` (`_NUMBER_WORDS`), `:1257` (the roster call), `:21` (the roster's line 15)
- Test: `adjudant/scripts/test_validate.py` class `TestVerbSurfaceParity` (line 157)

**Interfaces:**
- Consumes: `_profile.audience()` and `_profile.description_suffix()` from task 2.
- Produces, used by tasks 7, 8 and 9:
  - `render_verb_surfaces.NUMBER_WORDS: tuple[str, ...]` — index-to-word, `("zero", "one", ... "fifteen")`. `validate.py` imports it.
  - `render_verb_surfaces.SurfaceError(RuntimeError)`
  - `render_verb_surfaces.load_metadata(plugin_root: Path) -> dict`
  - `render_verb_surfaces.verbs_for(meta: dict, audience: str) -> list[dict]`
  - `render_verb_surfaces.full_only_paths(meta: dict) -> set[str]` — plugin-relative paths a public build must not carry. Task 8's generator uses it as its deletion allowlist.
  - `render_verb_surfaces.render(plugin_root: Path, audience: str) -> dict[Path, str]` — the desired text of every markdown surface, written or compared but never partially applied.
  - `render_verb_surfaces.apply(plugin_root: Path = PLUGIN_ROOT, check: bool = False) -> list[str]` — the paths that changed (or would change). `check=True` writes nothing.
  - `render_verb_surfaces.main(argv: Optional[list[str]] = None) -> int`

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_render_verb_surfaces.py`:

```python
"""Tests for adjudant/scripts/render_verb_surfaces.py.

Ten doc surfaces used to name the verbs by hand: SKILL.md's description,
argument-hint, verb-count sentence, router table, weight bullets and
content-authoring list; the README's heading and table; plugin.json's
description; and the marketplace entry, in each of two repos. Validator 15
existed only to notice when they disagreed, which they did.

The tests that matter are idempotence (a second run changes nothing), audience
filtering (the public build sheds full-only verbs everywhere at once), and pipe
escaping (a raw `|` in an argument hint breaks a markdown table, which is how
the projects index grew malformed rows).
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import render_verb_surfaces as rvs

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


class _Sandbox(unittest.TestCase):
    """A throwaway copy of the real plugin tree, so tests never write to it."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "adjudant"
        shutil.copytree(PLUGIN_ROOT, self.root, symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        self.meta = rvs.load_metadata(self.root)

    def tearDown(self):
        self._tmp.cleanup()


class TestAudienceFiltering(_Sandbox):

    def test_every_verb_declares_an_audience(self):
        for verb in self.meta["verbs"]:
            self.assertIn(verb.get("audience"), ("all", "full"), verb["name"])

    def test_public_is_a_strict_subset_of_full(self):
        full = {v["name"] for v in rvs.verbs_for(self.meta, "full")}
        public = {v["name"] for v in rvs.verbs_for(self.meta, "public")}
        self.assertTrue(public < full or public == full)
        self.assertEqual(public, {v["name"] for v in self.meta["verbs"]
                                  if v["audience"] == "all"})

    def test_full_only_paths_come_from_full_only_verbs(self):
        paths = rvs.full_only_paths(self.meta)
        for verb in self.meta["verbs"]:
            if verb["audience"] == "full":
                for rel in verb.get("files", []):
                    self.assertIn(rel, paths)
            else:
                for rel in verb.get("files", []):
                    self.assertNotIn(rel, paths)

    def test_every_full_only_path_exists_on_disk(self):
        # A path named but absent would make the generator refuse a deletion
        # it should allow, or allow one it should refuse.
        for rel in sorted(rvs.full_only_paths(self.meta)):
            self.assertTrue((self.root / rel).exists(), rel)


class TestRendering(_Sandbox):

    def test_the_shipped_tree_is_already_generated(self):
        self.assertEqual(rvs.apply(self.root, check=True), [],
                         "a surface is out of date; run render_verb_surfaces.py")

    def test_apply_is_idempotent(self):
        rvs.apply(self.root)
        self.assertEqual(rvs.apply(self.root, check=True), [])

    def test_check_writes_nothing(self):
        skill = self.root / "skills" / "adjudant" / "SKILL.md"
        before = skill.read_text()
        skill.write_text(before.replace("| `board` |", "| `bored` |"))
        broken = skill.read_text()
        self.assertNotEqual(rvs.apply(self.root, check=True), [])
        self.assertEqual(skill.read_text(), broken)

    def test_a_stale_surface_is_repaired(self):
        readme = self.root / "README.md"
        readme.write_text(readme.read_text().replace(
            "| Verb | What it does |", "| Verb | What it did |"))
        self.assertIn("README.md", " ".join(rvs.apply(self.root)))
        self.assertIn("| Verb | What it does |", readme.read_text())

    def test_missing_marker_raises_rather_than_guessing(self):
        readme = self.root / "README.md"
        readme.write_text(readme.read_text().replace("<!-- VERBS:TABLE:END -->", ""))
        with self.assertRaises(rvs.SurfaceError):
            rvs.apply(self.root, check=True)

    def test_pipes_in_an_argument_hint_are_escaped(self):
        # A raw pipe closes a markdown cell. The README's own check row carries
        # `[vault|repo|all]`, which is why every hand-edit had to remember this.
        rendered = rvs.render(self.root, "full")
        readme = rendered[self.root / "README.md"]
        for line in readme.splitlines():
            if line.startswith("| `/adjudant "):
                cells = [c for c in line.split("|") if c.strip()]
                self.assertEqual(len(cells), 2, line)

    def test_the_router_keeps_the_shape_validator_5_parses(self):
        # command-metadata-coherence matches: | `verb` | `reference/...
        rendered = rvs.render(self.root, "full")
        skill = rendered[self.root / "skills" / "adjudant" / "SKILL.md"]
        import re
        found = set(re.findall(r"\|\s+`(\w+)`\s+\|\s+`reference/", skill))
        self.assertEqual(found, {v["name"] for v in rvs.verbs_for(self.meta, "full")})

    def test_the_internals_row_survives_generation(self):
        rendered = rvs.render(self.root, "full")
        skill = rendered[self.root / "skills" / "adjudant" / "SKILL.md"]
        self.assertIn("_(internals)_", skill)
        self.assertIn("reference/internals.md", skill)


class TestJsonSurfaces(_Sandbox):

    def test_plugin_description_names_every_verb(self):
        rvs.apply(self.root)
        desc = json.loads(
            (self.root / ".claude-plugin" / "plugin.json").read_text())["description"]
        for verb in rvs.verbs_for(self.meta, rvs._audience()):
            self.assertIn(verb["name"], desc)

    def test_plugin_identity_fields_are_untouched(self):
        pj = self.root / ".claude-plugin" / "plugin.json"
        before = json.loads(pj.read_text())
        rvs.apply(self.root)
        after = json.loads(pj.read_text())
        for key in ("name", "version", "author", "homepage", "repository",
                    "license", "keywords"):
            self.assertEqual(before.get(key), after.get(key), key)

    def test_the_spelled_out_count_matches_the_verb_count(self):
        rvs.apply(self.root)
        desc = json.loads(
            (self.root / ".claude-plugin" / "plugin.json").read_text())["description"]
        n = len(rvs.verbs_for(self.meta, rvs._audience()))
        self.assertIn(f"{rvs.NUMBER_WORDS[n]} verbs", desc)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_render_verb_surfaces -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'render_verb_surfaces'`

- [ ] **Step 3: Add audience, blurb and files to the metadata**

Rewrite `adjudant/scripts/command-metadata.json`. Post-plan-3 the verb set is the spec's six. Keep every existing field; add `audience`, `blurb`, and `files` (only on `full` verbs), and add the top-level `content_references` block. `blurb` is a verb phrase: it is the one field that feeds the SKILL description, the plugin description, and the README cell, so there is no fourth place to keep in step.

```json
{
  "name": "adjudant",
  "version": "3.0.0",
  "verbs": [
    {
      "name": "connect",
      "audience": "all",
      "blurb": "onboards a project and asks where it lives",
      "description": "Link a project to its vault: breadcrumb, AGENTS.md+CLAUDE.md, vault scaffold, .gitignore. Asks the lifecycle folder, the board, and proactive mode. Idempotent.",
      "argumentHint": "(no args)",
      "reference": "reference/connect.md",
      "weight": "light"
    },
    {
      "name": "status",
      "audience": "all",
      "blurb": "reports where you are, what is wrong, and what is stale",
      "description": "Make derived state current, then report: orientation, truth checks ordered by cost of being wrong, and staleness. Read-only; gates nothing.",
      "argumentHint": "[vault|repo|all]",
      "reference": "reference/status.md",
      "weight": "medium"
    },
    {
      "name": "clean",
      "audience": "all",
      "blurb": "removes what the vault does not need",
      "description": "Mechanical cleanup: tags, wikilink form, dates, off-schema frontmatter, archive sweeps. Net-subtractive; never creates a vault file. Previews then applies.",
      "argumentHint": "[--folder <path>]",
      "reference": "reference/clean.md",
      "weight": "medium"
    },
    {
      "name": "dream",
      "audience": "all",
      "blurb": "reads the prose and reports what only judgement finds",
      "description": "Semantic review: at most twenty scored candidates, judged by Claude, applied through clean's primitives. One report per run.",
      "argumentHint": "[--folder <path>]",
      "reference": "reference/dream.md",
      "weight": "heavy"
    },
    {
      "name": "draw",
      "audience": "full",
      "blurb": "builds diagrams, canvases, and bases",
      "description": "Create a canvas, base, or mermaid diagram, either hand-authored or generated from vault data.",
      "argumentHint": "<canvas|base|diagram> <name|type>",
      "reference": "reference/draw.md",
      "weight": "light",
      "files": [
        "scripts/graph.py",
        "scripts/test_graph.py",
        "skills/adjudant/reference/draw.md"
      ]
    },
    {
      "name": "board",
      "audience": "all",
      "blurb": "runs a self-hosted kanban",
      "description": "Scaffold a self-hosted kanban seeded from tasks/: drag to move, saved to disk. Re-seeding keeps your dragged cards. Use --project SLUG or --all.",
      "argumentHint": "[scaffold|serve|status] [--project SLUG|--all] [--from-tasks] [--force]",
      "reference": "reference/board.md",
      "weight": "light"
    }
  ],
  "content_references": [
    {"path": "reference/content-canvas.md", "label": "`.canvas` files", "audience": "full"},
    {"path": "reference/content-bases.md", "label": "`.base` files", "audience": "all"},
    {"path": "reference/content-mermaid.md", "label": "mermaid diagrams (syntax)", "audience": "full"},
    {"path": "reference/mermaid-generation-rules.md", "label": "mermaid generation discipline (always applies when producing fences)", "audience": "full"},
    {"path": "reference/content-markdown.md", "label": "Obsidian-flavoured markdown (callouts, embeds, wikilinks)", "audience": "all"},
    {"path": "reference/content-clipper.md", "label": "Web Clipper templates", "audience": "all"},
    {"path": "reference/content-cli.md", "label": "Obsidian CLI", "audience": "all"},
    {"path": "reference/repo-standards.md", "label": "code-repo conventions (the `status`/`clean` `[repo|all]` target)", "audience": "all"}
  ]
}
```

Before writing this, run `python3 -c "import json,sys;print([v['name'] for v in json.load(open('command-metadata.json'))['verbs']])"` from `adjudant/scripts/`. If the names on disk are not exactly `['connect', 'status', 'clean', 'dream', 'draw', 'board']`, plan 3 landed a different surface. **Stop and report the difference** rather than overwriting it: keep the names on disk, keep every existing `description`, `argumentHint`, `reference` and `weight` verbatim, and add only `audience`, `blurb`, `files` and `content_references`.

The audience split follows the twin's shipped surface: it has never carried `draw`, because canvases, bases and mermaid generation are a large surface with its own reference set. Everything else is `all`.

- [ ] **Step 4: Write the renderer**

Create `adjudant/scripts/render_verb_surfaces.py`:

```python
#!/usr/bin/env python3
"""Render every verb-derived doc surface from scripts/command-metadata.json.

Ten places used to spell out the verb list by hand: SKILL.md's frontmatter
description and argument-hint, its verb-count sentence, its router table, its
cost-gate weight bullets and its content-authoring list; the README's heading
and verb table; plugin.json's description; and the marketplace entry's
description. Twice over, because adjudant ships in two repositories. The
`verb-surface-parity` validator existed only to notice when they disagreed,
and the marketplace's own AGENTS.md still said eleven verbs when there were
thirteen.

They are rendered from one file now. `build-profile.json` says which audience
this build serves, so the same renderer produces the full build's verbs and the
public build's subset.

Usage:
    python3 render_verb_surfaces.py            # write the surfaces
    python3 render_verb_surfaces.py --check    # exit 1 if any surface is stale

Stdlib only. Idempotent: a second run reports nothing changed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import _profile

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# Index to word. validate.py imports this and inverts it, so the language table
# lives once.
NUMBER_WORDS: tuple[str, ...] = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
)

ROUTER_TAIL = ("| _(internals)_ | `reference/internals.md` | Not a verb. Hook "
               "wiring, verb-to-helper map, environment probes. Load only when "
               "the question is about adjudant's own machinery |")

SKILL_SUMMARY = ("Vault editor/writer and project initializer. One skill, one "
                 "command, {count} verbs.")

SKILL_DESCRIPTION = (
    "Operate an Obsidian vault from a code project. `/adjudant {{{pipes}}}` — "
    "{clauses}. Also fires whenever decisions, sessions, or notes are written "
    "into a linked vault.")

PLUGIN_DESCRIPTION = (
    "Operate an Obsidian vault from your code project. One command, /adjudant, "
    "with {count} verbs: {clauses}. Schema-locked vault writes, cost-gated "
    "heavy verbs, and ambient hooks that keep session notes, handoffs, and the "
    "board current. Stdlib-only Python helpers, no build step.{suffix}")

WEIGHT_BULLETS = (
    "- **Heavy verbs** ({heavy}): run the backing helper with `--estimate-only` "
    "FIRST. If `cost.warn` is true, stop, show the numbers, and ask the user to "
    "proceed, scope down, or abort. Proceed only on explicit confirmation. If "
    "`warn` is false, run normally and include the estimate as one line.\n"
    "- **Medium verbs** ({medium}): no pre-flight. The helper's JSON carries a "
    "`cost` block; render it as one line.\n"
    "- **Light verbs** ({light}): no estimate; the static weight badge is enough."
)


class SurfaceError(RuntimeError):
    """A surface is missing its markers, or its shape is not what we render."""


def _audience() -> str:
    return _profile.audience()


def load_metadata(plugin_root: Path = PLUGIN_ROOT) -> dict[str, Any]:
    path = plugin_root / "scripts" / "command-metadata.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SurfaceError(f"{path}: {exc}") from exc


def _wanted(entry: dict[str, Any], audience: str) -> bool:
    """An entry ships in this build. `all` ships everywhere; `full` only in the
    full build. An entry with no audience is a metadata bug, not a default."""
    declared = entry.get("audience")
    if declared not in ("all", "full"):
        raise SurfaceError(
            f"{entry.get('name') or entry.get('path')}: audience must be "
            f"'all' or 'full', got {declared!r}")
    return declared == "all" or audience == "full"


def verbs_for(meta: dict[str, Any], audience: str) -> list[dict[str, Any]]:
    return [v for v in meta["verbs"] if _wanted(v, audience)]


def content_refs_for(meta: dict[str, Any], audience: str) -> list[dict[str, Any]]:
    return [c for c in meta["content_references"] if _wanted(c, audience)]


def full_only_paths(meta: dict[str, Any]) -> set[str]:
    """Plugin-relative paths a public build must not carry, derived from data.

    Task 8's generator uses this as its deletion allowlist: a file it cannot
    trace back to a full-only verb, a full-only content reference, or a
    capability this build declares is never deleted.
    """
    out: set[str] = set()
    for verb in meta["verbs"]:
        if verb.get("audience") == "full":
            out.update(verb.get("files", []))
    for ref in meta["content_references"]:
        if ref.get("audience") == "full":
            out.add(f"skills/adjudant/{ref['path']}")
    for cap in _profile.capabilities():
        out.add(f"skills/adjudant/{cap['reference']}")
    return out


def _escape_pipes(text: str) -> str:
    """A raw `|` closes a markdown cell. The hint `[vault|repo|all]` is the
    common case, and forgetting it is how the projects index grew rows with
    the wrong column count."""
    return text.replace("|", "\\|")


def _clauses(verbs: list[dict[str, Any]]) -> str:
    return "; ".join(f"{v['name']} {v['blurb']}" for v in verbs)


def _pipes(verbs: list[dict[str, Any]]) -> str:
    return "|".join(v["name"] for v in verbs)


def _count_word(verbs: list[dict[str, Any]]) -> str:
    n = len(verbs)
    if n >= len(NUMBER_WORDS):
        raise SurfaceError(f"{n} verbs is past the spelled-out range")
    return NUMBER_WORDS[n]


def render_router(verbs: list[dict[str, Any]]) -> str:
    rows = ["| Verb | Loads | Purpose |", "|---|---|---|"]
    rows += [f"| `{v['name']}` | `{v['reference']}` | {_escape_pipes(v['description'])} |"
             for v in verbs]
    rows.append(ROUTER_TAIL)
    return "\n".join(rows)


def render_content_refs(refs: list[dict[str, Any]]) -> str:
    return "\n".join(f"- `{r['path']}` — {r['label']}" for r in refs)


def render_weights(verbs: list[dict[str, Any]]) -> str:
    def named(weight: str) -> str:
        picked = [f"`{v['name']}`" for v in verbs if v["weight"] == weight]
        return ", ".join(picked) if picked else "none in this build"
    return WEIGHT_BULLETS.format(heavy=named("heavy"), medium=named("medium"),
                                 light=named("light"))


def render_readme_table(verbs: list[dict[str, Any]]) -> str:
    rows = [f"## The {_count_word(verbs)} verbs", "",
            "| Verb | What it does |", "|---|---|"]
    for v in verbs:
        hint = "" if v["argumentHint"] == "(no args)" else " " + v["argumentHint"]
        cmd = _escape_pipes(f"/adjudant {v['name']}{hint}")
        blurb = v["blurb"][0].upper() + v["blurb"][1:]
        rows.append(f"| `{cmd}` | {blurb}. |")
    return "\n".join(rows)


def replace_region(text: str, tag: str, body: str) -> str:
    start, end = f"<!-- {tag}:START -->", f"<!-- {tag}:END -->"
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0 or j < i:
        raise SurfaceError(f"missing or inverted {tag} markers")
    return text[:i + len(start)] + "\n" + body.rstrip("\n") + "\n" + text[j:]


def set_frontmatter_field(text: str, key: str, value: str) -> str:
    """Replace `key:` inside the frontmatter BLOCK only. Borrowed from
    bump_plugin_version._set_skill_version, which learned the hard way that a
    body line starting with the same key must not be touched."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        raise SurfaceError("SKILL.md has no frontmatter")
    close = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
    if close is None:
        raise SurfaceError("SKILL.md frontmatter is not closed")
    for i in range(1, close):
        if lines[i].startswith(f"{key}:"):
            lines[i] = f"{key}: {value}"
            return "\n".join(lines)
    raise SurfaceError(f"SKILL.md frontmatter has no {key}:")


def render(plugin_root: Path, audience: str) -> dict[Path, str]:
    """The desired text of every markdown surface. Nothing is written here."""
    meta = load_metadata(plugin_root)
    verbs = verbs_for(meta, audience)
    refs = content_refs_for(meta, audience)
    count = _count_word(verbs)

    skill_path = plugin_root / "skills" / "adjudant" / "SKILL.md"
    skill = skill_path.read_text()
    skill = set_frontmatter_field(skill, "description", SKILL_DESCRIPTION.format(
        pipes=_pipes(verbs), clauses=_clauses(verbs)))
    skill = set_frontmatter_field(skill, "argument-hint",
                                  f'"[{_pipes(verbs)}] [args]"')
    skill = replace_region(skill, "VERBS:SUMMARY", SKILL_SUMMARY.format(count=count))
    skill = replace_region(skill, "VERBS:ROUTER", render_router(verbs))
    skill = replace_region(skill, "VERBS:WEIGHTS", render_weights(verbs))
    skill = replace_region(skill, "VERBS:CONTENT-REFS", render_content_refs(refs))

    readme_path = plugin_root / "README.md"
    readme = replace_region(readme_path.read_text(), "VERBS:TABLE",
                            render_readme_table(verbs))

    return {skill_path: skill, readme_path: readme}


def _set_json_field(path: Path, key: str, value: str) -> bool:
    if not path.is_file():
        return False
    data = json.loads(path.read_text())
    if data.get(key) == value:
        return False
    data[key] = value
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return True


def _set_marketplace_description(path: Path, plugin: str, value: str) -> bool:
    if not path.is_file():
        return False
    data = json.loads(path.read_text())
    entry = next((p for p in data.get("plugins", []) if p.get("name") == plugin), None)
    if entry is None or entry.get("description") == value:
        return False
    entry["description"] = value
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return True


def apply(plugin_root: Path = PLUGIN_ROOT, check: bool = False) -> list[str]:
    """Write every surface. Returns the paths that changed, or would change
    under `check`. `check` writes nothing at all, including the JSON."""
    audience = _audience()
    meta = load_metadata(plugin_root)
    verbs = verbs_for(meta, audience)
    description = PLUGIN_DESCRIPTION.format(
        count=_count_word(verbs), clauses=_clauses(verbs),
        suffix=_profile.description_suffix())

    changed: list[str] = []
    for path, text in render(plugin_root, audience).items():
        if path.read_text() != text:
            changed.append(str(path))
            if not check:
                path.write_text(text)

    plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
    marketplace = plugin_root.parent / ".claude-plugin" / "marketplace.json"
    if check:
        if plugin_json.is_file():
            if json.loads(plugin_json.read_text()).get("description") != description:
                changed.append(str(plugin_json))
        if marketplace.is_file():
            entry = next((p for p in json.loads(marketplace.read_text()).get("plugins", [])
                          if p.get("name") == meta["name"]), None)
            if entry is not None and entry.get("description") != description:
                changed.append(str(marketplace))
    else:
        if _set_json_field(plugin_json, "description", description):
            changed.append(str(plugin_json))
        if _set_marketplace_description(marketplace, meta["name"], description):
            changed.append(str(marketplace))
    return changed


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="render_verb_surfaces.py",
        description="Render the verb-derived doc surfaces from command-metadata.json.")
    p.add_argument("--check", action="store_true",
                   help="report stale surfaces and exit 1; write nothing")
    p.add_argument("--plugin-root", default=str(PLUGIN_ROOT),
                   help="plugin directory (default: this script's plugin)")
    args = p.parse_args(argv)
    try:
        changed = apply(Path(args.plugin_root).expanduser().resolve(), check=args.check)
    except (SurfaceError, _profile.ProfileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not changed:
        print("surfaces are current")
        return 0
    verb = "stale" if args.check else "updated"
    for path in changed:
        print(f"  {verb} {path}")
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Put the markers in SKILL.md and README.md**

In `adjudant/skills/adjudant/SKILL.md`:

- Wrap the summary sentence (currently line 12, `Vault editor/writer and project initializer. One skill, one command, thirteen verbs. Pairs with hookify...`) in `<!-- VERBS:SUMMARY:START -->` / `<!-- VERBS:SUMMARY:END -->`. The renderer emits the sentence without the hookify clause; move that clause into the paragraph below the region if it should survive, since it is a profile fact, not a verb fact.
- Wrap the router table (currently lines 16-31, header row through the `_(internals)_` row) in `<!-- VERBS:ROUTER:START -->` / `<!-- VERBS:ROUTER:END -->`.
- Wrap the three weight bullets in the cost-gate section (currently lines 49-51: heavy, medium, light) in `<!-- VERBS:WEIGHTS:START -->` / `<!-- VERBS:WEIGHTS:END -->`. Leave the surrounding bullets (`check all` summing, the unresolvable case, the threshold line from task 2) outside the region.
- Wrap the content-authoring bullet list (currently lines 72-79) in `<!-- VERBS:CONTENT-REFS:START -->` / `<!-- VERBS:CONTENT-REFS:END -->`.

In `adjudant/README.md`, wrap the heading and table (currently lines 23-39, `## The thirteen verbs` through the last verb row) in `<!-- VERBS:TABLE:START -->` / `<!-- VERBS:TABLE:END -->`.

- [ ] **Step 6: Render, and see the surfaces converge**

Run: `cd adjudant/scripts && python3 render_verb_surfaces.py`
Expected: a list of updated paths, then a clean second run.

Run: `cd adjudant/scripts && python3 render_verb_surfaces.py --check`
Expected: `surfaces are current`, exit 0.

Run: `cd adjudant/scripts && python3 -m unittest test_render_verb_surfaces -v`
Expected: PASS, 14 tests.

- [ ] **Step 7: Turn validator 15 from a comparison into a generation check**

In `adjudant/scripts/validate.py`, replace `validate_verb_surface_parity` (currently lines 474-517) with:

```python
def validate_verb_surfaces_generated(r: Result) -> None:
    """15. verb-surfaces-generated — the ten verb-derived doc surfaces are
    rendered from command-metadata.json, not typed twice.

    This used to compare copies: it checked that each verb name appeared in
    plugin.json, the README and the marketplace entry, and that any spelled-out
    "<N> verbs" agreed. Comparing copies is the weaker test, and it still let
    the marketplace's own AGENTS.md say eleven verbs when there were thirteen.
    Now there is one copy, and this fails when it is stale.
    """
    name = "verb-surfaces-generated"
    try:
        stale = render_verb_surfaces.apply(ROOT, check=True)
    except (render_verb_surfaces.SurfaceError, _profile.ProfileError) as exc:
        r.add_fail(name, f"could not render: {exc}")
        return
    if stale:
        r.add_fail(name, "stale surfaces (run scripts/render_verb_surfaces.py): "
                         + ", ".join(Path(p).name for p in stale))
        return
    r.add_pass(name)
```

Add `import render_verb_surfaces` beside `import _profile`, replace `_NUMBER_WORDS` (currently lines 467-471) with:

```python
_NUMBER_WORDS = {word: n for n, word in enumerate(render_verb_surfaces.NUMBER_WORDS) if n}
```

replace the call at line 1257 with `validate_verb_surfaces_generated(r)`, and change the roster's line 15 (currently line 21) to:

```
 15. verb-surfaces-generated  — the ten verb-derived doc surfaces are rendered from command-metadata.json, not typed twice
```

`_NUMBER_WORDS` still has one reader: leave it in place if `grep -n "_NUMBER_WORDS" validate.py` shows another use, and delete it if the parity validator was the only one.

- [ ] **Step 8: Update the validator's own tests**

In `adjudant/scripts/test_validate.py`, replace class `TestVerbSurfaceParity` (line 157) with:

```python
class TestVerbSurfacesGenerated(unittest.TestCase):
    """15. Runs against the REAL tree: the fixture in _build() has no markers,
    and a validator that only ever sees a fixture proves nothing about what
    ships."""

    def test_the_shipped_surfaces_are_current(self):
        r = Result()
        validate.validate_verb_surfaces_generated(r)
        self.assertIn("verb-surfaces-generated", r.passes, r.failures)

    def test_a_stale_surface_fails(self):
        import shutil as _sh
        import tempfile as _tf
        real = Path(__file__).resolve().parent.parent
        with _tf.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "adjudant"
            _sh.copytree(real, fake, symlinks=True,
                         ignore=_sh.ignore_patterns("__pycache__", ".pytest_cache"))
            readme = fake / "README.md"
            readme.write_text(readme.read_text().replace(
                "| Verb | What it does |", "| Verb | What it once did |"))
            orig = validate.ROOT
            validate.ROOT = fake
            try:
                r = Result()
                validate.validate_verb_surfaces_generated(r)
            finally:
                validate.ROOT = orig
            self.assertTrue(any("verb-surfaces-generated" in f for f in r.failures))
```

`TestModuleDocstringRoster` (line 1118) already asserts the roster is numbered 1..N with no gaps and that the names match `main()`'s calls, so the rename is checked for free.

- [ ] **Step 9: Run everything**

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | grep -E "^Ran |^OK|^FAILED"`
Expected: `OK`

Run: `cd ../.. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

Run: `cd ../.. && python3 scripts/check_marketplace_versions.py 2>&1 | tail -1`
Expected: `PASS`. The renderer rewrites the marketplace entry's `description` and never its `version`, so the parity guard is untouched.

- [ ] **Step 10: Commit**

```bash
git add adjudant/scripts/command-metadata.json adjudant/scripts/render_verb_surfaces.py \
  adjudant/scripts/test_render_verb_surfaces.py adjudant/scripts/validate.py \
  adjudant/scripts/test_validate.py adjudant/skills/adjudant/SKILL.md \
  adjudant/README.md adjudant/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "feat(adjudant): render the ten verb-derived surfaces from one file

SKILL.md's description, argument-hint, verb count, router, weight bullets and
content list; the README's heading and table; plugin.json's description; the
marketplace entry. Ten hand-typed copies of one list, twice over because
adjudant ships in two repos.

command-metadata.json gains audience, blurb and files per verb, plus the
content-reference list. render_verb_surfaces.py writes the rest, and validator
15 stops comparing copies: it now fails when a surface is stale.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: The twin gets a gate

The twin ships 31 validators and 995 tests and runs neither automatically. It has no `.pre-commit-config.yaml`, no `.github/`, and no `scripts/` at its root, so a version bump there is four hand-edits with nothing checking them. This is the first task that writes into the second repository.

**Files:** (every path but the last is relative to `$ADJUDANT_TWIN`)
- Create: `.pre-commit-config.yaml`
- Create: `.github/workflows/validate.yml`
- Create: `scripts/bump_plugin_version.py`, `scripts/test_bump_plugin_version.py`
- Modify (main): `scripts/bump_plugin_version.py:4-7` (docstring), so the two copies are byte-identical

**Interfaces:**
- Consumes: nothing from earlier tasks. Task 9's parity gate requires `scripts/bump_plugin_version.py` to be byte-identical across the repos, which is why main's docstring is reworded here rather than in the twin's copy.
- Produces: `bump(plugin: str, version: str, root: Path = ROOT) -> list[str]` in the twin, with the same signature as main's.

- [ ] **Step 1: Confirm the twin's baseline before touching it**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
( cd "$TWIN/adjudant/scripts" && python3 -m unittest discover -p 'test_*.py' 2>&1 | grep -E "^Ran |^OK|^FAILED" )
( cd "$TWIN" && python3 adjudant/scripts/validate.py 2>&1 | tail -2 )
ls "$TWIN/.pre-commit-config.yaml" "$TWIN/scripts" 2>&1
```

Expected: `OK` with the twin's test count, `PASS — 31 validator(s) green`, and `No such file or directory` for both of the last two paths. If the suite or the validators are red before this plan touches anything, stop: fix the twin on its own first.

- [ ] **Step 2: Reword main's bump docstring so both copies can be identical**

The twin has no `marketplace-version-parity` guard, so main's docstring line would be false there. Rewording once is cheaper than forking the file. In `adjudant/../scripts/bump_plugin_version.py` (that is, main's `scripts/bump_plugin_version.py`), replace lines 4-7:

```python
The `version-consistency` validator (adjudant/scripts/validate.py) requires a
plugin's version to match across up to four files, and a repo may add a
marketplace-parity guard on top. Keeping them in sync by hand is error-prone —
this writes all of them atomically.
```

Run: `cd scripts && python3 -m unittest test_bump_plugin_version -v 2>&1 | grep -E "^Ran |^OK|^FAILED"`
Expected: `OK`. The docstring is not asserted anywhere.

- [ ] **Step 3: Copy the bumper and its tests into the twin**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
mkdir -p "$TWIN/scripts"
cp scripts/bump_plugin_version.py scripts/test_bump_plugin_version.py "$TWIN/scripts/"
diff scripts/bump_plugin_version.py "$TWIN/scripts/bump_plugin_version.py" && echo "byte-identical"
```

Expected: `byte-identical`. `ROOT = Path(__file__).resolve().parent.parent` resolves to the twin's root, and `bump()` globs `<plugin>/skills/*/SKILL.md`, so it finds the twin's single skill without change. `check_marketplace_versions.py` is deliberately **not** copied: `version-consistency` (validator 7 in the twin's roster) already reads `ROOT.parent/.claude-plugin/marketplace.json` when it is present, which covers the same ground with one fewer file to keep in step.

- [ ] **Step 4: Prove the bumper works in the twin, then put it back**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
( cd "$TWIN/scripts" && python3 -m unittest test_bump_plugin_version -v 2>&1 | grep -E "^Ran |^OK|^FAILED" )
( cd "$TWIN" && python3 scripts/bump_plugin_version.py adjudant 1.0.1 && python3 adjudant/scripts/validate.py 2>&1 | tail -2 )
( cd "$TWIN" && python3 scripts/bump_plugin_version.py adjudant 1.0.0 && git diff --stat )
```

Expected: `OK` from the tests; the bump reports three updated files (`plugin.json`, `command-metadata.json`, `SKILL.md`) plus `marketplace.json`; `PASS — 31 validator(s) green`; and after the second bump `git diff --stat` is empty. An empty diff is the real assertion: the round trip proves the bumper touches exactly the four lockstep files and nothing else.

- [ ] **Step 5: Wire the pre-commit hook**

Create `$ADJUDANT_TWIN/.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: adjudant-validate
        name: Adjudant — validate vault standards & template coherence
        entry: python3 adjudant/scripts/validate.py
        language: system
        pass_filenames: false
        stages: [pre-commit]
      - id: adjudant-tests
        name: Adjudant — unit tests
        entry: python3 -m unittest discover -s adjudant/scripts -p "test_*.py"
        language: system
        pass_filenames: false
        stages: [pre-commit]
```

The twin gets the test run in its hook and main does not, because main has CI on every push and the twin has never had any. Step 6 gives the twin CI too; the hook stays as the faster local gate.

Install and prove it fires:

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
( cd "$TWIN" && pre-commit install && pre-commit run --all-files )
```

Expected: both hooks `Passed`.

- [ ] **Step 6: Give the twin CI**

Create `$ADJUDANT_TWIN/.github/workflows/validate.yml`:

```yaml
name: validate

on:
  push:
    branches: [master]
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.9"
      - name: Adjudant validators
        run: python3 adjudant/scripts/validate.py
      - name: Adjudant unit tests
        run: python3 -m unittest discover -s adjudant/scripts -p "test_*.py"
      - name: Repo-root script tests
        run: python3 -m unittest discover -s scripts -p "test_*.py"
```

The branch is `master`, which is what `origin/HEAD` points at in the twin. The Python is pinned to `3.9`, the declared floor, so the twin's CI actually tests the floor. Main's workflow pins `3.12` and therefore has never tested it; leave that alone here and note it under "Not in this plan".

- [ ] **Step 7: Prove the gate catches a real break**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
( cd "$TWIN" && python3 -c "
import json, pathlib
p = pathlib.Path('adjudant/.claude-plugin/plugin.json')
d = json.loads(p.read_text()); d['version'] = '9.9.9'
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')" \
  && python3 adjudant/scripts/validate.py 2>&1 | grep -E "version-consistency|FAIL" ; git checkout -- adjudant/.claude-plugin/plugin.json )
```

Expected: a `version-consistency` failure naming the mismatch, then a clean checkout. Before this task nothing in the twin would have caught that.

- [ ] **Step 8: Commit, in the twin**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
cd "$TWIN"
git add .pre-commit-config.yaml .github/workflows/validate.yml scripts/
git commit -m "chore: wire the validators to pre-commit and CI, and add the version bumper

This repo shipped 31 validators and a full unit suite and ran neither
automatically, so a version bump was four hand-edits with nothing checking
them. Pre-commit runs the validators and the tests; CI reruns both on master
and on every PR, pinned to the declared 3.9 floor.

bump_plugin_version.py is byte-identical to the marketplace copy.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 9: Commit the docstring change, in main**

```bash
git add scripts/bump_plugin_version.py
git commit -m "chore(marketplace): reword the bumper docstring so both repos can share it

It named a marketplace-parity guard that only this repo has, which would have
made the twin's copy false and forced a fork of a file that has no reason to
differ.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: The generator, and the rule that no deletion is unnamed

**Files:**
- Create: `scripts/generate_twin.py`, `scripts/test_generate_twin.py` (main repo root, beside `bump_plugin_version.py`)

**Interfaces:**
- Consumes: `test_backport_guard.missing_markers()` and `BACKPORT_MARKERS` (task 1), `render_verb_surfaces.full_only_paths()` and `apply()` (task 6), `_profile.capabilities()` (tasks 2 and 3).
- Produces, used by task 9:
  - `generate_twin.PROFILE_FILE: str` — `"scripts/build-profile.json"`, the one file never copied.
  - `generate_twin.GENERATED: frozenset[str]` — plugin-relative paths the renderer owns in the twin.
  - `generate_twin.IDENTITY_KEYS: tuple[str, ...]` — `plugin.json` keys the generator preserves.
  - `generate_twin.AUDIENCE_AUTHORED: frozenset[str]` — `GUIDE.md` and `reference/internals.md`, written per audience and never copied.
  - `generate_twin.missing_backport(plugin_root: Path) -> list[str]` — delegates to task 1's guard.
  - `generate_twin.apply_plan(main_root: Path, twin_root: Path, p: Plan) -> list[str]`
  - `generate_twin.Plan` — a `NamedTuple` with `create: list[str]`, `update: list[str]`, `delete: list[str]`, `unexplained: list[str]`.
  - `generate_twin.plan(main_root: Path, twin_root: Path) -> Plan`
  - `generate_twin.main(argv: Optional[list[str]] = None) -> int` — `0` clean, `1` a dry run with work pending, `2` the back-port guard failed, `3` an unexplained deletion.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_generate_twin.py`:

```python
"""Tests for scripts/generate_twin.py — the one irreversible step in v3.

The twin held code that existed nowhere else, so the failure this file exists
to prevent is a regeneration that quietly drops something and reports success.
Two rules carry that: the back-port guard must pass before anything is planned,
and every deletion must trace back to data (a full-only verb, a full-only
content reference, or a capability this build declares). Anything else stops
the run.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_twin

MAIN_ROOT = Path(__file__).resolve().parent.parent


def _copy_main(dest: Path) -> Path:
    shutil.copytree(MAIN_ROOT / "adjudant", dest / "adjudant", symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    (dest / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    shutil.copy(MAIN_ROOT / ".claude-plugin" / "marketplace.json",
                dest / ".claude-plugin" / "marketplace.json")
    return dest


class TestBackportGate(unittest.TestCase):

    def test_a_missing_backport_marker_stops_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_main = _copy_main(Path(tmp) / "main")
            doc = fake_main / "adjudant" / "skills" / "adjudant" / "reference" / "connect.md"
            doc.write_text(doc.read_text().replace(
                "No vault yet? Guided location setup", "Setup"))
            twin = _copy_main(Path(tmp) / "twin")
            rc = generate_twin.main(["--main-root", str(fake_main),
                                     "--twin", str(twin)])
            self.assertEqual(rc, 2)

    def test_the_real_tree_passes_the_gate(self):
        self.assertEqual(generate_twin.missing_backport(MAIN_ROOT / "adjudant"), [])


class TestPlan(unittest.TestCase):

    def test_an_identical_tree_plans_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            p = generate_twin.plan(main_root, twin)
            self.assertEqual(p.delete, [])
            self.assertEqual(p.unexplained, [])

    def test_a_twin_only_file_is_unexplained_and_never_deleted(self):
        # The exact shape of the disaster this guards: something that exists
        # only in the twin.
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            stray = twin / "adjudant" / "scripts" / "twin_only_helper.py"
            stray.write_text("# only here\n")
            p = generate_twin.plan(main_root, twin)
            self.assertIn("scripts/twin_only_helper.py", p.unexplained)
            self.assertNotIn("scripts/twin_only_helper.py", p.delete)

    def test_an_unexplained_deletion_stops_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            (twin / "adjudant" / "scripts" / "twin_only_helper.py").write_text("# x\n")
            rc = generate_twin.main(["--main-root", str(main_root),
                                     "--twin", str(twin), "--apply"])
            self.assertEqual(rc, 3)
            self.assertTrue(
                (twin / "adjudant" / "scripts" / "twin_only_helper.py").is_file(),
                "an unexplained file was deleted anyway")

    def test_full_only_files_are_named_deletions(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            p = generate_twin.plan(main_root, twin)
            self.assertIn("scripts/graph.py", p.delete)
            self.assertIn("skills/adjudant/reference/draw.md", p.delete)
            self.assertEqual(p.unexplained, [])

    def test_the_profile_is_never_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            prof = twin / "adjudant" / "scripts" / "build-profile.json"
            prof.write_text(json.dumps({"marker": "twin"}) + "\n")
            p = generate_twin.plan(main_root, twin)
            self.assertNotIn(generate_twin.PROFILE_FILE, p.update)
            self.assertNotIn(generate_twin.PROFILE_FILE, p.delete)


class TestApply(unittest.TestCase):

    def test_a_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            target = twin / "adjudant" / "scripts" / "graph.py"
            (twin / "adjudant" / "scripts" / "tidy.py").write_text("# stale\n")
            generate_twin.main(["--main-root", str(main_root), "--twin", str(twin)])
            self.assertTrue(target.is_file(), "dry run deleted a file")
            self.assertEqual(
                (twin / "adjudant" / "scripts" / "tidy.py").read_text(), "# stale\n")

    def test_apply_copies_the_shared_tree_and_prunes_the_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            (twin / "adjudant" / "scripts" / "tidy.py").write_text("# stale\n")
            rc = generate_twin.main(["--main-root", str(main_root),
                                     "--twin", str(twin), "--apply"])
            self.assertEqual(rc, 0)
            self.assertEqual(
                (twin / "adjudant" / "scripts" / "tidy.py").read_text(),
                (main_root / "adjudant" / "scripts" / "tidy.py").read_text())
            self.assertFalse((twin / "adjudant" / "scripts" / "graph.py").exists())

    def test_apply_keeps_the_twins_plugin_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            pj = twin / "adjudant" / ".claude-plugin" / "plugin.json"
            data = json.loads(pj.read_text())
            data.update({"version": "1.0.0",
                         "author": {"name": "Tom Vanderheyden"},
                         "homepage": "https://example.invalid/twin",
                         "repository": "https://example.invalid/twin"})
            pj.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            generate_twin.main(["--main-root", str(main_root),
                                "--twin", str(twin), "--apply"])
            after = json.loads(pj.read_text())
            self.assertEqual(after["version"], "1.0.0")
            self.assertEqual(after["author"], {"name": "Tom Vanderheyden"})
            self.assertEqual(after["homepage"], "https://example.invalid/twin")

    def test_the_guided_setup_survives_a_regeneration(self):
        # The named risk, asserted directly.
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            generate_twin.main(["--main-root", str(main_root),
                                "--twin", str(twin), "--apply"])
            walk = (twin / "adjudant" / "scripts" / "_vault_walk.py").read_text()
            connect = (twin / "adjudant" / "scripts" / "connect.py").read_text()
            doc = (twin / "adjudant" / "skills" / "adjudant"
                   / "reference" / "connect.md").read_text()
            self.assertIn("def suggest_vault_roots(", walk)
            self.assertIn("def _describe_vault_root(", walk)
            self.assertIn("--create-vault", connect)
            self.assertIn("--suggest-vaults", connect)
            self.assertIn("No vault yet? Guided location setup", doc)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd scripts && python3 -m unittest test_generate_twin -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generate_twin'`

- [ ] **Step 3: Write the generator**

Create `scripts/generate_twin.py`:

```python
#!/usr/bin/env python3
"""Generate the public twin's adjudant from this marketplace's copy.

The twin is `furtive-follies`, a reduced public build. It used to be a
hand-maintained fork, which meant every shared edit had to be made twice and
the trees drifted between edits. v3 moved every legitimate difference into
`adjudant/scripts/build-profile.json` and `command-metadata.json`, so the rest
of the tree can simply be copied.

The twin also held code that existed nowhere else — the guided vault setup —
so the failure this script is built around is a regeneration that drops
something and reports success. Two rules prevent it:

  1. The back-port guard runs first. If any marker in
     `test_backport_guard.BACKPORT_MARKERS` is missing from THIS tree, nothing
     is planned and the run exits 2.
  2. Every deletion must trace back to data: a file listed by a `full`-audience
     verb, a `full`-audience content reference, or the reference doc of a
     capability this build declares. A file in the twin that the data cannot
     explain is reported as unexplained and never touched, and `--apply` exits
     3 rather than proceeding.

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
from typing import Any, NamedTuple, Optional

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

# plugin.json keys that belong to the repo, not to the build.
IDENTITY_KEYS = ("name", "version", "author", "homepage", "repository",
                 "license", "keywords")

# Hand-written per audience. Named here so they are a decision, not an accident.
AUDIENCE_AUTHORED = frozenset({
    "GUIDE.md",
    "skills/adjudant/reference/internals.md",
})

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}


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


def _deletable(plugin_root: Path) -> set[str]:
    """Paths a public build must not carry, derived from the metadata and the
    capability registry. This set is the ONLY licence to delete."""
    sys.path.insert(0, str(plugin_root / "scripts"))
    try:
        import render_verb_surfaces
        meta = render_verb_surfaces.load_metadata(plugin_root)
        return set(render_verb_surfaces.full_only_paths(meta))
    finally:
        sys.path.pop(0)


def plan(main_root: Path, twin_root: Path) -> Plan:
    main_plugin = main_root / "adjudant"
    twin_plugin = twin_root / "adjudant"
    ours = _plugin_files(main_plugin)
    theirs = _plugin_files(twin_plugin)
    deletable = _deletable(main_plugin)
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
    _sync_plugin_json(main_plugin, twin_plugin)
    _sync_metadata(main_plugin, twin_plugin)
    for path in _render_in_twin(twin_plugin):
        done.append(f"rendered {path}")
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

    p = plan(main_root, twin_root)
    for label, items in (("create", p.create), ("update", p.update),
                         ("delete", p.delete)):
        for rel in items:
            print(f"  {label} {rel}")
    if p.unexplained:
        print("\nerror: files exist in the twin that this build cannot explain.",
              file=sys.stderr)
        print("Nothing was deleted. Either add them to a verb's `files` list in "
              "command-metadata.json, or back-port them.", file=sys.stderr)
        for rel in p.unexplained:
            print(f"  unexplained {rel}", file=sys.stderr)
        return 3
    if not args.apply:
        pending = len(p.create) + len(p.update) + len(p.delete)
        print(f"\ndry run: {pending} change(s) pending; re-run with --apply")
        return 1 if pending else 0
    for line in apply_plan(main_root, twin_root, p):
        print(f"  {line}")
    print("\ntwin regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Two details in that file carry weight and are easy to lose. `_render_in_twin` repoints `_profile.PROFILE_PATH` and clears the `lru_cache` around the render, because one process reads two profiles from the same module and the second read would otherwise return the first. And `_plugin_files` skips symlinks, because `source/`, `.claude/` and `.gemini/` are symlinks into `skills/adjudant` and following them would copy the tree four times; both repos already carry those links, and the `harness-parity` validator fails loudly in either tree if one goes missing.

- [ ] **Step 4: Run the generator tests**

Run: `cd scripts && python3 -m unittest test_generate_twin -v`
Expected: PASS, 10 tests. `test_full_only_files_are_named_deletions` proves `graph.py` and `draw.md` are deletable; `test_a_twin_only_file_is_unexplained_and_never_deleted` and `test_an_unexplained_deletion_stops_the_run` are the pair that make the step safe.

- [ ] **Step 5: Run the repo-root suite and main's validators**

Run: `cd scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | grep -E "^Ran |^OK|^FAILED"`
Expected: `OK`

Run: `cd .. && python3 adjudant/scripts/validate.py 2>&1 | tail -2`
Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add scripts/generate_twin.py scripts/test_generate_twin.py
git commit -m "feat(marketplace): generate the public twin, refusing unnamed deletions

The twin held code that existed nowhere else, so the failure mode is a
regeneration that drops something and reports success. Two rules stop it: the
back-port guard runs before anything is planned, and every deletion must trace
back to a full-only verb, a full-only content reference, or a declared
capability. An unexplained file is reported and never touched.

Dry run by default. plugin.json identity, the build profile and the twin's
version all survive.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Regenerate, and prove it

The irreversible step, run once, with the proof standing afterwards.

**Files:**
- Create: `adjudant/scripts/test_twin_parity.py`
- Modify: `$ADJUDANT_TWIN/adjudant/scripts/build-profile.json` (new), and everything the generator writes

**Interfaces:**
- Consumes: `generate_twin.plan()`, `generate_twin.PROFILE_FILE`, `generate_twin.GENERATED`, `generate_twin.AUDIENCE_AUTHORED` (task 8); `render_verb_surfaces.load_metadata()` and `full_only_paths()` (task 6). `EXPECTED_DIVERGENCE` is a reasons map **over** the generator's set, never a second copy of it, and one test asserts the two agree.
- Produces: nothing importable. This is the gate.

- [ ] **Step 1: Check the twin is on the branch that publishes**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
git -C "$TWIN" branch --show-current
git -C "$TWIN" symbolic-ref --short refs/remotes/origin/HEAD
git -C "$TWIN" log --oneline master..HEAD | wc -l
git -C "$TWIN" status --short
```

On 2026-09-01 this reported `onboarding`, `origin/master`, `37`, and a clean tree. **A marketplace install pulls the default branch, so generating onto `onboarding` publishes nothing.** Stop and report: either `onboarding` merges into `master` first, or `origin/HEAD` moves. Do not regenerate onto a branch that is not the one `origin/HEAD` names, and do not regenerate onto a dirty tree.

- [ ] **Step 2: Snapshot the twin, so "reversible" is a fact and not a hope**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
git -C "$TWIN" rev-parse HEAD | tee /tmp/twin-before.sha
git -C "$TWIN" ls-files -s adjudant | shasum -a 256 | tee /tmp/twin-before-tree.sha
```

Every change from here is one `git -C "$TWIN" reset --hard $(cat /tmp/twin-before.sha)` away from being undone. Keep both files until step 9 passes.

- [ ] **Step 3: Write the twin's build profile**

Create `$ADJUDANT_TWIN/adjudant/scripts/build-profile.json`, carrying forward exactly the values the twin ships today (`_cost.py:30`, `_vault_walk.py:851-865`):

```json
{
  "audience": "public",
  "description_suffix": "",
  "cost_warn_tokens": 10000,
  "tags": {
    "bucket_b_migrations": {},
    "bucket_b_prefixes": [],
    "bucket_d_tag_prefixes": ["ob/"],
    "vague_topical_tags": [
      "architecture",
      "architecture-lockin",
      "architecture-source",
      "frontend",
      "backend",
      "cms",
      "moc",
      "toolbox",
      "scheduler"
    ],
    "crew_names": []
  },
  "capabilities": []
}
```

`capabilities: []` is what makes the twin's `status`, its briefing and its SessionStart banner print nothing about the suitcase while running the same code as main. `backend` is in the twin's vague list and not in main's; that is a real difference in what each vault wants dropped, and the profile is where it belongs.

- [ ] **Step 4: Dry-run the generator and read every line**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
python3 scripts/generate_twin.py --twin "$TWIN" | tee /tmp/twin-plan.txt
```

Expected: exit 1 with a list of `create` / `update` lines and **no `unexplained` lines**.

The `delete` list should be **empty**, and that is the healthy answer: the twin has never carried the seven full-only paths, so there is nothing to remove. Confirm they are absent and stay absent:

```bash
for f in scripts/graph.py scripts/test_graph.py \
         skills/adjudant/reference/draw.md \
         skills/adjudant/reference/content-canvas.md \
         skills/adjudant/reference/content-mermaid.md \
         skills/adjudant/reference/mermaid-generation-rules.md \
         skills/adjudant/reference/suitcase.md; do
  test -e "$TWIN/adjudant/$f" && echo "PRESENT $f"
  grep -q "create $f" /tmp/twin-plan.txt && echo "WOULD CREATE $f"
done
echo "checked"
```

Expected: nothing but `checked`. Six of those seven belong to `draw`, a `full`-audience verb and its content references; the seventh is the `suitcase` capability's reference doc, which the twin's empty registry does not declare. A `PRESENT` or `WOULD CREATE` line means the audience data and the tree disagree.

**Any line at all under `delete` is a stop.** Read it, and satisfy yourself that the data explains it, before applying. That moment is what this plan exists for.

If any `unexplained` line appears, exit code 3, nothing was touched. Either the file belongs in main (back-port it) or it belongs to a full-only verb (add it to that verb's `files` list in `command-metadata.json`). Never widen the deletable set to make a warning go away.

- [ ] **Step 5: Apply**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
python3 scripts/generate_twin.py --twin "$TWIN" --apply | tee /tmp/twin-apply.txt
python3 scripts/generate_twin.py --twin "$TWIN"
```

Expected: `twin regenerated` and exit 0 from the first, then `dry run: 0 change(s) pending` and exit 0 from the second. A second run that still has work pending means the generator is not idempotent; fix it before committing anything.

- [ ] **Step 6: Prove the twin still works**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
( cd "$TWIN/adjudant/scripts" && python3 -m unittest discover -p 'test_*.py' 2>&1 | grep -E "^Ran |^OK|^FAILED" )
( cd "$TWIN" && python3 adjudant/scripts/validate.py 2>&1 | tail -2 )
( cd "$TWIN" && pre-commit run --all-files )
```

Expected: `OK`, `PASS`, and both pre-commit hooks `Passed`. The twin's test count now equals main's minus the `draw` tests, because the two trees run the same files.

Then assert the named risk by hand:

```bash
grep -c "def suggest_vault_roots" "$TWIN/adjudant/scripts/_vault_walk.py"
grep -c -- "--create-vault" "$TWIN/adjudant/scripts/connect.py"
grep -c "No vault yet? Guided location setup" "$TWIN/adjudant/skills/adjudant/reference/connect.md"
( cd "$TWIN/adjudant/scripts" && python3 connect.py --suggest-vaults | head -5 )
```

Expected: `1`, `1`, `1`, and a JSON object with a `vault_roots` array. The guided onboarding story survived the regeneration.

- [ ] **Step 7: Write the standing parity gate**

Create `adjudant/scripts/test_twin_parity.py`:

```python
"""The two trees ship the same adjudant, and every difference is named.

Before v3 the twin was a hand-maintained fork: 35 files under adjudant/ differed
between the trees, and nothing in either repo could see it. Now the differences
are a short, deliberate list, and this test is what keeps it short.

It skips when the twin is not on this machine, so it never fails a clone that
has only one repo. Point it at a twin with ADJUDANT_TWIN.
"""

import filecmp
import os
import sys
import unittest
from pathlib import Path

MAIN_PLUGIN = Path(__file__).resolve().parent.parent
MAIN_ROOT = MAIN_PLUGIN.parent
TWIN_ROOT = Path(os.environ.get("ADJUDANT_TWIN")
                 or MAIN_ROOT.parent / "furtive-follies")

sys.path.insert(0, str(MAIN_ROOT / "scripts"))

# Files that may differ, each with the reason it may.
EXPECTED_DIVERGENCE = {
    "scripts/build-profile.json":
        "the one file a build may differ in: audience, threshold, tag rules, capabilities",
    "scripts/command-metadata.json":
        "generated: the public build ships the audience-filtered verb list, and its own version",
    "skills/adjudant/SKILL.md":
        "generated: description, argument-hint, router, weights and content refs follow the verb list",
    "README.md":
        "generated: the verb table and its heading follow the verb list",
    ".claude-plugin/plugin.json":
        "generated description, plus per-repo identity and version",
    "GUIDE.md":
        "hand-written per audience: the full build's walkthrough covers verbs the public build does not ship",
    "skills/adjudant/reference/internals.md":
        "hand-written per audience: the helper table lists draw's helper, a full-only verb",
}

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}


def _files(plugin_root: Path) -> set:
    out = set()
    for path in plugin_root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(plugin_root)
        if SKIP_DIRS & set(rel.parts):
            continue
        out.add(rel.as_posix())
    return out


@unittest.skipUnless((TWIN_ROOT / "adjudant").is_dir(),
                     f"no twin at {TWIN_ROOT}; set ADJUDANT_TWIN")
class TestTwinParity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import generate_twin
        cls.gen = generate_twin
        cls.twin_plugin = TWIN_ROOT / "adjudant"
        cls.ours = _files(MAIN_PLUGIN)
        cls.theirs = _files(cls.twin_plugin)

    def test_the_twin_holds_nothing_of_its_own(self):
        # The 2026-09-01 disaster shape: suggest_vault_roots lived only here.
        extra = sorted(self.theirs - self.ours)
        self.assertEqual(extra, [], f"files only in the twin: {extra}")

    def test_every_absence_is_a_named_full_only_path(self):
        import render_verb_surfaces
        meta = render_verb_surfaces.load_metadata(MAIN_PLUGIN)
        deletable = render_verb_surfaces.full_only_paths(meta)
        for rel in sorted(self.ours - self.theirs):
            self.assertIn(rel, deletable,
                          f"{rel} is missing from the twin and nothing explains it")

    def test_every_shared_file_is_byte_identical(self):
        drifted = []
        for rel in sorted(self.ours & self.theirs):
            if rel in EXPECTED_DIVERGENCE:
                continue
            if not filecmp.cmp(MAIN_PLUGIN / rel, self.twin_plugin / rel, shallow=False):
                drifted.append(rel)
        self.assertEqual(drifted, [],
                         "shared files differ; either regenerate the twin or add "
                         f"a named reason to EXPECTED_DIVERGENCE: {drifted}")

    def test_every_named_divergence_is_still_real(self):
        # A stale exemption hides the next drift. If a file stopped differing,
        # take it off the list.
        pointless = []
        for rel in sorted(EXPECTED_DIVERGENCE):
            a, b = MAIN_PLUGIN / rel, self.twin_plugin / rel
            if a.is_file() and b.is_file() and filecmp.cmp(a, b, shallow=False):
                pointless.append(rel)
        self.assertEqual(pointless, [],
                         f"these no longer differ; drop them from EXPECTED_DIVERGENCE: {pointless}")

    def test_the_repo_root_bumper_is_byte_identical(self):
        a = MAIN_ROOT / "scripts" / "bump_plugin_version.py"
        b = TWIN_ROOT / "scripts" / "bump_plugin_version.py"
        self.assertTrue(b.is_file(), "the twin has no version bumper")
        self.assertTrue(filecmp.cmp(a, b, shallow=False))

    def test_the_guided_setup_is_in_both_trees(self):
        for root in (MAIN_PLUGIN, self.twin_plugin):
            self.assertIn("def suggest_vault_roots(",
                          (root / "scripts" / "_vault_walk.py").read_text())
            self.assertIn("--create-vault", (root / "scripts" / "connect.py").read_text())
            self.assertIn("No vault yet? Guided location setup",
                          (root / "skills" / "adjudant" / "reference" / "connect.md").read_text())

    def test_the_reason_list_matches_the_generator(self):
        # EXPECTED_DIVERGENCE must be a reasons map over the generator's set,
        # not a second declaration of it. A file the generator treats as
        # per-build with no reason here, or a reason here for a file the
        # generator copies, is the drift this whole plan removes.
        allowed = ({self.gen.PROFILE_FILE} | set(self.gen.GENERATED)
                   | set(self.gen.AUDIENCE_AUTHORED))
        self.assertEqual(set(EXPECTED_DIVERGENCE), allowed)

    def test_a_regeneration_would_change_nothing(self):
        p = self.gen.plan(MAIN_ROOT, TWIN_ROOT)
        self.assertEqual(p.unexplained, [])
        self.assertEqual(p.create, [])
        self.assertEqual(p.update, [])
        self.assertEqual(p.delete, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 8: Run the parity gate**

Run: `cd adjudant/scripts && python3 -m unittest test_twin_parity -v`
Expected: PASS, 8 tests. A failure here names the exact file: `test_the_twin_holds_nothing_of_its_own` means something must be back-ported, `test_every_shared_file_is_byte_identical` means the twin needs regenerating or the difference needs a reason, and `test_every_named_divergence_is_still_real` means an exemption has gone stale.

Run: `cd adjudant/scripts && ADJUDANT_TWIN=/nonexistent python3 -m unittest test_twin_parity -v 2>&1 | tail -3`
Expected: `OK (skipped=8)`. A clone with only one repo must not fail.

Run: `cd adjudant/scripts && python3 -m unittest discover -p 'test_*.py' 2>&1 | grep -E "^Ran |^OK|^FAILED"`
Expected: `OK`

- [ ] **Step 9: Prove the whole thing is still reversible**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
git -C "$TWIN" stash push -u -m "generated twin" >/dev/null
git -C "$TWIN" ls-files -s adjudant | shasum -a 256
diff <(git -C "$TWIN" ls-files -s adjudant | shasum -a 256) /tmp/twin-before-tree.sha \
  && echo "REVERSIBLE: the pre-generation tree is recoverable"
git -C "$TWIN" stash pop
```

Expected: `REVERSIBLE`, then the generated tree back in the working directory. Only commit after this line prints.

- [ ] **Step 10: Commit, in the twin then in main**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
cd "$TWIN"
git add -A adjudant
git commit -m "feat(adjudant): generated from the marketplace source

Every file under adjudant/ except seven is now byte-identical to the
marketplace copy. The seven are named: the build profile, the four generated
surfaces, and two documents written per audience.

Absent, all named by data rather than by hand: graph.py, test_graph.py and
draw.md (the draw verb, audience full), content-canvas.md, content-mermaid.md
and mermaid-generation-rules.md (its content references), and suitcase.md (a
capability this build does not declare). The generator would delete them if
they appeared, and refuses to delete anything else.

The guided vault setup survives, which is the thing this repo held alone.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

```bash
cd -
git add adjudant/scripts/test_twin_parity.py
git commit -m "test(adjudant): standing parity gate against the generated twin

35 files under adjudant/ used to differ between the trees with nothing in
either repo able to see it. Seven named divergences are allowed, every absence
must trace to a full-only verb, and a stale exemption fails too. Skips cleanly
when the twin is not on this machine.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: The field guide's release boundary

`furtive-follies/field-guide.html` is 1.4 MB and `field-guide.pdf` is 5.7 MB, almost all of it eleven embedded WebP screenshots plus a PNG and an SVG. The guide also bakes the verb list into markup: an `<h4>` reading `The adjudant has seven <span…>verbs</span>` and seven `<div class="verb"><code>…</code>` cards. Regenerating it per change would push megabytes of near-identical binary into git history for a one-word edit, and reshooting the screenshots is manual work. So it is regenerated at a release boundary only — and a checker tells you when that boundary has arrived.

**Files:**
- Create: `$ADJUDANT_TWIN/RELEASING.md`
- Create: `$ADJUDANT_TWIN/scripts/check_field_guide.py`, `$ADJUDANT_TWIN/scripts/test_check_field_guide.py`

**Interfaces:**
- Consumes: the twin's `adjudant/scripts/command-metadata.json`, already audience-filtered by task 9.
- Produces: `check_field_guide.NUMBER_WORDS: tuple[str, ...]`, `baked_verbs(html: str) -> list[str]`, `baked_count_word(html: str) -> Optional[str]`, `shipped_verbs(root: Path) -> list[str]`, `report(root: Path = REPO_ROOT) -> list[str]`, `main(argv: Optional[list[str]] = None) -> int`. Exit 0 when the guide agrees with the verb list, 1 when it does not. Never a pre-commit hook.

- [ ] **Step 1: Write the failing test**

Create `$ADJUDANT_TWIN/scripts/test_check_field_guide.py`:

```python
"""Tests for scripts/check_field_guide.py.

The field guide is 1.4 MB of embedded screenshots and it bakes the verb list
into markup. It is regenerated at a release boundary, never per change, so this
is a reporter and not a gate: it tells you the boundary has arrived.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_field_guide as cfg

REPO = Path(__file__).resolve().parent.parent

SAMPLE = """<h4>The adjudant has seven <span style="color:var(--zt-accent-1)">verbs</span></h4>
<div class="verbs">
  <div class="verb"><code>connect</code><span>Link a project to its vault</span></div>
  <div class="verb"><code>sync</code><span>Push current state to the vault</span></div>
  <div class="verb"><code>board</code><span>Drag-and-drop kanban</span></div>
</div>
"""


class TestParsing(unittest.TestCase):

    def test_reads_the_baked_verb_cards(self):
        self.assertEqual(cfg.baked_verbs(SAMPLE), ["connect", "sync", "board"])

    def test_reads_the_baked_count_word_across_the_span(self):
        # The number and the word "verbs" are separated by a styled span, which
        # is why a plain "seven verbs" search finds nothing.
        self.assertEqual(cfg.baked_count_word(SAMPLE), "seven")

    def test_absent_markup_reports_none_rather_than_raising(self):
        self.assertEqual(cfg.baked_verbs("<p>nothing here</p>"), [])
        self.assertIsNone(cfg.baked_count_word("<p>nothing here</p>"))


class TestReport(unittest.TestCase):

    def test_a_disagreeing_guide_is_reported_line_by_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "adjudant" / "scripts").mkdir(parents=True)
            (root / "adjudant" / "scripts" / "command-metadata.json").write_text(
                '{"name": "adjudant", "version": "1.0.0", "verbs": ['
                '{"name": "connect"}, {"name": "board"}], "content_references": []}\n')
            (root / "field-guide.html").write_text(SAMPLE)
            lines = cfg.report(root)
            self.assertTrue(any("sync" in ln for ln in lines))
            self.assertTrue(any("seven" in ln for ln in lines))

    def test_an_agreeing_guide_reports_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "adjudant" / "scripts").mkdir(parents=True)
            (root / "adjudant" / "scripts" / "command-metadata.json").write_text(
                '{"name": "adjudant", "version": "1.0.0", "verbs": ['
                '{"name": "connect"}, {"name": "sync"}, {"name": "board"}],'
                ' "content_references": []}\n')
            (root / "field-guide.html").write_text(
                SAMPLE.replace("has seven", "has three"))
            self.assertEqual(cfg.report(root), [])

    def test_the_shipped_guide_is_checked_and_the_result_is_reported(self):
        # After task 9 the guide is five verbs behind. The test records that
        # rather than pretending otherwise: it asserts the checker runs and
        # returns a list, not that the list is empty.
        self.assertIsInstance(cfg.report(REPO), list)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd "$ADJUDANT_TWIN/scripts" && python3 -m unittest test_check_field_guide -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'check_field_guide'`

- [ ] **Step 3: Write the checker**

Create `$ADJUDANT_TWIN/scripts/check_field_guide.py`:

```python
#!/usr/bin/env python3
"""Report whether field-guide.html still names the verbs adjudant ships.

The guide is one self-contained page carrying eleven embedded WebP screenshots,
a PNG and an SVG: 1.4 MB of HTML and a 5.7 MB PDF beside it. Regenerating it
for a one-word change would push megabytes of near-identical binary into
history, and the screenshots are shot by hand. So it is regenerated at a
RELEASE BOUNDARY only, and this script is how you learn the boundary arrived.

It is a reporter, never a gate. It is deliberately absent from
.pre-commit-config.yaml and from CI: a red build on every verb change would
train people to skip the hook that also runs the validators.

Usage:
    python3 scripts/check_field_guide.py         # exit 1 when the guide is behind
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

# <div class="verb"><code>connect</code>...
VERB_CARD_RE = re.compile(r'<div class="verb"><code>([a-z-]+)</code>')
# <h4>The adjudant has seven <span ...>verbs</span></h4> — the number and the
# word are separated by a styled span, so a plain "seven verbs" finds nothing.
COUNT_RE = re.compile(r'has\s+([a-z]+)\s*<span[^>]*>\s*verbs\s*</span>', re.I)

NUMBER_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
)


def baked_verbs(html: str) -> list[str]:
    return VERB_CARD_RE.findall(html)


def baked_count_word(html: str) -> Optional[str]:
    m = COUNT_RE.search(html)
    return m.group(1).lower() if m else None


def shipped_verbs(root: Path) -> list[str]:
    meta = json.loads(
        (root / "adjudant" / "scripts" / "command-metadata.json").read_text())
    return [v["name"] for v in meta["verbs"]]


def report(root: Path = REPO_ROOT) -> list[str]:
    """Every disagreement between the guide and the shipped verb list."""
    guide = root / "field-guide.html"
    if not guide.is_file():
        return [f"{guide.name} is missing"]
    html = guide.read_text(errors="replace")
    shipped = shipped_verbs(root)
    baked = baked_verbs(html)
    lines: list[str] = []
    for name in baked:
        if name not in shipped:
            lines.append(f"the guide still shows a `{name}` card; it is not a verb")
    for name in shipped:
        if name not in baked:
            lines.append(f"the guide has no card for `{name}`")
    word = baked_count_word(html)
    expected = NUMBER_WORDS[len(shipped)] if len(shipped) < len(NUMBER_WORDS) else None
    if word is not None and expected is not None and word != expected:
        lines.append(f"the guide says '{word} verbs'; there are {expected}")
    return lines


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="check_field_guide.py",
        description="Report whether the field guide is behind the verb list.")
    ap.add_argument("--root", default=str(REPO_ROOT))
    args = ap.parse_args(argv)
    lines = report(Path(args.root).expanduser().resolve())
    if not lines:
        print("field guide is current")
        return 0
    print("field guide is behind; regenerate it at the next release:")
    for line in lines:
        print(f"  {line}")
    print("\nSee RELEASING.md. Both field-guide.html and field-guide.pdf are "
          "regenerated together, at a release boundary only.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the checker and its tests**

Run: `cd "$ADJUDANT_TWIN/scripts" && python3 -m unittest test_check_field_guide -v`
Expected: PASS, 6 tests.

Run: `cd "$ADJUDANT_TWIN" && python3 scripts/check_field_guide.py`
Expected: exit 1, reporting that the guide has cards for `sync`, `check`, `sitrep` and `tidy` which are no longer verbs, has no cards for `status` and `clean`, and says "seven verbs" where there are five. That is the correct state after task 9: the guide is behind on purpose until the release.

- [ ] **Step 5: Write the release rule down**

Create `$ADJUDANT_TWIN/RELEASING.md`:

```markdown
# Releasing furtive-follies

Two things happen at a release boundary and at no other time.

## 1. Bump the version

```bash
python3 scripts/bump_plugin_version.py adjudant <X.Y.Z>
```

That writes all four lockstep files at once: `adjudant/.claude-plugin/plugin.json`,
`adjudant/scripts/command-metadata.json`, `adjudant/skills/adjudant/SKILL.md`, and
this repo's `.claude-plugin/marketplace.json`. Never edit them by hand; the
`version-consistency` validator fails the commit if they disagree.

## 2. Regenerate the field guide, if it is behind

```bash
python3 scripts/check_field_guide.py
```

Exit 0 means nothing to do. Exit 1 lists what disagrees: a verb card the guide
still shows, a verb it has no card for, or a spelled-out count that is wrong.

`field-guide.html` is 1.4 MB and `field-guide.pdf` is 5.7 MB, nearly all of it
embedded screenshots. **Regenerate both together, at a release boundary only.**
Doing it per change would push megabytes of near-identical binary into history
for a one-word edit, and the screenshots are shot by hand against a staged
vault (`onboarding/SCREENSHOTS.md` is the runbook).

The checker is not a pre-commit hook and not a CI step. It is a reporter you
run when you are already releasing. A gate that goes red on every verb change
trains people to skip the hook that also runs the validators.

## What is NOT part of a release

`adjudant/` is generated from the marketplace repo by
`scripts/generate_twin.py` over there. Do not hand-edit anything under
`adjudant/` here: the next regeneration overwrites it, and the marketplace's
`test_twin_parity` fails until it does. Fix it in the marketplace and
regenerate.
```

- [ ] **Step 6: Confirm the checker is not wired into any gate**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
grep -c "check_field_guide" "$TWIN/.pre-commit-config.yaml" "$TWIN/.github/workflows/validate.yml"
( cd "$TWIN" && pre-commit run --all-files )
```

Expected: `0` from both greps, and both hooks `Passed`. The `Repo-root script tests` CI step does discover `test_check_field_guide.py` and run it, which is correct: the tests are a gate, the checker is not.

- [ ] **Step 7: Commit, in the twin**

```bash
TWIN="${ADJUDANT_TWIN:-$(cd .. && pwd)/furtive-follies}"
cd "$TWIN"
git add RELEASING.md scripts/check_field_guide.py scripts/test_check_field_guide.py
git commit -m "docs: release boundary rules, and a field-guide staleness reporter

field-guide.html is 1.4 MB and the PDF 5.7 MB, almost all embedded screenshots,
and both bake the verb list into markup. Regenerating per change would push
megabytes of near-identical binary into history for a one-word edit.

check_field_guide.py reports when the guide has fallen behind the verb list.
Deliberately not a hook and not a CI step: a gate that goes red on every verb
change trains people to skip the hook that runs the validators.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Done when

- `python3 -m unittest discover -p 'test_*.py'` from `adjudant/scripts/` reports `OK` in **both** repositories, and the two counts differ only by the `draw` tests.
- `python3 adjudant/scripts/validate.py` reports `PASS` in both repositories, with **the same validator count**, because `validate.py` is byte-identical in both.
- `python3 -m unittest discover -p 'test_*.py'` from `scripts/` reports `OK` in both repositories.
- `python3 adjudant/scripts/render_verb_surfaces.py --check` prints `surfaces are current` in both.
- `python3 scripts/generate_twin.py --twin "$ADJUDANT_TWIN"` reports `dry run: 0 change(s) pending`.
- `python3 -m unittest test_twin_parity` passes all eight tests, and passes as eight skips when `ADJUDANT_TWIN` points nowhere.
- `python3 -m unittest test_no_personal_identifiers` passes, so neither tree names a client, a project or a crew member outside `build-profile.json` and `plugin.json`.
- `diff <main>/scripts/bump_plugin_version.py <twin>/scripts/bump_plugin_version.py` is empty.
- `connect.py --suggest-vaults` prints a `vault_roots` array in both trees, and `reference/connect.md` carries the guided-setup section in both.
- `pre-commit run --all-files` passes in the twin, which had no gate at all before this plan.
- Exactly seven files under `adjudant/` differ between the trees, and each has a one-sentence reason in `EXPECTED_DIVERGENCE`.

## Not in this plan

- **Regenerating the field guide.** Task 10 writes the rule and the reporter. The regeneration itself, including reshooting screenshots against a staged vault, belongs to the v3.0.0 release session. The guide is knowingly five verbs behind until then.
- **The twin's branch reconciliation.** `onboarding` is 37 commits ahead of `master` and `origin/HEAD` points at `master`. Task 9 step 1 stops on it rather than deciding it; merging or re-pointing is a call for the repo owner.
- **`internals.md` and `GUIDE.md`.** Both are hand-written per audience and both are named in `EXPECTED_DIVERGENCE`. `internals.md`'s helper table is the obvious next generated surface — it needs one `helper` field per verb in `command-metadata.json` — but the spec named ten surfaces and this plan renders ten.
- **Main's CI Python version.** `.github/workflows/validate.yml` pins 3.12 while the declared floor is 3.9, so main has never tested its own floor. The twin's new workflow pins 3.9. Aligning main is a one-line change with a real chance of surfacing latent failures, and it does not belong inside the irreversible plan.
- **`references/` splitting, the truth checks, dream's rebuild, template-as-schema.** Plans 2 through 4.
- **HubSpot Nightly remediation.** A separate session owns it, per the spec.
