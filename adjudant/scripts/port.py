#!/usr/bin/env python3
"""Adjudant port verb — migrate legacy projects to adjudant compliance.

Run from the project root (or via `python3 adjudant/scripts/port.py`).
Detects project flavor (X/Y/Z) or port phase (preview/applied) and
dispatches accordingly. See docs/superpowers/2026-05-26-adjudant-port.design.md.
"""

import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from connect import validate_slug  # single source of the kebab-case rule


def create_backup(project_root: Path, files_to_backup: list[Path]) -> Path:
    """Create .adjudant-port-backup/{ISO-8601-basic-Z-timestamp}/ and copy
    each existing file into it with `.legacy` suffix. Returns the backup dir."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = project_root / ".adjudant-port-backup" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    for rel in files_to_backup:
        src = project_root / rel
        if not src.is_file():
            continue
        dst_name = src.name + ".legacy"
        shutil.copy2(src, backup_dir / dst_name)

    return backup_dir


_TEMPLATE_SENTINEL_LINES = (
    "# {Project Name}",
    "`{slug}` · type: `{coding|knowledge|plugin|tinkerage}` · vault: [[projects/{slug}/brief|{slug}]]",
)


def _looks_like_template(path: Path) -> bool:
    """Return True if the file's first 5 non-empty lines match the AGENTS.md
    template sentinels (placeholders intact). Used to distinguish a project
    that has just been scaffolded by `connect` from one that's been authored."""
    if not path.is_file():
        return False
    lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()][:5]
    return all(sentinel in lines for sentinel in _TEMPLATE_SENTINEL_LINES)


def detect_flavor(project_root: Path) -> str:
    """Detect the legacy flavor or port phase of a project.

    Returns: "X", "Y", "Z", "preview", or "applied".
    Order matters — preview/applied are checked before legacy markers.
    """
    if (project_root / ".adjudant-port-preview").is_dir():
        return "preview"

    # Compliance alone is enough — the backup dir may have been cleaned or
    # gitignored; a compliant project must never be re-detected as legacy.
    if _is_adjudant_compliant(project_root):
        return "applied"

    if (project_root / ".claude" / "obsidian-bridge").is_file():
        return "Y"

    agents = project_root / "AGENTS.md"
    claude = project_root / "CLAUDE.md"
    if agents.is_file() and not _looks_like_template(agents):
        return "Z"
    if claude.is_file() and claude.read_text().strip() and \
            next((ln.strip() for ln in claude.read_text().splitlines() if ln.strip()), "") != "@AGENTS.md":
        return "Z"

    return "X"


def resolve_vault_path(project_root: Path) -> Optional[Path]:
    """Resolve the vault path for this project per spec resolution order:
    1. OB_VAULT env var
    2. .claude/adjudant breadcrumb (vault_path: field)
    3. .claude/obsidian-bridge breadcrumb (vault: field)
    4. Walk parent dirs for Home.md with `type: vault-home` frontmatter
    5. Return None (caller must prompt)
    """
    env = os.environ.get("OB_VAULT")
    if env:
        return Path(env)

    adj_breadcrumb = project_root / ".claude" / "adjudant"
    if adj_breadcrumb.is_file():
        path = _parse_breadcrumb_field(adj_breadcrumb, "vault_path")
        if path:
            return Path(path)

    ob_breadcrumb = project_root / ".claude" / "obsidian-bridge"
    if ob_breadcrumb.is_file():
        path = _parse_breadcrumb_field(ob_breadcrumb, "vault")
        if path:
            return Path(path)

    return _walk_up_for_vault_home(project_root)


def _parse_breadcrumb_field(path: Path, field: str) -> Optional[str]:
    """Parse a simple `key: value` breadcrumb file. Returns the value of `field` or None."""
    for line in path.read_text().splitlines():
        m = re.match(rf"^\s*{re.escape(field)}\s*:\s*(.+?)\s*$", line)
        if m:
            return m.group(1)
    return None


def _walk_up_for_vault_home(start: Path) -> Optional[Path]:
    """Walk parent dirs looking for Home.md with `type: vault-home` in frontmatter."""
    current = start
    seen = set()
    while True:
        resolved = current.resolve()
        if resolved in seen or resolved == resolved.parent:
            break
        seen.add(resolved)
        home = current / "Home.md"
        if home.is_file():
            text = home.read_text()
            fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
            if fm_match and re.search(r"^\s*type\s*:\s*vault-home\s*$", fm_match.group(1), re.MULTILINE):
                return current
        current = current.parent
    return None


