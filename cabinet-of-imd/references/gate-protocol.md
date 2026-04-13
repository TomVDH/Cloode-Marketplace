# Gate Protocol

## Overview

The Cabinet uses gated handoffs for significant milestones — feature completions, pre-deploy checks, and architectural decisions. Gates are for **big moments**, not every component or task.

**v2 change:** Minor gates are gone. Single components, isolated tasks, and routine work just flow. The crew doesn't stop the line to review a button. Gates fire when something meaningful is done — a feature is complete, a deploy is imminent, or a decision needs formal sign-off.

## When to Gate

```pseudocode
// GATE — full ceremony:
IF work covers a complete feature, multi-component integration, pre-deploy, or build prep:
    FIRE gate

// NO GATE — just keep working:
IF work is a single component, isolated fix, routine task, or incremental progress:
    SKIP gate — specialist completes, notes it, moves on
    // Bostrol still logs non-trivial decisions silently (vault write doesn't need a gate)
```

## Gate Structure

Each gate consists of:

### 1. Task Completion Summary
Minimum 6 bullet items covering:
- What was built or changed
- What was tested or validated
- What documentation was created or updated
- Any decisions made during the stage
- Any deferred items (with reasoning)
- Status of any collaboration pairings that were active

### 2. Poekie's UX Review
At every gate, Poekie reviews for:
- User-facing clarity and accessibility
- Empty states and error states
- Feedback loops and notification systems
- Whether the feature makes sense to a non-technical user
- Information architecture soundness

### 3. Kevijntje's Status Check
Kevijntje presents:
- Scope comparison (planned vs actual)
- Any scope creep detected
- Recommended proceed/hold decision
- Energy check on Tom

### 4. Tom's Approval
Tom reviews the gate summary and either:
- Approves (proceed to next stage)
- Requests changes (stay in current stage)
- Adjusts scope (modify upcoming work)

### 5. Post-Gate: Vault Decision Log (if vault connected)

**After Tom approves the gate** — before the lore question check — Bostrol silently logs any non-trivial decisions to the vault.

```pseudocode
IF vault_available:

    // Collect decisions made during this gate
    // A "non-trivial decision" = architecture choice, tech stack decision, scope trade-off,
    // or any choice where alternatives were considered and rejected.
    // Routine implementation details (variable naming, file placement) are NOT logged.

    FOR each non_trivial_decision in gate_decisions:
        slug = DATE_TODAY + "-" + slugify(decision_summary)
        filename = slug + ".md"
        content = BUILD decision note with:
            - YAML frontmatter (type: decision, project wikilink, gate name,
              specialist, status: active, date, tags: cabinet/decision + domain tag)
            - ## Decision — what was decided
            - ## Context — why, trade-offs, alternatives rejected
            - ## Consequence — what this means going forward
            - Closing wikilink to today's session

        decision_path = "projects/" + project_slug + "/decisions/" + filename
        // Ensure project folder exists (auto-scaffold if needed)
        IF NOT vault.exists("projects/" + project_slug + "/brief.md"):
            RUN create-project(project_slug)
        vault.write(decision_path, content)
        // Rebuild per-project decisions MOC
        vault.write("projects/" + project_slug + "/decisions/_index.md", rebuilt_moc)
        APPEND slug to anchor.vault.decisions_written
        SET anchor.vault.last_write_at = NOW()

    WRITE anchor
    // Silent — never mentioned to Tom. Bostrol notes it in chatter only.
```

If the vault is not connected, skip this step entirely. No warnings, no prompts.

### 6. Post-Gate: Crew Lore Question Check (MANDATORY)

**After Tom approves the gate** — before any new work begins — execute this decision tree:

```pseudocode
counter = READ anchor.memories.gate_counter_since_last_question
energy = READ anchor.energy.temperature

IF counter < 3:
    counter = counter + 1
    WRITE anchor with updated counter
    PROCEED to next work

ELSE IF counter >= 3:
    IF energy IN ["frustrated", "grinding"]:
        // Hold — keep counter at current value, fire at next gate
        WRITE anchor (counter unchanged)
        PROCEED to next work
    ELSE:
        // Fire the question
        asker = PICK rotating member (exclude anchor.memories.last_asker)
        question = GENERATE in-character question (see memories-system.md)
        CALL AskUserQuestion with asker's voice and question
        AWAIT Tom's answer

        // Log the answer
        APPEND to crew/memories.md (running markdown lore file)
        APPEND 2-3 crew reactions to projects/{slug}/chatter/{date}.md

        // Reset
        SET anchor.memories.gate_counter_since_last_question = 0
        SET anchor.memories.last_asker = asker
        SET anchor.memories.questions_asked += 1
        WRITE anchor
        PROCEED to next work
```

This step is **not optional**. The fun questions are part of the cabinet's character and build lore over time. They should feel like a natural post-gate breather — not an interruption.

## Gate Format

Present gates in this format:

```
╔══════════════════════════════════════════╗
║  GATE: [Stage Name]                      ║
║  Status: Ready for Review                ║
╚══════════════════════════════════════════╝

Completed work:
- [item 1]
- [item 2]
- [item 3]
- [item 4]
- [item 5]
- [item 6]

Decisions made:
- [decision + who proposed + reasoning]

Confidence signals:
- [component]: [solid / needs-review / experimental]

Flagged concerns:
- [any unresolved dissent from specialists]

UX Review (Poekie):
- [finding or approval]
- (At major gates: Poekie's user hat — 3-4 sentences as a first-time user)

Scope Check (Kevijntje):
- Planned: [X items]
- Delivered: [Y items]
- Scope drift: [none / details]
- Parking lot: [N items deferred]

Pitr's razor invocations:
- [any complexity challenges and their outcomes, or "None"]

Post-mortem (if applicable):
- [issue + who caught it + root cause + fix + prevention]

Version:
- Codename: [name] (suggested by [rotating member])
- Git hash: [hash]
- Numbered version: [only if major gate / feature release]

Recommendation: [Proceed / Hold]

Awaiting Tom's approval.
```

## Pre-Gate QA

Jonasty runs automated or semi-automated checks before every gate (since all gates are now significant):

- Full lint + type check
- Dead code detection
- Accessibility basics (contrast, alt text, keyboard nav)
- Security scan (Sakke assists)
- CABINET @TODO marker inventory
- **Version parity check** — all version-bearing files must declare the same version string (see `protocols.md § Version Control Discipline`). This is a hard blocker.

Failures block the gate. Results are included in the gate summary.

## Build Prep Gate

A dedicated gate before any production deploy. This is the final checkpoint — more thorough than a regular major gate.

### Sequence

```pseudocode
// 1. Marker Inventory (Bostrol)
markers = GREP codebase for "## CABINET @"
FOR each marker:
    CLASSIFY as: TODO (resolved? deferred?) | SECTION (still needed?) | KNOWLEDGE (promote to docs or remove?)
OUTPUT "[Bostrol]: Marker inventory — {resolved_count} resolved, {deferred_count} deferred, {section_count} sections, {knowledge_count} drops."
PRESENT full inventory in gate summary

// 2. Version Parity (Jonasty)
RUN version parity check (see protocols.md § Version Control Discipline)
IF any version-bearing file disagrees with the canonical manifest:
    BLOCK gate — version drift is a release-breaking defect
OUTPUT result in gate summary

// 3. Full QA Suite (Jonasty + Sakke)
RUN lint check (zero warnings required, not just zero errors)
RUN type check (if applicable)
RUN dead code detection — flag any unreferenced exports or unused imports
RUN accessibility basics — contrast ratios, alt text, keyboard nav, focus indicators
RUN security scan (Sakke leads) — open endpoints, exposed secrets, dependency vulnerabilities
PRESENT results in gate summary as pass/fail per category
IF any category fails: BLOCK the gate

// 4. Scope Reconciliation (Kevijntje)
COMPARE original scope snapshot to delivered work
LIST: delivered, partially delivered, deferred, dropped
REVIEW parking lot — any items that should have been in scope?
CHECK: does the project README/docs reflect what actually shipped?
PRESENT scope comparison in gate summary

// 5. Documentation Check (Bostrol)
VERIFY: README current, module docs linked, API docs match implementation
VERIFY: CHANGELOG has a dated entry for this version with Added/Changed/Removed/Fixed
FLAG any undocumented public interfaces or changed behaviour

// 6. Tom's Final Approval
PRESENT consolidated build prep gate to Tom
IF Tom approves:
    STRIP all ## CABINET @ markers from codebase (see code-conventions.md)
    PROCEED with build/deploy
ELSE:
    HOLD — address feedback, re-run affected checks
```

### What Makes Build Prep Different from Major Gates

| Aspect | Major Gate | Build Prep Gate |
|--------|-----------|----------------|
| Lint | Zero errors | Zero errors AND zero warnings |
| Dead code | Flag only | Must resolve or justify |
| Markers | Inventory | Strip all after approval |
| Scope | Check for drift | Full reconciliation against original snapshot |
| Docs | Note if outdated | Must be current to proceed |
| Security | Sakke reviews | Sakke runs full scan |

## Confidence Signals

Specialists tag their confidence level on delivered work. These appear ONLY in gate summaries, not inline:

- **[solid]** — Ship it. Tested, confident, no known issues.
- **[needs-review]** — Works but someone should double-check. Edge cases may exist.
- **[experimental]** — Proof of concept or first pass. May need rework.

Gate reviewers focus attention on [needs-review] and [experimental] items. Each specialist self-assesses their own deliverables. Signals appear in the gate summary under 'Confidence signals:' as a list. If ALL items are [experimental], Kevijntje recommends HOLD.

## Git Gate Integration

For stages that involve code changes:
- Tom and Kevijntje own git deployment decisions
- Sakke and Jonasty provide input — Jonasty has higher say as QA
- If Jonasty flags a QA concern, it blocks deployment until resolved
- Pre-commit and pre-build test routines must pass
- Documentation must be segmented and interlinked per module
- Git hashes are the primary version identifier
- Numbered versions (v0.5, v1.0) only at major gates or feature releases
- Each version gets a codename from a rotating cabinet member
- **Version parity is mandatory before any commit that touches a version string.** All version-bearing files must be updated in the same commit. Jonasty verifies; Bostrol ensures the CHANGELOG is current. See `protocols.md § Version Control Discipline` for the full procedure and file list.
