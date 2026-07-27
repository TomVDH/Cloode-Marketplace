"""Tests for hooks/scripts/posttooluse-commit-log.py: commit-gated logging.

The hook is SELF-GATED: any hooks.json `if` filter added at wiring time is
defense in depth, never a dependency. So these tests drive main() with full
PostToolUse(Bash) payloads and assert the gates hold (non-commit ignored,
failed commit ignored, stale breadcrumb fail-closed) and the writes land
(session-log commit line, release stub from templates/release.md, one index
row in releases/_index.md, never clobbering an existing note).
"""

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
HOOK = SCRIPTS.parent / "hooks" / "scripts" / "posttooluse-commit-log.py"

# Hyphenated filename: load via importlib, same interpreter (main invoked
# in-process with stdin patched, mirroring test_precompact's approach).
_spec = importlib.util.spec_from_file_location("posttooluse_commit_log", HOOK)
commit_log = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(commit_log)


class _CommitLogCase(unittest.TestCase):
    """Temp project + vault + breadcrumb + session note, OB_VAULT hygiene.

    vault_name in the breadcrumb is deliberately implausible so the
    resolve_vault name-candidate scan can never land on a real vault on the
    developer's machine when a test deletes the temp vault.
    """

    def setUp(self):
        self._ob_vault = os.environ.pop("OB_VAULT", None)
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.project = tmp / "code"
        self.vault = tmp / "vault"
        self.project_root = self.vault / "projects" / "demo"
        (self.project_root / "sessions").mkdir(parents=True)
        self.session_note = self.project_root / "sessions" / "2020-01-02.md"
        self.session_note.write_text("## Log\n")
        (self.project / ".claude").mkdir(parents=True)
        (self.project / ".claude" / "adjudant").write_text(
            f"vault_path: {self.vault}\n"
            "vault_name: commit-log-test-vault-1f9a\n"
            "slug: demo\nmode: project\n")

    def tearDown(self):
        self._tmp.cleanup()
        if self._ob_vault is not None:
            os.environ["OB_VAULT"] = self._ob_vault

    def _run(self, payload) -> int:
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.project)
        stdin_before = sys.stdin
        sys.stdin = io.StringIO(json.dumps(payload))
        try:
            return commit_log.main()
        finally:
            sys.stdin = stdin_before
            del os.environ["CLAUDE_PROJECT_DIR"]

    @staticmethod
    def _payload(command, *, tool_name="Bash", tool_response=None):
        if tool_response is None:
            tool_response = {"stdout": "", "stderr": "", "exit_code": 0}
        return {
            "session_id": "abc123",
            "hook_event_name": "PostToolUse",
            "tool_name": tool_name,
            "tool_input": {"command": command},
            "tool_response": tool_response,
        }


class TestGates(_CommitLogCase):

    def test_non_commit_ignored(self):
        rc = self._run(self._payload("ls -la"))
        self.assertEqual(rc, 0)
        self.assertEqual(self.session_note.read_text(), "## Log\n")

    def test_non_bash_tool_ignored(self):
        rc = self._run(self._payload(
            'git commit -m "feat(demo): smuggled"', tool_name="Write"))
        self.assertEqual(rc, 0)
        self.assertEqual(self.session_note.read_text(), "## Log\n")

    def test_failed_commit_ignored(self):
        rc = self._run(self._payload(
            'git commit -m "feat(demo): broken"',
            tool_response={"stdout": "", "stderr": "nothing added", "exit_code": 1}))
        self.assertEqual(rc, 0)
        self.assertEqual(self.session_note.read_text(), "## Log\n")

    def test_interrupted_commit_ignored(self):
        rc = self._run(self._payload(
            'git commit -m "feat(demo): cut short"',
            tool_response={"stdout": "", "stderr": "", "interrupted": True}))
        self.assertEqual(rc, 0)
        self.assertEqual(self.session_note.read_text(), "## Log\n")

    def test_stale_breadcrumb_fail_closed(self):
        # Vault gone (other machine's path): nothing may be materialized.
        shutil.rmtree(self.vault)
        rc = self._run(self._payload('git commit -m "feat(demo): orphan"'))
        self.assertEqual(rc, 0)
        self.assertFalse(self.vault.exists(),
                         "stale vault path must NOT be materialized by the hook")


