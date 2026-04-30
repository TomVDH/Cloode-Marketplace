> **STALE.** Superseded by `obsidian-bridge/references/vault-integration.md`. Cabinet refactor pending.

# Vault Integration

Loaded at boot. The cabinet detects vault availability during startup (step 1.6). As of v2.2 a connected vault is required — see the Vault Requirement section below.

---

## Vault Requirement (v2.2)

The Cabinet of IMD requires a connected vault to operate. This is a hard requirement — there is no local-filesystem fallback for session state, chatter, or memories. Without a vault:

- `/cabinet` aborts boot and points the user at `/vault-bridge`
- Specialist skills invoked via `/invoke` operate ephemerally for the duration of the call and do not attempt anchor I/O
- Chatter, decisions, preferences, and lessons are not captured

Rationale: the plugin's value proposition is cross-session persistence. A vault-less "degraded mode" created confusing expectations and ghost session state. v2.2 removes the fallback entirely.

---

## What the Vault Provides

The vault serves as the cabinet's **long-term memory** — persistent knowledge that survives across sessions, projects, and context compactions. The session anchor is today's save file. The vault is everything the crew has ever learned.

Four surfaces:

1. **Project briefs** — goals, constraints, tech stack, stakeholders. Pulled at startup so the crew starts informed.
2. **Decision log** — architecture choices, trade-offs, scope decisions. Written at gate completions. Queryable in future sessions via wikilinks and Dataview.
3. **Session history** — what happened each day. Written at wrap-up. Linked to projects and decisions.
4. **Crew preferences** — Tom's known preferences, project conventions, lessons learned. Accumulates over time.

---

## Vault Structure (v2 — Project-Scoped)

Each project owns its decisions and sessions inside a subfolder. Cross-project knowledge (crew/, templates/) stays at the root. This scales cleanly: new project = new subfolder, archive = move folder.

```
Claude Cabinet/
├── .obsidian/
├── Home.md                        ← auto-maintained landing page
├── crew/
│   ├── preferences.md             ← global preferences
│   └── lessons-learned.md         ← tagged per project where relevant
├── projects/
│   ├── _index.md                  ← MOC: all projects table
│   └── {project-slug}/
│       ├── brief.md               ← project brief
│       ├── decisions/
│       │   ├── _index.md          ← MOC: this project's decisions
│       │   └── {date}-{slug}.md
│       ├── sessions/
│       │   └── {date}.md          ← just date — project is the folder
│       └── images/                ← screenshots captured via Playwright (see vault-images.md)
├── archive/                       ← same structure, completed/shelved projects
│   └── {project-slug}/
└── templates/
    ├── project-brief.md
    ├── decision.md
    └── session-summary.md
```

### v1 → v2 Differences

| Aspect | v1 (flat) | v2 (project-scoped) |
|--------|-----------|---------------------|
| Brief location | `projects/{slug}.md` | `projects/{slug}/brief.md` |
| Decision location | `decisions/{date}-{slug}.md` | `projects/{slug}/decisions/{date}-{slug}.md` |
| Session location | `sessions/{date}-{slug}.md` | `projects/{slug}/sessions/{date}.md` |
| Session filename | `YYYY-MM-DD-{project}.md` | `YYYY-MM-DD.md` (project is the folder) |
| Decision MOC | `decisions/_index.md` (global) | `projects/{slug}/decisions/_index.md` (per-project) |
| Archive | None | `archive/{slug}/` |
| Version field | Not set | `anchor.vault.version = "2.0"` |

The `/vault-bridge migrate` command converts v1 → v2 non-destructively. See `vault-bridge/SKILL.md`.

---

## CLI-First Policy

**The cabinet heavily favours the Obsidian CLI wherever it is available, efficient, or relevant.** This is not just a transport fallback — it is the preferred interface for all vault operations when Obsidian is running and the CLI is on PATH.

```pseudocode
// Decision rule — applies to every vault operation:
IF cli_available() AND operation is supported by CLI:
    USE cli_call()      // always preferred
ELSE:
    USE filesystem_call()  // fallback only
```

**Why CLI-first:**
- Wikilinks in frontmatter are recognised natively by Obsidian's parser (not just written as text)
- `property:set` writes frontmatter without re-parsing the whole file
- `move` and `rename` trigger Obsidian's automatic internal link updater
- `search` and `search:context` use Obsidian's index — faster and vault-aware
- `backlinks` and `tags` return live graph data, not grep approximations
- No manual YAML parsing, no fragile regex, no accidental frontmatter corruption

