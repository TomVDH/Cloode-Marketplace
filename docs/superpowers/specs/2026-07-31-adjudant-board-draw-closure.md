# Board and draw audit: closure record

Companion to `2026-07-30-adjudant-board-draw-audit.md`. That document is the
findings; this one records what was done about them, and the judgment calls that
are worth keeping. Written into tracked `docs/` deliberately: the audit itself
spent four releases invisible in a gitignored `.superpowers/` scratch directory,
which is why v0.20.0 through v0.23.0 closed audit tiers 4 and 5 and left every
board and draw finding untouched.

## Status: closed

| surface | shipped in | what closed |
|---|---|---|
| `board.py` | v0.19.0 | merge_deck silent deletion, self-destroying backup, `--project` traversal + containment, U+FFFD zombie cards, atomic + locked deck write |
| `_vault_walk`, `port.py` | v0.19.0 | the verb-path slug gate (hooks had it, verbs did not) |
| `graph.py` | v0.24.0 | `--out` containment/backup/atomicity, `_q` label sanitising, board_graph cap + classDef, stderr truncation, traceback suppression, CLI branch coverage |
| `templates/board.html` | v0.25.0 | all 13 findings: data loss, accessibility, correctness |

49 findings raised, 26 adversarially verified, 26 confirmed, none refuted.

## Judgment calls worth keeping

**A guard was removed for failing its own bar.** A `safe_project_root` call in
board.py's slug helper survived mutation, meaning nothing depended on it. It was
protection in name only, so it went. The rule that made this visible: a guard
that cannot be made to fail is not a guard.

**The board's persistence model changed shape, not just its error handling.**
The browser layer used to persist the whole deck blob, keyed against the SET of
card ids, so a re-scaffold that renamed a card was permanently invisible in the
UI. It now persists ONLY drag overrides and renders every other field from the
freshly seeded deck. One correction the audit missed: the override's `from` lane
must track the current deck, not the first-ever base, or the second move of a
card is silently dropped once the disk absorbs the first. The browser caught
that; static reasoning had not.

**`.canvas` and `.base` output is deliberately unvalidated.** No adjudant code
path writes either format, so a runtime check would mean inventing an
interception point rather than hardening one, and a malformed artefact destroys
nothing and surfaces when Obsidian opens it. `reference/draw.md` now says this
plainly rather than leaving a silent implied guarantee. If a future wave decides
to build it, start at `pretooluse-schema-gate.py`, which already sees every
Write, not at `check.py`.

**Structural tests are labelled as structural.** The 25 Python guards over
`board.html` assert the template's TEXT, not its behaviour. Green means the code
implementing a verified behaviour is still present and still shaped the way it
was when a browser confirmed it. It does not mean the UI works. That warning is
written into the test module itself so nobody later mistakes one for the other.
The exception is the contrast guard, which parses the OKLCH tokens, converts to
sRGB in stdlib Python, and computes the real WCAG ratio.

**Validator 25 grew rather than spawning a 33rd.** The three new rules (seeded
deck has at least one column, template references nothing off-machine, no empty
catch) are properties of the shipped artefact rather than of a code path, so
they must hold against an edit by someone who never runs the Python suite.

## Defects found while fixing, not present in the audit

- An empty but entirely legal deck (`{"columns": [], "cards": []}`) divided the
  node cap by a lane count of zero and answered with `ZeroDivisionError`.
- An `_index.md` needing both a schema fix and an index rebuild appeared in two
  proposal dicts and was applied twice, the second pass overwriting its own
  `.legacy` backup. That is the tidy backup-collision failure mode reappearing
  inside a single run.

## The process lesson

Audit output that is meant to be acted on belongs in tracked `docs/`. A
gitignored scratch directory is the right home for briefs, review packages and
mutation transcripts. It is the wrong home for findings, because the other
machine cannot see them and will confidently ship four releases around them.
