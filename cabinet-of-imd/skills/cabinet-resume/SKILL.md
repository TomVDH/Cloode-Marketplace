---
name: cabinet-resume
description: >
  Resume a previous Cabinet of IMD session — pick up where the crew left off
  on a project from an earlier day. Reads the session anchor and vault history
  to restore context without a full cold boot. Use when Tom says "resume",
  "pick up where we left off", "continue the project", "back to work on X",
  or invokes /cabinet on a project the anchor already knows about from a
  previous day.
version: 2.0.0
---

# Cabinet Resume

Resume a previous session instead of cold-booting. The cabinet reads the session anchor and (if available) the vault's session summary to rebuild context from the last time the crew worked on this project. No full roster display, no wake-up chatter — just a quick re-orientation and straight to work.

This skill exists because `/cabinet` treats cross-day returns as cold boots by default. `/cabinet-resume` is the explicit "we were here before, let's keep going" path. The regular `/cabinet` also offers this path when it detects a prior anchor — but `/cabinet-resume` skips the question and goes straight to resuming.

## When This Triggers

- Tom explicitly invokes `/cabinet-resume`
- Tom says something like "pick up where we left off", "resume the project", "continue from last time", "back on {project name}"
- `/cabinet` detects a prior-day anchor for the same project and Tom confirms resume (handled in cabinet's step 1.5 — see below)

## On Activation

### 1. Load Boot References

Same as `/cabinet` step 1:

```
${CLAUDE_PLUGIN_ROOT}/references/specialist-contract.md
${CLAUDE_PLUGIN_ROOT}/references/dynamics.md
${CLAUDE_PLUGIN_ROOT}/references/gate-protocol.md
${CLAUDE_PLUGIN_ROOT}/references/protocols.md
${CLAUDE_PLUGIN_ROOT}/references/code-conventions.md
${CLAUDE_PLUGIN_ROOT}/references/chatter-system.md
${CLAUDE_PLUGIN_ROOT}/references/session-anchor.md
${CLAUDE_PLUGIN_ROOT}/references/terminal-colours.md
```

### 2. Read the Session Anchor

Look for `crew-notes/cabinet-session.json` in the project directory.

```pseudocode
anchor = READ("crew-notes/cabinet-session.json")

IF anchor does not exist OR fails parse:
    OUTPUT "[Kevijntje]: No anchor on file — can't resume what we don't have.
            Want a fresh start? Try /cabinet."
    EXIT

IF anchor.status == "wrapped":
    // Previous session was formally closed. Context is in the vault,
    // but the anchor marks a clean ending — not an interrupted session.
    OUTPUT "[Kevijntje]: Last session was wrapped up properly.
            I can pull context from the vault and start fresh.
            Want me to boot /cabinet with {anchor.project_name}?"
    AWAIT Tom's response
    IF confirmed: RUN /cabinet with project_name pre-set
    EXIT
```

### 3. Check for Vault

Run the same vault detection as `/cabinet` step 1.6 — the full discovery chain from `vault-integration.md`. If the anchor has vault config, use it. If vault is available, load `vault-integration.md`.

### 4. Restore Context from Anchor + Vault

```pseudocode
project_name = anchor.project_name
project_slug = slugify(project_name)

// Restore session state
active_specialist = anchor.active_specialist
active_task = anchor.active_task
scope = anchor.scope
gates = anchor.gates
parking_lot = anchor.parking_lot
dissent = anchor.dissent

// Pull vault context (if available)
IF vault_available:
    // 1. Last session summary — the recap of what happened
    last_session = find_latest_session(project_slug)
    IF last_session:
        summary = vault.read(last_session, max_chars=3200)
        INJECT summary as context: "Last Session Summary (from vault)"

    // 2. Project brief — for orientation
    brief_path = "projects/" + project_slug + "/brief.md"
    IF vault.exists(brief_path):
        brief = vault.read(brief_path, max_chars=3200)
        INJECT brief as context: "Project Brief (from vault)"
        SET anchor.vault.brief_loaded = true

    // 3. Preferences + lessons (same as /cabinet boot)
    prefs_path = "crew/preferences.md"
    IF vault.exists(prefs_path):
        prefs = vault.read(prefs_path, max_chars=2000)
        INJECT prefs as context: "Known Preferences (from vault)"
        SET anchor.vault.preferences_loaded = true

    lessons_path = "crew/lessons-learned.md"
    IF vault.exists(lessons_path):
        lessons = vault.read(lessons_path, max_chars=1200)
        INJECT lessons as context: "Lessons Learned (from vault)"
        SET anchor.vault.lessons_loaded = true

    // 4. Recent decisions for this project (last 3)
    decision_dir = "projects/" + project_slug + "/decisions/"
    recent_decisions = vault.list(decision_dir)  // sorted by date desc
    FOR each of top 3 recent_decisions:
        decision = vault.read(decision_path, max_chars=800)
        INJECT as context: "Recent Decision (from vault)"
```

### 5. Display Resume Header

Abbreviated header — not the full roster. Kevijntje leads.

In terminal:
```bash
echo -e "\033[38;2;240;168;40m╔══════════════════════════════════════════════╗\033[0m"
echo -e "\033[38;2;240;168;40m║\033[0m  \033[1;38;2;212;160;23mCABINET RESUME\033[0m — {project_name}           \033[38;2;240;168;40m║\033[0m"
echo -e "\033[38;2;240;168;40m╚══════════════════════════════════════════════╝\033[0m"
```

In Cowork:
```
**▓▓ CABINET RESUME ▓▓** — {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 6. Kevijntje's Recap

Kevijntje presents a brief recap from the anchor and vault data. This is the "where we left off" moment — it should feel like a captain's briefing, not a data dump.

```pseudocode
OUTPUT "[Kevijntje]: Right, we were on {project_name}.
        Last session: {anchor_date}.
        {active_specialist} was on {active_task}.
        Gates: {gates.completed}/{gates.total} — last passed: {last_gate_name}.
        {parking_lot.length} items in the parking lot."

IF last_session summary was loaded from vault:
    OUTPUT "[Bostrol]: Quick recap from last time: {2-3 sentence summary
            extracted from the session summary note}."