def parse_markdown_sections(text: str) -> dict[str, str]:
    """Parse a markdown file into a dict of {lowercased-heading-text: body}.

    Captures ## and ### headings. Heading text is normalized: lowercased,
    leading/trailing whitespace stripped. Body is everything until the next
    heading at the same or higher level.

    The # (h1) title is ignored. Content before any ## heading is discarded.
    """
    sections: dict[str, str] = {}
    current_key: Optional[str] = None
    current_body: list[str] = []

    for line in text.splitlines():
        heading_match = re.match(r"^(#{2,3})\s+(.+?)\s*$", line)
        if heading_match:
            if current_key is not None:
                sections[current_key] = "\n".join(current_body).strip()
            current_key = heading_match.group(2).strip().lower()
            current_body = []
        elif current_key is not None:
            current_body.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(current_body).strip()

    return sections


OB_SECTION_MAPPING = {
    "working tree":          ("where_things_live_extra_rows", None),
    "stack":                 ("conventions",                  None),
    "stack and tools":       ("conventions",                  None),
    "vault rules":           (None,                           "DROPPED — now in vault-standards.md (single source of truth)"),
    "vault layout":          (None,                           "DROPPED — now in vault-standards.md (single source of truth)"),
    "claude instructions":   ("claude_md_body",               None),
    "claude-specific":       ("claude_md_body",               None),
    "conventions":           ("conventions",                  None),
    "project rules":         ("conventions",                  None),
    "what this is":          ("what_this_is",                 None),
    "purpose":               ("what_this_is",                 None),
    "overview":              ("what_this_is",                 None),
}


def map_ob_sections(ob_sections: dict[str, str]) -> dict[str, str]:
    """Apply the OB → adjudant mapping. Input keys are lowercased headings.

    Returns a dict with these slots:
      - what_this_is: prose for the "What this is" section
      - conventions: prose for the "Conventions" section
      - where_things_live_extra_rows: rows to append to the standard table
      - claude_md_body: content moved to CLAUDE.md (under @AGENTS.md)
      - from_legacy: unmatched headings, appended to AGENTS.md at end
      - decisions: log of all mapping decisions (for summary.md)
    """
    result = {
        "what_this_is": "",
        "conventions": "",
        "where_things_live_extra_rows": "",
        "claude_md_body": "",
        "from_legacy": "",
        "decisions": "",
    }

    for heading, body in ob_sections.items():
        slot, dropped_reason = OB_SECTION_MAPPING.get(heading, (None, None))

        if dropped_reason:
            result["decisions"] += f'- OB "## {heading}" → {dropped_reason}\n'
        elif slot is None:
            # Unmatched
            result["from_legacy"] += f"### {heading}\n\n{body}\n\n"
            result["decisions"] += f'- OB "## {heading}" → "## From legacy AGENTS.md" section at end (no template match)\n'
        elif slot == "where_things_live_extra_rows":
            # Format as a markdown table row — this slot is appended directly to a table
            if heading == "working tree":
                formatted = f"| Working tree (legacy) | {body.strip()} |"
            else:
                formatted = f"| {heading.capitalize()} | {body.strip()} |"
            if result[slot]:
                result[slot] += "\n"
            result[slot] += formatted
            result["decisions"] += f'- OB "## {heading}" → adjudant "{slot}" (deterministic OB mapping)\n'
        else:
            if result[slot]:
                result[slot] += "\n\n"
            result[slot] += body
            result["decisions"] += f'- OB "## {heading}" → adjudant "{slot}" (deterministic OB mapping)\n'

    return result


def render_agents_md(
    project_name: str,
    slug: str,
    project_type: str,
    what_this_is: str,
    conventions: str,
    where_things_live_extra_rows: str,
    from_legacy: str,
) -> str:
    """Render a complete AGENTS.md from inputs. Matches templates/AGENTS.md shape."""
    extra = f"\n{where_things_live_extra_rows}" if where_things_live_extra_rows else ""
    body = f"""# {project_name}

`{slug}` · type: `{project_type}` · vault: [[projects/{slug}/brief|{slug}]]

> One-line purpose of this project.

## What this is

{what_this_is or "{Two to four sentences. Why this project exists, who it's for, what success looks like.}"}

## Where things live

| | |
|---|---|
| Working tree | (this folder) |
| Canonical context | [[projects/{slug}/brief]] |
| Decisions | [[projects/{slug}/decisions]] |
| Sessions | [[projects/{slug}/sessions]] |
| Handoff | [[projects/{slug}/_handoff]] |{extra}

## Conventions

{conventions or "{Project-specific guardrails. Add as they're decided. Examples: stack choices, naming rules, forbidden commands, deploy paths.}"}

## Vault is canonical

When asked "is X documented?" or "do we know Y?", check the vault first: repos document code, the vault documents decisions and context. Use the `adjudant` skill to read/write vault files.

## Claude-specific overrides

Live in `CLAUDE.md` next to this file. CLAUDE.md `@`-imports this file.
"""
    if from_legacy.strip():
        body += f"\n## From legacy AGENTS.md\n\n{from_legacy.rstrip()}\n"
    return body


