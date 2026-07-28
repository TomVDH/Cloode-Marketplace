#!/usr/bin/env python3
"""Adjudant vault-walk primitives.

Shared module for dream/check/tidy. Stdlib-only. Read-only.

Public API:
    parse_frontmatter(text) -> (Frontmatter, body)
    extract_wikilinks(body) -> list[Wikilink]
    extract_inline_tags(body) -> list[str]
    extract_markdown_md_links(body) -> list[(text, path, line)]
    walk_project(root) -> Iterator[VaultFile]
    build_vault_index(vault_root) -> set[str]
    resolve_wikilink(target, index) -> bool
    parse_breadcrumb(project_root) -> Optional[dict]
    resolve_vault(project_root, env_vault=None) -> Optional[Path]
    is_safe_slug(slug) -> bool
    safe_project_root(vault, slug) -> Optional[Path]
    is_bucket_d_tag(tag, project_slug=None) -> bool
    schema_drift_for_file(vf, aliases=None) -> Optional[dict]
    schema_drift(files, aliases=None) -> dict

Schema constants (single source of truth, imported by dream + tidy):
    BUCKET_A_TYPES, BUCKET_B_MIGRATIONS, BUCKET_D_TAG_PREFIXES,
    BUCKET_D_TAG_EXACT, VAGUE_TOPICAL_TAGS, CREW_NAMES,
    PROJECT_TYPE_DEFAULT_FOLDERS, AUTO_CREATED_FOLDERS, INDEX_EXEMPT_FOLDERS

CLI smoke-test mode (read-only, the module never writes):
    python3 _vault_walk.py --project-dir PATH [--vault-dir PATH] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator, Optional


# ============================================================
# Frontmatter parsing — minimal YAML (stdlib only, mirrors port.py regex approach)
# ============================================================


@dataclass
class Frontmatter:
    raw: str = ""
    fields: dict[str, Any] = field(default_factory=dict)
    parse_error: Optional[str] = None
    has_block: bool = False


def parse_frontmatter(text: str) -> tuple[Frontmatter, str]:
    """Extract YAML frontmatter from a markdown file. Returns (fm, body).

    Recognizes the standard `---\\n...\\n---\\n` opening.
    """
    fm = Frontmatter()
    if not text.startswith("---"):
        return fm, text

    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return fm, text

    close_idx: Optional[int] = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            close_idx = i
            break

    if close_idx is None:
        fm.parse_error = "frontmatter block missing closing ---"
        return fm, text

    fm.has_block = True
    fm.raw = "\n".join(lines[1:close_idx])
    body = "\n".join(lines[close_idx + 1:])
    fm.fields = _parse_minimal_yaml(fm.raw)
    return fm, body


_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$")
# Zero-or-more indent: Obsidian tolerates flush-left list items under a key
_LIST_ITEM_RE = re.compile(r"^(\s*)-\s+(.*)$")


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    """Tiny YAML parser. Handles:
      - key: value
      - key: "quoted" or 'quoted'
      - key:
          - list_item
          - list_item
      - # comments
      - null/~/empty values (preserved as None to allow drift detection)

    Does NOT handle: nested mappings, multi-line scalars, flow style,
    anchors. Unknown shapes are recorded as raw string.
    """
    result: dict[str, Any] = {}
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        m = _KEY_RE.match(line)
        if not m:
            i += 1
            continue
        key = m.group(1)
        rest = m.group(2).strip()

        # Strip trailing comments OUTSIDE quotes (cheap heuristic)
        if rest and not (rest.startswith('"') or rest.startswith("'")):
            rest = re.sub(r"\s+#.*$", "", rest)

        if rest == "":
            # Possible list block
            items: list[str] = []
            j = i + 1
            while j < len(lines):
                ln = lines[j]
                if ln.strip() == "" or ln.strip().startswith("#"):
                    j += 1
                    continue
                m2 = _LIST_ITEM_RE.match(ln)
                if m2:
                    items.append(_strip_quotes(m2.group(2).strip()))
                    j += 1
                else:
                    break
            if items:
                result[key] = items
                i = j
                continue
            else:
                result[key] = None
                i += 1
                continue

        # Flow-style list: tags: [a, b] — parse into a real list, not a scalar
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            result[key] = (
                [_strip_quotes(part.strip()) for part in inner.split(",") if part.strip()]
                if inner else []
            )
            i += 1
            continue

        # Single-line value
        # Preserve literal "null"/"~" as the string so drift detection can flag it,
        # rather than coercing to Python None.
        result[key] = _strip_quotes(rest)
        i += 1
    return result


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        return s[1:-1]
    return s


# ============================================================
# Wikilinks & inline tags
# ============================================================


@dataclass
class Wikilink:
    target: str
    alias: Optional[str]
    heading: Optional[str]
    line: int
    raw: str
    is_embed: bool = False  # ![[...]] — attachment/transclusion, not a nav link


WIKILINK_RE = re.compile(r"\[\[(.+?)\]\]")
ALIAS_SEP_RE = re.compile(r"\\?\|")  # | or \|, both alias separators
TAG_RE = re.compile(r"(?:^|[\s,()])#([A-Za-z][\w/-]*)")
# Scheme lookahead keeps external URLs ending in .md (e.g. GitHub blobs) out
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((?![a-z][a-z0-9+.-]*://)([^)\s]+\.md(?:#[^)\s]*)?)\)")
# Wikilink target extensions the vault index can resolve; anything else
# (png, pdf, …) is an attachment and not checkable against the index
INDEXABLE_LINK_EXTS = (".md", ".canvas", ".base")
URL_RE = re.compile(r"https?://\S+")
# Inline code spans (single-line): `…`. Triple backticks are fenced blocks,
# handled separately. Substituting with spaces preserves line geometry.
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def _strip_inline_code(line: str) -> str:
    """Replace `inline code` spans with spaces to neutralise content
    that shouldn't match link/tag patterns (e.g. ``[[stem|text]]`` in a
    code example, or ``#tag`` in a literal command)."""
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)


