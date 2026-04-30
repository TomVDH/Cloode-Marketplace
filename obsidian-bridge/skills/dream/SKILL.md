---
name: dream
description: Two-pass vault analysis. Pass 1 finds structural drift and offers auto-fixes. Pass 2 surfaces content-level issues for review.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
version: 0.1.0
---

`/dream` performs a deep analysis of vault data, surfacing issues that accumulate silently across sessions. This is not a status report — it's a diagnostic.

## Scope

Default: current project only (read `project_slug` from breadcrumb). `--vault-wide` scans all projects. `--save` persists the report to `projects/{slug}/dreams/YYYY-MM-DD.md`.

## Token Budget

`/dream` is the hungriest command. Mitigations:
- Read frontmatter first; full body only when needed for content checks.
- Summarise findings as the scan proceeds; don't accumulate then dump.
- Target: complete project dream in <5 minutes wall time.

---

## Pass 1 — Structural Sanitation

Scans for auto-fixable drift and manual-decision items.

```pseudocode
vault_path = read vault_path from breadcrumb
project_slug = read project_slug from breadcrumb
vault_wide = "--vault-wide" in args

IF vault_wide:
    slugs = list all project dirs in projects/ and archive/
ELSE:
    IF NOT project_slug: ERROR "No project linked. Use --vault-wide or link a project first."
    slugs = [project_slug]

auto_fixes = []
needs_decision = []

FOR each slug in slugs:
    project_dir = resolve(slug)  // projects/{slug} or archive/{slug}

    // --- Core structural checks ---

    // 1. Empty project folder
    md_count = count .md files in project_dir (recursive)
    IF md_count == 0:
        needs_decision.add("Empty project folder: {slug} — archive or delete?")
        CONTINUE

    // 2. Missing brief.md
    IF NOT exists brief.md:
        needs_decision.add("Project '{slug}' has no brief.md — scaffold from template?")

    // 3. Slug shape violation
    IF slug contains dots OR spaces OR uppercase:
        needs_decision.add("Slug '{slug}' violates naming rules — rename via CLI?")

    // 4. Collection folders missing _index.md
    FOR each subfolder:
        IF has ≥2 .md siblings AND name NOT IN [sessions, images, assets, previews, .obsidian]:
            IF NOT exists _index.md:
                auto_fixes.add({
                    desc: "Missing _index.md in {slug}/{folder}",
                    action: "create from collection-index template"
                })

    // 5. _index.md out of sync
    FOR each _index.md:
        disk_entries = list .md siblings (excluding _index.md)
        index_links = extract [[...]] from _index.md
        IF disk_entries != index_links:
            auto_fixes.add({
                desc: "_index.md out of sync in {slug}/{folder}",
                action: "rebuild from disk"
            })

    // 6. Files missing frontmatter
    FOR each .md file (excluding .obsidian/, templates/):
        IF no YAML frontmatter (no leading ---):
            auto_fixes.add({
                desc: "No frontmatter: {file}",
                action: "add minimal frontmatter based on location"
            })

    // 7. Malformed/incomplete frontmatter
    FOR each .md with frontmatter:
        required = get_required_fields(file.type)
        missing = required - present_fields
        IF missing:
            auto_fixes.add({
                desc: "Incomplete frontmatter: {file} — missing {missing}",
                action: "add missing fields with defaults"
            })

    // 8. Broken wikilinks
    FOR each [[target]] in all files:
        IF NOT resolvable in vault:
            needs_decision.add("Broken wikilink [[{target}]] in {file}")

    // 9. Markdown-style links
    FOR each [text](path) in vault files:
        auto_fixes.add({
            desc: "Markdown link in {file}: [{text}]({path})",
            action: "replace with [[{equivalent}]]"
        })

    // 10. Tag hygiene
    all_tags = collect all tags in scope
    FOR tag with usage == 1:
        needs_decision.add("Single-use tag #{tag} in {file}")
    FOR (a, b) where a and b are near-duplicates:
        needs_decision.add("Near-duplicate tags: #{a} vs #{b}")
    FOR tag in [wip, misc, general, thoughts]:
        IF used:
            needs_decision.add("Vague tag #{tag} — consolidate or remove?")
    FOR tag NOT matching ob/* and starting with ob/:
        needs_decision.add("Tag #{tag} drifts from ob/ namespace convention")

    // 11. Stale updated date
    IF brief.status == "active" AND brief.updated > 90 days ago:
        needs_decision.add("Stale project '{slug}' — active but not updated in {days}d")

    // 12. Decision filename pattern
    FOR each file in decisions/:
        IF NOT matches /^\d{4}-\d{2}-\d{2}-.+\.md$/:
            auto_fixes.add({
                desc: "Decision filename violation: {file}",
                action: "rename to YYYY-MM-DD-{slug}.md"
            })

    // 13. Session filename pattern
    FOR each file in sessions/:
        IF NOT matches /^\d{4}-\d{2}-\d{2}\.md$/:
            auto_fixes.add({
                desc: "Session filename violation: {file}",
                action: "rename to YYYY-MM-DD.md"
            })

    // 14. Root docs missing type: doc
    FOR each .md in project root:
        IF name NOT IN [brief.md, _handoff.md, _index.md] AND NOT starts with _:
            IF NOT has type: doc:
                auto_fixes.add({
                    desc: "Root doc missing type: doc — {file}",
                    action: "add type: doc frontmatter"
                })

    // 15. Brief body missing required blocks
    IF brief.md exists:
        project_type = read project_type from brief
        required_blocks = get_required_blocks(project_type)
        existing_blocks = parse ## headers from brief body
        FOR block IN required_blocks NOT IN existing_blocks:
            auto_fixes.add({
                desc: "Brief missing block: ## {block}",
                action: "add empty block"
            })

    // --- Iteration-specific checks ---

    // 16. Emergent iteration folders
    FOR folder_name IN [design-iterations, surfaces, aesthetics]:
        IF exists {project_dir}/{folder_name}/:
            needs_decision.add("Emergent iteration folder '{folder_name}' — canonicalise to iterations/?")

    // 17. Iteration filename pattern
    IF exists iterations/:
        FOR each entry in iterations/:
            IF is .md AND NOT matches /^\d{4}-\d{2}-\d{2}-iter-.+\.md$/ AND name != _index.md:
                auto_fixes.add({
                    desc: "Iteration filename violation: {entry}",
                    action: "rename to YYYY-MM-DD-iter-{id}-{slug}.md"
                })

    // 18. Stale drafting iterations (>30d)
    FOR each iteration with status == "drafting":
        IF date > 30 days ago:
            needs_decision.add("Iteration {identifier} drafting for {days}d — park, finish, or reject?")

    // 19. Track with picked but siblings not superseded
    tracks = group iterations by track
    FOR each track:
        picked = iterations with status == "picked"
        others = iterations with status NOT IN [picked, rejected, superseded, parked]
        IF picked.length > 0 AND others.length > 0:
            auto_fixes.add({
                desc: "Track '{track}' has picked iteration but {others.length} sibling(s) not superseded",
                action: "set siblings to superseded"
            })

    // 20. Broken supersedes/builds_on
    FOR each iteration with supersedes or builds_on:
        IF target not resolvable:
            needs_decision.add("Broken lineage link in iteration {identifier}: {link}")

    // 21. iterations/_index.md out of sync
    IF exists iterations/_index.md:
        disk_iters = list iteration files
        index_iters = parse _index.md links
        IF mismatch:
            auto_fixes.add({
                desc: "iterations/_index.md out of sync",
                action: "rebuild from disk"
            })
```

