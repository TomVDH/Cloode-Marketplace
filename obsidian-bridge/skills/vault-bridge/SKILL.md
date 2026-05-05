---
name: vault-bridge
description: Operate the Obsidian vault. Dispatched by /connect, /sync, /check, /draw, /ramasse, /iterate. Use for vault setup, project scaffolding, syncing briefs, status views, cleanup, visual-artefact discovery, iteration state.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
version: 0.1.0
---

Bridge between Claude Code sessions and a persistent Obsidian vault. This skill handles explicit vault operations — creating, connecting, scaffolding, syncing, archiving, housekeeping, iterations, migration, and handoff. Vault interactions outside of explicit commands should be silent and automatic.

## Vault Structure (v3)

Full structure, frontmatter schemas, naming rules, wikilink conventions, and tag taxonomy are in the `obsidian-bridge:vault-standards` skill. Key paths:

- `projects/{slug}/brief.md` — project brief (type-shaped by `project_type`)
- `projects/{slug}/decisions/` — decision records
- `projects/{slug}/sessions/` — session summaries
- `projects/{slug}/notes/` — general notes
- `projects/{slug}/iterations/` — design/code iterations (opt-in)
- `archive/{slug}/` — archived projects (same shape)
- `Home.md` — auto-rebuilt vault home

Subfolder defaults vary by project type (`coding`, `knowledge`, `plugin`, `tinkerage`) — see `obsidian-bridge:vault-standards` § Per-Type Project Subfolder Defaults.

## Vault Primitives

All vault operations go through the `vault.*` abstraction defined in `references/vault-integration.md`. CLI-first policy: prefer Obsidian CLI for every operation it supports. Filesystem fallback when CLI unavailable.

```pseudocode
FUNCTION vault_op(op, args):
    IF cli_available():
        RUN via obsidian CLI
    ELSE:
        RUN via filesystem (Read/Write/Glob/Grep)
```

Read `references/vault-integration.md` for the full operation table and fallback rules.

---

## Anchor / Breadcrumb file

Every per-project link to a vault is persisted in a small key=value anchor file. All vault-bridge operations read it on every operation; SessionStart, UserPromptSubmit, PostToolUse, and PreCompact hooks read it too.

**Canonical location (current):** `$CLAUDE_PROJECT_DIR/.claude/obsidian-bridge`
**Legacy location (still read for backward compat):** `$CLAUDE_PROJECT_DIR/.obsidian-bridge`

**Read pattern (all operations):** look for the canonical file first; if absent, fall back to the legacy file. If neither exists, the project is "not linked."

**Write pattern (all operations that create or update the anchor):**
1. `mkdir -p $CLAUDE_PROJECT_DIR/.claude` (no-op if it already exists).
2. Write to `$CLAUDE_PROJECT_DIR/.claude/obsidian-bridge`.
3. Append `.claude/obsidian-bridge` to `.gitignore` if not already present.
4. Legacy `$CLAUDE_PROJECT_DIR/.obsidian-bridge` cleanup is handled silently and automatically by the SessionStart hook (step 0).

Wherever the pseudocode below says `read … from breadcrumb` or `WRITE breadcrumb`, this is the file and the pattern in use.

---

## Commands

### /connect — onboard

Combined entry for create + connect + link + create-project. Inference rules:

| Path state | Action |
|---|---|
| Path doesn't exist | Create new vault (scaffold Home.md, projects/, templates/) |
| Path exists with Home.md (type: vault-home or cabinet-home) | Connect (read-only verification of vault structure) |
| Path exists with projects/ folder, no Home.md | Connect (best-effort) |
| Path exists with neither | Error: "Expected Home.md with type: vault-home or a projects/ folder at <path>" |

Subforms:
- `/connect` (no args) — discover or prompt for path
- `/connect <path>` — infer create vs connect from path state
- `/connect <path> <slug>` — connect AND link to project <slug>
- `/connect --new <path>` — force-create (error if path is non-empty and not a vault)
- `/connect --link-only <slug>` — set slug only; vault must already be connected

```pseudocode
PARSE flags and positional args from invocation
breadcrumb = read canonical anchor at $CLAUDE_PROJECT_DIR/.claude/obsidian-bridge

CASE invocation:
  --link-only <slug>:
    // Original /link logic — see "link subform" pseudocode below

  --new <path>:
    // Force-create — see "create subform" pseudocode below

  bare <path>:
    IF path doesn't exist: → create flow
    ELIF path/Home.md exists with type vault-home|cabinet-home: → connect flow
    ELIF path/projects/ exists: → connect flow (best-effort)
    ELSE: ERROR

  bare <path> <slug>:
    Run the path-inference flow above to ensure connect, then run link <slug>

  no args:
    IF breadcrumb exists: REPORT current vault + project (read-only summary)
    ELSE: PROMPT user for vault path
```

#### create subform — Scaffold a new v3 vault

