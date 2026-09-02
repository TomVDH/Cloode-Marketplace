# /adjudant status

Makes derived state current, then reports on it. Backed by `status.py`, which
absorbed `sync`, `check`, `sitrep`, `kebab --scan` and the advisor pulse: five
verbs that answered one question between them, and none of which told you which
finding mattered most.

The report has three bands, ordered by the cost of being wrong:

| Band | Means |
|---|---|
| `wrong_now` | The vault is making a claim that is false today. The only band that earns an interruption. |
| `going_stale` | True now, decaying. A nudge, not an alarm. |
| `worth_a_look` | A question rather than a defect. |

## Target `[vault|repo|all]`

Default is `vault` (everything below).

- **`repo`** — audit the *code repo* instead of the vault. Runs
  `python3 "$(dirname "$0")/../../../scripts/repo_scan.py" --project-dir "$REPO_ROOT"`
  and renders the JSON: a version-coherence table (marketplace.json against each
  plugin.json), a symlink-integrity matrix (skills-bearing plugins only), a
  registration check (every plugin registered, every `source` path resolves), a
  stale-plan list, the repo-root context-file and `@AGENTS.md` import check, and
  a single `drift_items` score. Per-plugin context files are shown
  *informational* (not counted). Repo conventions live in
  `reference/repo-standards.md`. Never writes.
  - `token_budget`: per-surface context cost (`file`, `tokens`, `budget`,
    `over`) plus `total` and `over_count`, from `token_budget.py`. Render as one
    line when `over_count` is 0 (`context: ~{total/1000}k tokens across {n}
    surfaces`), and list the offenders when it is not. Report only: it never
    fails a build, and an over-budget surface is a prompt to look, not an error.
- **`all`** — run the vault report *and* the repo scan; render both blocks.

Repo ops use `--project-dir` as the repo root directly (no breadcrumb: the repo
*is* the project dir).

## Run

```bash
python3 "$(dirname "$0")/../../../scripts/status.py" \
  --project-dir "$PROJECT_ROOT" \
  --vault-dir "$VAULT_PATH" \
  --out /tmp/status-{slug}.json
```

Add `--no-sync` for a strictly read-only pass. Add `--estimate-only` for the
cost block alone.

## The make-current phase

The one part that writes, and it writes exactly what `sync` wrote:

1. **Brief refresh** — bump `updated:` in `brief.md`. An undecodable brief is
   left byte-identical and the skip is reported, never silent.
2. **Handoff mirror** — copy the `.remember/` body into `_handoff.md` through
   `_handoff_freshness.render_handoff`, the same renderer the PreCompact and
   SessionEnd hooks use, so a manual run and an auto-compaction produce
   byte-identical handoffs. A blank source is never mirrored. Needs the CODE
   root; without one there is nothing to mirror, which is a state, not a
   failure.

There used to be a third step here, refreshing this project's row in
`projects/_index.md`. That surface is retired: Home groups every project by
lifecycle folder and is generated whole instead, so a hand-upserted row could
only disagree with it.

Results land under `synced.steps`; anything the phase could not do lands in
`synced.warnings`. Report both.

## JSON output shape (top-level keys)

- `synced` — `{today, slug, steps, warnings}` from the phase above
- `wrong_now`, `going_stale`, `worth_a_look` — the three bands, each a list of
  `{signal, file?, detail?, …}`
- `orientation` — momentum: `project`, `purpose`, `freshness` (traffic light and
  age from real activity), `were_doing`, `whats_done`, `board`, `repo` (branch,
  dirty count, recent commits), `server` (dev servers from `.claude/launch.json`,
  probed with a 0.6s HEAD; down is an answer, never an error), `suitcase`,
  `next_step`, `open_signals`, `status`
- `compliance` — `project`, `counts`, `recent`, `handoff`, `drift_signal`,
  `board`, `suitcase`, `remember`, `status`, `schema`, `environment`
- `naming` — vault-standards §4 title violations: `{file, type, suggested, issue}`.
  Read-only; a rename breaks every wikilink pointing at the file, and that repair
  belongs to `clean`, with its preview and its backups
- `advisor` — `{state, pulse}`. The pulse is the read-only context-integrity
  check: `quiet`, `next_step`, `dangling_scopes`, `recent_decisions`
- `cost` — `{est_read_tokens, files, bytes, threshold, warn}`