def render_breadcrumb(vault_path: Path, vault_name: str, slug: str, mode: str) -> str:
    """Render the .claude/adjudant breadcrumb content. Plain `key: value` lines."""
    return (
        f"vault_path: {vault_path}\n"
        f"vault_name: {vault_name}\n"
        f"slug: {slug}\n"
        f"mode: {mode}\n"
    )


def render_claude_md(claude_specific_body: str) -> str:
    """Render CLAUDE.md from the template + optional claude-specific body."""
    extra = f"\n{claude_specific_body.rstrip()}\n" if claude_specific_body.strip() else ""
    return f"""@AGENTS.md

# Claude-specific overrides

Project context, conventions, vault references, and working-files index live in `AGENTS.md` (imported above). Any agent (Claude, Gemini, Codex, Cursor) reads from there.

This file is for **Claude Code-specific overrides only**:
- Slash-command behavior hints
- Plugin/skill invocation preferences
- Claude-only tool guidance (e.g., specific `Bash` allowlists)

**If you're about to add generic project context here, move it to `AGENTS.md` instead.**
{extra}"""


def _agents_hash(project_root: Path) -> str:
    """sha256 over BOTH context files, or 'absent' per file.

    Basis of the apply-time staleness guard promised by reference/port.md.
    CLAUDE.md joined AGENTS.md here after the 2026-07-27 audit (finding 15):
    the guard covered AGENTS.md only, so CLAUDE.md edits made between preview
    and apply were silently clobbered.
    """
    digest = hashlib.sha256()
    for name in ("AGENTS.md", "CLAUDE.md"):
        f = project_root / name
        digest.update(name.encode())
        digest.update(f.read_bytes() if f.is_file() else b"absent")
    return digest.hexdigest()


def _write_source_hash(preview_dir: Path, project_root: Path) -> None:
    (preview_dir / "source-hash.txt").write_text(_agents_hash(project_root) + "\n")


def render_brief_md_y(legacy_brief_text: str, slug: str, project_type: str) -> str:
    """For Y flavor: produce a new adjudant-shape brief.md preserving the legacy body.

    Strips the legacy frontmatter (if any), writes a new adjudant frontmatter
    block, appends the legacy body (without its title duplicate if present).
    """
    body = legacy_brief_text
    # Strip legacy frontmatter
    fm_match = re.match(r"^---\s*\n.*?\n---\s*\n", body, re.DOTALL)
    if fm_match:
        body = body[fm_match.end():]
    body = body.lstrip()

    today = datetime.now().strftime("%Y-%m-%d")
    # Canonical brief frontmatter shape (templates/project-brief-*.md):
    # type is `project` with project_type alongside — NOT type: project-brief-*.
    return (
        f"---\n"
        f"type: project\n"
        f"project_type: {project_type}\n"
        f"slug: {slug}\n"
        f"aliases:\n"
        f"  - {slug}\n"
        f"status: active\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        f"tags:\n"
        f"  - project\n"
        f"---\n"
        f"\n"
        f"{body}"
    )


