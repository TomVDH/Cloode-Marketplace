# shelf: project lifecycle

One small verb for the six-state lifecycle: `active | stale | fridge | done | dead | seed`.
Physical placement follows status: `projects/` holds active+stale+seed, `projects/_fridge/`
holds fridge, `projects/_archive/` holds done+dead.

## Flow

**`/adjudant shelf`** (no args): run

    python3 {plugin}/scripts/shelf.py list --project-dir {code root}

Render the JSON as one table: slug, zone, declared, suggested, days quiet, last session.
Flag rows where `zone_matches` is false or `declared_valid` is false. Suggestions come
only from the active/stale axis; fridge rows can carry a `nudge` string. Never write
anything from list mode.

**`/adjudant shelf <slug> <state> [reason]`**: two-phase, always with explicit user
confirmation between phases.

1. `python3 {plugin}/scripts/shelf.py preview --project-dir {code root} --slug S --to STATE [--reason "..."]`
2. Show the plan: from/to state, folder move yes/no, how many files get wikilink
   rewrites. Ask the user to confirm.
3. On confirmation: `python3 {plugin}/scripts/shelf.py apply ...` (same args).
4. Render the apply summary: final dir, links rewritten, index row action, backup path.

## Rules

- Machines suggest only along the active/stale axis. `fridge`, `done`, `dead`, `seed`
  are set by the user, through this verb, never automatically.
- Apply refuses to run without a matching preview, and aborts untouched if the target
  zone dir already exists.
- Every modified file is backed up under `{vault}/.adjudant-shelf-backup/{timestamp}/`
  with a manifest.json (plan + file list) for manual rollback.
- Transitions land in the brief: `status:` + `updated:` frontmatter, and a dated line
  under `## Status log` (newest first).
- Files that are not valid UTF-8 are **never rewritten**: reading them leniently and
  writing the result back would bake a permanent `U+FFFD` over each undecodable byte.
  They are skipped, left byte-identical, and reported in `skipped_undecodable` (also on
  stderr). Their wikilinks still point at the OLD path, so render that list as its own
  line and say the links need a manual fix.
- Working on a fridged or archived project? Session hooks now write to whichever zone
  the project actually lives in, so notes land correctly without shelving back first.
