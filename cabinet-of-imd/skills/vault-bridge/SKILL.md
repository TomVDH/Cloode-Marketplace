---
name: vault-bridge
description: >
  Connect the Cabinet to an Obsidian vault or external folder for persistent
  cross-session memory — project briefs, decision logs, preferences, and
  session summaries. Use when setting up, checking, or manually syncing the
  vault connection.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
version: 3.0.0
---

Bridge between the Cabinet of IMD and a persistent knowledge vault (Obsidian vault or any markdown folder). This skill handles explicit vault operations — creating, connecting, checking status, syncing, archiving, and housekeeping. During normal `/cabinet` sessions, all vault interactions are silent and automatic (see `vault-integration.md`).

The vault supports two transport modes: **CLI** (Obsidian CLI, primary in Claude Code/terminal) and **filesystem** (direct file access, fallback in Cowork). All commands in this skill use the `vault.*` abstraction layer defined in `vault-integration.md` — they work identically in both modes unless noted otherwise.

Bostrol leads all vault operations — he's the documentation specialist and knowledge keeper.

## Vault Structure

Full structure tree, frontmatter schemas, naming rules, and Obsidian conventions are in `vault-integration.md § "Vault Structure"`. Key paths: `projects/{slug}/brief.md`, `projects/{slug}/decisions/`, `projects/{slug}/sessions/`, `archive/{slug}/`, `crew/`. For Obsidian plugin setup, see `references/obsidian-setup.md`.

---

## Commands

### create — Scaffold a new vault

```pseudocode
IF Tom provides path: vault_path = resolve(path)
ELSE: REQUEST directory access → vault_path = selected + "/Claude Cabinet"

IF non-empty dir: offer subfolder mode (_cabinet/) or new location
ELSE: vault_layout = "dedicated", base = vault_path

mkdir -p projects, archive, crew, templates
COPY templates from plugin examples/vault-templates/
CREATE Home.md, projects/_index.md, crew/preferences.md, crew/lessons-learned.md, crew/memories.md, crew/easter-eggs.md

// Detect transport mode
IF cli_available():
    vault_mode = "cli"
    vault_name = basename(vault_path)  // e.g. "Claude Cabinet"
ELSE:
    vault_mode = "filesystem"
    vault_name = null

SET anchor.vault = {
    mode: vault_mode,
    layout: vault_layout,
    base_path: base,
    vault_name: vault_name,
    version: "2.0"
}
```

### create-project — Scaffold a project subfolder

Auto-triggered when `/cabinet` starts on a new project, or manual. Creates a rigid, predictable structure — every project looks the same.

```pseudocode
project_dir = base + "/projects/" + slugify(name)
IF exists: STOP (already scaffolded)

// Vault scaffold (inside Obsidian vault)
mkdir decisions, sessions, chatter, references, tasks inside project_dir
WRITE brief.md from template (with repo and stack fields)
WRITE decisions/_index.md (empty MOC)
WRITE tasks/tasks.md from template
UPDATE projects/_index.md, Home.md

// Codebase scaffold (inside project working directory, if applicable)
// Only create if a git root or working directory is detected
IF codebase_root detected:
    mkdir -p assets, concepts, previews inside codebase_root
    IF NOT exists README.md:
        WRITE README.md — human-written style, not AI boilerplate
        // Must NOT read like AI generated it. Short, direct, useful.
        // Project name, one-line description, stack, getting started.
```

### connect — Point at an existing vault

```pseudocode
// 1. Detect layout (dedicated vs subfolder)
IF path contains Home.md with type: cabinet-home OR path contains projects/:
    vault_layout = "dedicated"
    base = path
ELSE IF path contains _cabinet/:
    vault_layout = "subfolder"
    base = path + "/_cabinet"
ELSE:
    ERROR "No cabinet vault found at this path."

// 2. Detect version
IF any project dir inside base/projects/ has brief.md + decisions/ + sessions/:
    version = "2.0"
ELSE:
    version = "1.0"

// 3. Detect transport mode
IF cli_available():
    vault_mode = "cli"
    vault_name = detect_vault_name() OR basename(path)
ELSE:
    vault_mode = "filesystem"
    vault_name = null

// 4. Inventory
FOR each project dir: count decisions, sessions, read brief status.
Report to Tom.

// 5. Store
SET anchor.vault = {
    mode: vault_mode,
    layout: vault_layout,
    base_path: base,
    vault_name: vault_name,
    version: version
}

IF version == "1.0":
    Suggest: "Run /vault-bridge migrate to convert to v2."

IF vault_mode == "cli":
    CHATTER "[Bostrol]: Connected via Obsidian CLI. Full vault powers active."
ELSE:
    CHATTER "[Bostrol]: Connected via filesystem. All core ops available."
```

