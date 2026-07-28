# Adjudant robustness audit - 2026-07-27

Three empirical audit passes against v0.16.0 (hooks runtime, shared primitives,
destructive write paths), each running the real scripts against hostile fixtures
in a scratchpad, plus a docs check of the hooks schema. 42 findings; 13 HIGH.
Fixtures preserved under the session scratchpad (`audit-hooks/`,
`audit-primitives/`, `audit-verbs/`).

This document is the source of truth for the v0.17.0 hardening release.

## Verdict

Architecture sound, implementation has a real bug cluster. The safety-critical
invariants that were attacked and held: shelf's transaction design, dream and
ramasse being provably read-only, YAML parser fuzz resistance (220 mutations,
zero exceptions), board HTML injection escaping, concurrent session-note
appends, shell quoting under space-and-unicode paths, session-id sanitization
in task-ledger. The failures cluster in the hooks and in cross-module
agreement about who owns which frontmatter key.

Strongest signal: three independent agents converged on hooks not being
zone-aware. That is the defect to fix first after the security tier.

## Hooks schema check (resolved in adjudant's favour)

All wiring in `hooks/hooks.json` is valid against current docs:
`TaskCreated`, `TaskCompleted`, `PostCompact` are real events; `"if"` with
permission-rule syntax is real and prevents the hook process from spawning at
all; `"async": true` is real. Matchers are pipe-separated exact matches and
`MultiEdit` no longer ships, so the `Write|Edit` matcher has no gap.
Undocumented: whether a mid-session plugin cache swap keeps old hooks.

## Tier 1 - security (fix first)

External or careless input causing writes outside the vault.

1. **HIGH - slug path traversal.** `hooks/scripts/session-start.sh:144-147`
   and `precompact.py:155-158` interpolate an unsanitized `slug` from
   `.claude/adjudant` straight into `mkdir -p`. A repo-committed breadcrumb
   with `slug: ../../../escaped` made SessionStart create
   `<scratchpad>/escaped/sessions/<date>.md` two levels above the declared
   vault on first open, no user action. `vault_path` is also accepted for any
   existing directory with no vault-shape check. `noclobber` saves existing
   files but precompact's `_handoff.md` uses `write_text` and does clobber.
   Fix: reject slugs not matching `[a-z0-9][a-z0-9-]*`; require the resolved
   project dir to be under the vault before any mkdir or write.

2. **HIGH - prompt injection via context echo.** `session-start.sh:77` echoes
   the repo-controlled slug verbatim, and SessionStart stdout is injected into
   the model's context before the user types. Fix: validate and truncate
   against a strict charset; never echo raw breadcrumb values.

3. **HIGH - dry-run forges release records.** `posttooluse-commit-log.py:236-241`
   `_COMMIT_RE` does not exclude `--dry-run`, so
   `git commit --dry-run -m "release(x): v9.9.9"` scaffolded a real
   `releases/v9.9.9.md` plus its index row. Fix: bail on `--dry-run`,
   `--short`, `--porcelain`, `--long` before the success gate.

4. **HIGH - success check fails open.** `posttooluse-commit-log.py:83-108`
   `response_indicates_success` looks for exit-code keys the Bash
   `tool_response` never carries, so `nothing to commit, working tree clean`
   was logged as a real commit. The docstring's "never claim an effect that
   was not verified" is a no-op. Fix: verify against git
   (`git -C <repo> log -1 --format=%s` matches the parsed subject).

5. **LOW (same file) - unescaped subjects.** Commit subjects land in the
   session note verbatim, so `[[projects/other/decisions/secret]]` in a
   subject becomes a live wikilink that check scores as broken. Forging a
   second log line via newline correctly failed. Fix: escape `[[`/`]]`, cap
   length.

## Tier 2 - zone awareness (triple-converged)