**CLI-first extends beyond vault ops** — the crew applies the same principle in any context where a canonical CLI tool is available. Use the official tool before reaching for a filesystem workaround or custom script.

---

## Vault Modes

The cabinet accesses the vault through two transport modes, detected automatically at boot. Both modes produce identical outcomes — same files, same structure, same Obsidian-native content. The mode determines *how* the cabinet talks to the vault, not *what* it does.

### Mode A: Obsidian CLI (Primary — Claude Code / Terminal)

Uses the **official Obsidian CLI** (`obsidian` command). Available when Claude runs natively on the host machine (Claude Code, terminal) and Obsidian 1.12+ is installed with CLI enabled.

**Requirements:**
- Obsidian 1.12+ with CLI enabled (Settings → General → Command line interface)
- Obsidian app must be running
- The `obsidian` command must be on PATH

**Advantages over file access:**
- First-party — no community plugin dependencies
- Native property (frontmatter) read/write without YAML parsing
- Vault search with context (line-level matches)
- Backlink and tag queries
- Wikilink-style file resolution (`file=name` without full path)
- Automatic internal link updates on move/rename
- No API keys, no ports, no HTTP overhead

**Vault targeting:** Use `vault="Claude Cabinet"` (or the vault name) as the first parameter if the terminal's working directory is not inside the vault.

### Mode B: Filesystem (Fallback — Cowork / Mounted Directory)

Direct file access when the vault directory is mounted or accessible. This is the fallback when the CLI is unavailable — typically in Cowork sessions (where the VM can't reach the host's Obsidian), or when Obsidian is closed.

**Requirements:**
- Vault directory is mounted or on a reachable path

### Layout Modes (Orthogonal to Transport)

Transport mode (CLI vs filesystem) is independent of layout mode:

**Dedicated Vault (Recommended):** The entire vault belongs to the cabinet. Content lives at the root. Detected when: vault root contains `Home.md` with `type: cabinet-home`, or a `projects/` folder.

**Subfolder Mode (Shared Vault):** The cabinet lives inside `_cabinet/` in an existing vault. Same structure, just nested. Detected when: `_cabinet/` exists in a mounted directory.

### Base Path Resolution

```pseudocode
IF vault.layout == "dedicated":
    base = vault_path
ELSE IF vault.layout == "subfolder":
    base = vault_path + "/_cabinet"
```

For CLI mode, `base` is used to construct `path=` parameters. For filesystem mode, `base` is the absolute directory path.

### v2 Path Resolution

```pseudocode
project_base(slug)  = {base}/projects/{slug}/
brief_path(slug)    = {base}/projects/{slug}/brief.md
decision_dir(slug)  = {base}/projects/{slug}/decisions/
session_dir(slug)   = {base}/projects/{slug}/sessions/
archive_base(slug)  = {base}/archive/{slug}/
crew_path()         = {base}/crew/
```

All path references below use these functions. The cabinet resolves `base` once at connection time and stores it in the anchor as `vault.base_path`.

---

## Obsidian Conventions

The cabinet writes notes that are **Obsidian-native** — wikilinks, YAML frontmatter, tags, and Dataview-compatible metadata.

### Frontmatter Schema

Every note gets YAML frontmatter. This is the contract — Dataview queries and templates depend on these fields.

**Canonical schemas for all file types are defined in `vault-standards.md`.** That file is the single source of truth for frontmatter fields, required vs optional status, value formats, and naming conventions. Templates in `examples/vault-templates/` mirror those definitions.

Key rules (see `vault-standards.md` for full details):
- Project references use piped wikilinks: `project: "[[projects/{slug}/brief|{slug}]]"`
- Specialist names are always lowercase: `specialist: bostrol`
- Structural tags use the `cabinet/` namespace: `cabinet/decision`, `cabinet/session`
- Topic tags are bare: `architecture`, `email`, `cleanup`
- Empty optional fields are omitted, not set to null

> **Why aliases on briefs?** In v2, briefs live at `projects/{slug}/brief.md` — so `[[dashboard-v2]]` wouldn't resolve without an alias. The `aliases` field tells Obsidian to treat this file as the target for `[[dashboard-v2]]` wikilinks.

