"""Tests for status.py — sync, sitrep, check, kebab --scan and advisor pulse,
merged into one verb that makes derived state current and then reports.

Every behavioural test the five absorbed modules carried is here, moved rather
than rewritten: the fail-closed tests, the traversal and slug-guard tests, the
zone-awareness tests, the byte-identical writer-parity contract with the
PreCompact hook, and the non-UTF-8 safety tests. Only the module under test
and the JSON nesting changed; not one assertion was weakened.
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import status
from status import (
    _board_status,
    _folder_counts,
    _handoff_info,
    _latest_dream_signal,
    _most_recent_dated,
    _next_step,
    _read_brief,
    _repo_brief,
    _server_brief,
    _suitcase_brief,
    _suitcase_status,
    AGENTS_MARKER_PREFIX,
    cli_main as status_cli,
    find_remember_source,
    kebab_violations,
    mirror_handoff,
    refresh_brief_updated,
    refresh_projects_index_row,
    run_sync,
    slugify,
)

# check and sitrep were two halves of one report; status keeps both, under
# the names they now have inside the merged verb.
run_check = status.compliance
run_sitrep = status.orientation

_json = json


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


_write = _w


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


# ============================================================
# Moved from test_sync.py — the make-current phase
# ============================================================


def _connected_setup(tmp: Path, slug: str = "p") -> tuple[Path, Path]:
    """Create a code project + connected vault."""
    proj = tmp / "code"; proj.mkdir()
    vault = tmp / "vault"; vault.mkdir()
    (vault / "Home.md").write_text("---\ntype: vault-home\n---\n")
    (vault / "projects").mkdir()
    (vault / "projects" / slug).mkdir()
    _w(vault / "projects" / slug / "brief.md",
       f"---\ntype: project\nproject_type: coding\nslug: {slug}\nstatus: active\nupdated: 2026-05-01\n---\n\n# Test\n")
    (vault / "projects" / slug / "sessions").mkdir()
    _w(proj / ".claude" / "adjudant",
       f"vault_path: {vault}\nvault_name: vault\nslug: {slug}\nmode: project\n")
    return proj, vault


# ============================================================
# Brief refresh
# ============================================================


class TestRefreshBriefUpdated(unittest.TestCase):

    def test_bumps_existing_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.md"
            brief.write_text("---\nupdated: 2026-05-01\n---\nbody")
            r = refresh_brief_updated(brief, "2026-05-27")
            self.assertEqual(r, "bumped")
            self.assertIn("updated: 2026-05-27", brief.read_text())

    def test_unchanged_when_same(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.md"
            brief.write_text("---\nupdated: 2026-05-27\n---\nbody")
            r = refresh_brief_updated(brief, "2026-05-27")
            self.assertEqual(r, "unchanged")

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(refresh_brief_updated(Path(tmp) / "nope.md", "2026-05-27"), "missing")


# ============================================================
# Handoff mirror
# ============================================================


class TestFindRememberSource(unittest.TestCase):

    def test_prefers_remember_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp)
            _w(proj / ".remember" / "remember.md", "canonical")
            _w(proj / ".remember" / "now.md", "fallback")
            self.assertEqual(find_remember_source(proj).name, "remember.md")

    def test_falls_back_to_now_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp)
            _w(proj / ".remember" / "now.md", "fallback")
            self.assertEqual(find_remember_source(proj).name, "now.md")

    def test_none_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_remember_source(Path(tmp)))


class TestMirrorHandoff(unittest.TestCase):

    def test_creates_handoff_from_remember(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "code"; proj.mkdir()
            _w(proj / ".remember" / "now.md", "current state\n")
            handoff = Path(tmp) / "_handoff.md"
            r = mirror_handoff(proj, handoff, "p", "2026-05-27")
            self.assertEqual(r, "mirrored")
            content = handoff.read_text()
            self.assertIn("type: handoff", content)
            self.assertIn("updated: 2026-05-27", content)
            self.assertIn("current state", content)

    def test_no_source_when_remember_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "code"; proj.mkdir()
            handoff = Path(tmp) / "_handoff.md"
            r = mirror_handoff(proj, handoff, "p", "2026-05-27")
            self.assertEqual(r, "no-source")

    def test_preserves_existing_handoff_frontmatter(self):
        """reference/sync.md: 'preserve handoff frontmatter'. Custom fields and
        the template's extras must survive a re-mirror; only updated: bumps."""
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "code"; proj.mkdir()
            _w(proj / ".remember" / "now.md", "new state\n")
            handoff = Path(tmp) / "_handoff.md"
            handoff.write_text(
                "---\ntype: handoff\nproject: \"[[projects/p/brief|p]]\"\n"
                "created: 2026-01-01\nsource: now\ncodename: falcon\n"
                "updated: 2026-05-01\ntags:\n  - handoff\n---\n\n# old\n\nold body\n"
            )
            r = mirror_handoff(proj, handoff, "p", "2026-05-27")
            self.assertEqual(r, "mirrored")
            content = handoff.read_text()
            self.assertIn("created: 2026-01-01", content)   # custom field survives
            self.assertIn("codename: falcon", content)      # custom field survives
            self.assertIn("updated: 2026-05-27", content)   # bumped
            self.assertNotIn("updated: 2026-05-01", content)
            self.assertIn("new state", content)              # body regenerated

    def test_adds_updated_when_existing_frontmatter_lacks_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "code"; proj.mkdir()
            _w(proj / ".remember" / "now.md", "state\n")
            handoff = Path(tmp) / "_handoff.md"
            handoff.write_text("---\ntype: handoff\n---\n\nbody\n")
            mirror_handoff(proj, handoff, "p", "2026-05-27")
            self.assertIn("updated: 2026-05-27", handoff.read_text())

    def test_includes_freshness_header(self):
        """Parity with the PreCompact hook: the verb writes the freshness block."""
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "code"; proj.mkdir()
            _w(proj / ".remember" / "remember.md", "NEXT: finish the thing\n\nstate body\n")
            handoff = Path(tmp) / "_handoff.md"
            mirror_handoff(proj, handoff, "p", "2026-05-27")
            content = handoff.read_text()
            self.assertIn("handoff age:", content)
            self.assertIn("NEXT: finish the thing", content)
            self.assertIn("state body", content)

    def test_empty_source_never_wipes_existing_handoff(self):
        # Regression: the remember plugin leaves now.md empty at rest after
        # rotation; the mirror overwrote a populated handoff with nothing.
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "code"; proj.mkdir()
            _w(proj / ".remember" / "now.md", "")
            handoff = Path(tmp) / "_handoff.md"
            before = ("---\ntype: handoff\nupdated: 2026-05-01\n---\n\n"
                      "# Handoff: p\n\nprecious context\nNEXT: keep this\n")
            handoff.write_text(before)
            r = mirror_handoff(proj, handoff, "p", "2026-05-27")
            self.assertEqual(r, "source-empty")
            self.assertEqual(handoff.read_text(), before)

    def test_whitespace_source_treated_as_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "code"; proj.mkdir()
            _w(proj / ".remember" / "now.md", "\n   \n\t\n")
            handoff = Path(tmp) / "_handoff.md"
            r = mirror_handoff(proj, handoff, "p", "2026-05-27")
            self.assertEqual(r, "source-empty")
            self.assertFalse(handoff.exists())

    def test_mirror_line_carries_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "code"; proj.mkdir()
            _w(proj / ".remember" / "now.md", "state\n")
            handoff = Path(tmp) / "_handoff.md"
            mirror_handoff(proj, handoff, "p", "2026-05-27",
                           now=datetime(2026, 5, 27, 9, 30))
            self.assertIn("on 2026-05-27 09:30.", handoff.read_text())


