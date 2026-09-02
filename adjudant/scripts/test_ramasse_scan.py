"""Tests for adjudant/scripts/ramasse_scan.py."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ramasse_scan import (
    cli_main as ramasse_cli,
    detect_broken_wikilinks,
    detect_doc_decision_flags,
    detect_folder_drift,
    detect_frontmatter_drift,
    detect_index_gaps,
    detect_artefact_naming,
    detect_naming_violations,
    detect_type_drift,
    detect_wikilink_form_violations,
    run_scan,
)
from _vault_walk import build_vault_index, walk_project


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _make_minimal_project(root: Path, slug: str = "test", project_type: str = "coding", extra_folders=None) -> None:
    """Standard adjudant project skeleton for tests."""
    ef = extra_folders or []
    ef_block = "extra_folders:\n" + "".join(f"  - {x}\n" for x in ef) if ef else ""
    _write_file(root / "brief.md", (
        "---\n"
        "type: project\n"
        f"project_type: {project_type}\n"
        f"slug: {slug}\n"
        f"{ef_block}"
        "tags:\n  - project\n"
        "---\n\n# Test Project\n"
    ))
    _write_file(root / "_handoff.md", "---\ntype: handoff\nupdated: 2026-05-26\n---\n\nbody")
    (root / "sessions").mkdir()
    (root / "images").mkdir()


# ============================================================
# Folder drift
# ============================================================


class TestDetectFolderDrift(unittest.TestCase):

    def test_no_drift_when_only_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_project(root)
            (root / "decisions").mkdir()
            (root / "notes").mkdir()
            drift = detect_folder_drift(root, "coding", [])
            self.assertEqual(drift, [])

    def test_unexpected_folder_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_project(root)
            (root / "weird-folder").mkdir()
            drift = detect_folder_drift(root, "coding", [])
            self.assertEqual(drift, ["weird-folder"])

    def test_extra_folders_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_project(root, extra_folders=["memory", "gemini"])
            (root / "memory").mkdir()
            (root / "gemini").mkdir()
            drift = detect_folder_drift(root, "coding", ["memory", "gemini"])
            self.assertEqual(drift, [])

    def test_auto_created_folders_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_project(root)
            (root / "dreams").mkdir()
            (root / "canvases").mkdir()
            drift = detect_folder_drift(root, "coding", [])
            self.assertEqual(drift, [])

    def test_board_folder_not_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_project(root)
            (root / "board").mkdir()
            drift = detect_folder_drift(root, "coding", [])
            self.assertEqual(drift, [])

    def test_dotted_folders_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_project(root)
            (root / ".obsidian").mkdir()
            (root / ".trash").mkdir()
            drift = detect_folder_drift(root, "coding", [])
            self.assertEqual(drift, [])


# ============================================================
# Index gaps
# ============================================================


class TestDetectIndexGaps(unittest.TestCase):

    def test_two_siblings_no_index_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "memory" / "a.md", "---\ntype: note\n---\n\na")
            _write_file(root / "memory" / "b.md", "---\ntype: note\n---\n\nb")
            files = list(walk_project(root))
            gaps = detect_index_gaps(root, files)
            self.assertEqual(gaps, ["memory"])

    def test_index_present_no_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "memory" / "a.md", "---\ntype: note\n---\n\na")
            _write_file(root / "memory" / "b.md", "---\ntype: note\n---\n\nb")
            _write_file(root / "memory" / "_index.md", "---\ntype: index\n---\n# Memory")
            files = list(walk_project(root))
            self.assertEqual(detect_index_gaps(root, files), [])

    def test_exempt_folders_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "sessions" / "2026-05-26.md", "---\ntype: session\n---\n")
            _write_file(root / "sessions" / "2026-05-27.md", "---\ntype: session\n---\n")
            files = list(walk_project(root))
            self.assertEqual(detect_index_gaps(root, files), [])

    def test_single_file_no_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "notes" / "lone.md", "---\ntype: note\n---\n")
            files = list(walk_project(root))
            self.assertEqual(detect_index_gaps(root, files), [])


# ============================================================
# Frontmatter drift
# ============================================================


class TestDetectFrontmatterDrift(unittest.TestCase):

    def test_null_value_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "x.md", "---\ntype: note\ncodename: null\n---\n\nbody")
            files = list(walk_project(root))
            drift = detect_frontmatter_drift(files)
            self.assertEqual(len(drift), 1)
            self.assertIn("codename", drift[0]["issue"])

    def test_missing_frontmatter_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "MEMORY.md", "Just body, no frontmatter")
            files = list(walk_project(root))
            drift = detect_frontmatter_drift(files)
            self.assertEqual(len(drift), 1)
            self.assertIn("missing frontmatter", drift[0]["issue"])


# ============================================================
# Type drift
# ============================================================


class TestDetectTypeDrift(unittest.TestCase):

    def test_canonical_types_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "a.md", "---\ntype: note\n---\n")
            _write_file(root / "b.md", "---\ntype: decision\n---\n")
            files = list(walk_project(root))
            self.assertEqual(detect_type_drift(files)["non_canonical_count"], 0)

    def test_non_canonical_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "a.md", "---\ntype: api-ref\n---\n")
            # `dream-report` was a kind until v3 retired its template; the
            # canonical set is now whatever the templates declare.
            _write_file(root / "b.md", "---\ntype: dream-report\n---\n")
            _write_file(root / "c.md", "---\ntype: api-ref\n---\n")
            files = list(walk_project(root))
            drift = detect_type_drift(files)
            self.assertEqual(drift["non_canonical_count"], 3)
            self.assertEqual(drift["values"]["api-ref"]["count"], 2)


# ============================================================
# Naming violations
# ============================================================


class TestDetectNamingViolations(unittest.TestCase):

    def test_lowercase_doc_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "lowercase-name.md", "---\ntype: doc\n---\n")
            files = list(walk_project(root))
            v = detect_naming_violations(files)
            self.assertTrue(any("UPPERCASE" in x["issue"] for x in v))

    def test_uppercase_doc_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "STANDARDS.md", "---\ntype: doc\n---\n")
            files = list(walk_project(root))
            self.assertEqual(detect_naming_violations(files), [])

    def test_decision_without_date_prefix_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "decisions" / "no-date.md", "---\ntype: decision\n---\n")
            files = list(walk_project(root))
            v = detect_naming_violations(files)
            self.assertTrue(any("YYYY-MM-DD-" in x["issue"] for x in v))

    def test_templates_folder_exempt_from_naming(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # template scaffolds are named for their type, not an instance — exempt
            _write_file(root / "templates" / "decision.md", "---\ntype: decision\n---\n")
            _write_file(root / "templates" / "session.md", "---\ntype: session\n---\n")
            _write_file(root / "templates" / "doc.md", "---\ntype: doc\n---\n")
            files = list(walk_project(root))
            self.assertEqual(detect_naming_violations(files), [])

    def test_session_with_trailing_kebab_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "sessions" / "2026-05-26-extra.md", "---\ntype: session\n---\n")
            files = list(walk_project(root))
            v = detect_naming_violations(files)
            self.assertTrue(any("session" in x["issue"].lower() for x in v))


# ============================================================
# Wikilink form + broken
# ============================================================


class TestDetectWikilinkFormViolations(unittest.TestCase):

    def test_markdown_link_to_vault_md_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "target.md", "---\ntype: note\n---\n# T")
            _write_file(root / "src.md", "---\ntype: note\n---\n\nSee [target](target.md).")
            files = list(walk_project(root))
            idx = build_vault_index(root)
            v = detect_wikilink_form_violations(files, idx)
            self.assertEqual(len(v), 1)
            self.assertEqual(v[0]["path"], "target.md")

    def test_external_md_link_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "src.md", "---\ntype: note\n---\n\nSee [doc](nonexistent.md).")
            files = list(walk_project(root))
            idx = build_vault_index(root)
            self.assertEqual(detect_wikilink_form_violations(files, idx), [])


class TestDetectBrokenWikilinks(unittest.TestCase):

    def test_embeds_and_heading_links_not_broken(self):
        # ![[img.png]] (attachment) and [[#Head]] (same-file) are uncheckable,
        # not broken — they used to be false positives.
        from _vault_walk import extract_wikilinks
        import types
        f = types.SimpleNamespace(
            rel_path=Path("notes/n.md"),
            wikilinks=extract_wikilinks("![[img.png]] [[#Head]] [[real]] [[missing]]"),
        )
        out = detect_broken_wikilinks([f], {"real.md", "real"})
        self.assertEqual(out["total_wikilinks"], 2)      # only checkable ones counted
        self.assertEqual(out["broken_count"], 1)
        self.assertEqual(out["samples"][0]["target"], "missing")

    def test_counts_broken(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "target.md", "---\ntype: note\n---\n")
            _write_file(root / "src.md",
                "---\ntype: note\n---\n\n"
                "Real: [[target]]\n"
                "Broken: [[no-such-target]]\n"
            )
            files = list(walk_project(root))
            idx = build_vault_index(root)
            result = detect_broken_wikilinks(files, idx)
            self.assertEqual(result["total_wikilinks"], 2)
            self.assertEqual(result["broken_count"], 1)


# ============================================================
# Doc-decision flags
# ============================================================


class TestDetectDocDecisionFlags(unittest.TestCase):

    def test_decision_at_root_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_file(root / "2026-05-26-misplaced.md", "---\ntype: decision\n---\n")
            files = list(walk_project(root))
            flags = detect_doc_decision_flags(files)
            self.assertEqual(len(flags), 1)


# ============================================================
# End-to-end run_scan
# ============================================================


class TestRunDream(unittest.TestCase):

    def test_clean_project_no_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_project(root)
            (root / "decisions").mkdir()
            _write_file(root / "decisions" / "2026-05-26-test.md", "---\ntype: decision\n---\n")
            _write_file(root / "decisions" / "2026-05-25-test.md", "---\ntype: decision\n---\n")
            _write_file(root / "decisions" / "_index.md", "---\ntype: index\n---\n# Decisions")
            report = run_scan(root, root)
            self.assertEqual(report["meta"]["project_slug"], "test")
            self.assertEqual(report["meta"]["project_type"], "coding")
            self.assertEqual(report["summary"]["drift_items"], 0)

    def test_dirty_project_drift_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_project(root)
            # A frontmatter value the standards say to omit rather than write
            _write_file(root / "a.md", "---\ntype: note\nsession: null\n---\n")
            # Add a non-canonical type
            _write_file(root / "b.md", "---\ntype: api-ref\n---\n")
            report = run_scan(root, root)
            self.assertGreater(report["summary"]["drift_items"], 0)
            self.assertGreater(len(report["frontmatter_drift"]), 0)
            self.assertGreater(report["type_drift"]["non_canonical_count"], 0)

    def test_emits_serializable_json(self):
        """The full report must round-trip through json.dumps without errors."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_project(root)
            _write_file(root / "a.md", "---\ntype: note\nsession: null\n---\n")
            report = run_scan(root, root)
            payload = json.dumps(report, default=str)
            roundtrip = json.loads(payload)
            self.assertEqual(roundtrip["meta"]["project_slug"], "test")