---

## Pass 2 — Content Analysis

Report-only findings. Never auto-actioned.

```pseudocode
content_findings = {
    contradictions: [],
    stale_info: [],
    dangling_scopes: [],
    unacted_decisions: [],
    documentation_gaps: []
}

FOR each slug in slugs:

    // 1. Contradicting information
    // Scan brief, decisions, sessions for conflicting statements:
    // - Decisions that contradict each other (e.g., "chose REST" vs "using GraphQL")
    // - Brief stating one stack but decisions referencing another
    // - Scope "out" items appearing in later sessions as completed
    decisions = read all decision files (frontmatter + body)
    brief = read brief body
    sessions = read recent session summaries
    FOR each pair of potentially contradicting claims:
        content_findings.contradictions.add({
            what: description of contradiction,
            where: [wikilink to file A, wikilink to file B],
            likely_current: best guess at which is current
        })

    // 2. Stale information
    // - Decisions marked "active" but >30d with no recent references
    // - Brief sections unchanged since creation
    // - Session notes referencing components that may no longer exist
    FOR each decision with status "active" AND date > 30 days ago:
        refs = vault.search("[[{decision_filename}]]", "projects/{slug}")
        IF refs.count == 0:
            content_findings.stale_info.add({
                what: "Unreferenced active decision: {title}",
                age: "{days}d",
                suggestion: "update, archive, or mark implemented"
            })

    // 3. Dangling scopes
    // - Scope "in" items never appearing in session summaries
    // - Parking lot items never revisited
    // - References to "next session" or "follow-up" with no subsequent entry
    IF brief contains scope sections:
        scope_items = parse scope in/out items from brief
        session_content = concatenate all session summaries
        FOR each scope_in item:
            IF item NOT mentioned in any session:
                content_findings.dangling_scopes.add({
                    what: item,
                    added: "unknown",
                    suggestion: "do, park, or drop"
                })

    // 4. Unacted decisions
    // Decisions with consequences that show no evidence of implementation
    FOR each decision with status "active":
        consequences = parse consequence section
        IF consequences AND NOT found evidence in sessions/brief:
            content_findings.unacted_decisions.add({
                decision: wikilink to decision,
                consequence: summary,
                gap: "no evidence of implementation"
            })

    // 5. Documentation gaps
    // - Sessions with no decisions (notable work happened but wasn't captured?)
    // - Brief missing core sections for its type
    // - Empty stub files
    FOR each session:
        session_date = filename date
        decisions_on_date = decisions with date == session_date
        IF decisions_on_date.count == 0:
            content_findings.documentation_gaps.add({
                what: "Session {date} has no decisions",
                severity: "minor"
            })
    FOR each .md file with body shorter than 3 lines (excluding frontmatter):
        content_findings.documentation_gaps.add({
            what: "Stub file: {file}",
            severity: "minor"
        })
```

