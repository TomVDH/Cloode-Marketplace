"""The two trees ship the same adjudant, and every difference is named.

Before this regeneration the twin was a hand-maintained fork: 141 files under
`adjudant/` differed between the trees — 21 the twin had alone, 56 this tree
had alone, and 64 present in both with different bytes — and nothing in either
repo could see it. The differences are a list of seven now, and this file is
what keeps it seven.

It lives in the marketplace's own `scripts/`, beside the generator it checks,
and NOT in `adjudant/scripts/`. That matters: everything under `adjudant/` is
copied into the twin, where `TWIN_ROOT` would resolve to the twin itself and
`generate_twin` would not import at all. A gate that compares the twin to
itself passes for the wrong reason, which is worse than no gate.

It skips when the twin is not on this machine, so it never fails a clone that
has only one repo. Point it at a twin with ADJUDANT_TWIN.
"""

import filecmp
import os
import subprocess
import sys
import unittest
from pathlib import Path

MAIN_ROOT = Path(__file__).resolve().parent.parent
MAIN_PLUGIN = MAIN_ROOT / "adjudant"
TWIN_ROOT = Path(os.environ.get("ADJUDANT_TWIN")
                 or MAIN_ROOT.parent / "furtive-follies")

sys.path.insert(0, str(MAIN_ROOT / "scripts"))
sys.path.insert(0, str(MAIN_PLUGIN / "scripts"))

# Files that may differ, each with the reason it may.
EXPECTED_DIVERGENCE = {
    "scripts/build-profile.json":
        "the one file a build may differ in: audience, threshold, capabilities",
    "scripts/command-metadata.json":
        "generated: the public build ships the audience-filtered verb list, and its own version",
    "skills/adjudant/SKILL.md":
        "generated: description, argument-hint, router, weights and content refs follow the verb list; the version is the repository's",
    "README.md":
        "generated: the verb table follows the verb list, and the install line names this repository's marketplace",
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
        # The 2026-09-01 disaster shape: suggest_vault_roots lived only there.
        extra = sorted(self.theirs - self.ours)
        self.assertEqual(extra, [], f"files only in the twin: {extra}")

    def test_every_absence_is_a_named_full_only_path(self):
        # Asked of the generator rather than recomputed here. Two reasons: the
        # gate then checks the set that actually licenses deletions instead of
        # a second copy of it, and _deletable repoints the profile at the tree
        # being asked about — this process may already hold a _profile loaded
        # from somewhere else entirely.
        deletable = self.gen._deletable(MAIN_PLUGIN)
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

    def test_no_retired_path_came_back(self):
        # RETIRED is a standing deletion licence. It stays safe only while the
        # paths on it are absent from both trees: a name that comes back in
        # this tree would have the twin's copy deleted on the next run.
        alive = sorted(rel for rel in self.gen.RETIRED
                       if rel in self.ours or rel in self.theirs)
        self.assertEqual(alive, [],
                         f"listed as retired but present in a tree: {alive}")

    def test_the_twin_passes_its_own_test_suite(self):
        # The one assertion that reads the outcome rather than the shape. Six
        # tests failed the first time the twin ran the shared suite, and every
        # structural check above was green while they did: each spelled out a
        # fact the build profile decides, so it could only pass in the tree it
        # was written in. Nothing but running the other build finds that.
        out = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-p", "test_*.py"],
            cwd=self.twin_plugin / "scripts", capture_output=True, text=True)
        self.assertEqual(out.returncode, 0,
                         "the twin's own suite fails:\n"
                         + "\n".join(l for l in out.stderr.splitlines()
                                     if l.startswith(("FAIL:", "ERROR:"))))

    def test_the_twin_passes_its_own_validators(self):
        out = subprocess.run(
            [sys.executable, "adjudant/scripts/validate.py"],
            cwd=TWIN_ROOT, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0,
                         "the twin's own validators fail:\n"
                         + "\n".join(l for l in out.stdout.splitlines()
                                     if "✗" in l))


if __name__ == "__main__":
    unittest.main()
