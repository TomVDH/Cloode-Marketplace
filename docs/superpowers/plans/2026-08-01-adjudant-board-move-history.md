# Adjudant Board Move-History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the board a durable, time-stamped move ledger: every card move (human drag, keyboard, tap, or a merge-induced park) is recorded as an event in `board-data.json`, so a later reader can reconstruct when what moved where.

**Architecture:** A deck-level `history` array of append-only events `{card, from, to, at, by}`, capped at 500. The browser queues events in localStorage (`pending`) and flushes them into the deck's `history` on each confirmed disk write, riding the existing single mutation path (`applyMove`) and its rollback contract. `board.py` preserves `history` across re-seeds, appends `seed` events when a merge parks an orphan, and `status --history N` prints the tail.

**Tech Stack:** Python 3 stdlib only (`board.py` + `unittest` in `test_board.py`); vanilla JS inside the self-contained `templates/board.html`.

## Global Constraints

- Python stdlib only; no new dependencies anywhere (`AGENTS.md`: no compile step, validators via pre-commit).
- Deck `version` stays `1`: `history` is additive and optional; a deck without it means "no ledger yet", never an error.
- `HISTORY_KEEP = 500` exists twice (board.py and templates/board.html) and MUST carry a lockstep comment on both sides.
- Event shape everywhere: `{"card": str, "from": str, "to": str, "at": ISO-8601 str, "by": "ui" | "seed"}`. Browser stamps UTC (`new Date().toISOString()`); Python stamps local-with-offset (`datetime.now().astimezone().isoformat(timespec="seconds")`). Consumers must parse offset-aware; the two shapes are both valid ISO-8601.
- Never hand-edit a scaffolded `board.html` instance; change `templates/board.html` and re-run scaffold (`emit_html` refreshes instances via the template-hash check).
- The v0.25.0 save-honesty contract is law: an event may only claim persistence a backing store confirmed. No history write outside the existing `persist()` / `writeDisk()` paths; the rollback in `applyMove` must also roll back the queued event.
- `python3 adjudant/scripts/validate.py` and the board test suite (`cd adjudant/scripts && python3 -m unittest test_board -v`) pass at every commit; `pre-commit run --all-files` before the release commit.
- Voice: plan and doc prose plain, no glazing; rendered CLI output stays scannable.

## Context for a zero-context engineer

Read these before Task 1; every anchor below is current at v0.26.0 (`15b89f7`):

- `adjudant/skills/adjudant/reference/board.md`: the locked feature spec. The Data model section and "What board does NOT do" both change in Task 4.
- `adjudant/scripts/board.py`: `build_deck` (line ~202) composes a fresh deck; `merge_deck` (~238) is the refresh-without-clobber merge whose docstring explains every rule; `_status_line` (~913) renders one project's terminal status; `cmd_status` (~940) has three call sites of `_status_line`; subparser wiring is in `cli_main` (~1039).
- `adjudant/skills/adjudant/templates/board.html`: since v0.25.0 the browser persists ONLY hand-move overrides `{cardId: {from, to}}` (comment block at ~285 explains why whole-deck snapshots were abandoned). `MOVES_VERSION=2` and the module globals are at ~250. `applyMove` (~507) is the single mutation path: optimistic render, `persist()`, rollback + notice on failure. `writeDisk` (~371) re-reads the disk deck, merges overrides onto it (`mergeMoves`), and writes the reconciled deck; `persist` (~395) reports which store confirmed. `moves=readMoves()` is called at two sites (~710, ~741).
- Why: on 2026-07-31 a user's drags on the tomfolio board reached neither disk nor any later reader, and even after the v0.25.0 save fixes the schema records no *when*. The ledger is the missing half. The overrides map is current-state-only and self-retiring (`recordMove` deletes an override when a card returns to its base lane), so it can never serve as a history.

**Known accepted limits (document, do not fight):**
- Events queued in a browser that never gets a file handle live only in that browser's localStorage. That matches the existing override semantics exactly.
- Moves applied by editing `board/kanban.md` in Obsidian (the v0.23.0 interop surface) are absorbed by the deck without events. Logging those means diffing placements inside `_apply_kanban_placement`; explicitly out of scope, note it in Task 4's doc text.
- Two interleaved `applyMove` calls share the same snapshot-rollback exposure the `moves` undo already has; the pending queue follows the identical pattern, no new guarantee claimed.

---

