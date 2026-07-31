"""Tests for adjudant/scripts/graph.py — mermaid scaffolds from vault data."""

import json
import tempfile
import unittest
from pathlib import Path

from graph import (
    _q,
    board_graph,
    fenced,
    relations_graph,
    tiers_graph,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class TestLabelSanitiser(unittest.TestCase):
    """`_q` is the single choke point every label passes through. Each branch
    gets its own assertion: the audit found the newline branch survived being
    deleted because only the quote branch was ever exercised."""

    def test_empty_label_falls_back_to_a_placeholder(self):
        # mermaid refuses to parse `n0[""]`, and ONE such label kills the whole
        # fence — not just that node.
        for raw in ("", "   ", "\n", "\t \n"):
            self.assertEqual(_q(raw), '"(untitled)"', f"empty label {raw!r}")

    def test_angle_brackets_and_ampersands_are_entity_escaped(self):
        # mermaid renders flowchart labels as HTML (htmlLabels defaults to
        # true), so a raw `<br>` is consumed by the renderer instead of shown.
        self.assertEqual(_q("fix <br> handling"), '"fix &lt;br&gt; handling"')
        self.assertEqual(_q("a & b"), '"a &amp; b"')
        # `&` escapes FIRST, or `<` would become `&amp;lt;`
        self.assertEqual(_q("a <b> & c"), '"a &lt;b&gt; &amp; c"')

    def test_newlines_collapse_so_a_label_stays_one_line(self):
        self.assertEqual(_q("a\nb"), '"a b"')
        self.assertEqual(_q("a\r\nb"), '"a b"')
        self.assertEqual(_q("a\rb"), '"a b"')

    def test_double_quotes_downgrade_to_single(self):
        self.assertEqual(_q('say "hi"'), "\"say 'hi'\"")


class TestRelations(unittest.TestCase):

    def _project(self, root: Path) -> Path:
        _write(root / "brief.md",
               "---\ntype: project\n---\n# P\n\nSee [[decisions/2026-01-01-choose-x]] and [[notes/idea]].\n")
        _write(root / "decisions" / "2026-01-01-choose-x.md",
               "---\ntype: decision\n---\n# Choose X\n\nBack to [[brief]].\n")
        _write(root / "notes" / "idea.md", "---\ntype: note\n---\n# Idea\n")
        _write(root / "sessions" / "2026-01-01.md", "---\ntype: session\n---\n- 10:00 · [[brief]]\n")
        _write(root / "sessions" / "2026-01-02.md", "---\ntype: session\n---\n- 11:00 · x\n")
        return root

    def test_nodes_edges_and_grouping(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = relations_graph(self._project(Path(tmp)))
            self.assertTrue(g.startswith("flowchart LR"))
            self.assertIn('"brief"', g)
            self.assertIn('"2026-01-01-choose-x"', g)
            # sessions/ collapses into ONE group node with a count
            self.assertIn('"sessions/ (2 notes)"', g)
            self.assertNotIn("2026-01-02", g)
            self.assertIn("-->", g)                       # edges exist
            self.assertIn("classDef project", g)          # role styling stamped
            self.assertIn("classDef group", g)

    def test_edges_are_deduped_and_no_self_loops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md",
                   "---\ntype: project\n---\n[[notes/a]] [[notes/a]] [[brief]]\n")
            _write(root / "notes" / "a.md", "---\ntype: note\n---\n# A\n")
            g = relations_graph(root)
            self.assertEqual(g.count("-->"), 1)  # dedup + self-loop dropped

    def test_max_nodes_cap_drops_leaves_with_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
            for i in range(12):
                _write(root / "notes" / f"leaf-{i:02d}.md", "---\ntype: note\n---\n# L\n")
            g = relations_graph(root, max_nodes=5)
            node_lines = [ln for ln in g.splitlines() if ln.strip().startswith("n") and "[" in ln]
            self.assertLessEqual(len(node_lines), 5)
            self.assertIn("omitted", g)                   # no silent truncation
            self.assertIn('"brief"', g)                   # the brief always survives

    def test_labels_with_quotes_are_sanitized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / 'a "quoted" name.md', "---\ntype: note\n---\n# Q\n")
            g = relations_graph(root)
            self.assertNotIn('""', g)          # every label is non-empty
            self.assertIn("'quoted'", g)

    def test_empty_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = relations_graph(Path(tmp))
            self.assertIn("no vault files found", g)