def extract_wikilinks(body: str) -> list[Wikilink]:
    """All [[...]] in body, skipping code blocks (fenced + 4-space indented)."""
    links: list[Wikilink] = []
    in_fenced = False
    for lineno, line in enumerate(body.split("\n"), start=1):
        ls = line.lstrip()
        if ls.startswith("```"):
            in_fenced = not in_fenced
            continue
        if in_fenced:
            continue
        # 4-space indented code block heuristic: skip when line begins with 4+ spaces
        # but only if it's not a list continuation. Safe minimum: skip if starts with
        # exactly 4+ spaces AND doesn't have a `-`/`*`/`+` as the first non-space char.
        if line.startswith("    ") and line.lstrip()[:1] not in ("-", "*", "+", "|", "["):
            continue
        # Strip inline-code spans before extracting (prevents [[stem|text]] in
        # backticks from being picked up).
        scan = _strip_inline_code(line)
        for m in WIKILINK_RE.finditer(scan):
            inner = m.group(1)
            parts = ALIAS_SEP_RE.split(inner, maxsplit=1)
            target_full = parts[0].strip()
            alias = parts[1].strip() if len(parts) > 1 else None
            heading: Optional[str] = None
            target = target_full
            if "#" in target:
                target, heading = target.split("#", 1)
                target = target.strip()
                heading = heading.strip()
            is_embed = m.start() > 0 and scan[m.start() - 1] == "!"
            links.append(Wikilink(
                target=target,
                alias=alias,
                heading=heading,
                line=lineno,
                raw=m.group(0),
                is_embed=is_embed,
            ))
    return links


def extract_inline_tags(body: str) -> list[str]:
    """Inline #tags in body, skipping code blocks and URLs."""
    out: list[str] = []
    in_fenced = False
    for line in body.split("\n"):
        ls = line.lstrip()
        if ls.startswith("```"):
            in_fenced = not in_fenced
            continue
        if in_fenced:
            continue
        if line.startswith("    "):
            continue
        cleaned = URL_RE.sub("", line)
        cleaned = _strip_inline_code(cleaned)
        for m in TAG_RE.finditer(cleaned):
            out.append(m.group(1))
    return out


def extract_markdown_md_links(body: str) -> list[tuple[str, str, int]]:
    """[text](path.md) occurrences (potential wikilink-form violations)."""
    out: list[tuple[str, str, int]] = []
    in_fenced = False
    for lineno, line in enumerate(body.split("\n"), start=1):
        ls = line.lstrip()
        if ls.startswith("```"):
            in_fenced = not in_fenced
            continue
        if in_fenced:
            continue
        scan = _strip_inline_code(line)
        for m in MD_LINK_RE.finditer(scan):
            out.append((m.group(1), m.group(2), lineno))
    return out


# ============================================================
# VaultFile + walker
# ============================================================


@dataclass
class VaultFile:
    path: Path
    rel_path: Path
    frontmatter: Frontmatter
    body: str
    tags_frontmatter: list[str]
    tags_inline: list[str]
    wikilinks: list[Wikilink]
    markdown_md_links: list[tuple[str, str, int]]

    @property
    def tags(self) -> list[str]:
        return self.tags_frontmatter + self.tags_inline

    @property
    def file_type(self) -> Optional[str]:
        t = self.frontmatter.fields.get("type")
        return t if isinstance(t, str) else None


DEFAULT_SKIP: tuple[str, ...] = (
    ".git", "node_modules", "__pycache__", ".obsidian", ".trash",
    # adjudant's own scratch dirs — never scan a pending preview/backup
    ".adjudant-tidy-preview", ".adjudant-tidy-backup",
    ".adjudant-port-preview", ".adjudant-port-backup",
    ".adjudant-shelf-preview", ".adjudant-shelf-backup",
)