6. **HIGH - no hook is zone-aware.** `session-start.sh:144`,
   `precompact.py:155`, `postcompact.py:127`, `posttooluse-vault-log.py:101`,
   `sessionend.sh:65` all hardcode `projects/<slug>` while shelf moves
   projects to `projects/_fridge/` and `projects/_archive/`. Empirically: a
   shelved project got a phantom active-zone `sessions/<date>.md` on the next
   SessionStart, precompact rewrote a phantom `_handoff.md` every compaction,
   and a Write into the archived project logged nothing - silently dropped.
   `_vault_walk.find_project_dir()` exists for exactly this; no hook calls it.
   Fix: route every hook through a `find_project_dir` shim; no-op when it
   returns None.

7. **HIGH - subdirectory escape writes into the code repo.**
   `_vault_walk.py:620-621` smart_project_dir's no-breadcrumb fallback accepts
   any directory as an already-vault-project dir with no walk-up. Running
   `board.py --ensure --project-dir <repo>/backend/svc` returned rc=0 and
   wrote `board-data.json` plus `board.html` inside the code repo. `tidy.py:845`
   and `board_bridge.py:180` share the line, so a tidy preview/apply from a
   subdir rewrites repo markdown - the exact hazard VaultUnresolvableError
   documents as impossible. Fix: walk up looking for `.claude/adjudant` first;
   require a vault-project marker (brief.md, or a parent named `projects` or a
   zone) before accepting the direct-path branch.

## Tier 3 - data loss in write paths

8. **HIGH - tidy apply clobbers edits made after preview.** `tidy.py:807-820`
   records `original_hash` in changes.json but never checks it at apply; a
   paragraph appended to a live file after preview vanished when the stale
   proposal was copied over it. The backup captures the edited version, but
   nothing warns. port.py already implements this guard for AGENTS.md. The
   vault is also multi-machine synced. Fix: compare live hash to
   `original_hash` at apply; skip-with-warning or abort on mismatch.

9. **HIGH - shelf bakes U+FFFD into files.** `shelf.py:232-235,247-251` reads
   with `errors="replace"` and writes the replaced text back; a latin-1 byte
   became a permanent replacement character. tidy explicitly avoids this exact
   round-trip. Fix: strict-decode, skip-and-report undecodable files.

10. **HIGH - interrupted port apply wedges.** `port.py:659-671` writes project
    files first, then vault changes with no rollback; a colliding rename raised
    a raw OSError mid-loop. Retry is then blocked by port's own staleness guard
    (the recorded hash versus the AGENTS.md the failed apply wrote), and
    re-previewing reports "Already ported" because compliance checks only
    project-side files. Vault left permanently half-migrated, silently. Fix:
    shelf-style try/rollback; record the post-apply hash, or delete the preview
    only after vault changes succeed.

11. **HIGH - board `--data` overwrites without backup.** `board.py:331-347`
    gates both the refusal guard and the `.bak` escape hatch on `force`, so
    `scaffold --data foo.json` replaced a deck (cards, custom lane, title) with
    no backup. Fix: back up on any overwrite of an existing deck.

12. **MEDIUM - backup timestamp collision destroys the only backup.**
    `tidy.py:800-802` uses second-granularity dirs with `exist_ok=True`; an
    interrupted apply retried within the same second reused the dir and
    overwrote the original `.legacy` files with already-tidied content. Fix:
    mkdtemp under the backup root, or never overwrite an existing `.legacy`.

13. **MEDIUM - projects-index upsert corrupts hand-maintained tables.**
    `connect.py:565-615` inserts the canonical row after the first `|---|`
    anywhere in the file, landing inside an unrelated table. port.py has the
    "unknown format, do not write" guard; connect, sync and shelf use the
    unguarded version. Fix: port the canonical-header check across.

14. **MEDIUM - repo repair deletes file content.** `repo_tidy.py:93-99`
    classifies a regular file at a harness link path as "missing", unlinks it
    and symlinks over it; the `.legacy` record holds only metadata, so content
    is gone. A directory there crashes apply mid-loop. Fix: back up content or
    refuse.

15. **MEDIUM - port staleness guard covers AGENTS.md only.** CLAUDE.md edits
    between preview and apply are silently clobbered. Fix: hash CLAUDE.md and
    the breadcrumb into source-hash.txt too.

