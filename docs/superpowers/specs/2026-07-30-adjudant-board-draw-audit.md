<!-- Promoted from a gitignored .superpowers/ workspace on 2026-07-31.
The findings below were produced on the work machine and were invisible to the
other machine for four releases, which is why v0.20.0 through v0.23.0 closed
audit tiers 4 and 5 but left every item here open. Audit output that matters
belongs in tracked docs/, not in scratch. -->

# Board and draw audit - 2026-07-30

5 dimensions, 49 findings raised, 26 adversarially verified,
26 confirmed, 0 refuted.
Nothing was refuted, which is unusual and suggests these are solid.


## CRITICAL (5)

### board.py:233 [reproduced]
merge_deck keys the on-disk deck by `str(card.get("id"))` into a plain dict, so any two on-disk cards that share an id — or that have no id at all (both key to the string "None") — collapse to one entry and every loser is SILENTLY DELETED. cards_from_tasks dedupes and warns about duplicate ids on the fresh side (board.py:154-165); the on-disk side has no equivalent guard, no warning, and no test. This directly violates the documented contract in reference/board.md:113-114 ("a card whose task disappeared is moved to icebox (never deleted)").

FAILURE: Verified end-to-end on a fixture. Deck has 3 task cards plus two board-only cards the user hand-added to board-data.json (reference/board.md and the board.html footer both invite hand-editing): {"title":"call the vendor","column":"next","notes":"ref PO-114"} and {"title":"renew the cert","column":"next","notes":"expires 2026-08-14"}. An agent then writes one task note under tasks/ — posttooluse-vault-log.py:162 fires `board_bridge.py --ensure-only`, ensure_board runs the merge. Result before: [T-1, T-2, T-3, 'call the vendor', 'renew the cert']. After: [T-1, T-2, T-3, T-4, 'renew the cert']. '

FIX: Build ex_cards from a list, not a dict: key only on a non-empty id, and carry id-less / duplicate-id cards through the merge verbatim as pass-through survivors (they can never match a fresh task card anyway). Emit the same `[board] warning: duplicate card id ...` line cards_from_tasks already emits. Add two tests that fail when the pass-through is removed: one deck with two id-less cards, one with

### board.py:341 [reproduced]
The pre-replace backup goes to one fixed filename `board-data.json.bak` (shutil.copy2, no rotation, no timestamp), and it is taken BEFORE the replacement deck is read or validated. So (a) the second replace overwrites the only copy of the user's real deck with the already-destroyed one, and (b) an operation that FAILS and writes nothing still destroys the backup. There is also no preview/apply step and no recorded-hash check, unlike every other destructive verb in the plugin — and `--all --force --from-tasks` applies this to every project in the vault in one shot.

FAILURE: Verified on a fixture. Deck has T-1/T-2/T-3 all dragged to 'doing' with notes 'PRECIOUS' and a user-added 'parking' lane. Run 1: `board.py scaffold --project demo --from-tasks --force` → .bak correctly holds the doing/PRECIOUS deck. Run 2 (same command, e.g. a re-run or a wrapper script): .bak now holds [('T-1','backlog',''),('T-2','backlog',''),('T-3','backlog','')] — the drag state, the notes and the custom lane are unrecoverable. Worse, verified separately: after run 1, a simple typo — `board.py scaffold --project demo --data ~/nope.json` — exits 1 with "could not read deck ... No such file

FIX: Move the copy2 to after the replacement deck has been read and validated (i.e. immediately before the write at line 388), and back up to a non-colliding name — `board-data.<YYYYMMDD-HHMMSS>.bak.json` or a `board/.bak/` directory keeping the last N. Add a test that runs the replace twice and asserts the ORIGINAL deck is still recoverable, and a test that a failed `--data` leaves the existing .bak b

### _vault_walk.py:576 [reproduced]
The shared breadcrumb resolver used by board_bridge.py, board.py and graph.py builds the vault project path from the repo-committed `slug` with no `is_safe_slug` gate, so a traversal slug makes all three write outside the vault. `resolve_project_from_cwd` does `vpd = find_project_dir(vault, bc["slug"]) or (vault / "projects" / bc["slug"])` — neither branch validates. Every hook gates the slug (posttooluse-vault-log.py:108, precompact.py:219, sessionend.sh:57-65) and validator 30 enforces that for `hooks/`, but `scripts/` is outside validator 30's scan and inherits nothing. board.py:492 and board.py:604 have the same ungated build for `--project SLUG`.

FAILURE: Empirically confirmed. `repo/.claude/adjudant` containing `slug: ../../outside/victim` plus a valid `vault_path`, then the DOCUMENTED invocation from reference/board.md:57 (`board.py scaffold --project-dir "$PROJECT_ROOT" --from-tasks`) or `board_bridge.py --bridge ledger.jsonl --project-dir repo`: adjudant wrote `outside/victim/tasks/fix-the-widget.md`, `outside/victim/board/board-data.json` and `outside/victim/board/board.html`, exit 0, and graph.py happily read the same escaped directory. Since `.claude/adjudant` is committed to the repo, cloning a repo whose breadcrumb carries a traversal 

FIX: Gate in `resolve_project_from_cwd`: `if not is_safe_slug(bc["slug"]): return None` (which makes `smart_project_dir` raise VaultUnresolvableError, the existing fail-closed path). Add the same gate to board.py's two `--project` builds, and extend validator 30 to cover `scripts/` modules that resolve a slug into a path.

### board.html:369 [reproduced]
The localStorage rev-guard keys only on the SET of card ids, so a re-scaffold that re-seeds title/category/related is permanently invisible in the browser — the UI keeps showing the pre-edit deck with no staleness signal and no in-page way to recover.

FAILURE: Empirically confirmed end to end. Fixture project `hostile` with task H-1 titled `close ...`, category `build`, no refs. Loaded board.html, dragged H-1 one lane (this is what populates localStorage — a fresh visit does not). Then edited tasks/a.md to `title: RENAMED BY THE USER IN THE TASK NOTE`, `category: infra`, `related: [SPEC-999]` and re-ran `board.py scaffold --from-tasks`. board-data.json on disk now correctly reads title="RENAMED BY THE USER IN THE TASK NOTE", category="infra", related=["SPEC-999"] (merge_deck did its job). Reloaded board.html in the browser: UI_shows_title="close </s

FIX: Make the rev a hash of the whole deck payload, not just the id set, and keep drag state separately: persist only `{cardId: column}` overrides to localStorage and always render title/category/related/notes from SEED. That preserves the stated intent (a re-scaffold must not lose the column you dragged a card into) while letting every other field re-seed. As a minimum, add a visible "deck updated — r

### graph.py:271 [reproduced]
`--out` writes to a completely unvalidated path: no containment check, no is-inside-project check, no existing-file guard, no backup, no atomic replace, no preview/apply. It silently destroys whatever file it is pointed at, and `--mode tiers` does not even resolve a project first, so the target is entirely arbitrary.

FAILURE: Ran against a throwaway vault project: `python3 graph.py --project-dir <vp> --mode tiers --out <vp>/brief.md`. brief.md went from `---\ntype: project\n---\n# P\n` to the raw tiers fence. No `.bak` was written (the dir afterwards contains only `board/` and `brief.md`), the process printed `[graph] wrote .../brief.md` and exited 0. The project brief — the file the whole vault-project model is anchored on — is unrecoverable. The same call with `--out ~/.zshrc` or `--out ../../anything` is equally accepted; nothing binds the path to the project dir or the vault. This is the one write in a helper t

FIX: Gate --out the way the destructive verbs are gated: resolve the path, require it to be inside the resolved project dir (or refuse with a clear error), refuse to overwrite an existing file unless `--force`, `shutil.copy2` to `<name>.bak` before overwriting when --force is given, mkdir the parent, and write via a temp file + os.replace. Add a CLI test that fails when each of those guards is removed.


