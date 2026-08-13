"""Tests for kebab.py — the slugifier, and the naming scan behind the joke.

vault-standards §4 says most filename rules are "on you": ramasse checks doc
case, the decision date prefix, session filenames and canvas/base names, and
nothing checks the kebab-title portion of a note, task, source, or decision.
kebab closes that gap. Read-only by design: renaming a file breaks every
wikilink pointing at it, and that repair is ramasse's job, with its preview
and its backups.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kebab import cli_main as kebab_cli, kebab_violations, slugify


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


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
            rc = kebab_cli(list(argv))
        return rc, out.getvalue(), err.getvalue()

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
            rc, out, _ = self._run("--scan", "--project-dir", str(root))
            self.assertEqual(rc, 0)
            payload = json.loads(out)
            self.assertEqual(payload["summary"]["violations"], 1)
            self.assertEqual(payload["violations"][0]["suggested"], "bad-name.md")
            for p, m in before.items():
                self.assertEqual(p.stat().st_mtime_ns, m)

    def test_scan_of_a_tidy_project_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _w(root / "brief.md",
               "---\ntype: project\nproject_type: coding\nslug: demo\n"
               "tags:\n  - project\n---\n\n# Demo\n")
            _, out, _ = self._run("--scan", "--project-dir", str(root))
            self.assertEqual(json.loads(out)["summary"]["violations"], 0)


if __name__ == "__main__":
    unittest.main()