16. **MEDIUM - breadcrumb rewrite drops unknown keys.** `connect.py:277-298`
    preserves via a hardcoded allowlist, so any future or user-added key is
    lost on every re-connect (v0.16.0's stamp_source_session preservation
    works, but only because it is on the list). Fix: carry unrecognized keys
    through.

17. **LOW - tidy apply trusts changes.json paths.** A tampered proposal keyed
    `../../escaped.md` was written outside the project dir, bypassing backup.
    The preview window exists precisely for human and agent editing. Fix:
    resolve and require containment under project_dir.

## Tier 3 status: closed 2026-07-28

All four HIGH findings plus the five MEDIUM/LOW ones fixed, tested,
committed. 808 tests, 30 validators.

- 8 + 12 + 17 (tidy apply): re-hashes each live file against `original_hash`
  and leaves changed ones alone, reported in `{backup}/SKIPPED-STALE.txt`,
  on stderr, and in a `skipped_stale` JSON key - a silent skip would be
  nearly as bad as the silent clobber it replaces. Each apply gets its own
  mkdtemp backup dir. Both sides of every copy are resolved and required to
  stay inside their root.
- 9 (shelf): both write-back paths decode strictly; undecodable files are
  skipped byte-identical and reported in `skipped_undecodable`, since their
  wikilinks still point at the old path.
- 10 + 15 (port): `validate_vault_changes` pre-flights every line and
  refuses before any write, shelf-style, leaving the preview intact so a
  retry works once the conflict is resolved. The staleness guard now hashes
  CLAUDE.md as well as AGENTS.md.
- 11 (board): any deck-replacing path backs up first, not just `--force`.
- 13 (index upsert): rows land only under the canonical 6-column header.
- 16 (breadcrumb): unknown keys carry through by construction.
- 14 (repo_tidy): real files get their bytes preserved; real directories are
  refused and recorded.

Also dropped the now-false shelf.md rule telling users to unshelve before
working on a fridged project - hooks became zone-aware in tier 2.

## Tier 4 - concurrency and atomicity

18. **MEDIUM - no atomic writes anywhere.** `_session_stamp.py:94-118`,
    `board.py:382` and every read-modify-write in these modules lack temp-file
    plus `os.replace` and any locking. Empirically 19 of 30 concurrent
    session-id updates lost a UUID, and a poller caught 35 torn or empty deck
    reads in 20 seconds; one board ensure failed spuriously on a mid-truncate
    read. Fails closed (skipped refresh) rather than corrupting, but updates
    are genuinely lost. Fix: temp-file plus os.replace everywhere, flock around
    read-merge-write.

## Tier 5 - correctness and hygiene

19. **MEDIUM - future-dated note captures every fallback write.** Five call
    sites take `sorted(glob)[-1]` with no upper bound, so a `2029-12-31.md`
    (clock skew, restored backup) permanently absorbs midnight-straddle
    appends. `_vault_walk.newest_dated_stem` validates calendars; these do not.
    Fix: filter to real dates not after today.

20. **MEDIUM - commit-log misses real commit forms.** `_COMMIT_RE` matches only
    a literal leading `git commit`, dropping `git -C /repo commit` and
    `(cd /r && git commit ...)`. Separately the harness `if` gate uses prefix
    syntax and cannot match the `cd ... && git commit` form the script is
    explicitly written to strip, so the two layers contradict: the hook never
    spawns for commits from a non-cwd repo. Fix: widen the regex; drop the `if`
    (the script self-gates) or widen the pattern.

21. **MEDIUM - vault-log pays full import cost on the no-op path.**
    `posttooluse-vault-log.py:30-51` imports the 1100-line `_vault_walk` before
    the breadcrumb check, and it is the only PostToolUse hook that is not
    async, so it blocks every Write/Edit machine-wide. Measured: 18.8 ms bare
    python, 36.5 ms with no breadcrumb, 37.1 ms linked. Fix: move imports
    inside main below the breadcrumb check; add `async: true`.