### Wikilink Rules

1. **Projects are hubs.** Decisions and sessions link TO their project via `[[project-slug]]` in frontmatter and body. Projects link OUT to key decisions.
2. **Decisions interlink.** Supersedes/builds-on links: `Supersedes [[2026-03-15-session-auth]]`.
3. **Sessions are daily snapshots.** Link to project and decisions made that day.
4. **Preferences and lessons are leaf nodes** — other notes link to them, they don't link out.

**Link format:** Always `[[note-name]]` (wikilink), not `[text](path)`. Use `[[name|Display Text]]` when slugs are ugly.

### Tag Taxonomy

All under `#cabinet/` namespace.

**Structural:** `#cabinet/project`, `#cabinet/decision`, `#cabinet/session`, `#cabinet/crew`, `#cabinet/moc`

**Domain:** `#cabinet/frontend` (Thieuke), `#cabinet/backend` (Sakke), `#cabinet/integration` (Jonasty), `#cabinet/fullstack` (Pitr), `#cabinet/creative` (Henske), `#cabinet/docs` (Bostrol), `#cabinet/ops` (Kevijntje), `#cabinet/ux` (Poekie)

### Maps of Content (MOCs)

Two levels of MOC in v2:

**`projects/_index.md`** — Master index. All active projects with status, decision count, session count, last session.

**`projects/{slug}/decisions/_index.md`** — Per-project. All decisions for that project with specialist, date, status.

MOCs are rewritten (not appended) by `update_home()` and `reindex`.

### Home Note

`Home.md` is rebuilt by `update_home()` from disk state. Gathers across all project folders:

- Active projects (from `projects/*/brief.md` frontmatter)
- Recent decisions (last 5 across all `projects/*/decisions/`)
- Recent sessions (last 5 across all `projects/*/sessions/`)
- Archived projects (from `archive/`)

### Naming Rules

- **Project slugs:** lowercase, hyphens, no spaces. E.g. `dff2026-web`, `dashboard-v2`.
- **Decision filenames:** `YYYY-MM-DD-{descriptive-slug}.md` inside `projects/{slug}/decisions/`.
- **Session filenames:** `YYYY-MM-DD.md` inside `projects/{slug}/sessions/`. One per day per project. Second session same day appends to existing file.
- **No Obsidian-specific syntax in body** except wikilinks and tags.

---

## Vault Discovery — How the Cabinet Finds It

The cabinet checks for a vault during startup step 1.6. This is the **single source of truth** for vault detection — same logic referenced by `cabinet/SKILL.md` and `specialist-contract.md`.

### Discovery Chain