def walk_project(
    root: Path,
    *,
    skip: tuple[str, ...] = DEFAULT_SKIP,
    include_legacy: bool = False,
) -> Iterator[VaultFile]:
    """Yield VaultFile for every .md in root, recursively.

    By default skips .git, node_modules, etc. `_legacy/` is also skipped
    unless `include_legacy=True` is passed (legacy files often have
    intentional historical drift we don't want to flag in routine ops).
    """
    skip_set = set(skip)
    if not include_legacy:
        skip_set.add("_legacy")

    for f in sorted(root.rglob("*.md")):
        rel = f.relative_to(root)
        if any(part in skip_set for part in rel.parts):
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        fm, body = parse_frontmatter(text)
        fm_tags_raw = fm.fields.get("tags")
        fm_tags: list[str] = []
        if isinstance(fm_tags_raw, list):
            fm_tags = [str(t) for t in fm_tags_raw if t]
        elif isinstance(fm_tags_raw, str) and fm_tags_raw.strip():
            fm_tags = [fm_tags_raw.strip()]
        yield VaultFile(
            path=f,
            rel_path=rel,
            frontmatter=fm,
            body=body,
            tags_frontmatter=fm_tags,
            tags_inline=extract_inline_tags(body),
            wikilinks=extract_wikilinks(body),
            markdown_md_links=extract_markdown_md_links(body),
        )


# ============================================================
# Vault index for wikilink resolution
# ============================================================


def build_vault_index(vault_root: Path) -> set[str]:
    """All resolvable wikilink target forms across the vault.

    Includes:
      - relative path with extension
      - relative path without extension
      - bare basename (Obsidian default match if unique)
    Spans .md, .canvas, .base.
    """
    index: set[str] = set()
    for ext in ("md", "canvas", "base"):
        for f in vault_root.rglob(f"*.{ext}"):
            try:
                rel = f.relative_to(vault_root)
            except ValueError:
                continue
            s = str(rel)
            index.add(s)
            index.add(s[: -(len(ext) + 1)])  # strip `.ext`
            index.add(f.stem)
            index.add(f.name)
    return index


def resolve_wikilink(target: str, index: set[str]) -> bool:
    """True if target resolves in the vault index.

    Tries (in order): exact path, path+.md, basename, basename+.md.
    The basename fallback matches Obsidian's default resolution: `[[foo]]`
    resolves to any `foo.md` anywhere in the vault.
    """
    if not target:
        return False
    if target in index:
        return True
    if (target + ".md") in index:
        return True
    # Basename fallback (Obsidian default resolution)
    base = target.replace("\\", "/").rstrip("/").split("/")[-1]
    if base != target:
        if base in index:
            return True
        if (base + ".md") in index:
            return True
    return False


def is_checkable_wikilink(wl: Wikilink) -> bool:
    """True if this wikilink can be validated against the vault index.

    Not checkable (and therefore never "broken"):
      - embeds (``![[image.png]]``) — attachments aren't indexed
      - empty targets (``[[#Heading]]``) — same-file heading links
      - targets with a non-md/canvas/base extension — attachments by name
    """
    if wl.is_embed:
        return False
    if not wl.target:
        return False
    lower = wl.target.lower()
    if "." in lower.rsplit("/", 1)[-1] and not lower.endswith(INDEXABLE_LINK_EXTS):
        return False
    return True


# ============================================================
# Breadcrumb + vault resolution (port.py patterns)
# ============================================================