class TestAliasResolution(unittest.TestCase):

    def test_real_note_beats_group_node_for_same_stem(self):
        # dreams/x.md and notes/x.md share a stem: [[x]] must edge to the real
        # note, never be absorbed by the dreams/ group (walk-order trap).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", "---\ntype: project\n---\n[[2026-01-01-review]]\n")
            _write(root / "dreams" / "2026-01-01-review.md", "---\ntype: dream-report\n---\n# D\n")
            _write(root / "notes" / "2026-01-01-review.md", "---\ntype: note\n---\n# N\n")
            g = relations_graph(root)
            import re as _re
            nodes = dict(_re.findall(r'(n\d+)\[("[^"]+")\]', g))
            note_id = next(k for k, v in nodes.items() if v == '"2026-01-01-review"')
            brief_id = next(k for k, v in nodes.items() if v == '"brief"')
            group_id = next(k for k, v in nodes.items() if v.startswith('"dreams/'))
            self.assertIn(f"{brief_id} --> {note_id}", g)      # edge to the real note
            self.assertNotIn(f"{brief_id} --> {group_id}", g)  # not absorbed by the group

    def test_duplicate_stems_get_folder_disambiguated_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "notes" / "setup.md", "---\ntype: note\n---\n# A\n")
            _write(root / "docs" / "setup.md", "---\ntype: doc\n---\n# B\n")
            g = relations_graph(root)
            self.assertIn('"notes/setup"', g)
            self.assertIn('"docs/setup"', g)

    def test_broken_path_qualified_link_makes_no_edge(self):
        # [[archive/setup]] is broken (no archive/setup.md): must NOT invent
        # an edge to notes/setup.md via the basename fallback.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", "---\ntype: project\n---\n[[archive/setup]]\n")
            _write(root / "notes" / "setup.md", "---\ntype: note\n---\n# S\n")
            g = relations_graph(root)
            self.assertNotIn("-->", g)

    def test_vault_rooted_link_resolves_via_basename(self):
        # [[projects/slug/notes/setup]] is vault-rooted: basename fallback OK.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "brief.md", "---\ntype: project\n---\n[[projects/slug/notes/setup]]\n")
            _write(root / "notes" / "setup.md", "---\ntype: note\n---\n# S\n")
            g = relations_graph(root)
            self.assertIn("-->", g)


class TestBoard(unittest.TestCase):

    def test_board_snapshot_subgraphs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck = {
                "columns": [{"id": "backlog", "name": "Backlog"}, {"id": "done", "name": "Done"}],
                "cards": [
                    {"id": "T-1", "title": "First thing", "column": "backlog"},
                    {"id": "T-2", "title": "Shipped thing", "column": "done"},
                ],
            }
            _write(root / "board" / "board-data.json", json.dumps(deck))
            g = board_graph(root)
            self.assertIn('subgraph col0["Backlog"]', g)
            self.assertIn('"T-1 · First thing"', g)
            self.assertIn('"T-2 · Shipped thing"', g)

    def test_orphan_cards_get_their_own_subgraph(self):
        # Cards in a removed/unknown column must not vanish from a snapshot;
        # integer ids in hand-edited decks must still match (str both sides).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck = {
                "columns": [{"id": 1, "name": "Only"}],
                "cards": [
                    {"id": "T-1", "title": "Here", "column": 1},
                    {"id": "T-9", "title": "Lost lane", "column": "old-lane"},
                ],
            }
            _write(root / "board" / "board-data.json", json.dumps(deck))
            g = board_graph(root)
            self.assertIn('"T-1 · Here"', g)              # int column matched
            self.assertIn("orphaned", g)
            self.assertIn('"T-9 · Lost lane"', g)          # surfaced, not dropped

    def test_empty_column_name_and_card_id_never_emit_an_empty_label(self):
        # One `[""]` anywhere makes mermaid reject the ENTIRE fence.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck = {
                "columns": [{"id": "wip", "name": ""}],
                "cards": [{"id": "", "title": "", "column": "wip"}],
            }
            _write(root / "board" / "board-data.json", json.dumps(deck))
            g = board_graph(root)
            self.assertNotIn('""', g)
            self.assertIn("(untitled)", g)

    def test_card_title_with_a_newline_stays_on_one_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def _lines(title: str) -> int:
                deck = {"columns": [{"id": "b", "name": "B"}],
                        "cards": [{"id": "T-1", "title": title, "column": "b"}]}
                _write(root / "board" / "board-data.json", json.dumps(deck))
                return len(board_graph(root).splitlines())
            # A newline in the title must not split the node onto two lines —
            # that is what terminates the surrounding ```mermaid fence early.
            self.assertEqual(_lines("fix\nthe widget"), _lines("fix the widget"))

    def test_card_title_with_angle_brackets_is_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck = {"columns": [{"id": "b", "name": "B"}],
                    "cards": [{"id": "T-3", "title": "fix <br> handling", "column": "b"}]}
            _write(root / "board" / "board-data.json", json.dumps(deck))
            g = board_graph(root)
            self.assertNotIn("<br>", g)
            self.assertIn("&lt;br&gt;", g)

    def test_missing_deck_raises_with_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError) as ctx:
                board_graph(Path(tmp))
            self.assertIn("scaffold", str(ctx.exception))


class TestTiersAndFence(unittest.TestCase):

    def test_tiers_static_diagram(self):
        g = tiers_graph()
        self.assertTrue(g.startswith("stateDiagram-v2"))
        for verb in ("tidy", "ramasse", "dream"):
            self.assertIn(verb, g)

    def test_fenced_block_shape(self):
        block = fenced("flowchart LR\n  a --> b\n")
        self.assertTrue(block.startswith("```mermaid\n"))
        self.assertTrue(block.endswith("```\n"))


if __name__ == "__main__":
    unittest.main()
