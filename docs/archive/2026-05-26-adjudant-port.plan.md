# adjudant port verb Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `/adjudant:adjudant port` — a universal verb that migrates any legacy project (raw repo, obsidian-bridge legacy, or hand-authored AGENTS.md) into adjudant compliance via a safe two-phase preview → apply flow with hybrid deterministic + AI merge.

**Architecture:** Python `scripts/port.py` handles all mechanical work (detection, OB section mapping, vault folder operations, backup creation, preview scaffolding, phase 2 apply). The skill router file `reference/port.md` orchestrates `port.py` calls and provides the AI-classifier instructions Claude follows for the hand-authored (Z) flavor. Three new validators in `validate.py` enforce port-directory coherence at pre-commit time.

**Tech Stack:** Python 3.10+ stdlib only (unittest for tests — no new deps), bash for git operations, markdown + JSON for templates/metadata. Pre-commit hook chain via `.pre-commit-config.yaml`.

**Spec reference:** `docs/superpowers/2026-05-26-adjudant-port.design.md`

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `adjudant/scripts/port.py` | NEW | Mechanical: detection, OB mapping, folder ops, backups, preview/apply |
| `adjudant/scripts/test_port.py` | NEW | unittest tests for port.py |
| `adjudant/skills/adjudant/reference/port.md` | NEW | Claude runbook (phase decision, AI classifier for Z, error handling) |
| `adjudant/skills/adjudant/SKILL.md` | MODIFY | Add `port` row to verb router table |
| `adjudant/scripts/command-metadata.json` | MODIFY | Add `port` entry to verbs array |
| `adjudant/scripts/validate.py` | MODIFY | Add 3 new validators (port-preview-coherence, port-backup-integrity, gitignore-includes-port-dirs) |
| `adjudant/.claude-plugin/plugin.json` | MODIFY | Bump version 0.1.2 → 0.2.0 |
| `.claude-plugin/marketplace.json` | MODIFY | Bump adjudant 0.1.2 → 0.2.0; marketplace 1.1.2 → 1.2.0 |

**Decomposition rationale:** `port.py` is a single file because all the mechanical functions are tightly related and share helpers (path utilities, breadcrumb format, etc.). `reference/port.md` is the Claude-facing runbook — separate concern. `test_port.py` is paired one-to-one with `port.py` per stdlib convention. Validators live in the existing `validate.py` (additive). Versioning files are touched last.

---

## Conventions for this plan

- All paths absolute or repo-rooted: repo root = `/Users/tomvanderhegden/Library/CloudStorage/OneDrive-zenatech.com/Documents/ZenaTech CC Space/Remote Plugin Bench/onnozelaer-claude-plugins/`. In commands shown below, `cd "$REPO"` assumes the repo root.
- All Python: standard library only. No pip installs.
- Tests use `unittest` (stdlib). Run via `python3 -m unittest adjudant.scripts.test_port -v`.
- Commit messages follow conventional commits per AGENTS.md: `feat(adjudant):`, `test(adjudant):`, etc. Each commit ends with `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- TDD discipline: write failing test → run + see fail → minimal implementation → run + see pass → commit. **Do not skip the run-and-see-fail step.**

---

## Task 1: port.py skeleton + first test (detect_flavor for X)

**Files:**
- Create: `adjudant/scripts/port.py`
- Create: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Create the empty test file with first failing test**

Write `adjudant/scripts/test_port.py`:

```python
"""Tests for adjudant/scripts/port.py."""

import tempfile
import unittest
from pathlib import Path

from port import detect_flavor


class TestDetectFlavor(unittest.TestCase):
    def test_raw_repo_returns_x(self):
        """An empty project dir (no breadcrumb, no AGENTS.md) is flavor X."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_flavor(Path(tmp)), "X")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: `ModuleNotFoundError: No module named 'port'` (or `ImportError`).

- [ ] **Step 3: Create the minimal port.py to make the test pass**

Write `adjudant/scripts/port.py`:

```python
#!/usr/bin/env python3
"""Adjudant port verb — migrate legacy projects to adjudant compliance.

Run from the project root (or via `python3 adjudant/scripts/port.py`).
Detects project flavor (X/Y/Z) or port phase (preview/applied) and
dispatches accordingly. See docs/superpowers/2026-05-26-adjudant-port.design.md.
"""

from pathlib import Path


def detect_flavor(project_root: Path) -> str:
    """Detect the legacy flavor of a project.

    Returns one of: "X" (raw repo), "Y" (obsidian-bridge legacy),
    "Z" (hand-authored AGENTS.md/CLAUDE.md), "preview" (port preview
    pending apply), "applied" (already ported).
    """
    return "X"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: `test_raw_repo_returns_x ... ok` and `OK` summary line.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): port.py skeleton + first detect_flavor test

Returns "X" (raw repo) as the trivial baseline. Other flavors
(Y, Z, preview, applied) added in subsequent tasks via TDD.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: detect_flavor for preview + applied states

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing tests for preview + applied detection**

Append to `adjudant/scripts/test_port.py` (inside `TestDetectFlavor`):

```python
    def test_preview_dir_present_returns_preview(self):
        """If .adjudant-port-preview/ exists, flavor is 'preview' (phase 2)."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".adjudant-port-preview").mkdir()
            self.assertEqual(detect_flavor(Path(tmp)), "preview")

    def test_applied_state_returns_applied(self):
        """Backup dir + compliant project (breadcrumb + AGENTS.md starting with project header) → 'applied'."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".adjudant-port-backup").mkdir()
            (root / ".claude").mkdir()
            (root / ".claude" / "adjudant").write_text("vault_path: /tmp/v\nvault_name: v\nslug: x\nmode: project\n")
            (root / "AGENTS.md").write_text("# Test Project\n\n`x` · type: `coding` · vault: [[projects/x/brief|x]]\n")
            (root / "CLAUDE.md").write_text("@AGENTS.md\n\n# Claude-specific overrides\n")
            self.assertEqual(detect_flavor(root), "applied")
```

- [ ] **Step 2: Run tests to verify the two new ones fail**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: `test_preview_dir_present_returns_preview ... FAIL` (got 'X' expected 'preview'); `test_applied_state_returns_applied ... FAIL`. Old test still passes.

- [ ] **Step 3: Implement preview + applied detection in port.py**

Replace `detect_flavor` in `adjudant/scripts/port.py`:

```python
def detect_flavor(project_root: Path) -> str:
    """Detect the legacy flavor or port phase of a project.

    Returns: "X", "Y", "Z", "preview", or "applied".
    Order matters — preview/applied are checked before legacy markers.
    """
    if (project_root / ".adjudant-port-preview").is_dir():
        return "preview"

    if (project_root / ".adjudant-port-backup").is_dir() and _is_adjudant_compliant(project_root):
        return "applied"

    return "X"


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
```

- [ ] **Step 4: Run tests to verify all three pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 3 tests, all OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): detect_flavor handles preview + applied states

preview = .adjudant-port-preview/ present (phase 2 trigger).
applied = backup dir + project meets all four compliance criteria.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: detect_flavor for Y (obsidian-bridge legacy)

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing test for Y detection**

Append to `TestDetectFlavor` in `test_port.py`:

```python
    def test_obsidian_bridge_breadcrumb_returns_y(self):
        """If .claude/obsidian-bridge breadcrumb exists, flavor is Y."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text("vault: /tmp/v\nslug: legacy-proj\n")
            self.assertEqual(detect_flavor(root), "Y")