22. **MEDIUM - hooks exit before consuming stdin.** PostToolUse payloads carry
    the full `tool_input.content` of a Write. An 8 MB payload EPIPE'd the
    harness writer (`BrokenPipeError`); precompact.py never reads stdin at all.
    Harness EPIPE behaviour is undocumented. Fix: read stdin first, then gate.

23. **MEDIUM - board refresh scales inside a capped hook.** `cards_from_tasks`
    full-reads every task note on every task-note Write, inside a 3 s
    subprocess cap. 500 notes measured at 103-137 ms on local SSD; on dataless
    iCloud files each read is a network materialization. Fix: debounce on deck
    mtime, make it async.

24. **MEDIUM - board.html never re-rendered on the ambient path.**
    `board.py:440-441` short-circuits before scaffold on no-change, so after a
    plugin upgrade ships a new template, quiet projects serve stale HTML
    forever. Fix: stamp a template hash and re-emit html-only on drift.

25. **MEDIUM - stamp defeated by newline translation.** `_session_stamp.py:44`
    the `_FM_OPEN = "---\n"` guard never sees CRLF because `read_text()`
    translates it, so CRLF files are stamped and rewritten entirely as LF -
    every line churns in git and sync. Non-UTF8 raises UnicodeDecodeError and
    read-only files raise PermissionError from the direct-call API, against the
    module's safe-skip contract. Fix: read with `newline=""`; catch decode and
    OS errors inside the primitives.

26. **MEDIUM - vault_name fallback accepts any directory.**
    `_vault_walk.py:459-484` has no `.obsidian`/`projects` shape check and its
    fixed order prefers legacy locations over CloudStorage mounts, so a stale
    same-named directory silently captures all writes on the fallback machine.
    An empty directory was accepted. Fix: require a vault marker.

27. **MEDIUM-LOW - empty or list status passes schema-clean.**
    `_vault_walk.py:820-828` only checks non-empty `str`, so a blank `status:`
    (parsed None) or a list value is invisible drift while literal `null` is
    flagged - an inconsistent trio. Fix: flag present-but-None, list, or empty.

28. **LOW-MEDIUM - Home.md match is not frontmatter-scoped.**
    `_vault_walk.py:530-542` matches `^type: vault-home` anywhere in the file
    (MULTILINE), so a prose Home.md up-tree becomes "the vault". Fix: parse
    frontmatter and check the field.

29. **LOW-MEDIUM - OB_VAULT accepts a relative path** and returns it
    unresolved, so the override built to enforce the same-vault invariant can
    itself break it across processes with different cwds. Fix: expanduser and
    reject non-absolute.

30. **LOW - BOM hides frontmatter.** `parse_frontmatter` returns has_block=False
    with no parse_error for a BOM-prefixed note, so it silently drops out of
    type inventory and schema checks while Obsidian renders it fine. Fix:
    `lstrip("﻿")` at entry.

