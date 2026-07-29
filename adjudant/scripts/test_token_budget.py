"""Tests for token_budget.py: report-only context-cost accounting."""

import tempfile
import unittest
from pathlib import Path

import token_budget as tb


class TestReport(unittest.TestCase):

    def _skill(self, tmp: Path) -> Path:
        root = tmp / "adjudant"
        (root / "reference").mkdir(parents=True)
        (root / "SKILL.md").write_text("x" * 4000)          # ~1000 tok
        (root / "reference" / "sync.md").write_text("y" * 400)   # ~100 tok
        return root

    def test_counts_tokens_per_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._skill(Path(tmp))
            rep = tb.report(root)
            by = {s["file"]: s["tokens"] for s in rep["surfaces"]}
            self.assertEqual(by["SKILL.md"], 1000)
            self.assertEqual(by["reference/sync.md"], 100)
            self.assertEqual(rep["total"], 1100)

    def test_flags_over_budget_without_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._skill(Path(tmp))
            tb.BUDGETS["SKILL.md"] = 500          # deliberately low
            try:
                rep = tb.report(root)
                skill = [s for s in rep["surfaces"] if s["file"] == "SKILL.md"][0]
                self.assertTrue(skill["over"])
                self.assertEqual(rep["over_count"], 1)
            finally:
                tb.BUDGETS.pop("SKILL.md", None)

    def test_undeclared_surface_has_no_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._skill(Path(tmp))
            rep = tb.report(root)
            sync = [s for s in rep["surfaces"] if s["file"] == "reference/sync.md"][0]
            self.assertIsNone(sync["budget"])
            self.assertFalse(sync["over"])

    def test_missing_skill_root_is_empty_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            rep = tb.report(Path(tmp) / "nope")
            self.assertEqual(rep["surfaces"], [])
            self.assertEqual(rep["total"], 0)


if __name__ == "__main__":
    unittest.main()