```

- [ ] **Step 2: Run tests, verify Y test fails**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 4 tests total; new test FAILS with 'X' returned instead of 'Y'.

- [ ] **Step 3: Add Y detection to detect_flavor**

In `port.py`, insert before the final `return "X"`:

```python
    if (project_root / ".claude" / "obsidian-bridge").is_file():
        return "Y"
```

- [ ] **Step 4: Run tests, verify all 4 pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 4 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): detect_flavor handles Y (obsidian-bridge legacy)

Y is identified by the presence of .claude/obsidian-bridge
breadcrumb. Checked after preview/applied per spec detection order.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: detect_flavor for Z (hand-authored)

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing tests for Z detection**

Append to `TestDetectFlavor`:

```python
    def test_hand_authored_agents_md_returns_z(self):
        """AGENTS.md with non-template content (no .claude/obsidian-bridge) is Z."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                "# My Custom Project\n\n## Stack\n- Node 22, pnpm\n\n## Conventions\n- Tabs not spaces\n"
            )
            self.assertEqual(detect_flavor(root), "Z")

    def test_template_shaped_agents_md_returns_x(self):
        """An AGENTS.md whose content matches the template (placeholders intact) is NOT Z; falls through to X."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Mirror first line of templates/AGENTS.md
            (root / "AGENTS.md").write_text(
                "# {Project Name}\n\n`{slug}` · type: `{coding|knowledge|plugin|tinkerage}` · vault: [[projects/{slug}/brief|{slug}]]\n\n> One-line purpose of this project.\n"
            )
            self.assertEqual(detect_flavor(root), "X")
```

- [ ] **Step 2: Run tests, verify the two new ones fail**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 6 tests; `test_hand_authored_agents_md_returns_z` FAILS (got 'X' expected 'Z'); `test_template_shaped_agents_md_returns_x` passes by accident.

- [ ] **Step 3: Implement Z detection via template hash comparison**

In `port.py`, add a helper above `detect_flavor`:

```python
import hashlib

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
```

Then in `detect_flavor`, insert before the final `return "X"`:

```python
    agents = project_root / "AGENTS.md"
    claude = project_root / "CLAUDE.md"
    if agents.is_file() and not _looks_like_template(agents):
        return "Z"
    if claude.is_file() and claude.read_text().strip() and \
            next((ln.strip() for ln in claude.read_text().splitlines() if ln.strip()), "") != "@AGENTS.md":
        return "Z"
```

- [ ] **Step 4: Run tests, verify all 6 pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 6 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): detect_flavor handles Z (hand-authored AGENTS/CLAUDE)

Z is identified by AGENTS.md or CLAUDE.md present with non-template
content. Template detection uses sentinel lines from
templates/AGENTS.md to avoid false positives on fresh-scaffolded
projects.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Vault path resolution

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing tests for vault path resolution**

Append to `test_port.py` (new test class):

```python
import os
from port import resolve_vault_path


