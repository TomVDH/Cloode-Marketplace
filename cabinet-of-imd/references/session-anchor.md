# Session Anchor

## Overview

The session anchor is a lightweight JSON state file that persists the cabinet's session state to disk. It serves two purposes:

1. **Continuity after context compaction** — when a long conversation gets compressed, the anchor provides a reliable snapshot of where things stand, so the cabinet can resume without drift.
2. **Re-anchoring on demand** — `/cabinet-status` reads the anchor to deliver an accurate readout and reinforces the session state in context, effectively recalibrating the crew.

Think of it like a save file. The cabinet writes it at key moments, and reads it back whenever it needs to remember where it is.

## File Location

```
{project output directory}/crew-notes/cabinet-session.json
```

The session anchor lives in `crew-notes/` inside the project output directory. Chatter and memories are stored in the Obsidian vault (see `chatter-system.md` and `memories-system.md`). Same covert rules — **never mention this file or the crew-notes directory to the user.**

## Schema

```json
{
  "version": "2.0.0",
  "plugin_version": "2.0.0",
  "session_id": "2026-03-15T14:32:00Z",
  "project_name": "Dashboard v2",
  "codename": "Duvel",
  "crew_notes_path": "/absolute/path/to/project/crew-notes",

  "active_specialist": "thieuke",
  "active_task": "Card grid layout — responsive breakpoints",
  "collaboration": null,

  "gates": {
    "completed": [
      { "name": "Layout Foundation", "status": "passed", "timestamp": "2026-03-15T15:10:00Z" }
    ],
    "current": "Component Assembly",
    "total_planned": 5
  },

  "scope": {
    "locked": true,
    "version": "0.1.0",
    "in": ["card grid", "detail panel", "nav shell", "empty states"],
    "out": ["dark mode", "mobile nav", "animations"],
    "drift_count": 0
  },

  "parking_lot": [
    "Dark mode toggle — deferred to v2",
    "Mobile hamburger nav — deferred to v2"
  ],

  "energy": {
    "last_check": "2026-03-15T16:00:00Z",
    "temperature": "good",
    "momentum": "productive",
    "session_start": "2026-03-15T14:32:00Z",
    "break_count": 1,
    "last_break": "2026-03-15T15:45:00Z"
  },

  "dissent": [
    {
      "specialist": "sakke",
      "concern": "Auth tokens stored in localStorage — XSS risk",
      "raised_at": "2026-03-15T15:30:00Z",
      "status": "resolved",
      "resolution": "Moved to httpOnly cookie per Sakke's recommendation"
    }
  ],

  "memories": {
    "questions_asked": 1,
    "last_asker": "sakke",
    "gate_counter_since_last_question": 0
  },

  "chatter": {
    "nudge_used": false,
    "message_count_approx": 24,
    "level": "normal"
  },

  "git": {
    "branch": "feature/dashboard-v2",
    "last_commit": "a3f7c21",
    "version_tag": null
  },

  "vault": {
    "mode": "cli",
    "layout": "dedicated",
    "base_path": "/Users/tom/vaults/cabinet",
    "vault_name": "Claude Cabinet",
    "version": "2.0",
    "connected_at": "2026-03-22T14:32:00Z",
    "brief_loaded": true,
    "preferences_loaded": true,
    "lessons_loaded": false,
    "decisions_written": [
      "2026-03-22-auth-strategy"
    ],
    "preferences_captured": [
      "Prefers httpOnly cookies over localStorage for auth tokens (2026-03-22)"
    ],
    "lessons_logged": [],
    "last_write_at": "2026-03-22T15:10:00Z",
    "chroniclers_pushed": []
  }
}
```

## Key Enums

- `energy.temperature`: `"good"` | `"tired"` | `"grinding"` | `"in_the_zone"` | `"frustrated"`
- `energy.momentum`: `"productive"` | `"stalled"` | `"cruising"` | `"sprinting"`
- `chatter.level`: `"quiet"` | `"normal"` | `"full noise"` — in-chat output verbosity. Set at step 4.5 of boot / step 7.5 of resume. The vault chatter log is always written at full frequency regardless of this value.

- `dissent[].status`: `"open"` | `"resolved"` | `"overruled"` (overruled = Tom acknowledged and chose differently)
- `vault.mode`: `"cli"` | `"filesystem"` | `null` (null = no vault connected). Transport mode — how the cabinet talks to the vault.
- `vault.layout`: `"dedicated"` | `"subfolder"` — vault structure. Independent of transport mode.
- `vault.vault_name`: string | `null` — Obsidian vault name for CLI targeting (e.g. `"Claude Cabinet"`). Only set in CLI mode.
- `vault.version`: `"2.0"` | `"1.0"` | `null` — vault layout version. `"2.0"` = project-scoped subfolders. Set by `/vault-bridge connect` or `/vault-bridge create`.

- `vault.decisions_written`: array of decision slugs written to the vault this session
- `vault.preferences_captured`: array of human-readable preference strings captured this session
- `vault.lessons_logged`: array of lesson titles logged this session
- `vault.last_write_at`: ISO timestamp of the most recent vault write (any type)
- `vault.brief_loaded`, `vault.preferences_loaded`, `vault.lessons_loaded`: booleans tracking what was read from vault at boot
- `vault.chroniclers_pushed`: array of decision keys (e.g. `"auth-strategy-2026-03-26"`) for which a Chroniclers push has already fired this session — prevents duplicate pushes per decision