```pseudocode
// 1. Anchor has a vault from a previous session (fast path)
IF anchor exists AND anchor.vault AND anchor.vault.base_path:
    IF anchor.vault.mode == "cli":
        IF cli_available():  // see CLI Detection below
            vault = { mode: "cli", layout: anchor.vault.layout,
                      base: anchor.vault.base_path, vault_name: anchor.vault.vault_name,
                      available: true }
        ELSE:
            // CLI gone (Obsidian closed?) — try filesystem fallback
            IF directory_exists(anchor.vault.base_path):
                vault = { mode: "filesystem", layout: anchor.vault.layout,
                          base: anchor.vault.base_path, available: true }
            ELSE:
                PROCEED to step 2
    ELSE IF anchor.vault.mode == "filesystem":
        IF directory_exists(anchor.vault.base_path):
            vault = { mode: "filesystem", layout: anchor.vault.layout,
                      base: anchor.vault.base_path, available: true }
        ELSE:
            PROCEED to step 2

// 2. Try CLI detection (terminal/Code environments only)
IF NOT cowork_detected:
    IF cli_available():
        // CLI is available — detect vault name and path
        vault_name = detect_vault_name()  // see below
        IF vault_name:
            vault = { mode: "cli", vault_name, available: true }
            // Layout and base_path resolved after first read
            SKIP to "After Discovery"

// 3. Scan mounted/accessible directories for filesystem mode
scan_paths = []
IF cowork_detected:
    scan_paths += [mounted_directories]
IF terminal_detected:
    scan_paths += [pwd, git_root]
scan_paths.append(expand("~/vaults/cabinet"))

FOR path IN scan_paths:
    IF file_exists(path + "/Home.md") AND contains "type: cabinet-home":
        vault = { mode: "filesystem", layout: "dedicated", base: path, available: true }
        BREAK
    ELSE IF directory_exists(path + "/projects"):
        vault = { mode: "filesystem", layout: "dedicated", base: path, available: true }
        BREAK
    ELSE IF directory_exists(path + "/_cabinet"):
        vault = { mode: "filesystem", layout: "subfolder",
                  base: path + "/_cabinet", available: true }
        BREAK

// 4. No vault found — offer directory picker in Cowork, silent skip elsewhere
IF NOT vault.available:
    IF cowork_detected AND tool_available("request_cowork_directory"):
        // One-time gentle ask — Kevijntje voice, not a system warning
        ASK Tom: "Geen vault gevonden in je gemounte mappen.
                  Wil je me naar je Obsidian vault wijzen?
                  (Sla over als je er geen gebruikt.)"
        IF Tom provides a directory:
            // Re-run step 3 scan logic against the user-provided path
            path = user_provided_directory
            IF file_exists(path + "/Home.md") AND contains "type: cabinet-home":
                vault = { mode: "filesystem", layout: "dedicated", base: path, available: true }
            ELSE IF directory_exists(path + "/projects"):
                vault = { mode: "filesystem", layout: "dedicated", base: path, available: true }
            ELSE IF directory_exists(path + "/_cabinet"):
                vault = { mode: "filesystem", layout: "subfolder",
                          base: path + "/_cabinet", available: true }
            ELSE:
                // Directory exists but doesn't look like a cabinet vault
                // Offer to initialise it as a new dedicated vault
                ASK Tom: "Die map ziet er niet uit als een Cabinet vault.
                          Wil je er eentje opstarten? (Ja/Nee)"
                IF yes:
                    // Bootstrap minimal vault structure
                    COPY vault templates from ${CLAUDE_PLUGIN_ROOT}/examples/vault-templates/
                    vault = { mode: "filesystem", layout: "dedicated", base: path, available: true }
                ELSE:
                    vault.available = false
        ELSE:
            // Tom skipped — no vault, no fuss
            vault.available = false
    ELSE:
        // Terminal/Code: silent skip. CLI detection already tried.
        vault.available = false
```

### CLI Detection

```pseudocode
FUNCTION cli_available():
    result = BASH("obsidian version 2>/dev/null")
    RETURN result.exit_code == 0

FUNCTION detect_vault_name():
    // If pwd is inside a vault, obsidian uses it automatically.
    // Otherwise, check for "Claude Cabinet" by name.
    result = BASH('obsidian vault="Claude Cabinet" files total 2>/dev/null')
    IF result.exit_code == 0:
        RETURN "Claude Cabinet"
    RETURN null
```

### After Discovery

Vault mode and base path stored in anchor at `vault.mode` and `vault.base_path`. All subsequent operations use stored values — no re-scanning. If vault becomes unavailable mid-session, `vault_available = false` for the rest of the session.

**Critical (v2.2): no vault is a hard stop for `/cabinet`.** If the discovery chain ends without an available vault, `/cabinet` aborts boot and points the user at `/vault-bridge`. In Cowork mode, the directory picker is the primary recovery path; in terminal/Code mode, the crew directs Tom to run `/vault-bridge create` or `/vault-bridge connect`. After discovery completes successfully, the cabinet never revisits vault state mid-session.

---

## Vault Access Methods

`vault.read()`, `vault.write()`, `vault.append()`, `vault.search()`, `vault.exists()`, and `vault.list()` resolve based on the detected mode. The cabinet has two concrete transport modes:

### Mode A: Obsidian CLI

All operations use the `obsidian` command via Bash. Vault targeting uses `vault="Claude Cabinet"` (or the stored vault name) as the first parameter.