class TestResolveVaultPath(unittest.TestCase):
    def test_ob_vault_env_var_wins(self):
        """OB_VAULT env var is preferred over any other resolution path."""
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["OB_VAULT"] = tmp
            try:
                self.assertEqual(resolve_vault_path(Path("/nonexistent")), Path(tmp))
            finally:
                del os.environ["OB_VAULT"]

    def test_existing_adjudant_breadcrumb_returns_its_vault(self):
        """If .claude/adjudant breadcrumb exists, its vault_path field is used."""
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "adjudant").write_text(
                f"vault_path: {vault}\nvault_name: v\nslug: x\nmode: project\n"
            )
            self.assertEqual(resolve_vault_path(root), Path(vault))

    def test_ob_breadcrumb_returns_its_vault(self):
        """For Y case: read vault from .claude/obsidian-bridge breadcrumb."""
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text(
                f"vault: {vault}\nslug: legacy-proj\n"
            )
            self.assertEqual(resolve_vault_path(root), Path(vault))

    def test_walk_up_finds_home_md_with_vault_home_frontmatter(self):
        """If parent dir contains Home.md with `type: vault-home` frontmatter, that dir is the vault."""
        with tempfile.TemporaryDirectory() as parent:
            vault_root = Path(parent)
            (vault_root / "Home.md").write_text("---\ntype: vault-home\n---\n\n# Vault\n")
            child = vault_root / "projects" / "myproject"
            child.mkdir(parents=True)
            self.assertEqual(resolve_vault_path(child), vault_root)

    def test_none_returned_when_unresolvable(self):
        """No env var, no breadcrumbs, no Home.md anywhere up → returns None."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(resolve_vault_path(Path(tmp)))
```

- [ ] **Step 2: Run tests, verify the new ones fail**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 5 new tests FAIL with `ImportError: cannot import name 'resolve_vault_path'`.

- [ ] **Step 3: Implement resolve_vault_path in port.py**

Add to `port.py`:

```python
import os
import re
from typing import Optional


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
    current = start.resolve()
    while current != current.parent:
        home = current / "Home.md"
        if home.is_file():
            text = home.read_text()
            # Look for `type: vault-home` in the YAML frontmatter block
            fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
            if fm_match and re.search(r"^\s*type\s*:\s*vault-home\s*$", fm_match.group(1), re.MULTILINE):
                return current
        current = current.parent
    return None
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: all tests OK (6 from previous + 5 new = 11 total).

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): resolve_vault_path with 4-tier fallback

OB_VAULT env → .claude/adjudant breadcrumb → .claude/obsidian-bridge
breadcrumb → walk parents for Home.md with type: vault-home. Returns
None when unresolvable; caller handles the prompt.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: OB section parser

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing tests for OB section parsing**

Append to `test_port.py`:

```python
from port import parse_markdown_sections


class TestParseMarkdownSections(unittest.TestCase):
    def test_simple_two_section_file(self):
        text = "# Title\n\nIntro\n\n## Working tree\n\nThis folder\n\n## Stack\n\nNode 22\n"
        sections = parse_markdown_sections(text)
        self.assertEqual(set(sections.keys()), {"working tree", "stack"})
        self.assertIn("This folder", sections["working tree"])
        self.assertIn("Node 22", sections["stack"])

    def test_headings_are_case_insensitive(self):
        text = "## WORKING TREE\n\nfoo\n## stack\n\nbar\n"
        sections = parse_markdown_sections(text)
        self.assertEqual(set(sections.keys()), {"working tree", "stack"})

    def test_h3_headings_also_captured(self):
        text = "## Top\n\n### Subheading\n\ncontent\n"
        sections = parse_markdown_sections(text)
        self.assertIn("top", sections)
        self.assertIn("subheading", sections)

    def test_empty_text_returns_empty_dict(self):
        self.assertEqual(parse_markdown_sections(""), {})
```

- [ ] **Step 2: Run tests, verify the new ones fail**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 4 new tests FAIL with ImportError.

- [ ] **Step 3: Implement parse_markdown_sections**

Add to `port.py`:

```python
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
```

- [ ] **Step 4: Run tests, verify all 15 pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 15 tests OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): parse_markdown_sections for OB legacy AGENTS.md parsing

Case-insensitive section heading capture for h2 and h3.
Foundation for the deterministic Y merge.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: OB → adjudant section mapping (Y merge)

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing tests for the OB → adjudant mapping**

Append to `test_port.py`:

```python
from port import map_ob_sections


class TestMapObSections(unittest.TestCase):
    def test_working_tree_maps_to_where_things_live_row(self):
        ob_sections = {"working tree": "/path/to/repo"}
        result = map_ob_sections(ob_sections)
        self.assertIn("/path/to/repo", result["where_things_live_extra_rows"])

    def test_stack_maps_to_conventions(self):
        ob_sections = {"stack": "Node 22, pnpm, Vite"}
        result = map_ob_sections(ob_sections)
        self.assertIn("Node 22, pnpm, Vite", result["conventions"])

    def test_vault_rules_dropped(self):
        ob_sections = {"vault rules": "Use [[Title|Alias]] form"}
        result = map_ob_sections(ob_sections)
        self.assertEqual(result["conventions"], "")
        self.assertEqual(result["where_things_live_extra_rows"], "")
        # The dropped content should be noted in the decisions log
        self.assertIn("vault rules", result["decisions"])
        self.assertIn("DROPPED", result["decisions"])

    def test_claude_instructions_moved_to_claude_md(self):
        ob_sections = {"claude instructions": "Always use /pnpm not /npm"}
        result = map_ob_sections(ob_sections)
        self.assertIn("Always use /pnpm not /npm", result["claude_md_body"])

    def test_what_this_is_preserved(self):
        ob_sections = {"what this is": "A tool that does X."}
        result = map_ob_sections(ob_sections)
        self.assertIn("A tool that does X.", result["what_this_is"])

    def test_unmatched_heading_goes_to_legacy_section(self):
        ob_sections = {"random heading": "Custom note"}
        result = map_ob_sections(ob_sections)
        self.assertIn("Custom note", result["from_legacy"])
        self.assertIn("random heading", result["from_legacy"])

    def test_aliases_work(self):
        ob_sections = {"purpose": "A tool."}
        result = map_ob_sections(ob_sections)
        self.assertIn("A tool.", result["what_this_is"])
```

- [ ] **Step 2: Run tests, verify they fail with ImportError**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 7 new failures, ImportError.

- [ ] **Step 3: Implement map_ob_sections**

Add to `port.py`:

```python
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
        else:
            # Append to the destination slot
            if result[slot]:
                result[slot] += "\n\n"
            result[slot] += body
            result["decisions"] += f'- OB "## {heading}" → adjudant "{slot}" (deterministic OB mapping)\n'

    return result
```

- [ ] **Step 4: Run tests, verify all 22 pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 22 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): map_ob_sections (Y deterministic merge)

Hardcoded mapping per spec — OB sections map to adjudant slots
(what_this_is, conventions, where_things_live row, claude_md_body,
or from_legacy catchall). Dropped sections (vault rules/layout)
logged in decisions for summary.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: AGENTS.md renderer

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing tests for render_agents_md**

Append to `test_port.py`:

```python
from port import render_agents_md


class TestRenderAgentsMd(unittest.TestCase):
    def test_basic_render_has_all_template_sections(self):
        result = render_agents_md(
            project_name="My Project",
            slug="my-project",
            project_type="coding",
            what_this_is="A tool that does X.",
            conventions="Tabs not spaces.",
            where_things_live_extra_rows="",
            from_legacy="",
        )
        self.assertIn("# My Project", result)
        self.assertIn("`my-project` · type: `coding`", result)
        self.assertIn("[[projects/my-project/brief|my-project]]", result)
        self.assertIn("A tool that does X.", result)
        self.assertIn("Tabs not spaces.", result)
        self.assertIn("## What this is", result)
        self.assertIn("## Where things live", result)
        self.assertIn("## Conventions", result)
        self.assertIn("## Vault is canonical", result)

    def test_from_legacy_section_appended_at_end(self):
        result = render_agents_md(
            project_name="P", slug="p", project_type="coding",
            what_this_is="", conventions="",
            where_things_live_extra_rows="",
            from_legacy="### custom\n\nSome content\n",
        )
        self.assertIn("## From legacy AGENTS.md", result)
        self.assertIn("Some content", result)
        # from_legacy should come AFTER the standard sections
        self.assertGreater(
            result.index("## From legacy AGENTS.md"),
            result.index("## Vault is canonical"),
        )

    def test_extra_rows_added_to_where_things_live_table(self):
        result = render_agents_md(
            project_name="P", slug="p", project_type="coding",
            what_this_is="", conventions="",
            where_things_live_extra_rows="| Custom path | `/foo/bar` |",
            from_legacy="",
        )
        self.assertIn("| Custom path | `/foo/bar` |", result)
        # Standard rows still present
        self.assertIn("| Working tree | (this folder) |", result)
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 3 new failures, ImportError.

- [ ] **Step 3: Implement render_agents_md**

Add to `port.py`:

```python
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

{what_this_is or '{Two to four sentences. Why this project exists, who it\\'s for, what success looks like.}'}

## Where things live

| | |
|---|---|
| Working tree | (this folder) |
| Canonical context | [[projects/{slug}/brief]] |
| Decisions | [[projects/{slug}/decisions]] |
| Sessions | [[projects/{slug}/sessions]] |
| Handoff | [[projects/{slug}/_handoff]] |{extra}

## Conventions

{conventions or '{Project-specific guardrails. Add as they\\'re decided. Examples: stack choices, naming rules, forbidden commands, deploy paths.}'}

## Vault is canonical

When asked "is X documented?" or "do we know Y?", check the vault first — repos document code, the vault documents decisions and context. Use the `adjudant` skill to read/write vault files.

## Claude-specific overrides

Live in `CLAUDE.md` next to this file. CLAUDE.md `@`-imports this file.
"""
    if from_legacy.strip():
        body += f"\n## From legacy AGENTS.md\n\n{from_legacy.rstrip()}\n"
    return body
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 25 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): render_agents_md emits template-shaped output

