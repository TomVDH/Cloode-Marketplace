# Vault Integration

The `vault.*` abstraction layer for Obsidian vault operations. Single interface that resolves CLI vs filesystem at call time. This is the implementation reference — read on-demand when performing vault operations.

## Transport Modes

### CLI mode (preferred)

Uses Obsidian CLI 1.12+. Advantages:

- Wikilinks in frontmatter recognised natively by Obsidian's parser.
- `property:set` writes frontmatter without re-parsing the file.
- `move` and `rename` trigger Obsidian's automatic internal-link updater.
- `search` uses Obsidian's index — vault-aware, faster.
- `backlinks` and `tags` return live graph data.
- No manual YAML parsing, no fragile regex.

### Filesystem mode (fallback)

Direct file access via Read/Write/Glob/Grep tools. Used when CLI is unavailable (Cowork, Obsidian not installed, CLI broken).

### Detection

```bash
command -v obsidian >/dev/null 2>&1 && obsidian version 2>/dev/null
```

Result stored in breadcrumb file as `mode=cli` or `mode=filesystem`. Re-detection on next SessionStart only.

### Graceful degradation

If CLI was selected but a CLI op fails mid-session (e.g., Obsidian closed), attempt filesystem fallback transparently for that op, log once, continue.

---

## Vault Discovery

Run by SessionStart hook. Order:

1. Read breadcrumb `$CLAUDE_PROJECT_DIR/.obsidian-bridge` if it exists.
2. Fall back to `$CLAUDE_PROJECT_DIR/.cabinet-anchor-hint` (backward-compatible).
3. Try `$OB_DEFAULT_VAULT` env var.
4. Try CLI: `obsidian vault="<known name>" files total` for known vault names.
5. Walk parent dirs of `$CLAUDE_PROJECT_DIR` for `Home.md` with `type: vault-home` or `type: cabinet-home`.
6. None found → emit "not linked" context.

---

## Breadcrumb File — `.obsidian-bridge`

Plain `KEY=VALUE` text file in the working directory. Written by `/connect` (or `/connect --link-only`). Add to `.gitignore`.

```
vault_path=/Users/tom/Documents/MyVault
vault_name=MyVault
project_slug=oz-floer
linked_at=2026-04-30
mode=cli
```

Optional field for iteration-shelf coordination:

```
iterations_path=projects/oz-floer/iterations
```

---

## Vault Primitives — `vault.*` Operations

### Resolution

```pseudocode
FUNCTION vault.<op>(args):
    IF cli_available() AND op is supported by CLI:
        RUN obsidian CLI command
    ELSE:
        RUN filesystem equivalent
```

### CLI + filesystem (both supported)

| Operation | CLI command | Filesystem equivalent |
|---|---|---|
| `vault.read(path)` | `obsidian vault="V" read "path"` | Read tool on `{vault_path}/{path}` |
| `vault.write(path, content)` | `obsidian vault="V" write "path" --content "..."` | Write tool to `{vault_path}/{path}` (mkdir -p parent) |
| `vault.append(path, content)` | `obsidian vault="V" append "path" --content "..."` | Read + append + Write |
| `vault.search(query, folder?)` | `obsidian vault="V" search "query" --folder "f"` | Grep tool in `{vault_path}/{folder}` |
| `vault.search_context(query, folder?)` | `obsidian vault="V" search "query" --context --folder "f"` | Grep with context lines |
| `vault.exists(path)` | `obsidian vault="V" read "path" --dry-run` | Check file exists via Read |
| `vault.list(dir)` | `obsidian vault="V" list "dir"` | Glob `{vault_path}/{dir}/*.md` |

### CLI-exclusive (filesystem degrades to best-effort)

| Operation | CLI command | Filesystem fallback |
|---|---|---|
| `vault.property_read(path, name)` | `obsidian vault="V" property:read "path" "name"` | Parse YAML frontmatter from file |
| `vault.property_set(path, name, value)` | `obsidian vault="V" property:set "path" "name" "value"` | Rewrite YAML frontmatter in file |
| `vault.backlinks(path)` | `obsidian vault="V" backlinks "path"` | Grep for `[[{filename}]]` across vault |
| `vault.tags(path?)` | `obsidian vault="V" tags "path"` | Parse frontmatter tags + grep body |
| `vault.move(from, to)` | `obsidian vault="V" move "from" "to"` | Filesystem move + manual link rewrite (lossy) |
| `vault.rename(from, new_name)` | `obsidian vault="V" rename "from" "new_name"` | Filesystem rename + manual link rewrite (lossy) |

Note: CLI `move` and `rename` automatically update all internal links pointing to the moved/renamed file. Filesystem fallback cannot do this reliably — it's marked "lossy" and `/dream` should be run afterward to detect broken links.

---

## `update_home()` Procedure

Rebuilds `Home.md` from disk state. Never appends — always rewrites dynamic sections.

```pseudocode
Scan projects/ for active projects (slug, status, project_type, latest session from brief.md + sessions/)
Scan all projects/*/decisions/ for recent decisions (last 5 across vault)
Scan all projects/*/sessions/ for recent sessions (last 5 across vault)
Scan archive/ for archived project names

WRITE Home.md:
  Active Projects (per project: link, type, status, last session date)
  Recent Decisions (last 5: link, project, date)
  Recent Sessions (last 5: link, project, date)
  Archived Projects (if any)
  Quick Links (all projects index, crew/ if it exists)
```

When `crew/` exists (cabinet installed), Quick Links includes pointers to crew files. Bridge does not rewrite the crew section — just links to it.