class TestWriterParity(unittest.TestCase):
    """sync.mirror_handoff and the PreCompact hook's sync_handoff must emit
    byte-identical handoffs from identical inputs. The two writers drifted
    (heading form, mirror-line time, source: field) and churned the file on
    every alternation."""

    def _fixture(self, root: Path) -> tuple[Path, Path]:
        proj = root / "code"; proj.mkdir(parents=True)
        _w(proj / ".remember" / "now.md", "live state\n\nNEXT: carry on\n")
        _w(proj / ".remember" / "today-2026-06-01.md", "- 13:30 worked\n")
        vault = root / "vault"
        _w(vault / "projects" / "p" / "sessions" / "2026-06-01.md",
           "- 12:00 · Added: [[x]]\n")
        return proj, vault

    def test_sync_and_hook_write_identical_handoffs(self):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks" / "scripts"))
        import precompact as hook
        now = datetime(2026, 6, 1, 14, 0)
        with tempfile.TemporaryDirectory() as tmp:
            root_a = Path(tmp) / "a"
            root_b = Path(tmp) / "b"
            proj_a, vault_a = self._fixture(root_a)
            proj_b, vault_b = self._fixture(root_b)

            handoff_a = vault_a / "projects" / "p" / "_handoff.md"
            r = mirror_handoff(proj_a, handoff_a, "p", "2026-06-01", now=now)
            self.assertEqual(r, "mirrored")

            # sync_handoff takes the RESOLVED project root since the
            # 2026-07-28 zone-awareness fix (main() resolves it via
            # find_project_dir), not the vault root.
            hook.sync_handoff(proj_b, vault_b / "projects" / "p", "p",
                              "2026-06-01", "14:00", now)
            handoff_b = vault_b / "projects" / "p" / "_handoff.md"
            self.assertTrue(handoff_b.is_file())

            self.assertEqual(handoff_a.read_text(), handoff_b.read_text())


# ============================================================
# Projects index row refresh
# ============================================================


class TestRefreshProjectsIndexRow(unittest.TestCase):

    def test_updates_row_with_current_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj, vault = _connected_setup(Path(tmp), "p")
            # Add a session + a decision
            _w(vault / "projects" / "p" / "sessions" / "2026-05-27.md", "---\ntype: session\n---\n")
            (vault / "projects" / "p" / "decisions").mkdir()
            _w(vault / "projects" / "p" / "decisions" / "2026-05-27-x.md", "---\ntype: decision\n---\n")
            r = refresh_projects_index_row(vault, "p")
            self.assertIn(r, ("inserted", "created-index", "updated"))
            text = (vault / "projects" / "_index.md").read_text()
            self.assertIn("p/brief", text)
            self.assertIn("2026-05-27", text)


# ============================================================
# End-to-end run_sync
# ============================================================


class TestRunSyncEndToEnd(unittest.TestCase):

    def test_full_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj, vault = _connected_setup(Path(tmp), "p")
            _w(proj / ".remember" / "now.md", "live state body\n")
            summary = run_sync(proj)
            # All three steps should produce useful outputs
            self.assertEqual(summary["slug"], "p")
            self.assertEqual(summary["steps"]["brief_refresh"], "bumped")
            self.assertEqual(summary["steps"]["handoff_mirror"], "mirrored")
            self.assertIn(summary["steps"]["projects_index_row"], ("inserted", "created-index", "updated"))
            # Handoff actually exists with the body
            handoff_content = (vault / "projects" / "p" / "_handoff.md").read_text()
            self.assertIn("live state body", handoff_content)

    def test_unconnected_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            # No breadcrumb
            with self.assertRaises(RuntimeError):
                run_sync(Path(tmp))


