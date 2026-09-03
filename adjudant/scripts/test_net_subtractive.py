"""Acceptance test for plan 3: clean removes more than it adds, always.

The complaint this plan answers, verbatim: the cleanup tier "fills SO much
more crud than it actually cleans". This test makes the opposite a property
of the code.

Two things this file does that the plan's sketch did not, both because the
last acceptance test in this plugin shipped green while being wrong:

It runs every case into `tasks/` as well as `notes/`. Plan 1's `test_no_crud`
only ever wrote to `notes/`, and that single fixture choice hid a live leak
for a whole release. `tasks/` is the folder with its own status vocabulary and
its own hook branch, so it is the folder a regression hides in.

It samples the project WHILE the preview is on disk, not only after. Every
assertion in the sketch ran after `apply_preview`, which ends by deleting the
preview tree — so the ~25 scratch files that started this whole plan would
have been invisible to it. `test_scratch_never_resolves_inside_the_project`
is what actually holds that line; the mid-run sample is what notices if it
ever stops.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import clean
from _vault_walk import build_vault_index
from _vault_write import VaultCreateRefused, VaultWriteGuard

_MODULE_TMP = None
_OLD_TMPDIR = None


def setUpModule():
    """Pin $TMPDIR: clean's preview and backup live under it, and an un-pinned
    run would leave rotated backup dirs in the developer's real temp dir."""
    global _MODULE_TMP, _OLD_TMPDIR
    _OLD_TMPDIR = os.environ.get("TMPDIR")
    _MODULE_TMP = tempfile.mkdtemp(prefix="adjudant-test-net-subtractive-")
    os.environ["TMPDIR"] = _MODULE_TMP


def tearDownModule():
    if _OLD_TMPDIR is None:
        os.environ.pop("TMPDIR", None)
    else:
        os.environ["TMPDIR"] = _OLD_TMPDIR
    if _MODULE_TMP:
        shutil.rmtree(_MODULE_TMP, ignore_errors=True)


# Both folders, every case. See the module docstring.
FOLDERS = ("notes", "tasks")

# `tags:` is the field plan 2 retired from every kind, so it is an unknown
# field both templates reject and the one thing clean is certain to strip.
# That is deliberate: a net-subtractive test whose fixture gives clean nothing
# to remove passes by doing nothing at all.
_BODY = {
    "notes": ("---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
              "tags:\n  - note\n---\n\n# N\n\nbody\n"),
    "tasks": ("---\ntype: task\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
              "status: backlog\ntags:\n  - task\n---\n\n# T\n\nbody\n"),
}


