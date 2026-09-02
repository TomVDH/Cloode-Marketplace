"""Tests for adjudant/scripts/_place.py — the single owner of where a file
goes and how it is linked.

Before v3 three writers each had their own link shape and none agreed. Two of
the three embedded the lifecycle folder, so moving a project between active/
and paused/ broke every link into it — which is what shelf.py's 380-line
vault-wide link rewrite existed to repair.
"""

import tempfile
import unittest
from pathlib import Path

from _place import (
    DATED_KINDS,
    KIND_FOLDER,
    link,
    place,
    project_rel,
)


class TestKindTable(unittest.TestCase):

    def test_fifteen_kinds(self):
        self.assertEqual(len(KIND_FOLDER), 15)

    def test_the_settled_folders(self):
        self.assertEqual(KIND_FOLDER["session"], "sessions")
        self.assertEqual(KIND_FOLDER["decision"], "decisions")
        self.assertEqual(KIND_FOLDER["task"], "tasks")
        self.assertEqual(KIND_FOLDER["note"], "notes")
        self.assertEqual(KIND_FOLDER["doc"], "docs")
        self.assertEqual(KIND_FOLDER["spec"], "specs")
        self.assertEqual(KIND_FOLDER["component"], "components")
        self.assertEqual(KIND_FOLDER["api"], "api")
        self.assertEqual(KIND_FOLDER["schema"], "schemas")
        self.assertEqual(KIND_FOLDER["source"], "sources")
        self.assertEqual(KIND_FOLDER["release"], "releases")
        self.assertEqual(KIND_FOLDER["dream"], "dreams")

    def test_root_kinds_have_no_folder(self):
        for kind in ("project", "handoff", "index"):
            self.assertEqual(KIND_FOLDER[kind], "", kind)

    def test_dated_kinds(self):
        self.assertEqual(DATED_KINDS, frozenset({"session", "decision", "dream"}))


class TestPlace(unittest.TestCase):

    def _project(self, tmp: Path) -> Path:
        p = tmp / "vault" / "projects" / "active" / "demo"
        p.mkdir(parents=True)
        return p

    def test_undated_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            got = place("note", proj, {"slug": "cold-cache-quadratic"})
            self.assertEqual(got, proj / "notes" / "cold-cache-quadratic.md")

    def test_dated_kind_takes_the_date_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            got = place("decision", proj,
                        {"slug": "drop-bucket-a-tags", "date": "2026-09-01"})
            self.assertEqual(
                got, proj / "decisions" / "2026-09-01-drop-bucket-a-tags.md")

    def test_session_is_dated_with_no_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            got = place("session", proj, {"date": "2026-09-01"})
            self.assertEqual(got, proj / "sessions" / "2026-09-01.md")

    def test_root_kinds(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            self.assertEqual(place("project", proj), proj / "brief.md")
            self.assertEqual(place("handoff", proj), proj / "_handoff.md")
            self.assertEqual(place("index", proj), proj / "_index.md")

    def test_one_level_of_grouping_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            got = place("component", proj, {"slug": "button", "group": "modules"})
            self.assertEqual(got, proj / "components" / "modules" / "button.md")
            with self.assertRaises(ValueError):
                place("component", proj, {"slug": "b", "group": "a/b"})
            with self.assertRaises(ValueError):
                place("note", proj, {"slug": "n", "group": "deep"})

    def test_creates_the_folder_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            got = place("note", proj, {"slug": "a"})
            self.assertTrue(got.parent.is_dir())
            self.assertFalse(got.exists(), "place() must not create the file")
            self.assertEqual(sorted(p.name for p in proj.iterdir()), ["notes"],
                             "place() created a folder nobody asked for")

    def test_unknown_kind_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            with self.assertRaises(ValueError):
                place("iteration", proj, {"slug": "x"})

    def test_non_kebab_slug_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            for bad in ("Upper", "with space", "with.dot", "../escape", ""):
                with self.assertRaises(ValueError, msg=bad):
                    place("note", proj, {"slug": bad})

    def test_missing_date_on_a_dated_kind_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            with self.assertRaises(ValueError):
                place("dream", proj, {})

    def test_malformed_date_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._project(Path(tmp))
            with self.assertRaises(ValueError):
                place("session", proj, {"date": "2026-9-1"})


class TestProjectRel(unittest.TestCase):

    def test_drops_the_lifecycle_folder_and_the_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "vault" / "projects" / "active" / "demo"
            (proj / "decisions").mkdir(parents=True)
            f = proj / "decisions" / "2026-09-01-x.md"
            self.assertEqual(project_rel(f, proj), "demo/decisions/2026-09-01-x")

    def test_project_root_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "vault" / "projects" / "paused" / "demo"
            proj.mkdir(parents=True)
            self.assertEqual(project_rel(proj / "brief.md", proj), "demo/brief")

    def test_a_legacy_project_path_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "vault" / "projects" / "demo"
            (proj / "notes").mkdir(parents=True)
            self.assertEqual(project_rel(proj / "notes" / "a.md", proj),
                             "demo/notes/a")

    def test_a_file_outside_the_project_is_loud(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "p"
            proj.mkdir()
            with self.assertRaises(ValueError):
                project_rel(Path(tmp) / "elsewhere.md", proj)


class TestLink(unittest.TestCase):

    def test_the_settled_shape(self):
        self.assertEqual(
            link("hubspot-nightly/decisions/2026-08-12-branch-track",
                 "branch track"),
            "[[hubspot-nightly/decisions/2026-08-12-branch-track|branch track]]")

    def test_no_alias(self):
        self.assertEqual(link("demo/notes/a"), "[[demo/notes/a]]")

    def test_extension_is_stripped(self):
        self.assertEqual(link("demo/notes/a.md"), "[[demo/notes/a]]")

    def test_table_cells_escape_the_separator(self):
        self.assertEqual(link("demo/brief", "demo", in_table=True),
                         "[[demo/brief\\|demo]]")

    def test_a_lifecycle_folder_in_the_target_is_loud(self):
        for zone in ("active", "paused", "finished", "archive"):
            with self.assertRaises(ValueError, msg=zone):
                link(f"{zone}/demo/notes/a")

    def test_a_projects_prefix_is_loud(self):
        with self.assertRaises(ValueError):
            link("projects/demo/notes/a")

    def test_an_empty_target_is_loud(self):
        with self.assertRaises(ValueError):
            link("")

    def test_an_alias_pipe_is_loud(self):
        # An alias carrying a pipe would silently truncate the link.
        with self.assertRaises(ValueError):
            link("demo/notes/a", "a|b")


if __name__ == "__main__":
    unittest.main()