```pseudocode
vault.read(path):
    BASH: obsidian vault="{vault_name}" read path="{path}"
    RETURN stdout

vault.write(path, content):
    // CLI create with overwrite — creates parent dirs implicitly
    BASH: obsidian vault="{vault_name}" create path="{path}" content="{content}" overwrite
    // For large content, use a temp file:
    WRITE content to /tmp/vault-write.md
    BASH: obsidian vault="{vault_name}" create path="{path}" overwrite < /tmp/vault-write.md
    // Note: test which approach the CLI supports for piped content.
    // Fallback: write to filesystem if vault path is also accessible.

vault.append(path, content):
    BASH: obsidian vault="{vault_name}" append path="{path}" content="{content}"

vault.search(query, folder?):
    IF folder:
        BASH: obsidian vault="{vault_name}" search query="{query}" path="{folder}" format=json
    ELSE:
        BASH: obsidian vault="{vault_name}" search query="{query}" format=json
    RETURN parsed results

vault.search_context(query, folder?):
    // Returns grep-style path:line:text — richer than basic search
    BASH: obsidian vault="{vault_name}" search:context query="{query}" path="{folder}"
    RETURN parsed results

vault.exists(path):
    result = BASH: obsidian vault="{vault_name}" file path="{path}" 2>/dev/null
    RETURN result.exit_code == 0

vault.list(dir):
    BASH: obsidian vault="{vault_name}" files folder="{dir}"
    RETURN file list

vault.property_read(path, name):
    // CLI-exclusive — direct frontmatter access without parsing YAML
    BASH: obsidian vault="{vault_name}" property:read path="{path}" name="{name}"
    RETURN value

vault.property_set(path, name, value):
    // CLI-exclusive — set frontmatter field without rewriting the file
    BASH: obsidian vault="{vault_name}" property:set path="{path}" name="{name}" value="{value}"

vault.backlinks(path):
    // CLI-exclusive — get all notes linking to this one
    BASH: obsidian vault="{vault_name}" backlinks path="{path}" format=json
    RETURN parsed results

vault.tags(path?):
    // CLI-exclusive — list tags, optionally for a specific file
    IF path:
        BASH: obsidian vault="{vault_name}" tags path="{path}" counts format=json
    ELSE:
        BASH: obsidian vault="{vault_name}" tags counts format=json
    RETURN parsed results
```

**CLI-exclusive operations** (`property_read`, `property_set`, `backlinks`, `tags`) are only available in CLI mode. In filesystem mode, the cabinet falls back to YAML parsing and Grep-based equivalents where needed. These are enhancements, not requirements — all core vault operations (read, write, append, search, exists, list) work in both modes.

### Mode B: Filesystem

Direct file access when the vault directory is mounted or accessible.

```pseudocode
vault.read(path):       Read tool on {base}/{path}
vault.write(path, c):   Write tool to {base}/{path}
vault.append(path, c):  Read file, append content, Write back (or python append)
vault.search(query):    Grep tool on {base}/ with pattern
vault.exists(path):     Bash: test -f "{base}/{path}"
vault.list(dir):        Glob tool or Bash: ls "{base}/{dir}/"

// No CLI-exclusive operations — fallbacks:
vault.property_read(path, name):    Read file, parse YAML frontmatter, extract field
vault.property_set(path, name, v):  Read file, modify YAML frontmatter, Write back
vault.backlinks(path):              Grep for "[[{filename}]]" across vault
vault.tags(path):                   Grep for "#" patterns, or parse frontmatter tags field
```

### Mode Resolution

The cabinet resolves the mode once at boot (step 1.6) and stores it in `anchor.vault.mode`. All subsequent `vault.*` calls use the stored mode — no re-detection mid-session.

```pseudocode
FUNCTION resolve_operation(op, path, ...args):
    IF anchor.vault.mode == "cli":
        RETURN cli_call(op, anchor.vault.vault_name, path, ...args)
    ELSE IF anchor.vault.mode == "filesystem":
        RETURN filesystem_call(op, anchor.vault.base_path + "/" + path, ...args)
```

---

## Read Triggers — When to Pull from the Vault

### At Boot (After project name is known)

```pseudocode
IF vault_available:
    slug = slugify(project_name)

    // Project brief
    brief = "projects/" + slug + "/brief.md"
    IF vault.exists(brief):
        INJECT vault.read(brief, max_chars=3200) as "Project Brief (from vault)"
        CHATTER "[Bostrol]: Pulled the brief. We're starting informed."

    // Preferences (global)
    prefs = "crew/preferences.md"
    IF vault.exists(prefs):
        INJECT vault.read(prefs, max_chars=2000) as "Known Preferences (from vault)"

    // Lessons (global)
    lessons = "crew/lessons-learned.md"
    IF vault.exists(lessons):
        INJECT vault.read(lessons, max_chars=1200) as "Lessons Learned (from vault)"
```

### On Demand (During Session)