class TestStatusVocabularyGuard(unittest.TestCase):

    def _fixture(self, tmp: str, status: str, zone: str = "") -> Path:
        root = Path(tmp)
        vault = root / "vault"
        proj = vault / "projects" / zone / "p" if zone else vault / "projects" / "p"
        proj.mkdir(parents=True)
        (proj / "brief.md").write_text(
            f"---\ntype: project\nslug: p\nproject_type: coding\nstatus: {status}\n---\n\n# P\n")
        code = root / "code"
        (code / ".claude").mkdir(parents=True)
        (code / ".claude" / "adjudant").write_text(
            f"vault_path: {vault}\nvault_name: vault\nslug: p\nmode: project\n")
        return code

    def test_off_vocabulary_status_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self._fixture(tmp, "paused")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                rc = status_cli(["--project-dir", str(code)])
            self.assertEqual(rc, 0)
            summary = json.loads(buf.getvalue())["synced"]
            self.assertTrue(any("paused" in w for w in summary.get("warnings", [])),
                            summary)

    def test_fridged_project_row_still_refreshes(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self._fixture(tmp, "fridge", zone="_fridge")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                rc = status_cli(["--project-dir", str(code)])
            self.assertEqual(rc, 0)
            summary = json.loads(buf.getvalue())["synced"]
            self.assertNotEqual(summary["steps"]["projects_index_row"], "project-missing")


class TestTraversalSlugBreadcrumb(unittest.TestCase):
    """Verb-level proof for the repo-committed-slug hole. A primitive-only test
    is exactly what let the hole survive the v0.18.0 hardening pass: hooks were
    gated, verbs were not. sync is a WRITE verb reached through
    resolve_project_from_cwd, so it demonstrates the actual damage: before the
    gate it bumped `updated:` inside a brief that lived outside the vault.
    """

    @staticmethod
    def _snapshot(root: Path, skip: Path) -> dict[str, bytes]:
        """Byte-exact census of everything under `root` except the `skip`
        subtree. Any file created, deleted, or rewritten shows up as a diff."""
        out: dict[str, bytes] = {}
        for p in sorted(root.rglob("*")):
            if p == skip or skip in p.parents:
                continue
            out[str(p)] = p.read_bytes() if p.is_file() else b"<dir>"
        return out

    def _fixture(self, root: Path) -> tuple[Path, Path, Path]:
        vault = root / "vault"
        (vault / "projects").mkdir(parents=True)
        (vault / "Home.md").write_text("---\ntype: vault-home\n---\n")
        # `{vault}/projects/../../escaped`, a real project-shaped dir that is
        # a SIBLING of the vault, not inside it.
        escaped = root / "escaped"
        _w(escaped / "brief.md",
           "---\ntype: project\nproject_type: coding\nslug: escaped\n"
           "status: active\nupdated: 2026-01-01\n---\n\n# Not the vault's\n")
        code = root / "code"
        _w(code / ".claude" / "adjudant",
           f"vault_path: {vault}\nvault_name: vault\n"
           f"slug: ../../escaped\nmode: project\n")
        return code, vault, escaped

    def test_sync_writes_nothing_outside_the_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, vault, escaped = self._fixture(root)
            before = self._snapshot(root, skip=vault)

            buf, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                rc = status_cli(["--project-dir", str(code)])

            self.assertNotEqual(rc, 0, "sync accepted a traversal slug")
            self.assertEqual(self._snapshot(root, skip=vault), before,
                             "sync wrote outside the vault")
            self.assertIn("updated: 2026-01-01",
                          (escaped / "brief.md").read_text(),
                          "the out-of-vault brief was rewritten")

    def test_sync_refusal_explains_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _vault, _escaped = self._fixture(Path(tmp))
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(err):
                rc = status_cli(["--project-dir", str(code)])
            self.assertEqual(rc, 1)
            msg = err.getvalue()
            self.assertIn("error:", msg)
            self.assertIn("../../escaped", msg)
            self.assertIn("connect", msg)


class TestNonUtf8BriefSafety(unittest.TestCase):
    """Fix wave 1 finding 3: the strict-decode remediation applied to shelf and
    tidy missed sync, on the SAME file shelf was fixed for.
    refresh_brief_updated read brief.md with errors="replace" and wrote the
    decoded text straight back, so one latin-1 byte became a permanent U+FFFD
    on the next sync.
    """

    _BRIEF = ("---\ntype: project\nslug: p\nproject_type: coding\n"
              "status: active\nupdated: 2026-05-01\n---\n\n# P\n\nCaf")

    def _latin1_brief(self, path: Path) -> bytes:
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = self._BRIEF.encode() + b"\xe9" + " noir\n".encode()
        path.write_bytes(raw)
        return raw

    def test_undecodable_brief_is_left_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.md"
            before = self._latin1_brief(brief)
            result = refresh_brief_updated(brief, "2026-05-27")
            after = brief.read_bytes()
            self.assertNotIn("�".encode(), after,
                             "sync must never bake U+FFFD into a vault brief")
            self.assertEqual(before, after,
                             "an undecodable brief must survive byte-identical")
            self.assertEqual(result, "skipped-undecodable",
                             "the skip must be reported, never silent")

    def test_utf8_brief_still_bumps(self):
        # Guard against over-correction: an ordinary accented brief is valid
        # UTF-8 and must still be rewritten.
        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.md"
            brief.write_text(self._BRIEF + "é noir\n", encoding="utf-8")
            self.assertEqual(refresh_brief_updated(brief, "2026-05-27"), "bumped")
            text = brief.read_text()
            self.assertIn("updated: 2026-05-27", text)
            self.assertIn("Café noir", text)

    def test_full_sync_reports_the_skip_and_preserves_the_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            brief = vault / "projects" / "p" / "brief.md"
            before = self._latin1_brief(brief)
            code = root / "code"
            (code / ".claude").mkdir(parents=True)
            (code / ".claude" / "adjudant").write_text(
                f"vault_path: {vault}\nvault_name: vault\nslug: p\nmode: project\n")
            buf, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                rc = status_cli(["--project-dir", str(code)])
            self.assertEqual(rc, 0)
            summary = json.loads(buf.getvalue())["synced"]
            self.assertEqual(summary["steps"]["brief_refresh"], "skipped-undecodable")
            self.assertEqual(brief.read_bytes(), before,
                             "a whole sync must leave the undecodable brief intact")
            self.assertTrue(
                any("UTF-8" in w for w in summary.get("warnings", [])),
                f"the un-bumped `updated:` field must warn: {summary}")


# ============================================================
# Moved from test_check.py — the compliance half
# ============================================================


class TestReadBrief(unittest.TestCase):

    def test_brief_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md",
                "---\ntype: project\nslug: test\nproject_type: coding\nstatus: active\n---\n\n# Test Project\n\nBody.")
            brief = _read_brief(root)
            self.assertTrue(brief["present"])
            self.assertEqual(brief["slug"], "test")
            self.assertEqual(brief["project_type"], "coding")
            self.assertEqual(brief["status"], "active")
            self.assertEqual(brief["title"], "Test Project")

    def test_brief_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(_read_brief(Path(tmp))["present"])


class TestFolderCounts(unittest.TestCase):

    def test_counts_non_index_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "decisions").mkdir()
            (root / "decisions" / "_index.md").write_text("# idx")
            (root / "decisions" / "2026-05-26-a.md").write_text("a")
            (root / "decisions" / "2026-05-27-b.md").write_text("b")
            counts = _folder_counts(root)
            self.assertEqual(counts["decisions"], 2)

    def test_missing_folder_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            counts = _folder_counts(Path(tmp))
            self.assertEqual(counts, {})


class TestMostRecentDated(unittest.TestCase):

    def test_finds_max(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ["2026-05-26", "2026-05-28", "2026-05-27"]:
                (root / f"{d}.md").write_text("x")
            self.assertEqual(_most_recent_dated(root), "2026-05-28")

    def test_empty_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(_most_recent_dated(Path(tmp)))

    def test_ignores_non_dated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "no-date.md").write_text("x")
            (root / "2026-05-26.md").write_text("y")
            self.assertEqual(_most_recent_dated(root), "2026-05-26")


class TestHandoffInfo(unittest.TestCase):

    def test_handoff_present_with_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "_handoff.md", "---\ntype: handoff\nupdated: 2026-05-25\n---\n\nbody")
            info = _handoff_info(root)
            self.assertTrue(info["present"])
            self.assertEqual(info["updated"], "2026-05-25")
            self.assertIsInstance(info["stale_hours"], float)

    def test_handoff_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(_handoff_info(Path(tmp))["present"])


class TestLatestDreamSignal(unittest.TestCase):

    def test_picks_most_recent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "dreams").mkdir()
            (root / "dreams" / "2026-05-20.md").write_text("# old")
            (root / "dreams" / "2026-05-26.md").write_text("# new\n**90 drift items**")
            sig = _latest_dream_signal(root)
            self.assertEqual(sig["date"], "2026-05-26")
            self.assertEqual(sig["drift_items"], 90)

    def test_no_dreams_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(_latest_dream_signal(Path(tmp))["present"])

    def test_matches_real_dream_report_filename(self):
        # The dream verb writes {YYYY-MM-DD}-dream.md (reference/dream.md §Phase 3);
        # regression: the old regex only accepted bare {YYYY-MM-DD}.md.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "dreams").mkdir()
            (root / "dreams" / "2026-06-30-dream.md").write_text("# report\n**12 drift items**")
            sig = _latest_dream_signal(root)
            self.assertTrue(sig["present"])
            self.assertEqual(sig["date"], "2026-06-30")
            self.assertEqual(sig["drift_items"], 12)


