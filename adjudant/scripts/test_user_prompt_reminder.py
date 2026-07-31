"""Tests for hooks/scripts/user-prompt-reminder.sh — the smart-fire reminder.

Finding 31: the keyword regex fired on everyday English ("give me a brief
summary", "good decision"), and each session leaked one marker file into
TMPDIR forever. Precision over recall: distinctive words and phrase forms
only, and stale markers are swept when a new one is written.
"""

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "user-prompt-reminder.sh"


class _ReminderHarness(unittest.TestCase):

    def _run(self, prompt: str, tmp: Path, session_id: str = "sess-1") -> str:
        """Run the hook against an UNLINKED project dir; returns stdout."""
        project = tmp / "code"
        project.mkdir(exist_ok=True)
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(project)
        env["TMPDIR"] = str(tmp)
        env.pop("ADJUDANT_REMINDER_DISABLE", None)
        proc = subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps({"session_id": session_id, "prompt": prompt}),
            capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(proc.returncode, 0)
        return proc.stdout


class TestKeywordPrecision(_ReminderHarness):

    def test_fires_on_vault_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._run("put this in the vault please", Path(tmp))
            self.assertIn("adjudant", out)

    def test_silent_on_brief_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._run("give me a brief summary of the diff", Path(tmp))
            self.assertEqual(out, "")

    def test_silent_on_good_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._run("good decision, ship it", Path(tmp))
            self.assertEqual(out, "")

    def test_fires_on_this_decision_phrase(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._run("record this decision somewhere", Path(tmp))
            self.assertIn("adjudant", out)


class TestMarkerHygiene(_ReminderHarness):

    def test_stale_markers_are_swept_on_fire(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpp = Path(tmp)
            stale = tmpp / "adjudant-reminder-old-session"
            stale.write_text("")
            two_days_ago = time.time() - 2 * 86400
            os.utime(stale, (two_days_ago, two_days_ago))
            out = self._run("note this in the vault", tmpp, session_id="sess-9")
            self.assertIn("adjudant", out)
            self.assertTrue((tmpp / "adjudant-reminder-sess-9").exists())
            self.assertFalse(stale.exists(),
                             "markers from past sessions must be swept")


if __name__ == "__main__":
    unittest.main()