Generates a complete AGENTS.md matching templates/AGENTS.md shape,
with optional extra rows in "Where things live" table and optional
"## From legacy AGENTS.md" section at end.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: CLAUDE.md renderer

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing tests for render_claude_md**

Append to `test_port.py`:

```python
from port import render_claude_md


class TestRenderClaudeMd(unittest.TestCase):
    def test_minimal_render_just_template(self):
        result = render_claude_md(claude_specific_body="")
        self.assertTrue(result.startswith("@AGENTS.md"))
        self.assertIn("Claude-specific overrides", result)

    def test_with_body_inserts_after_template(self):
        result = render_claude_md(claude_specific_body="## Bash allowlist\n\n- npm, pnpm\n")
        self.assertTrue(result.startswith("@AGENTS.md"))
        self.assertIn("## Bash allowlist", result)
        self.assertIn("- npm, pnpm", result)
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 2 new failures.

- [ ] **Step 3: Implement render_claude_md**

Add to `port.py`:

```python
def render_claude_md(claude_specific_body: str) -> str:
    """Render CLAUDE.md from the template + optional claude-specific body."""
    extra = f"\n{claude_specific_body.rstrip()}\n" if claude_specific_body.strip() else ""
    return f"""@AGENTS.md

# Claude-specific overrides

Project context, conventions, vault references, and working-files index live in `AGENTS.md` (imported above). Any agent — Claude, Gemini, Codex, Cursor — reads from there.

This file is for **Claude Code-specific overrides only**:
- Slash-command behavior hints
- Plugin/skill invocation preferences
- Claude-only tool guidance (e.g., specific `Bash` allowlists)

**If you're about to add generic project context here, move it to `AGENTS.md` instead.**
{extra}"""
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 27 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): render_claude_md emits @AGENTS.md import + optional body

CLAUDE.md always starts with @AGENTS.md (validator enforced).
Optional claude-specific content appended after the template block.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Breadcrumb writer

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing tests for render_breadcrumb**

Append to `test_port.py`:

```python
from port import render_breadcrumb


class TestRenderBreadcrumb(unittest.TestCase):
    def test_basic_breadcrumb_format(self):
        result = render_breadcrumb(
            vault_path=Path("/v"),
            vault_name="VaultName",
            slug="my-proj",
            mode="project",
        )
        self.assertIn("vault_path: /v", result)
        self.assertIn("vault_name: VaultName", result)
        self.assertIn("slug: my-proj", result)
        self.assertIn("mode: project", result)
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 1 new failure.

- [ ] **Step 3: Implement render_breadcrumb**

Add to `port.py`:

```python
def render_breadcrumb(vault_path: Path, vault_name: str, slug: str, mode: str) -> str:
    """Render the .claude/adjudant breadcrumb content. Plain `key: value` lines."""
    return (
        f"vault_path: {vault_path}\n"
        f"vault_name: {vault_name}\n"
        f"slug: {slug}\n"
        f"mode: {mode}\n"
    )
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 28 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): render_breadcrumb writes .claude/adjudant content

Plain key:value format per spec. Used by both phase 1 (proposed) and
phase 2 (live write).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Preview directory scaffolding (Y case fully wired)

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing test for end-to-end Y preview generation**

Append to `test_port.py`:

```python
from port import generate_preview_y


class TestGeneratePreviewY(unittest.TestCase):
    def test_y_preview_writes_all_required_files(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            # Simulate an OB-legacy project
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text(
                f"vault: {vault}\nslug: legacy-proj\n"
            )
            (root / "AGENTS.md").write_text(
                "# Legacy Project\n\n## Working tree\n\n/path/to/legacy\n\n"
                "## Stack\n\nNode 22, pnpm\n\n## Vault rules\n\nUse wikilinks\n"
            )
            (root / "CLAUDE.md").write_text("# Old\n\n## Bash allowlist\n\n- npm, pnpm, git\n")
            # Vault project_type required input
            generate_preview_y(root, vault_path=Path(vault), project_type="coding", project_name="Legacy Project")

            preview = root / ".adjudant-port-preview"
            self.assertTrue(preview.is_dir())
            self.assertTrue((preview / "AGENTS.md.proposed").is_file())
            self.assertTrue((preview / "CLAUDE.md.proposed").is_file())
            self.assertTrue((preview / "breadcrumb.proposed").is_file())
            self.assertTrue((preview / "vault-changes.txt").is_file())
            self.assertTrue((preview / "summary.md").is_file())

            agents = (preview / "AGENTS.md.proposed").read_text()
            self.assertIn("# Legacy Project", agents)
            self.assertIn("Node 22, pnpm", agents)
            self.assertNotIn("Use wikilinks", agents)  # vault rules dropped

            summary = (preview / "summary.md").read_text()
            self.assertIn("Flavor: Y", summary)
            self.assertIn("Vault rules", summary)
            self.assertIn("DROPPED", summary)
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 1 new failure (ImportError).

- [ ] **Step 3: Implement generate_preview_y**

Add to `port.py`:

```python
def generate_preview_y(
    project_root: Path,
    vault_path: Path,
    project_type: str,
    project_name: str,
) -> None:
    """For Flavor Y: parse legacy files, run OB mapping, write preview dir."""
    preview_dir = project_root / ".adjudant-port-preview"
    preview_dir.mkdir(exist_ok=True)

    slug = _parse_breadcrumb_field(project_root / ".claude" / "obsidian-bridge", "slug") or project_root.name
    vault_name = vault_path.name

    # Parse legacy files
    agents_legacy = project_root / "AGENTS.md"
    claude_legacy = project_root / "CLAUDE.md"

    ob_sections = parse_markdown_sections(agents_legacy.read_text()) if agents_legacy.is_file() else {}
    claude_sections = parse_markdown_sections(claude_legacy.read_text()) if claude_legacy.is_file() else {}

    # Run mapping
    mapped = map_ob_sections(ob_sections)

    # CLAUDE.md merge: combine OB's claude-instructions slot with any legacy CLAUDE.md content
    claude_body = mapped["claude_md_body"]
    for heading, body in claude_sections.items():
        if claude_body:
            claude_body += "\n\n"
        claude_body += f"## {heading.title()}\n\n{body}"
        mapped["decisions"] += f'- Legacy CLAUDE.md "## {heading}" → Kept in CLAUDE.md (legacy claude content)\n'

    # Render proposed files
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

    # Vault changes — write list for phase 2 to consume
    vault_changes = _y_vault_changes(vault_path, slug, project_type)
    (preview_dir / "vault-changes.txt").write_text("\n".join(vault_changes) + "\n")

    # Summary
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
        changes.append(f"REPLACE:{proj / 'brief.md'}")
    changes.append(f"REGEN:{proj / '_index.md'}")
    changes.append(f"UPDATE-ROW:{vault_path / 'projects' / '_index.md'}:{slug}")
    return changes