`handoff` carries two clocks, deliberately. `updated` and `stale_hours` are the
**mirror clock**: when the handoff was last written. Every SessionEnd stamps it
to today, so a mirror of an empty buffer still reads fresh — diagnostic only,
never the answer to "are we drifting?". `light` / `age` / `next` / `stale` come
from `_handoff_freshness`: remember dailies and session-note markers, the same
sensor the hooks render into the handoff banner. **Render the activity clock.**
When the two disagree, the handoff has not been re-synced since the last real
work: say so rather than picking one.

`schema` is frontmatter drift per `FIELD_SCHEMA`, which is the templates:
`checked`, `unchecked` (no block, parse error, or non-canonical type — those are
`clean --deep` territory), `flagged`, `counts`, and `samples` capped at 20.

## Render

> Render the JSON `cost` block as one line: `cost: ~{est_read_tokens/1000}k tokens, {files} files`.

```
## {slug} — {status} · {freshness.light} {freshness.age}

{purpose}
Last session {whats_done.last_session} · {counts summary} · NEXT: {next_step}
{orientation.repo.branch}, {dirty} dirty{" · " + board.line if board.present}

## Wrong now

{one line per entry, or "nothing" — this band silent means the vault's claims hold}

## Going stale

{one line per entry, or skip the section entirely when empty}

## Worth a look

{one line per entry, or skip the section entirely when empty}

Made current: brief {steps.brief_refresh} · handoff {steps.handoff_mirror}
```

Adapt phrasing to be conversational; the shape above is the data layout, not a
rigid template.

Shape (voice.md §Shape): open with the most decision-relevant fact — the
lifecycle status and freshness beat the title — and close with exactly one next
step, drawn from `wrong_now` if it has anything and from `next_step` otherwise.
Never end on a recap.

Skip an empty band's section entirely rather than printing "none". A `wrong_now`
that is empty is the good case and should read as silence, not as a heading with
nothing under it.

Never render every `naming` entry when there are more than five: give the count
and the first three, and point at the list in the JSON.

## The advisor rails

The advisor mode itself is a standing contract, not code: see
`reference/advisor.md`, which the SessionStart hook loads when the mode is on.
`status.py` owns its two state surfaces so they cannot drift apart:

```bash
python3 status.py --advisor {on|off|status} --project-dir "$REPO_ROOT"
python3 status.py --capture-task --title "..." [--note "..."] --project-dir "$REPO_ROOT"
```

`--advisor on` sets `advisor: on` in `.claude/adjudant` *and* stamps a marker
line into `AGENTS.md`, so the mode is never a hidden setting someone has to
remember exists. `off` removes both. `--capture-task` lands an approved
suggestion as a task note through the same rail the session-end bridge uses,
deduplicated by slug so a re-capture never clobbers an edited note.

## Lifecycle triage

```bash
python3 status.py --triage --project-dir "$REPO_ROOT"
python3 status.py --move SLUG ZONE --project-dir "$REPO_ROOT"
```

`--triage` prints one prompt per project in the vault and moves nothing — a
read-only plan, never an action. Ask about each project one at a time rather
than dumping the whole list and letting it get skimmed. Each confirmed move is
exactly one `--move SLUG ZONE` call, so nothing moves until a person says so
for that project. A project in `active/` with no session for 30 days is the
prompt that makes triage happen at all — the verb it replaces went unused for
a year because nothing ever asked.

## Naming a thing

```bash
python3 status.py --slug Fix the parser rewrite    # -> fix-the-parser-rewrite
```

One slug rule for the whole plugin (`board_bridge.kebab`), so a captured task
and a hand-named note agree about what the same title is called.

## Inputs

None. Operates on the project resolved from the `.claude/adjudant` breadcrumb at
cwd.

## Fail conditions

- No breadcrumb at cwd and the argument is not a vault project dir → exit
  non-zero pointing at `/adjudant connect`
- A breadcrumb whose slug is not safe kebab-case, or whose project would land
  outside the vault → exit non-zero naming the slug. The verb path fails closed;
  nothing is written first
- Vault path unreachable → exit non-zero with the message

## See also

- `scripts/status.py`, `scripts/test_status.py`
- `scripts/_lifecycle.py`, `scripts/test__lifecycle.py` — the guided triage behind `--triage`/`--move`
- `reference/clean.md` — repairs what this reports
- `reference/dream.md` — the deeper diagnostic; use when `drift_signal` looks elevated
- `reference/advisor.md` — the standing contract behind the advisor rails
