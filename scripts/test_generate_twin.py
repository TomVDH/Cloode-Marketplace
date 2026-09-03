"""Tests for scripts/generate_twin.py — the one irreversible step in v3.

The twin held code that existed nowhere else, so the failure this file exists
to prevent is a regeneration that quietly drops something and reports success.
Three rules carry that: the back-port guard must pass before anything is
planned, the public tree must name nobody, and every deletion must trace back
to data (a full-only verb, a full-only content reference, or a capability this
build declares). Anything else stops the run.
"""

import json
import re
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


def _make_public(twin: Path) -> None:
    """Turn a copy of main into a plausible public twin: its own profile."""
    (twin / "adjudant" / "scripts" / "build-profile.json").write_text(json.dumps({
        "audience": "public",
        "description_suffix": "",
        "cost_warn_tokens": 10000,
        "capabilities": [],
    }, indent=2) + "\n")


class TestGeneratedSurfaces(unittest.TestCase):
    """The four surfaces the generator renders rather than copies.

    The real twin's SKILL.md was pre-v3: it routed to sync.md, check.md,
    sitrep.md and tidy.md. Those four docs and their four helpers are deleted
    by this same run, so a regeneration that leaves the twin's own SKILL.md
    alone ships a router pointing at nothing. It reports success; a reader
    finds it.
    """

    def _stale_skill(self, twin: Path) -> None:
        (twin / "adjudant" / "skills" / "adjudant" / "SKILL.md").write_text(
            "---\nname: adjudant\ndescription: pre-v3\n"
            'argument-hint: "[connect|sync|check|sitrep|tidy|dream|board] [args]"\n'
            "---\n\n# Adjudant\n\n"
            "| Verb | Loads | Purpose |\n|---|---|---|\n"
            "| `sync` | `reference/sync.md` | push state |\n"
            "| `tidy` | `reference/tidy.md` | surface sweep |\n")
        (twin / "adjudant" / "README.md").write_text(
            "# adjudant\n\n## The seven verbs\n\n"
            "| Verb | Args |\n|---|---|\n| `tidy` | |\n")

    def test_a_stale_skill_is_regenerated_not_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            _make_public(twin)
            self._stale_skill(twin)
            rc = generate_twin.main(["--main-root", str(main_root),
                                     "--twin", str(twin), "--apply"])
            self.assertEqual(rc, 0)
            skill = (twin / "adjudant" / "skills" / "adjudant" / "SKILL.md").read_text()
            for gone in ("reference/sync.md", "reference/check.md",
                         "reference/sitrep.md", "reference/tidy.md"):
                self.assertNotIn(gone, skill,
                                 f"the twin's router still points at {gone}")

    def test_every_reference_the_router_names_exists_in_the_twin(self):
        # The outcome a reader gets: follow any row of the router and land on
        # a file. This is the assertion the crash-free run has to earn.
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            _make_public(twin)
            self._stale_skill(twin)
            generate_twin.main(["--main-root", str(main_root),
                                "--twin", str(twin), "--apply"])
            skill_dir = twin / "adjudant" / "skills" / "adjudant"
            named = re.findall(r"`(reference/[A-Za-z0-9._-]+\.md)`",
                               (skill_dir / "SKILL.md").read_text())
            self.assertTrue(named, "the router named no reference files at all")
            missing = sorted({r for r in named if not (skill_dir / r).is_file()})
            self.assertEqual(missing, [],
                             f"SKILL.md routes to files the twin does not have: {missing}")

    def test_the_readme_names_only_verbs_the_twin_ships(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            _make_public(twin)
            self._stale_skill(twin)
            generate_twin.main(["--main-root", str(main_root),
                                "--twin", str(twin), "--apply"])
            readme = (twin / "adjudant" / "README.md").read_text()
            self.assertNotIn("`tidy`", readme)
            self.assertNotIn("`draw`", readme, "draw is a full-only verb")
            self.assertIn("`connect`", readme)

    def test_a_render_failure_is_reported_not_a_traceback(self):
        # The half-generated tree: copies land, the render raises, and the
        # operator is left with a twin that is neither old nor new.
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            (twin / "adjudant" / "scripts" / "build-profile.json").write_text("{ not json")
            rc = generate_twin.main(["--main-root", str(main_root),
                                     "--twin", str(twin), "--apply"])
            self.assertEqual(rc, 2)


class TestRetirements(unittest.TestCase):
    """A twin left behind by a retirement is the third kind of difference.

    The plan knew two: a file is audience-gated, or it must be back-ported.
    The real twin carried a third — 21 files belonging to verbs and templates
    that no build ships any more. They cannot be back-ported (nothing wants
    them) and they belong to no verb (the verbs are gone), so the generator
    refused, correctly, and the regeneration could not start.

    RETIRED names each one with the reason. It is a deletion licence, so it is
    held to the same standard as the rest: named per path, never a pattern,
    and it may never cover a file this tree still ships.
    """

    def test_a_retired_path_is_a_named_deletion_not_unexplained(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            # The shape the real twin was in: a retired verb's module.
            (twin / "adjudant" / "scripts" / "tidy.py").write_text("# pre-v3\n")
            p = generate_twin.plan(main_root, twin)
            self.assertIn("scripts/tidy.py", p.delete)
            self.assertEqual(p.unexplained, [])

    def test_a_retirement_never_shadows_a_file_this_tree_ships(self):
        # The way a tombstone list turns dangerous: someone revives a name,
        # and the generator silently deletes the twin's copy of live code.
        # This is the assertion that makes the licence safe to keep.
        shipped = sorted(rel for rel in generate_twin.RETIRED
                         if (MAIN_ROOT / "adjudant" / rel).exists())
        self.assertEqual(shipped, [],
                         "these are listed as retired but this tree ships them; "
                         "take them off RETIRED before the generator deletes "
                         "the twin's copy")

    def test_every_retirement_carries_a_reason(self):
        unexplained = sorted(rel for rel, why in generate_twin.RETIRED.items()
                             if not (why or "").strip())
        self.assertEqual(unexplained, [])

    def test_a_retirement_is_not_a_licence_for_its_neighbours(self):
        # Deleting scripts/tidy.py must not make scripts/ deletable.
        with tempfile.TemporaryDirectory() as tmp:
            main_root = _copy_main(Path(tmp) / "main")
            twin = _copy_main(Path(tmp) / "twin")
            (twin / "adjudant" / "scripts" / "tidy.py").write_text("# pre-v3\n")
            stray = twin / "adjudant" / "scripts" / "tidy_helper.py"
            stray.write_text("# not retired, not shared\n")
            p = generate_twin.plan(main_root, twin)
            self.assertIn("scripts/tidy.py", p.delete)
            self.assertEqual(p.unexplained, ["scripts/tidy_helper.py"])
            self.assertNotIn("scripts/tidy_helper.py", p.delete)


class TestPlanProfile(unittest.TestCase):

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
