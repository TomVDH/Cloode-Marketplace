"""Tests for hooks/scripts/posttooluse-vault-log.py — the PostToolUse hook.

Coverage focus: stdin payload parsing must fail closed (malformed JSON, missing
file_path, non-Write tools, out-of-project paths); the session-log entry must
keep its `- HH:MM · Label: [[link]]` shape with the Decision/Added split; new
files must get `source_session:` stamped from the payload's session_id; and
the stamp skip rules (session notes, _handoff, _index*, _iteration) must hold
through the hook, not just in the primitive.
"""

import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "posttooluse-vault-log.py"

# Hyphenated filename — importlib, not a bare import. Exec runs the hook's own
# sys.path bootstrap, so _session_stamp/_vault_walk come from the real scripts/.
_spec = importlib.util.spec_from_file_location("posttooluse_vault_log", HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

SESSION_ID = "sess-abc123"
FRONTMATTER = "---\ntype: note\ncreated: 2026-01-01\n---\n\nbody\n"


class _HookHarness(unittest.TestCase):
    """Shared fixture + in-process runner. OB_VAULT from the developer's shell
    must never leak in — resolve_vault consults it as step 1."""

    def setUp(self):
        self._ob_vault = os.environ.pop("OB_VAULT", None)

    def tearDown(self):
        if self._ob_vault is not None:
            os.environ["OB_VAULT"] = self._ob_vault

    def _fixture(self, tmp: Path) -> tuple[Path, Path, Path]:
        """Project + vault + today's session note. Returns (project,
        project_root_in_vault, session_note)."""
        project = tmp / "code"
        vault = tmp / "vault"
        proot = vault / "projects" / "demo"
        (proot / "sessions").mkdir(parents=True)
        (project / ".claude").mkdir(parents=True)
        (project / ".claude" / "adjudant").write_text(
            f"vault_path: {vault}\nvault_name: vault\nslug: demo\nmode: project\n")
        today = datetime.now().strftime("%Y-%m-%d")
        session = proot / "sessions" / f"{today}.md"
        session.write_text("## Log\n")
        return project, proot, session

    def _note(self, proot: Path, rel: str, content: str = FRONTMATTER) -> Path:
        """Materialize the file the Write tool just produced — PostToolUse
        fires after the write, so the target exists when the hook runs."""
        p = proot / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def _payload(self, path: Path, *, tool: str = "Write",
                 session_id: str = SESSION_ID) -> dict:
        return {"tool_name": tool,
                "tool_input": {"file_path": str(path)},
                "session_id": session_id}

    def _run(self, project: Path, payload) -> int:
        """Run hook.main() in-process with `payload` (dict or raw str) on stdin."""
        os.environ["CLAUDE_PROJECT_DIR"] = str(project)
        stdin_before = sys.stdin
        sys.stdin = io.StringIO(
            payload if isinstance(payload, str) else json.dumps(payload))
        try:
            return hook.main()
        finally:
            sys.stdin = stdin_before
            del os.environ["CLAUDE_PROJECT_DIR"]


class TestPayloadParsing(_HookHarness):

    def test_malformed_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            rc = self._run(project, "not json {{{")
            self.assertEqual(rc, 0)
            self.assertEqual(session.read_text(), "## Log\n")

    def test_missing_file_path_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            rc = self._run(project, {"tool_name": "Write", "tool_input": {},
                                     "session_id": SESSION_ID})
            self.assertEqual(rc, 0)
            self.assertEqual(session.read_text(), "## Log\n")

    def test_path_key_fallback_accepted(self):
        # Some Write payloads carry `path` instead of `file_path`.
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            note = self._note(proot, "notes/idea.md")
            rc = self._run(project, {"tool_name": "Write",
                                     "tool_input": {"path": str(note)},
                                     "session_id": SESSION_ID})
            self.assertEqual(rc, 0)
            self.assertIn("[[projects/demo/notes/idea.md]]", session.read_text())

    def test_edit_tool_is_ignored(self):
        # Edit modifies existing files — logging it would double-count.
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            note = self._note(proot, "notes/idea.md")
            rc = self._run(project, self._payload(note, tool="Edit"))
            self.assertEqual(rc, 0)
            self.assertEqual(session.read_text(), "## Log\n")
            self.assertNotIn("source_session", note.read_text())

    def test_write_outside_project_root_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            other = proot.parent / "other" / "notes" / "x.md"
            other.parent.mkdir(parents=True)
            other.write_text(FRONTMATTER)
            rc = self._run(project, self._payload(other))
            self.assertEqual(rc, 0)
            self.assertEqual(session.read_text(), "## Log\n")
            self.assertNotIn("source_session", other.read_text())

    def test_stale_vault_fails_closed(self):
        # Cross-machine breadcrumb pointing nowhere: no log, no phantom dirs.
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "code"
            phantom = Path(tmp) / "gone" / "vault"
            (project / ".claude").mkdir(parents=True)
            (project / ".claude" / "adjudant").write_text(
                f"vault_path: {phantom}\nslug: demo\nmode: project\n")
            rc = self._run(project, self._payload(phantom / "projects" / "demo" / "n.md"))
            self.assertEqual(rc, 0)
            self.assertFalse(phantom.exists())


class TestSessionLogFormat(_HookHarness):

    def test_added_entry_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            note = self._note(proot, "notes/idea.md")
            rc = self._run(project, self._payload(note))
            self.assertEqual(rc, 0)
            self.assertRegex(
                session.read_text(),
                r"(?m)^- \d{2}:\d{2} · Added: \[\[projects/demo/notes/idea\.md\]\]$")

    def test_decision_label_for_decisions_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            note = self._note(proot, "decisions/0001-pick-x.md")
            rc = self._run(project, self._payload(note))
            self.assertEqual(rc, 0)
            self.assertRegex(
                session.read_text(),
                r"(?m)^- \d{2}:\d{2} · Decision: \[\[projects/demo/decisions/0001-pick-x\.md\]\]$")

    def test_nested_path_link_keeps_full_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            note = self._note(proot, "docs/sub/deep.md")
            rc = self._run(project, self._payload(note))
            self.assertEqual(rc, 0)
            self.assertIn("Added: [[projects/demo/docs/sub/deep.md]]",
                          session.read_text())

    def test_midnight_straddle_appends_to_latest_note(self):
        # No note for today (session started before midnight): the entry must
        # land in the latest dated note — and the digit glob must not be fooled
        # by a 4-2-2-shaped non-date filename.
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            session.unlink()
            latest = proot / "sessions" / "2020-01-02.md"
            latest.write_text("## Log\n")
            (proot / "sessions" / "2020-01-01.md").write_text("## Log\n")
            decoy = proot / "sessions" / "abcd-ef-gh.md"
            decoy.write_text("## Not a session\n")
            note = self._note(proot, "notes/idea.md")
            rc = self._run(project, self._payload(note))
            self.assertEqual(rc, 0)
            self.assertIn("[[projects/demo/notes/idea.md]]", latest.read_text())
            self.assertNotIn("idea", decoy.read_text())

    def test_no_session_note_still_stamps(self):
        # Job independence: a missing session log must not block job 2.
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            session.unlink()
            note = self._note(proot, "notes/idea.md")
            rc = self._run(project, self._payload(note))
            self.assertEqual(rc, 0)
            self.assertIn(f"source_session: {SESSION_ID}", note.read_text())


class TestSourceSessionStamp(_HookHarness):

    def test_new_note_gets_stamped_in_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            note = self._note(proot, "notes/idea.md")
            rc = self._run(project, self._payload(note))
            self.assertEqual(rc, 0)
            fm = note.read_text().split("---\n")[1]
            self.assertIn(f"source_session: {SESSION_ID}", fm)

    def test_blank_session_id_logs_but_does_not_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            note = self._note(proot, "notes/idea.md")
            rc = self._run(project, self._payload(note, session_id="  "))
            self.assertEqual(rc, 0)
            self.assertIn("[[projects/demo/notes/idea.md]]", session.read_text())
            self.assertNotIn("source_session", note.read_text())

    def test_missing_session_id_key_logs_but_does_not_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            note = self._note(proot, "notes/idea.md")
            rc = self._run(project, {"tool_name": "Write",
                                     "tool_input": {"file_path": str(note)}})
            self.assertEqual(rc, 0)
            self.assertIn("[[projects/demo/notes/idea.md]]", session.read_text())
            self.assertNotIn("source_session", note.read_text())


class TestStampSkipRules(_HookHarness):

    def test_session_note_write_is_not_stamped(self):
        # Session notes accumulate session_id (list) via SessionStart — the
        # PostToolUse pass must not also pin a scalar source_session on them.
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            session.write_text("---\ntype: session\ndate: 2026-01-01\n---\n\n## Log\n")
            rc = self._run(project, self._payload(session))
            self.assertEqual(rc, 0)
            self.assertNotIn("source_session", session.read_text())

    def test_system_files_are_never_stamped(self):
        # _handoff / _index / _index-* / _iteration are system-managed —
        # "which conversation authored this" makes no sense there.
        for name in ("_handoff.md", "_index.md", "_index-decisions.md", "_iteration.md"):
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    project, proot, session = self._fixture(Path(tmp))
                    target = self._note(proot, name)
                    rc = self._run(project, self._payload(target))
                    self.assertEqual(rc, 0)
                    self.assertNotIn("source_session", target.read_text())
                    # The log entry is still appended — skip rules gate only
                    # the stamp, not job 1.
                    self.assertIn(f"[[projects/demo/{name}]]", session.read_text())


class TestHookProcess(_HookHarness):
    """End-to-end through the __main__ guard: real stdin, real imports."""

    def _run_proc(self, project: Path, stdin: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(project)
        env.pop("OB_VAULT", None)
        return subprocess.run(
            [sys.executable, str(HOOK)],
            env=env, capture_output=True, text=True, input=stdin, timeout=15)

    def test_end_to_end_write_logs_and_stamps(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            note = self._note(proot, "notes/idea.md")
            r = self._run_proc(project, json.dumps(self._payload(note)))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertRegex(
                session.read_text(),
                r"(?m)^- \d{2}:\d{2} · Added: \[\[projects/demo/notes/idea\.md\]\]$")
            self.assertIn(f"source_session: {SESSION_ID}", note.read_text())

    def test_garbage_stdin_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot, session = self._fixture(Path(tmp))
            r = self._run_proc(project, "\x00garbage\nnot json")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(session.read_text(), "## Log\n")


if __name__ == "__main__":
    unittest.main()