class TestCommitLogged(_CommitLogCase):

    def test_commit_logged(self):
        rc = self._run(self._payload('git commit -m "feat(demo): wire the thing"'))
        self.assertEqual(rc, 0)
        text = self.session_note.read_text()
        self.assertRegex(text, r"- \d{2}:\d{2} · commit: feat\(demo\): wire the thing")

    def test_commit_logged_without_exit_key(self):
        # Payload shape without an exit code field (older harness): no failure
        # signal present counts as success.
        rc = self._run(self._payload(
            'git commit -m "feat(demo): plain payload"',
            tool_response={"stdout": "1 file changed", "stderr": "", "interrupted": False}))
        self.assertEqual(rc, 0)
        self.assertIn("· commit: feat(demo): plain payload", self.session_note.read_text())

    def test_cd_prefix_stripped(self):
        rc = self._run(self._payload(
            'cd "/tmp/some dir" && git commit -m "fix(demo): after cd"'))
        self.assertEqual(rc, 0)
        self.assertIn("· commit: fix(demo): after cd", self.session_note.read_text())

    def test_heredoc_subject_only_first_line(self):
        cmd = ('git commit -m "$(cat <<\'EOF\'\n'
               "feat(demo): heredoc subject\n"
               "\n"
               "body line one\n"
               "EOF\n"
               ')"')
        rc = self._run(self._payload(cmd))
        self.assertEqual(rc, 0)
        text = self.session_note.read_text()
        self.assertIn("· commit: feat(demo): heredoc subject", text)
        self.assertNotIn("body line one", text)


class TestReleaseScaffold(_CommitLogCase):

    RELEASE_CMD = ('git commit -m "$(cat <<\'EOF\'\n'
                   "release(adjudant): v0.15.0 - ambient board\n"
                   "\n"
                   "- task schema locked\n"
                   "- board born on first task\n"
                   "EOF\n"
                   ')"')

    def test_release_scaffold(self):
        rc = self._run(self._payload(self.RELEASE_CMD))
        self.assertEqual(rc, 0)
        note = self.project_root / "releases" / "v0.15.0.md"
        self.assertTrue(note.is_file(), "release stub must be scaffolded")
        text = note.read_text()
        self.assertIn("type: release", text)
        self.assertIn("version: 0.15.0", text)
        # v0.16.0: membership is the path — no project: field on written notes
        self.assertNotIn("project:", text)
        self.assertIn("# v0.15.0 (adjudant)", text)
        self.assertIn("- task schema locked", text)
        index = self.project_root / "releases" / "_index.md"
        self.assertTrue(index.is_file(), "index must be created on first release")
        self.assertIn("- [[v0.15.0|v0.15.0 (adjudant)]]", index.read_text())

    def test_release_no_clobber(self):
        releases = self.project_root / "releases"
        releases.mkdir()
        note = releases / "v0.15.0.md"
        note.write_text("hand-written release history\n")
        rc = self._run(self._payload(self.RELEASE_CMD))
        self.assertEqual(rc, 0)
        self.assertEqual(note.read_text(), "hand-written release history\n",
                         "an existing release note must never be overwritten")

    def test_release_index_upsert_no_duplicate(self):
        self._run(self._payload(self.RELEASE_CMD))
        self._run(self._payload(self.RELEASE_CMD))
        index_text = (self.project_root / "releases" / "_index.md").read_text()
        self.assertEqual(index_text.count("[[v0.15.0|"), 1,
                         "upsert must not duplicate the index row")

    def test_plain_commit_no_release_files(self):
        rc = self._run(self._payload('git commit -m "feat(demo): not a release"'))
        self.assertEqual(rc, 0)
        self.assertFalse((self.project_root / "releases").exists(),
                         "non-release commits must not create releases/")


if __name__ == "__main__":
    unittest.main()