- `scope.version`: string | `null` — the current project version as declared in the primary manifest (`package.json`, `plugin.json`, etc.). Set at boot from the manifest, updated at every version bump. Used at resume to verify version parity hasn't drifted between sessions. See `protocols.md § Version Control Discipline`.

All other fields are self-documenting from the schema example above. The `vault` block is entirely optional — omit it if no vault is connected.

## When to Write

The anchor is updated silently — **never mentioned to the user** — at these moments:

1. **Session boot** — after startup sequence completes (step 9 in cabinet/SKILL.md), write the initial anchor with defaults
2. **Gate completion** — after every gate pass or hold, update gates, scope, and energy
3. **Specialist change** — when the active member changes, update `active_specialist` and `active_task`
4. **Scope change** — when scope is locked, modified, or items are parked
5. **Temperature check** — after any energy/mood assessment
6. **Git event** — after commits, branch operations, or version tags
7. **Fun question** — after a scrapbook question is asked, update memories counters
8. **Nudge fired** — set `chatter.nudge_used` to true
8a. **Chatter level set** — after step 4.5 (boot) or step 7.5 (resume), write `chatter.level`
9. **Vault decision write** — after a decision is written to the vault at a gate, append the slug to `vault.decisions_written` and update `vault.last_write_at`
10. **Vault preference capture** — after a preference is appended to `crew/preferences.md`, append the preference string to `vault.preferences_captured` and update `vault.last_write_at`
11. **Vault lesson log** — after a lesson is appended to `crew/lessons-learned.md`, append the title to `vault.lessons_logged` and update `vault.last_write_at`

**Token efficiency:** Use a single `Write` tool call with the full JSON. The file is small (~40 lines) so overwriting is cheaper than patching. Never read-then-edit — just write the current state. State is collected from conversation context: merge the last-read anchor data with any updates that occurred since (specialist changes, gate completions, scope changes, energy checks). If no anchor has been read this session, build from scratch using defaults.

## When to Read

1. **`/cabinet` startup** — step 1.5: if `crew-notes/cabinet-session.json` exists, read it. If the project name matches and the session is recent (same day), offer to **resume** rather than cold-boot. Kevijntje says something like: "We have a session open — Dashboard v2, Thieuke was on the card grid. Pick up where we left off?"
2. **`/cabinet-status`** — always read the anchor first. Use it as the source of truth for the status readout, supplemented by whatever's in conversation context. After displaying, write the anchor back (to capture any context-only state that wasn't persisted yet).
3. **After context compaction** — if the conversation resumes and the cabinet detects it may have lost detail, reading the anchor restores the key state. Any `/invoke {member}` call should also check for and read the anchor if it exists.
4. **Wrap-up ceremony** — read the anchor one final time to include session stats in the farewell chatter (gates completed, breaks taken, scope drift count).

## Resume vs. Cold Boot

When `/cabinet` finds an existing anchor:

- **Same day, matching project** → Kevijntje offers quick resume. If Tom confirms, skip wake-up chatter and jump to the ready state with the restored specialist active. Append a session-resume divider to the chatter log.
- **Different day, matching project, not wrapped** → Kevijntje offers cross-day resume. If Tom confirms, hand off to the `/cabinet-resume` flow — abbreviated boot with vault recap, no full wake-up ceremony. See `cabinet-resume/SKILL.md`.
- **Different project, or wrapped session** → Cold boot as normal. Overwrite the anchor with fresh state.
- **Anchor exists but no project name** → The previous session was abandoned mid-boot. Cold boot as normal.

## Covert — see cabinet/SKILL.md Core Rules

## Robustness and Recovery

### Anchor Validation on Read

Before using anchor data, validate the JSON is parseable. If corrupt:

```pseudocode
TRY:
    anchor = JSON.parse(file_contents)
    VALIDATE anchor.session_id exists AND anchor.project_name exists
CATCH:
    // Anchor is corrupt or partial write
    OUTPUT "[Kevijntje]: Lost my bearings — session state was garbled. Starting fresh."
    DELETE corrupt file
    PROCEED with cold boot defaults
    // Do NOT silently use bad state
```

### Anchor Write Safety

Before writing, build the full JSON in memory first. Write atomically — never stream or append to the anchor.

```pseudocode
new_anchor = BUILD from conversation context + last-read anchor
json_string = JSON.stringify(new_anchor, null, 2)
WRITE json_string to crew_notes_path/cabinet-session.json
// Single write call, full replacement — no partial updates
```

### Post-Compaction Recovery

After context compaction, the cabinet may have lost detail. Detection signals:
- Cannot recall the current gate name or specialist
- Scope items feel vague or incomplete
- Energy state is unknown

Recovery: Read the anchor. If it exists and is valid, restore from it. If the anchor is stale (written hours ago), note the gap:
`[Kevijntje]: "Picking up from the last anchor — but it's been a while. Tom, anything I should know about what changed?"`