def generate_preview_y(
    project_root: Path,
    vault_path: Path,
    project_type: str,
    project_name: str,
    slug: Optional[str] = None,
) -> None:
    """For Flavor Y: parse legacy files, run OB mapping, write preview dir.

    Slug precedence: explicit `slug` arg (CLI --slug) → legacy OB breadcrumb's
    slug field → project_root.name.
    """
    preview_dir = project_root / ".adjudant-port-preview"
    preview_dir.mkdir(exist_ok=True)
    _write_source_hash(preview_dir, project_root)

    slug = slug or _parse_breadcrumb_field(project_root / ".claude" / "obsidian-bridge", "slug") or project_root.name
    vault_name = vault_path.name

    agents_legacy = project_root / "AGENTS.md"
    claude_legacy = project_root / "CLAUDE.md"

    ob_sections = parse_markdown_sections(agents_legacy.read_text()) if agents_legacy.is_file() else {}
    claude_sections = parse_markdown_sections(claude_legacy.read_text()) if claude_legacy.is_file() else {}

    mapped = map_ob_sections(ob_sections)

    claude_body = mapped["claude_md_body"]
    for heading, body in claude_sections.items():
        if claude_body:
            claude_body += "\n\n"
        claude_body += f"## {heading.capitalize()}\n\n{body}"
        mapped["decisions"] += f'- Legacy CLAUDE.md "## {heading}" → Kept in CLAUDE.md (legacy claude content)\n'

    agents_out = render_agents_md(
        project_name=project_name,
        slug=slug,
        project_type=project_type,
        what_this_is=mapped["what_this_is"],
        conventions=mapped["conventions"],
        where_things_live_extra_rows=mapped["where_things_live_extra_rows"],
        from_legacy=mapped["from_legacy"],
    )
    claude_out = render_claude_md(claude_specific_body=claude_body)
    breadcrumb_out = render_breadcrumb(vault_path=vault_path, vault_name=vault_name, slug=slug, mode="project")

    (preview_dir / "AGENTS.md.proposed").write_text(agents_out)
    (preview_dir / "CLAUDE.md.proposed").write_text(claude_out)
    (preview_dir / "breadcrumb.proposed").write_text(breadcrumb_out)

    # Generate brief.md.proposed if the legacy vault project has a brief
    legacy_brief = vault_path / "projects" / slug / "brief.md"
    if legacy_brief.is_file():
        brief_out = render_brief_md_y(legacy_brief.read_text(), slug, project_type)
        (preview_dir / "brief.md.proposed").write_text(brief_out)

    vault_changes = _y_vault_changes(vault_path, slug, project_type)
    (preview_dir / "vault-changes.txt").write_text("\n".join(vault_changes) + "\n")

    summary = _render_summary(
        flavor="Y",
        vault_path=vault_path,
        slug=slug,
        decisions=mapped["decisions"],
        vault_changes=vault_changes,
    )
    (preview_dir / "summary.md").write_text(summary)


def _y_vault_changes(vault_path: Path, slug: str, project_type: str) -> list[str]:
    """Return list of vault change operations as strings, one per line.
    Format: "ACTION:path1[:path2]" where ACTION is RENAME, CREATE, ARCHIVE, REPLACE, REGEN, UPDATE-ROW."""
    proj = vault_path / "projects" / slug
    changes = []
    refs = proj / "refs"
    if refs.is_dir():
        changes.append(f"RENAME:{refs}:{proj / 'references'}")
    iterations = proj / "iterations"
    if iterations.is_dir():
        changes.append(f"ARCHIVE:{iterations}:{vault_path / 'legacy' / 'iterations' / slug}")
    for sub in ("tasks", "images"):
        if not (proj / sub).is_dir():
            changes.append(f"CREATE:{proj / sub}")
    if (proj / "brief.md").is_file():
        changes.append(f"REPLACE-FROM-PROPOSED:{proj / 'brief.md'}:brief.md.proposed")
    changes.append(f"REGEN:{proj / '_index.md'}")
    changes.append(f"UPDATE-ROW:{vault_path / 'projects' / '_index.md'}:{slug}")
    return changes


def _capitalise_heading_in_decisions(decisions: str) -> str:
    """Capitalise the first letter of heading names inside '## <name>' patterns in decisions log.
    Leaves the rest of each word lowercase (e.g. 'vault rules' → 'Vault rules')."""
    return re.sub(
        r'"## ([^"]+)"',
        lambda m: f'"## {m.group(1)[0].upper() + m.group(1)[1:]}"',
        decisions,
    )


def _render_summary(flavor: str, vault_path: Path, slug: str, decisions: str, vault_changes: list[str]) -> str:
    """Render the summary.md content for the preview dir."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    vault_changes_table = "\n".join(f"| `{change}` |" for change in vault_changes)
    decisions_display = _capitalise_heading_in_decisions(decisions)
    return f"""# Port preview summary

Generated: {timestamp} · Flavor: {flavor} ({"obsidian-bridge legacy" if flavor == "Y" else "see flavor"})
Vault: {vault_path}/projects/{slug}

## File changes (project side)
| File | Action |
|---|---|
| AGENTS.md | Replace (merged) |
| CLAUDE.md | Replace (merged) |
{"| .claude/obsidian-bridge | Remove (migrated to .claude/adjudant) |" if flavor == "Y" else ""}
| .claude/adjudant | Create |
| .gitignore | Append (.adjudant-port-*) |

## Vault changes
| Operation |
|---|
{vault_changes_table}

## Merge decisions
{decisions_display or "(none)"}