class TestArtefactNaming(unittest.TestCase):

    def test_canvas_base_kebab_case_enforced(self):
        # draw.md promises strict kebab-case for .canvas/.base — this is the
        # check that makes that promise true.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "canvases").mkdir(parents=True)
            (root / "bases").mkdir(parents=True)
            (root / "canvases" / "user-flow.canvas").write_text("{}")
            (root / "canvases" / "MyCoolCanvas.canvas").write_text("{}")
            (root / "bases" / "research_targets.base").write_text("")
            v = detect_artefact_naming(root)
            issues = {x["file"]: x["issue"] for x in v}
            self.assertNotIn("canvases/user-flow.canvas", issues)
            self.assertIn("canvases/MyCoolCanvas.canvas", issues)
            self.assertIn("bases/research_targets.base", issues)
            self.assertIn("kebab-case", issues["canvases/MyCoolCanvas.canvas"])

    def test_templates_and_legacy_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "templates").mkdir(parents=True)
            (root / "_legacy").mkdir(parents=True)
            (root / "templates" / "BigScaffold.canvas").write_text("{}")
            (root / "_legacy" / "Old Canvas.canvas").write_text("{}")
            self.assertEqual(detect_artefact_naming(root), [])

    def test_include_legacy_scans_legacy_artefacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "_legacy").mkdir(parents=True)
            (root / "_legacy" / "Old Canvas.canvas").write_text("{}")
            self.assertEqual(detect_artefact_naming(root), [])
            v = detect_artefact_naming(root, include_legacy=True)
            self.assertEqual(len(v), 1)
            self.assertIn("Old Canvas.canvas", v[0]["file"])

    def test_artefact_naming_lands_in_run_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_project(root)
            (root / "canvases").mkdir()
            (root / "canvases" / "BadName.canvas").write_text("{}")
            report = run_scan(root, root)
            files = [x["file"] for x in report["naming_violations"]]
            self.assertIn("canvases/BadName.canvas", files)