31. **LOW - assorted:** stamp follows symlinks outside the vault on direct
    calls (the hook's containment guard protects hook flow); a closing fence at
    EOF without trailing newline is parseable but not stampable (two grammars
    drifted); id-less board cards collapse onto one `str(None)` key so a reseed
    deletes all but one; `_handoff_freshness` activity regex matches any `d:dd`
    token so prose like "ratio 3:45" skews the stale banner; `board_bridge`
    `read_ledger` drops a falsy-but-real id of `0`; user-prompt-reminder's
    keyword regex fires on everyday English ("give me a brief summary") and
    leaks one marker file per session in TMPDIR; `_session_stamp` docstring
    claims connect.py stamps session_id, which it never does; project `_archive/`
    and `scratch/` are not in DEFAULT_SKIP.

## Already fixed (2026-07-27, committed)

- task `id:` and handoff `session_id:` restored to FIELD_SCHEMA optional sets
  with regression tests naming the reader. tidy's v0.16.0 schema strip was
  destroying board card identity (reseed re-keyed the dragged card to the file
  stem, iceboxing it and creating a duplicate) and deleting handoff keys the
  sync mirror contractually preserves.
- FIELD_SCHEMA optional sets widened for descriptive fields (`related`,
  `title`, `name`, `description`, `superseded_by`, `implemented_verified`).

## Tier 1 status: closed 2026-07-28

All five security findings fixed, tested, committed. 780 tests, 29 validators.

- Findings 1+2: `_vault_walk` now owns the slug rule (`SLUG_RE`,
  `is_safe_slug`, `safe_project_root`); connect.py imports it, making port.py's
  "single source of the kebab-case rule" claim true. All five slug-consuming
  hooks gate on it, the Python ones with a stdlib-free fallback so a broken
  import cannot reopen the hole. Verified: zero artifacts outside the vault
  across all four hooks; happy path unchanged.
- Findings 3+4+20: commit-log asks git (`git log -1 --format=%s` must equal the
  parsed subject) instead of trusting a payload that carries no exit code;
  refuses `--dry-run`/`--short`/`--porcelain`/`--long`; accepts the `-c`/`-C`
  global-option forms. Test fixtures are now real git repos - the old ones
  passed only because the hook trusted the payload.
- Finding 5: `log_safe` neutralizes `[[`/`]]`, flattens newlines, caps at 200.

## Tier 2 status: closed 2026-07-28

Findings 6 and 7 fixed, tested, committed. 792 tests, 30 validators.

- Finding 6: all six hooks resolve zone-aware (python via find_project_dir,
  bash via a zone_project_dir mirror kept in-shell so degraded mode matches and
  no extra subprocess runs per session). Each no-ops when the project exists in
  no zone instead of creating it, which also closes phantom-project-from-an-
  unconnected-slug; session-start reports the condition rather than going quiet.
  Reported note paths now name the real zone. commit-log also picked up the
  tier-1 slug guard it had been missing.
- Finding 7: smart_project_dir walks up for a breadcrumb before falling back,
  so a helper run from a subdirectory of a connected repo resolves to the vault
  project instead of writing into the code repo; a directory holding repo
  furniture without vault-project markers is refused outright.
- Validator 30 (hook-zone-awareness) forbids `projects/<slug>` in any hook and
  requires both guards. Verified by deliberately reintroducing the bug and
  watching it fail.

## Parked: archive verb decisions (locked with Tom, 2026-07-27)

Brainstorm paused at the approaches step in favour of hardening first. Decided:

- **Perma-memory**: a new per-project `MEMORY.md` (all caps, like `AGENTS.md`),
  schema-typed, never archived and never staled. The deep-analysis pass appends
  dated, sourced entries under themed headings; check and sitrep can surface it.
- **Destination**: project-root `archived-context/` mirroring the original
  structure (`archived-context/sessions/2026-05-27.md`), added to the walker
  skip set so check, dream, ramasse, board and the cost estimator stop paying
  for it. Still greppable and Obsidian-searchable. A manifest `_index.md`
  records what moved when.
- **Scope**: `sessions/`, `dreams/`, `notes/` (by `updated:`), and `tasks/` in
  terminal states (done, icebox) untouched 30+ days. Never `references/`,
  `specs/`, `releases/`, `decisions/`, `brief.md`, `_handoff.md`, `MEMORY.md`,
  or board files.
- **Trigger**: a verb with two-phase preview then apply, plus an ambient nudge
  from check, sitrep and SessionStart when eligible files pile up. Automatic
  awareness, human-confirmed action.
- **Deep analysis**: before anything moves, a judgment pass over the outgoing
  set proposes durable facts for promotion into `MEMORY.md`, so archiving is
  lossless in substance even when it is lossy in volume.

Still open: verb name, threshold configurability (breadcrumb knob versus flag),
and the exact analysis-to-promotion contract.

## Design constraint for the parked archive verb

The archive verb is a mover, the most destructive shape in the plugin. It must
inherit shelf's transaction pattern (re-plan at apply, abort before any write,
manifest backup), not tidy's, or it inherits finding 8 by construction. Plus
containment checks (17), atomic writes (18), and zone awareness (6) from birth.
