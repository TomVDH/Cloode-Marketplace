"""Tests for scripts/generate_twin.py — the one irreversible step in v3.

The twin held code that existed nowhere else, so the failure this file exists
to prevent is a regeneration that quietly drops something and reports success.
Three rules carry that: the back-port guard must pass before anything is
planned, the public tree must name nobody, and every deletion must trace back
to data (a full-only verb, a full-only content reference, or a capability this
build declares). Anything else stops the run.
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


class TestLeakGate(unittest.TestCase):
    """The twin is public. A published name cannot be taken back, so the
    generator refuses rather than reporting the leak afterwards."""

    def test_a_personal_identifier_stops_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_main = _copy_main(Path(tmp) / "main")
            (fake_main / "adjudant" / "scripts" / "_fixture.py").write_text(
                'DEMO_SLUG = "hubspot-nightly"\n')
            twin = _copy_main(Path(tmp) / "twin")
            rc = generate_twin.main(["--main-root", str(fake_main),
                                     "--twin", str(twin), "--apply"])
            self.assertEqual(rc, 2)
            self.assertFalse(
                (twin / "adjudant" / "scripts" / "_fixture.py").exists(),
                "a client name was copied into the public tree")
            self.assertTrue((twin / "adjudant" / "scripts" / "graph.py").is_file(),
                            "the refused run deleted something anyway")

    def test_the_real_tree_passes_the_gate(self):
        self.assertEqual(generate_twin.leaking_identifiers(MAIN_ROOT / "adjudant"), [])


class TestPlan(unittest.TestCase):

    def test_a_regenerated_twin_plans_nothing(self):
        # The plan asked for "an identical tree plans nothing". Two identical
        # copies of main are not a correct twin: the copy carries main's seven
        # full-only files, which plan() names for deletion and its sibling test
        # below asserts. Idempotence is the promise that actually holds — and
        # the one the generator's own docstring makes.
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            generate_twin.main(["--main-root", str(main_root),
                                "--twin", str(twin), "--apply"])
            p = generate_twin.plan(main_root, twin)
            self.assertEqual(p.create, [])
            self.assertEqual(p.update, [])
            self.assertEqual(p.delete, [])
            self.assertEqual(p.unexplained, [])
            rc = generate_twin.main(["--main-root", str(main_root),
                                     "--twin", str(twin)])
            self.assertEqual(rc, 0, "a second run still reported work pending")

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
            (twin / "adjudant" / "scripts" / "clean.py").write_text("# stale\n")
            rc = generate_twin.main(["--main-root", str(main_root), "--twin", str(twin)])
            self.assertEqual(rc, 1, "a dry run with work pending should say so")
            self.assertTrue(target.is_file(), "dry run deleted a file")
            self.assertEqual(
                (twin / "adjudant" / "scripts" / "clean.py").read_text(), "# stale\n")

    def test_apply_copies_the_shared_tree_and_prunes_the_named(self):
        # The plan used tidy.py here. Plans 1-4 deleted it; clean.py is the
        # shared file that replaced it.
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            (twin / "adjudant" / "scripts" / "clean.py").write_text("# stale\n")
            rc = generate_twin.main(["--main-root", str(main_root),
                                     "--twin", str(twin), "--apply"])
            self.assertEqual(rc, 0)
            self.assertEqual(
                (twin / "adjudant" / "scripts" / "clean.py").read_text(),
                (main_root / "adjudant" / "scripts" / "clean.py").read_text())
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

    def test_an_audience_authored_file_keeps_the_twins_text(self):
        # GUIDE.md and reference/internals.md are written per audience and
        # nothing regenerates them, so overwriting one loses prose that exists
        # in no other tree.
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            guide = twin / "adjudant" / "GUIDE.md"
            internals = (twin / "adjudant" / "skills" / "adjudant"
                         / "reference" / "internals.md")
            guide.write_text("# the public build's own guide\n")
            internals.write_text("# the public build's own internals\n")
            generate_twin.main(["--main-root", str(main_root),
                                "--twin", str(twin), "--apply"])
            self.assertEqual(guide.read_text(), "# the public build's own guide\n")
            self.assertEqual(internals.read_text(),
                             "# the public build's own internals\n")

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
