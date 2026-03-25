# Gate Protocol

## Overview

The Cabinet uses gated handoffs to ensure quality and completeness at each stage of a project. No work proceeds to the next stage until the current gate is passed.

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
        APPEND card to crew-notes/team-fun-memories.html
        APPEND 2-3 crew reactions to crew-notes/cabinet-chatter.html

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

## Tiered Pre-Gate QA

Jonasty runs automated or semi-automated checks before gates. The level of scrutiny is proportional to the gate's significance:

**Classification rule:**
```pseudocode
IF gate covers a single component, function, or isolated task:
    tier = MINOR
ELSE IF gate covers a complete feature, pre-deploy check, or build prep:
    tier = MAJOR
```

### Minor Gates (component done, task complete)
- Quick lint check
- Type errors (if applicable)
- Basic sanity pass

### Major Gates (feature complete, pre-deploy, build prep)
- Full lint + type check
- Dead code detection
- Accessibility basics (contrast, alt text, keyboard nav)
- Security scan (Sakke assists)
- CABINET @TODO marker inventory

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

// 2. Full QA Suite (Jonasty + Sakke)
RUN lint check (zero warnings required, not just zero errors)
RUN type check (if applicable)
RUN dead code detection — flag any unreferenced exports or unused imports
RUN accessibility basics — contrast ratios, alt text, keyboard nav, focus indicators
RUN security scan (Sakke leads) — open endpoints, exposed secrets, dependency vulnerabilities
PRESENT results in gate summary as pass/fail per category
IF any category fails: BLOCK the gate

// 3. Scope Reconciliation (Kevijntje)
COMPARE original scope snapshot to delivered work
LIST: delivered, partially delivered, deferred, dropped
REVIEW parking lot — any items that should have been in scope?
CHECK: does the project README/docs reflect what actually shipped?
PRESENT scope comparison in gate summary

// 4. Documentation Check (Bostrol)
VERIFY: README current, module docs linked, API docs match implementation
FLAG any undocumented public interfaces or changed behaviour

// 5. Tom's Final Approval
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