def _render_summary(flavor: str, vault_path: Path, slug: str, decisions: str, vault_changes: list[str]) -> str:
    """Render the summary.md content for the preview dir."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    vault_changes_table = "\n".join(f"| `{change}` |" for change in vault_changes)
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
{decisions or "(none)"}

To apply: re-run `/adjudant:adjudant port`.
To discard: delete `.adjudant-port-preview/` and start over.
"""
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 29 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): generate_preview_y wires Y end-to-end

Parses legacy OB AGENTS.md + CLAUDE.md, runs deterministic mapping,
renders all 5 preview files (AGENTS.md.proposed, CLAUDE.md.proposed,
breadcrumb.proposed, vault-changes.txt, summary.md). No AI calls
required for Y flavor.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Preview for X (raw repo, identical to connect)

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing test**

Append to `test_port.py`:

```python
from port import generate_preview_x


class TestGeneratePreviewX(unittest.TestCase):
    def test_x_preview_uses_fresh_templates(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            generate_preview_x(
                root,
                vault_path=Path(vault),
                slug="fresh-proj",
                project_type="coding",
                project_name="Fresh Project",
            )
            preview = root / ".adjudant-port-preview"
            agents = (preview / "AGENTS.md.proposed").read_text()
            claude = (preview / "CLAUDE.md.proposed").read_text()
            self.assertIn("# Fresh Project", agents)
            self.assertIn("`fresh-proj` · type: `coding`", agents)
            self.assertTrue(claude.startswith("@AGENTS.md"))
            self.assertNotIn("## From legacy AGENTS.md", agents)
            summary = (preview / "summary.md").read_text()
            self.assertIn("Flavor: X", summary)
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 1 new failure (ImportError).

- [ ] **Step 3: Implement generate_preview_x**

Add to `port.py`:

```python
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
    vault_changes.append(f"CREATE:{proj / 'brief.md'}")
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
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 30 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): generate_preview_x for raw repos

X case is connect-equivalent: fresh scaffold from templates, no
legacy parsing. Per-project-type subfolder defaults per spec.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Preview scaffold for Z (stub for Claude to fill)

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing test**

Append to `test_port.py`:

```python
from port import generate_preview_z_scaffold


class TestGeneratePreviewZ(unittest.TestCase):
    def test_z_scaffold_creates_dir_and_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Custom\n\n## Stack\n\nGo\n")
            generate_preview_z_scaffold(
                root,
                vault_path=Path(vault),
                slug="hand-proj",
                project_type="coding",
                project_name="Hand Project",
            )
            preview = root / ".adjudant-port-preview"
            self.assertTrue(preview.is_dir())
            self.assertTrue((preview / "breadcrumb.proposed").is_file())
            self.assertTrue((preview / "vault-changes.txt").is_file())
            self.assertTrue((preview / "summary.md").is_file())
            # AGENTS.md.proposed and CLAUDE.md.proposed are placeholders awaiting Claude
            agents_proposed = (preview / "AGENTS.md.proposed")
            self.assertTrue(agents_proposed.is_file())
            self.assertIn("TODO: Claude AI classifier fills this", agents_proposed.read_text())
            # Legacy content copied into a known place for Claude to read
            self.assertTrue((preview / "legacy-AGENTS.md").is_file())
            self.assertIn("Go", (preview / "legacy-AGENTS.md").read_text())
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 1 new failure.

- [ ] **Step 3: Implement generate_preview_z_scaffold**

Add to `port.py`:

```python
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
    vault_name = vault_path.name

    # Copy legacy files for Claude's reference
    for name in ("AGENTS.md", "CLAUDE.md"):
        src = project_root / name
        if src.is_file():
            (preview_dir / f"legacy-{name}").write_text(src.read_text())

    # Placeholder proposed files (Claude will replace)
    placeholder = "TODO: Claude AI classifier fills this. See reference/port.md for instructions.\n"
    (preview_dir / "AGENTS.md.proposed").write_text(placeholder)
    (preview_dir / "CLAUDE.md.proposed").write_text(placeholder)

    breadcrumb_out = render_breadcrumb(vault_path=vault_path, vault_name=vault_name, slug=slug, mode="project")
    (preview_dir / "breadcrumb.proposed").write_text(breadcrumb_out)

    proj = vault_path / "projects" / slug
    subfolders = _project_type_subfolders(project_type)
    vault_changes = [f"CREATE:{proj / sub}" for sub in subfolders]
    if not (proj / "brief.md").is_file():
        vault_changes.append(f"CREATE:{proj / 'brief.md'}")
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
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 31 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): generate_preview_z_scaffold for AI handoff

Z case: scaffold preview dir with placeholders for AGENTS.md.proposed
and CLAUDE.md.proposed; copy legacy files into preview dir as
legacy-AGENTS.md / legacy-CLAUDE.md for Claude to read. The AI
classifier (per reference/port.md) fills in the proposed files.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Backup creation

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing test**

Append to `test_port.py`:

```python
from port import create_backup


class TestCreateBackup(unittest.TestCase):
    def test_backup_copies_originals_with_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("legacy agents")
            (root / "CLAUDE.md").write_text("legacy claude")
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text("legacy ob")

            backup_dir = create_backup(root, files_to_backup=[
                Path("AGENTS.md"),
                Path("CLAUDE.md"),
                Path(".claude/obsidian-bridge"),
            ])

            self.assertTrue(backup_dir.is_dir())
            self.assertTrue(backup_dir.name.startswith("20") and backup_dir.name.endswith("Z"))
            self.assertEqual((backup_dir / "AGENTS.md.legacy").read_text(), "legacy agents")
            self.assertEqual((backup_dir / "CLAUDE.md.legacy").read_text(), "legacy claude")
            self.assertEqual((backup_dir / "obsidian-bridge.legacy").read_text(), "legacy ob")

    def test_backup_skips_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("agents only")
            backup_dir = create_backup(root, files_to_backup=[
                Path("AGENTS.md"),
                Path("CLAUDE.md"),  # doesn't exist
            ])
            self.assertTrue((backup_dir / "AGENTS.md.legacy").is_file())
            self.assertFalse((backup_dir / "CLAUDE.md.legacy").exists())
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 2 new failures.

- [ ] **Step 3: Implement create_backup**

Add to `port.py`:

```python
from datetime import datetime, timezone
import shutil


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
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 33 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): create_backup with ISO-8601 basic Z timestamp