```pseudocode
IF user provides path: vault_path = resolve(path)
ELSE: REQUEST path from user

IF non-empty dir AND not an Obsidian vault:
    offer subfolder mode (_cabinet/) or new location
ELSE:
    base = vault_path

mkdir -p projects, archive, templates
COPY templates from plugin examples/vault-templates/ to {base}/templates/
CREATE Home.md from home.md template (set updated: TODAY)
CREATE projects/_index.md from projects-index.md template

// Detect transport
IF cli_available():
    mode = "cli"
    vault_name = basename(vault_path)
ELSE:
    mode = "filesystem"
    vault_name = basename(vault_path)

// Write breadcrumb (canonical location — see "Anchor / Breadcrumb file")
mkdir -p $CLAUDE_PROJECT_DIR/.claude
WRITE $CLAUDE_PROJECT_DIR/.claude/obsidian-bridge:
    vault_path={base}
    vault_name={vault_name}
    project_slug=
    linked_at={TODAY}
    mode={mode}

// Add to .gitignore if not present
IF .gitignore exists AND NOT contains ".claude/obsidian-bridge":
    APPEND ".claude/obsidian-bridge" to .gitignore

REPORT: "Vault created at {base}. Transport: {mode}. Run /connect <path> <slug> to scaffold your first project."
```

#### connect subform — Point at an existing vault

```pseudocode
path = resolve(user-provided path)

// 1. Detect vault
IF path contains Home.md with type: vault-home OR type: cabinet-home:
    base = path
ELIF path/projects/ exists:
    base = path
ELSE:
    ERROR "No vault found at this path. Expected Home.md with type: vault-home or a projects/ folder."

// 2. Detect schema version
has_project_type = false
FOR each project dir in base/projects/:
    IF brief.md exists AND contains "project_type:":
        has_project_type = true
        BREAK

IF has_project_type:
    version = "v3"
ELIF any project has brief.md + decisions/ + sessions/:
    version = "v2"
ELSE:
    version = "unknown"

// 3. Detect transport
IF cli_available():
    mode = "cli"
    vault_name = detect_vault_name() OR basename(path)
ELSE:
    mode = "filesystem"
    vault_name = basename(path)

// 4. Inventory
FOR each project dir in base/projects/:
    count decisions, sessions
    read brief status and project_type
    REPORT: slug, type, status, decisions, sessions

// 5. Write breadcrumb (no project_slug yet — user links separately)
//    Canonical location — see "Anchor / Breadcrumb file"
mkdir -p $CLAUDE_PROJECT_DIR/.claude
WRITE $CLAUDE_PROJECT_DIR/.claude/obsidian-bridge:
    vault_path={base}
    vault_name={vault_name}
    project_slug=
    linked_at={TODAY}
    mode={mode}

// 6. Add to .gitignore if needed
IF .gitignore exists AND NOT contains ".claude/obsidian-bridge":
    APPEND ".claude/obsidian-bridge" to .gitignore

// 7. Cabinet detection
IF base/crew/ exists:
    REPORT: "Cabinet detected — crew/ folder present, untouched by bridge."

IF version == "v2":
    SUGGEST: "Run vault migration to convert to v3 schema."

REPORT: "Connected to {vault_name} at {base}. Schema: {version}. Transport: {mode}."
```

#### link subform — Set project slug for current directory

```pseudocode
slug = user-provided slug
breadcrumb = first existing of:
    $CLAUDE_PROJECT_DIR/.claude/obsidian-bridge
    $CLAUDE_PROJECT_DIR/.obsidian-bridge   // legacy

IF NOT breadcrumb:
    ERROR "No vault connected. Run /connect <path> first."

// Read existing breadcrumb
vault_path = read vault_path from breadcrumb

// Validate slug exists
IF NOT exists {vault_path}/projects/{slug}/brief.md:
    // List available projects
    available = list dirs in {vault_path}/projects/
    ERROR "Project '{slug}' not found. Available: {available}"

// Update breadcrumb with new slug
UPDATE breadcrumb: project_slug={slug}, linked_at={TODAY}

// Read project info
project_type = read project_type from brief.md
status = read status from brief.md

REPORT: "Linked to project '{slug}' (type: {project_type}, status: {status})."
```

#### create-project subform — Scaffold a type-shaped project

Requires both `<slug>` and `<type>`. Asks if either is omitted. Validates slug against naming rules (lowercase, hyphenated, no spaces, no dots).

```pseudocode
slug = validate_slug(user-provided slug)
project_type = validate_type(user-provided type)  // coding | knowledge | plugin | tinkerage

// Read breadcrumb for vault path (canonical-then-legacy lookup)
vault_path = read vault_path from breadcrumb
IF NOT vault_path: ERROR "No vault connected."

project_dir = {vault_path}/projects/{slug}
IF exists project_dir: ERROR "Project '{slug}' already exists."

// 1. Create project directory
mkdir {project_dir}

// 2. Create brief from type-shaped template
template = read examples/vault-templates/brief-{project_type}.md
brief = template with:
    slug: {slug}
    aliases: [{slug}]
    created: {TODAY}
    updated: {TODAY}
    # Title set to slug (user can rename)
vault.write("projects/{slug}/brief.md", brief)

// 3. Scaffold type-specific subfolders
MATCH project_type:
    "coding":
        FOR folder IN [decisions, notes, tasks, references, sessions, images]:
            mkdir {project_dir}/{folder}
        FOR folder IN [decisions, notes, tasks, references]:
            vault.write("projects/{slug}/{folder}/_index.md", collection_index(slug, folder))

    "plugin":
        FOR folder IN [decisions, notes, tasks, references, releases, sessions, images]:
            mkdir {project_dir}/{folder}
        FOR folder IN [decisions, notes, tasks, references, releases]:
            vault.write("projects/{slug}/{folder}/_index.md", collection_index(slug, folder))

    "knowledge":
        FOR folder IN [notes, sources, references, sessions]:
            mkdir {project_dir}/{folder}
        FOR folder IN [notes, sources, references]:
            vault.write("projects/{slug}/{folder}/_index.md", collection_index(slug, folder))

    "tinkerage":
        mkdir {project_dir}/sessions   // optional, created for convenience

// 4. Update projects/_index.md
REBUILD projects/_index.md from all project briefs

// 5. Update Home.md
RUN update_home()

// 6. Update breadcrumb with slug (writes go to canonical .claude/obsidian-bridge)
UPDATE breadcrumb: project_slug={slug}

// 7. If codebase root detected, scaffold codebase dirs
IF git root OR $CLAUDE_PROJECT_DIR is a code project:
    mkdir -p assets, concepts, previews in codebase root (if not exists)

REPORT: "Project '{slug}' scaffolded as {project_type}. Folders: [list]. Brief at projects/{slug}/brief.md."


// Helper: generate collection _index.md
FUNCTION collection_index(slug, folder_name):
    RETURN template from examples/vault-templates/collection-index.md with:
        project: "[[projects/{slug}/brief|{slug}]]"
        title: capitalize(folder_name)
```

