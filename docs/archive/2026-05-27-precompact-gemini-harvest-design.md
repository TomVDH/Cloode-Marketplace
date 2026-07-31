---
date: 2026-05-27
status: design — ready for implementation
scope: adjudant plugin — extend PreCompact hook with Gemini-driven harvest into _handoff.md
plugin: adjudant
version-target: 0.5.0
related: 2026-05-26-adjudant-port-verb-design.md, 2026-05-26-adjudant-verb-implementation-gaps.md
---

# Gemini harvest at PreCompact: extract decisions before context dies

## Problem statement

Right before Claude Code compacts its context, the running session holds the freshest, densest, most expensively-built understanding of the current work. Compaction destroys most of it — Claude keeps a summarized version, but anything not surfaced in the summary is lost.

Today, adjudant's `PreCompact` hook does two things (`adjudant/hooks/scripts/precompact.py`):
1. Appends `- HH:MM · paused (compaction)` to today's session log
2. Calls `sync_handoff()` which mirrors `.remember/now.md` (or `.remember/remember.md`) to `_handoff.md` in the vault

Both are useful. Neither asks a **second model** what's worth keeping.

A pre-compaction Gemini-driven harvest can surface 3–5 durable bullets (decisions made, blockers, unresolved questions) that the user can later read from `_handoff.md` even when Claude has compacted past them.

## Goals