class TestRunCheck(unittest.TestCase):

    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md",
                "---\ntype: project\nslug: test\nproject_type: coding\nstatus: active\n---\n\n# Test\n")
            _write(root / "_handoff.md", "---\ntype: handoff\nupdated: 2026-05-25\n---\nbody")
            (root / "decisions").mkdir()
            (root / "decisions" / "2026-05-26-a.md").write_text("---\ntype: decision\n---\n")
            (root / "sessions").mkdir()
            (root / "sessions" / "2026-05-26.md").write_text("---\ntype: session\n---\n")
            report = run_check(root)
            self.assertEqual(report["project"]["slug"], "test")
            self.assertEqual(report["counts"]["decisions"], 1)
            self.assertEqual(report["recent"]["last_decision"], "2026-05-26")
            self.assertTrue(report["handoff"]["present"])

    def test_status_block_with_suggestion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md",
                "---\ntype: project\nslug: t\nproject_type: coding\nstatus: active\n---\n\n# T\n")
            (root / "sessions").mkdir()
            (root / "sessions" / "2026-01-01.md").write_text("---\ntype: session\n---\n")
            report = run_check(root)
            self.assertEqual(report["status"]["declared"], "active")
            self.assertEqual(report["status"]["suggested"], "stale")
            self.assertIn("zone", report["status"])


class TestBoardStatus(unittest.TestCase):

    def _deck(self, root: Path, cards, columns=None, updated="2026-07-20") -> Path:
        deck = {
            "version": 1,
            "boardId": root.name,
            "title": "T",
            "subtitle": "Work-order board",
            "updated": updated,
            "columns": columns or [
                {"id": "backlog", "name": "Backlog"},
                {"id": "doing", "name": "Doing"},
                {"id": "done", "name": "Done"},
            ],
            "categories": ["build"],
            "cards": cards,
        }
        path = root / "board" / "board-data.json"
        _write(path, _json.dumps(deck))
        return path

    def test_board_absent_present_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(_board_status(root)["present"])
            report = run_check(root)  # no crash; the block is in the report
            self.assertFalse(report["board"]["present"])

    def test_board_present_counts_deck_columns(self):
        # Columns are counted per deck column id (custom lanes included),
        # never per a hardcoded status list; empty lanes still show as 0.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._deck(
                root,
                [
                    {"id": "a", "title": "A", "column": "backlog"},
                    {"id": "b", "title": "B", "column": "doing"},
                    {"id": "c", "title": "C", "column": "doing"},
                    {"id": "d", "title": "D", "column": "shipping"},
                ],
                columns=[
                    {"id": "backlog", "name": "Backlog"},
                    {"id": "doing", "name": "Doing"},
                    {"id": "done", "name": "Done"},
                    {"id": "shipping", "name": "Shipping"},
                ],
            )
            board = _board_status(root)
            self.assertTrue(board["present"])
            self.assertEqual(
                board["columns"],
                {"backlog": 1, "doing": 2, "done": 0, "shipping": 1})
            self.assertEqual(board["updated"], "2026-07-20")
            self.assertFalse(board["stale"])

    def test_board_stale_when_task_newer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck_path = self._deck(root, [{"id": "a", "title": "A", "column": "backlog"}])
            task = root / "tasks" / "fix-the-thing.md"
            _write(task, "---\ntype: task\nstatus: todo\n---\n\n# Fix the thing\n")
            base = deck_path.stat().st_mtime
            os.utime(deck_path, (base, base))
            os.utime(task, (base + 60, base + 60))
            self.assertTrue(_board_status(root)["stale"])

    def test_board_fresh_when_deck_newer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck_path = self._deck(root, [{"id": "a", "title": "A", "column": "backlog"}])
            task = root / "tasks" / "fix-the-thing.md"
            _write(task, "---\ntype: task\nstatus: todo\n---\n\n# Fix the thing\n")
            base = deck_path.stat().st_mtime
            os.utime(deck_path, (base, base))
            os.utime(task, (base - 60, base - 60))
            self.assertFalse(_board_status(root)["stale"])

    def test_board_unreadable_deck_present_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "board" / "board-data.json", "{not json")
            self.assertFalse(_board_status(root)["present"])


class TestCheckCost(unittest.TestCase):

    def _project(self, root: Path) -> None:
        _write(root / "brief.md",
            "---\ntype: project\nslug: t\nproject_type: coding\nstatus: active\n---\n\n# T\n")
        _write(root / "notes" / "a.md", "x" * 4000)

    def test_estimate_only_prints_cost_block_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = status_cli(["--project-dir", str(root), "--estimate-only"])
            self.assertEqual(rc, 0)
            payload = _json.loads(buf.getvalue())
            self.assertEqual(set(payload), {"cost"})
            self.assertEqual(
                set(payload["cost"]),
                {"est_read_tokens", "files", "bytes", "threshold", "warn"})
            self.assertEqual(payload["cost"]["files"], 2)

    def test_normal_run_includes_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = status_cli(["--project-dir", str(root), "--no-sync"])
            self.assertEqual(rc, 0)
            payload = _json.loads(buf.getvalue())
            self.assertIn("cost", payload)
            # check's whole report is the `compliance` half of status's.
            self.assertIn("compliance", payload)
            self.assertTrue(payload["compliance"]["project"]["present"])


class TestSuitcaseStatus(unittest.TestCase):
    """PATH-probe awareness of the suitcase environment; never executes it."""

    def test_present_when_cli_on_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "suitcase-brief"
            fake.write_text("#!/bin/sh\nexit 0\n")
            fake.chmod(0o755)
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{tmp}:{old_path}"
            try:
                self.assertTrue(_suitcase_status()["present"])
            finally:
                os.environ["PATH"] = old_path

    def test_absent_when_cli_missing(self):
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = "/usr/bin:/bin"
        try:
            self.assertFalse(_suitcase_status()["present"])
        finally:
            os.environ["PATH"] = old_path


_CLEAN_BRIEF = (
    "---\ntype: project\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
    "verified: 2026-01-01\nverified_by: read\n---\n\n# T\n")
_CLEAN_DECISION = (
    "---\ntype: decision\nstatus: active\ncreated: 2026-07-27\n"
    "updated: 2026-07-27\n---\n\nD\n")


class TestSchemaSection(unittest.TestCase):

    def test_clean_project_zero_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", _CLEAN_BRIEF)
            _write(root / "decisions" / "2026-07-27-a.md", _CLEAN_DECISION)
            report = run_check(root)
            self.assertIn("schema", report)
            self.assertEqual(report["schema"]["flagged"], 0)
            self.assertEqual(report["schema"]["checked"], 2)

    def test_drift_counted_with_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", _CLEAN_BRIEF)
            _write(root / "notes" / "n.md",
                   "---\ntype: note\nproject: \"[[projects/t/brief|t]]\"\n"
                   "created: 2026-01-01\nupdated: 2026-01-01\n---\nN\n")
            _write(root / "decisions" / "2026-07-27-a.md",
                   _CLEAN_DECISION.replace("status: active", "status: accepted"))
            report = run_check(root)
            self.assertEqual(report["schema"]["flagged"], 2)
            self.assertEqual(report["schema"]["counts"]["unknown_fields"], 1)
            self.assertEqual(report["schema"]["counts"]["status_invalid"], 1)
            files = [s["file"] for s in report["schema"]["samples"]]
            self.assertIn("notes/n.md", files)

    def test_report_json_serializable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", _CLEAN_BRIEF)
            report = run_check(root)
            _json.dumps(report)


