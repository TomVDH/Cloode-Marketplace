"""Tests for hooks/scripts/pretooluse-schema-gate.py.

The gate blocks a Write into the vault project when the proposed frontmatter
is missing required fields or carries a type/node_type conflict. Everything
else - unknown fields, writes outside the project, any infrastructural
problem - must let the write through.
"""

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
HOOK = SCRIPTS.parent / "hooks" / "scripts" / "pretooluse-schema-gate.py"
_spec = importlib.util.spec_from_file_location("pretooluse_schema_gate", HOOK)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

GOOD_NOTE = ("---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
             "tags:\n  - note\n---\n\nBody.\n")


class _GateHarness(unittest.TestCase):

    def setUp(self):
        self._ob = os.environ.pop("OB_VAULT", None)

    def tearDown(self):
        if self._ob is not None:
            os.environ["OB_VAULT"] = self._ob

    def _fixture(self, tmp: Path, zone: str = "") -> tuple[Path, Path]:
        project = tmp / "code"
        vault = tmp / "vault"
        proot = vault / "projects" / zone / "demo" if zone else vault / "projects" / "demo"
        proot.mkdir(parents=True)
        (proot / "brief.md").write_text(
            "---\ntype: project\nslug: demo\n---\n\n# Demo\n")
        (project / ".claude").mkdir(parents=True)
        (project / ".claude" / "adjudant").write_text(
            f"vault_path: {vault}\nvault_name: vault\nslug: demo\nmode: project\n")
        return project, proot

    def _run(self, project: Path, payload) -> int:
        os.environ["CLAUDE_PROJECT_DIR"] = str(project)
        before = sys.stdin
        sys.stdin = io.StringIO(payload if isinstance(payload, str)
                                else json.dumps(payload))
        try:
            return gate.main()
        finally:
            sys.stdin = before
            del os.environ["CLAUDE_PROJECT_DIR"]

    def _payload(self, path: Path, content: str, tool: str = "Write") -> dict:
        return {"tool_name": tool,
                "tool_input": {"file_path": str(path), "content": content}}


class TestBlocks(_GateHarness):

    def test_missing_required_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            rc = self._run(project, self._payload(
                proot / "decisions" / "d.md", "---\ntype: decision\n---\n\nB\n"))
            self.assertEqual(rc, 2)

    def test_type_conflict_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            bad = GOOD_NOTE.replace("type: note\n", "type: note\nnode_type: note\n")
            rc = self._run(project, self._payload(proot / "notes" / "n.md", bad))
            self.assertEqual(rc, 2)


class TestAllows(_GateHarness):

    def test_conformant_note_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            rc = self._run(project, self._payload(proot / "notes" / "n.md", GOOD_NOTE))
            self.assertEqual(rc, 0)

    def test_unknown_field_warns_but_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            bad = GOOD_NOTE.replace("type: note\n", "type: note\nbogus: x\n")
            rc = self._run(project, self._payload(proot / "notes" / "n.md", bad))
            self.assertEqual(rc, 0)

    def test_write_outside_project_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = self._fixture(Path(tmp))
            rc = self._run(project, self._payload(
                Path(tmp) / "elsewhere.md", "---\ntype: decision\n---\n\nB\n"))
            self.assertEqual(rc, 0)

    def test_edit_tool_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            rc = self._run(project, self._payload(
                proot / "decisions" / "d.md", "---\ntype: decision\n---\n\nB\n",
                tool="Edit"))
            self.assertEqual(rc, 0)

    def test_shelved_project_is_gated_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp), zone="_fridge")
            rc = self._run(project, self._payload(
                proot / "decisions" / "d.md", "---\ntype: decision\n---\n\nB\n"))
            self.assertEqual(rc, 2)


class TestFailsOpen(_GateHarness):

    def test_no_breadcrumb_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "code"
            project.mkdir()
            rc = self._run(project, self._payload(
                Path(tmp) / "x.md", "---\ntype: decision\n---\n\nB\n"))
            self.assertEqual(rc, 0)

    def test_garbage_payload_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = self._fixture(Path(tmp))
            self.assertEqual(self._run(project, "not json {{{"), 0)

    def test_traversal_slug_allows_and_does_not_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, proot = self._fixture(root)
            (project / ".claude" / "adjudant").write_text(
                f"vault_path: {root / 'vault'}\nslug: ../../../escaped\nmode: project\n")
            rc = self._run(project, self._payload(
                proot / "decisions" / "d.md", "---\ntype: decision\n---\n\nB\n"))
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