def parse_breadcrumb(project_root: Path) -> Optional[dict]:
    """Read .claude/adjudant breadcrumb (key:value, one per line).

    Legacy pre-v0.4.0 `key=value` form is tolerated — every other breadcrumb
    parser (hooks, shell sed) accepts it, and this one feeds resolve_vault's
    vault_path/vault_name steps, which would otherwise go dead on a legacy
    breadcrumb whose absolute path is stale on this machine.
    """
    bc = project_root / ".claude" / "adjudant"
    if not bc.is_file():
        return None
    out: dict[str, str] = {}
    for line in bc.read_text().splitlines():
        m = re.match(r"^\s*([A-Za-z_][\w-]*)\s*[:=]\s*(.+?)\s*$", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def _candidate_vault_paths(vault_name: str) -> list[Path]:
    """Standard macOS locations where an Obsidian vault named `vault_name`
    might live. Used as a cross-machine portability fallback when an
    absolute `vault_path` in the breadcrumb doesn't resolve on this user."""
    home = Path.home()
    candidates = [
        home / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / vault_name,
        # Generic iCloud Drive (vault stored outside the Obsidian app container)
        home / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / vault_name,
        home / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Obsidian" / vault_name,
        home / "Documents" / vault_name,
        home / "Documents" / "Obsidian" / vault_name,
        home / "Obsidian" / vault_name,
        home / "Dropbox" / "Obsidian" / vault_name,  # legacy pre-CloudStorage mount
    ]
    # Modern provider mounts: ~/Library/CloudStorage/<Provider>/[Obsidian/]<name>
    cloud_storage = home / "Library" / "CloudStorage"
    if cloud_storage.is_dir():
        try:
            for provider in sorted(cloud_storage.iterdir()):
                if provider.is_dir():
                    candidates.append(provider / vault_name)
                    candidates.append(provider / "Obsidian" / vault_name)
        except OSError:
            pass
    return candidates


def resolve_vault(
    project_root: Path,
    env_vault: Optional[str] = None,
) -> Optional[Path]:
    """5-step resolution:
      1. env var override (OB_VAULT or passed env_vault)
      2. .claude/adjudant breadcrumb `vault_path` field (absolute, current machine)
      3. .claude/adjudant breadcrumb `vault_name` field → standard locations
         under THIS machine's $HOME (cross-machine portability)
      4. .claude/obsidian-bridge legacy breadcrumb `vault:` field
      5. walk up parents for `Home.md` with `type: vault-home`
    """
    # 1. Env var override (explicit param wins; OB_VAULT read when not passed)
    if env_vault is None:
        env_vault = os.environ.get("OB_VAULT")
    if env_vault:
        p = Path(env_vault).expanduser()
        if p.is_dir():
            return p

    # 2. adjudant breadcrumb absolute vault_path
    bc = parse_breadcrumb(project_root)
    if bc and "vault_path" in bc:
        p = Path(bc["vault_path"]).expanduser()
        if p.is_dir():
            return p

    # 3. adjudant breadcrumb vault_name (cross-machine portability)
    if bc and "vault_name" in bc:
        for cand in _candidate_vault_paths(bc["vault_name"]):
            if cand.is_dir():
                return cand

    # 4. legacy OB breadcrumb
    ob = project_root / ".claude" / "obsidian-bridge"
    if ob.is_file():
        for line in ob.read_text().splitlines():
            m = re.match(r"^\s*vault\s*:\s*(.+?)\s*$", line)
            if m:
                p = Path(m.group(1)).expanduser()
                if p.is_dir():
                    return p

    # 5. Walk up for Home.md
    cur = project_root.resolve()
    while cur != cur.parent:
        home = cur / "Home.md"
        if home.is_file():
            try:
                text = home.read_text(errors="replace")
                if re.search(r"^type:\s*vault-home", text, re.MULTILINE):
                    return cur
            except OSError:
                pass
        cur = cur.parent
    return None


@dataclass
class ProjectContext:
    """Resolved adjudant project — links code-side root to vault project."""
    code_root: Path
    vault_path: Path
    slug: str
    vault_project_dir: Path

    @property
    def is_connected(self) -> bool:
        return self.vault_project_dir.is_dir()


def resolve_project_from_cwd(cwd: Optional[Path] = None) -> Optional[ProjectContext]:
    """Read `.claude/adjudant` at cwd (or given dir), resolve the vault,
    return a `ProjectContext`. None if no breadcrumb or vault unresolvable.

    Used by check/tidy/ramasse_scan/sync to auto-follow the breadcrumb
    when invoked from the code-side project root.
    """
    root = Path(cwd) if cwd else Path.cwd()
    root = root.expanduser().resolve()
    bc = parse_breadcrumb(root)
    if not bc or "slug" not in bc:
        return None
    vault = resolve_vault(root)
    if not vault:
        return None
    vpd = find_project_dir(vault, bc["slug"]) or (vault / "projects" / bc["slug"])
    return ProjectContext(
        code_root=root,
        vault_path=vault,
        slug=bc["slug"],
        vault_project_dir=vpd,
    )


class VaultUnresolvableError(RuntimeError):
    """A `.claude/adjudant` breadcrumb exists but the vault cannot be resolved.

    Raised instead of falling back to the code repo as the scan dir — that
    fallback would let write-path verbs (tidy apply) rewrite the repository.
    """


def smart_project_dir(project_dir_arg: str) -> tuple[Path, Optional[Path]]:
    """Resolve `--project-dir` smartly across helpers.

    Returns (project_scan_dir, vault_dir_hint).

    - If the arg points at a directory containing `.claude/adjudant`:
      treat it as a code root, follow the breadcrumb, return the vault
      project dir + vault path. If the breadcrumb is present but the vault
      cannot be resolved, raise VaultUnresolvableError — never fall back to
      scanning the code repo itself.
    - Otherwise: treat the arg as already-the-vault-project-dir,
      return it unchanged + try to resolve the vault upward.

    Backward-compatible: code that passed a vault project path still works.
    """
    arg_path = Path(project_dir_arg).expanduser().resolve()
    breadcrumb = arg_path / ".claude" / "adjudant"
    if breadcrumb.is_file():
        ctx = resolve_project_from_cwd(arg_path)
        if ctx is not None and ctx.is_connected:
            return ctx.vault_project_dir, ctx.vault_path
        if ctx is not None and not ctx.is_connected:
            # Breadcrumb exists but vault project dir missing — surface the
            # intended path so callers can error out with a clear message.
            return ctx.vault_project_dir, ctx.vault_path
        raise VaultUnresolvableError(
            f"breadcrumb at {breadcrumb} exists but the vault could not be resolved "
            f"(bad slug or vault_path/vault_name points nowhere on this machine). "
            f"Fix the breadcrumb or re-run /adjudant connect."
        )
    # Treat as vault project path directly
    return arg_path, None


# ============================================================
# Schema constants — single source of truth (imported by dream + tidy)
# ============================================================


BUCKET_A_TYPES: frozenset[str] = frozenset({
    "decision", "session", "note", "doc", "project", "handoff",
    "index", "iteration", "release", "source", "dream-report", "task",
})
BUCKET_A_TYPES_PLUS_HOME: frozenset[str] = BUCKET_A_TYPES | {"vault-home"}

# Bucket B — custom file types migrated from cabinet/*
BUCKET_B_MIGRATIONS: dict[str, str] = {
    "cabinet/recon": "recon-item",
    "cabinet/portal-concept": "portal-concept",
    "cabinet/preview": "preview",
    "cabinet/asset-index": "index",
    "cabinet/dev-doc": "doc",
    "cabinet/decision": "decision",
}

# Bucket D — tags to drop entirely
BUCKET_D_TAG_PREFIXES: tuple[str, ...] = ("ob/",)

VAGUE_TOPICAL_TAGS: frozenset[str] = frozenset({
    "architecture", "architecture-lockin", "architecture-source",
    "frontend", "cms", "moc", "toolbox", "scheduler",
    "campaign-request", "flow-c", "nightly", "hubspot",
    "reconciler",
})

CREW_NAMES: frozenset[str] = frozenset({
    "bostrol", "kevijntje", "henske", "jonasty",
})

# Project-type tag form is forbidden — it lives in frontmatter `project_type:`
PROJECT_TYPE_TAGS: frozenset[str] = frozenset({
    "type/coding", "type/knowledge", "type/plugin", "type/tinkerage",
})

BUCKET_D_TAG_EXACT: frozenset[str] = VAGUE_TOPICAL_TAGS | CREW_NAMES | PROJECT_TYPE_TAGS

# Other cabinet/* tags — drop unless in BUCKET_B_MIGRATIONS keys
_BUCKET_B_KEYS = frozenset(BUCKET_B_MIGRATIONS.keys())

# Per-project_type folder defaults (must align with vault-standards.md §5)
PROJECT_TYPE_DEFAULT_FOLDERS: dict[str, dict[str, list[str]]] = {
    "coding": {
        "with_index": ["decisions", "notes", "tasks", "references"],
        "no_index": ["sessions", "images"],
    },
    "plugin": {
        "with_index": ["decisions", "notes", "tasks", "references", "releases"],
        "no_index": ["sessions", "images"],
    },
    "knowledge": {
        "with_index": ["notes", "sources", "references"],
        "no_index": ["sessions"],
    },
    "tinkerage": {
        "with_index": [],
        "no_index": ["sessions"],
    },
}

AUTO_CREATED_FOLDERS: frozenset[str] = frozenset({"dreams", "canvases", "bases", "board"})
INDEX_EXEMPT_FOLDERS: frozenset[str] = frozenset({
    "sessions", "images", "assets", "previews", "iterations", "_archive", "templates",
})


# ============================================================
# Project status lifecycle + zones (locked 2026-07-16)
# ============================================================

PROJECT_STATUS_VALUES: tuple[str, ...] = ("active", "stale", "fridge", "done", "dead", "seed")
ZONE_FOR_STATUS: dict[str, str] = {
    "active": "", "stale": "", "seed": "",
    "fridge": "_fridge", "done": "_archive", "dead": "_archive",
}
PROJECT_ZONES: tuple[str, ...] = ("", "_fridge", "_archive")
DEFAULT_STALE_DAYS = 30
FRIDGE_NUDGE_DAYS = 180


# ============================================================
# Note-level frontmatter schema (locked 2026-07-27)
# ============================================================

DECISION_STATUS_VALUES: tuple[str, ...] = (
    "active", "superseded", "reversed", "implemented", "deferred")
TASK_STATUS_VALUES: tuple[str, ...] = (
    "todo", "doing", "review", "blocked", "done", "icebox")
ITERATION_STATUS_VALUES: tuple[str, ...] = (
    "drafting", "on-shelf", "picked", "parked", "rejected", "superseded")

# Types whose `status:` value is an enum. Everything else has no status field.
STATUS_VALUES_FOR_TYPE: dict[str, tuple[str, ...]] = {
    "decision": DECISION_STATUS_VALUES,
    "task": TASK_STATUS_VALUES,
    "project": PROJECT_STATUS_VALUES,
    "iteration": ITERATION_STATUS_VALUES,
}

# Per Bucket-A type: required keys must be present; required | optional is the
# full legal key set — any other key is an unknown field (drift). `project` is
# deliberately absent everywhere: membership is the path. `source_session` is
# optional wherever the stamp hook could historically write it, so old stamps
# never read as drift.
# Descriptive fields legal on every content type (not on system shapes:
# session, handoff, index, project, vault-home). Widened 2026-07-27 so tidy
# never strips real-world metadata Tom actually writes.
_CONTENT_OPTIONAL: frozenset[str] = frozenset({
    "related", "title", "name", "description",
})

FIELD_SCHEMA: dict[str, dict[str, frozenset[str]]] = {
    "decision": {
        "required": frozenset({"type", "status", "date", "tags"}),
        "optional": frozenset({"supersedes", "superseded_by",
                               "implemented_verified", "source_session"})
                    | _CONTENT_OPTIONAL,
    },
    "session": {
        "required": frozenset({"type", "date", "started", "session_id", "tags"}),
        "optional": frozenset(),
    },
    "note": {
        "required": frozenset({"type", "created", "updated", "tags"}),
        "optional": frozenset({"superseded_by", "source_session"}) | _CONTENT_OPTIONAL,
    },
    "doc": {
        "required": frozenset({"type", "title", "updated", "tags"}),
        "optional": frozenset({"superseded_by", "source_session"})
                    | (_CONTENT_OPTIONAL - {"title"}),
    },
    "handoff": {
        # session_id and future custom keys are legal here: the sync mirror
        # (_handoff_freshness.preserved_frontmatter) contractually preserves
        # them, so tidy must not stage them for stripping.
        "required": frozenset({"type", "updated", "source", "tags"}),
        "optional": frozenset({"created", "session_id"}),
    },
    "task": {
        # `id` is card identity: board.py reads it (cards_from_tasks) and a
        # reseed re-keys the card to the file stem if it disappears, losing
        # the user's dragged column. Never strippable.
        "required": frozenset({"type", "status", "tags"}),
        "optional": frozenset({"category", "code", "id", "note", "source_session"})
                    | _CONTENT_OPTIONAL,
    },
    "release": {
        "required": frozenset({"type", "version", "date", "tags"}),
        "optional": frozenset({"source_session"}) | _CONTENT_OPTIONAL,
    },
    "source": {
        "required": frozenset({"type", "title", "tags"}),
        "optional": frozenset({"author", "url", "medium", "year", "source_session"})
                    | (_CONTENT_OPTIONAL - {"title"}),
    },
    "iteration": {
        "required": frozenset({"type", "identifier", "status", "date", "tags"}),
        "optional": frozenset({"track", "register", "supersedes", "builds_on",
                               "artefacts", "source_session"}) | _CONTENT_OPTIONAL,
    },
    "dream-report": {
        "required": frozenset({"type", "date", "tags"}),
        "optional": frozenset({"source_session"}) | _CONTENT_OPTIONAL,
    },
    "project": {
        "required": frozenset({"type", "project_type", "slug", "aliases",
                               "status", "created", "updated", "tags"}),
        "optional": frozenset({"repo", "stack", "marketplace", "extra_folders",
                               "relations", "codename"}),
    },
    "index": {
        "required": frozenset({"type", "tags"}),
        "optional": frozenset({"updated"}),
    },
    "vault-home": {
        "required": frozenset({"type", "updated"}),
        "optional": frozenset(),
    },
}

# The kebab-case project-slug rule. Lives here (not in connect.py) because the
# BREADCRUMB IS A REPO-COMMITTED FILE: a cloned repo can carry any slug, and
# hooks interpolate it into mkdir/write paths and into SessionStart stdout,
# which is injected into the model's context. Every consumer of a breadcrumb
# slug must gate on is_safe_slug before building a path from it.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SLUG_MAX_LEN = 64


def is_safe_slug(slug: object) -> bool:
    """True when `slug` is a kebab-case project slug safe to put in a path.

    Rejects traversal (`../`), absolute paths, separators, whitespace, shell
    and markdown metacharacters, empty values, and anything over
    SLUG_MAX_LEN. Non-str input is rejected rather than coerced.
    """
    if not isinstance(slug, str) or not slug or len(slug) > SLUG_MAX_LEN:
        return False
    return SLUG_RE.match(slug) is not None


def safe_project_root(vault: Path, slug: str) -> Optional[Path]:
    """`{vault}/projects/{slug}` only when slug is safe AND the result stays
    inside the vault. None otherwise, so callers fail closed.

    Zone-unaware by design (active zone only) - callers wanting _fridge /
    _archive should use find_project_dir. This is the containment guard.
    """
    if not is_safe_slug(slug):
        return None
    try:
        vault_r = Path(vault).expanduser().resolve()
        candidate = (vault_r / "projects" / slug).resolve()
    except (OSError, ValueError):
        return None
    if candidate != vault_r and vault_r not in candidate.parents:
        return None
    return candidate


# Wild historical decision-status values that are plain synonyms of active.
# tidy migrates these after preview; anything else off-enum is reported only.
DECISION_STATUS_ALIASES: dict[str, str] = {
    "accepted": "active", "locked": "active", "current": "active",
}


def schema_drift_for_file(vf: "VaultFile", aliases: Optional[set] = None) -> Optional[dict]:
    """Schema drift for one file per FIELD_SCHEMA, or None when clean.

    Only files with a parsed frontmatter block and a canonical type are
    checked; everything else is ramasse territory (detect_frontmatter_drift,
    detect_type_drift) and returns None here. `aliases` is the task-status
    alias set (board.STATUS_TO_COLUMN keys) used to mark task values as
    normalizable; decision values normalize via DECISION_STATUS_ALIASES.
    """
    fm = vf.frontmatter
    ftype = vf.file_type
    if not fm.has_block or fm.parse_error or ftype not in FIELD_SCHEMA:
        return None
    spec = FIELD_SCHEMA[ftype]
    keys = set(fm.fields)
    out: dict[str, Any] = {}
    missing = spec["required"] - keys
    if missing:
        out["missing_required"] = sorted(missing)
    unknown = keys - spec["required"] - spec["optional"]
    if unknown:
        out["unknown_fields"] = sorted(unknown)
    enum = STATUS_VALUES_FOR_TYPE.get(ftype)
    if enum is not None:
        status = fm.fields.get("status")
        if isinstance(status, str) and status and status not in enum:
            if ftype == "task" and aliases and status in aliases:
                pass  # accepted input per the alias table; the board normalizes lanes on read
            else:
                normalizable = ftype == "decision" and status in DECISION_STATUS_ALIASES
                out["status_invalid"] = {"value": status, "normalizable": normalizable}
    if "node_type" in keys and "type" in keys:
        out["type_conflict"] = True
    if not out:
        return None
    out["file"] = str(vf.rel_path)
    out["type"] = ftype
    return out


def schema_drift(files: list["VaultFile"], aliases: Optional[set] = None) -> dict[str, Any]:
    """Aggregate schema drift across walked files: counts + capped samples."""
    flagged: list[dict] = []
    checked = 0
    unchecked = 0
    for vf in files:
        fm = vf.frontmatter
        if not fm.has_block or fm.parse_error or vf.file_type not in FIELD_SCHEMA:
            unchecked += 1
            continue
        checked += 1
        d = schema_drift_for_file(vf, aliases)
        if d:
            flagged.append(d)
    return {
        "checked": checked,
        "unchecked": unchecked,
        "flagged": len(flagged),
        "counts": {
            "missing_required": sum(1 for d in flagged if "missing_required" in d),
            "unknown_fields": sum(1 for d in flagged if "unknown_fields" in d),
            "status_invalid": sum(1 for d in flagged if "status_invalid" in d),
            "type_conflict": sum(1 for d in flagged if "type_conflict" in d),
        },
        "samples": flagged[:20],
    }


_DATED_STEM_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def newest_dated_stem(folder: Path) -> Optional[str]:
    """Most recent valid YYYY-MM-DD stem prefix among .md files in folder.

    Calendar-validates each candidate: a malformed stem like 2026-99-01 is
    skipped rather than lexicographically beating a valid older date. None
    only when no valid dated stem exists.
    """
    if not folder.is_dir():
        return None
    dates: list[str] = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix == ".md":
            m = _DATED_STEM_RE.match(f.stem)
            if m:
                try:
                    datetime.strptime(m.group(1), "%Y-%m-%d")
                except ValueError:
                    continue
                dates.append(m.group(1))
    return max(dates) if dates else None


def suggest_status(
    declared: Optional[str],
    project_dir: Path,
    today: date,
    stale_after_days: int = DEFAULT_STALE_DAYS,
) -> dict[str, Any]:
    """Machine suggestion along the active/stale axis ONLY.

    fridge gets a nudge string after FRIDGE_NUDGE_DAYS; seed, done, dead are
    never suggested away. An invalid declared value is flagged
    (declared_valid=False) and treated as active for suggestion purposes.
    Never writes.
    """
    last = newest_dated_stem(project_dir / "sessions")
    days_quiet: Optional[int] = None
    if last:
        try:
            days_quiet = (today - datetime.strptime(last, "%Y-%m-%d").date()).days
        except ValueError:
            days_quiet = None
    valid = declared in PROJECT_STATUS_VALUES
    effective = declared if valid else "active"
    out: dict[str, Any] = {
        "declared": declared,
        "declared_valid": valid,
        "last_session": last,
        "days_quiet": days_quiet,
        "suggested": None,
        "reason": None,
        "nudge": None,
    }
    if effective == "active" and days_quiet is not None and days_quiet >= stale_after_days:
        out["suggested"] = "stale"
        out["reason"] = f"{days_quiet} days without a session note (threshold {stale_after_days})"
    elif effective == "stale" and days_quiet is not None and days_quiet < stale_after_days:
        out["suggested"] = "active"
        out["reason"] = f"session activity {days_quiet} days ago (threshold {stale_after_days})"
    elif effective == "fridge" and days_quiet is not None and days_quiet >= FRIDGE_NUDGE_DAYS:
        out["nudge"] = f"in the fridge {days_quiet} days, still intentional?"
    return out


def find_project_dir(vault: Path, slug: str) -> Optional[Path]:
    """Locate a project across zones. Prefers a dir containing brief.md."""
    candidates = [
        (vault / "projects" / zone / slug) if zone else (vault / "projects" / slug)
        for zone in PROJECT_ZONES
    ]
    for c in candidates:
        if (c / "brief.md").is_file():
            return c
    for c in candidates:
        if c.is_dir():
            return c
    return None


def zone_of(project_dir: Path) -> str:
    """'' | '_fridge' | '_archive' from the path shape projects[/zone]/slug."""
    parent = project_dir.parent.name
    return parent if parent in ("_fridge", "_archive") else ""


def zone_matches_status(status: Optional[str], zone: str) -> bool:
    """True when the folder zone agrees with the declared status.

    Unknown status values return True: the vocabulary problem is reported
    separately (declared_valid), not double-counted as a zone mismatch.
    """
    if status not in PROJECT_STATUS_VALUES:
        return True
    return ZONE_FOR_STATUS[status] == zone


def enumerate_projects_all_zones(vault: Path) -> list[tuple[str, Path, str]]:
    """Every project (slug, dir, zone) across projects/, _fridge/, _archive/.

    A project is a directory containing brief.md. Leading-underscore and dot
    dirs are skipped inside each zone. Sorted by zone order then slug.
    """
    out: list[tuple[str, Path, str]] = []
    base = vault / "projects"
    for zone in PROJECT_ZONES:
        zdir = (base / zone) if zone else base
        if not zdir.is_dir():
            continue
        for d in sorted(zdir.iterdir(), key=lambda p: p.name):
            if not d.is_dir() or d.name.startswith("_") or d.name.startswith("."):
                continue
            if (d / "brief.md").is_file():
                out.append((d.name, d, zone))
    return out


def is_bucket_d_tag(tag: str, project_slug: Optional[str] = None) -> bool:
    """Return True if tag should be dropped per Bucket D."""
    # ob/* prefix
    if any(tag.startswith(p) for p in BUCKET_D_TAG_PREFIXES):
        return True
    # cabinet/* — drop unless in Bucket B migrations
    if tag.startswith("cabinet/") and tag not in _BUCKET_B_KEYS:
        return True
    # Exact match (vague topicals, crew, project-type tags)
    if tag in BUCKET_D_TAG_EXACT:
        return True
    # Project-slug self-tag and slug/* / slug-* variants
    if project_slug:
        if tag == project_slug:
            return True
        if tag.startswith(project_slug + "/"):
            return True
        if tag.startswith(project_slug + "-"):
            return True
    return False


def is_bucket_b_migration(tag: str) -> Optional[str]:
    """If tag is a Bucket B migration source, return the target tag; else None."""
    return BUCKET_B_MIGRATIONS.get(tag)


# ============================================================
# CLI smoke-test (read-only — the module never writes)
# ============================================================


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="_vault_walk.py",
        description="Vault-walk primitives — read-only smoke test.",
    )
    parser.add_argument("--project-dir", required=True, help="Project root to walk")
    parser.add_argument("--vault-dir", help="Vault root for wikilink resolution")
    parser.add_argument("--include-legacy", action="store_true", help="Walk into _legacy/")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human format")
    args = parser.parse_args(argv)

    project_dir = Path(args.project_dir).expanduser().resolve()
    vault_dir = Path(args.vault_dir).expanduser().resolve() if args.vault_dir else None

    if not project_dir.is_dir():
        print(f"error: --project-dir not found: {project_dir}", file=sys.stderr)
        return 1

    files = list(walk_project(project_dir, include_legacy=args.include_legacy))
    parse_errors = [
        {"file": str(f.rel_path), "error": f.frontmatter.parse_error}
        for f in files if f.frontmatter.parse_error
    ]
    no_fm = [str(f.rel_path) for f in files if not f.frontmatter.has_block]

    tag_counter: Counter[str] = Counter()
    for f in files:
        for t in f.tags:
            tag_counter[t] += 1

    type_counter: Counter[str] = Counter()
    for f in files:
        t = f.file_type
        if t:
            type_counter[t] += 1

    total_wl = sum(len(f.wikilinks) for f in files)
    broken_wl = 0
    md_link_violations = sum(len(f.markdown_md_links) for f in files)
    if vault_dir and vault_dir.is_dir():
        idx = build_vault_index(vault_dir)
        for f in files:
            for wl in f.wikilinks:
                if is_checkable_wikilink(wl) and not resolve_wikilink(wl.target, idx):
                    broken_wl += 1

    output: dict[str, Any] = {
        "project_dir": str(project_dir),
        "vault_dir": str(vault_dir) if vault_dir else None,
        "files_scanned": len(files),
        "files_no_frontmatter": no_fm[:10],
        "parse_errors": parse_errors[:10],
        "tag_inventory_top30": tag_counter.most_common(30),
        "type_inventory": type_counter.most_common(),
        "wikilinks_total": total_wl,
        "wikilinks_broken": broken_wl,
        "markdown_md_link_violations": md_link_violations,
    }

    if args.json:
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"project:        {project_dir}")
        print(f"vault:          {vault_dir or '(not specified)'}")
        print(f"files:          {len(files)}")
        print(f"no frontmatter: {len(no_fm)}")
        print(f"parse errors:   {len(parse_errors)}")
        print(f"wikilinks:      {total_wl} total, {broken_wl} broken")
        print(f"md-link violations: {md_link_violations}")
        if type_counter:
            print(f"\ntype inventory:")
            for t, n in type_counter.most_common():
                marker = " " if t in BUCKET_A_TYPES_PLUS_HOME else "*"
                print(f"  {marker} {n:4}  {t}")
        if tag_counter:
            print(f"\ntop 30 tags:")
            for tag, n in tag_counter.most_common(30):
                print(f"  {n:4}  {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