class TestRememberSection(unittest.TestCase):
    """The handoff's source is a dependency, and check declares it. When
    `.remember/` was missing or empty adjudant mirrored nothing and said
    nothing, so the handoff read as a banner with no body."""

    def test_absent_remember_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", _CLEAN_BRIEF)
            report = run_check(root)
            self.assertIn("remember", report)
            self.assertFalse(report["remember"]["present"])

    def test_probe_reads_the_code_root_not_the_vault_project(self):
        # `.remember/` lives beside the code, never in the vault.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault_project = root / "vault" / "projects" / "t"
            code = root / "code"
            _write(vault_project / "brief.md", _CLEAN_BRIEF)
            _write(code / ".remember" / "remember.md", "## State\nwork\n")
            report = run_check(vault_project, code_root=code)
            self.assertTrue(report["remember"]["present"])
            self.assertFalse(report["remember"]["empty"])

    def test_present_but_empty_is_distinguished_from_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault_project = root / "vault" / "projects" / "t"
            code = root / "code"
            _write(vault_project / "brief.md", _CLEAN_BRIEF)
            _write(code / ".remember" / "remember.md", "\n  \n")
            report = run_check(vault_project, code_root=code)
            self.assertTrue(report["remember"]["present"])
            self.assertTrue(report["remember"]["empty"])


# ============================================================
# Moved from test_sitrep.py — the orientation half
# ============================================================


class TestNextStep(unittest.TestCase):

    def test_next_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "_handoff.md", "---\nupdated: 2026-07-02\n---\n\nNEXT: wire up the sitrep verb\n")
            self.assertEqual(_next_step(root), "wire up the sitrep verb")

    def test_next_absent_when_no_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(_next_step(Path(tmp)))

    def test_next_none_when_no_next_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "_handoff.md", "---\nupdated: 2026-07-02\n---\n\nJust some prose, no marker.\n")
            self.assertIsNone(_next_step(root))


class TestRunSitrep(unittest.TestCase):

    def _project(self, root: Path) -> None:
        _write(root / "brief.md",
               "---\ntype: project\nslug: demo\nproject_type: coding\nstatus: active\n---\n\n# Demo Project\n\nBody.")
        _write(root / "_handoff.md", "---\nupdated: 2026-07-02\n---\n\nNEXT: ship v0.10.0\n")
        _write(root / "sessions" / "2026-07-01.md", "# session\n")
        _write(root / "decisions" / "2026-06-30-pick-approach.md", "# decision\n")
        _write(root / "notes" / "idea.md", "# note\n")

    def test_populated_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            _write(root / ".remember" / "today-2026-07-02.md", "- 09:00 · started work\n- 10:30 · wrote code\n")
            now = datetime(2026, 7, 2, 11, 0)  # 30m after last activity
            rep = run_sitrep(root, vault_path=Path("/vault/demo"), now=now)

            self.assertEqual(rep["purpose"], "Demo Project")
            self.assertEqual(rep["vault_path"], "/vault/demo")
            self.assertEqual(rep["next_step"], "ship v0.10.0")
            self.assertEqual(rep["whats_done"]["last_session"], "2026-07-01")
            self.assertEqual(rep["whats_done"]["last_decision"], "2026-06-30")
            self.assertEqual(rep["whats_done"]["counts"]["notes"], 1)
            self.assertEqual(rep["whats_done"]["total_files"], 3)  # session+decision+note
            # 30 minutes → green light
            self.assertEqual(rep["freshness"]["light"], "\U0001f7e2")
            self.assertEqual(rep["freshness"]["age"], "30m")

    def test_stale_activity_turns_light_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            _write(root / ".remember" / "today-2026-07-01.md", "- 09:00 · old work\n")
            now = datetime(2026, 7, 2, 18, 0)  # >8h later
            rep = run_sitrep(root, now=now)
            self.assertEqual(rep["freshness"]["light"], "\U0001f534")  # red

    def test_missing_handoff_yields_null_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", "---\ntype: project\nslug: demo\n---\n\n# Demo\n")
            now = datetime(2026, 7, 2, 12, 0)
            rep = run_sitrep(root, now=now)
            self.assertIsNone(rep["next_step"])

    def test_breadcrumb_flow_reads_remember_from_code_root(self):
        # In the real flow the vault project dir and the code root are DIFFERENT
        # directories: .remember/ lives at the code root only. Freshness must
        # come from there, not from the vault dir (regression: always-⚪ bug).
        with tempfile.TemporaryDirectory() as tmp:
            vault_proj = Path(tmp) / "vault" / "projects" / "demo"
            code_root = Path(tmp) / "code"
            self._project(vault_proj)
            _write(code_root / ".remember" / "today-2026-07-02.md", "- 10:30 · wrote code\n")
            now = datetime(2026, 7, 2, 11, 0)
            rep = run_sitrep(vault_proj, now=now, code_root=code_root)
            self.assertEqual(rep["freshness"]["light"], "\U0001f7e2")
            self.assertEqual(rep["freshness"]["age"], "30m")

    def test_status_block_with_suggestion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md",
                "---\ntype: project\nslug: t\nproject_type: coding\nstatus: active\n---\n\n# T\n")
            (root / "sessions").mkdir()
            (root / "sessions" / "2026-01-01.md").write_text("---\ntype: session\n---\n")
            now = datetime(2026, 7, 2, 12, 0)
            rep = run_sitrep(root, now=now)
            self.assertEqual(rep["status"]["declared"], "active")
            self.assertEqual(rep["status"]["suggested"], "stale")
            self.assertIn("zone", rep["status"])

    def test_empty_project_no_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            now = datetime(2026, 7, 2, 12, 0)
            rep = run_sitrep(root, now=now)
            self.assertFalse(rep["project"]["present"])
            self.assertIsNone(rep["purpose"])
            self.assertIsNone(rep["were_doing"])
            self.assertEqual(rep["freshness"]["light"], "⚪")  # white — age unknown
            self.assertEqual(rep["whats_done"]["counts"], {})