### Task 1: `history` becomes a first-class deck field (board.py)

**Files:**
- Modify: `adjudant/scripts/board.py` (constants block ~line 62, `build_deck` ~202, `merge_deck` ~238)
- Test: `adjudant/scripts/test_board.py`

**Interfaces:**
- Consumes: existing `merge_deck(existing, fresh)`, `build_deck(project_dir, *, from_tasks, title, ...)`.
- Produces: module constant `HISTORY_KEEP = 500`; helper `_now_iso() -> str`; decks whose `history` key is always present after build/merge. Task 2 reads `deck.get("history")`; Task 3's template writes the same event shape.

- [ ] **Step 1: Write the failing tests**

Append to `adjudant/scripts/test_board.py` (imports: add `HISTORY_KEEP` to the existing `from board import (...)` list):

```python
class TestMoveHistory(unittest.TestCase):
    """Deck-level `history`: an append-only move ledger. Merge preserves it,
    parking an orphan appends a `seed` event, the cap trims oldest first."""

    def _deck(self, cards, **kw):
        d = {"version": 1, "boardId": "p", "title": "P", "subtitle": "s",
             "updated": "2026-01-01", "columns": [], "categories": [], "cards": cards}
        d.update(kw)
        return d

    def test_build_deck_emits_empty_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck = build_deck(Path(tmp), from_tasks=False, title="T")
        self.assertEqual(deck["history"], [])

    def test_merge_preserves_existing_history(self):
        ev = {"card": "X-1", "from": "backlog", "to": "doing",
              "at": "2026-07-31T10:00:00+00:00", "by": "ui"}
        existing = self._deck([{"id": "X-1", "column": "doing", "category": "b", "notes": ""}],
                              history=[ev])
        fresh = self._deck([{"id": "X-1", "column": "backlog", "category": "b", "notes": ""}])
        out = merge_deck(existing, fresh)
        self.assertEqual(out["history"], [ev])

    def test_orphan_park_appends_seed_event(self):
        existing = self._deck([{"id": "X-9", "column": "done", "category": "b",
                                "notes": "", "source": "task"}])
        fresh = self._deck([{"id": "X-1", "column": "backlog", "category": "b", "notes": ""}])
        out = merge_deck(existing, fresh)
        ev = out["history"][-1]
        self.assertEqual((ev["card"], ev["from"], ev["to"], ev["by"]),
                         ("X-9", "done", "icebox", "seed"))
        self.assertIn("T", ev["at"])  # ISO-8601 date/time separator present

    def test_orphan_already_in_icebox_logs_no_repeat_event(self):
        # Reseeding twice must not log a park event per reseed.
        existing = self._deck([{"id": "X-9", "column": "icebox", "category": "b",
                                "notes": "", "source": "task"}])
        fresh = self._deck([{"id": "X-1", "column": "backlog", "category": "b", "notes": ""}])
        out = merge_deck(existing, fresh)
        self.assertEqual(out["history"], [])

    def test_history_trimmed_to_cap_newest_kept(self):
        evs = [{"card": f"X-{i}", "from": "a", "to": "b",
                "at": "2026-07-31T00:00:00+00:00", "by": "ui"}
               for i in range(HISTORY_KEEP + 40)]
        existing = self._deck([], history=evs)
        out = merge_deck(existing, self._deck([]))
        self.assertEqual(len(out["history"]), HISTORY_KEEP)
        self.assertEqual(out["history"][-1], evs[-1])   # newest kept
        self.assertEqual(out["history"][0], evs[40])    # oldest trimmed
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd adjudant/scripts && python3 -m unittest test_board.TestMoveHistory -v`
Expected: FAIL / ERROR on all five (`ImportError: cannot import name 'HISTORY_KEEP'` first; after a stub import, `KeyError: 'history'`).

- [ ] **Step 3: Implement in board.py**

In the constants block (after `BACKUP_KEEP = 5`, ~line 68):

```python
# Deck-level move ledger: append-only {card, from, to, at, by} events, newest
# last, trimmed to the newest HISTORY_KEEP on every write. Lockstep: the same
# constant lives in templates/board.html (HISTORY_KEEP).
HISTORY_KEEP = 500
```

Beside `_today()` (~line 136):

```python
def _now_iso() -> str:
    """Local time with UTC offset, seconds precision. The browser side stamps
    `new Date().toISOString()` (UTC); both are ISO-8601, parse offset-aware."""
    return datetime.now().astimezone().isoformat(timespec="seconds")
```

