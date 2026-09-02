"""Tests for advisor.py — the v2 advisor's toggle (and later, its pulse).

The advisor is opt-in, and the opt-in is deliberately VISIBLE twice over:
`advisor: on` in the breadcrumb (machine-read by SessionStart, syncs across
machines) and a marker line in AGENTS.md (read into every session's context by
the harness itself, and by any human opening the repo). The toggle owns both
surfaces so they cannot drift apart.
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from advisor import AGENTS_MARKER_PREFIX, cli_main as advisor_cli


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
            rc = advisor_cli([*argv, "--project-dir", str(project)])
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
            rc = advisor_cli(["pulse", "--project-dir", str(proj),
                              "--today", "2026-08-13"])
        text = out.getvalue()
        return rc, (json.loads(text) if text.strip() else {})

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
            rc = advisor_cli(["capture-task", "--project-dir", str(proj), *argv])
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


if __name__ == "__main__":
    unittest.main()