class TestSitrepBoard(unittest.TestCase):

    def _deck(self, root: Path, cards) -> Path:
        deck = {
            "version": 1,
            "boardId": root.name,
            "title": "T",
            "subtitle": "Work-order board",
            "updated": "2026-07-20",
            "columns": [
                {"id": "backlog", "name": "Backlog"},
                {"id": "next", "name": "Next"},
                {"id": "doing", "name": "Doing"},
                {"id": "review", "name": "Review"},
                {"id": "done", "name": "Done"},
                {"id": "icebox", "name": "Icebox"},
            ],
            "categories": ["build"],
            "cards": cards,
        }
        path = root / "board" / "board-data.json"
        _write(path, _json.dumps(deck))
        return path

    def test_board_line_rendered(self):
        # open = every column except done and icebox; doing = the doing column.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", "---\ntype: project\nslug: demo\n---\n\n# Demo\n")
            self._deck(root, [
                {"id": "a", "title": "A", "column": "backlog"},
                {"id": "b", "title": "B", "column": "doing"},
                {"id": "c", "title": "C", "column": "done"},
                {"id": "d", "title": "D", "column": "icebox"},
            ])
            rep = run_sitrep(root, now=datetime(2026, 7, 21, 12, 0))
            self.assertTrue(rep["board"]["present"])
            self.assertEqual(rep["board"]["open"], 2)
            self.assertEqual(rep["board"]["doing"], 1)
            self.assertEqual(rep["board"]["line"], "Board: 2 open (1 in motion)")

    def test_board_line_stale_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", "---\ntype: project\nslug: demo\n---\n\n# Demo\n")
            deck_path = self._deck(root, [{"id": "a", "title": "A", "column": "doing"}])
            task = root / "tasks" / "a.md"
            _write(task, "---\ntype: task\nstatus: doing\n---\n\n# A\n")
            base = deck_path.stat().st_mtime
            os.utime(deck_path, (base, base))
            os.utime(task, (base + 60, base + 60))
            rep = run_sitrep(root, now=datetime(2026, 7, 21, 12, 0))
            self.assertEqual(rep["board"]["line"], "Board: 1 open (1 in motion), stale")

    def test_board_absent_no_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", "---\ntype: project\nslug: demo\n---\n\n# Demo\n")
            rep = run_sitrep(root, now=datetime(2026, 7, 21, 12, 0))
            self.assertFalse(rep["board"]["present"])
            self.assertNotIn("line", rep["board"])


class TestSitrepCost(unittest.TestCase):

    def test_estimate_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "brief.md").write_text(
                "---\ntype: project\nslug: t\nproject_type: coding\nstatus: active\n---\n\n# T\n")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = status_cli(["--project-dir", str(root), "--estimate-only"])
            self.assertEqual(rc, 0)
            payload = _json.loads(buf.getvalue())
            self.assertEqual(set(payload), {"cost"})

    def test_normal_run_includes_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "brief.md").write_text(
                "---\ntype: project\nslug: t\nproject_type: coding\nstatus: active\n---\n\n# T\n")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = status_cli(["--project-dir", str(root), "--no-sync"])
            self.assertEqual(rc, 0)
            payload = _json.loads(buf.getvalue())
            self.assertIn("cost", payload)
            # sitrep's whole report is the `orientation` half of status's.
            self.assertIn("orientation", payload)


class TestSuitcaseBrief(unittest.TestCase):
    """Suitcase line rendered only when the CLI is on PATH; probe only."""

    def test_line_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "suitcase-brief"
            fake.write_text("#!/bin/sh\nexit 0\n")
            fake.chmod(0o755)
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{tmp}:{old_path}"
            try:
                sc = _suitcase_brief()
                self.assertTrue(sc["present"])
                self.assertIn("suitcase-brief", sc["line"])
            finally:
                os.environ["PATH"] = old_path

    def test_no_line_when_absent(self):
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = "/usr/bin:/bin"
        try:
            sc = _suitcase_brief()
            self.assertFalse(sc["present"])
            self.assertIsNone(sc["line"])
        finally:
            os.environ["PATH"] = old_path


if __name__ == "__main__":
    unittest.main()


class TestRepoBrief(unittest.TestCase):
    """Git state must degrade to {present: False}, never raise — orientation
    that can crash is worse than orientation that says 'unknown'."""

    def test_absent_without_code_root(self):
        self.assertFalse(_repo_brief(None)["present"])

    def test_absent_when_not_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(_repo_brief(Path(tmp))["present"])

    def test_reads_a_real_repo(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
            run = lambda *a: subprocess.run(["git", "-C", str(root), *a],
                                            capture_output=True, env=env)
            run("init", "-q", "-b", "main")
            _write(root / "a.txt", "one\n")
            run("add", "-A"); run("commit", "-qm", "first commit")
            info = _repo_brief(root)
            self.assertTrue(info["present"])
            self.assertEqual(info["branch"], "main")
            self.assertFalse(info["detached"])
            self.assertEqual(info["dirty"], 0)
            self.assertEqual(info["head"]["subject"], "first commit")
            self.assertEqual(len(info["recent"]), 1)
            # an untracked file counts as dirty
            _write(root / "b.txt", "two\n")
            self.assertEqual(_repo_brief(root)["dirty"], 1)


class TestServerBrief(unittest.TestCase):
    """launch.json drives the probe; a down server is an answer, not an error."""

    def test_absent_without_code_root(self):
        self.assertFalse(_server_brief(None)["present"])

    def test_absent_without_launch_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(_server_brief(Path(tmp))["present"])

    def test_unreadable_launch_json_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / ".claude" / "launch.json", "{not json")
            out = _server_brief(root)
            self.assertFalse(out["present"])

    def test_down_server_reports_false_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # port 1 is reserved and never listening
            _write(root / ".claude" / "launch.json",
                   '{"configurations":[{"name":"x","port":1}]}')
            out = _server_brief(root)
            self.assertTrue(out["present"])
            self.assertEqual(len(out["servers"]), 1)
            self.assertFalse(out["servers"][0]["up"])

    def test_entries_without_a_port_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / ".claude" / "launch.json",
                   '{"configurations":[{"name":"noport"},{"name":"bad","port":"5184"}]}')
            self.assertFalse(_server_brief(root)["present"])



# ============================================================
# Moved from test_kebab.py — the §4 naming scan
# ============================================================


class TestSlugify(unittest.TestCase):

    def test_the_obvious_case(self):
        self.assertEqual(slugify("Fix the parser rewrite"), "fix-the-parser-rewrite")

    def test_punctuation_and_runs_collapse(self):
        self.assertEqual(slugify("Auth: OAuth *and* PAT!!"), "auth-oauth-and-pat")

    def test_leading_and_trailing_separators_go(self):
        self.assertEqual(slugify("  --Hello, world--  "), "hello-world")

    def test_already_kebab_is_unchanged(self):
        self.assertEqual(slugify("already-kebab-case"), "already-kebab-case")

    def test_nothing_survivable_is_empty(self):
        self.assertEqual(slugify("???"), "")

    def test_agrees_with_the_board_bridge(self):
        # One slug rule in the plugin, or a captured task and a hand-named
        # note disagree about what the same title is called.
        from board_bridge import kebab as bridge_kebab
        for s in ("Fix the parser", "Auth: OAuth *and* PAT!!", "  spaced  out  "):
            self.assertEqual(slugify(s), bridge_kebab(s))