### /sync — push state

Combined sync + handoff sync. Subforms:
- `/sync` — both brief and handoff
- `/sync brief` — brief only
- `/sync handoff` — handoff only

The default `/sync` runs brief sync followed by handoff sync in sequence.

#### brief subform — Write/update current project's brief

```pseudocode
// Read breadcrumb
vault_path = read vault_path from breadcrumb
project_slug = read project_slug from breadcrumb
IF NOT project_slug: ERROR "No project linked."

brief_path = "projects/{project_slug}/brief.md"

// Build brief content from current session context
// Gather: overview, tech stack, constraints, work notes, milestones, user decisions
// from conversation context and any existing brief content

IF vault.exists(brief_path):
    existing = vault.read(brief_path)
    ASK: "Brief exists. Merge (preserve existing, update changed sections) or overwrite?"
    IF merge:
        // Preserve existing sections, update scope + work notes from session
        merged = merge_briefs(existing, session_context)
        vault.write(brief_path, merged)
    ELSE:
        vault.write(brief_path, new_brief)
ELSE:
    // Read project_type from breadcrumb context or ask
    vault.write(brief_path, new_brief)

// Update brief frontmatter
vault.property_set(brief_path, "updated", TODAY)

// Rebuild indices
REBUILD projects/_index.md
RUN update_home()

REPORT: "Brief synced for '{project_slug}'."
```

#### handoff subform — Mirror remember.md → `_handoff.md`

Light integration with the `remember` plugin. See `references/remember-integration.md`.

```pseudocode
vault_path = read vault_path from breadcrumb
project_slug = read project_slug from breadcrumb
IF NOT project_slug: ERROR "No project linked."

remember_file = $CLAUDE_PROJECT_DIR/.remember/remember.md
IF NOT exists remember_file:
    ERROR "No .remember/remember.md found in project directory."

// Read remember content
content = read remember_file

// Build handoff file
handoff = """
---
type: handoff
project: "[[projects/{project_slug}/brief|{project_slug}]]"
updated: {TODAY}
source: remember
tags:
  - ob/handoff
---

# Handoff — {project_slug}

*Mirrored from `.remember/remember.md` on {TODAY}.*

---

{content}
"""

vault.write("projects/{project_slug}/_handoff.md", handoff)

REPORT: "Handoff synced for '{project_slug}'. Mirrored {line_count} lines from remember.md."
```

### /check — read-only

Status + handoff status + iterations listing, with optional sections.

Subforms:
- `/check` — full vault summary
- `/check handoff` — handoff section only
- `/check iterations [--all]` — iteration listing
- `/check decisions [--all]` — recent decisions
- `/check sessions` — recent sessions
- `/check tags` — tag taxonomy summary
- Multi-section: `/check iterations decisions` returns both

#### Full status (default `/check`)

```pseudocode
// Read breadcrumb
vault_path = read vault_path from breadcrumb
vault_name = read vault_name from breadcrumb
mode = read mode from breadcrumb

REPORT header: "Vault: {vault_name} at {vault_path}"
REPORT: "Transport: {mode}"
IF mode == "cli":
    cli_ver = run "obsidian version"
    REPORT: "CLI version: {cli_ver}"

// Schema version detection
has_v3 = any brief has project_type field
has_v2 = any brief lacks project_type field
IF has_v3 AND has_v2: version_note = "v3 (mixed — some v2 projects remain)"
ELIF has_v3: version_note = "v3"
ELSE: version_note = "v2"
REPORT: "Schema: {version_note}"

// Per-project inventory
FOR each project dir in {vault_path}/projects/:
    slug = dirname
    brief = read brief.md frontmatter
    status = brief.status
    project_type = brief.project_type OR "unknown"
    decisions = count files in decisions/
    sessions = count files in sessions/
    last_session = most recent session filename date
    REPORT row: "  {slug} — {project_type} — {status} — {decisions}d {sessions}s — last: {last_session}"

// Archive
FOR each dir in {vault_path}/archive/:
    REPORT: "  [archived] {dirname}"

// Cabinet detection
IF {vault_path}/crew/ exists:
    REPORT: "Cabinet: detected — crew/ folder present, untouched by bridge."

// Remember detection
IF $CLAUDE_PROJECT_DIR/.remember/ exists:
    IF _handoff.md exists for current project:
        handoff_date = read updated from _handoff.md frontmatter
        REPORT: "Remember: detected — last handoff sync: {handoff_date}"
    ELSE:
        REPORT: "Remember: detected — no handoff yet."

// Drift teaser (quick check)
issues = quick_scan_for_drift()  // briefs missing project_type, collections without _index, etc.
IF issues > 0:
    REPORT: "Drift: {issues} issues detected. Run /dream for details."
```