IF recent_decisions loaded:
    OUTPUT "[Bostrol]: Key decisions still in play: {list 1-3 decision titles
            as [[wikilinks]]}."
```

### 7. Resume Chatter (Short)

3-4 messages from the crew — not the full 6-8 wake-up burst. The crew already knows the project; these messages should feel like coming back from a break, not starting fresh.

**What to pull from:**
- The `anchor.active_specialist` — they acknowledge being back on point, referencing what they were working on
- The `anchor.active_task` — someone makes a remark about the task (progress, frustration, anticipation)
- Time gap since last session — if days have passed, someone notices ("Three days. Thought you forgot about us." — Thieuke energy). If same day, it's lighter ("Back already?" — Pitr).
- The anchor's last `energy.temperature` — if it was low, Poekie checks in. If it was high, the crew picks up that energy.

**Running joke pull** — same as cold boot: check 1 random character YAML's `running_jokes`, weave one in if it fits the moment. Don't force it.

**Voice rules:**
- Kevijntje rallies, but briefly — "Allez, verder." not a full speech
- The returning specialist gets a line — acknowledging the work, not narrating it
- 1-2 others react — keep it tight, no filler
- Same banned openers as cold boot (§ cabinet/SKILL.md Step 4) apply here

### 7.5. Chatter Level

After the resume chatter, Kevijntje asks Tom how loud he wants the crew — same as `/cabinet` step 4.5, but shorter in tone since context is already established.

**The vault chatter log is always written at full frequency regardless of this setting.**

```pseudocode
hour = CURRENT_HOUR()
days_gap = today - anchor_date

// Recommend from context
IF hour < 9 OR hour >= 22:
    recommended = "quiet"
ELIF vault_available AND anchor.vault.last_temperature IN ["frustrated", "grinding"]:
    recommended = "quiet"
ELIF days_gap >= 7:
    recommended = "normal"   // been a while — ease back in
ELSE:
    recommended = "normal"
```

Kevijntje offers all three options, briefly — this is a resume, not a fresh boot, so he keeps it tight:

```
// Example — resuming after a few days:
[Kevijntje]: "Good to be back. Noise level — quiet, normal, or full noise?"

// Example — late-night resume:
[Kevijntje]: "Late one. Quiet, normal, or are we going full crew?"

// Example — vault shows last session was frustrated:
[Kevijntje]: "Last one was rough. Quiet might be the call — but you pick.
              Quiet / Normal / Full noise."
```

AWAIT Tom's response and store in anchor exactly as per `/cabinet` step 4.5.

### 8. Update Anchor for New Session

```pseudocode
// Start a new session ID but preserve project state
anchor.session_id = NOW()  // new timestamp
anchor.status = "active"
// Keep: project_name, active_specialist, active_task, scope, gates,
//       parking_lot, dissent, vault config, chatter.level (re-asked at step 7.5)
// Reset: session-specific counters only
anchor.chatter.message_count_approx = 0
anchor.chatter.nudge_used = false
anchor.energy.break_count = 0
anchor.energy.last_break = null
anchor.energy.session_start = NOW()

WRITE anchor
```

### 9. Initialize Crew Notes

Same as `/cabinet` step 6-8:
- Ensure `crew-notes/` exists
- Append a resume divider to the vault chatter: `"\n---\n*Session resumed — {NOW()}*\n"`
- Do NOT overwrite existing chatter — append to it

### 10. Ready State

```pseudocode
OUTPUT "[Kevijntje]: Caught up. {active_specialist}, you're still on point
        unless Tom says otherwise. What's the move, Tom?"
```

The cabinet is now active. All subsequent work follows the standard `/cabinet` flow — gating, dynamics, chatter, vault ops, wrap-up.

## Helper: find_latest_session

```pseudocode
FUNCTION find_latest_session(project_slug):
    session_dir = "projects/" + project_slug + "/sessions/"
    files = vault.list(session_dir)
    // Session files are named YYYY-MM-DD.md — sort desc
    IF files not empty:
        RETURN session_dir + files[0]  // most recent
    RETURN null
```

## Edge Cases

**No vault, but anchor exists:** Resume works — Kevijntje recaps from the anchor alone. No session summary, no decision history. The recap is shorter but functional.

**Anchor from a different project:** Kevijntje flags it: "The anchor is from {anchor.project_name}, not the project you mentioned. Want to resume that one, or fresh start on the new one?"

**Anchor is very old (30+ days):** Kevijntje notes it: "This one's been shelved for a while — {N} days since the last session. Quick skim of the brief before we dive in?"

**Wrapped session:** Handled in step 2 — redirects to `/cabinet` with project name pre-set. The vault has the history; the anchor signals a clean ending.

## What This Skill Does NOT Do

- Does not replace `/cabinet` — it's a shortcut for the resume path
- Does not create new projects — if no anchor exists, it points to `/cabinet`
- Does not replay the full wake-up ceremony
- Does not advance gates or change scope — it restores state, then hands off to standard cabinet flow
