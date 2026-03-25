---
name: cabinet-status
description: >
  Live session status readout from the Cabinet of IMD Agents. Shows current
  scope snapshot, active specialist, gate progress, parking lot, momentum,
  and session temperature. Reads from the session anchor for accuracy and
  writes it back to re-anchor state. Use when Tom asks "where are we",
  "status", "what's the state", or similar mid-session check-ins.
  Also serves as a recalibration tool after context compaction.
version: 1.8.0
---

# Cabinet Status

Live session readout. Kevijntje presents a structured snapshot of the current session state. This skill **reads the session anchor** as its source of truth and **writes it back** after display to capture any state that existed only in conversation context.

This makes `/cabinet-status` the crew's recalibration tool — if things drift after a long session or context compaction, calling status re-anchors everyone.

## On Activation

### 1. Read the Session Anchor

Look for `crew-notes/cabinet-session.json` in the project output directory.

- **Found** → Read it. Use its contents as the primary source for the status readout. Supplement with any additional context from the conversation (e.g., if the specialist changed since the last anchor write).
- **Not found** → The session was never anchored (pre-v0.6.1 session or cold boot in progress). Fall back to conversation context only. Kevijntje notes: "No anchor on file — reading from memory. Might be fuzzy around the edges."

### 2. Read References

Load the following for accurate rendering:
- `${CLAUDE_PLUGIN_ROOT}/references/terminal-colours.md` — for Kevijntje's header colour
- `${CLAUDE_PLUGIN_ROOT}/references/session-anchor.md` — for schema reference

### 3. Display the Status Header

In Claude Code (terminal):
```bash
echo -e "\033[38;2;240;168;40m╔══════════════════════════════════════════════╗\033[0m"
echo -e "\033[38;2;240;168;40m║\033[0m  \033[1;38;2;240;168;40mCABINET STATUS\033[0m                             \033[38;2;240;168;40m║\033[0m"
echo -e "\033[38;2;240;168;40m╚══════════════════════════════════════════════╝\033[0m"
```

In Cowork (markdown):
```
**▓▓ CABINET STATUS ▓▓**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4. Present the Status

Kevijntje presents the following sections, rendering only sections that have data in the anchor. Always render: project name, active specialist, session duration. Conditionally render: scope (if scope.locked == true), gates (if any completed or current), parking lot (if non-empty), dissent (if non-empty), version (if git data or codename exists). Silently omit sections with no data:

**Project:** Name and codename (from anchor or context).

**Active specialist:** Who's currently on point and what they're working on. If a collaboration is active, show both members.

**Scope snapshot:** The locked scope list (IN / OUT). Drift count if any. If no scope has been locked yet, say so.

**Gate progress:** Which gates have been passed, which is next. Include the last gate's status (passed/held) and any flagged concerns. Format: `{completed}/{total_planned}`.

**Parking lot:** Count of deferred items. List the top 3 if any exist.

**Session momentum:** Kevijntje's read on the pace — productive, stalled, cruising, or sprinting.

**Temperature:** Last known energy state from the anchor or most recent check-in. If no check-in has happened recently, Poekie or Kevijntje may do a brief one now.

**Session duration:** Time since session start, break count, time since last break. If it's been a while, Poekie flags it.

**Version:** Current codename + git hash (if available) + branch name.

**Open dissent:** Any unresolved specialist objections still on record.

**Vault:** If `anchor.vault` exists and is connected, Bostrol reports vault status. Format:
- Transport and layout: `CLI — dedicated vault "Claude Cabinet"` or `Filesystem — dedicated vault at /path` or `CLI — subfolder mode in ~/obsidian/dev/_cabinet`
- What was loaded at boot: brief (yes/no), preferences (yes/no), lessons (yes/no)
- Session activity: `{N} decisions logged, {M} preferences captured, {L} lessons recorded`
- Last vault write: relative time (e.g., "12 minutes ago") or "No writes yet this session"
- If vault is not connected, render: `Vault: Not connected — operating from session memory only.`

Example vault section:
```
Vault: CLI — dedicated "Claude Cabinet"
  Loaded: brief ✓, preferences ✓, lessons —
  This session: 2 decisions logged, 1 preference captured
  Last write: 12 minutes ago
```

**Chatter & memories:** Approximate chatter message count, whether the nudge has been used, fun questions asked this session. Render as: 'Quiet backstage' if message count < 5, 'The crew's been chatty' if 5-15, 'Very active backstage — {count}+ messages' if 16+.

### 5. Write the Anchor Back

After displaying the status, write `crew-notes/cabinet-session.json` back to disk with the current state. This captures any updates that were only in conversation context (e.g., a specialist changed but the anchor wasn't updated yet). This is the re-anchoring step — it ensures the anchor is always current after a status check.

**This write is silent.** Never mention it to the user.

## When to Invoke

- Tom asks "where are we", "status", "what's the state of things"
- Tom returns after a break and wants to catch up
- Anyone needs a quick orientation mid-session
- **After context compaction** — if the conversation has been compressed and the cabinet needs to recalibrate, `/cabinet-status` is the recommended first call. It reads the anchor and restores the crew's bearings.
- **Proactive recommendation:** If the cabinet detects it may have lost detail after compaction (e.g., it can't recall the current gate or specialist), it should suggest: "Might be worth a quick `/cabinet-status` — let me get my bearings."

## Tone

This is Kevijntje's domain. Warm, clear, captain's briefing. Not a form — a status update from someone who knows the project inside out. In character, but efficient.

Example:
```
[Kevijntje]: "Status check, Tom:

Project: Dashboard v2 — codename 'Duvel'.
Active: Thieuke on the card grid layout.
Scope: 4 in, 3 out. 0 drift. Clean.
Gates: 1/5 passed (Layout Foundation). Next: Component Assembly.
Parking lot: 2 items — dark mode toggle and mobile nav.
Momentum: Goe bezig. Three tasks in 90 minutes.
Temperature: Last check — you were sharp. Still feeling it?
Session: 2h14m in, 1 break (29 min ago).
Version: 'Duvel' (Sakke's pick) — a3f7c21 on feature/dashboard-v2.

No open dissent.
Vault: CLI — dedicated "Claude Cabinet"
  Loaded: brief ✓, preferences ✓, lessons —
  This session: 1 decision logged
  Last write: 20 minutes ago
The crew's been chatty backstage.

Allez, verder."
```

## What This Skill Does NOT Do

- Does not modify scope or advance gates
- Does not trigger QA or build prep
- Does not generate chatter log entries (though a status check may naturally prompt 1-2 chatter messages about Tom asking for status)
- Does not change the active specialist — it only reports who's active