```pseudocode
// Decision precedent lookup — search within the current project's decisions
IF specialist needs precedent:
    results = vault.search(query, "projects/" + slug + "/decisions/")
    FOR each: PRESENT vault.read(result.path, max_chars=1600) as context

// Cross-project decision search (rare)
IF specialist needs cross-project precedent:
    results = vault.search(query)  // vault-wide search, then filter by decision type

// Full brief read
IF specialist needs deeper context:
    vault.read("projects/" + slug + "/brief.md")  // no truncation
```

### Token Budget

| Trigger | Max tokens | Notes |
|---------|-----------|-------|
| Boot — project brief | 800 | Truncate with `[...]` if longer |
| Boot — preferences | 500 | Single file, kept concise |
| Boot — lessons learned | 300 | Recent entries only |
| On-demand — decision lookup | 400 per result, 3 max | Search returns snippets first |
| On-demand — full brief | No limit | Specialist explicitly asked |

---

## Write Triggers — When to Push to the Vault

### At Gate Completion

The full decision-log write flow — including non-trivial decision detection, frontmatter structure, auto-scaffold, and MOC rebuild — lives in `gate-protocol.md § step 5 ("Vault Decision Log")`. That is the single source of truth. This section only notes: writes use `vault.write()` and `vault.exists()` with relative `"projects/{slug}/decisions/"` paths.

### At Wrap-Up

```pseudocode
IF vault_available:
    session_path = "projects/" + project_slug + "/sessions/" + DATE_TODAY + ".md"

    // Ensure project folder exists
    IF NOT vault.exists("projects/" + project_slug + "/brief.md"):
        RUN create-project(project_slug)

    // If same-day session already exists, append to it
    IF vault.exists(session_path):
        vault.append(session_path, new_session_content)
    ELSE:
        vault.write(session_path, session_content)

    // Update indexes
    RUN update_home()
    UPDATE "projects/_index.md" if project status changed
    REBUILD "projects/" + project_slug + "/decisions/_index.md"
```

### Preferences — Append Only

The full preference capture flow — including keyword detection, categorisation, deduplication, and vault I/O — lives in `protocols.md § "Preference Detection"`. That is the single source of truth. This section only notes: writes use `vault.read()`, `vault.append()`, and `vault.property_set()` (CLI mode) or frontmatter update via `vault.write()` (filesystem mode), targeting `"crew/preferences.md"`.

### Lessons Learned — Append with Context

```pseudocode
IF vault_available AND lesson_identified:
    lessons_path = "crew/lessons-learned.md"
    new_entry = """
### {lesson_title} ({DATE_TODAY})

{what happened, what was learned}
Project: [[{project_slug}]]
"""
    vault.append(lessons_path, new_entry)
```

---

## Graceful Degradation

```pseudocode
TRY:
    vault_operation()
CATCH cli_error (CLI mode — command not found, Obsidian not running):
    // Attempt filesystem fallback if vault path is also accessible
    IF directory_exists(anchor.vault.base_path):
        CHATTER "[Bostrol]: CLI down — Obsidian might be closed. Switching to file access."
        anchor.vault.mode = "filesystem"
        RETRY operation in filesystem mode
    ELSE:
        CHATTER "[Bostrol]: Vault offline — CLI down and no file access. Continuing without it."
        vault_available = false
CATCH file_error (filesystem mode — not found, permission denied):
    CHATTER "[Bostrol]: Vault hiccup — {error_type}. Continuing without it."
    vault_available = false
// In all cases: do NOT block the session
```

---

## The `/vault-bridge` Skill

Manual vault operations — the only place vault ops are user-facing:

- **create**: Scaffold new vault
- **create-project**: Scaffold project subfolder
- **connect**: Point at existing vault (detects v1/v2, detects CLI availability)
- **status**: Per-project breakdown
- **sync**: Write/update current project brief
- **archive / unarchive**: Move projects to/from archive
- **reindex**: Rebuild all MOCs from disk
- **housekeeping**: Full consistency check
- **migrate**: Convert v1 → v2 layout

During normal cabinet work, all vault interactions are covert.

---

## Anchor Schema — Vault Block

The vault section of the session anchor is defined in `session-anchor.md § "Schema"` — that is the single source of truth for the full JSON structure and field enums. Key fields: `mode` (cli/filesystem), `layout` (dedicated/subfolder), `base_path`, `vault_name`, `version`, and tracking arrays for reads and writes.