#### handoff subform — Show last sync time

```pseudocode
vault_path = read vault_path from breadcrumb
project_slug = read project_slug from breadcrumb

remember_file = $CLAUDE_PROJECT_DIR/.remember/remember.md
handoff_file = {vault_path}/projects/{project_slug}/_handoff.md

remember_exists = exists remember_file
handoff_exists = vault.exists("projects/{project_slug}/_handoff.md")

IF NOT remember_exists:
    REPORT: "No .remember/remember.md found."
    RETURN

IF handoff_exists:
    handoff_date = vault.property_read("projects/{project_slug}/_handoff.md", "updated")
    // Compare mtimes
    remember_mtime = file mtime of remember_file
    handoff_mtime = file mtime of handoff_file (resolved to filesystem path)
    IF remember_mtime > handoff_mtime:
        REPORT: "Handoff: stale. Last sync: {handoff_date}. remember.md updated since."
    ELSE:
        REPORT: "Handoff: current. Last sync: {handoff_date}."
ELSE:
    REPORT: "Handoff: never synced. Run /sync handoff."
```

#### iterations subform — List iterations grouped by track

```pseudocode
slug = user-provided slug OR read project_slug from breadcrumb
tree_flag = optional --tree flag
vault_path = read vault_path from breadcrumb

iter_dir = {vault_path}/projects/{slug}/iterations
IF NOT exists iter_dir: REPORT "No iterations for project '{slug}'." RETURN

// Collect all iterations
iterations = []
FOR each entry in iter_dir (excluding _index.md):
    IF entry is .md file:
        fm = read frontmatter
    ELIF entry is folder with _iteration.md:
        fm = read _iteration.md frontmatter
    ELSE: SKIP

    iterations.add({
        identifier: fm.identifier,
        status: fm.status,
        date: fm.date,
        track: fm.track OR "Loose",
        register: fm.register,
        supersedes: fm.supersedes,
        builds_on: fm.builds_on,
        filename: entry name
    })

// Group by track
tracks = group iterations by track
sort tracks by most recent iteration date (descending)

FOR each track:
    REPORT: "## Track: {track_name}"
    FOR each iteration in track (sorted by date):
        status_badge = iteration.status
        REPORT: "  [{iteration.identifier}] {iteration.filename} — {status_badge}"
        IF iteration.register:
            REPORT: "      {iteration.register}"

IF tree_flag:
    // Show lineage tree
    REPORT: "\n## Lineage"
    FOR each iteration with supersedes or builds_on:
        REPORT: "  {identifier} → supersedes {target}" or "  {identifier} ← builds on {ancestor}"
```

### /ramasse — tidy

Combined reindex + housekeeping. Subforms:
- `/ramasse` — full sweep (both)
- `/ramasse --dry-run` — show what would change without writing
- `/ramasse indexes` — reindex only
- `/ramasse housekeeping` — consistency check only

The full sweep runs the `indexes` subform followed by the `housekeeping` subform.

#### indexes subform — Rebuild all `_index.md` files from disk

```pseudocode
vault_path = read vault_path from breadcrumb

// 1. Rebuild projects/_index.md
projects = list dirs in {vault_path}/projects/
FOR each project:
    read brief frontmatter (slug, status, project_type, created, updated)
    count decisions, sessions
    find latest session date
WRITE projects/_index.md with table rows

// 2. Rebuild per-project collection indices
FOR each project dir:
    FOR each subfolder that is a collection (has ≥2 .md siblings, not sessions/images/assets/):
        IF _index.md missing:
            CREATE from collection-index template
        REBUILD _index.md entries from folder contents
            sort chronologically if filenames have dates, else alphabetically

// 3. Rebuild iterations/_index.md (if exists)
FOR each project with iterations/:
    group iterations by track (from frontmatter)
    sort by date within track
    WRITE iterations/_index.md with track grouping and status badges

// 4. Rebuild Home.md
RUN update_home()

// 5. Report
REPORT: "Reindexed {N} projects, rebuilt {M} _index.md files."
```

#### housekeeping subform — Full consistency check

Runs all structural checks from the housekeeping checklist. Auto-fixes safe items, reports manual items.