class TestRamasseCost(unittest.TestCase):

    def test_estimate_only_is_cost_only_and_stat_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "brief.md").write_text(
                "---\ntype: project\nslug: t\nproject_type: coding\nstatus: active\n---\n\n# T\n")
            (root / "notes").mkdir()
            (root / "notes" / "big.md").write_text("x" * 8000)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = ramasse_cli(["--project-dir", str(root), "--estimate-only"])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(set(payload), {"scope", "cost"})  # scope null when unscoped
            self.assertGreaterEqual(payload["cost"]["est_read_tokens"], 2000)

    def test_normal_run_includes_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "brief.md").write_text(
                "---\ntype: project\nslug: t\nproject_type: coding\nstatus: active\n---\n\n# T\n")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = ramasse_cli(["--project-dir", str(root)])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertIn("cost", payload)
            self.assertIn("summary", payload)


class TestFolderScope(unittest.TestCase):
    """--folder mirrors dream's: contained subtree walk, scope named in the
    report, subtree-honest cost. One ramasse-specific rule: folder drift is a
    question about the project ROOT'S shape, so a scoped run skips it rather
    than answering it against a fraction of the folders."""

    def _project(self, root: Path) -> None:
        (root / "brief.md").parent.mkdir(parents=True, exist_ok=True)
        (root / "brief.md").write_text(
            "---\ntype: project\nslug: t\nproject_type: coding\n"
            "status: active\n---\n\n# T\n")
        notes = root / "notes"
        notes.mkdir()
        # A §4 naming violation inside the scope (doc filename not UPPERCASE)
        # and a sibling violation outside it.
        (notes / "bad-doc.md").write_text(
            "---\ntype: doc\ntitle: B\nupdated: 2026-01-01\n"
            "tags:\n  - doc\n---\n\nN\n")
        docs = root / "docs"
        docs.mkdir()
        (docs / "also-bad.md").write_text(
            "---\ntype: doc\ntitle: A\nupdated: 2026-01-01\n"
            "tags:\n  - doc\n---\n\nD\n" + "y" * 6000)

    def _run(self, root: Path, *extra: str) -> tuple[int, dict]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            rc = ramasse_cli(["--project-dir", str(root), *extra])
        out = buf.getvalue()
        return rc, (json.loads(out) if rc == 0 and out.strip() else {})

    def test_scoped_run_sees_only_the_subtree_and_names_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            rc, report = self._run(root, "--folder", "notes")
            self.assertEqual(rc, 0)
            self.assertEqual(report["scope"], "notes")
            names = json.dumps(report["naming_violations"])
            self.assertIn("bad-doc.md", names)
            self.assertNotIn("also-bad.md", names)

    def test_scoped_run_skips_root_shape_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            (root / "unexpected-folder").mkdir()
            _, full = self._run(root)
            _, scoped = self._run(root, "--folder", "notes")
            self.assertTrue(full["folder_drift"])          # root question, full run answers
            self.assertEqual(scoped["folder_drift"], [])   # scoped run declines it

    def test_cost_estimate_is_the_subtrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            _, scoped = self._run(root, "--folder", "notes")
            _, full = self._run(root)
            self.assertLess(scoped["cost"]["est_read_tokens"],
                            full["cost"]["est_read_tokens"])

    def test_escape_is_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proj"
            self._project(root)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc, _ = self._run(root, "--folder", "..")
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