class TestScan(unittest.TestCase):

    def _project(self, root: Path) -> None:
        _w(root / "brief.md",
           "---\ntype: project\nproject_type: coding\nslug: demo\n"
           "tags:\n  - project\n---\n\n# Demo\n")

    def test_flags_a_non_kebab_note_and_suggests_the_fix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            _w(root / "notes" / "My Great Note.md",
               "---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
               "tags:\n  - note\n---\n\nn\n")
            out = kebab_violations(root)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["suggested"], "my-great-note.md")

    def test_a_clean_note_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            _w(root / "notes" / "clean-name.md",
               "---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
               "tags:\n  - note\n---\n\nn\n")
            self.assertEqual(kebab_violations(root), [])

    def test_decision_keeps_its_date_and_only_the_title_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            _w(root / "decisions" / "2026-01-01-Auth Strategy.md",
               "---\ntype: decision\nstatus: active\ndate: 2026-01-01\n"
               "tags:\n  - decision\n---\n\nd\n")
            out = kebab_violations(root)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["suggested"], "2026-01-01-auth-strategy.md")

    def test_docs_are_exempt_because_section_four_wants_them_uppercase(self):
        # The one rule that would fight §4 if kebab applied it blindly.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            _w(root / "docs" / "ARCHITECTURE.md",
               "---\ntype: doc\ntitle: A\nupdated: 2026-01-01\n"
               "tags:\n  - doc\n---\n\nd\n")
            self.assertEqual(kebab_violations(root), [])

    def test_system_files_and_sessions_are_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            _w(root / "_handoff.md", "---\ntype: handoff\nupdated: 2026-01-01\n---\n\nh\n")
            _w(root / "notes" / "_index.md",
               "---\ntype: index\ntags:\n  - index\n---\n\n# Notes\n")
            _w(root / "sessions" / "2026-01-01.md",
               "---\ntype: session\ndate: 2026-01-01\nstarted: 09:00\n"
               "session_id: []\ntags:\n  - session\n---\n\ns\n")
            self.assertEqual(kebab_violations(root), [])

    def test_a_release_note_keeps_its_version_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            _w(root / "releases" / "v1.2.0.md",
               "---\ntype: release\nversion: 1.2.0\ndate: 2026-01-01\n"
               "tags:\n  - release\n---\n\nr\n")
            self.assertEqual(kebab_violations(root), [])