```pseudocode
vault_path = read vault_path from breadcrumb
project_slug = read project_slug from breadcrumb

// Scope: current project if linked, otherwise vault-wide
IF project_slug:
    scope = [project_slug]
ELSE:
    scope = list all project slugs

auto_fixes = []
manual_items = []

FOR each slug in scope:
    project_dir = {vault_path}/projects/{slug}

    // 1. Empty project folder
    IF project_dir has no .md files and no subfolders:
        manual_items.add("Empty project folder: {slug} — archive or delete?")

    // 2. Missing brief.md
    IF NOT exists brief.md:
        auto_fixes.add("Missing brief.md for {slug} — scaffold from template")
        ACTION: scaffold brief from type template (ask type if unknown)

    // 3. Slug shape violation
    IF slug contains dots, spaces, or uppercase:
        manual_items.add("Slug '{slug}' violates naming rules — rename?")

    // 4. Collection folders missing _index.md
    FOR each subfolder with ≥2 .md siblings (excluding sessions/, images/, assets/):
        IF NOT exists _index.md:
            auto_fixes.add("Missing _index.md in {slug}/{folder}")
            ACTION: create from collection-index template

    // 5. _index.md out of sync
    FOR each _index.md:
        expected_entries = list .md siblings
        actual_entries = parse _index.md links
        IF mismatch:
            auto_fixes.add("_index.md out of sync in {slug}/{folder}")
            ACTION: rebuild from disk

    // 6. Files missing frontmatter
    FOR each .md file (excluding .obsidian/, templates/):
        IF no YAML frontmatter:
            auto_fixes.add("Missing frontmatter: {file}")
            ACTION: add minimal valid frontmatter based on location

    // 7. Malformed/incomplete frontmatter
    FOR each .md file with frontmatter:
        IF missing required fields for its type:
            auto_fixes.add("Incomplete frontmatter: {file} — missing {fields}")
            ACTION: add missing required fields with defaults

    // 8. Broken wikilinks
    FOR each wikilink [[target]] in all files:
        IF target not resolvable:
            manual_items.add("Broken wikilink [[{target}]] in {file}")

    // 9. Markdown-style links
    FOR each [text](path) in vault files:
        auto_fixes.add("Markdown link in {file} — convert to wikilink")
        ACTION: replace with [[equivalent]]

    // 10. Tag clutter
    all_tags = collect all tags across scope
    FOR tag with usage_count == 1:
        manual_items.add("Single-use tag #{tag} in {file}")
    FOR near-duplicates (e.g. #postgres vs #postgresql):
        manual_items.add("Near-duplicate tags: #{a} vs #{b}")

    // 11. Stale updated date
    IF status == "active" AND updated > 90 days ago:
        manual_items.add("Stale project '{slug}' — last updated {updated}")

    // 12. Decision filename pattern
    FOR each file in decisions/:
        IF NOT matches YYYY-MM-DD-{kebab}.md:
            auto_fixes.add("Decision filename violation: {file}")
            ACTION: rename to correct pattern

    // 13. Session filename pattern
    FOR each file in sessions/:
        IF NOT matches YYYY-MM-DD.md:
            auto_fixes.add("Session filename violation: {file}")
            ACTION: rename or merge same-day

    // 14. Root docs missing type: doc
    FOR each .md in project root (not brief.md, not _handoff.md, not _index.md):
        IF NOT has type: doc in frontmatter:
            auto_fixes.add("Root doc missing type: doc — {file}")
            ACTION: add type: doc frontmatter

    // 15. Brief body missing required blocks for type
    project_type = read from brief frontmatter
    required_blocks = get_required_blocks(project_type)
    existing_blocks = parse ## headers from brief body
    FOR each missing block:
        auto_fixes.add("Brief missing block: ## {block} for type {project_type}")
        ACTION: add empty block with placeholder

    // 16. relations references unknown slugs
    relations = vault.property_read(brief_path, "relations")
    IF relations:
        FOR field IN [parents, children, related]:
            FOR slug IN relations[field]:
                IF NOT vault.exists("projects/{slug}/brief.md")
                   AND NOT vault.exists("archive/{slug}/brief.md"):
                    manual_items.add("relations.{field} in {brief_path} references unknown slug '{slug}'")

// Report
REPORT:
    "## Auto-fixable ({count})"
    list auto_fixes
    "[Fix all] [Pick] [Skip]"
    ""
    "## Needs decision ({count})"
    list manual_items

// If user chooses "Fix all": run all auto_fixes sequentially
// If "Pick": present each, user approves/skips
// If "Skip": done
```

### /draw — list visual artefacts

The `/draw` command in `commands/draw.md` has subverbs (`canvas`, `base`, `diagram`) that route to the `canvas`, `bases`, and `mermaid` skills directly. The bare `/draw` form (no subverb) lists visual artefacts in the current project — that flow lives here.

Subforms (other than bare):
- `/draw canvas <name>` → handled by `obsidian-bridge:canvas` skill (this skill is not invoked)
- `/draw base <name>` → handled by `obsidian-bridge:bases` skill
- `/draw diagram [type]` → handled by `obsidian-bridge:mermaid` skill