---

## Output

```pseudocode
// Build report
report = """
# Dream Report — {project_name}
*{TODAY}*

## Structural — Auto-fixable ({auto_fixes.count} items)
"""
FOR each fix in auto_fixes:
    report += "1. {fix.desc}\n"

report += "[Fix all] [Pick] [Skip]\n\n"

report += "## Structural — Needs decision ({needs_decision.count} items)\n"
FOR each item in needs_decision:
    report += "- {item}\n"

report += "\n## Content — Findings\n"

IF content_findings.contradictions:
    report += "### Contradictions ({count})\n"
    FOR each: report += "- {what}\n  Files: {where}\n"

IF content_findings.stale_info:
    report += "### Stale Info ({count})\n"
    FOR each: report += "- {what} ({age})\n"

IF content_findings.dangling_scopes:
    report += "### Dangling Scopes ({count})\n"
    FOR each: report += "- {what}\n"

IF content_findings.unacted_decisions:
    report += "### Unacted Decisions ({count})\n"
    FOR each: report += "- {decision}: {consequence}\n"

IF content_findings.documentation_gaps:
    report += "### Documentation Gaps ({count})\n"
    FOR each: report += "- {what} ({severity})\n"

// Display
PRINT report

// Handle auto-fix choices
IF user chooses "Fix all":
    FOR each fix in auto_fixes:
        EXECUTE fix.action
        REPORT: "✓ {fix.desc}"
ELIF user chooses "Pick":
    FOR each fix in auto_fixes:
        ASK: "Fix: {fix.desc}? [y/n]"
        IF yes: EXECUTE fix.action

// Save if --save flag
IF "--save" in args:
    dreams_dir = "projects/{slug}/dreams"
    IF NOT exists dreams_dir:
        mkdir dreams_dir
        CREATE dreams/_index.md from collection-index template
    vault.write("projects/{slug}/dreams/{TODAY}.md", dream_report_with_frontmatter(report))
    REPORT: "Report saved to projects/{slug}/dreams/{TODAY}.md"
```

---

## Personality Layer

When cabinet-of-imd is installed and active, the chronicler voice (Bostrol/Kevijntje/Jonasty) wraps the report. Bridge detects cabinet via the `crew/` folder and adjusts formatting if the current session is a `/cabinet` session. Without cabinet, `/dream` is dry — no personality, no flair, just the report.

---

## When to Suggest

Bridge does not auto-suggest `/dream`. The command is always explicit. If cabinet is installed, cabinet's suggestion logic applies (Kevijntje suggests at 5+ sessions, 14+ days idle, or 3+ scope drifts).