1. **Zero-risk addition.** Existing PreCompact behavior preserved verbatim. Gemini step is purely additive and fails closed (any failure → no harvest, existing sync still runs).
2. **Cheap.** `gemini-2.5-flash` model, ~30-message context window, 5-bullet output, runs once per compaction.
3. **Useful.** Bullets must be concrete decisions/blockers, not chat summary. Discipline enforced by the prompt template (per gemineye's pattern).
4. **No MCP dependency in the hook.** Hook calls `gemini` CLI directly via subprocess — avoids requiring the MCP server to be running at compaction time.
5. **Transcript-aware.** Read the transcript file from the JSON payload that CC sends on stdin (currently unread).

## Non-goals

- Replacing the existing `.remember/` mirror — that's still the canonical handoff body.
- Calling Gemini at SessionEnd (different transition; out of scope).
- Asking Gemini to *write* anything to the project. It only outputs bullets that the hook appends to `_handoff.md`.
- Streaming, multi-turn, or interactive Gemini behavior. Single round-trip, capped timeout.

## How CC's PreCompact hook contract works

CC sends a JSON payload to the hook script via **stdin**. The payload contains (at minimum):

```json
{
  "session_id": "string",
  "transcript_path": "/Users/.../.claude/projects/<encoded>/<session-uuid>.jsonl",
  "cwd": "string",
  "hook_event_name": "PreCompact",
  "trigger": "manual" | "auto",
  "custom_instructions": "string (manual trigger only)"
}
```

The current script reads only `CLAUDE_PROJECT_DIR` from env and ignores stdin. The new script reads stdin first, falls back to env if stdin is empty or non-JSON.

## Design

### Flow

```
[CC fires PreCompact]
        │
        ▼
[precompact.py reads stdin JSON]
        │
        ├─→ Existing: append pause marker to session log
        │
        ├─→ NEW: harvest_with_gemini(transcript_path) → bullets (5 max) | ""
        │           │
        │           ├─ Reads last N messages from transcript
        │           ├─ Builds rigid template prompt
        │           ├─ subprocess gemini --sandbox -m gemini-2.5-flash -p <prompt>
        │           ├─ Timeout 30s
        │           └─ Returns bullets on success, "" on any failure
        │
        └─→ sync_handoff(): write _handoff.md
                ├─ Existing: frontmatter + mirrored .remember/now.md body
                └─ NEW: if bullets non-empty, prepend "## Gemini harvest" section
```

### Prompt template (locked)

```
ROLE
You are a session-end archivist for a Claude Code working session about to be compacted.

DO
- Extract concrete decisions, problems solved, blockers, and unresolved questions
- One bullet per item, max 25 words
- Reference specific files/commits/issues by name when possible

DON'T
- Summarise the chat
- Include code blocks
- Use softening language ("we discussed", "considered")
- Output anything except the bullets

SCOPE — IN
- The most recent {N} messages of the transcript (provided below)

SCOPE — OUT
- Greetings, tool-call mechanics, status pings, hook output
- Anything older than what's included

OUTPUT
- Exactly 5 bullets, no preamble, no trailing text. If fewer than 5 concrete items exist, output fewer.
- Format: `- <bullet text>`

CONTEXT
{transcript_chunk}
```

### Transcript chunking strategy

- Read last 60 lines from the `.jsonl` (≈ 30 user/assistant message pairs)
- Strip tool-call internals (`tool_use` and `tool_result` content) to text only
- Truncate to ~10,000 chars before sending (keeps flash call cheap)
- If transcript file is unreadable or empty → return "" immediately

### Output format in `_handoff.md`

Current shape (preserved):

```markdown
---
type: handoff
project: "[[projects/<slug>/brief|<slug>]]"
updated: <date>
source: now
tags:
  - handoff
---

# Handoff — <slug>

*Mirrored from `.remember/now.md` on <date> <time>.*

---

<mirrored body>
```

New shape (Gemini harvest section inserted between mirror header and mirrored body, only when harvest succeeded):

```markdown
---
type: handoff
project: "[[projects/<slug>/brief|<slug>]]"
updated: <date>
source: now
tags:
  - handoff
---

# Handoff — <slug>

*Mirrored from `.remember/now.md` on <date> <time>.*

## Gemini harvest — <date> <time> (model: gemini-2.5-flash)

- bullet 1
- bullet 2
- bullet 3
- bullet 4
- bullet 5

---

<mirrored body>
```

When harvest fails or returns empty, the `## Gemini harvest` section is omitted entirely (no empty heading, no error noise).

### Code shape

New function in `adjudant/hooks/scripts/precompact.py`:

```python
import json
import re
import subprocess
from pathlib import Path
from typing import Optional


HARVEST_PROMPT_TEMPLATE = """ROLE
You are a session-end archivist for a Claude Code working session about to be compacted.

DO
- Extract concrete decisions, problems solved, blockers, and unresolved questions
- One bullet per item, max 25 words
- Reference specific files/commits/issues by name when possible

DON'T
- Summarise the chat
- Include code blocks
- Use softening language ("we discussed", "considered")
- Output anything except the bullets

SCOPE — IN
- The most recent {n_msgs} messages of the transcript (provided below)

SCOPE — OUT
- Greetings, tool-call mechanics, status pings, hook output
- Anything older than what's included

OUTPUT
- Exactly 5 bullets, no preamble, no trailing text. If fewer than 5 concrete items exist, output fewer.
- Format: `- <bullet text>`

CONTEXT
{transcript_chunk}
"""

HARVEST_MAX_CHARS = 10_000
HARVEST_TIMEOUT_SECS = 30
HARVEST_N_MSGS = 30


def read_payload() -> dict:
    """Read the JSON payload CC sends on stdin. Returns {} on any failure."""
    try:
        if sys.stdin.isatty():
            return {}
        data = sys.stdin.read()
        if not data.strip():
            return {}
        return json.loads(data)
    except (json.JSONDecodeError, OSError):
        return {}


def extract_transcript_text(transcript_path: Path, n_msgs: int = HARVEST_N_MSGS) -> str:
    """Read last n_msgs * 2 lines from the .jsonl transcript, strip tool internals.
    Returns plain text suitable for a Gemini prompt, capped at HARVEST_MAX_CHARS."""
    if not transcript_path.is_file():
        return ""
    try:
        lines = transcript_path.read_text().splitlines()[-(n_msgs * 2):]
    except OSError:
        return ""
    out = []
    for line in lines:
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        role = msg.get("role") or msg.get("type", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
            )
        if not isinstance(content, str):
            continue
        content = re.sub(r"\s+", " ", content).strip()
        if not content:
            continue
        out.append(f"[{role}] {content[:1000]}")
    text = "\n".join(out)
    return text[-HARVEST_MAX_CHARS:]


def harvest_with_gemini(transcript_path: Path) -> str:
    """Return bullet block on success, '' on any failure. Always fails closed."""
    chunk = extract_transcript_text(transcript_path)
    if not chunk:
        return ""
    prompt = HARVEST_PROMPT_TEMPLATE.format(n_msgs=HARVEST_N_MSGS, transcript_chunk=chunk)
    try:
        result = subprocess.run(
            ["gemini", "--sandbox", "-m", "gemini-2.5-flash", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=HARVEST_TIMEOUT_SECS,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
    if result.returncode != 0:
        return ""
    output = result.stdout.strip()
    # Sanity: only return if it looks like a bullet list
    if not output.startswith("- ") and not output.startswith("• "):
        return ""
    return output
```

`sync_handoff` is extended to accept an optional `harvest: str = ""` parameter and inject the `## Gemini harvest` section before the `---` separator that introduces the mirrored body.

`main()` calls `harvest_with_gemini(transcript_path)` between the pause-marker step and `sync_handoff()`, then passes the result to `sync_handoff(..., harvest=harvest)`.

## Tests

Add to `adjudant/scripts/test_sync.py` (or new `test_precompact.py`):

| Test | Asserts |
|---|---|
| `test_harvest_returns_empty_on_missing_transcript` | `harvest_with_gemini(Path("/nonexistent"))` returns `""` |
| `test_harvest_returns_empty_on_unparseable_transcript` | Transcript file with non-JSONL content → returns `""` |
| `test_harvest_returns_empty_on_gemini_timeout` | Mock subprocess.run to raise TimeoutExpired → returns `""` |
| `test_harvest_returns_empty_on_non_zero_exit` | Mock subprocess.run returncode=1 → returns `""` |
| `test_harvest_returns_empty_on_non_bullet_output` | Mock gemini stdout = "I'm sorry, I can't help with that." → returns `""` |
| `test_harvest_returns_bullets_on_success` | Mock gemini stdout = "- decision 1\n- decision 2" → returns that exact string |
| `test_sync_handoff_includes_harvest_when_provided` | Pass non-empty harvest → `_handoff.md` contains "## Gemini harvest" section |
| `test_sync_handoff_omits_harvest_when_empty` | Pass empty harvest → `_handoff.md` has no "## Gemini harvest" section |
| `test_extract_transcript_text_strips_tool_calls` | Transcript with `tool_use` content blocks → output contains only text content |
| `test_extract_transcript_text_truncates_to_max_chars` | Long transcript → output ≤ HARVEST_MAX_CHARS |

All tests can mock subprocess.run with `unittest.mock.patch`.

## Failure modes (all fail-closed)

| Failure | Behavior |
|---|---|
| stdin not present or not JSON | `read_payload()` returns `{}`, no transcript_path, harvest skipped |
| `transcript_path` missing or unreadable | `extract_transcript_text()` returns `""`, harvest skipped |
| `gemini` CLI not on PATH | `subprocess.run` raises `FileNotFoundError`, caught → harvest skipped |
| Gemini timeout (30s) | `TimeoutExpired` caught → harvest skipped |
| Gemini non-zero exit | returncode check → harvest skipped |
| Gemini output doesn't look like bullets | Sanity check → harvest skipped |
| Any failure mid-flow | Existing `sync_handoff()` still runs unchanged |

Net result: the hook is **never worse than the current behavior**. Best case it adds 5 high-signal bullets; worst case it adds nothing and the existing handoff mirror happens.

## Versioning + validators

- adjudant `0.4.1` → `0.5.0` (new behavior, minor bump)
- marketplace entry + plugin.json + command-metadata.json + SKILL.md version field — all four bumped together per `version-consistency` validator
- No new validator needed — failure-closed design means there's no invariant to enforce

## Open questions / deferred

- **Manual vs auto trigger.** PreCompact fires both ways. Currently we don't distinguish. Could be useful to skip harvest on manual `/compact` (user is in control, no need to second-opinion) and only run on auto. Defer until we see how the data looks.
- **Cost ceiling.** No per-day cap on Gemini calls. If you set up cron-style auto-compaction and burn through quota, this hook adds to that. Could log a metric to `~/.claude/data/gemini-harvest-calls.jsonl` and read a daily-limit env var. Defer.
- **Pro vs flash.** Flash is plenty for 5-bullet summarization. Don't switch to pro without strong reason — pro at PreCompact rate would burn budget.
- **Bullet quality scoring.** Could later compare the harvested bullets to the actual session log and grade the harvest. Out of scope for v0.5.0.

## Implementation phasing

Single PR:

1. Extend `precompact.py` with `read_payload`, `extract_transcript_text`, `harvest_with_gemini`
2. Extend `sync_handoff` to accept `harvest` parameter and inject the section
3. Wire `main()` to call harvest between pause-marker and sync
4. Add 10 tests (see above)
5. Bump version in all 4 files
6. Commit, push

Estimated effort: 2-3 hours single-pass for an implementer, then live-fire on this repo to verify the harvest renders in `_handoff.md` after a real compaction.

## Out of scope (explicit)

- Touching SessionEnd hook (it calls `precompact.py --sync-only`; harvest would NOT run because no transcript is in flight at session end the same way)
- Changing `.remember/` schema or how the `now.md` mirror works
- Adding any non-Gemini AI provider
- Surfacing the harvest in CC's UI / statusline (could be a follow-up; for now it's just in the vault file)
- Changing any other adjudant verb (sync, port, tidy, ramasse) to use Gemini

## Pointers

- Current hook: `adjudant/hooks/scripts/precompact.py`
- Hook registration: `adjudant/hooks/hooks.json` (PreCompact entry)
- Tests pattern: `adjudant/scripts/test_sync.py`, `adjudant/scripts/test_port.py`
- Gemini CLI invocation reference: `gemineye/references/invocation-patterns.md`
- The user's vault: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Claude Cabinet/`
- Test fixture available: this project (`onnozelaer-claude-plugins`) is adjudant-connected as of today; manually triggering `/compact` here will exercise the new code path against a real transcript
