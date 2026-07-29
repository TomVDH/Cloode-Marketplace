"""Tests for adjudant/scripts/shelf.py."""

import contextlib
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from shelf import cli_main as shelf_cli, run_list


def _mk_project(vault: Path, slug: str, zone: str = "", status: str = "active",
                sessions: list = ()) -> Path:
    pdir = vault / "projects" / zone / slug if zone else vault / "projects" / slug
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "brief.md").write_text(
        f"---\ntype: project\nslug: {slug}\nproject_type: coding\nstatus: {status}\n"
        f"created: 2026-01-01\nupdated: 2026-01-01\ntags:\n  - project\n---\n\n# {slug}\n")
    if sessions:
        (pdir / "sessions").mkdir(exist_ok=True)
        for d in sessions:
            (pdir / "sessions" / f"{d}.md").write_text("---\ntype: session\n---\n")
    return pdir


class TestRunList(unittest.TestCase):

    def test_lists_all_zones_with_suggestions(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "hot", sessions=["2026-07-15"])
            _mk_project(vault, "quiet", sessions=["2026-03-01"])
            _mk_project(vault, "cold", zone="_fridge", status="fridge")
            _mk_project(vault, "shipped", zone="_archive", status="done")
            out = run_list(vault, stale_days=30, today=date(2026, 7, 16))
            rows = {r["slug"]: r for r in out["projects"]}
            self.assertEqual(set(rows), {"hot", "quiet", "cold", "shipped"})
            self.assertIsNone(rows["hot"]["suggested"])
            self.assertEqual(rows["quiet"]["suggested"], "stale")
            self.assertEqual(rows["cold"]["zone"], "_fridge")
            self.assertTrue(rows["cold"]["zone_matches"])
            self.assertTrue(rows["shipped"]["zone_matches"])

    def test_zone_mismatch_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "misfiled", status="dead")  # dead but in living zone
            out = run_list(vault, stale_days=30, today=date(2026, 7, 16))
            self.assertFalse(out["projects"][0]["zone_matches"])


class TestListCli(unittest.TestCase):

    def test_cli_list_via_vault_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "p", sessions=["2026-07-10"])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = shelf_cli(["list", "--vault-dir", str(vault),
                                "--today", "2026-07-16"])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["projects"][0]["slug"], "p")
            self.assertEqual(payload["stale_after_days"], 30)


from shelf import (
    append_status_log,
    apply_transition,
    plan_transition,
    set_brief_status,
    write_preview,
)


class TestBriefEdits(unittest.TestCase):

    BRIEF = ("---\ntype: project\nslug: p\nproject_type: coding\nstatus: active\n"
             "created: 2026-01-01\nupdated: 2026-01-01\ntags:\n  - project\n---\n\n# P\n")

    def test_set_brief_status_rewrites_frontmatter_only(self):
        text = self.BRIEF + "\nBody mentions status: active in prose.\n"
        out = set_brief_status(text, "fridge", "2026-07-16")
        self.assertIn("status: fridge", out)
        self.assertIn("updated: 2026-07-16", out)
        self.assertIn("Body mentions status: active in prose.", out)
        self.assertEqual(out.count("status: fridge"), 1)

    def test_append_status_log_creates_section(self):
        out = append_status_log(self.BRIEF, "active", "fridge", "2026-07-16", "summer break")
        self.assertIn("## Status log", out)
        self.assertIn("- 2026-07-16: active → fridge (summer break)", out)

    def test_append_status_log_prepends_to_existing_section(self):
        first = append_status_log(self.BRIEF, "active", "fridge", "2026-07-01", None)
        second = append_status_log(first, "fridge", "active", "2026-07-16", None)
        self.assertEqual(second.count("## Status log"), 1)
        idx_new = second.index("2026-07-16: fridge → active")
        idx_old = second.index("2026-07-01: active → fridge")
        self.assertLess(idx_new, idx_old)


