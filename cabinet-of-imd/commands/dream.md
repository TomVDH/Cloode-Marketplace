---
description: Deep analytical crawl of vault data — surfaces contradictions, stale info, dangling scopes, unacted decisions, documentation gaps.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

The Chroniclers (Bostrol, Kevijntje, Jonasty) slept on the project and have thoughts. `/dream` performs a deep analysis of the vault data for the current project, surfacing issues that accumulate silently across sessions.

**This is not a status report.** It's a diagnostic — the kind of thing that happens when three people who care about documentation spend a quiet evening reviewing everything.

---

## When to Suggest

The cabinet should suggest `/dream` to Tom (never auto-run) when:

```pseudocode
session_count = COUNT vault files in projects/{slug}/sessions/
last_session_date = MAX date from session frontmatter
days_since_last = TODAY - last_session_date
scope_drift_count = anchor.scope.drift_count (if mid-session)

IF session_count >= 5:
    SUGGEST — "We've been at this a while. Might be time for a /dream."
ELIF days_since_last >= 14:
    SUGGEST — "It's been {days} days. A /dream might shake out some dust."
ELIF scope_drift_count >= 3:
    SUGGEST — "Scope's been moving. /dream before we go further?"
```

**Kevijntje suggests.** Phrased as a recommendation, not a command. Tom approves or declines.

Example:
```
[Kevijntje]: "Tom — 6 sessions deep on this one, and scope moved twice last time.
              The Chroniclers could do a /dream pass. Worth 10 minutes?"
```

---

## Presentation Flavor

The Chroniclers present their findings as though they slept on the project and woke up with clarity. Not robotic analysis — meditative review. They thought about things. They noticed patterns. They have opinions.

```
[Bostrol]: "Alright. We slept on {project_name}. Here's what surfaced."
[Kevijntje]: "Some of this might sting. That's the point."
[Jonasty]: "I checked every schema reference. Some of them point at ghosts."
```

---

## Analysis Scope

All analysis is scoped to the **current project** only. Cross-project dreams are not supported (yet).

### 1. Contradicting Information

Scan all vault files for the project — brief, decisions, sessions, chatter, tasks.

```pseudocode
// Look for:
- Decisions that contradict each other (e.g., "chose REST" in one, "using GraphQL" in another)
- Brief stating one stack but decisions referencing another
- Scope "out" items that appear in later sessions as completed work
- Preferences in crew/preferences.md that conflict with project-specific conventions

FOR each contradiction found:
    REPORT: what contradicts what, where each claim lives (wikilinks), which is likely current
```

**Bostrol presents contradictions.** He's the one who cares most about documentation consistency.

### 2. Stale Information

```pseudocode
// Look for:
- Decisions marked "active" but older than 30 days with no recent references
- Brief sections that haven't been updated since project start
- Session notes referencing components/endpoints that no longer exist in codebase
- Tasks marked "open" that were completed (cross-reference with session summaries)

FOR each stale item:
    REPORT: what's stale, how old, suggested action (update / archive / remove)
```

**Jonasty presents stale info.** His QA instincts make him the natural auditor.

### 3. Dangling Scopes

```pseudocode
// Look for:
- Scope items marked "in" that never appear in any session summary as worked on
- Parking lot items that were never revisited
- Tasks with no assignee or no activity
- Decisions that reference "next session" or "follow-up" with no subsequent entry

FOR each dangling item:
    REPORT: what's dangling, when it was added, suggested disposition (do / park / drop)
```

**Kevijntje presents scope issues.** This is his domain — he lives for this.

### 4. Unacted Decisions

```pseudocode
// Decisions with status "active" that have consequences listed but no evidence
// of those consequences being implemented in subsequent sessions.

FOR each unacted decision:
    REPORT: decision summary, consequence that was supposed to happen, evidence gap
```

### 5. Documentation Gaps

```pseudocode
// Look for:
- Sessions with no decisions logged (did nothing notable happen, or was it missed?)
- Gates mentioned in sessions but no corresponding decision notes
- Project brief missing stack, repo, or scope sections
- Empty or stub files in decisions/ or sessions/

FOR each gap:
    REPORT: what's missing, where it should be, severity (minor gap / significant omission)
```

---

## Output Format

The dream produces an **in-chat report** with wikilink references to every item discussed. It is NOT persisted to the vault — it's a working document. After Tom reviews and acts on the findings, the cleanup is what persists.

```markdown
# 💤 Dream Report — {project_name}
*{DATE} — The Chroniclers*

## Contradictions (X found)
- ...

## Stale Info (X items)
- ...

## Dangling Scopes (X items)
- ...

## Unacted Decisions (X items)
- ...

## Documentation Gaps (X items)
- ...

## Recommended Actions
1. ...
2. ...
3. ...

---
*This report is ephemeral. Act on it, then let it go.*
```

---

## After the Dream

Tom reviews the report. For each item, he can:
- **Fix it** — the crew makes the update immediately
- **Park it** — acknowledged but not urgent
- **Dismiss it** — the Chroniclers accept (with personality)

Bostrol tracks which items were addressed and which were dismissed. The session summary notes that a `/dream` was run and how many items were resolved.

---

## Token Budget

A `/dream` crawl reads a lot of vault content. Be efficient:
- Read frontmatter first, full content only when needed
- Don't re-read files already in context
- Summarize findings as you go — don't accumulate then dump
- Target: complete dream in under 5 minutes of wall time