## IMPORTANT (22)

### board.py:492 [reproduced]
board.py builds its write path from an ungated slug. `--project` goes straight into find_project_dir/`vault / "projects" / args.project` with no is_safe_slug call, and the default `--project-dir` path reaches the same place through smart_project_dir → resolve_project_from_cwd (_vault_walk.py:576), which interpolates the REPO-COMMITTED breadcrumb `slug` with no gate either. board.py imports is_safe_slug nowhere. Validator 30 (validate.py:711) enforces this gate only over hooks/scripts/, so scripts/board.py — a destructive writer — is outside its reach. There is no containment check that the resolved project dir stays under the vault.

FAILURE: Verified twice on a fixture. (1) `board.py scaffold --vault $V --project '../../../../scratchpad/outside'` exits 0 and creates $S/outside/board/board.html + board-data.json — entirely outside the vault. (2) The untrusted-input path: a cloned repo carrying `.claude/adjudant` with `slug: ../../../../scratchpad/pwned`; running `board.py scaffold --project-dir .` from that repo exits 0 and writes $S/pwned/board/board.html and board-data.json. The HTML content is attacker-influenceable too (card titles come from tasks/*.md). smart_project_dir returns the bogus dir rather than raising because _vault

FIX: Gate both entry points on is_safe_slug before any path build (reject with a clear error), and add a containment assertion in scaffold_one: resolve `dest` and refuse when it is neither under the resolved vault root nor under an explicitly passed `--dest` (which reference/board.md:35 legitimately allows to point at a code repo). Add tests that a traversal slug in `--project` and a traversal slug in 

### board.py:143 [reproduced]
cards_from_tasks reads every task note with `f.read_text(errors="replace")`, and the decoded result is written straight into vault files (board-data.json and board.html). This is exactly the class the plugin already fixed elsewhere (commit 5bd7164 "sync stops baking U+FFFD into the brief", 1934eac "an undecodable brief rolls the shelf transition back"). Because U+FFFD lands in the card ID, the corruption is not self-healing: fixing the source note produces a NEW id, and merge_deck iceboxes the mojibake card forever instead of removing it.

FAILURE: Verified on a fixture. tasks/deploiement.md saved as latin-1 with `code: "DÉP-1"`. Scaffold exits 0 and writes `"id": "D�P-1"` into board-data.json and `D�P-1` into board.html. The author then re-saves the note as proper UTF-8; the next ambient reseed yields TWO cards: ('DÉP-1','backlog') and ('D�P-1','icebox') — a permanent zombie ticket in Icebox that no reseed can ever clear, because merge_deck's orphan rule is "never deleted".

FIX: Decode task notes strictly (`f.read_text(encoding="utf-8")`); on UnicodeDecodeError, skip that note with a named `[board] warning: <file> is not valid UTF-8 — card omitted` on stderr, or abort the scaffold, matching the shelf precedent. Add a test with latin-1 bytes asserting no U+FFFD reaches board-data.json.

### board.html:241
writeDisk() serialises the whole in-memory `state` and truncates board-data.json (`createWritable()` defaults to keepExistingData:false) without ever re-reading the file first. The tab's state is loaded once at boot() (board.html:356-372) and never refreshed, so the browser holds a snapshot that goes stale the moment any reseed writes. Every subsequent drag blind-writes that stale snapshot over the file. There is no mtime, etag, or `updated` comparison on either side — python and the browser are two unsynchronised writers of the same document.

FAILURE: Board open in Chromium with the file handle connected at 09:00. 09:05 the agent writes tasks/new-feature.md; posttooluse-vault-log.py fires ensure_board, which adds card T-4 to board-data.json and (because tasks/old-thing.md was deleted) moves T-2 to icebox. The tab knows nothing of either. 09:10 the user drags T-1 one lane right; persist() → writeDisk() truncates and rewrites the 09:00 snapshot: T-4 vanishes from the deck and T-2 is restored to its old lane. Any lane the user added to board-data.json by hand after 09:00 is also erased, and merge_deck then adopts the browser's stale `columns` 

FIX: Before writing, re-read the file through the handle, and reconcile: if the on-disk `cards` id-set or `updated` differs from what the tab last read, merge (take the tab's `column` for the card just moved, take disk for everything else) rather than clobber. Cheap first step: re-read on window focus and on a visibilitychange, plus refuse to write when the on-disk `updated`/rev differs from the value 

### board.py:388 [reproduced]
Separately from the known non-atomic write, scaffold_one is an unlocked read-modify-write: it reads the deck at line 355, does the merge at 377, renders the template at 387, then blind-writes at 388. Anything that lands in that window — a browser drag saved via the File System Access API, or a second concurrent ensure_board — is silently overwritten. ensure_board's own pre-read at line 436 does not narrow this; it is a separate read and scaffold_one re-reads anyway.

FAILURE: Verified by instrumenting the exact window (patching render_template, which board.py calls between the read and the write, to perform the write a browser would). Deck seeded with T-1/T-2/T-3; tasks/t4.md appears; ensure_board(P) runs; mid-window the browser saves T-1 moved to 'done'. Final deck: [('T-1','backlog'),('T-2','backlog'),('T-3','backlog'),('T-4','backlog')] — the drag is gone, verdict "reseeded", exit 0, nothing on stderr. In production the window spans cards_from_tasks walking every task note plus a 383-line template read and regex substitution, and posttooluse-vault-log.py:162 fir

FIX: Fold this into the atomicity fix: take an exclusive lock (fcntl.flock on board-data.json or an O_EXCL sidecar) for the whole read-merge-write, read the deck INSIDE the lock, and write via tempfile + os.replace in the same directory. Then also write board.html under the same lock so the two files cannot diverge. Add a two-process test that asserts a concurrent column change survives the reseed.

### board_bridge.py:78 [reproduced]
`read_ledger` catches only `OSError`, so a ledger with an undecodable byte raises `UnicodeDecodeError` straight out of `read_ledger` -> `bridge_ledger` -> `main`. The `except Exception` at line 195 wraps only `ensure_board`, not the ledger replay. The module docstring at lines 25-26 explicitly promises the opposite: "A missing or unreadable ledger under `--bridge` degrades to the same thing: no notes, ensure still runs." It does not — this is a hook-time script that must fail open.

FAILURE: Empirically confirmed. A ledger whose first line is valid JSON and whose second line contains a raw 0xe9 byte: `board_bridge.py --bridge bad.jsonl --project-dir vault/projects/demo` printed a full Python traceback to stderr and exited 1. Two losses, not one: the valid survivor on line 1 was never written, AND `ensure_board` never ran, so an already-existing board silently missed its session-end reseed. The verdict line the callers' contract depends on (`board.py --ensure` parity, last stdout line) was never printed.

FIX: Read with `path.read_text(encoding="utf-8", errors="replace")` (safe here — the ledger is parsed, never written back, so no U+FFFD reaches the vault) or widen to `except (OSError, UnicodeDecodeError)`. Additionally wrap the `bridge_ledger` call in main under the same `except Exception` as `ensure_board`, so no ledger-side failure can stop the ensure pass.

### board_bridge.py:157 [reproduced]
`bridge_ledger` does `tasks_dir.mkdir(parents=True, exist_ok=True)` unconditionally, without consulting the project's `project_type`. For `knowledge` and `tinkerage` projects, `tasks` is not in `PROJECT_TYPE_DEFAULT_FOLDERS` (_vault_walk.py:728-745), so adjudant's own structural scanner reports the folder adjudant just created as drift.

FAILURE: Empirically confirmed. A project with `project_type: knowledge`, a session that used the harness task tool, and session end: `board_bridge.py --bridge` created `tasks/fix-the-widget.md` plus `board/`. Running `ramasse_scan.py --project-dir vault/projects/kb` then reported `folder_drift: ['tasks']`. The user is told by /adjudant ramasse that their knowledge vault has structural drift, caused entirely by adjudant's own SessionEnd hook, and the loop repeats every session — remove the folder, the next session end recreates it.

FIX: Read `project_type` from the project's `brief.md` in `bridge_ledger` and skip the ledger replay entirely (still running `ensure_board`) when `tasks` is not an allowed folder for that project type, or when `tasks/` does not already exist for a non-coding/plugin project.

### test_board_bridge.py:141 [reproduced]
None of board_bridge's fail-open guards has a test that fails when the guard is deleted. Mutation-tested against the FULL 912-test suite (a pristine copy under /tmp; `git status` confirms nothing was mutated in place): removing the `project_dir.is_dir()` check at board_bridge.py:184, the `_FALLBACK_TEMPLATE` fallback at 126-127, the per-survivor `except OSError: continue` at 160-161, and the hook-time `except Exception` at 195-197 all SURVIVED — 912 tests still passed with each guard gone. These are exactly the guards the "runs from a hook, must fail open and never corrupt" contract rests on.

FAILURE: Concretely for the is_dir guard (the phantom-project guard): with `if not project_dir.is_dir():` neutered to `if False:` in a /tmp copy, a breadcrumb naming a slug with no project in the vault (`slug: ghost-project`) caused the bridge to fabricate `vault/projects/ghost-project/tasks/fix-the-widget.md` + `vault/projects/ghost-project/board/board-data.json` + `board.html` and exit 0. With the guard restored the same run correctly printed `error: project not found ... (run /adjudant connect first)` and wrote nothing. A regression that deletes that one line ships green.

FIX: Add to test_board_bridge.py: (a) a breadcrumb whose slug has no project -> rc 1 and zero files created under the vault; (b) a ledger survivor whose tasks/ path is unwritable -> other survivors still written, rc 0; (c) TEMPLATE monkeypatched to a nonexistent path -> note still written and schema-clean via _FALLBACK_TEMPLATE; (d) `ensure_board` monkeypatched to raise -> rc 1 with an `error:` line an

### test_board_bridge.py:171 [reproduced]
board_bridge's zone-awareness and its (absent) slug gate have no test at all. test_board_bridge.py only ever passes `--project-dir` pointed straight at `vault/projects/demo`; it never constructs a `.claude/adjudant` breadcrumb, so the entire `smart_project_dir` -> `resolve_project_from_cwd` -> `find_project_dir` path that board_bridge actually uses in production (sessionend.sh and posttooluse-vault-log.py both go through it) is untested. test_board.py has TestZoneAwareProjectFlag for board.py's `--project`; there is no equivalent for the bridge.

FAILURE: I verified by hand that the bridge IS currently zone-aware — a `slug: demo` breadcrumb against a project shelved to `projects/_fridge/demo` correctly wrote `vault/projects/_fridge/demo/tasks/fix-the-widget.md`. Nothing in the suite would notice if that regressed to a hardcoded `projects/<slug>`, which is precisely the ghost-twin bug validator 30 exists to prevent, and nothing would notice the missing `is_safe_slug` gate (finding 1) either — that traversal escape is invisible to all 912 tests.

FIX: Add breadcrumb-driven cases: a fridged project resolves to `_fridge/<slug>` (fails if zone-awareness regresses), and a breadcrumb with `slug: ../../escape` writes nothing outside the vault and returns non-zero (fails today, passes once finding 1 is fixed).

### board.html:237 [reproduced]
persistLocal() swallows every storage error in a totally empty `catch(e){}` — not even a console.warn — so a drag can appear to succeed while nothing is written, and the `conn` badge reads "local" identically whether saving works or is failing.

FAILURE: Empirically confirmed in Chromium. Patched `Storage.prototype.setItem` to throw QuotaExceededError (the shape of Safari private browsing, Firefox strict/blocked storage, an enterprise storage policy, or a genuinely full origin), then moved card H-2 one lane. Result: cardMovedInUI=true, UI lane changed to "Next", alertShown=null, conn text "local" before AND after, connHasOnClass=false, zero [role=alert]/.error/.toast nodes, and no console output at all. The persisted column for H-2 was still "backlog". The user closes the tab and every move made in that session is gone. The footer copy at line

FIX: Have persistLocal() return a boolean and have persist() surface a real failed-save state — flip `conn` to a distinct "unsaved" class with error styling and show a dismissible banner naming the reason. Do not let a mutation render as committed until at least one backing store confirmed the write.

### board.html:244 [reproduced]
persist() writes the tab's entire in-memory `state` blob with no read-before-write, no revision check, and no `storage` event listener, so two tabs open on the same board silently clobber each other last-writer-wins — on both localStorage and the File System Access disk write.

FAILURE: Empirically confirmed. Tab B moves card H-3 to `done` and persists (verified: localStorage now has H-3 in "done"). Tab A — still holding the in-memory state from before, as it must, since there is no storage listener — then moves H-2 one lane. After tab A's persist(), localStorage reports H-3 back in "doing": tab B's move is gone, and tab B's UI still shows H-3 in Done until it is reloaded, so both tabs believe they saved and one is wrong. Confirmed absent from the source: `storage` event handler (0 occurrences), `visibilitychange` (0), `beforeunload` (0). The same whole-file clobber applies t

FIX: Add a `window.addEventListener('storage', ...)` that reloads state and re-renders when another tab writes LS_KEY, and stamp each write with a monotonic counter that persist() verifies before overwriting (refuse and warn on a mismatch instead of clobbering). For the disk path, re-read the file and compare before createWritable().

### board.html:114 [reproduced]
`.ticket:focus-visible{outline:2px solid var(--c)}` is the ONLY focus affordance on a card, and it uses the category hue — all eight palette colours measure 1.65:1 to 2.28:1 against the card surface, failing WCAG 2.2 SC 1.4.11 (3:1 for focus indicators). The documented keyboard alternative to drag-and-drop is therefore unusable.

FAILURE: Measured in Chromium via canvas pixel readback of the computed colours (surface = rgb(255,255,255), bg = rgb(248,248,250)). Contrast of each PALETTE entry (line 197) against `--surface`: oklch(78% 0.16 295)=2.17, oklch(82% 0.17 142)=1.65, oklch(82% 0.15 50)=1.94, oklch(78% 0.16 215)=1.86, oklch(80% 0.16 340)=2.02, oklch(80% 0.15 200)=1.73, oklch(80% 0.14 110)=1.84, oklch(78% 0.16 25)=2.28. Every one is below 3:1; the worst is under half. Concrete failure: a keyboard user follows the footer instruction "Focus a ticket (Tab) and press [ / ] to move it a stage left / right", tabs into the board a

FIX: Use a token guaranteed to pass — e.g. `outline:2px solid var(--text)` with `outline-offset:2px` plus a `box-shadow` halo in `--surface` for separation — and keep the category hue for the `.t-cat` stamp only. Verify at 3:1 against both `--surface` and the dark-mode surface.

### board.html:281 [reproduced]
The board has zero ARIA: no roles on lanes or cards, no accessible names, and no live region — so a screen-reader user cannot tell a lane from a card, cannot know which lane a card is in, and gets no feedback when [ / ] moves one.

FAILURE: Confirmed by both source grep and a real Chromium accessibility snapshot. Source: `role=` occurs 0 times, `aria-` 0 times in the whole 383-line file. Live DOM query: `document.querySelectorAll('[role]').length === 0` and `[aria-live],[role=status],[role=alert]` length 0. The Playwright a11y tree for a populated board renders every lane, every ticket, every ticket id/category/title, and every legend key as an undifferentiated `generic` node — the ticket's only attributes are `class`, `draggable`, `tabindex=0`, `data-id`, `style`. Concrete failure: a VoiceOver user tabs to a ticket and hears the

FIX: Give `.lane-body` `role="list"` + `aria-labelledby` pointing at its `.lane-head .nm`, give `.ticket` `role="listitem"` with an `aria-label` that includes the lane name, and add a visually-hidden `role="status"` region that moveCard() and the drop handler write to ("H-1 moved to Review, 2 of 3"). Announce the no-op at the ends too.

### board.html:313 [reproduced]
The legend category filter is a bare <span> with a click handler — not focusable, no role, no keydown — so it is mouse-only, a straight WCAG 2.1.1 keyboard failure on a control the footer explicitly tells users to use.

FAILURE: Confirmed in the live DOM: the legend key element is `{tag:'SPAN', tabIndex:-1, attrs:['class=k','style=--c: ...']}` — no tabindex, no role, no aria-pressed, and render() at line 317 attaches only a `click` listener. Concrete failure: a keyboard-only user reads the footer line "Type in filter (or click a legend key) to narrow", tabs through the whole page, and the legend keys are simply skipped — the category filter is unreachable, and there is no keyboard equivalent (the text filter matches category substrings only incidentally, and cannot express "category is exactly X"). The toggled state i

FIX: Render the legend keys as real `<button type="button">` with `aria-pressed` reflecting `filterCat===cat`. That gets focus, Enter/Space, and state announcement for free and removes the need for the cursor:pointer/user-select overrides.

### board.html:306 [reproduced]
render() reads state.cards/state.columns with no shape validation and boot() calls it outside any try, so a deck missing a key does not fail visibly — it renders a confident, fully-styled board reporting "0 ORDERS / 0 STAGES". The static skeleton is a lie, which is also exactly what a JS-disabled visitor sees.

FAILURE: Empirically confirmed. Rendered a deck `{version,boardId,title:'Broken',columns:[{id:'backlog',name:'Backlog'}],categories:['build']}` — valid JSON, one real column, but no `cards` key (reference/board.md invites hand-editing board-data.json, and the FSA read paths at lines 229 and 362 do `normalize(JSON.parse(txt))` with no validation whatsoever). Loading it: boardChildren=0, board innerHTML empty, masthead correctly shows "BROKEN", orderCount "0", stageCount "0" (even though the deck has 1 column), conn "local", and `document.body.innerText` contains no error string — the visible page reads 

FIX: Validate in normalize(): coerce `cards`/`columns`/`categories` to arrays and reject a non-object root, then wrap boot()'s tail in try/catch that paints a real error state naming the bad file. Add a `<noscript>` block saying the board requires JavaScript, and set the static counters to "—" rather than "0" so an unrendered page can never read as an empty one.

### board.html:297 [reproduced]
There is no touch or pointer input path at all — the only two ways to move a card are HTML5 drag events (which do not fire from touch input) and the [ / ] keys — so on a phone or tablet the board is silently read-only while the footer promises dragging.

FAILURE: Confirmed by source grep on the template: `touchstart` 0 occurrences, `pointerdown` 0, and the only two mutation paths in the file are the `drop` handler (line 340) and the `keydown` [ / ] handler (line 299). HTML5 dragstart/dragover/drop are not synthesised from touch gestures on iOS Safari or Android Chrome, and a tablet without a hardware keyboard has no way to fire the keydown path either. Concrete failure: a user opens the served board on an iPad, reads "Drag an order between stages — saved to this browser instantly", presses and drags a ticket, and the card does not move and nothing indi

FIX: Add a Pointer Events fallback (pointerdown on a ticket + pointerup over a lane, or a simple tap-to-select then tap-a-lane-to-move), or at minimum render explicit left/right move buttons on each ticket when `matchMedia('(pointer: coarse)')` matches — those also give the keyboard and SR paths a real control instead of an undiscoverable bracket key.

### board_bridge.py:180 [reproduced]
board_bridge (and board.py and graph.py) never gate the breadcrumb slug with is_safe_slug, so a repo-committed `.claude/adjudant` carrying a traversal slug makes every write land outside the vault. The root cause is _vault_walk.resolve_project_from_cwd:576, which passes bc["slug"] straight into find_project_dir with no validation; smart_project_dir returns that path, and board_bridge writes tasks/ notes and board/ files into it. The `_looks_like_code_repo` refusal is bypassed entirely on the breadcrumb path. _vault_walk.py:877 states the invariant explicitly ("Every consumer of a breadcrumb slug must gate on is_safe_slug before building a path from it") but validator 30 (`hook-zone-awareness`, validate.py:721) only globs hooks/scripts/*, so no verb in scripts/ is checked. There is no test for this on any of the three modules.

FAILURE: VERIFIED. Fixture: vault at /tmp/adj-audit/vault with projects/demo; a code repo at /tmp/adj-audit/repo containing pyproject.toml and `.claude/adjudant` with `slug: ../../outside/pwned` + `vault_path: /tmp/adj-audit/vault`; an existing dir /tmp/adj-audit/outside/pwned. Running `python3 board_bridge.py --bridge ledger.jsonl --project-dir /tmp/adj-audit/repo` exits rc=0, prints `created`, and creates /tmp/adj-audit/outside/pwned/tasks/fix-the-widget.md, /outside/pwned/board/board-data.json and /outside/pwned/board/board.html — all outside the vault. `board.py scaffold --project-dir <repo> --from

FIX: Gate in _vault_walk.resolve_project_from_cwd: after `if not bc or "slug" not in bc: return None`, add `if not is_safe_slug(bc["slug"]): return None` (or raise VaultUnresolvableError so callers get the friendly message rather than falling through to the code-repo branch). That closes it for all eleven verbs at once. Then widen validator 30's scan from hooks/scripts/* to include scripts/*.py so it s

### board_bridge.py:158 [reproduced]
bridge_ledger writes each task note with a plain `note.write_text(...)` (non-atomic), while the dedupe one line above is `if note.exists(): continue`. Any partially-written or zero-byte note is therefore permanently canonical: the bridge will never rewrite it, and cards_from_tasks turns it into a permanent ghost card. This is the same non-atomicity class already measured for board-data.json, but with a worse consequence, because for the deck a later run overwrites the torn file whereas here the torn file is what stops the rewrite. The SessionEnd hook is declared with `timeout: 10` in hooks/hooks.json, so the harness kills the process mid-batch by design.

FAILURE: VERIFIED. In /tmp/adj-audit3, a zero-byte tasks/fix-the-widget.md (standing in for a write interrupted by the 10s SessionEnd timeout, a full disk, or a OneDrive/iCloud sync collision) was placed in an otherwise-normal project. Running `board_bridge.py --bridge led.jsonl --project-dir .../demo` with a ledger entry `{"id":"T-1","subject":"Fix the widget","description":"real content"}` exits 0, prints `created`, and leaves the note at 0 bytes — the description is silently lost forever. The deck it then writes contains {'id': 'fix-the-widget', 'title': 'fix-the-widget', 'column': 'backlog', 'categ

FIX: Write via a sibling temp file and os.replace: `tmp = note.with_name(note.name + '.tmp'); tmp.write_text(text, encoding='utf-8'); os.replace(tmp, note)`. Same-directory rename is atomic on the vault filesystem. Additionally treat a zero-length existing note as absent in the dedupe (`if note.exists() and note.stat().st_size > 0`) so an already-torn note self-heals. Add `encoding="utf-8"` to the TEMP

### test_board_bridge.py:127 [reproduced]
test_hostile_session_id_no_write is vacuous: it passes with the guard it exists to protect (`if not _SESSION_ID_RE.match(session_id): return 0`, hooks/scripts/task-ledger.py:59) deleted. Two reasons. First, `session_id="../evil"` yields the path `$TMPDIR/adjudant-task-ledger-../evil.jsonl`, whose parent component `adjudant-task-ledger-..` does not exist, so `open(..., "a")` raises FileNotFoundError, which the pre-existing `except OSError: pass` at line 72 swallows — the containment is accidental, supplied by the filename prefix, not by the guard. Second, the test's own assertion checks for `tmp.parent / "adjudant-task-ledger-evil.jsonl"`, a filename the code cannot produce with or without the guard, so it can never fail.

FAILURE: VERIFIED by mutation on a copy at /tmp/adj-mut/adjudant. Deleting the two-line `_SESSION_ID_RE` gate from hooks/scripts/task-ledger.py and running `python3 -m unittest test_board_bridge` reports `Ran 17 tests ... OK`. The full sweep (`test_board test_board_bridge test_graph test__vault_walk`, 79 tests) is also OK with the guard gone. The guard is therefore unprotected against future refactors: the day someone changes ledger_path to mkdir its parent, or drops the `adjudant-task-ledger-` prefix, or widens `except OSError` handling, the escape opens and no test says a word.

FIX: Assert the guard's own behaviour rather than a downstream side effect. Either (a) pre-create the intermediate directory the escape needs — mkdir `$TMPDIR/adjudant-task-ledger-x` — then feed `session_id="x/../../evil"` and assert `(self.tmp.parent / 'evil.jsonl')` does not exist (this fails with the guard removed), or (b) call `task_ledger.ledger_path` / a new `_accept_session_id` helper directly a

### board.py:387 [reproduced]
The ordering guard in scaffold_one — `html = render_template(deck)` deliberately placed before the two write_text calls, with the comment "Render FIRST: a missing/markerless template must fail before any write, never leaving board-data.json and board.html out of sync" — has no covering test. Reordering it so board-data.json is written first is not detected by any of the 79 tests across test_board, test_board_bridge, test_graph and test__vault_walk.

FAILURE: VERIFIED by mutation. Replacing lines 387-389 with `data_path.write_text(json.dumps(deck, indent=2) + "\n")` followed by `(dest / "board.html").write_text(render_template(deck))` — i.e. exactly the desync the comment forbids — leaves the whole suite green (`Ran 79 tests ... OK`). The real failure it is meant to prevent: templates/board.html is unreadable or has lost its BOARD_DATA markers (the mid-OneDrive-sync clone that board_bridge's own _FALLBACK_TEMPLATE exists to survive). With the guard reordered, `board.py scaffold --from-tasks` writes a fresh board-data.json and then raises FileNotFou

FIX: Add to TestScaffoldOne: seed a board, monkeypatch `board.TEMPLATE` to a nonexistent path (and, as a second case, to a temp file with the markers stripped), snapshot board-data.json, call scaffold_one, and assert it fails (raises or rc != 0) AND board-data.json is byte-for-byte unchanged / not created. The nonexistent-path case must also assert board.html was not created.

### graph.py:55 [reproduced]
`_q` emits `""` for an empty/whitespace-only label, and mermaid refuses to parse an empty node or subgraph label — so one empty string anywhere in the deck kills the entire generated fence, not just one node.

FAILURE: Verified against mermaid 11.16's own flowchart parser (loaded the bundled `flowDiagram-*.mjs` grammar directly under node). A deck with `{"columns": [{"id": "wip", "name": ""}, ...]}` makes graph.py emit ` subgraph col0[""]`, and the parser returns: `Parse error on line 2 ... Expecting 'TAGEND', 'STR', 'MD_STR', 'UNICODE_TEXT', 'TEXT', 'TAGSTART', got 'SQE'`. The identical failure occurs for a node: `c0[""]`, reachable from a card with `"id": ""` and no title (label = `card_id` when title is falsy, graph.py:191-192). Pasted into Obsidian the block renders as a red mermaid parse error and nothi

FIX: In `_q`, fall back to a placeholder when the cleaned label is empty: `clean = ... .strip() or "(untitled)"`. Add a test with an empty column name and an empty card id that asserts no `[""]` appears in the output.

### graph.py:185 [reproduced]
`board_graph` applies neither of the two disciplines the reference docs promise for graph.py output: there is no node cap and no classDef styling. Only `relations_graph` implements them.

FAILURE: Ran graph.py against a 200-card deck with `--max-nodes 30`: the emitted fence contains 200 card nodes over 205 lines, `classDef` appears zero times, and nothing is printed on stderr. `--max-nodes` is silently ignored in board mode (it is only threaded into `relations_graph`, graph.py:262-265). This directly contradicts three reference files the model is told to follow: `reference/draw.md:42-44` ("`scripts/graph.py` (read-only, node-capped, labels quoted + role classDefs per the generation rules)"), `reference/content-mermaid.md:37` ("`scripts/graph.py` emits a node-capped fence with quoted lab

FIX: Either implement the cap and role classDefs in board mode (cap per column, emit a `%% N cards omitted` note plus a stderr warning, stamp a classDef per lane), or fix draw.md:42, content-mermaid.md:37 and mermaid-generation-rules.md:79-83 to scope both claims to `--mode relations` (content-mermaid.md:254 already scopes the cap correctly — the other three sites do not).

### graph.py:72 [reproduced]
The relations graph is markdown-only — `walk_project` iterates `rglob("*.md")` — so `.canvas` and `.base` files are neither nodes nor resolvable link targets. The draw verb's own two other artefact types are invisible to the draw verb's own graph, and every wikilink pointing at them silently produces no edge.

FAILURE: Fixture: `brief.md` containing `See [[canvases/user-flow]] and [[user-flow]] and [[research-targets]] and [[notes/idea]].`, plus `canvases/user-flow.canvas`, `bases/research-targets.base`, and `notes/idea.md`. `graph.py --mode relations` emits exactly two nodes (`brief`, `idea`) and one edge. Three of the four links vanish with no diagnostic, so the graph presents a project whose canvases and bases do not exist and whose brief looks like it links nowhere. This contradicts graph.py's own docstring (line 8-9, "one node per vault file, one edge per resolving wikilink between project files") and i

FIX: In `relations_graph`, after `walk_project`, additionally glob `*.canvas` and `*.base` under the project dir and register them as leaf nodes (no outbound edges, a new `artefact` role in CLASS_DEFS) so links to them resolve. Test with a canvas + base fixture asserting both nodes and the inbound edges appear.


## MINOR (22)

### board.py:389
board-data.json and board.html are two independent write_text calls with nothing tying them together. The comment at 386 claims render-first keeps them in sync, but that only covers a missing/markerless template — an ENOSPC, EACCES, or interrupt between line 388 and 389 leaves board.html embedding the previous deck while board-data.json holds the new one.

FAILURE: Disk fills (or the process is killed) between the two writes on a reseed that added T-4. board-data.json has 4 cards; board.html's SEED block still has 3. A user without the File System Access API (Firefox/Safari — board.html:223 tells them to fall back to the embedded deck plus Download) opens board.html, sees 3 cards, hits `download`, and saves that 3-card deck back over the 4-card file.

FIX: Write both files to temporaries and os.replace them back-to-back after both succeed, under the same lock as the finding above.

### board.py:387 [reproduced]
board.py's template-integrity guards are uncovered. The comment at 385-386 states the invariant — "Render FIRST: a missing/markerless template must fail before any write, never leaving board-data.json and board.html out of sync" — but reordering `render_template(deck)` to run AFTER `data_path.write_text(...)` SURVIVED all 912 tests, as did deleting the markerless-template `raise ValueError` at render_template (board.py:288-289).

FAILURE: With the ordering inverted in a /tmp copy, a board.html template that lost its BOARD_DATA markers (a bad merge, a truncated cloud sync) leaves a freshly written board-data.json on disk with no matching board.html — the exact desync the comment forbids — and the suite reports OK. The invariant is documented, load-bearing, and enforced by nothing.

FIX: Monkeypatch board.TEMPLATE to a markerless file and to a nonexistent path; assert `scaffold_one` returns non-zero (or raises) and that `board-data.json` is byte-identical to its pre-call contents.

### test_board.py:468 [reproduced]
`test_non_object_deck_friendly_error` reads as coverage for the "deck root must be a JSON object" guard, but it only exercises the on-disk-deck branch (board.py:356-357). The identical guard on the `--data` branch (board.py:352-353) is uncovered: deleting it survived all 912 tests. Same class: `cmd_ensure`'s `except VaultUnresolvableError` (board.py:636-638) and `scaffold_one`'s project-not-found check (board.py:320-322) both survived deletion too.

FAILURE: With board.py:352-353 removed, `board.py scaffold --project-dir P --data list.json` where list.json is `[]` produces `AttributeError: 'list' object has no attribute 'setdefault'` at board.py:366 instead of the friendly `could not read deck` message — and the test whose name promises to catch exactly that still passes. Verified: the guard itself works today (`error: could not read deck bad.json: deck root must be a JSON object`); it is only the test that is vacuous.

FIX: Extend the test to loop over both branches — the existing deck file AND `--data` pointing at a `null`/`[]` file. Add a case for `cmd_ensure` against a breadcrumb with an unresolvable vault (assert rc 1 and an `error:` line, no traceback).

### test_graph.py:8 [reproduced]
test_graph.py has zero CLI-level coverage: it imports only `board_graph`, `fenced`, `relations_graph`, `tiers_graph` and never calls `graph.cli_main`. `--out` (the module's only write path, graph.py:270-272), `--mode` dispatch, `--include-legacy`, `--max-nodes` plumbing, breadcrumb resolution via `smart_project_dir`, and the `VaultUnresolvableError` / `json.JSONDecodeError` error handling at graph.py:255-268 are all untested. The 14 tests exercise pure functions only.

FAILURE: graph.py's docstring claims "Never writes into the vault — the only write is the optional --out file." Nothing tests that. `--out` takes an arbitrary path with no containment check at all, and no test would fail if the error branches at 257-258 or 266-268 were deleted, turning a stale breadcrumb or a corrupt board-data.json into a raw traceback for a verb the skill invokes on the user's behalf.

FIX: Add cli_main tests: `--mode tiers` needs no project; `--mode board` with a corrupt deck returns 1 with an `error:` line; `--out` writes the fenced block and nothing else; a breadcrumb-linked project dir resolves through smart_project_dir; a code repo with no breadcrumb returns 1.

### board_bridge.py:91 [reproduced]
`tid = str(entry.get("id") or "").strip()` treats a falsy-but-present id as missing, so ledger entries with `"id": 0` or `"id": false` are silently discarded. Non-string ids are also stringified rather than rejected, so `{"id": {"a": 1}}` becomes the dedupe key `"{'a': 1}"`.

FAILURE: Verified against read_ledger: a ledger containing `{"id": 0, "subject": "Zero id task"}`, `{"id": false, ...}` and an entry with no id at all yields keys `['T-1','T-2','T-3','T-4',"{'a': 1}",'T-5','T-6']` — the zero/false-id tasks vanish and never become notes. Today's task-ledger.py always writes a non-empty string id so this is latent, but the module's contract is "latest status per id" and a harness that ever emits a numeric task id would drop task 0 forever, with no diagnostic.

FIX: `raw = entry.get("id"); if raw is None or isinstance(raw, bool): continue; tid = str(raw).strip()` — and reject non-(str|int) ids outright rather than stringifying containers.

### board_bridge.py:153 [reproduced]
Two distinct ledger ids whose subjects kebab to the same slug silently collapse to one note, with the second survivor's description discarded and no warning. This happens on case differences and on any two subjects sharing their first 80 kebab characters (the `_KEBAB_MAX` truncation at line 70). board.py warns loudly on duplicate card ids (board.py:162-164); the bridge is silent about the equivalent collision.

FAILURE: Verified: a ledger with `{"id":"T-3","subject":"Same Subject"}` and `{"id":"T-4","subject":"same subject"}` produced exactly one file, `same-subject.md`, containing only T-3's content; T-4 vanished with exit 0 and the `[bridge] 1 task note(s)` line implying success. Same for two long subjects differing only after character 80 (both truncate to the same 80-char slug).

FIX: Track slugs written during the run and, on collision with a different id, either suffix (`slug-2.md`, mirroring board.py's `~2` disambiguation) or emit a `[bridge] warning:` line naming both ids so the loss is visible.

### board.html:263 [reproduced]
A deck's category colour is passed verbatim into a CSS custom property used as `background:var(--c)`, so a deck can make the otherwise fully offline board issue outbound network requests.

FAILURE: Empirically confirmed with a real request. Rendered a deck with `"categories": {"build": "url(https://evil.example/pixel.png)", "docs": "red"}` — the documented object form (reference/board.md: 'or supply explicit { "name": "oklch(...)" }'). normalize() line 263 assigns it straight into catColors, render() line 315 does `k.style.setProperty("--c", catColor(cat))`, and `.legend .k i{background:var(--c)}` (line 83) consumes it. Live DOM: swatch backgroundImage = `url("https://evil.example/pixel.png")`, and the network log shows `[GET] https://evil.example/pixel.png => net::ERR_NAME_NOT_RESOLVED`

FIX: Validate the colour before assigning it: accept only values matching a strict colour pattern (oklch/hsl/rgb/#hex/named), falling back to the palette hue otherwise. `CSS.supports('color', v)` is a one-line gate that rejects `url(...)`.

### board.html:18 [reproduced]
`--text-faint` at the 11px `--fs-micro` size measures 3.43:1 against `--bg`, below the 4.5:1 WCAG 1.4.3 requirement for normal-size text — and it is the colour of the per-lane card counts, the empty-lane markers, the connection status, and the entire footer help text.

FAILURE: Measured in Chromium by canvas pixel readback: `--text-faint` = oklch(62% 0.005 280) against `--bg` = rgb(248,248,250) gives 3.43:1, and 3.64:1 against `--surface`. 11px is far below the 18.66px large-text threshold, so 4.5:1 applies. Live element checks: `.lane-head .ct` (the card count per stage) computes to 11px at 3.43:1, and `.foot` — the paragraph that is the only documentation of the [ / ] keyboard shortcut, the connect-file flow, and the wip-limit syntax — is also 11px at 3.43:1. `.conn`, the sole save-status indicator, is the same. For comparison `--text-dim` measures 7.01:1 and `--te

FIX: Darken `--text-faint` to roughly oklch(48% ...) so it clears 4.5:1 at 11px (and the dark-mode counterpart oklch(52%) likewise), or raise `--fs-micro` for the `.foot` and `.lane-head .ct` roles. Drop the `.stamp` opacity and use a lighter border instead.

### board.html:344
The synthetic Unfiled lane registers a dragover handler that paints the drop affordance, then the drop handler silently refuses the drop — a dead target that lies about being live.

FAILURE: laneNode() is shared, so the Unfiled lane created at line 353 gets the same `dragover` listener (line 338) that calls preventDefault(), sets dropEffect="move", and adds the `.drop` class — which renders `outline:1.5px dashed var(--border-strong)` (line 101), the identical affordance every real lane shows. But line 344 guards with `col.id!=="__unfiled"`, so releasing does nothing. Concrete failure: a user hand-edits board-data.json to remove a column, sees the orphaned cards appear in UNFILED, drags a card from Backlog over UNFILED to group it there, gets the dashed accept outline and a move cu

FIX: Skip the dragover/drop listeners entirely for `__unfiled` (or set dropEffect="none" and never add `.drop`) so the lane reads as inert, which it is.

### board.html:204
The BUILT/PARKED stamps and the muted-lane treatment hardcode the column ids `done` and `icebox`, silently breaking for the custom lanes that merge_deck goes out of its way to preserve.

FAILURE: `STAMP={done:[...],icebox:[...]}` (line 204, consumed at 296) and `(col.id==="done"||col.id==="icebox")?" muted":""` (line 324) key on literal ids. board.py's merge_deck lines 273-277 deliberately preserve user-edited `columns` across a re-seed ("Columns are user-ownable deck data (added/renamed lanes)"), and reference/board.md documents both the custom-lane support and the stamps as features. Concrete failure: a user renames the terminal lane's id from `done` to `shipped` in board-data.json — a supported, documented edit that survives every re-scaffold — and the BUILT rubber stamp and the mut

FIX: Move the stamp label and the muted flag into the column object itself (`{"id":"shipped","name":"Shipped","stamp":"BUILT","muted":true}`), defaulting from the current ids for existing decks, and document the keys alongside `wip`.

### board.html:343
The drop handler resolves the dragged card by `state.cards.find(c=>c.id===id)`, so with duplicate ids in the deck it moves the first match rather than the card the user dragged — and board.py only de-duplicates on the tasks path.

FAILURE: dragstart (line 297) puts only `card.id` on the dataTransfer, and drop (line 343) resolves it with `.find()`, first-match. cards_from_tasks() de-dupes ids with a stderr warning (board.py:155-165), but the `--data` path (board.py:350-373) and a hand-edited deck have no such check. Concrete failure: a deck with two cards both id `T-1`, one in `backlog` and one in `doing`. The user drags the `doing` one to `done`; the backlog copy jumps to Done instead and the dragged card does not move. moveCard()'s focus restore at line 277 has the same first-match bug via `querySelector`. The same duplicate th

FIX: Give each rendered ticket a render-unique key (array index or a generated uid) alongside data-id and drag on that. Separately, have normalize() detect duplicate ids and surface them in the UI rather than letting them resolve arbitrarily.

### test_board.py:384
None of the 48 board tests and no validator executes a single line of the template's JavaScript, so every defect above sits in code with zero automated coverage and no guard here would fail a test if it were deleted.

FAILURE: test_board.py touches board.html only as text: test_injects_deck_between_markers and test_escapes_script_breakout slice the payload out by string index and assert on the JSON. validate.py's board-template-markers check (validator 25) only asserts the markers exist and the seeded JSON parses. There is no JS test harness anywhere under adjudant/scripts. Concrete consequence against the repo's own stated standard that every guard must have a test that fails when the guard is removed: delete the null-coalescing in cardMatches (line 213), whose comment explicitly calls it a guard — 'undefined must 

FIX: Add a small Node-based test that loads the emitted board.html into a DOM shim (or drives it with Playwright, already available in this repo's plugin set) and asserts the guard behaviours: orphan cards land in UNFILED, a rename in the deck reaches the DOM, a failed setItem surfaces a visible error, and a card with no category still gets a visible focus ring.

### graph.py:55 [reproduced]
_q's newline neutralisation (`.replace("\n", " ")`) is uncovered. test_labels_with_quotes_are_sanitized (test_graph.py:67) exercises only the quote branch, so removing the newline replacement alone leaves the suite green.

FAILURE: VERIFIED by mutation: deleting `.replace("\n", " ")` from _q leaves all 79 tests OK. (Deleting the quote replacement as well IS caught, by the `assertIn("'quoted'", g)` assertion — so the quote half is covered and the newline half is not.) Concrete failure: board.html lets a user type a card title, and the deck stores it verbatim, so a title of `fix\nthe widget` makes board_graph emit ` c0["fix` and `the widget"]` on two lines. The fenced block graph.py hands back for pasting into a session note is then unparseable mermaid, and Obsidian renders a syntax error where the kanban snapshot should b

FIX: Extend test_graph's TestBoard with a deck whose card title contains a literal newline (and a `"`), assert the generated block has the same number of lines as the un-newlined equivalent and that json/mermaid node lines stay one-per-line. Cheaper still: unit-test `graph._q` directly against `'a\nb'`, `'a"b'`, `' padded '`.

### board_bridge.py:150 [reproduced]
Two distinct ledger survivors whose subjects kebab to the same slug collapse into one note, and the loser is dropped with no warning. bridge_ledger's dedupe (`if note.exists(): continue`) is documented as protecting notes already on disk, but it also fires within a single batch because the first survivor writes the file before the second is considered. board.py:154-164 already handles the analogous duplicate-card-id case by disambiguating with a `~2` suffix and warning on stderr; the bridge does neither.

FAILURE: VERIFIED. A ledger containing {"id":"T-6","subject":"Fix the widget!","description":"first"} and {"id":"T-7","subject":"Fix the widget?","description":"second"} produced exactly one note, tasks/fix-the-widget.md, carrying "first". T-7 — a genuinely different task with a different id and a different description — vanished silently: no note, no stderr line, and rc=0. Same collapse for any subject pair differing only in punctuation, casing, or trailing/leading symbols, which is common for tasks created a few minutes apart in one session.

FIX: Track slugs written during the batch in a local set and, on collision, fall back to `{slug}-2`, `{slug}-3` (mirroring board.py's `~2` convention) rather than skipping; or at minimum emit the same style of stderr warning board.py does so the loss is visible. Keep the existing on-disk dedupe unchanged.

### board_bridge.py:160 [reproduced]
bridge_ledger's docstring promises "One failed write skips that survivor only, never the batch", but the handler is `except OSError` only. Any non-OSError from render_task_note or write_text — UnicodeDecodeError on a corrupt template, UnicodeEncodeError on the note text (both are ValueError subclasses) — propagates out of bridge_ledger, and main() has no try around the bridge_ledger call at line 189, so the process tracebacks and every remaining survivor is lost. The same gap exists one call earlier: main() catches only VaultUnresolvableError from smart_project_dir, so a decode failure inside parse_breadcrumb escapes uncaught.

FAILURE: VERIFIED, both halves. (a) With a two-entry ledger where the first description contains non-ASCII, `LC_ALL=C python3 -X utf8=0 board_bridge.py --bridge ... ` tracebacks with UnicodeEncodeError at board_bridge.py:158, rc=1, leaving a zero-byte cafe-alpha.md and never reaching the second, perfectly-writable survivor T-2. (b) Appending the bytes `\xff\xfe binary junk` to a valid `.claude/adjudant` breadcrumb and running `board_bridge.py --ensure-only --project-dir <repo>` tracebacks with UnicodeDecodeError out of _vault_walk.parse_breadcrumb, uncaught. Both are survivable at hook time only becaus

FIX: Widen the per-survivor handler to `except (OSError, ValueError)` so the docstring is true, and wrap the `bridge_ledger(...)` call in main() in a broad `except Exception` that logs to stderr and falls through to ensure_board — the bridge already does exactly that for ensure_board at line 195, and a hook-invoked writer should degrade the same way on both halves. Give parse_breadcrumb an errors-toler

### board_bridge.py:91 [reproduced]
A ledger entry whose id is falsy-but-present is treated as having no id and skipped: `tid = str(entry.get("id") or "").strip()` turns an integer 0 or a boolean false into "", which the next line rejects. The same shape appears upstream at hooks/scripts/task-ledger.py:56 (`str(payload.get("task_id") or "").strip()`), so such a task never even reaches the ledger.

FAILURE: VERIFIED. A ledger containing {"id": 0, "subject": "Zero id task"} and {"id": false, "subject": "False id task"} produced no notes at all for either entry, while the string-id entries in the same file were written normally. Currently unreachable in practice (Claude Code task ids are strings like `T-1`), so this is latent rather than live — but it is a silent-drop shape duplicated in two files, and a harness change to zero-based integer task ids would lose exactly one task per session with no diagnostic.

FIX: Use an explicit None test instead of truthiness in both places: `raw = entry.get("id"); tid = "" if raw is None else str(raw).strip()`. Add a read_ledger unit test covering id 0, id false, id "" and a missing id key, asserting only the last two are dropped.

### test_board_bridge.py:141 [reproduced]
No test exercises board_bridge's project resolution. _BridgeCase.setUp always builds `tmp/vault/projects/demo` and passes that already-resolved path as --project-dir, which `_looks_like_vault_project` short-circuits, so smart_project_dir's breadcrumb branch is never entered from this module. Consequently there is no coverage of: a code root with a `.claude/adjudant` breadcrumb, a project shelved to `_fridge`/`_archive`, an unresolvable vault, or a hostile slug.

FAILURE: The zone-awareness the plugin now guarantees is unprotected against regression here specifically. I confirmed by hand that it currently works — breadcrumb `slug: demo` + a project at vault/projects/_fridge/demo resolved correctly and wrote tasks/zone-check.md and board/ into the fridged copy — but nothing in the suite would catch a future change to find_project_dir or resolve_project_from_cwd that reintroduces the ghost-twin bug validator 30 exists to prevent, because every board_bridge test bypasses that code path entirely. It is also why finding #1 shipped undetected.

FIX: Add a _BridgeCase variant that builds a code root with a real `.claude/adjudant` (slug + vault_path) and passes THAT as --project-dir, then assert: (a) notes land in vault/projects/demo, (b) with the project moved to projects/_fridge/demo they land in the fridged dir and no projects/demo twin is created, (c) a `slug: ../../escape` breadcrumb writes nothing and returns non-zero, (d) a breadcrumb wh

### graph.py:160 [reproduced]
Relations truncation is reported only as a mermaid `%%` comment inside the fence — which is invisible in the rendered diagram — and never on stderr, so the rendered deliverable presents a partial graph as complete.

FAILURE: 81-file project, default cap: `graph.py --mode relations --out r.md` emitted 30 nodes with ` %% 51 low-degree file(s) omitted (--max-nodes 30)` as line 3 of the fence, and stderr contained only `[graph] wrote .../r.md` — no mention of the 51 dropped files. Mermaid strips `%%` lines at render time, so a reader of the note in Obsidian sees a 30-node graph with nothing indicating that 63% of the project was cut. With `--out` the operator never sees the fence text at all, so the only channel carrying the truncation is one they did not read. (Secondary: `degree` is computed once at line 140-143 and

FIX: Print the omission count to stderr as well as into the fence, and mention it in `--out` mode's confirmation line: `[graph] wrote X (51 of 81 files omitted at --max-nodes 30)`. Assert the stderr line in a CLI test.

### graph.py:55 [reproduced]
`_q` does not escape `<`, `>` or `&`, which `reference/mermaid-generation-rules.md` §2 (line 27-28) explicitly mandates and §8 (line 79-83) claims graph.py "applies mechanically". The docstring on line 54 also claims "no raw brackets/newlines" while the body only handles newlines.

FAILURE: A card titled `fix <br> handling` produces `c0["T-3 · fix <br> handling"]` verbatim (confirmed by running board mode against a deck with `"title": "a <b> and & amp"`). Mermaid parses it, but flowchart labels are rendered as HTML, so the literal tag text is consumed by the renderer instead of displayed — the card reads `fix handling` with a stray line break. `board.py:290-292` escapes `<` for exactly this class of reason (`"Escape every `<` as \\u003c ... so a task title containing `</script>` or `<!--` can't break out"`), so the plugin already knows the hazard; graph.py is the surface that mis

FIX: In `_q`, escape `&` → `&amp;` first, then `<` → `&lt;` and `>` → `&gt;`. Fix the docstring to describe what the function actually does. Add a test with a `<`-bearing card title.

### graph.py:266 [reproduced]
Two reachable inputs escape the error handling and dump a Python traceback instead of the `error: ...` line the CLI otherwise emits: a deck whose top-level JSON is not an object, and an `--out` path whose parent directory does not exist.

FAILURE: (1) `board-data.json` containing `[]` (valid JSON, wrong shape) → `AttributeError: 'list' object has no attribute 'get'` at graph.py:183. The `except` at line 266 catches OSError/JSONDecodeError/FileNotFoundError but not AttributeError/TypeError. (2) `graph.py --mode tiers --out /some/missing/dir/x.md` → `FileNotFoundError: [Errno 2]` raised from line 271, which sits *outside* the try block, so even the caught type escapes there. Both were reproduced. A traceback in a helper that a skill shells out to is noise the model has to interpret rather than a message it can relay.

FIX: Validate the deck shape after `json.loads` (`if not isinstance(deck, dict): raise ValueError(...)`), widen the except to include ValueError/TypeError/AttributeError, and move the `--out` write inside a try that returns 1 with an `error:` line (after mkdir-ing the parent).

### test_graph.py:67 [reproduced]
Two guards in graph.py have no test with teeth: the newline collapse in `_q` survives being deleted, and `cli_main` — including the entire `--out` write path and `smart_project_dir` resolution — has zero coverage across all 14 tests.

FAILURE: Mutation-tested against a copy of the module. Mutant A (delete `.replace('\"', \"'\")`) → 1 failure, guard has teeth. Mutant B (delete `.replace(\"\\n\", \" \")`) → all 14 tests pass, guard is unprotected; that guard is what keeps a card title containing a newline followed by a code fence from terminating the surrounding ```mermaid block early. Mutant C (neuter orphan accounting) → 1 failure, has teeth. Separately, `grep -n 'cli_main|--out|args.out' test_graph.py` returns nothing — the file imports only `board_graph`, `fenced`, `relations_graph`, `tiers_graph`, so the highest-risk code in the 

FIX: Add a `TestCli` class driving `cli_main` for each mode, plus tests for the --out guards from finding 1 (refuses outside the project dir, refuses to clobber without --force, writes a .bak with --force). Add a `_q` test with a literal `\n` in a card title. Delete or replace the vacuous `assertNotIn('""')` assertion.

### draw.md:84 [reproduced]
Nothing in the plugin validates `.canvas` or `.base` shape — or even that they are parseable JSON/YAML — before or after they are written. draw.md's "Fail conditions" section lists only the two breadcrumb/existing-file cases and names no shape check.

FAILURE: `.canvas` and `.base` are written by the model directly (there is no helper script for them — `grep` across `scripts/*.py` shows the only mentions are `INDEXABLE_LINK_EXTS` at `_vault_walk.py:197`, the link-index glob at `_vault_walk.py:380-384`, and a *filename* kebab-case check in `ramasse_scan.py:276`). No code path ever `json.loads` a `.canvas`. So a canvas written with a trailing comma, a missing `nodes` array, or an `edges` entry referencing a nonexistent node id is accepted silently, is indexed as a valid link target by `build_vault_index`, and then fails to open in Obsidian with no war

FIX: Add a shape check to the draw verb: after writing a `.canvas`, `json.loads` it and assert `nodes`/`edges` are lists and every edge's `fromNode`/`toNode` matches a node `id`; after writing a `.base`, parse the YAML. Wire the same check into `check.py` so an already-broken artefact is reported. Document it under draw.md's "Fail conditions".