class TestTransition(unittest.TestCase):

    def _vault(self, tmp: str) -> Path:
        vault = Path(tmp)
        _mk_project(vault, "p", sessions=["2026-07-01"])
        other = vault / "projects" / "other"
        other.mkdir(parents=True)
        (other / "brief.md").write_text(
            "---\ntype: project\nslug: other\nproject_type: coding\nstatus: active\n---\n\n"
            "# Other\n\nSee [[projects/p/brief|p]] and [[projects/p/notes/idea]].\n")
        return vault

    def test_plan_counts_link_rewrites_and_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(tmp)
            plan = plan_transition(vault, "p", "fridge", "pause", "2026-07-16")
            self.assertTrue(plan["move_required"])
            self.assertEqual(plan["to_dir"], "projects/_fridge/p")
            files = {r["file"]: r["count"] for r in plan["link_rewrites"]}
            self.assertEqual(files.get("projects/other/brief.md"), 2)

    def test_plan_rejects_bad_state_and_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(tmp)
            with self.assertRaises(ValueError):
                plan_transition(vault, "p", "paused", None, "2026-07-16")
            with self.assertRaises(ValueError):
                plan_transition(vault, "ghost", "fridge", None, "2026-07-16")

    def test_same_zone_transition_needs_no_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(tmp)
            plan = plan_transition(vault, "p", "stale", None, "2026-07-16")
            self.assertFalse(plan["move_required"])
            self.assertEqual(plan["link_rewrites"], [])

    def test_apply_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(tmp)
            plan = plan_transition(vault, "p", "fridge", "pause", "2026-07-16")
            write_preview(vault, plan)
            result = apply_transition(vault, plan)
            new_dir = vault / "projects" / "_fridge" / "p"
            self.assertTrue(new_dir.is_dir())
            self.assertFalse((vault / "projects" / "p").exists())
            brief = (new_dir / "brief.md").read_text()
            self.assertIn("status: fridge", brief)
            self.assertIn("- 2026-07-16: active → fridge (pause)", brief)
            other = (vault / "projects" / "other" / "brief.md").read_text()
            self.assertIn("[[projects/_fridge/p/brief|p]]", other)
            self.assertIn("[[projects/_fridge/p/notes/idea]]", other)
            idx = (vault / "projects" / "_index.md").read_text()
            self.assertIn("| fridge |", idx)
            backups = list((vault / ".adjudant-shelf-backup").iterdir())
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / "manifest.json").is_file())
            self.assertTrue((backups[0] / "projects" / "other" / "brief.md").is_file())
            self.assertFalse((vault / ".adjudant-shelf-preview").exists())
            self.assertEqual(result["moved"], True)

    def test_apply_refuses_existing_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(tmp)
            (vault / "projects" / "_fridge" / "p").mkdir(parents=True)
            plan = plan_transition(vault, "p", "fridge", None, "2026-07-16")
            with self.assertRaises(RuntimeError):
                apply_transition(vault, plan)
            # original untouched
            self.assertTrue((vault / "projects" / "p" / "brief.md").is_file())

    def test_apply_rolls_back_on_midflight_failure(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            vault = self._vault(tmp)
            before = (vault / "projects" / "other" / "brief.md").read_text()
            plan = plan_transition(vault, "p", "fridge", None, "2026-07-16")
            with mock.patch("shelf.shutil.move", side_effect=OSError("disk says no")):
                with self.assertRaises(RuntimeError):
                    apply_transition(vault, plan)
            # link rewrites reverted, folder never moved, brief untouched
            self.assertEqual(
                (vault / "projects" / "other" / "brief.md").read_text(), before)
            self.assertTrue((vault / "projects" / "p" / "brief.md").is_file())
            self.assertFalse((vault / "projects" / "_fridge" / "p").exists())


class TestTransitionCli(unittest.TestCase):

    def test_apply_without_preview_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "p")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                rc = shelf_cli(["apply", "--vault-dir", str(vault),
                                "--slug", "p", "--to", "fridge"])
            self.assertEqual(rc, 1)

    def test_preview_then_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "p")
            for phase in ("preview", "apply"):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = shelf_cli([phase, "--vault-dir", str(vault),
                                    "--slug", "p", "--to", "done",
                                    "--today", "2026-07-16"])
                self.assertEqual(rc, 0)
            self.assertTrue((vault / "projects" / "_archive" / "p" / "brief.md").is_file())