Backups land in .adjudant-port-backup/{YYYYMMDDTHHMMSSZ}/ with
.legacy suffix on each file. Missing files are silently skipped.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: Apply phase (file moves + .gitignore)

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add failing tests for apply_preview**

Append to `test_port.py`:

```python
from port import apply_preview


class TestApplyPreview(unittest.TestCase):
    def test_apply_writes_proposed_to_live_positions(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            # Set up a Y-flavor scenario with a preview already generated
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text("vault: " + vault + "\nslug: p\n")
            (root / "AGENTS.md").write_text("# Old\n\n## Stack\n\nGo\n")
            (root / "CLAUDE.md").write_text("# Old claude\n")

            generate_preview_y(root, vault_path=Path(vault), project_type="coding", project_name="P")
            # Vault project dir must exist for vault changes to apply
            (Path(vault) / "projects" / "p").mkdir(parents=True)

            apply_preview(root)

            self.assertIn("Go", (root / "AGENTS.md").read_text())
            self.assertTrue((root / ".claude" / "adjudant").is_file())
            self.assertFalse((root / ".claude" / "obsidian-bridge").exists())
            self.assertFalse((root / ".adjudant-port-preview").exists())
            # Backup created
            backups = list((root / ".adjudant-port-backup").iterdir())
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / "AGENTS.md.legacy").is_file())
            self.assertTrue((backups[0] / "obsidian-bridge.legacy").is_file())

    def test_apply_adds_gitignore_entries(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# T\n")
            generate_preview_x(root, vault_path=Path(vault), slug="t", project_type="coding", project_name="T")
            (Path(vault) / "projects" / "t").mkdir(parents=True)
            apply_preview(root)
            ignore = (root / ".gitignore").read_text()
            self.assertIn(".adjudant-port-preview/", ignore)
            self.assertIn(".adjudant-port-backup/", ignore)
            self.assertIn(".claude/adjudant", ignore)
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 2 new failures.

- [ ] **Step 3: Implement apply_preview**

Add to `port.py`:

```python
def apply_preview(project_root: Path) -> None:
    """Phase 2: apply the .adjudant-port-preview/ to the live project."""
    preview = project_root / ".adjudant-port-preview"
    if not preview.is_dir():
        raise RuntimeError(f"No preview at {preview}. Run preview phase first.")

    # 1. Backup originals
    files_to_backup = [
        Path("AGENTS.md"),
        Path("CLAUDE.md"),
        Path(".claude/obsidian-bridge"),
        Path(".claude/adjudant"),  # in case there's a stale one
    ]
    create_backup(project_root, files_to_backup)

    # 2. Write proposed files to live positions
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

    # 3. Remove OB breadcrumb if it was there
    ob = project_root / ".claude" / "obsidian-bridge"
    if ob.exists():
        ob.unlink()

    # 4. Apply vault changes
    vault_changes_file = preview / "vault-changes.txt"
    if vault_changes_file.is_file():
        for line in vault_changes_file.read_text().splitlines():
            line = line.strip()
            if line:
                _apply_vault_change(line)

    # 5. Update .gitignore
    _ensure_gitignore_entries(
        project_root,
        [".adjudant-port-preview/", ".adjudant-port-backup/", ".claude/adjudant"],
    )

    # 6. Delete preview
    shutil.rmtree(preview)


def _apply_vault_change(line: str) -> None:
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
    elif action == "REPLACE":
        # Caller should have arranged content via proposed files; REPLACE is informational
        pass
    elif action == "REGEN":
        # _index.md regeneration: write a stub if missing; full regen is beyond v0.2.0
        target = Path(parts[1])
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"# Index\n\n(Regenerate manually or via `/adjudant:adjudant ramasse`)\n")
    elif action == "UPDATE-ROW":
        # Write or update a row in projects/_index.md
        idx_path = Path(parts[1])
        slug = parts[2]
        _upsert_project_index_row(idx_path, slug)


def _upsert_project_index_row(idx_path: Path, slug: str) -> None:
    """Add or update a row for `slug` in the vault's projects/_index.md."""
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    if not idx_path.is_file():
        idx_path.write_text(f"# Projects\n\n| Slug | Brief |\n|---|---|\n| {slug} | [[projects/{slug}/brief]] |\n")
        return
    text = idx_path.read_text()
    row = f"| {slug} | [[projects/{slug}/brief]] |"
    if row in text:
        return
    if "| Slug |" not in text:
        # No table yet, append one
        idx_path.write_text(text.rstrip() + f"\n\n| Slug | Brief |\n|---|---|\n{row}\n")
        return
    idx_path.write_text(text.rstrip() + f"\n{row}\n")


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
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 35 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): apply_preview wires phase 2 end-to-end

1. Backs up originals to .adjudant-port-backup/{ts}/
2. Writes .proposed files to live positions (AGENTS.md, CLAUDE.md, .claude/adjudant)
3. Removes legacy .claude/obsidian-bridge if present
4. Applies vault-changes.txt (CREATE/RENAME/ARCHIVE/REGEN/UPDATE-ROW)
5. Appends .gitignore entries (preview dir, backup dir, breadcrumb)
6. Deletes preview dir

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: CLI entry point

**Files:**
- Modify: `adjudant/scripts/port.py`
- Modify: `adjudant/scripts/test_port.py`

- [ ] **Step 1: Add a smoke test for the CLI**

Append to `test_port.py`:

