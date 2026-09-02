"""Tests for adjudant/scripts/graph.py — mermaid scaffolds from vault data."""

import contextlib
import io
import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import graph
from graph import (
    _q,
    board_graph,
    cli_main,
    fenced,
    relations_graph,
    tiers_graph,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    """cli_main with stdout/stderr captured. Returns (rc, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli_main(argv)
    return rc, out.getvalue(), err.getvalue()


def _baks(directory: Path) -> list[Path]:
    """The dot-prefixed backups graph.py leaves beside an --out target."""
    return sorted(p for p in directory.iterdir() if p.name.endswith(".bak"))


class _FrozenClock:
    """A `datetime` stand-in whose `now()` never advances, so two backups in a
    row genuinely collide on the same timestamp."""

    @staticmethod
    def now() -> datetime:
        return datetime(2026, 7, 31, 12, 0, 0)


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

    def test_project_prefixed_link_resolves_project_relative(self):
        # Since v3 the session log writes zone-less links: [[{slug}/notes/a.md]]
        # rather than [[projects/{slug}/notes/a.md]], so a shelf move cannot
        # break them. The project folder's own name is not part of a
        # project-relative path — strip it, or every session-log edge vanishes.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
            _write(root / "sessions" / "2026-09-01.md",
                   "---\ntype: session\n---\n- 10:00 · Added: [[demo/notes/setup.md]]\n")
            _write(root / "notes" / "setup.md", "---\ntype: note\n---\n# S\n")
            g = relations_graph(root)
            nodes = dict(re.findall(r'(n\d+)\[("[^"]+")\]', g))
            setup_id = next(k for k, v in nodes.items() if v == '"setup"')
            group_id = next(k for k, v in nodes.items() if v.startswith('"sessions/'))
            self.assertIn(f"{group_id} --> {setup_id}", g)

    def test_broken_project_prefixed_link_makes_no_edge(self):
        # Stripping the project prefix must resolve EXACTLY, never fall through
        # to the basename guess: [[demo/archive/setup]] has no target.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            _write(root / "brief.md", "---\ntype: project\n---\n[[demo/archive/setup]]\n")
            _write(root / "notes" / "setup.md", "---\ntype: note\n---\n# S\n")
            g = relations_graph(root)
            self.assertNotIn("-->", g)



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


class TestBoardCapAndStyling(unittest.TestCase):
    """draw.md, content-mermaid.md and mermaid-generation-rules all promise
    graph.py output is node-capped and classDef-styled. Board mode used to do
    neither, and `--max-nodes` was silently ignored there."""

    def _deck(self, root: Path, n_cards: int, n_cols: int = 4) -> Path:
        cols = [{"id": f"c{i}", "name": f"Lane {i}"} for i in range(n_cols)]
        cards = [{"id": f"T-{i}", "title": f"card {i}", "column": f"c{i % n_cols}"}
                 for i in range(n_cards)]
        _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
        _write(root / "board" / "board-data.json",
               json.dumps({"columns": cols, "cards": cards}))
        return root

    @staticmethod
    def _card_nodes(g: str) -> list[str]:
        return [ln for ln in g.splitlines() if re.match(r"^\s+c\d+\[", ln)]

    def test_card_nodes_are_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._deck(Path(tmp).resolve(), 200)
            g = board_graph(root, max_nodes=30)
            self.assertLessEqual(len(self._card_nodes(g)), 30)
            self.assertIn("omitted", g)

    def test_the_cap_is_per_lane_so_no_lane_disappears(self):
        # A cap that simply stopped at 30 cards would empty the terminal lane
        # entirely, which is the lane a snapshot is usually read for.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._deck(Path(tmp).resolve(), 200, n_cols=4)
            g = board_graph(root, max_nodes=12)
            for i in range(4):
                lane = g.split(f'subgraph col{i}[')[1].split("  end")[0]
                self.assertTrue(self._card_nodes(lane), f"lane {i} lost every card")

    def test_role_classdefs_are_stamped_and_the_palette_stays_small(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._deck(Path(tmp).resolve(), 40, n_cols=8)
            g = board_graph(root, max_nodes=30)
            classdefs = [ln for ln in g.splitlines() if ln.strip().startswith("classDef ")]
            self.assertTrue(classdefs)
            # mermaid-generation-rules section 5: palette of 6 or fewer
            self.assertLessEqual(len(classdefs), 6)
            self.assertTrue(any(ln.strip().startswith("class c") for ln in g.splitlines()),
                            "no node was actually stamped with its role")

    def test_orphans_are_capped_and_styled_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            deck = {"columns": [{"id": "b", "name": "B"}],
                    "cards": [{"id": f"T-{i}", "title": f"c{i}", "column": "gone"}
                              for i in range(50)]}
            _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
            _write(root / "board" / "board-data.json", json.dumps(deck))
            g = board_graph(root, max_nodes=10)
            self.assertIn("orphaned", g)
            self.assertLessEqual(len(self._card_nodes(g)), 10)
            self.assertIn("classDef orphan", g)

    def test_every_lane_keeps_one_card_when_lanes_outnumber_the_cap(self):
        # 8 lanes at --max-nodes 4 makes per-lane share 4 // 8 == 0. Without
        # the floor of one, the snapshot comes back as eight named but empty
        # lanes with every card counted as omitted: a diagram that says the
        # board is empty when it is full.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._deck(Path(tmp).resolve(), 40, n_cols=8)
            g = board_graph(root, max_nodes=4)
            for i in range(8):
                lane = g.split(f"subgraph col{i}[")[1].split("  end")[0]
                self.assertTrue(self._card_nodes(lane), f"lane {i} lost every card")

    def test_an_empty_deck_is_a_named_diagram_not_a_traceback(self):
        # reference/board.md invites hand-editing board-data.json, so a deck
        # with no columns AND no cards is reachable. It used to divide the cap
        # by a lane count of zero. It must come back as a diagram that says it
        # is empty, the way relations mode names its own empty case.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
            _write(root / "board" / "board-data.json",
                   json.dumps({"columns": [], "cards": []}))
            rc, so, err = _run_cli(["--mode", "board", "--project-dir", str(root)])
            self.assertEqual(rc, 0, err)
            self.assertNotIn("Traceback", err)
            self.assertIn("empty deck", so)
            self.assertNotIn('""', so)          # even the placeholder is quoted

    def test_an_uncapped_deck_is_emitted_whole_with_no_omission_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._deck(Path(tmp).resolve(), 8)
            g = board_graph(root, max_nodes=30)
            self.assertEqual(len(self._card_nodes(g)), 8)
            self.assertNotIn("omitted", g)

    def test_cli_threads_max_nodes_into_board_mode_and_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._deck(Path(tmp).resolve(), 200)
            rc, so, err = _run_cli(
                ["--mode", "board", "--project-dir", str(root), "--max-nodes", "30"])
            self.assertEqual(rc, 0, err)
            self.assertLessEqual(len(self._card_nodes(so)), 30)
            self.assertIn("of 200 card(s) omitted", err)
            self.assertIn("--max-nodes 30", err)


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


class TestCliModeDispatch(unittest.TestCase):
    """Each `--mode` is its own path through cli_main. `tiers` takes an early
    branch that must never need a project; `relations` and `board` must both
    resolve one through the breadcrumb first, and resolve it to the VAULT
    project rather than to the code repo they were pointed at."""

    def test_tiers_prints_a_fence_with_no_project_at_all(self):
        # A bare code repo: the same fixture that makes relations exit 1.
        # tiers is static, so it is the one mode that still works there, and
        # draw.md says so. Routing it through the resolver would make that
        # documented claim false.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "pyproject.toml").write_text("[project]\nname='x'\n")
            rc, so, err = _run_cli(["--mode", "tiers", "--project-dir", str(root)])
            self.assertEqual(rc, 0, err)
            self.assertTrue(so.startswith("```mermaid\n"))
            self.assertTrue(so.endswith("```\n"))
            self.assertIn("stateDiagram-v2", so)
            self.assertNotIn("error:", err)

    def test_relations_follows_the_breadcrumb_to_the_vault_project(self):
        # --project-dir names the CODE repo; the graph must be of the vault
        # project the breadcrumb resolves to. Walking the code repo instead
        # would emit an empty graph and still exit 0.
        with tempfile.TemporaryDirectory() as tmp:
            code, vault = _linked_project(Path(tmp).resolve())
            _write(vault / "projects" / "demo" / "notes" / "idea.md",
                   "---\ntype: note\n---\n# Idea\n\nBack to [[brief]].\n")
            rc, so, err = _run_cli(["--mode", "relations", "--project-dir", str(code)])
            self.assertEqual(rc, 0, err)
            self.assertTrue(so.startswith("```mermaid\n"))
            self.assertIn('"brief"', so)
            self.assertIn('"idea"', so)
            self.assertNotIn("no vault files found", so)


class TestCliFlagPlumbing(unittest.TestCase):
    """Flags whose only job is to reach a graph builder. Each is a branch of
    cli_main, and an unexercised cli_main branch is exactly where the --out
    file-destroying bug lived."""

    def test_include_legacy_is_off_by_default_and_on_when_asked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
            _write(root / "_legacy" / "old-note.md", "---\ntype: note\n---\n# Old\n")
            rc, plain, err = _run_cli(["--mode", "relations", "--project-dir", str(root)])
            self.assertEqual(rc, 0, err)
            self.assertNotIn("old-note", plain)
            rc, widened, err = _run_cli(
                ["--mode", "relations", "--project-dir", str(root), "--include-legacy"])
            self.assertEqual(rc, 0, err)
            self.assertIn("old-note", widened)

    def test_board_data_reads_a_deck_outside_the_default_location(self):
        # No board/board-data.json exists here, so an ignored --board-data
        # would exit 1 on a missing deck rather than draw the one named.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
            deck = {"columns": [{"id": "b", "name": "Backlog"}],
                    "cards": [{"id": "T-7", "title": "elsewhere", "column": "b"}]}
            _write(root / "decks" / "snapshot.json", json.dumps(deck))
            rc, so, err = _run_cli(
                ["--mode", "board", "--project-dir", str(root),
                 "--board-data", str(root / "decks" / "snapshot.json")])
            self.assertEqual(rc, 0, err)
            self.assertIn('"T-7 · elsewhere"', so)


class TestCliErrorHandling(unittest.TestCase):
    """Every reachable bad input must produce the `error: ...` line the CLI
    emits everywhere else, never a Python traceback. graph.py is shelled out to
    by the skill: a traceback is noise the model has to interpret."""

    def _project(self, root: Path, deck_text: str) -> Path:
        _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
        _write(root / "board" / "board-data.json", deck_text)
        return root

    def _assert_clean_failure(self, root: Path) -> str:
        rc, _so, err = _run_cli(["--mode", "board", "--project-dir", str(root)])
        self.assertEqual(rc, 1)
        self.assertIn("error:", err)
        self.assertNotIn("Traceback", err)
        return err

    def test_deck_root_is_a_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(Path(tmp).resolve(), "[]")
            self.assertIn("JSON object", self._assert_clean_failure(root))

    def test_deck_root_is_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(Path(tmp).resolve(), "null")
            self.assertIn("JSON object", self._assert_clean_failure(root))

    def test_deck_columns_is_not_a_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(Path(tmp).resolve(), '{"columns": "backlog", "cards": []}')
            self.assertIn("arrays", self._assert_clean_failure(root))

    def test_deck_card_is_not_an_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(Path(tmp).resolve(),
                                 '{"columns": [], "cards": ["T-1"]}')
            self.assertIn("JSON object", self._assert_clean_failure(root))

    def test_deck_is_not_json_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(Path(tmp).resolve(), "{not json")
            self._assert_clean_failure(root)

    def test_missing_deck_is_a_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
            self.assertIn("scaffold", self._assert_clean_failure(root))

    def test_unresolvable_project_is_a_friendly_error(self):
        # A code repo with no breadcrumb: the verb must say so, not traceback.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "pyproject.toml").write_text("[project]\nname='x'\n")
            rc, _so, err = _run_cli(["--mode", "relations", "--project-dir", str(root)])
            self.assertEqual(rc, 1)
            self.assertIn("error:", err)
            self.assertNotIn("Traceback", err)

    def test_out_parent_missing_and_outside_the_root_is_an_error_not_a_traceback(self):
        # The audit's second traceback: the --out write sat OUTSIDE the try, so
        # even a caught exception type escaped from there.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            rc, _so, err = _run_cli(
                ["--mode", "tiers", "--project-dir", str(root),
                 "--out", str(root / ".." / "missing" / "dir" / "x.md")])
            self.assertEqual(rc, 1)
            self.assertIn("error:", err)
            self.assertNotIn("Traceback", err)


class TestTruncationIsVisible(unittest.TestCase):
    """A `%%` note inside the fence is a mermaid COMMENT: it is stripped at
    render time, so the reader of a pasted diagram sees a confident, complete
    looking graph that is actually partial. With `--out` the operator never
    even sees the fence text."""

    def _big_project(self, root: Path, n: int = 40) -> Path:
        _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
        for i in range(n):
            _write(root / "notes" / f"leaf-{i:02d}.md", "---\ntype: note\n---\n# L\n")
        return root

    def test_relations_truncation_reaches_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._big_project(Path(tmp).resolve())
            rc, so, err = _run_cli(
                ["--mode", "relations", "--project-dir", str(root), "--max-nodes", "5"])
            self.assertEqual(rc, 0, err)
            self.assertIn("36 of 41", err)         # 40 leaves + the brief
            self.assertIn("--max-nodes 5", err)
            self.assertIn("file(s) omitted", err)   # files here, cards in board mode
            self.assertIn("%%", so)                # the in-fence note stays

    def test_relations_truncation_is_reported_in_out_mode_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._big_project(Path(tmp).resolve())
            rc, _so, err = _run_cli(
                ["--mode", "relations", "--project-dir", str(root),
                 "--max-nodes", "5", "--out", str(root / "r.md")])
            self.assertEqual(rc, 0, err)
            self.assertIn("36 of 41", err)
            self.assertIn("wrote", err)

    def test_an_uncapped_graph_says_nothing_about_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._big_project(Path(tmp).resolve(), n=3)
            rc, _so, err = _run_cli(["--mode", "relations", "--project-dir", str(root)])
            self.assertEqual(rc, 0, err)
            self.assertNotIn("omitted", err)


class TestOutGuards(unittest.TestCase):
    """`--out` is graph.py's ONLY write. It used to be a bare `write_text` on a
    completely unvalidated path: no containment, no existing-file guard, no
    backup, no atomicity. A typo'd `--out` destroyed the target in silence."""

    def test_happy_path_writes_the_fenced_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            out = root / "tiers.md"
            rc, _so, err = _run_cli(
                ["--mode", "tiers", "--project-dir", str(root), "--out", str(out)])
            self.assertEqual(rc, 0, err)
            text = out.read_text()
            self.assertTrue(text.startswith("```mermaid\n"))
            self.assertIn("stateDiagram-v2", text)
            self.assertIn("wrote", err)

    def test_traversal_out_writes_nothing_and_exits_non_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo = root / "repo"
            repo.mkdir()
            victim = root / "victim.md"
            victim.write_text("PRECIOUS\n")
            rc, _so, err = _run_cli(
                ["--mode", "tiers", "--project-dir", str(repo),
                 "--out", str(repo / ".." / "victim.md")])
            self.assertEqual(rc, 1)
            self.assertIn("error:", err)
            self.assertEqual(victim.read_text(), "PRECIOUS\n")

    def test_absolute_out_outside_every_root_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo = root / "repo"
            repo.mkdir()
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            target = elsewhere / "loot.md"
            rc, _so, err = _run_cli(
                ["--mode", "tiers", "--project-dir", str(repo), "--out", str(target)])
            self.assertEqual(rc, 1)
            self.assertIn("error:", err)
            self.assertFalse(target.exists())

    def test_symlink_out_of_the_root_is_refused(self):
        # A string check alone passes here — containment must be tested on the
        # RESOLVED path, exactly as board.py's _is_inside does.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo = root / "repo"
            repo.mkdir()
            outside = root / "outside"
            outside.mkdir()
            (repo / "link").symlink_to(outside, target_is_directory=True)
            rc, _so, err = _run_cli(
                ["--mode", "tiers", "--project-dir", str(repo),
                 "--out", str(repo / "link" / "loot.md")])
            self.assertEqual(rc, 1)
            self.assertIn("error:", err)
            self.assertFalse((outside / "loot.md").exists())

    def test_existing_file_is_not_silently_destroyed(self):
        # The audit's reproduction: `--out <project>/brief.md` replaced the
        # project brief with a raw fence and exited 0.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            brief = root / "brief.md"
            brief.write_text("---\ntype: project\n---\n# P\n")
            rc, _so, err = _run_cli(
                ["--mode", "tiers", "--project-dir", str(root), "--out", str(brief)])
            self.assertEqual(rc, 1)
            self.assertIn("error:", err)
            self.assertEqual(brief.read_text(), "---\ntype: project\n---\n# P\n")
            self.assertEqual(_baks(root), [])      # a refusal spends no backup

    def test_force_backs_the_target_up_before_replacing_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            brief = root / "brief.md"
            brief.write_text("PRECIOUS\n")
            rc, _so, err = _run_cli(
                ["--mode", "tiers", "--project-dir", str(root),
                 "--out", str(brief), "--force"])
            self.assertEqual(rc, 0, err)
            self.assertIn("stateDiagram-v2", brief.read_text())
            baks = _baks(root)
            self.assertEqual(len(baks), 1)
            self.assertEqual(baks[0].read_text(), "PRECIOUS\n")
            self.assertTrue(baks[0].name.startswith("."))   # invisible in Obsidian

    def test_a_second_force_cannot_destroy_the_first_backup(self):
        # board.py's old fixed `board-data.json.bak` was exactly this bug: run
        # two overwrote the only copy of the real file with the destroyed one.
        # The clock is frozen so both backups WANT the same name — the
        # collision loop, not the passage of time, is what has to save them.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            brief = root / "brief.md"
            brief.write_text("PRECIOUS\n")
            with mock.patch.object(graph, "datetime", _FrozenClock):
                for _ in range(2):
                    rc, _so, err = _run_cli(
                        ["--mode", "tiers", "--project-dir", str(root),
                         "--out", str(brief), "--force"])
                    self.assertEqual(rc, 0, err)
            self.assertEqual(len(_baks(root)), 2)
            self.assertTrue(any(b.read_text() == "PRECIOUS\n" for b in _baks(root)),
                            "the original is no longer recoverable from any backup")

    def test_a_failed_write_leaves_the_target_byte_identical(self):
        # atomic_write_text writes a temp and os.replace()s it; a bare
        # write_text truncates the destination FIRST, so a write that fails
        # part-way destroys the file it was replacing. A lone surrogate — which
        # survives json.loads and cannot be encoded to UTF-8 — makes it fail.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            deck = {"columns": [{"id": "b", "name": "B"}],
                    "cards": [{"id": "T-1", "title": "PLACEHOLDER", "column": "b"}]}
            _write(root / "brief.md", "---\ntype: project\n---\n# P\n")
            _write(root / "board" / "board-data.json",
                   json.dumps(deck).replace('"PLACEHOLDER"', '"\\ud800"'))
            out = root / "snapshot.md"
            out.write_text("PRECIOUS\n")
            rc, _so, err = _run_cli(["--mode", "board", "--project-dir", str(root),
                                     "--out", str(out), "--force"])
            self.assertEqual(rc, 1)
            self.assertIn("error:", err)
            self.assertEqual(out.read_text(), "PRECIOUS\n")

    def test_out_pointing_at_a_directory_is_refused_by_name(self):
        # Without the explicit check this still fails, but as a raw
        # `[Errno 21] Is a directory` the caller has to decode.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            target = root / "diagrams"
            target.mkdir()
            rc, _so, err = _run_cli(
                ["--mode", "tiers", "--project-dir", str(root), "--out", str(target)])
            self.assertEqual(rc, 1)
            self.assertIn(f"error: --out {target} is a directory", err)

    def test_missing_parent_inside_the_root_is_created_not_tracebacked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            out = root / "deep" / "nested" / "tiers.md"
            rc, _so, err = _run_cli(
                ["--mode", "tiers", "--project-dir", str(root), "--out", str(out)])
            self.assertEqual(rc, 0, err)
            self.assertIn("stateDiagram-v2", out.read_text())

    def test_tiers_out_may_land_in_the_resolved_vault_project_too(self):
        # tiers needs no project, and a resolution failure there stays
        # non-fatal — but when one DOES resolve it is a legitimate --out
        # destination (draw.md: the tiers fence belongs in a brief or a doc).
        # Skipping the best-effort resolve would refuse this write.
        with tempfile.TemporaryDirectory() as tmp:
            code, vault = _linked_project(Path(tmp).resolve())
            out = vault / "projects" / "demo" / "docs" / "tiers.md"
            rc, _so, err = _run_cli(
                ["--mode", "tiers", "--project-dir", str(code), "--out", str(out)])
            self.assertEqual(rc, 0, err)
            self.assertIn("stateDiagram-v2", out.read_text())

    def test_out_inside_the_resolved_vault_project_is_allowed(self):
        # Containment is two roots: the invocation root AND the vault project
        # the breadcrumb resolves to.
        with tempfile.TemporaryDirectory() as tmp:
            code, vault = _linked_project(Path(tmp).resolve())
            out = vault / "projects" / "demo" / "docs" / "relations.md"
            rc, _so, err = _run_cli(
                ["--mode", "relations", "--project-dir", str(code), "--out", str(out)])
            self.assertEqual(rc, 0, err)
            self.assertIn("flowchart LR", out.read_text())


def _linked_project(root: Path, slug: str = "demo") -> tuple[Path, Path]:
    """A code repo with a `.claude/adjudant` breadcrumb + its vault project."""
    vault = root / "vault"
    (vault / "projects" / slug).mkdir(parents=True)
    _write(vault / "Home.md", "---\ntype: vault-home\n---\n")
    _write(vault / "projects" / slug / "brief.md",
           f"---\ntype: project\nproject_type: coding\nslug: {slug}\n"
           f"status: active\nupdated: 2026-05-01\n---\n\n# Demo\n")
    code = root / "code"
    _write(code / ".claude" / "adjudant",
           f"vault_path: {vault}\nvault_name: vault\nslug: {slug}\nmode: project\n")
    return code, vault


if __name__ == "__main__":
    unittest.main()