class TestNonUtf8Safety(unittest.TestCase):
    """Audit 2026-07-27 finding 9: apply_transition read with errors='replace'
    and wrote the replaced text BACK, so one undecodable byte became a
    permanent U+FFFD. tidy avoids this exact round-trip on purpose."""

    def _vault_with_latin1_link(self, tmp: str) -> tuple[Path, Path]:
        vault = Path(tmp)
        _mk_project(vault, "p", sessions=["2026-07-01"])
        other = vault / "projects" / "other"
        other.mkdir(parents=True)
        # A note that BOTH carries the link prefix (so shelf wants to rewrite
        # it) and holds a latin-1 byte that is not valid UTF-8.
        (other / "brief.md").write_bytes(
            "---\ntype: project\nslug: other\nproject_type: coding\nstatus: active\n---\n\n"
            "# Other\n\nSee [[projects/p/brief|p]].\n\nCaf".encode()
            + b"\xe9" + " noir\n".encode())
        return vault, other / "brief.md"

    def test_undecodable_file_is_not_corrupted(self):
        from shelf import apply_transition, plan_transition
        with tempfile.TemporaryDirectory() as tmp:
            vault, note = self._vault_with_latin1_link(tmp)
            before = note.read_bytes()
            plan = plan_transition(vault, "p", "fridge", "pause", "2026-07-16")
            apply_transition(vault, plan)
            after = note.read_bytes()
            self.assertNotIn("�".encode(), after,
                             "shelf must never bake U+FFFD into a vault file")
            self.assertEqual(before, after,
                             "an undecodable file must be left byte-identical")

    def test_transition_still_completes_and_reports(self):
        from shelf import apply_transition, plan_transition
        with tempfile.TemporaryDirectory() as tmp:
            vault, _ = self._vault_with_latin1_link(tmp)
            plan = plan_transition(vault, "p", "fridge", "pause", "2026-07-16")
            result = apply_transition(vault, plan)
            self.assertTrue((vault / "projects" / "_fridge" / "p").is_dir(),
                            "the move must still happen")
            self.assertIn("skipped_undecodable", result)
            self.assertIn("projects/other/brief.md", result["skipped_undecodable"])

    def test_utf8_links_still_rewritten(self):
        from shelf import apply_transition, plan_transition
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "p", sessions=["2026-07-01"])
            other = vault / "projects" / "other"
            other.mkdir(parents=True)
            (other / "brief.md").write_text(
                "---\ntype: project\nslug: other\nproject_type: coding\nstatus: active\n---\n\n"
                "# Other\n\nSee [[projects/p/brief|p]].\n")
            plan = plan_transition(vault, "p", "fridge", "pause", "2026-07-16")
            apply_transition(vault, plan)
            self.assertIn("[[projects/_fridge/p/brief|p]]", (other / "brief.md").read_text())


class TestUndecodableBrief(unittest.TestCase):
    """Fix wave 1 finding 1: step 4 read the brief with a STRICT
    `brief.read_text()`. UnicodeDecodeError subclasses ValueError, so it was
    caught by NEITHER the rollback handler (OSError, RuntimeError) NOR
    cli_main's handler: the traceback escaped past the safety net, leaving the
    folder MOVED to _fridge with the brief still declaring `status: active`,
    no index row, and the preview never cleared. Every retry died identically.
    """

    def _vault_with_undecodable_brief(self, tmp: str) -> tuple[Path, Path]:
        vault = Path(tmp)
        pdir = vault / "projects" / "p"
        (pdir / "sessions").mkdir(parents=True)
        (pdir / "sessions" / "2026-07-01.md").write_text("---\ntype: session\n---\n")
        (pdir / "brief.md").write_bytes(
            "---\ntype: project\nslug: p\nproject_type: coding\nstatus: active\n"
            "created: 2026-01-01\nupdated: 2026-01-01\ntags:\n  - project\n---\n\n"
            "# p\n\nCaf".encode() + b"\xe9" + " noir\n".encode())
        return vault, pdir / "brief.md"

    def test_undecodable_brief_leaves_no_half_moved_project(self):
        from shelf import apply_transition, plan_transition
        with tempfile.TemporaryDirectory() as tmp:
            vault, brief = self._vault_with_undecodable_brief(tmp)
            before = brief.read_bytes()
            plan = plan_transition(vault, "p", "fridge", "pause", "2026-07-16")
            # Reported as a rolled-back failure, never a raw UnicodeDecodeError.
            with self.assertRaises(RuntimeError) as ctx:
                apply_transition(vault, plan)
            self.assertNotIsInstance(ctx.exception, UnicodeDecodeError)
            self.assertIn("brief.md", str(ctx.exception))
            self.assertTrue(
                (vault / "projects" / "p" / "brief.md").is_file(),
                "rollback must return the project to its original zone")
            self.assertFalse(
                (vault / "projects" / "_fridge" / "p").exists(),
                "a half-moved project is the exact corruption being prevented")
            self.assertEqual(before, brief.read_bytes(),
                             "the brief must be restored byte-identical")
            self.assertFalse(
                (vault / "projects" / "_index.md").is_file(),
                "no index row may claim a transition that was rolled back")

    def test_cli_apply_reports_undecodable_brief_and_keeps_the_preview(self):
        from shelf import PREVIEW_DIR
        with tempfile.TemporaryDirectory() as tmp:
            vault, _ = self._vault_with_undecodable_brief(tmp)
            buf, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = shelf_cli(["preview", "--vault-dir", str(vault),
                                "--slug", "p", "--to", "fridge",
                                "--today", "2026-07-16"])
            self.assertEqual(rc, 0)
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                rc = shelf_cli(["apply", "--vault-dir", str(vault),
                                "--slug", "p", "--to", "fridge",
                                "--today", "2026-07-16"])
            self.assertEqual(rc, 1, "an undecodable brief must be a clean failure")
            self.assertIn("brief", err.getvalue().lower())
            self.assertTrue((vault / PREVIEW_DIR / "changes.json").is_file(),
                            "an aborted apply must leave the preview to retry")
            self.assertFalse((vault / "projects" / "_fridge" / "p").exists())


if __name__ == "__main__":
    unittest.main()