```python
import subprocess
import sys


class TestCLI(unittest.TestCase):
    def test_help_runs(self):
        """`port.py --help` exits 0 with usage."""
        script = Path(__file__).parent / "port.py"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("preview", result.stdout)
        self.assertIn("apply", result.stdout)
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 1 new failure (no main / no argparse output yet).

- [ ] **Step 3: Add CLI main to port.py**

Append to `adjudant/scripts/port.py`:

```python
import argparse
import sys


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="port.py",
        description="Adjudant port verb — migrate legacy projects to adjudant compliance.",
    )
    parser.add_argument("phase", choices=["preview", "apply", "detect"], help="Phase to run")
    parser.add_argument("--project-root", default=".", help="Project root path (default: cwd)")
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

    # preview
    vault_path = Path(args.vault_path) if args.vault_path else resolve_vault_path(root)
    if vault_path is None:
        print("[port] ERROR: Vault path unresolvable. Pass --vault-path or set OB_VAULT env var.", file=sys.stderr)
        return 1

    slug = args.slug or root.name
    project_type = args.project_type or "coding"  # caller should pass; default for safety
    project_name = args.project_name or slug.replace("-", " ").title()

    flavor = detect_flavor(root)
    if flavor == "Y":
        generate_preview_y(root, vault_path=vault_path, project_type=project_type, project_name=project_name)
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
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd "$REPO/adjudant/scripts" && python3 -m unittest test_port -v
```

Expected: 36 OK.

- [ ] **Step 5: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/port.py adjudant/scripts/test_port.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): port.py CLI entry point

Subcommands: preview | apply | detect. Resolves vault path via
spec's 4-tier fallback. Used by reference/port.md runbook.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: reference/port.md runbook (phase decision + Y/X paths)

**Files:**
- Create: `adjudant/skills/adjudant/reference/port.md`

- [ ] **Step 1: Write the runbook**

Write `adjudant/skills/adjudant/reference/port.md`:

```markdown
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
  4. Walk parent dirs for `Home.md` with `type: vault-home`
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
```

- [ ] **Step 2: Verify file written**

```bash
ls -la "$REPO/adjudant/skills/adjudant/reference/port.md"
```

Expected: file exists.

- [ ] **Step 3: Commit**

```bash
cd "$REPO" && \
git add adjudant/skills/adjudant/reference/port.md && \
git commit -m "$(cat <<'EOF'
feat(adjudant): reference/port.md Claude runbook

Orchestrates port.py calls for X/Y/Z flavors. Provides AI classifier
instructions for Z (per-section bucket classification with fallback
to verbatim append). Documents apply-phase validation and fail
conditions.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 18: Add port to SKILL.md router + command-metadata.json

**Files:**
- Modify: `adjudant/skills/adjudant/SKILL.md`
- Modify: `adjudant/scripts/command-metadata.json`

- [ ] **Step 1: Add port row to SKILL.md verb router**

Edit `adjudant/skills/adjudant/SKILL.md`. Find the router table (`## Verb router`) and add a new row for `port` between `connect` and `sync`:

```markdown
| `port` | `reference/port.md` | Migrate any legacy project (raw / obsidian-bridge / hand-authored) to adjudant compliance via two-phase preview → apply |
```

Result table:

```markdown
| Verb | Loads | Purpose |
|---|---|---|
| `connect` | `reference/connect.md` | Rigid project init — breadcrumb, AGENTS.md+CLAUDE.md, vault scaffold, session note, .gitignore |
| `port` | `reference/port.md` | Migrate any legacy project (raw / obsidian-bridge / hand-authored) to adjudant compliance via two-phase preview → apply |
| `sync` | `reference/sync.md` | Push brief + handoff to vault |
| `check` | `reference/check.md` | Read-only project + vault summary |
| `ramasse` | `reference/ramasse.md` | Rebuild indexes + normalize tags + fix wikilink form |
| `dream` | `reference/dream.md` | Diagnostic crawl — drift report, no auto-fix |
| `draw` | `reference/draw.md` | Create canvas / base / diagram |
```

Also update the `argument-hint` in the frontmatter to include `port`:

```yaml
argument-hint: "[connect|port|sync|check|ramasse|dream|draw] [args]"
```

- [ ] **Step 2: Add port entry to command-metadata.json**

Edit `adjudant/scripts/command-metadata.json`. Insert this verb entry between `connect` and `sync`:

```json
    {
      "name": "port",
      "description": "Migrate any legacy project (raw repo, obsidian-bridge legacy, hand-authored) to adjudant compliance. Two-phase: first run writes a preview, second run applies it. Idempotent.",
      "argumentHint": "(no args)",
      "reference": "reference/port.md"
    },
```

- [ ] **Step 3: Verify validators still pass**

```bash
cd "$REPO" && python3 adjudant/scripts/validate.py
```

Expected: all 6 validators OK (including `command-metadata-coherence` which now matches the new verb).

- [ ] **Step 4: Commit**

```bash
cd "$REPO" && \
git add adjudant/skills/adjudant/SKILL.md adjudant/scripts/command-metadata.json && \
git commit -m "$(cat <<'EOF'
feat(adjudant): register port verb in SKILL.md router + metadata

Adds port row to verb router table, updates argument-hint, adds
matching entry to command-metadata.json. Existing validators verify
coherence between SKILL.md and metadata.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 19: Add 3 new validators to validate.py

**Files:**
- Modify: `adjudant/scripts/validate.py`

- [ ] **Step 1: Add port-preview-coherence validator**

Append to `adjudant/scripts/validate.py` (after `validate_plugin_version_set`, before `main`):

```python
PORT_PREVIEW_REQUIRED = ["AGENTS.md.proposed", "CLAUDE.md.proposed", "breadcrumb.proposed", "vault-changes.txt", "summary.md"]


def validate_port_preview_coherence(r: Result) -> None:
    name = "port-preview-coherence"
    preview = ROOT / ".adjudant-port-preview"
    if not preview.is_dir():
        r.add_pass(name)  # no preview = nothing to check
        return
    missing = [f for f in PORT_PREVIEW_REQUIRED if not (preview / f).is_file()]
    if missing:
        r.add_fail(name, f"preview dir missing required files: {missing}")
        return
    r.add_pass(name)


def validate_port_backup_integrity(r: Result) -> None:
    name = "port-backup-integrity"
    backup_root = ROOT / ".adjudant-port-backup"
    if not backup_root.is_dir():
        r.add_pass(name)
        return
    # Each timestamped subdir should have at least one .legacy file
    for subdir in backup_root.iterdir():
        if subdir.is_dir():
            has_legacy = any(f.name.endswith(".legacy") for f in subdir.iterdir())
            if not has_legacy:
                r.add_fail(name, f"backup dir {subdir.name} has no .legacy files")
                return
    r.add_pass(name)


def validate_gitignore_includes_port_dirs(r: Result) -> None:
    name = "gitignore-includes-port-dirs"
    preview = ROOT / ".adjudant-port-preview"
    backup = ROOT / ".adjudant-port-backup"
    if not preview.is_dir() and not backup.is_dir():
        r.add_pass(name)
        return
    gi = ROOT / ".gitignore"
    if not gi.is_file():
        r.add_fail(name, "port directories exist but .gitignore is missing")
        return
    text = gi.read_text()
    required = []
    if preview.is_dir():
        required.append(".adjudant-port-preview/")
    if backup.is_dir():
        required.append(".adjudant-port-backup/")
    missing = [e for e in required if e not in text]
    if missing:
        r.add_fail(name, f".gitignore missing entries: {missing}")
        return
    r.add_pass(name)