To apply: re-run `/adjudant:adjudant port`.
To discard: delete `.adjudant-port-preview/` and start over.
"""


def generate_preview_x(
    project_root: Path,
    vault_path: Path,
    slug: str,
    project_type: str,
    project_name: str,
) -> None:
    """For Flavor X: fresh-scaffold using templates only. No legacy parsing."""
    preview_dir = project_root / ".adjudant-port-preview"
    preview_dir.mkdir(exist_ok=True)
    _write_source_hash(preview_dir, project_root)
    vault_name = vault_path.name

    agents_out = render_agents_md(
        project_name=project_name,
        slug=slug,
        project_type=project_type,
        what_this_is="",
        conventions="",
        where_things_live_extra_rows="",
        from_legacy="",
    )
    claude_out = render_claude_md(claude_specific_body="")
    breadcrumb_out = render_breadcrumb(vault_path=vault_path, vault_name=vault_name, slug=slug, mode="project")

    (preview_dir / "AGENTS.md.proposed").write_text(agents_out)
    (preview_dir / "CLAUDE.md.proposed").write_text(claude_out)
    (preview_dir / "breadcrumb.proposed").write_text(breadcrumb_out)

    proj = vault_path / "projects" / slug
    subfolders = _project_type_subfolders(project_type)
    vault_changes = [f"CREATE:{proj / sub}" for sub in subfolders]
    vault_changes.append(f"REGEN:{proj / 'brief.md'}")
    vault_changes.append(f"REGEN:{proj / '_index.md'}")
    vault_changes.append(f"UPDATE-ROW:{vault_path / 'projects' / '_index.md'}:{slug}")
    (preview_dir / "vault-changes.txt").write_text("\n".join(vault_changes) + "\n")

    summary = _render_summary(
        flavor="X",
        vault_path=vault_path,
        slug=slug,
        decisions="(no legacy content — fresh scaffold)\n",
        vault_changes=vault_changes,
    )
    (preview_dir / "summary.md").write_text(summary)


def _project_type_subfolders(project_type: str) -> list[str]:
    """Per spec, vault-standards.md per-type subfolder defaults."""
    base = {
        "coding":    ["decisions", "notes", "tasks", "references", "sessions", "images"],
        "plugin":    ["decisions", "notes", "tasks", "references", "sessions", "images", "releases"],
        "knowledge": ["notes", "sources", "references", "sessions"],
        "tinkerage": ["sessions"],
    }
    return base.get(project_type, ["sessions"])


def generate_preview_z_scaffold(
    project_root: Path,
    vault_path: Path,
    slug: str,
    project_type: str,
    project_name: str,
) -> None:
    """For Flavor Z: scaffold the preview dir but leave AGENTS.md.proposed
    and CLAUDE.md.proposed as TODO placeholders. Claude fills them in via
    the AI classifier instructions in reference/port.md.

    Also copies legacy AGENTS.md and CLAUDE.md into the preview dir as
    legacy-AGENTS.md / legacy-CLAUDE.md for Claude's reference.
    """
    preview_dir = project_root / ".adjudant-port-preview"
    preview_dir.mkdir(exist_ok=True)
    _write_source_hash(preview_dir, project_root)
    vault_name = vault_path.name

    for name in ("AGENTS.md", "CLAUDE.md"):
        src = project_root / name
        if src.is_file():
            (preview_dir / f"legacy-{name}").write_text(src.read_text())

    placeholder = "TODO: Claude AI classifier fills this. See reference/port.md for instructions.\n"
    (preview_dir / "AGENTS.md.proposed").write_text(placeholder)
    (preview_dir / "CLAUDE.md.proposed").write_text(placeholder)

    breadcrumb_out = render_breadcrumb(vault_path=vault_path, vault_name=vault_name, slug=slug, mode="project")
    (preview_dir / "breadcrumb.proposed").write_text(breadcrumb_out)

    proj = vault_path / "projects" / slug
    subfolders = _project_type_subfolders(project_type)
    vault_changes = [f"CREATE:{proj / sub}" for sub in subfolders]
    if not (proj / "brief.md").is_file():
        vault_changes.append(f"REGEN:{proj / 'brief.md'}")
    vault_changes.append(f"REGEN:{proj / '_index.md'}")
    vault_changes.append(f"UPDATE-ROW:{vault_path / 'projects' / '_index.md'}:{slug}")
    (preview_dir / "vault-changes.txt").write_text("\n".join(vault_changes) + "\n")

    summary = _render_summary(
        flavor="Z",
        vault_path=vault_path,
        slug=slug,
        decisions="(AI classifier decisions appended by Claude during preview phase)\n",
        vault_changes=vault_changes,
    )
    (preview_dir / "summary.md").write_text(summary)


def validate_vault_changes(preview: Path) -> None:
    """Pre-flight every vault-changes.txt line; raise before ANY write.

    Audit 2026-07-27 finding 10: apply wrote the project-side files first and
    then ran the vault changes with no rollback. A RENAME whose target already
    existed raised a raw OSError mid-loop, leaving the vault half-migrated.
    Retry was then blocked by port's own staleness guard (the recorded hash
    versus the AGENTS.md the failed apply had just written), and re-previewing
    reported "Already ported" because compliance only inspects project-side
    files. The vault stayed unfinished, silently, forever.

    Following shelf's pattern: refuse up front and touch nothing.
    """
    changes_file = preview / "vault-changes.txt"
    if not changes_file.is_file():
        return
    conflicts: list[str] = []
    for line in changes_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(":", 3)
        action = parts[0]
        if action in ("RENAME", "ARCHIVE") and len(parts) >= 3:
            src, dst = Path(parts[1]), Path(parts[2])
            if src.is_dir() and dst.exists():
                conflicts.append(f"{action}: {dst} already exists")
        elif action == "REPLACE-FROM-PROPOSED" and len(parts) >= 3:
            if not (preview / parts[2]).is_file():
                conflicts.append(f"REPLACE-FROM-PROPOSED: {parts[2]} missing from preview")
    if conflicts:
        raise RuntimeError(
            "vault changes cannot be applied cleanly, so NOTHING was changed:\n  "
            + "\n  ".join(conflicts)
            + "\nResolve the conflicts in the vault (or delete "
              ".adjudant-port-preview/ and re-run preview), then apply again."
        )


def apply_preview(project_root: Path) -> None:
    """Phase 2: apply the .adjudant-port-preview/ to the live project."""
    preview = project_root / ".adjudant-port-preview"
    if not preview.is_dir():
        raise RuntimeError(f"No preview at {preview}. Run preview phase first.")

    # Validate preview integrity — all 5 required files must exist
    required = ["AGENTS.md.proposed", "CLAUDE.md.proposed", "breadcrumb.proposed", "vault-changes.txt", "summary.md"]
    missing = [f for f in required if not (preview / f).is_file()]
    if missing:
        raise RuntimeError(
            f"Preview corrupt — missing files: {missing}. "
            "Delete .adjudant-port-preview/ and re-run preview."
        )

    # Guard against unfilled TODO placeholders (Z workflow skipped AI classifier)
    for proposed_name in ("AGENTS.md.proposed", "CLAUDE.md.proposed"):
        content = (preview / proposed_name).read_text()
        if content.lstrip().startswith("TODO:"):
            raise RuntimeError(
                f"{proposed_name} still contains the TODO placeholder. "
                "The AI classifier step was not completed. "
                "See reference/port.md AI classifier section, fill in the proposed files, "
                "then re-run."
            )

    # Staleness guard (reference/port.md fail-conditions): AGENTS.md edited
    # after the preview was generated must not be silently overwritten.
    # Old previews without source-hash.txt skip the check (backward compat).
    hash_file = preview / "source-hash.txt"
    if hash_file.is_file():
        recorded = hash_file.read_text().strip()
        if recorded and recorded != _agents_hash(project_root):
            raise RuntimeError(
                "AGENTS.md or CLAUDE.md changed since the preview was "
                "generated — applying would overwrite those edits. Delete "
                ".adjudant-port-preview/ and re-run the preview phase."
            )

    # Refuse before touching anything if the vault changes cannot land
    # cleanly — a half-migrated vault used to be unrecoverable (finding 10).
    validate_vault_changes(preview)

    files_to_backup = [
        Path("AGENTS.md"),
        Path("CLAUDE.md"),
        Path(".claude/obsidian-bridge"),
        Path(".claude/adjudant"),
    ]
    create_backup(project_root, files_to_backup)

    proposed_agents = preview / "AGENTS.md.proposed"
    proposed_claude = preview / "CLAUDE.md.proposed"
    proposed_breadcrumb = preview / "breadcrumb.proposed"

    if proposed_agents.is_file():
        (project_root / "AGENTS.md").write_text(proposed_agents.read_text())
    if proposed_claude.is_file():
        (project_root / "CLAUDE.md").write_text(proposed_claude.read_text())
    if proposed_breadcrumb.is_file():
        claude_dir = project_root / ".claude"
        claude_dir.mkdir(exist_ok=True)
        (claude_dir / "adjudant").write_text(proposed_breadcrumb.read_text())

    ob = project_root / ".claude" / "obsidian-bridge"
    if ob.exists():
        ob.unlink()

    vault_changes_file = preview / "vault-changes.txt"
    if vault_changes_file.is_file():
        for line in vault_changes_file.read_text().splitlines():
            line = line.strip()
            if line:
                _apply_vault_change(line, preview_dir=preview)

    _ensure_gitignore_entries(
        project_root,
        [".adjudant-port-preview/", ".adjudant-port-backup/", ".claude/adjudant"],
    )

    shutil.rmtree(preview)


def _apply_vault_change(line: str, preview_dir: Optional[Path] = None) -> None:
    """Apply a single vault-changes.txt line. Format: ACTION:path[:path2[:extra]]."""
    parts = line.split(":", 3)
    action = parts[0]
    if action == "CREATE":
        Path(parts[1]).mkdir(parents=True, exist_ok=True)
    elif action == "RENAME":
        src, dst = Path(parts[1]), Path(parts[2])
        if src.is_dir():
            src.rename(dst)
    elif action == "ARCHIVE":
        src, dst = Path(parts[1]), Path(parts[2])
        if src.is_dir():
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
    elif action == "REPLACE-FROM-PROPOSED":
        if preview_dir is None:
            raise RuntimeError("REPLACE-FROM-PROPOSED requires preview_dir")
        live_path = Path(parts[1])
        proposed_name = parts[2]
        proposed_path = preview_dir / proposed_name
        if not proposed_path.is_file():
            raise RuntimeError(f"REPLACE-FROM-PROPOSED: {proposed_path} not found in preview")
        # Vault-side files are outside create_backup's project-side list — back
        # them up here so "Originals backed up" holds for the vault too.
        if live_path.is_file():
            backup_dir = preview_dir.parent / ".adjudant-port-backup" / "vault"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_name = f"{live_path.parent.name}__{live_path.name}.legacy"
            (backup_dir / backup_name).write_text(live_path.read_text())
        live_path.write_text(proposed_path.read_text())
    elif action == "REPLACE":
        pass  # leave as-is for legacy compat; tests should use REPLACE-FROM-PROPOSED now
    elif action == "REGEN":
        target = Path(parts[1])
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.name == "brief.md":
                slug = target.parent.name
                today = datetime.now().strftime("%Y-%m-%d")
                target.write_text(
                    f"---\ntype: project\nproject_type: coding\nslug: {slug}\n"
                    f"aliases:\n  - {slug}\nstatus: active\n"
                    f"created: {today}\nupdated: {today}\ntags:\n  - project\n---\n\n"
                    "# Brief\n\n(Brief content goes here. Edit and re-run `/adjudant:adjudant sync`.)\n"
                )
            else:
                target.write_text(f"# Index\n\n(Regenerate manually or via `/adjudant:adjudant ramasse`)\n")
    elif action == "UPDATE-ROW":
        idx_path = Path(parts[1])
        slug = parts[2]
        _upsert_project_index_row(idx_path, slug)


PROJECTS_INDEX_HEADER = "| Project | Type | Status | Decisions | Sessions | Last Session |"
PROJECTS_INDEX_SEP = "|---|---|---|---|---|---|"


def _project_type_from_brief(proj_dir: Path) -> str:
    """Best-effort project_type for the index row. Reads the project's brief
    frontmatter; returns '—' when it can't be determined."""
    brief = proj_dir / "brief.md"
    if not brief.is_file():
        return "—"
    text = brief.read_text()
    m = re.search(r'^project_type:\s*"?([a-z]+)"?', text, re.M)
    if m:
        return m.group(1)
    m = re.search(r'^type:\s*project-brief-([a-z]+)', text, re.M)
    if m:
        return m.group(1)
    return "—"