class TestCleanIsNetSubtractive(unittest.TestCase):

    def _project(self, tmp: Path, folder: str = "notes", notes: int = 12) -> Path:
        project = tmp / "vault" / "projects" / "demo"
        (project / folder).mkdir(parents=True)
        for i in range(notes):
            (project / folder / f"n{i}.md").write_text(_BODY[folder])
        return project

    def _count(self, root: Path) -> tuple:
        files = [p for p in root.rglob("*") if p.is_file()]
        return len(files), sum(p.stat().st_size for p in files)

    def _paths(self, root: Path) -> set:
        return {p.relative_to(root) for p in root.rglob("*")}

    def _preview(self, project: Path, deep: bool = False) -> dict:
        # build_preview keeps tidy's signature: (project_dir, vault_index,
        # project_slug). The vault root is two levels up from the project.
        vault = project.parent.parent
        return clean.build_preview(project, build_vault_index(vault),
                                   project.name, deep=deep)

    def _run(self, project: Path, deep: bool = False) -> set:
        """Preview, sample the project while the preview is live, then apply.

        The mid-run sample is the point. `apply_preview` deletes the preview
        tree on its way out, so anything the run wrote into the vault and then
        tidied away is invisible to a before/after comparison.
        """
        clean.write_preview_to_disk(project, self._preview(project, deep=deep))
        mid = self._paths(project)
        clean.apply_preview(project)
        return mid

    def test_file_count_and_bytes_do_not_grow(self):
        for folder in FOLDERS:
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as t:
                project = self._project(Path(t), folder)
                before_n, before_b = self._count(project)
                self._run(project)
                after_n, after_b = self._count(project)
                self.assertLessEqual(after_n, before_n,
                                     "clean added files to the vault")
                self.assertLessEqual(after_b, before_b,
                                     "clean added bytes to the vault")

    def test_nothing_is_created_inside_the_vault(self):
        for folder in FOLDERS:
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as t:
                project = self._project(Path(t), folder)
                before = self._paths(project)
                mid = self._run(project)
                after = self._paths(project)
                self.assertEqual(mid - before, set(),
                                 f"clean staged inside the vault: {sorted(mid - before)}")
                self.assertEqual(after - before, set(),
                                 f"clean created: {sorted(after - before)}")

    def test_deep_pass_is_also_net_subtractive(self):
        for folder in FOLDERS:
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as t:
                project = self._project(Path(t), folder)
                before = self._paths(project)
                before_n, _ = self._count(project)
                mid = self._run(project, deep=True)
                after_n, _ = self._count(project)
                self.assertEqual(mid - before, set(),
                                 f"the deep pass staged inside the vault: "
                                 f"{sorted(mid - before)}")
                self.assertEqual(self._paths(project) - before, set())
                self.assertLessEqual(after_n, before_n)

    def test_the_guard_refuses_a_create(self):
        for folder in FOLDERS:
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as t:
                project = self._project(Path(t), folder)
                with VaultWriteGuard(project) as g:
                    with self.assertRaises(VaultCreateRefused):
                        g.rewrite(project / folder / "_index.md", "# Index\n")

    def test_scratch_never_resolves_inside_the_project(self):
        # The assertion that makes the two above bind. Both compare the vault
        # against itself, so they stay green no matter how much a run writes,
        # as long as it cleans up after itself — which is exactly what the
        # ~25-files-per-run version did.
        for folder in FOLDERS:
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as t:
                project = self._project(Path(t), folder)
                for name, path in (("preview", clean.preview_dir(project)),
                                   ("backup", clean.backup_root(project))):
                    self.assertNotIn(project.resolve(), path.resolve().parents,
                                     f"the {name} tree lives inside the vault: {path}")

    def test_the_pass_actually_removed_something(self):
        # A gate that a do-nothing clean passes is not a gate: every other
        # assertion here is satisfied by proposing no changes at all. The
        # fixture carries a retired `tags:` field, so a working clean strips
        # twelve of them and the byte count must fall, not merely hold.
        for folder in FOLDERS:
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as t:
                project = self._project(Path(t), folder)
                _, before_b = self._count(project)
                change_set = self._preview(project)
                self.assertEqual(
                    sorted(change_set["schema_actions"]),
                    sorted(f"{folder}/n{i}.md" for i in range(12)))
                for rel, act in change_set["schema_actions"].items():
                    self.assertEqual(act.get("dropped"), ["tags"], rel)
                clean.write_preview_to_disk(project, change_set)
                clean.apply_preview(project)
                _, after_b = self._count(project)
                self.assertLess(after_b, before_b, "clean removed nothing")

    def test_a_folder_with_no_index_is_reported_not_filled(self):
        # The single write that made a cleanup verb add more than it removed:
        # a folder with two or more notes and no `_index.md` used to get one
        # generated, then merely reported as a gap. Both are gone: the spec
        # retires every folder index but the two _index_gen writes, and
        # prune_index_files DELETES any other _index.md on the next status
        # run. Asking a reader to hand-build a file the tool then removes is
        # the ceremony this redesign exists to cut.
        for folder in FOLDERS:
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as t:
                project = self._project(Path(t), folder)
                change_set = self._preview(project)
                self.assertNotIn("index_gaps", change_set)
                # Task 8 retired the in-place rebuild entirely: there is no
                # second proposal dict to be empty, because there is no
                # longer any code path that could populate one.
                self.assertNotIn("index_proposals", change_set)
                self._run(project)
                self.assertFalse((project / folder / "_index.md").exists(),
                                 "clean generated an index")

    def test_an_existing_index_with_no_drift_is_left_alone(self):
        # Task 8 retired the in-place rebuild: an `_index.md` that already
        # exists and carries no schema drift now produces no proposal of any
        # kind, which is stronger than "does not grow" — it does not change.
        for folder in FOLDERS:
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as t:
                project = self._project(Path(t), folder)
                existing = ("---\ntype: index\ncreated: 2026-01-01\n"
                            "updated: 2026-01-01\n---\n\n# Entries\n\n## Entries\n\n")
                (project / folder / "_index.md").write_text(existing)
                before = self._paths(project)
                before_n, _ = self._count(project)
                change_set = self._preview(project)
                self.assertNotIn(f"{folder}/_index.md", change_set["file_proposals"])
                clean.write_preview_to_disk(project, change_set)
                clean.apply_preview(project)
                after_n, _ = self._count(project)
                self.assertEqual(after_n, before_n, "clean added files to the vault")
                self.assertEqual(self._paths(project) - before, set())
                self.assertEqual((project / folder / "_index.md").read_text(), existing,
                                 "clean touched an index file it no longer rebuilds")


if __name__ == "__main__":
    unittest.main()
