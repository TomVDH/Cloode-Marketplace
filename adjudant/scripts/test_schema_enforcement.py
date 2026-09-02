"""Acceptance test for plan 2: the template is the schema, and it bites.

Before v3 nothing ever compared a real vault file to its template, which is
how the vault reached 45 type values, 110 frontmatter keys and 420 tags.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from _template_schema import FIELD_SCHEMA, TEMPLATES_DIR, load_schema
from _vault_walk import schema_drift_for_text


class TestSchemaBites(unittest.TestCase):
    """`schema_drift_for_text` returns Optional[dict] and omits a key entirely
    when that class of drift is absent, so every assertion below goes through
    `.get()` with a default rather than indexing."""

    def _drift(self, text: str, rel: str) -> dict:
        return schema_drift_for_text(text, rel) or {}

    def test_a_missing_required_field_is_drift(self):
        text = "---\ntype: decision\ncreated: 2026-09-01\nupdated: 2026-09-01\n---\n\n# X\n"
        drift = self._drift(text, "decisions/x.md")
        self.assertIn("status", drift.get("missing_required", []))

    def test_a_retired_field_is_unknown(self):
        text = ("---\ntype: note\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
                "tags:\n  - note\n---\n\n# X\n")
        drift = self._drift(text, "notes/x.md")
        self.assertIn("tags", drift.get("unknown_fields", []))

    def test_an_off_vocabulary_status_is_reported(self):
        text = ("---\ntype: task\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
                "status: obsolete\n---\n\n# X\n")
        drift = self._drift(text, "tasks/x.md")
        invalid = drift.get("status_invalid") or {}
        self.assertEqual(invalid.get("value"), "obsolete",
                         "the value someone had to invent is still accepted")

    def test_dropped_is_now_a_real_status(self):
        text = ("---\ntype: task\ncreated: 2026-09-01\nupdated: 2026-09-01\n"
                "status: dropped\n---\n\n# X\n")
        drift = self._drift(text, "tasks/x.md")
        self.assertIsNone(drift.get("status_invalid"))

    def test_editing_a_template_changes_enforcement(self):
        """One declaration, proven end to end."""
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            for p in TEMPLATES_DIR.glob("*.md"):
                shutil.copy2(p, tmp / p.name)
            self.assertIn("verified", load_schema(tmp)["doc"]["required"])
            doc = tmp / "doc.md"
            doc.write_text("\n".join(
                ln for ln in doc.read_text().splitlines()
                if not ln.startswith("verified:")) + "\n")
            self.assertNotIn("verified", load_schema(tmp)["doc"]["required"])


class TestTagsAreGone(unittest.TestCase):

    def test_no_kind_accepts_tags(self):
        for kind, spec in FIELD_SCHEMA.items():
            self.assertNotIn("tags", spec["required"] | spec["optional"],
                             f"{kind} still accepts tags")

    def test_the_bucket_constants_are_gone(self):
        import _vault_walk
        src = Path(_vault_walk.__file__).read_text()
        for gone in ("BUCKET_A_TYPES", "BUCKET_B_MIGRATIONS",
                     "BUCKET_D_TAG_EXACT", "BUCKET_D_TAG_PREFIXES",
                     "PROJECT_TYPE_TAGS", "CREW_NAMES",
                     "VAGUE_TOPICAL_TAGS", "PROJECT_STATUS_VALUES"):
            self.assertNotIn(f"{gone}:", src, f"{gone} survived")


if __name__ == "__main__":
    unittest.main()