Bare `/draw` (this skill's `draw-list` flow):

```pseudocode
breadcrumb = read $CLAUDE_PROJECT_DIR/.claude/obsidian-bridge
IF NOT breadcrumb: ERROR "No vault connected. Run /connect first."

vault_path = read vault_path from breadcrumb
project_slug = read project_slug from breadcrumb
IF NOT project_slug: scope = "vault-wide" ELSE: scope = "project: {project_slug}"

// Discover artefacts
IF project_slug:
    project_dir = {vault_path}/projects/{project_slug}
    canvases = glob {project_dir}/**/*.canvas
    bases = glob {project_dir}/**/*.base
    diagrams = grep -lE '^```mermaid' {project_dir}/**/*.md
ELSE:
    canvases = glob {vault_path}/**/*.canvas (excluding archive/)
    bases = glob {vault_path}/**/*.base (excluding archive/)
    diagrams = grep -lE '^```mermaid' {vault_path}/**/*.md (excluding archive/)

// Render summary
REPORT: "Visual artefacts ({scope}):"
IF canvases.length > 0:
    REPORT: "  Canvases ({canvases.length}):"
    FOR c IN canvases (sort by mtime desc, top 10):
        REPORT: "    - {c.path} ({c.mtime})"
ELSE:
    REPORT: "  Canvases: none"

IF bases.length > 0:
    REPORT: "  Bases ({bases.length}):"
    FOR b IN bases:
        REPORT: "    - {b.path}"
ELSE:
    REPORT: "  Bases: none"

IF diagrams.length > 0:
    REPORT: "  Notes containing mermaid blocks ({diagrams.length}):"
    FOR d IN diagrams (sort by mtime desc, top 10):
        REPORT: "    - {d.path}"
ELSE:
    REPORT: "  Mermaid blocks: none"

REPORT: "(Use `/draw canvas|base|diagram <name>` to create. See obsidian-bridge:canvas / :bases / :mermaid skills for syntax.)"
```

### /iterate — state transitions

Set the status of an iteration. Replaces `iteration-set-status`.

> **Note on `/iterate`:** This command exists for mechanical state-machine reliability. Iteration creation and listing are conversational (e.g. "new iteration D for foo on navy track", "show on-shelf iterations"). If conversational handling of state transitions proves robust across model versions, /iterate may be sunset in a future release.

Subforms:
- `/iterate <id> <status>` — set in current project
- `/iterate <slug>:<id> <status>` — explicit project slug

Valid statuses: `drafting`, `on-shelf`, `picked`, `parked`, `rejected`, `superseded`.

```pseudocode
iter_id = user-provided identifier
new_status = validate(user-provided status)
    // drafting | on-shelf | picked | parked | rejected | superseded

vault_path = read vault_path from breadcrumb
project_slug = read project_slug from breadcrumb
iter_dir = {vault_path}/projects/{project_slug}/iterations

// Find iteration
iter_file = find iteration file by identifier (same logic as add-iteration-artefact)
IF NOT found: ERROR "Iteration '{iter_id}' not found."

// Set status
vault.property_set(iter_file, "status", new_status)

// If "picked": offer to mark same-track siblings as "superseded"
IF new_status == "picked":
    track = vault.property_read(iter_file, "track")
    IF track:
        siblings = find other iterations with same track AND status NOT IN [rejected, superseded]
        IF siblings.length > 0:
            ASK: "Mark {siblings.length} sibling(s) on track '{track}' as superseded?"
            IF yes:
                FOR each sibling:
                    vault.property_set(sibling.file, "status", "superseded")

// Rebuild _index.md
REBUILD iterations/_index.md

REPORT: "Iteration {iter_id} status set to {new_status}."
```

---

## Conversational operations

These operations don't have a slash-command in the new surface, but the vault-bridge skill still handles them — the model invokes the underlying logic when the user describes the intent in natural language.

### add-collection (formerly /vault-bridge add-collection)

Trigger: "add a tasks/ folder to foo", "scaffold a notes/ collection in bar"

```pseudocode
name = validate_slug(user-provided name)  // kebab-case

// Read breadcrumb
vault_path = read vault_path from breadcrumb
project_slug = read project_slug from breadcrumb
IF NOT project_slug: ERROR "No project linked. Run /connect --link-only <slug> first."

collection_dir = {vault_path}/projects/{project_slug}/{name}
IF exists collection_dir: ERROR "Collection '{name}' already exists."

mkdir {collection_dir}
vault.write("projects/{project_slug}/{name}/_index.md", collection_index(project_slug, name))

REPORT: "Collection '{name}' added to project '{project_slug}' with _index.md."
```

### archive / unarchive (formerly /vault-bridge archive | unarchive)

Trigger: "archive foo", "restore bar from archive"

```pseudocode
// archive
slug = user-provided slug OR read project_slug from breadcrumb
vault_path = read vault_path from breadcrumb

IF NOT exists {vault_path}/projects/{slug}/:
    ERROR "Project '{slug}' not found in projects/."

// Update brief status
vault.property_set("projects/{slug}/brief.md", "status", "archived")
vault.property_set("projects/{slug}/brief.md", "updated", TODAY)

// Move the folder
vault.move("projects/{slug}", "archive/{slug}")

// Rebuild indices
REBUILD projects/_index.md
RUN update_home()

// If current breadcrumb points to this slug, clear it
IF breadcrumb project_slug == slug:
    UPDATE breadcrumb: project_slug=

REPORT: "Project '{slug}' archived."


// unarchive
slug = user-provided slug
vault_path = read vault_path from breadcrumb

IF NOT exists {vault_path}/archive/{slug}/:
    ERROR "Project '{slug}' not found in archive/."

// Update brief status
vault.property_set("archive/{slug}/brief.md", "status", "active")
vault.property_set("archive/{slug}/brief.md", "updated", TODAY)

// Move back
vault.move("archive/{slug}", "projects/{slug}")

// Rebuild indices
REBUILD projects/_index.md
RUN update_home()

REPORT: "Project '{slug}' restored to active."
```

### set-type (formerly /vault-bridge set-type)

Trigger: "change foo to plugin type", "set baz's project_type to knowledge"

```pseudocode
slug = user-provided slug
new_type = validate_type(user-provided type)
vault_path = read vault_path from breadcrumb

brief_path = "projects/{slug}/brief.md"
IF NOT vault.exists(brief_path): ERROR "Project '{slug}' not found."

old_type = vault.property_read(brief_path, "project_type")

// Update frontmatter
vault.property_set(brief_path, "project_type", new_type)
vault.property_set(brief_path, "updated", TODAY)

// Update tags: remove old type tag, add new
// Read tags, replace type/{old_type} with type/{new_type}
tags = vault.property_read(brief_path, "tags")
tags = replace "type/{old_type}" with "type/{new_type}" in tags
vault.property_set(brief_path, "tags", tags)

// Scaffold new type-specific folders if missing
MATCH new_type:
    // Same logic as create-project folder scaffolding
    // Only create folders that don't already exist
    // Create _index.md for new collection folders

REPORT: "Project '{slug}' type changed from {old_type} to {new_type}. New folders scaffolded if needed."
```

### templates (formerly /vault-bridge templates)

Trigger: "show me the brief template for coding", "list available templates"

```pseudocode
IF subcommand == "list" OR no subcommand:
    FOR each .md file in examples/vault-templates/:
        name = filename without .md
        type = read type from frontmatter
        REPORT: "  {name} — type: {type}"

IF subcommand == "print" AND template_name provided:
    path = examples/vault-templates/{template_name}.md
    IF NOT exists path:
        path = examples/vault-templates/{template_name}  // try with extension
    IF NOT exists path:
        ERROR "Template '{template_name}' not found."
    content = read path
    REPORT: content
```

### add-iteration / add-iteration-artefact (formerly /vault-bridge add-iteration*)

Iterations are a first-class collection type. Canonical folder: `projects/{slug}/iterations/`. Opt-in for all project types — not auto-created on project scaffold. See `obsidian-bridge:vault-standards` for the iteration schema.

Trigger: "new iteration D for foo on navy track", "attach concept.png to iter D"

```pseudocode
// add-iteration
identifier = user-provided id (letter, number, or short word)
iter_slug = validate_slug(user-provided slug)
track = optional --track flag
with_folder = optional --with-folder flag

vault_path = read vault_path from breadcrumb
project_slug = read project_slug from breadcrumb
IF NOT project_slug: ERROR "No project linked."

iter_dir = {vault_path}/projects/{project_slug}/iterations

// Create iterations/ folder if first iteration
IF NOT exists iter_dir:
    mkdir iter_dir
    vault.write("projects/{project_slug}/iterations/_index.md",
        iterations_index(project_slug))

// Build filename
date = TODAY
filename = "{date}-iter-{identifier}-{iter_slug}"

IF with_folder:
    // Folder form
    mkdir {iter_dir}/{filename}
    vault.write("projects/{project_slug}/iterations/{filename}/_iteration.md",
        iteration_template(project_slug, identifier, date, track))
ELSE:
    // File form
    vault.write("projects/{project_slug}/iterations/{filename}.md",
        iteration_template(project_slug, identifier, date, track))

// Add ## ITERATIONS block to brief if not present
brief_content = vault.read("projects/{project_slug}/brief.md")
IF NOT contains "## ITERATIONS":
    APPEND to brief before last section or at end:
        "\n## ITERATIONS\n\nSee [[projects/{project_slug}/iterations/_index|iterations]].\n"

// Rebuild iterations/_index.md
REBUILD iterations/_index.md from disk (grouped by track, sorted by date)

REPORT: "Iteration {identifier} created: {filename}"


FUNCTION iteration_template(slug, identifier, date, track):
    frontmatter = {
        type: iteration,
        project: "[[projects/{slug}/brief|{slug}]]",
        identifier: identifier,
        status: drafting,
        date: date,
        tags: [ob/iteration]
    }
    IF track:
        frontmatter.track = track
    RETURN: frontmatter + "\n# Iteration {identifier}\n"


FUNCTION iterations_index(slug):
    RETURN collection_index template with:
        project: "[[projects/{slug}/brief|{slug}]]"
        title: "Iterations — {slug}"
        description: "Design and code iterations grouped by track."


// add-iteration-artefact
iter_id = user-provided iteration identifier (matches identifier field)
file = user-provided file path (absolute or relative to CWD)

vault_path = read vault_path from breadcrumb
project_slug = read project_slug from breadcrumb
iter_dir = {vault_path}/projects/{project_slug}/iterations

// Find the iteration by identifier
found = null
FOR each entry in iter_dir:
    IF entry name contains "-iter-{iter_id}-":
        found = entry
        BREAK
IF NOT found: ERROR "Iteration '{iter_id}' not found."

// If file form (.md), promote to folder form
IF found is a .md file:
    folder_name = found without .md extension
    mkdir {iter_dir}/{folder_name}
    // Rename the .md to _iteration.md inside the new folder
    vault.move("projects/{project_slug}/iterations/{found}",
               "projects/{project_slug}/iterations/{folder_name}/_iteration.md")
    found = folder_name  // now a folder

// Copy artefact into iteration folder
artefact_name = basename(file)
cp {file} to {iter_dir}/{found}/{artefact_name}

// Update frontmatter artefacts list
iter_file = "projects/{project_slug}/iterations/{found}/_iteration.md"
existing_artefacts = vault.property_read(iter_file, "artefacts") OR []
existing_artefacts.add(artefact_name)
vault.property_set(iter_file, "artefacts", existing_artefacts)

// Rebuild _index.md
REBUILD iterations/_index.md

REPORT: "Artefact '{artefact_name}' added to iteration {iter_id}. Promoted to folder form."
```

### migrate (v2 → v3 schema, formerly /vault-bridge migrate)

Trigger: "migrate this vault to v3"

Stays in `## Migration` section below (kept conversational because it's rare and deliberate).

---

## Migration

Anchor migration is now silent and automatic — handled by SessionStart hook step 0.

### migrate — v2 → v3 walkthrough

Conversational invocation only — no /migrate command. One-shot opt-in operation. Idempotent — re-running on a v3 vault effectively becomes housekeeping. See spec §16 for full detail.

```pseudocode
vault_path = read vault_path from breadcrumb

// 1. Confirm scope
projects = list dirs in {vault_path}/projects/
archived = list dirs in {vault_path}/archive/
total_files = count all .md files in vault
REPORT: "Migration scope: {projects.length} projects, {archived.length} archived, {total_files} files."
REPORT: "This will: add project_type to briefs, reformat brief bodies to v3 blocks, add _index.md to collections, normalise tags."
ASK: "Proceed? (A backup will be created first.)"
IF NOT proceed: RETURN

// 2. Backup
backup_dir = {vault_path}/.backup-v2-{TODAY}
cp -r {vault_path}/projects {backup_dir}/projects
cp -r {vault_path}/archive {backup_dir}/archive 2>/dev/null || true
cp {vault_path}/Home.md {backup_dir}/Home.md
REPORT: "Backup created at {backup_dir}. Delete after verifying migration."

// 3. Migrate each project
FOR each project in projects + archived:
    slug = dirname
    brief_path = resolve brief.md path (projects/ or archive/)

    // a. Detect project_type if not set
    existing_type = vault.property_read(brief_path, "project_type")
    IF NOT existing_type:
        // Heuristic defaults
        IF exists decisions/ under project: suggested = "coding"
        ELIF exists sources/ under project: suggested = "knowledge"
        ELIF exists releases/ under project: suggested = "plugin"
        ELSE: suggested = "tinkerage"

        ASK: "Project '{slug}' — assign type? Suggested: {suggested}. Options: coding, knowledge, plugin, tinkerage."
        project_type = user response OR suggested
        vault.property_set(brief_path, "project_type", project_type)
    ELSE:
        project_type = existing_type

    // b. Add aliases if missing
    aliases = vault.property_read(brief_path, "aliases")
    IF NOT aliases OR aliases is empty:
        vault.property_set(brief_path, "aliases", [slug])

    // c. Normalise tags: keep cabinet/*, add ob/*, add type/*
    tags = vault.property_read(brief_path, "tags")
    IF NOT contains "ob/project": tags.add("ob/project")
    IF NOT contains "type/{project_type}": tags.add("type/{project_type}")
    vault.property_set(brief_path, "tags", tags)

    // d. Ensure slug field
    IF NOT vault.property_read(brief_path, "slug"):
        vault.property_set(brief_path, "slug", slug)

    // e. Brief body reformat
    body = read brief body (after frontmatter)
    reformatted = reformat_brief_body(body, project_type)
    IF reformatted != body:
        write reformatted body back

    // f. Slug repair
    IF slug contains dots, spaces, or uppercase:
        suggested_slug = slugify(slug)
        ASK: "Rename '{slug}' → '{suggested_slug}'?"
        IF yes:
            vault.move("projects/{slug}", "projects/{suggested_slug}")
            slug = suggested_slug


// 4. Backfill _index.md
FOR each project:
    FOR each collection folder (≥2 .md siblings, not sessions/images/assets/):
        IF NOT exists _index.md:
            CREATE from collection-index template
        REBUILD _index.md from folder contents

// 5. Emergent iteration folders
FOR each project:
    FOR folder_name IN [design-iterations, surfaces, aesthetics]:
        IF exists {project_dir}/{folder_name}/:
            ASK: "Canonicalise '{folder_name}/' → 'iterations/' for project '{slug}'?"
            IF yes:
                vault.move("projects/{slug}/{folder_name}", "projects/{slug}/iterations")
                // Update frontmatter in moved files
                FOR each .md in iterations/:
                    IF type == "design-iteration":
                        vault.property_set(file, "type", "iteration")
                    tags = read tags
                    IF "cabinet/design-iteration" in tags:
                        tags.add("ob/iteration")
                    vault.property_set(file, "tags", tags)
                    // Preserve register, identifier, status, etc.
                CREATE iterations/_index.md (rebuild from disk)
            ELSE:
                // Leave as user-defined collection
                IF NOT exists _index.md:
                    CREATE _index.md for it

// 6. Root-level singleton docs
FOR each project:
    FOR each .md in project root (not brief.md, not _handoff.md, not _index.md):
        IF NOT has type: doc frontmatter:
            ADD type: doc frontmatter (preserve body)

// 7. Update Home.md frontmatter
home = read Home.md
IF type == "cabinet-home":
    IF {vault_path}/crew/ exists:
        SET type to [vault-home, cabinet-home]
    ELSE:
        SET type to vault-home
RUN update_home()

// 8. Run housekeeping
RUN housekeeping (auto-fix all safe items)

// 9. Report
changes = count all changes made
REPORT: "Migration complete. Changed {changes} files. Backup at {backup_dir}."
REPORT: "Review the changes, then delete {backup_dir} when satisfied."


FUNCTION reformat_brief_body(body, project_type):
    // v2 → v3 section mapping for coding type:
    //   ## Overview      → ## INTRO
    //   ## Tech Stack    → ## TECHNICAL STACK
    //   ## Scope         → split: ## CONSTRAINTS + ## USER DECISIONS
    //   ## Conventions   → append to ## TECHNICAL STACK or ## CONSTRAINTS
    //   ## Team Notes    → ## WORK NOTES
    //   anything else    → ## WORK NOTES
    //
    // Similar mappings for other types (knowledge, plugin, tinkerage)
    // All content preserved verbatim under best-fit headers.
    // Empty required blocks added with "TBD" placeholder.

    required_blocks = get_blocks_for_type(project_type)
    mapped_body = map_sections(body, project_type)

    FOR each required block NOT present in mapped_body:
        APPEND "## {BLOCK}\n\nTBD\n"

    RETURN mapped_body
```