In `build_deck`, add to the returned dict (after `"cards": cards,`):

```python
        "history": [],
```

In `merge_deck`: initialise `seed_events: list[dict[str, Any]] = []` before the `merged` loop, then replace the orphan branch

```python
        elif cid not in fresh_ids:
            ec = dict(ec)
            if ec.get("source") == "task":
                # Task genuinely disappeared from tasks/ — park it
                ec["column"] = "icebox"
            merged.append(ec)
```

with:

```python
        elif cid not in fresh_ids:
            ec = dict(ec)
            if ec.get("source") == "task" and ec.get("column") != "icebox":
                # Task genuinely disappeared from tasks/ — park it, on the record
                seed_events.append({"card": cid, "from": str(ec.get("column")),
                                    "to": "icebox", "at": _now_iso(), "by": "seed"})
                ec["column"] = "icebox"
            merged.append(ec)
```

At the end of `merge_deck`, before `return out`:

```python
    history = list(existing.get("history") or []) + seed_events
    out["history"] = history[-HISTORY_KEEP:]
```

Extend the `merge_deck` docstring's deck-level sentence: after "custom ``{name: colour}`` mappings on disk are preserved)", append: "``history`` is preserved from disk, gains one ``seed`` event per newly parked orphan, and is trimmed to the newest ``HISTORY_KEEP``."

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd adjudant/scripts && python3 -m unittest test_board -v`
Expected: PASS, including every pre-existing test (the merge tests assert fields they know; none forbids the new key).

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/board.py adjudant/scripts/test_board.py
git commit -m "feat(adjudant): the board deck gains a move-history ledger the merge preserves"
```

---

### Task 2: `status --history N` reads the ledger back

**Files:**
- Modify: `adjudant/scripts/board.py` (`_status_line` ~913, `cmd_status` ~940, `cli_main` status subparser ~1039)
- Test: `adjudant/scripts/test_board.py`

