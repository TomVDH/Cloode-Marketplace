"""Tests for adjudant/scripts/truth.py.

Check used to grade shape: 110 frontmatter keys against a schema, 99 failures,
69 of them in a folder adjudant does not own, and nobody acted on any of it.
Every finding here traces to a real failure in the audited vault, and every
one is settled by a file's existence or a date comparison.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from truth import BANDS, Finding, truth_report


def _w(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def _project(tmp: Path, slug: str = "demo") -> Path:
    pdir = tmp / "vault" / "projects" / "active" / slug
    _w(pdir / "brief.md",
       "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n"
       "# Demo\n\nWhat this project is.\n\n"
       "## Where things are\n| | |\n|---|---|\n")
    _w(pdir / "sessions" / "2026-09-01.md", "---\ntype: session\n---\n\n## Log\n")
    return pdir


def _kinds(report) -> list:
    return [f["kind"] for f in report["findings"]]


class TestReportShape(unittest.TestCase):

    def test_bands_are_ordered_by_cost_of_being_wrong(self):
        self.assertEqual(BANDS, ("wrong-now", "going-stale", "worth-a-look"))

    def test_a_clean_project_reports_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertEqual(report["findings"], [])
            self.assertEqual(report["counts"],
                             {"wrong-now": 0, "going-stale": 0, "worth-a-look": 0})
            self.assertGreater(report["checked"], 0)

    def test_findings_are_json_shaped_and_sorted_by_band(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "notes" / "a.md",
               "---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\n"
               "See [[demo/notes/ghost]].\n")
            _w(pdir / "docs" / "old.md",
               "---\ntype: doc\nupdated: 2026-01-01\nverified: 2026-01-01\n---\n\n"
               "# Old\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertTrue(report["findings"])
            for f in report["findings"]:
                self.assertEqual(set(f), {"band", "kind", "file", "detail"})
                self.assertIn(f["band"], BANDS)
            order = [BANDS.index(f["band"]) for f in report["findings"]]
            self.assertEqual(order, sorted(order))

    def test_the_memory_folder_is_never_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "memory" / "flat.md",
               "---\nname: x\ndescription: y\ntype: project\n---\n\n"
               "See [[nowhere-at-all]].\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertEqual(report["findings"], [])

    def test_a_generated_page_is_never_nagged_about(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "components" / "gen.md",
               "---\ntype: component\nupdated: 2026-01-01\n"
               "source: build-module-inventory.py\n---\n\n"
               "See [[demo/notes/ghost]].\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("broken-wikilink", _kinds(report))


class TestNamesSomethingThatIsNotThere(unittest.TestCase):

    def test_broken_wikilink(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "notes" / "a.md",
               "---\ntype: note\ncreated: 2026-09-01\nupdated: 2026-09-01\n---\n\n"
               "Real: [[demo/brief]]. Ghost: [[demo/notes/ghost]].\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            broken = [f for f in report["findings"] if f["kind"] == "broken-wikilink"]
            self.assertEqual(len(broken), 1)
            self.assertEqual(broken[0]["file"], "notes/a.md")
            self.assertEqual(broken[0]["band"], "wrong-now")
            self.assertIn("demo/notes/ghost", broken[0]["detail"])

    def test_an_embed_is_not_a_broken_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "notes" / "a.md",
               "---\ntype: note\ncreated: 2026-09-01\nupdated: 2026-09-01\n---\n\n"
               "![[diagram.png]]\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            self.assertNotIn("broken-wikilink", _kinds(report))

    def test_superseded_by_pointing_at_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "decisions" / "2026-08-01-a.md",
               "---\ntype: decision\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: superseded\nsuperseded_by: \"[[demo/decisions/nope]]\"\n---\n\n"
               "# A\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"]
                    if f["kind"] == "superseded-target-missing"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["file"], "decisions/2026-08-01-a.md")

    def test_a_card_citing_a_spec_that_was_never_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _project(Path(tmp))
            _w(pdir / "specs" / "spec-018-page-spinup.md",
               "---\ntype: spec\nstatus: agreed\ncreated: 2026-08-01\n"
               "updated: 2026-08-30\nverified: 2026-08-30\n---\n\n# SPEC-018\n")
            _w(pdir / "tasks" / "real.md",
               "---\ntype: task\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: doing\nspec: \"[[demo/specs/spec-018-page-spinup|SPEC-018]]\"\n"
               "---\n\n# Real\n")
            _w(pdir / "tasks" / "phantom.md",
               "---\ntype: task\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: doing\nspec: \"[[demo/specs/spec-999-nope|SPEC-999]]\"\n"
               "---\n\n# Phantom\n")
            report = truth_report(pdir, vault=Path(tmp) / "vault",
                                  today=date(2026, 9, 1))
            hits = [f for f in report["findings"] if f["kind"] == "task-spec-missing"]
            self.assertEqual([h["file"] for h in hits], ["tasks/phantom.md"])

    def test_a_frontmatter_link_written_without_quotes_still_resolves(self):
        # `superseded_by: [[demo/decisions/a]]` is what Obsidian's Properties
        # editor and a hand-written YAML line both produce, and the
        # frontmatter parser reads the brackets as a list: ['[demo/…/a]'].
        # Reported as broken, that is a wrong-now finding on a working link,
        # in the band that costs the most to get wrong.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            _w(pdir / "decisions" / "2026-08-01-a.md",
               "---\ntype: decision\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: active\n---\n\n# A\n")
            _w(pdir / "decisions" / "2026-08-02-b.md",
               "---\ntype: decision\ncreated: 2026-08-02\nupdated: 2026-08-02\n"
               "status: superseded\n"
               "superseded_by: [[demo/decisions/2026-08-01-a]]\n---\n\n# B\n")
            _w(pdir / "specs" / "spec-018.md",
               "---\ntype: spec\nstatus: agreed\ncreated: 2026-08-01\n"
               "updated: 2026-08-01\nverified: 2026-08-01\n---\n\n# S\n")
            _w(pdir / "tasks" / "t.md",
               "---\ntype: task\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: doing\nspec: [[demo/specs/spec-018|SPEC-018]]\n---\n\n# T\n")
            report = truth_report(pdir, vault=root / "vault", today=date(2026, 9, 1))
            self.assertEqual(report["findings"], [])

    def test_an_unquoted_frontmatter_link_that_is_broken_is_still_reported(self):
        # The other direction, and the one that matters: reading the unquoted
        # form must not be a way to stop checking it.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            _w(pdir / "decisions" / "2026-08-02-b.md",
               "---\ntype: decision\ncreated: 2026-08-02\nupdated: 2026-08-02\n"
               "status: superseded\nsuperseded_by: [[demo/decisions/nope]]\n---\n\n# B\n")
            _w(pdir / "tasks" / "t.md",
               "---\ntype: task\ncreated: 2026-08-01\nupdated: 2026-08-01\n"
               "status: doing\nspec: [[demo/specs/spec-999-nope|SPEC-999]]\n---\n\n# T\n")
            report = truth_report(pdir, vault=root / "vault", today=date(2026, 9, 1))
            self.assertEqual(sorted(_kinds(report)),
                             ["superseded-target-missing", "task-spec-missing"])
            detail = [f["detail"] for f in report["findings"]
                      if f["kind"] == "superseded-target-missing"][0]
            self.assertIn("demo/decisions/nope", detail)

    def test_an_unfilled_optional_link_is_not_a_finding(self):
        # The decision, spec and task templates all ship the field present and
        # empty, with a `# optional` comment. Every shape that reaches the
        # parser from one of those has to read as "nothing to check".
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            for i, value in enumerate(("", " []", ' ""', " '  '")):
                _w(pdir / "decisions" / f"2026-08-0{i + 1}-d.md",
                   f"---\ntype: decision\ncreated: 2026-08-01\n"
                   f"updated: 2026-08-01\nstatus: active\n"
                   f"superseded_by:{value}\n---\n\n# D\n")
            report = truth_report(pdir, vault=root / "vault", today=date(2026, 9, 1))
            self.assertEqual(report["findings"], [])


    def test_a_brief_repo_path_that_no_longer_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            real = root / "code"
            real.mkdir()
            _w(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n"
               "# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n"
               f"| Repo | {real} |\n| Deploy | https://example.test |\n")
            self.assertEqual(
                [f["kind"] for f in truth_report(
                    pdir, vault=root / "vault", today=date(2026, 9, 1))["findings"]],
                [])
            _w(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n"
               "# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n"
               f"| Repo | {root / 'moved-away'} |\n")
            report = truth_report(pdir, vault=root / "vault", today=date(2026, 9, 1))
            hits = [f for f in report["findings"] if f["kind"] == "brief-repo-missing"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["band"], "wrong-now")

    def test_a_freshly_rendered_brief_is_not_a_finding(self):
        # `_render.render` leaves an unfilled placeholder as `{Its Name}` on
        # purpose, so a human can see what belongs there. The brief template
        # ships `| Repo | {path or url} |`, so before this guard every project
        # opened its first status run with a wrong-now finding saying the repo
        # had moved. Rendered from the shipped template, not a copy of it, so
        # this keeps holding when the template changes.
        from _render import render
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            _w(pdir / "brief.md",
               render("project",
                      {"created": "2026-09-01", "updated": "2026-09-01",
                       "verified": "2026-09-01"},
                      {"Project Name": "Demo"}))
            report = truth_report(pdir, vault=root / "vault", today=date(2026, 9, 1))
            self.assertEqual(report["findings"], [],
                             "a project reported a lie on the day it was created")

    def test_the_repo_verdict_does_not_depend_on_where_you_ran_it(self):
        # `TomVDH/toolshed` is a plausible answer to "path or url" and is not
        # a claim about this disk. Statting it resolves against the shell's
        # cwd, so the same brief was clean from one directory and wrong-now
        # from another. Only an absolute path is settleable.
        import os
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            (root / "sibling").mkdir()
            _w(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n"
               "# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n"
               "| Repo | sibling |\n")
            before = Path.cwd()
            try:
                for cwd in (before, root):
                    os.chdir(cwd)
                    report = truth_report(pdir, vault=root / "vault",
                                          today=date(2026, 9, 1))
                    self.assertNotIn("brief-repo-missing", _kinds(report),
                                     f"verdict changed with the cwd ({cwd})")
            finally:
                os.chdir(before)


    def test_an_elided_repo_path_is_not_a_finding(self):
        # The brief template's own example writes `~/…/HubSpot - Nightly`.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = _project(root)
            _w(pdir / "brief.md",
               "---\ntype: project\nupdated: 2026-09-01\nverified: 2026-09-01\n---\n\n"
               "# Demo\n\nWhat this project is.\n\n"
               "## Where things are\n| | |\n|---|---|\n"
               "| Repo | ~/…/HubSpot - Nightly |\n")
            report = truth_report(pdir, vault=root / "vault", today=date(2026, 9, 1))
            self.assertNotIn("brief-repo-missing", _kinds(report))


if __name__ == "__main__":
    unittest.main()
