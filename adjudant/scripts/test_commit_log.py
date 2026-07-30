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
import subprocess
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
        # The project must be a REAL git repo: since the 2026-07-27 audit the
        # hook verifies the commit against `git log -1` instead of trusting
        # the payload (which carries no exit code), so a fixture without a
        # matching HEAD is correctly treated as "commit did not happen".
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "Test")
        self._git("config", "commit.gpgsign", "false")

    def _git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.project), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)

    RELEASE_CMD = ('git commit -m "$(cat <<\'EOF\'\n'
                   "release(adjudant): v0.15.0 - ambient board\n"
                   "\n"
                   "- task schema locked\n"
                   "- board born on first task\n"
                   "EOF\n"
                   ')"')

    def _land(self, subject: str, body: str = "") -> None:
        """Make HEAD actually be `subject`, so commit_verified passes.

        Every test that expects the hook to get PAST commit verification must
        call this (or _land_release). A fixture without a matching HEAD stops
        at the verification gate, and any guard the test is named for never
        runs — the test then passes with that guard deleted.
        """
        (self.project / "f.txt").write_text(subject)
        self._git("add", "-A")
        msg = subject if not body else f"{subject}\n\n{body}"
        self._git("commit", "-q", "-m", msg)

    def _land_release(self) -> None:
        """HEAD becomes the RELEASE_CMD commit."""
        self._land("release(adjudant): v0.15.0 - ambient board",
                   "- task schema locked\n- board born on first task")

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
        self._land("feat(demo): wire the thing")
        rc = self._run(self._payload('git commit -m "feat(demo): wire the thing"'))
        self.assertEqual(rc, 0)
        text = self.session_note.read_text()
        self.assertRegex(text, r"- \d{2}:\d{2} · commit: feat\(demo\): wire the thing")

    def test_commit_logged_without_exit_key(self):
        # Payload shape without an exit code field (older harness): no failure
        # signal present counts as success.
        self._land("feat(demo): plain payload")
        rc = self._run(self._payload(
            'git commit -m "feat(demo): plain payload"',
            tool_response={"stdout": "1 file changed", "stderr": "", "interrupted": False}))
        self.assertEqual(rc, 0)
        self.assertIn("· commit: feat(demo): plain payload", self.session_note.read_text())

    def test_cd_prefix_stripped(self):
        self._land("fix(demo): after cd")
        rc = self._run(self._payload(
            f'cd "{self.project}" && git commit -m "fix(demo): after cd"'))
        self.assertEqual(rc, 0)
        self.assertIn("· commit: fix(demo): after cd", self.session_note.read_text())

    def test_heredoc_subject_only_first_line(self):
        cmd = ('git commit -m "$(cat <<\'EOF\'\n'
               "feat(demo): heredoc subject\n"
               "\n"
               "body line one\n"
               "EOF\n"
               ')"')
        self._land("feat(demo): heredoc subject", "body line one")
        rc = self._run(self._payload(cmd))
        self.assertEqual(rc, 0)
        text = self.session_note.read_text()
        self.assertIn("· commit: feat(demo): heredoc subject", text)
        self.assertNotIn("body line one", text)


class TestReleaseScaffold(_CommitLogCase):

    def test_release_scaffold(self):
        self._land_release()
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
        # The release must actually LAND: without _land_release the hook stops
        # at commit verification and the no-clobber branch is never reached,
        # which is how this test used to pass with `if not note.exists()`
        # deleted from the hook.
        self._land_release()
        releases = self.project_root / "releases"
        releases.mkdir()
        note = releases / "v0.15.0.md"
        note.write_text("hand-written release history\n")
        rc = self._run(self._payload(self.RELEASE_CMD))
        self.assertEqual(rc, 0)
        self.assertIn("· commit: release(adjudant): v0.15.0",
                      self.session_note.read_text(),
                      "the hook must have got past commit verification")
        self.assertEqual(note.read_text(), "hand-written release history\n",
                         "an existing release note must never be overwritten")
        self.assertIn("- [[v0.15.0|v0.15.0 (adjudant)]]",
                      (releases / "_index.md").read_text(),
                      "the index row is still upserted around the kept note")

    def test_release_index_upsert_no_duplicate(self):
        self._land_release()
        self._run(self._payload(self.RELEASE_CMD))
        self._run(self._payload(self.RELEASE_CMD))
        index_text = (self.project_root / "releases" / "_index.md").read_text()
        self.assertEqual(index_text.count("[[v0.15.0|"), 1,
                         "upsert must not duplicate the index row")

    def test_plain_commit_no_release_files(self):
        self._land("feat(demo): not a release")
        rc = self._run(self._payload('git commit -m "feat(demo): not a release"'))
        self.assertEqual(rc, 0)
        self.assertFalse((self.project_root / "releases").exists(),
                         "non-release commits must not create releases/")