class TestCLI(unittest.TestCase):

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = status_cli(["--slug", *argv])
        return rc, out.getvalue(), err.getvalue()

    def _scan(self, root: Path) -> tuple[int, dict]:
        """`kebab --scan` is now the read-only report's `naming` band."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = status_cli(["--project-dir", str(root), "--no-sync"])
        return rc, json.loads(out.getvalue())

    def test_slugifies_its_arguments(self):
        rc, out, _ = self._run("Fix", "the", "parser")
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "fix-the-parser")

    def test_slugifies_one_quoted_argument(self):
        _, out, _ = self._run("Fix the parser")
        self.assertEqual(out.strip(), "fix-the-parser")

    def test_unslugifiable_input_fails_plainly(self):
        rc, _, err = self._run("???")
        self.assertEqual(rc, 1)
        self.assertIn("nothing", err.lower())

    def test_scan_emits_json_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _w(root / "brief.md",
               "---\ntype: project\nproject_type: coding\nslug: demo\n"
               "tags:\n  - project\n---\n\n# Demo\n")
            _w(root / "notes" / "Bad Name.md",
               "---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
               "tags:\n  - note\n---\n\nn\n")
            before = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
            rc, payload = self._scan(root)
            self.assertEqual(rc, 0)
            self.assertEqual(len(payload["naming"]), 1)
            self.assertEqual(payload["naming"][0]["suggested"], "bad-name.md")
            # and the finding reaches the band a human reads
            self.assertTrue(any(f.get("signal") == "naming"
                                for f in payload["worth_a_look"]))
            for p, m in before.items():
                self.assertEqual(p.stat().st_mtime_ns, m)

    def test_scan_of_a_tidy_project_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _w(root / "brief.md",
               "---\ntype: project\nproject_type: coding\nslug: demo\n"
               "tags:\n  - project\n---\n\n# Demo\n")
            _, payload = self._scan(root)
            self.assertEqual(payload["naming"], [])


# ============================================================
# Moved from test_advisor.py — the advisor's state and pulse
# ============================================================


class _Harness(unittest.TestCase):

    def _project(self, tmp: Path, *, agents: bool = True) -> Path:
        project = tmp / "code"
        (project / ".claude").mkdir(parents=True)
        (project / ".claude" / "adjudant").write_text(
            "vault_path: /tmp/nowhere\nvault_name: v\nslug: demo\nmode: project\n")
        if agents:
            (project / "AGENTS.md").write_text(
                "# Repository Guidelines\n\nSome existing context.\n")
        return project

    def _run(self, project: Path, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = status_cli(["--advisor", *argv, "--project-dir", str(project)])
        return rc, out.getvalue(), err.getvalue()

    def _crumb(self, project: Path) -> str:
        return (project / ".claude" / "adjudant").read_text()

    def _agents(self, project: Path) -> str:
        return (project / "AGENTS.md").read_text()


class TestToggle(_Harness):

    def test_on_sets_the_knob_and_stamps_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            rc, out, _ = self._run(project, "on")
            self.assertEqual(rc, 0)
            self.assertIn("advisor: on", self._crumb(project))
            self.assertIn(AGENTS_MARKER_PREFIX, self._agents(project))
            self.assertIn("on", out)

    def test_on_preserves_every_other_breadcrumb_line(self):
        # The breadcrumb is repo-committed and hand-readable; a toggle that
        # rewrites it wholesale would eat comments and unknown keys.
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            before = self._crumb(project)
            self._run(project, "on")
            after = self._crumb(project)
            for line in before.strip().splitlines():
                self.assertIn(line, after)

    def test_on_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            self._run(project, "on")
            once_crumb, once_agents = self._crumb(project), self._agents(project)
            self._run(project, "on")
            self.assertEqual(self._crumb(project), once_crumb)
            self.assertEqual(self._agents(project), once_agents)

    def test_off_flips_the_knob_and_removes_the_marker(self):
        # Off means gone: a lingering marker would keep telling every session
        # the advisor is watching when it is not.
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            self._run(project, "on")
            rc, _, _ = self._run(project, "off")
            self.assertEqual(rc, 0)
            self.assertIn("advisor: off", self._crumb(project))
            self.assertNotIn("advisor: on", self._crumb(project))
            self.assertNotIn(AGENTS_MARKER_PREFIX, self._agents(project))

    def test_off_leaves_the_rest_of_agents_md_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            before = self._agents(project)
            self._run(project, "on")
            self._run(project, "off")
            self.assertEqual(self._agents(project), before)

    def test_status_reports_the_current_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp))
            _, out_before, _ = self._run(project, "status")
            self.assertIn("off", out_before)
            self._run(project, "on")
            _, out_after, _ = self._run(project, "status")
            self.assertIn("on", out_after)

    def test_missing_agents_md_still_sets_the_knob(self):
        # AGENTS.md is connect's job; its absence degrades the marker, never
        # the toggle.
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(Path(tmp), agents=False)
            rc, _, err = self._run(project, "on")
            self.assertEqual(rc, 0)
            self.assertIn("advisor: on", self._crumb(project))
            self.assertIn("AGENTS.md", err)  # says what it could not stamp

    def test_unlinked_project_fails_plainly(self):
        with tempfile.TemporaryDirectory() as tmp:
            bare = Path(tmp) / "bare"
            bare.mkdir()
            rc, _, err = self._run(bare, "on")
            self.assertEqual(rc, 1)
            self.assertIn("connect", err)


class TestPulse(_Harness):
    """`pulse` answers one question, read-only: does the working context
    still hold? It composes sensors that already exist (freshness_report,
    the handoff NEXT, dream's dangling-scope detector) and adds a `quiet`
    verdict, because the advisor's contract is silence when nothing is
    flagged - a pulse that always finds something to say trains the user
    to skip it."""

    def _vault_project(self, tmp: Path) -> Path:
        proj = tmp / "vaultproj"
        (proj / "sessions").mkdir(parents=True)
        (proj / "brief.md").write_text(
            "---\ntype: project\nproject_type: coding\nslug: demo\n"
            "aliases:\n  - Demo\nstatus: active\ncreated: 2026-01-01\n"
            "updated: 2026-08-01\ntags:\n  - project\n---\n\n# Demo\n\n"
            "## INTRO\nx\n\n## TECHNICAL STACK\ny\n\n## CONSTRAINTS\nz\n\n"
            "## WORK NOTES\nw\n\n## MILESTONES\n- ship the parser rewrite\n")
        (proj / "sessions" / "2026-08-01.md").write_text(
            "---\ntype: session\ndate: 2026-08-01\nstarted: 09:00\n"
            "session_id: []\ntags:\n  - session\n---\n\n- worked\n")
        return proj

    def _pulse(self, proj: Path) -> tuple[int, dict]:
        import json
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = status_cli(["--project-dir", str(proj), "--no-sync",
                             "--today", "2026-08-13"])
        text = out.getvalue()
        report = json.loads(text) if text.strip() else {}
        return rc, (report.get("advisor", {}).get("pulse") or {})

    def test_untouched_milestone_is_a_dangling_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._vault_project(Path(tmp))
            rc, report = self._pulse(proj)
            self.assertEqual(rc, 0)
            self.assertTrue(any("parser" in str(d).lower()
                                for d in report["dangling_scopes"]))

    def test_handoff_next_is_carried(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._vault_project(Path(tmp))
            (proj / "_handoff.md").write_text(
                "---\ntype: handoff\nupdated: 2026-08-12\n---\n\n"
                "**NEXT:** wire the pulse into resume\n")
            _, report = self._pulse(proj)
            self.assertIn("pulse", (report["next_step"] or ""))

    def test_recent_decisions_capped_at_five(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._vault_project(Path(tmp))
            (proj / "decisions").mkdir()
            for i in range(1, 8):
                (proj / "decisions" / f"2026-07-{i:02d}-d{i}.md").write_text(
                    f"---\ntype: decision\nstatus: active\ndate: 2026-07-{i:02d}\n"
                    f"tags:\n  - decision\n---\n\nDecision {i}.\n")
            _, report = self._pulse(proj)
            self.assertEqual(len(report["recent_decisions"]), 5)
            # newest first: the pulse is about NOW
            self.assertIn("2026-07-07", report["recent_decisions"][0]["file"])

    def test_a_healthy_project_pulses_quiet(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._vault_project(Path(tmp))
            # touch the milestone in a session so nothing dangles
            (proj / "sessions" / "2026-08-02.md").write_text(
                "---\ntype: session\ndate: 2026-08-02\nstarted: 09:00\n"
                "session_id: []\ntags:\n  - session\n---\n\n"
                "- started the parser rewrite, shipping soon\n")
            rc, report = self._pulse(proj)
            self.assertEqual(rc, 0)
            self.assertTrue(report["quiet"])

    def test_pulse_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._vault_project(Path(tmp))
            before = sorted(p.relative_to(proj).as_posix()
                            for p in proj.rglob("*") if p.is_file())
            mtimes = {p: p.stat().st_mtime_ns for p in proj.rglob("*") if p.is_file()}
            self._pulse(proj)
            after = sorted(p.relative_to(proj).as_posix()
                           for p in proj.rglob("*") if p.is_file())
            self.assertEqual(before, after)
            for p, m in mtimes.items():
                self.assertEqual(p.stat().st_mtime_ns, m)


class TestCaptureTask(_Harness):
    """`capture-task` is the approved-suggestion landing path: one note
    through the existing rail (templates/task.md -> tasks/ -> the board
    seeds the card). Nothing advisor-specific touches disk; the advisor
    only standardizes the write it was already allowed to make."""

    def _vault_project(self, tmp: Path) -> Path:
        proj = tmp / "vaultproj"
        proj.mkdir(parents=True)
        (proj / "brief.md").write_text(
            "---\ntype: project\nproject_type: coding\nslug: demo\n"
            "aliases:\n  - Demo\nstatus: active\ncreated: 2026-01-01\n"
            "updated: 2026-08-01\ntags:\n  - project\n---\n\n# Demo\n")
        return proj

    def _capture(self, proj: Path, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = status_cli(["--capture-task", "--project-dir", str(proj), *argv])
        return rc, out.getvalue(), err.getvalue()

    def test_capture_writes_a_schema_legal_note_and_seeds_the_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._vault_project(Path(tmp))
            rc, out, err = self._capture(proj, "--title", "Fix the parser rewrite")
            self.assertEqual(rc, 0, err)
            note = proj / "tasks" / "fix-the-parser-rewrite.md"
            self.assertTrue(note.is_file())
            text = note.read_text()
            self.assertIn("type: task", text)
            self.assertIn("status: backlog", text)
            deck = proj / "board" / "board-data.json"
            self.assertTrue(deck.is_file(), "the board should seed the card")
            import json
            ids = [c["id"] for c in json.loads(deck.read_text())["cards"]]
            self.assertIn("fix-the-parser-rewrite", ids)

    def test_note_body_carries_the_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._vault_project(Path(tmp))
            self._capture(proj, "--title", "Close the auth loop",
                          "--note", "Third session touching auth without a decision note.")
            text = (proj / "tasks" / "close-the-auth-loop.md").read_text()
            self.assertIn("Third session touching auth", text)

    def test_capture_is_deduped_by_slug(self):
        # The advisor's raise-once rule, enforced at the disk layer too: a
        # re-capture must not clobber a note someone has since edited.
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._vault_project(Path(tmp))
            self._capture(proj, "--title", "Fix the parser")
            note = proj / "tasks" / "fix-the-parser.md"
            note.write_text(note.read_text() + "\nhand-added line\n")
            rc, out, _ = self._capture(proj, "--title", "Fix the parser")
            self.assertEqual(rc, 0)
            self.assertIn("exists", out.lower())
            self.assertIn("hand-added line", note.read_text())

    def test_a_title_that_kebabs_to_nothing_fails_plainly(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._vault_project(Path(tmp))
            rc, _, err = self._capture(proj, "--title", "???")
            self.assertEqual(rc, 1)
            self.assertIn("title", err.lower())


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


if __name__ == "__main__":
    unittest.main()