def _upsert_project_index_row(idx_path: Path, slug: str) -> None:
    """Add a row for `slug` in the vault's projects/_index.md using adjudant's
    canonical 6-column format (matches templates/_index-projects.md):
    `| Project | Type | Status | Decisions | Sessions | Last Session |`.
    Count columns are left as '—'; `/adjudant ramasse` fills them.

    Safety rules (never corrupt a hand-maintained vault index):
      1. Missing file -> create from the canonical 6-column template.
      2. Idempotent -> if a row already links projects/{slug}/brief, do nothing.
      3. Canonical 6-column header present -> append a 6-column row.
      4. Any other (unknown / custom) format -> DO NOT WRITE; the user adds the
         row themselves (surfaced in the port summary).
    """
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    proj_type = _project_type_from_brief(idx_path.parent / slug)
    # Canonical row form shared with connect.upsert_projects_index_row: link is
    # index-relative ({slug}/brief, not projects/{slug}/brief) and the alias
    # pipe MUST be escaped (\|) or it splits the markdown table cell.
    row = f"| [[{slug}/brief\\|{slug}]] | {proj_type} | active | — | — | — |"

    if not idx_path.is_file():
        idx_path.write_text(
            "---\ntype: index\ntags:\n  - index\n---\n\n# All Projects\n\n"
            f"{PROJECTS_INDEX_HEADER}\n{PROJECTS_INDEX_SEP}\n{row}\n"
        )
        return

    text = idx_path.read_text()
    # Idempotency: already listed — accept both historical row forms
    # (connect's `[[{slug}/brief\|…` and old port's `[[projects/{slug}/brief|…`)
    if re.search(r"\[\[(?:projects/)?" + re.escape(slug) + r"/brief[\\|\]]", text):
        return
    # Append only into the canonical 6-column index — never corrupt other formats
    if PROJECTS_INDEX_HEADER.replace(" ", "") in text.replace(" ", ""):
        idx_path.write_text(text.rstrip() + f"\n{row}\n")
    # else: unrecognised/custom format -> leave untouched (conservative)