class TestDryRunNeverLogs(_CommitLogCase):
    """Audit 2026-07-27: --dry-run commits nothing, so logging it forged
    records. `git commit --dry-run -m "release(x): v9.9.9"` scaffolded a real
    releases/v9.9.9.md for a release that never existed.

    Each test LANDS the matching commit first, so `commit_verified` passes and
    the no-commit-flag guard is the only gate left. That is the realistic
    shape too: a dry run is usually a repeat of a subject that already exists
    at HEAD. Without the landed commit these tests stopped at verification and
    stayed green with `_NO_COMMIT_FLAG_RE` deleted from the hook.
    """

    def test_dry_run_release_scaffolds_nothing(self):
        self._land("release(adjudant): v9.9.9 - never happened")
        rc = self._run(self._payload(
            'git commit --dry-run -m "release(adjudant): v9.9.9 - never happened"'))
        self.assertEqual(rc, 0)
        self.assertEqual(self.session_note.read_text(), "## Log\n")
        self.assertFalse((self.project_root / "releases").exists())

    def test_no_commit_flags_are_ignored(self):
        self._land("feat(demo): phantom")
        for flag in ("--dry-run", "--short", "--porcelain", "--long"):
            with self.subTest(flag=flag):
                rc = self._run(self._payload(
                    f'git commit {flag} -m "feat(demo): phantom"'))
                self.assertEqual(rc, 0)
                self.assertEqual(self.session_note.read_text(), "## Log\n")

    def test_same_fixture_logs_once_the_flag_is_gone(self):
        # Control: identical fixture, identical subject, no no-commit flag.
        # It logs. So the two tests above are green because of the flag guard,
        # not because the fixture never reached the write.
        self._land("feat(demo): phantom")
        rc = self._run(self._payload('git commit -m "feat(demo): phantom"'))
        self.assertEqual(rc, 0)
        self.assertIn("· commit: feat(demo): phantom", self.session_note.read_text())


class TestLogSafeSubject(_CommitLogCase):
    """Audit 2026-07-27: subjects are author text landing in a wikilink-bearing
    markdown file, written verbatim before this."""

    def test_wikilink_in_subject_is_neutralized(self):
        subject = "feat(demo): see [[projects/other/decisions/secret]] now"
        self._land(subject)
        rc = self._run(self._payload(f'git commit -m "{subject}"'))
        self.assertEqual(rc, 0)
        text = self.session_note.read_text()
        self.assertNotIn("[[projects/other", text)
        self.assertIn("[ [projects/other", text)

    def test_long_subject_capped(self):
        subject = "feat(demo): " + "x" * 400
        self._land(subject)
        self._run(self._payload(f'git commit -m "{subject}"'))
        line = [ln for ln in self.session_note.read_text().splitlines()
                if "commit:" in ln][0]
        self.assertLessEqual(len(line), 240)
        self.assertTrue(line.endswith("…"))

    def test_log_safe_flattens_newlines(self):
        self.assertEqual(
            commit_log.log_safe("feat: a\nforged: line"), "feat: a forged: line")
        self.assertEqual(commit_log.log_safe("a\r\nb"), "a b")


class TestCommitVerification(_CommitLogCase):
    """Audit 2026-07-27: the Bash tool_response carries no exit code, so the
    old payload-only gate failed OPEN and logged commits that never landed."""

    def test_nothing_to_commit_is_not_logged(self):
        # The exact real-world case: git prints this and exits non-zero, but
        # the payload shape carries no exit code to notice it by.
        rc = self._run(self._payload(
            'git commit -m "feat(demo): nothing staged"',
            tool_response={"stdout": "nothing to commit, working tree clean",
                           "stderr": ""}))
        self.assertEqual(rc, 0)
        self.assertEqual(self.session_note.read_text(), "## Log\n")

    def test_subject_mismatch_is_not_logged(self):
        # HEAD is a different commit than the command claims: unverifiable.
        self._land("feat(demo): what actually landed")
        rc = self._run(self._payload('git commit -m "feat(demo): what was claimed"'))
        self.assertEqual(rc, 0)
        self.assertEqual(self.session_note.read_text(), "## Log\n")

    def test_git_c_form_is_logged(self):
        # Also finding 20: `git -C <repo> commit` is a real commit form that
        # used to be dropped entirely.
        self._land("fix(demo): via dash-C")
        rc = self._run(self._payload(
            f'git -C "{self.project}" commit -m "fix(demo): via dash-C"'))
        self.assertEqual(rc, 0)
        self.assertIn("· commit: fix(demo): via dash-C", self.session_note.read_text())

    def test_not_a_repo_fails_closed(self):
        import shutil as _sh
        _sh.rmtree(self.project / ".git")
        rc = self._run(self._payload('git commit -m "feat(demo): no repo here"'))
        self.assertEqual(rc, 0)
        self.assertEqual(self.session_note.read_text(), "## Log\n")


if __name__ == "__main__":
    unittest.main()