```

Then update `main` to call the new validators:

```python
def main() -> int:
    print(f"adjudant validators — running from {ROOT}")
    r = Result()
    validate_harness_parity(r)
    validate_templates_tag_schema(r)
    validate_claude_md_imports_agents(r)
    validate_template_coverage(r)
    validate_command_metadata_coherence(r)
    validate_plugin_version_set(r)
    validate_port_preview_coherence(r)
    validate_port_backup_integrity(r)
    validate_gitignore_includes_port_dirs(r)
    return r.report()
```

Update the file's docstring to list the new validators (find the existing numbered list at top, add):

```
  7. port-preview-coherence  — if preview dir exists, has all required files
  8. port-backup-integrity   — backup dirs have at least one .legacy file
  9. gitignore-includes-port-dirs — .gitignore lists port dirs if either exists
```

- [ ] **Step 2: Run validators to confirm all 9 pass**

```bash
cd "$REPO" && python3 adjudant/scripts/validate.py
```

Expected: 9 validators OK.

- [ ] **Step 3: Commit**

```bash
cd "$REPO" && \
git add adjudant/scripts/validate.py && \
git commit -m "$(cat <<'EOF'
feat(adjudant): 3 new validators for port verb state

- port-preview-coherence: .adjudant-port-preview/ has required files
- port-backup-integrity: backup subdirs have .legacy files
- gitignore-includes-port-dirs: .gitignore lists port dirs if present

All three are no-op pass when port dirs aren't present.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 20: Version bumps

**Files:**
- Modify: `adjudant/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Bump adjudant version to 0.2.0**

Edit `adjudant/.claude-plugin/plugin.json`:

Change:
```json
"version": "0.1.2",
```
To:
```json
"version": "0.2.0",
```

Also update the `description` to mention the seven verbs (was six):

Change:
```json
"description": "Obsidian vault editor and project initializer. One command, /adjudant, with six verbs: connect, sync, check, ramasse, dream, draw. Enforces vault standards; pairs with hookify and Gemineye.",
```
To:
```json
"description": "Obsidian vault editor and project initializer. One command, /adjudant, with seven verbs: connect, port, sync, check, ramasse, dream, draw. Enforces vault standards; pairs with hookify and Gemineye.",
```

- [ ] **Step 2: Bump marketplace entry + marketplace version**

Edit `.claude-plugin/marketplace.json`. Two changes:

(a) Marketplace top-level version:

Change:
```json
"version": "1.1.2",
```
To:
```json
"version": "1.2.0",
```

(b) adjudant plugin entry:

Change:
```json
{
  "name": "adjudant",
  "version": "0.1.2",
  "source": "./adjudant",
  "description": "Vault editor/writer and project initializer. One skill, one command (/adjudant) with six verbs (connect, sync, check, ramasse, dream, draw). Rigid project provisioning, locked tag schema, AGENTS.md + CLAUDE.md auto-provisioning, drift-defense via pre-commit validators. Successor to obsidian-bridge."
},
```
To:
```json
{
  "name": "adjudant",
  "version": "0.2.0",
  "source": "./adjudant",
  "description": "Vault editor/writer and project initializer. One skill, one command (/adjudant) with seven verbs (connect, port, sync, check, ramasse, dream, draw). Port migrates legacy projects (raw, obsidian-bridge, hand-authored) to adjudant compliance. Rigid spec, locked tag schema, AGENTS.md + CLAUDE.md auto-provisioning, drift-defense via pre-commit validators. Successor to obsidian-bridge."
},
```

- [ ] **Step 3: Run validators to confirm everything still aligned**

```bash
cd "$REPO" && python3 adjudant/scripts/validate.py && python3 -m unittest discover -s adjudant/scripts -v
```

Expected: 9 validators OK + all unittest tests OK.

- [ ] **Step 4: Commit + push**

```bash
cd "$REPO" && \
git add adjudant/.claude-plugin/plugin.json .claude-plugin/marketplace.json && \
git commit -m "$(cat <<'EOF'
release(adjudant): v0.2.0 — port verb for legacy project migration

Marketplace bump 1.1.2 → 1.2.0. Adjudant 0.1.2 → 0.2.0.
Adds /adjudant:adjudant port verb: universal entry point migrating
any legacy project (raw repo, obsidian-bridge, hand-authored) to
adjudant compliance via two-phase preview → apply.

Spec: docs/superpowers/2026-05-26-adjudant-port.design.md
Plan: docs/superpowers/2026-05-26-adjudant-port.plan.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)" && \
git push origin main
```

Expected: push succeeds. Both machines + the marketplace install pointer can now pull the new version.

---

## Self-review

After implementation, the engineer should:

1. **Spec coverage:** Map each spec section to a task. The detection table → Tasks 1-4; vault path resolution → Task 5; OB mapping → Tasks 6-7; renderers → Tasks 8-10; preview generation → Tasks 11-13; apply → Tasks 14-15; CLI → Task 16; runbook → Task 17; integration → Task 18; validators → Task 19; versioning → Task 20.

2. **Type consistency:** All functions use `Path` for paths (no string-vs-Path drift). All dict keys in `map_ob_sections` output match what `render_agents_md` consumes. All vault-change action names (`CREATE`, `RENAME`, `ARCHIVE`, `REGEN`, `UPDATE-ROW`, `REPLACE`) defined consistently across generator and applier.

3. **No placeholders in steps:** Each step shows exact code, exact commands, exact expected output. No "implement remaining functions" instructions.

4. **TDD discipline:** Every task has the write-test → run-fail → implement → run-pass → commit cycle.

5. **Frequent commits:** 20 commits across the implementation (one per task). Easy to revert any one.

## Post-implementation testing on a real legacy project

After Task 20 is committed, the engineer should test the verb on a real project:

1. Pick a legacy project (a repo with `.claude/obsidian-bridge` for Y, or with a hand-authored AGENTS.md for Z).
2. `cd` into it.
3. Reinstall adjudant from marketplace: `/plugin marketplace update onnozelaer-claude-marketplace`, `/plugin uninstall adjudant@onnozelaer-claude-marketplace`, `/plugin install adjudant@onnozelaer-claude-marketplace`. Quit + relaunch CC.
4. Run `/adjudant:adjudant port`.
5. Inspect `.adjudant-port-preview/`. Verify all 5 files present. Review `summary.md`.
6. Re-run `/adjudant:adjudant port`.
7. Verify `AGENTS.md` and `CLAUDE.md` are now template-shaped, `.claude/adjudant` exists, vault has migrated structure, backup exists in `.adjudant-port-backup/{timestamp}/`.
8. Run `/adjudant:adjudant check` — expect zero drift.
9. Run `git diff` to inspect every change.
