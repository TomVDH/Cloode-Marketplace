# /adjudant port

Migrate any project to adjudant compliance. **One verb, two phases (preview → apply), auto-detects legacy flavor.**

## Decision: phase 1 vs phase 2

First, detect the project state by running:

```bash
python3 "$(dirname "$0")/../../../scripts/port.py" detect --project-root "$PROJECT_ROOT"
```

Where `$PROJECT_ROOT` is the user's current working directory (default: `.`).

Output is one of: `X`, `Y`, `Z`, `preview`, `applied`.

| Output | What to do |
|---|---|
| `preview` | Phase 2 (apply). Skip to "Apply phase" below. |
| `applied` | Print: "Already ported. Run `/adjudant:adjudant check` to verify." Exit. |
| `X`, `Y`, or `Z` | Phase 1 (preview). Continue to "Preview phase" below. |

## Preview phase

### 1. Resolve required inputs

- **vault_path:** Try in order:
  1. `OB_VAULT` env var
  2. `.claude/adjudant` breadcrumb (`vault_path:` field)
  3. `.claude/obsidian-bridge` breadcrumb (`vault:` field)
  4. Walk parent dirs for `Home.md` with `type: vault-home` or `type: index`
  5. Prompt the user once

- **slug:** Project root directory basename, kebab-case-enforced. If basename has spaces/dots/uppercase, prompt user for a clean slug.

- **project_type:** One of `coding | knowledge | plugin | tinkerage`. For Y, try to read from the OB breadcrumb or `brief.md` frontmatter. For Z, prompt the user. For X, prompt the user.

- **project_name:** For Y, try the `# Heading` of legacy AGENTS.md. For Z, same. For X, prompt the user (default: kebab-slug → title-case).

### 2. Run port.py preview

For **Y** or **X**:

```bash
python3 port.py preview \
  --project-root "$PROJECT_ROOT" \
  --vault-path "$VAULT_PATH" \
  --slug "$SLUG" \
  --project-type "$PROJECT_TYPE" \
  --project-name "$PROJECT_NAME"
```

This writes `.adjudant-port-preview/` with all required files (deterministic; no AI work needed).

For **Z**: run the same command, then proceed to the AI classifier step (below) to fill in the proposed files.

### 3. AI classifier (Z case only)

For Z, port.py wrote placeholder `.proposed` files and copied legacy files to `.adjudant-port-preview/legacy-AGENTS.md` and `legacy-CLAUDE.md`. Now:

1. Read `.adjudant-port-preview/legacy-AGENTS.md` and `legacy-CLAUDE.md`.
2. Parse them into sections (h2 + h3 headings).
3. For each section in legacy AGENTS.md, classify into one of these buckets:
   - `template-section:what-this-is` — purpose/overview prose
   - `template-section:conventions` — code style, stack, deploy paths, naming, project rules
   - `where-things-live-row` — explicit project file locations
   - `claude-tool-specific` — Bash allowlists, slash command behavior, tool routing
   - `vault-rules` — DROPPED (note in summary.md; user is informed they're in vault-standards.md now)
   - `unclassifiable` — appended to "## From legacy AGENTS.md" with explanation
4. For each section in legacy CLAUDE.md, classify into:
   - `move-to-agents` — generic project context → goes to AGENTS.md Conventions
   - `keep-in-claude` — Claude-tool-specific
5. Render the new AGENTS.md using the same template shape (see templates/AGENTS.md), populating sections from buckets.
6. Render the new CLAUDE.md: `@AGENTS.md` line + minimal template + kept Claude-specific sections.
7. Overwrite `.adjudant-port-preview/AGENTS.md.proposed` and `CLAUDE.md.proposed`.
8. Append per-section decisions to `.adjudant-port-preview/summary.md` under a `## AGENTS.md merge decisions` / `## CLAUDE.md merge decisions` heading.

If the AI classifier cannot complete (e.g., legacy file is binary, max-tokens hit), fall back: append entire legacy AGENTS.md verbatim under `## From legacy AGENTS.md` heading; dump legacy CLAUDE.md verbatim under `@AGENTS.md` import. Note the fallback in summary.md.

### 4. Tell the user

Print:

```
[port] Preview written to .adjudant-port-preview/
[port] Review:
  - AGENTS.md.proposed
  - CLAUDE.md.proposed
  - breadcrumb.proposed
  - vault-changes.txt
  - summary.md
[port] To apply: re-run /adjudant:adjudant port
[port] To discard: delete .adjudant-port-preview/
```

## Apply phase

When `detect` returns `preview`:

1. Validate preview integrity. Required files in `.adjudant-port-preview/`:
   - `AGENTS.md.proposed`
   - `CLAUDE.md.proposed`
   - `breadcrumb.proposed`
   - `vault-changes.txt`
   - `summary.md`

   If any missing: print error pointing user at fix + exit non-zero.

2. Run the mechanical apply:

```bash
python3 port.py apply --project-root "$PROJECT_ROOT"
```

This:
- Creates timestamped backup at `.adjudant-port-backup/{YYYYMMDDTHHMMSSZ}/`
- Writes proposed files to live positions
- Removes legacy `.claude/obsidian-bridge`
- Applies vault changes (folder renames/creates/archives, brief.md, _index.md update)
- Appends `.gitignore` entries
- Deletes `.adjudant-port-preview/`

3. Print:

```
[port] Done.
[port] Backup: .adjudant-port-backup/{timestamp}/
[port] Run /adjudant:adjudant check to verify.
```

## Fail conditions

| Condition | Action |
|---|---|
| Vault unresolvable AND user declines | Print error, exit non-zero |
| Preview corrupt during apply | Print "delete preview, re-run port" |
| Apply phase, AGENTS.md changed since preview generated | Warn user, suggest re-preview |
| Y: OB breadcrumb unparseable | Print error, suggest manual breadcrumb |
| Slug contains invalid chars | Print error with rename suggestion |
| `project_type` required and not promptable | Exit non-zero |

## See also

- `reference/connect.md` — adjudant's simpler counterpart (X-flavor only, no migration)
- `templates/AGENTS.md`, `templates/CLAUDE.md` — the shapes `port` enforces
- `reference/vault-standards.md` — per-`project_type` folder defaults
- `docs/superpowers/2026-05-26-adjudant-port.design.md` — full design spec
