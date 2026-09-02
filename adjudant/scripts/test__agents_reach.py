"""Tests for adjudant/scripts/_agents_reach.py.

AGENTS.md is the first thing every agent reads and nothing keeps it true. Of
five false statements in one project's file, three were detectable without
adjudant knowing anything about the project: they named things that are not
there.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from _agents_reach import AGENTS_STALE_COMMITS, agents_reach, named_paths


class TestNamedPaths(unittest.TestCase):

    def test_backticked_paths(self):
        text = "Run `scripts/validate.py` and read `docs/plan.md`.\n"
        self.assertEqual([t for _n, t in named_paths(text)],
                         ["scripts/validate.py", "docs/plan.md"])

    def test_a_backticked_path_with_spaces_survives_whole(self):
        text = "Rules live in `~/Library/Mobile Documents/claude/hookify/`.\n"
        self.assertEqual([t for _n, t in named_paths(text)],
                         ["~/Library/Mobile Documents/claude/hookify"])

    def test_markdown_link_targets(self):
        text = "See [the spec](docs/specs/thing.md).\n"
        self.assertEqual([t for _n, t in named_paths(text)],
                         ["docs/specs/thing.md"])

    def test_fenced_code_is_tokenised_on_whitespace(self):
        text = "```bash\npython3 adjudant/scripts/validate.py --all\n```\n"
        self.assertEqual([t for _n, t in named_paths(text)],
                         ["adjudant/scripts/validate.py"])

    def test_urls_placeholders_and_globs_are_not_paths(self):
        text = ("`https://example.test/a.md` `<plugin-name>/plugin.json` "
                "`{slug}/brief.md` `hooks/*.py` `$HOME/x.sh` `--flag`\n")
        self.assertEqual(named_paths(text), [])

    def test_bare_words_are_not_paths(self):
        text = "Install `pre-commit`, then run `make`.\n"
        self.assertEqual(named_paths(text), [])

    def test_a_bare_filename_with_a_known_extension_counts(self):
        self.assertEqual([t for _n, t in named_paths("Read `AGENTS.md`.\n")],
                         ["AGENTS.md"])

    def test_line_numbers_are_reported(self):
        text = "intro\n\nRun `scripts/go.sh`.\n"
        self.assertEqual(named_paths(text), [(3, "scripts/go.sh")])

    def test_each_token_is_reported_once_per_line(self):
        text = "`a/b.py` and `a/b.py` again\n"
        self.assertEqual(named_paths(text), [(1, "a/b.py")])


class TestAgentsReach(unittest.TestCase):

    def test_absent_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = agents_reach(Path(tmp))
            self.assertFalse(out["present"])
            self.assertEqual(out["missing"], [])
            self.assertEqual(out["checked"], 0)

    def test_reports_only_what_is_not_there(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "real.py").write_text("x")
            (root / "AGENTS.md").write_text(
                "Run `scripts/real.py`.\n\n"
                "Enforced mechanically by `scripts/enforce-branch-rule.sh`.\n")
            out = agents_reach(root)
            self.assertTrue(out["present"])
            self.assertEqual(out["checked"], 2)
            self.assertEqual([m["token"] for m in out["missing"]],
                             ["scripts/enforce-branch-rule.sh"])
            self.assertEqual(out["missing"][0]["line"], 3)

    def test_a_named_directory_counts_as_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "adjudant").mkdir()
            (root / "AGENTS.md").write_text("The plugin lives in `adjudant/`.\n")
            self.assertEqual(agents_reach(root)["missing"], [])

    def test_an_absolute_path_is_checked_as_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                f"Rules live in `{root}/nowhere/rules.sh`.\n")
            self.assertEqual([m["token"] for m in agents_reach(root)["missing"]],
                             [f"{root}/nowhere/rules.sh"])

    def test_commit_count_in_a_real_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.test",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.test",
                   "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(root)}

            def git(*args):
                subprocess.run(["git", "-C", str(root), *args],
                               env=env, capture_output=True, check=True)

            git("init", "-q", "-b", "main")
            (root / "AGENTS.md").write_text("Read `AGENTS.md`.\n")
            git("add", "AGENTS.md")
            git("commit", "-q", "-m", "a")
            for i in range(3):
                (root / f"f{i}.txt").write_text("x")
                git("add", f"f{i}.txt")
                git("commit", "-q", "-m", f"f{i}")
            out = agents_reach(root)
            self.assertEqual(out["commits_since_change"], 3)
            self.assertRegex(out["last_changed"], r"^\d{4}-\d{2}-\d{2}$")

    def test_outside_a_repo_the_commit_count_is_none_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("Read `AGENTS.md`.\n")
            out = agents_reach(root)
            self.assertIsNone(out["commits_since_change"])
            self.assertIsNone(out["last_changed"])

    def test_nothing_is_written_to_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = "Run `scripts/gone.py`.\n"
            (root / "AGENTS.md").write_text(original)
            agents_reach(root)
            self.assertEqual((root / "AGENTS.md").read_text(), original)

    def test_the_stale_threshold_is_named(self):
        self.assertEqual(AGENTS_STALE_COMMITS, 30)


if __name__ == "__main__":
    unittest.main()