def _ensure_gitignore_entries(project_root: Path, entries: list[str]) -> None:
    """Append entries to .gitignore if missing. Create file if needed."""
    gi = project_root / ".gitignore"
    if not gi.is_file():
        gi.write_text("\n".join(entries) + "\n")
        return
    existing = set(line.strip() for line in gi.read_text().splitlines())
    to_add = [e for e in entries if e not in existing]
    if to_add:
        with gi.open("a") as f:
            f.write("\n" + "\n".join(to_add) + "\n")


def _is_adjudant_compliant(project_root: Path) -> bool:
    """Project is compliant if all four hold:
    1. breadcrumb at .claude/adjudant exists
    2. AGENTS.md exists
    3. CLAUDE.md exists and starts with `@AGENTS.md`
    4. no .claude/obsidian-bridge breadcrumb lingering
    """
    if not (project_root / ".claude" / "adjudant").is_file():
        return False
    if not (project_root / "AGENTS.md").is_file():
        return False
    claude_md = project_root / "CLAUDE.md"
    if not claude_md.is_file():
        return False
    first_line = next(
        (ln.strip() for ln in claude_md.read_text().splitlines() if ln.strip()),
        "",
    )
    if first_line != "@AGENTS.md":
        return False
    if (project_root / ".claude" / "obsidian-bridge").exists():
        return False
    return True


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="port.py",
        description="Adjudant port verb — migrate legacy projects to adjudant compliance.",
    )
    parser.add_argument("phase", choices=["preview", "apply", "detect"], help="Phase to run")
    parser.add_argument("--project-root", "--project-dir", dest="project_root",
                        default=".", help="Project root path (default: cwd)")
    parser.add_argument("--vault-path", help="Vault path (overrides env/breadcrumb resolution)")
    parser.add_argument("--slug", help="Project slug (auto-derived if omitted)")
    parser.add_argument("--project-type", choices=["coding", "knowledge", "plugin", "tinkerage"], help="Project type")
    parser.add_argument("--project-name", help="Human-readable project name")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()

    if args.phase == "detect":
        print(detect_flavor(root))
        return 0

    if args.phase == "apply":
        try:
            apply_preview(root)
            print(f"[port] Applied. Originals backed up to {root}/.adjudant-port-backup/")
            print("[port] Run /adjudant:adjudant check to verify.")
            return 0
        except RuntimeError as e:
            print(f"[port] ERROR: {e}", file=sys.stderr)
            return 1

    # Check phase-state before resolving vault — short-circuit if no migration is due
    flavor = detect_flavor(root)
    if flavor == "applied":
        print("[port] Already ported. Run /adjudant:adjudant check to verify.")
        return 0
    if flavor == "preview":
        print("[port] Preview exists at .adjudant-port-preview/. Run `port.py apply` to apply it, or delete the preview dir to restart.", file=sys.stderr)
        return 1

    vault_path = Path(args.vault_path) if args.vault_path else resolve_vault_path(root)
    if vault_path is None:
        print("[port] ERROR: Vault path unresolvable. Pass --vault-path or set OB_VAULT env var.", file=sys.stderr)
        return 1

    slug = args.slug or root.name
    slug_error = validate_slug(slug)
    if slug_error:
        print(f"[port] ERROR: {slug_error}. Pass --slug with a kebab-case name.", file=sys.stderr)
        return 1
    project_type = args.project_type or "coding"
    project_name = args.project_name or slug.replace("-", " ").title()

    if flavor == "Y":
        # Only an explicit --slug overrides the legacy OB breadcrumb's slug
        generate_preview_y(root, vault_path=vault_path, project_type=project_type,
                           project_name=project_name, slug=args.slug)
    elif flavor == "Z":
        generate_preview_z_scaffold(root, vault_path=vault_path, slug=slug, project_type=project_type, project_name=project_name)
    elif flavor == "X":
        generate_preview_x(root, vault_path=vault_path, slug=slug, project_type=project_type, project_name=project_name)
    else:
        print(f"[port] Unexpected flavor for preview phase: {flavor}", file=sys.stderr)
        return 1

    print(f"[port] Preview written to {root}/.adjudant-port-preview/")
    print("[port] Review the .proposed files. Re-run /adjudant:adjudant port to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
