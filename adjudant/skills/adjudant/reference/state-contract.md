# State contract

Files and lines outside adjudant that read adjudant's output. Anything listed
here is a published interface: moving or reformatting it silently breaks a
consumer that has no test in this repo.

## Consumer: the statusline

`~/.claude/statusline-v2.sh`, a symlink into
`~/Library/Mobile Documents/com~apple~CloudDocs/Projects/IDE/claude/`. It lives
in iCloud and syncs to both machines, so it is edited once and lands on both.

Paths below are relative to the vault project directory unless they say
otherwise. `{project}` is that directory, `{repo}` is the code root, `{slug}`
is its basename, and the zone (`_fridge`, `_archive`) is resolved by probing,
not read from the breadcrumb.

| It reads | For |
|---|---|
| `{repo}/.claude/adjudant`, `vault_path:` and `slug:` | vault location, project name |
| `{repo}/.claude/adjudant`, `stale_after_days:` | the threshold for both the lifecycle hint and the dream age (30 when absent or non-numeric) |
| `{vault}/projects/[_fridge/ or _archive/]{slug}/brief.md` | which zone holds the project |
| `$TMPDIR/adjudant/{slug}/tidy-preview`, directory exists | "tidying" state |
| `$TMPDIR/adjudant/{repo basename}/repo-tidy-preview`, directory exists | "repo-tidying" state |
| `{vault}/.adjudant-shelf-preview`, directory exists | "shelving" |
| `{project}/.adjudant-remise-preview`, directory exists | "remising" (reserved, nothing writes it yet) |
| `brief.md` frontmatter, `status:` | lifecycle drift, read against the newest session date |
| newest `sessions/{YYYY-MM-DD}.md`, the filename only | how long the project has been quiet |
| `_handoff.md`, the first line matching `(🔴\|🟡\|🟢).*handoff age` | freshness tier and the age string, plus `🔴 **STALE**` anywhere in the file |
| `_handoff.md` frontmatter, `updated:` | the freshness fallback for a handoff with no banner |
| `board/board-data.json`, `"column":` on each card | open count, in-flight count, week-over-week direction |
| `board/board.html`, file exists | the board label becomes an OSC 8 link |
| `tasks/*.md` mtimes against the deck's | board lag |
| newest `dreams/{YYYY-MM-DD}.md` or `dreams/{YYYY-MM-DD}-dream.md`, the filename only | dream age |
| `$TMPDIR/adjudant-task-ledger-{session_id}.jsonl`, `.id` and `.status` per line | in-flight task count |

## Rules

1. The handoff traffic-light line keeps its exact format. It is the one surface
   where an emoji carries meaning rather than decoration, and the statusline
   reads those emoji without ever printing one.
2. The dream report keeps its dated filename, in either spelling. The finding
   count is optional: the statusline greps `N drift item` anywhere in the file
   and appends it only on a match, so a report without the phrase still ages
   correctly.
3. The task ledger keeps its `$TMPDIR` path and JSONL shape. Only its replay
   into vault task notes was removed.
4. Scratch is `$TMPDIR/adjudant/{key}/{kind}`, where `{key}` is the basename of
   the directory being operated on with every character outside
   `[A-Za-z0-9_.-]` collapsed to a hyphen, ends trimmed, empty becoming
   `project`. Adding a kind is safe; renaming one is not.
5. Anything added to this table needs the statusline updated in the same
   change. Nothing in this repo can catch that break.