### status — Per-project vault overview

```pseudocode
FOR each project dir: read brief frontmatter, count decisions + sessions, find latest session.
FOR each archive dir: list names.
Report: slug, status, decision count, session count, last session date.
Report: crew file availability.
Report: vault mode (cli/filesystem), layout (dedicated/subfolder), version.
IF vault_mode == "cli":
    Report: vault name, CLI version (from "obsidian version").
```

### sync — Write/update current project's brief

```pseudocode
Ensure project folder exists (auto-create if missing).
Build brief from session anchor context (overview, tech stack, scope, conventions, team notes).
IF brief exists: ask merge or overwrite. Merge preserves existing sections, updates scope + team notes.
UPDATE projects/_index.md, Home.md.
```

### archive — Move project to archive/

```pseudocode
UPDATE brief.md frontmatter: status = "archived"
mv projects/{slug} → archive/{slug}
REBUILD projects/_index.md, Home.md
```

### unarchive — Restore from archive/

```pseudocode
UPDATE brief.md frontmatter: status = "active"
mv archive/{slug} → projects/{slug}
REBUILD projects/_index.md, Home.md
```

### reindex — Rebuild all MOCs from disk

Fixes drift from manual edits, deleted files, or interrupted sessions.

```pseudocode
FOR each project dir:
    Validate structure (brief.md, decisions/, sessions/ exist — create if missing)
    Read brief frontmatter for status
    Count decisions, sessions, find latest session
    REBUILD project's decisions/_index.md from decision file frontmatter

Scan archive/ for archived project names.
REBUILD projects/_index.md (table: project, status, decisions, sessions, last session)
REBUILD Home.md via update_home()

Check for orphans: .md files in root-level decisions/ or sessions/ (v1 remnants)
Report issues, fixes, and orphan warnings.
```

### housekeeping — Full consistency check

```pseudocode
1. Frontmatter validation: every .md (excl .obsidian/, templates/) has type, required fields
   - Decisions need: project, date, specialist, status
   - Projects need: status, slug
2. Wikilink integrity: extract [[...]], verify targets exist
3. Stale sessions: flag projects with no session in 90+ days
4. Empty project folders: no brief, no decisions, no sessions → warn
5. Duplicate decisions: same filename across project folders → error

Report: errors (✗), warnings (⚠), auto-fixes (✓)
```

### migrate — Convert v1 flat layout to v2

```pseudocode
Inventory: old projects/*.md, decisions/*.md, sessions/*.md

FOR each project .md: create projects/{slug}/, move to brief.md
FOR each decision: read frontmatter project field, move to projects/{slug}/decisions/
FOR each session: parse slug from filename (YYYY-MM-DD-{slug}.md), move to projects/{slug}/sessions/{date}.md

Remove empty root decisions/ and sessions/ folders.
mkdir archive/
RUN reindex
SET anchor.vault.version = "2.0"
```

---

## Home.md Auto-Maintenance

`update_home()` rebuilds Home.md from disk — never appends, always rewrites dynamic sections.

```pseudocode
Scan projects/ for active projects (slug, status, latest session from brief.md + sessions/)
Scan all projects/*/decisions/ for recent decisions (last 5 across all projects)
Scan all projects/*/sessions/ for recent sessions (last 5 across all projects)
Scan archive/ for archived project names

WRITE Home.md:
  Active Projects (per project: link, status, last session date)
  Recent Decisions (last 5: link, project, specialist)
  Recent Sessions (last 5: link, project)
  Archived Projects (if any)
  Quick Links (preferences, lessons, all projects index)
```

---

## Storage Tiers

**Tier 1 — Session state:** `{project_root}/crew-notes/` — the session anchor (`cabinet-session.json`). Tied to project directory. Ephemeral.

**Tier 2 — Persistent knowledge:** The vault. Everything that matters: project briefs, decisions, sessions, chatter, tasks, references, crew preferences, lessons, memories. Always optional — without it, the cabinet works but nothing persists.

**Tier 3 — Codebase structure:** `{project_root}/` — the actual project files plus scaffolded directories (assets/, concepts/, previews/, README.md). Tied to the git repo.

---

## Covert Rules

`/vault-bridge` commands are **user-facing** — Bostrol reports.
Automatic vault ops during `/cabinet` sessions (brief loading, decision writing, preference capture, session summary) are **covert** — never mentioned to Tom.