**Interfaces:**
- Consumes: `deck["history"]` as produced by Task 1 (and by Task 3's template).
- Produces: `_status_line(slug, board_dir, history_n=0)` keyword; `board.py status --history N` CLI flag.

- [ ] **Step 1: Write the failing tests**

Append to `TestMoveHistory` in `test_board.py`:

```python
    def test_status_line_renders_history_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / "board"
            bdir.mkdir(parents=True)
            deck = {"version": 1, "boardId": "p", "title": "P", "subtitle": "s",
                    "updated": "2026-07-31",
                    "columns": [{"id": "backlog", "name": "Backlog"}],
                    "categories": [], "cards": [],
                    "history": [{"card": "X-1", "from": "backlog", "to": "done",
                                 "at": "2026-07-31T10:00:00+00:00", "by": "ui"}]}
            (bdir / "board-data.json").write_text(json.dumps(deck))
            line, ok = _status_line("p", bdir, history_n=5)
        self.assertTrue(ok)
        self.assertIn("X-1", line)
        self.assertIn("backlog -> done", line)
        self.assertIn("[ui]", line)

    def test_status_line_history_tolerates_ledgerless_deck(self):
        # Pre-history decks: --history N must degrade, never traceback.
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / "board"
            bdir.mkdir(parents=True)
            deck = {"version": 1, "boardId": "p", "title": "P", "subtitle": "s",
                    "updated": "2026-07-31", "columns": [], "categories": [], "cards": []}
            (bdir / "board-data.json").write_text(json.dumps(deck))
            line, ok = _status_line("p", bdir, history_n=3)
        self.assertTrue(ok)
        self.assertIn("no recorded moves", line)

    def test_status_line_default_prints_no_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / "board"
            bdir.mkdir(parents=True)
            deck = {"version": 1, "boardId": "p", "title": "P", "subtitle": "s",
                    "updated": "2026-07-31", "columns": [], "categories": [], "cards": [],
                    "history": [{"card": "X-1", "from": "a", "to": "b",
                                 "at": "2026-07-31T10:00:00+00:00", "by": "ui"}]}
            (bdir / "board-data.json").write_text(json.dumps(deck))
            line, _ok = _status_line("p", bdir)
        self.assertNotIn("X-1", line)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd adjudant/scripts && python3 -m unittest test_board.TestMoveHistory -v`
Expected: FAIL with `TypeError: _status_line() got an unexpected keyword argument 'history_n'`.

- [ ] **Step 3: Implement**

Change the `_status_line` signature to `def _status_line(slug: str, board_dir: Path, history_n: int = 0) -> tuple[str, bool]:` and, directly before its final `return line, True`:

```python
    if history_n:
        events = (deck.get("history") or [])[-history_n:]
        if not events:
            line += f"\n{'':24s} (no recorded moves)"
        for e in events:
            line += (f"\n{'':24s} {e.get('at', '?')}  {e.get('card', '?')}: "
                     f"{e.get('from', '?')} -> {e.get('to', '?')} [{e.get('by', 'ui')}]")
    return line, True
```

In `cmd_status`, pass `history_n=getattr(args, "history", 0)` at all three `_status_line(...)` call sites (the `--all` loop, the `--project` branch, the default project-dir branch).

In `cli_main`, after `st.add_argument("--dest", ...)`:

```python
    st.add_argument("--history", type=int, default=0, metavar="N",
                    help="also print the last N move events from the deck's history ledger")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd adjudant/scripts && python3 -m unittest test_board -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/board.py adjudant/scripts/test_board.py
git commit -m "feat(adjudant): board status --history N prints the move ledger tail"
```

---

### Task 3: the page queues events and flushes them on confirmed disk writes (templates/board.html)

**Files:**
- Modify: `adjudant/skills/adjudant/templates/board.html` (globals ~250, `readMoves`/`writeMoves` ~308/~327, `writeDisk` ~371, `applyMove` ~507, the two `moves=readMoves()` sites ~710/~741)
- Test: `adjudant/scripts/test_board.py` (template marker tests must stay green; JS has no unit harness, verification is scripted-manual below)

**Interfaces:**
- Consumes: deck `history` semantics from Task 1 (shape, cap, newest-last).
- Produces: localStorage shape `{v: MOVES_VERSION, moves, pending}` (same `MOVES_VERSION=2`; `pending` is additive and safely ignored by older pages); disk decks whose `history` grows by the flushed events.

- [ ] **Step 1: Declare the queue and cap**

After the `const MOVES_VERSION=2;` line (~250):

```js
const HISTORY_KEEP=500; /* lockstep: HISTORY_KEEP in scripts/board.py */
let pending=[]; /* move events confirmed locally but not yet flushed into the deck's history on disk */
```

- [ ] **Step 2: Persist and restore the queue with the moves**

In `writeMoves`, change the stored payload line to:

```js
    localStorage.setItem(LS_KEY,JSON.stringify({v:MOVES_VERSION,moves:moves,pending:pending}));
```

After the `readMoves` function definition, add:

```js
/* The queued events, same defensive parse as readMoves: a foreign or legacy
   blob yields [], never a throw. */
function readPending(){
  try{
    const o=JSON.parse(localStorage.getItem(LS_KEY)||"null");
    if(!o||typeof o!=="object"||o.v!==MOVES_VERSION||!Array.isArray(o.pending)) return [];
    return o.pending.filter(e=>e&&typeof e==="object"&&typeof e.card==="string"&&typeof e.to==="string");
  }catch(e){ return []; }
}
```

At BOTH `moves=readMoves();` call sites (~710 and ~741), add directly after: `pending=readPending();`

- [ ] **Step 3: Queue an event on the single mutation path, roll it back with the move**

In `applyMove`, after `const undo=JSON.stringify(moves);` add:

```js
  const undoPending=pending.length;
```

After `card.column=toCol; recordMove(key,card,toCol);` add:

```js
  pending.push({card:String(card.id),from:String(from),to:String(toCol),at:new Date().toISOString(),by:"ui"});
```

In the failure branch, extend the rollback line to restore the queue:

```js
    card.column=from; moves=JSON.parse(undo); pending.length=undoPending; render();
```

- [ ] **Step 4: Flush into the deck on a confirmed disk write**

In `writeDisk`, between `if(disk){ live=mergeMoves(disk,moves); out=disk; }` and `const written=JSON.stringify(out,null,2);`:

```js
    if(pending.length){
      out.history=(Array.isArray(out.history)?out.history:[]).concat(pending);
      if(out.history.length>HISTORY_KEEP) out.history=out.history.slice(-HISTORY_KEEP);
    }
```

And directly after `await w.close();` (the write is now confirmed):

```js
    pending=[];
```

The queue clears ONLY here: a failed or skipped disk write leaves it queued in localStorage for the next flush, and the deck re-read at the top of `writeDisk` means another tab's already-flushed events are the base this flush appends to.

- [ ] **Step 5: Python suite still green**

Run: `cd adjudant/scripts && python3 -m unittest test_board -v`
Expected: PASS (the marker-injection and escape tests read the template; no fixture pins its content).

- [ ] **Step 6: Scripted-manual verification (Chromium)**

```bash
cd "$(mktemp -d)" && mkdir -p proj/tasks
printf -- "---\ntype: task\nstatus: next\n---\n\n# Try me\n" > proj/tasks/try-me.md
python3 <repo>/adjudant/scripts/board.py scaffold --project-dir proj --from-tasks --title "Ledger check"
python3 <repo>/adjudant/scripts/board.py serve --dir proj/board --port 8790
```

In Chrome at `http://localhost:8790/board.html`: connect file (pick `proj/board/board-data.json`), drag the card to Doing, then:

```bash
python3 -c "import json;print(json.load(open('proj/board/board-data.json'))['history'])"
python3 <repo>/adjudant/scripts/board.py status --project-dir proj --history 5
```

Expected: exactly one event, `from` next, `to` doing, `by` ui, `at` a UTC timestamp minutes old; status renders the same line. Then drag WITHOUT connecting in a fresh profile/incognito: the deck's `history` must not change (event stays queued in that browser).

- [ ] **Step 7: Commit**

```bash
git add adjudant/skills/adjudant/templates/board.html
git commit -m "feat(adjudant): the board writes a time-stamped move event for every confirmed drag"
```

---

### Task 4: docs, reference spec, release

**Files:**
- Modify: `adjudant/skills/adjudant/reference/board.md`
- Modify (via script): the plugin version lockstep files
- Test: full suite + validators

**Interfaces:**
- Consumes: everything above.
- Produces: the released feature; reference/board.md is the locked spec the next session reads.

- [ ] **Step 1: Update reference/board.md**

Three edits:

1. Data model JSON sample: after the `"cards": [...]` line add `"history": [{ "card": "X-01", "from": "next", "to": "doing", "at": "2026-08-01T09:12:00Z", "by": "ui" }]`.
2. New subsection after "Merge provenance (refresh-without-clobber)":

```markdown
## Move history (the ledger)

The deck carries `history`: append-only move events `{card, from, to, at, by}`,
newest last, trimmed to the newest 500 (`HISTORY_KEEP`, lockstep in `board.py`
and the template). `by: "ui"` is a confirmed in-page move (drag, `[`/`]`, tap);
`by: "seed"` is a merge parking an orphaned task card in icebox. The page queues
events in localStorage and flushes them into the deck on each confirmed disk
write, so the ledger inherits the save-honesty contract: an event reaches disk
exactly when the move it records does. `status --history N` prints the tail.
Not logged (accepted): moves absorbed from `kanban.md` edits in Obsidian, and
events queued in a browser that never connects a file handle.
```

3. In "The features (locked spec)" item 4 (Status), append: "`--history N` also prints the last N ledger events."

- [ ] **Step 2: Bump the plugin version across lockstep files**

Run: `python3 scripts/bump_plugin_version.py --help` from the repo root, then bump `adjudant` to `0.27.0` per its usage (it writes plugin.json and every parity file atomically; the `version-consistency` validator confirms).

- [ ] **Step 3: Full verification**

```bash
cd adjudant/scripts && python3 -m unittest discover -s . -v && cd ../..
python3 adjudant/scripts/validate.py
pre-commit run --all-files
```

Expected: all pass.

- [ ] **Step 4: Release commit**

```bash
git add -A
git commit -m "release(adjudant): v0.27.0 - the board remembers when things moved"
```

---

## Self-review notes

- Spec coverage: preserve-on-merge (T1), seed park events with repeat-guard (T1), cap both sides (T1/T3), UI events on the single mutation path with rollback (T3), honest flush-on-confirm (T3), read path (T2), docs + accepted limits (T4). The 2026-07-31 ask ("infer the timings on a later read") is satisfied by `history[].at` + `status --history`.
- Type consistency: `HISTORY_KEEP` (both sides), `_now_iso`, `_status_line(history_n=)`, event keys `card/from/to/at/by` identical in Python, JS, tests, and docs.
- Out of scope, named: kanban.md-absorbed moves; sitrep/check surfacing of "last move" (natural follow-up once the ledger exists).
