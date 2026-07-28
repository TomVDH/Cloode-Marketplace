# Adjudant Token Discipline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut adjudant's per-invocation context cost by ~47% on write flows without trading away rule compliance, by moving enforceable rules out of prose and into a write-time gate.

**Architecture:** Four components in dependency order. A shared `schema_drift_for_text` primitive lets a new PreToolUse hook validate *proposed* frontmatter using the same detector `check` and `tidy` already use. With the write path enforcing schema, `vault-standards.md` and `voice.md` can be trimmed to shape-plus-enforcer instead of restating enforceable detail. `SKILL.md` sheds its background tables into a new reference. A report-only budget script keeps the cut visible.

**Tech Stack:** Python 3 stdlib only (no third-party imports anywhere in adjudant). bash for hooks that need no logic. `unittest` for tests. Validators in `adjudant/scripts/validate.py`.

## Global Constraints

- **Stdlib only.** No third-party imports in any adjudant script or hook.
- **Hooks fail open.** Every hook exits 0 on any infrastructural problem (no breadcrumb, unresolvable vault, unparseable payload, import failure). The ONLY non-zero exit in this plan is the deliberate schema block in Task 2.
- **Read stdin first.** Hooks read stdin before any gating logic (audit finding 22: exiting early EPIPEs the harness writer on multi-MB payloads).
- **Slug is untrusted.** Any hook building a path from a breadcrumb slug calls `is_safe_slug` first; any hook resolving a project calls `find_project_dir` (zone-aware). Both have stdlib-free fallbacks in the degraded-import branch.
- **No em dashes** in rendered output or vault writes (`voice.md`; validator 24 `voice-lexicon` enforces the machine-checkable subset).
- **Commit style:** Conventional Commits, scope is the plugin name. Every commit ends with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Full suite must stay green:** `cd adjudant/scripts && python3 -m unittest discover -s . -p "test_*.py"` (808 tests at plan time) and `python3 adjudant/scripts/validate.py` (30 validators).

---

### Task 1: `schema_drift_for_text` primitive

The gate must judge content that is not yet on disk. `schema_drift_for_file` takes a `VaultFile` (which reads from disk), so extract the shared core.

**Files:**
- Modify: `adjudant/scripts/_vault_walk.py` (near `schema_drift_for_file`)
- Test: `adjudant/scripts/test__vault_walk.py`

**Interfaces:**
- Consumes: existing `FIELD_SCHEMA`, `STATUS_VALUES_FOR_TYPE`, `DECISION_STATUS_ALIASES`, `parse_frontmatter`.
- Produces: `schema_drift_for_text(text: str, rel_path: str, aliases: Optional[set] = None) -> Optional[dict]` — same return shape as `schema_drift_for_file` (keys: `file`, `type`, and any of `missing_required`, `unknown_fields`, `status_invalid`, `type_conflict`), or `None` when clean/unjudgeable.

- [ ] **Step 1: Write the failing test**

Add to `adjudant/scripts/test__vault_walk.py`, inside the schema test class:

```python
    def test_schema_drift_for_text_matches_file_variant(self):
        from _vault_walk import schema_drift_for_text
        text = ("---\ntype: decision\nstatus: accepted\ndate: 2026-01-01\n"
                "tags:\n  - decision\n---\n\nBody.\n")
        by_text = schema_drift_for_text(text, "decisions/d.md")
        by_file = schema_drift_for_file(_vf(text, rel="decisions/d.md"))
        self.assertEqual(by_text, by_file)

    def test_schema_drift_for_text_flags_missing_required(self):
        from _vault_walk import schema_drift_for_text
        d = schema_drift_for_text("---\ntype: decision\n---\n\nB\n", "decisions/d.md")
        self.assertEqual(d["file"], "decisions/d.md")
        self.assertEqual(d["type"], "decision")
        self.assertIn("status", d["missing_required"])

    def test_schema_drift_for_text_clean_returns_none(self):
        from _vault_walk import schema_drift_for_text
        text = ("---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
                "tags:\n  - note\n---\n\nB\n")
        self.assertIsNone(schema_drift_for_text(text, "notes/n.md"))

    def test_schema_drift_for_text_ignores_unjudgeable(self):
        from _vault_walk import schema_drift_for_text
        # no frontmatter, unknown type, and a parse error are all ramasse
        # territory, not schema territory
        self.assertIsNone(schema_drift_for_text("no frontmatter\n", "notes/n.md"))
        self.assertIsNone(schema_drift_for_text(
            "---\ntype: unknowntype\n---\n\nB\n", "notes/n.md"))
        self.assertIsNone(schema_drift_for_text("---\ntype: note\nno close\n", "notes/n.md"))
```

If `_vf` does not already accept a `rel` argument, update its definition in the same file to `def _vf(text, rel="notes/n.md")` and pass `rel_path=Path(rel)` when constructing the `VaultFile`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test__vault_walk -v -k schema_drift_for_text`
Expected: FAIL with `ImportError: cannot import name 'schema_drift_for_text'`

- [ ] **Step 3: Write minimal implementation**

In `adjudant/scripts/_vault_walk.py`, replace the body of `schema_drift_for_file` with a delegation and add the new function above it:

```python
def _schema_drift_core(fields: dict, has_block: bool, parse_error: Optional[str],
                       ftype: Optional[str], rel: str,
                       aliases: Optional[set] = None) -> Optional[dict]:
    """Shared schema check. See schema_drift_for_file for the contract."""
    if not has_block or parse_error or ftype not in FIELD_SCHEMA:
        return None
    spec = FIELD_SCHEMA[ftype]
    keys = set(fields)
    out: dict[str, Any] = {}
    missing = spec["required"] - keys
    if missing:
        out["missing_required"] = sorted(missing)
    unknown = keys - spec["required"] - spec["optional"]
    if unknown:
        out["unknown_fields"] = sorted(unknown)
    enum = STATUS_VALUES_FOR_TYPE.get(ftype)
    if enum is not None:
        status = fields.get("status")
        if isinstance(status, str) and status and status not in enum:
            if ftype == "task" and aliases and status in aliases:
                pass  # accepted input; the board normalizes lanes on read
            else:
                normalizable = ftype == "decision" and status in DECISION_STATUS_ALIASES
                out["status_invalid"] = {"value": status, "normalizable": normalizable}
    if "node_type" in keys and "type" in keys:
        out["type_conflict"] = True
    if not out:
        return None
    out["file"] = rel
    out["type"] = ftype
    return out


def schema_drift_for_text(text: str, rel_path: str,
                          aliases: Optional[set] = None) -> Optional[dict]:
    """Schema drift for PROPOSED content that is not on disk yet.

    Used by the PreToolUse write gate so a note is judged before it lands,
    against the same FIELD_SCHEMA that check reports and tidy repairs.
    """
    fm, _ = parse_frontmatter(text)
    ftype = fm.fields.get("type")
    return _schema_drift_core(
        fm.fields, fm.has_block, fm.parse_error,
        ftype if isinstance(ftype, str) else None, rel_path, aliases)
```

Then make `schema_drift_for_file` delegate, keeping its existing docstring:

```python
def schema_drift_for_file(vf: "VaultFile", aliases: Optional[set] = None) -> Optional[dict]:
    """Schema drift for one file per FIELD_SCHEMA, or None when clean.

    Only files with a parsed frontmatter block and a canonical type are
    checked; everything else is ramasse territory (detect_frontmatter_drift,
    detect_type_drift) and returns None here. `aliases` is the task-status
    alias set (board.STATUS_TO_COLUMN keys) used to mark task values as
    normalizable; decision values normalize via DECISION_STATUS_ALIASES.
    """
    fm = vf.frontmatter
    return _schema_drift_core(fm.fields, fm.has_block, fm.parse_error,
                              vf.file_type, str(vf.rel_path), aliases)
```

Add both new names to the module docstring's public API list, next to the existing `schema_drift_for_file` line.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd adjudant/scripts && python3 -m unittest discover -s . -p "test_*.py" 2>&1 | tail -3`
Expected: `OK`, count increased by 4. `schema_drift` and `schema_drift_for_file` behaviour must be unchanged (existing tests cover this).

- [ ] **Step 5: Commit**

```bash
git add adjudant/scripts/_vault_walk.py adjudant/scripts/test__vault_walk.py
git commit -m "$(cat <<'EOF'
feat(adjudant): schema_drift_for_text - judge proposed content before it lands

Extracts the shared core out of schema_drift_for_file so the same
FIELD_SCHEMA check can run against content that is not on disk yet. The
PreToolUse write gate needs this; there must be exactly one copy of the
schema rules.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: PreToolUse schema gate

**Files:**
- Create: `adjudant/hooks/scripts/pretooluse-schema-gate.py`
- Create: `adjudant/scripts/test_pretooluse_schema_gate.py`
- Modify: `adjudant/hooks/hooks.json`

**Interfaces:**
- Consumes: `schema_drift_for_text` (Task 1), plus existing `is_safe_slug`, `find_project_dir`, `resolve_vault`.
- Produces: a hook that exits 2 on hard schema violations and 0 otherwise. No Python API other tasks consume.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_pretooluse_schema_gate.py`:

```python
"""Tests for hooks/scripts/pretooluse-schema-gate.py.

The gate blocks a Write into the vault project when the proposed frontmatter
is missing required fields or carries a type/node_type conflict. Everything
else - unknown fields, writes outside the project, any infrastructural
problem - must let the write through.
"""

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
HOOK = SCRIPTS.parent / "hooks" / "scripts" / "pretooluse-schema-gate.py"
_spec = importlib.util.spec_from_file_location("pretooluse_schema_gate", HOOK)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

GOOD_NOTE = ("---\ntype: note\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
             "tags:\n  - note\n---\n\nBody.\n")


class _GateHarness(unittest.TestCase):

    def setUp(self):
        self._ob = os.environ.pop("OB_VAULT", None)

    def tearDown(self):
        if self._ob is not None:
            os.environ["OB_VAULT"] = self._ob

    def _fixture(self, tmp: Path, zone: str = "") -> tuple[Path, Path]:
        project = tmp / "code"
        vault = tmp / "vault"
        proot = vault / "projects" / zone / "demo" if zone else vault / "projects" / "demo"
        proot.mkdir(parents=True)
        (proot / "brief.md").write_text(
            "---\ntype: project\nslug: demo\n---\n\n# Demo\n")
        (project / ".claude").mkdir(parents=True)
        (project / ".claude" / "adjudant").write_text(
            f"vault_path: {vault}\nvault_name: vault\nslug: demo\nmode: project\n")
        return project, proot

    def _run(self, project: Path, payload) -> int:
        os.environ["CLAUDE_PROJECT_DIR"] = str(project)
        before = sys.stdin
        sys.stdin = io.StringIO(payload if isinstance(payload, str)
                                else json.dumps(payload))
        try:
            return gate.main()
        finally:
            sys.stdin = before
            del os.environ["CLAUDE_PROJECT_DIR"]

    def _payload(self, path: Path, content: str, tool: str = "Write") -> dict:
        return {"tool_name": tool,
                "tool_input": {"file_path": str(path), "content": content}}


class TestBlocks(_GateHarness):

    def test_missing_required_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            rc = self._run(project, self._payload(
                proot / "decisions" / "d.md", "---\ntype: decision\n---\n\nB\n"))
            self.assertEqual(rc, 2)

    def test_type_conflict_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            bad = GOOD_NOTE.replace("type: note\n", "type: note\nnode_type: note\n")
            rc = self._run(project, self._payload(proot / "notes" / "n.md", bad))
            self.assertEqual(rc, 2)


class TestAllows(_GateHarness):

    def test_conformant_note_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            rc = self._run(project, self._payload(proot / "notes" / "n.md", GOOD_NOTE))
            self.assertEqual(rc, 0)

    def test_unknown_field_warns_but_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            bad = GOOD_NOTE.replace("type: note\n", "type: note\nbogus: x\n")
            rc = self._run(project, self._payload(proot / "notes" / "n.md", bad))
            self.assertEqual(rc, 0)

    def test_write_outside_project_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = self._fixture(Path(tmp))
            rc = self._run(project, self._payload(
                Path(tmp) / "elsewhere.md", "---\ntype: decision\n---\n\nB\n"))
            self.assertEqual(rc, 0)

    def test_edit_tool_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp))
            rc = self._run(project, self._payload(
                proot / "decisions" / "d.md", "---\ntype: decision\n---\n\nB\n",
                tool="Edit"))
            self.assertEqual(rc, 0)

    def test_shelved_project_is_gated_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, proot = self._fixture(Path(tmp), zone="_fridge")
            rc = self._run(project, self._payload(
                proot / "decisions" / "d.md", "---\ntype: decision\n---\n\nB\n"))
            self.assertEqual(rc, 2)


class TestFailsOpen(_GateHarness):

    def test_no_breadcrumb_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "code"
            project.mkdir()
            rc = self._run(project, self._payload(
                Path(tmp) / "x.md", "---\ntype: decision\n---\n\nB\n"))
            self.assertEqual(rc, 0)

    def test_garbage_payload_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = self._fixture(Path(tmp))
            self.assertEqual(self._run(project, "not json {{{"), 0)

    def test_traversal_slug_allows_and_does_not_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, proot = self._fixture(root)
            (project / ".claude" / "adjudant").write_text(
                f"vault_path: {root / 'vault'}\nslug: ../../../escaped\nmode: project\n")
            rc = self._run(project, self._payload(
                proot / "decisions" / "d.md", "---\ntype: decision\n---\n\nB\n"))
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_pretooluse_schema_gate -v`
Expected: FAIL at module load — the hook file does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `adjudant/hooks/scripts/pretooluse-schema-gate.py`:

```python
#!/usr/bin/env python3
"""PreToolUse hook for adjudant: schema gate on vault writes.

Validates the PROPOSED frontmatter of a Write landing under the resolved
vault project, using the same FIELD_SCHEMA detector that `check` reports and
`tidy` phase 5 repairs. Catching drift at write time is what lets
vault-standards.md stop restating enforceable detail.

  - BLOCK (exit 2) on missing required fields or a type/node_type conflict.
    PreToolUse exit 2 stops the tool and feeds stderr back to the model, so
    it corrects in the same turn.
  - WARN (exit 0 + stderr) on unknown fields; tidy strips those safely.
  - FAIL OPEN (exit 0) on anything infrastructural. A write must never be
    blocked because a hook had a bad day.

Write-only: an Edit payload carries old_string/new_string, not the resulting
file, so the outcome cannot be judged without simulating the edit. Edits keep
tidy as their backstop.
"""

import json
import os
import sys
from pathlib import Path

# Shared primitives live in <plugin>/scripts/. Same bootstrap as the other
# python hooks: a broken or mid-sync module only degrades its own capability.
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
except Exception:  # pragma: no cover - defensive
    pass

try:
    from _vault_walk import (find_project_dir, is_safe_slug, resolve_vault,
                             schema_drift_for_text)
    _READY = True
except Exception:  # pragma: no cover - degrade: gate disabled, never blocks
    _READY = False

# System files carry shapes the note schema does not describe.
_SKIP_NAMES = ("_handoff.md", "_index.md", "_iteration.md", "brief.md")


def read_breadcrumb(project_dir: Path) -> dict:
    """Read `.claude/adjudant` breadcrumb (`key: value` per line, YAML-ish)."""
    breadcrumb = project_dir / ".claude" / "adjudant"
    if not breadcrumb.exists():
        return {}
    info = {}
    for line in breadcrumb.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sep = ":" if ":" in line else ("=" if "=" in line else None)
        if not sep:
            continue
        k, v = line.split(sep, 1)
        info[k.strip()] = v.strip()
    return info


def main() -> int:
    # Read stdin FIRST: exiting before consuming it EPIPEs the harness writer
    # on multi-MB Write payloads.
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0
    if not _READY:
        return 0
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_dir:
        return 0
    try:
        payload = json.loads(raw)
    except Exception:
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Write":
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path_str = tool_input.get("file_path") or tool_input.get("path")
    content = tool_input.get("content")
    if not file_path_str or not isinstance(content, str):
        return 0

    info = read_breadcrumb(Path(project_dir))
    slug = info.get("slug", "")
    if not slug or not is_safe_slug(slug):
        return 0
    try:
        vault = resolve_vault(Path(project_dir))
        if vault is None or not vault.is_dir():
            return 0
        project_root = find_project_dir(vault, slug)
        if project_root is None:
            return 0
        rel = Path(file_path_str).resolve().relative_to(project_root.resolve())
    except Exception:
        return 0
    if not rel.parts or rel.name in _SKIP_NAMES or rel.parts[0] == "sessions":
        return 0

    try:
        drift = schema_drift_for_text(content, str(rel))
    except Exception:
        return 0
    if not drift:
        return 0

    ftype = drift.get("type")
    hard = []
    if drift.get("missing_required"):
        hard.append(f"missing required field(s): {', '.join(drift['missing_required'])}")
    if drift.get("type_conflict"):
        hard.append("both `type:` and `node_type:` are set; keep `type:` only")
    if hard:
        print(f"adjudant schema gate: {rel} (type: {ftype}) "
              f"does not match the vault schema.", file=sys.stderr)
        for h in hard:
            print(f"  - {h}", file=sys.stderr)
        print("  Fix the frontmatter and write again. "
              "See reference/vault-standards.md.", file=sys.stderr)
        return 2
    if drift.get("unknown_fields"):
        print(f"adjudant schema gate: {rel} carries unknown field(s): "
              f"{', '.join(drift['unknown_fields'])} "
              f"(allowed through; /adjudant tidy strips them).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    # Only the deliberate schema block may exit non-zero.
    try:
        sys.exit(main())
    except Exception:  # pragma: no cover - last-resort guard
        sys.exit(0)
```

- [ ] **Step 4: Wire it into hooks.json**

In `adjudant/hooks/hooks.json`, add a `PreToolUse` block as the first key inside `"hooks"`:

```json
    "PreToolUse": [{
      "matcher": "Write",
      "hooks": [{
        "type": "command",
        "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/pretooluse-schema-gate.py\"",
        "timeout": 5
      }]
    }],
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd adjudant/scripts && python3 -m unittest test_pretooluse_schema_gate -v`
Expected: PASS, 11 tests.

Then the full suite and validators:

Run: `cd adjudant/scripts && python3 -m unittest discover -s . -p "test_*.py" 2>&1 | tail -3 && cd .. && python3 scripts/validate.py 2>&1 | tail -1`
Expected: `OK` and `PASS — 30 validator(s) green`.

Pre-verified 2026-07-28: `hooks-wiring` iterates whatever events exist in
`hooks.json` and only checks that each command resolves to a real script under
`hooks/scripts/`. It has no hardcoded event list, so `PreToolUse` needs no
validator change. **Do not edit any validator in this task.** If a validator
does fail, that is a real signal — report it rather than adjusting the
validator to pass.

- [ ] **Step 6: Verify end-to-end against a real fixture**

```bash
SP="$(mktemp -d)"; mkdir -p "$SP/vault/projects/demo/decisions" "$SP/code/.claude"
printf -- '---\ntype: project\nslug: demo\n---\n\n# Demo\n' > "$SP/vault/projects/demo/brief.md"
printf 'vault_path: %s\nvault_name: vault\nslug: demo\nmode: project\n' "$SP/vault" > "$SP/code/.claude/adjudant"
# printf, not echo: zsh's builtin echo does not expand \n, which mangles the
# JSON and makes the hook (correctly) fail open instead of exercising the gate.
printf '{"tool_name":"Write","tool_input":{"file_path":"%s/vault/projects/demo/decisions/d.md","content":"---\\ntype: decision\\n---\\n\\nB\\n"}}' "$SP" \
  | env -u OB_VAULT CLAUDE_PROJECT_DIR="$SP/code" python3 adjudant/hooks/scripts/pretooluse-schema-gate.py; echo "exit=$?"
```
Expected: stderr names the missing fields, `exit=2`.

- [ ] **Step 7: Commit**

```bash
git add adjudant/hooks/scripts/pretooluse-schema-gate.py adjudant/hooks/hooks.json adjudant/scripts/test_pretooluse_schema_gate.py adjudant/scripts/validate.py
git commit -m "$(cat <<'EOF'
feat(adjudant): PreToolUse schema gate - vault writes are checked before they land

Blocks a Write whose proposed frontmatter is missing required fields or sets
both type and node_type, feeding the expected shape back on stderr so the
model corrects in the same turn. Unknown fields warn only (tidy strips them
safely). Everything infrastructural fails open.

Write-only by design: an Edit payload carries old_string/new_string, not the
resulting file, so the outcome cannot be judged without simulating the edit.

This is what makes trimming vault-standards.md safe rather than a trade: the
write path now enforces what the prose used to only remind about.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: SKILL.md split into reference/internals.md

**Files:**
- Create: `adjudant/skills/adjudant/reference/internals.md`
- Modify: `adjudant/skills/adjudant/SKILL.md`
- Test: `adjudant/scripts/test_validate.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `reference/internals.md` as a loadable reference; the router row that names it.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_validate.py`:

```python
class TestSkillSplit(unittest.TestCase):
    """v0.17.0 token discipline: background tables live in internals.md, not
    in the always-loaded router."""

    SKILL = Path(__file__).resolve().parent.parent / "skills" / "adjudant" / "SKILL.md"
    INTERNALS = (Path(__file__).resolve().parent.parent / "skills" / "adjudant"
                 / "reference" / "internals.md")

    def test_internals_exists_and_holds_the_tables(self):
        text = self.INTERNALS.read_text()
        self.assertIn("posttooluse-vault-log.py", text)   # hooks table
        self.assertIn("board_bridge.py", text)            # helper layer table
        self.assertIn("suitcase", text)                   # environment awareness

    def test_skill_sheds_the_background_tables(self):
        text = self.SKILL.read_text()
        self.assertNotIn("posttooluse-vault-log.py", text)
        self.assertNotIn("board_bridge.py", text)

    def test_skill_still_routes_and_points_at_internals(self):
        text = self.SKILL.read_text()
        for verb in ("connect", "port", "sync", "check", "sitrep", "tidy",
                     "ramasse", "dream", "draw", "board", "shelf"):
            self.assertIn(f"`{verb}`", text)
        self.assertIn("reference/internals.md", text)

    def test_skill_within_token_budget(self):
        # bytes // 4, the repo's own estimator. Target from the design spec.
        est = len(self.SKILL.read_text()) // 4
        self.assertLess(est, 2000, f"SKILL.md is ~{est} tok, budget 2000")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_validate.TestSkillSplit -v`
Expected: FAIL — `internals.md` does not exist.

- [ ] **Step 3: Create internals.md**

Create `adjudant/skills/adjudant/reference/internals.md` with this header, then move the three sections **verbatim** out of `SKILL.md`: `## Hooks` (the full nine-row table plus its intro line), `## Python helper layer` (intro paragraph plus table), and `## Environment awareness`.

```markdown
# Adjudant internals

How adjudant itself is built: the hook wiring, the verb-to-helper map, and the
environment probes. Load this when the question is about adjudant's own
machinery. Running a verb does not need it - `SKILL.md` routes, and the verb's
own reference file describes the job.
```

- [ ] **Step 4: Trim SKILL.md**

Delete those three sections from `adjudant/skills/adjudant/SKILL.md`. Add one row to the verb-router table (after the `shelf` row):

```markdown
| _(internals)_ | `reference/internals.md` | Not a verb. Hook wiring, verb-to-helper map, environment probes. Load only when the question is about adjudant's own machinery |
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd adjudant/scripts && python3 -m unittest discover -s . -p "test_*.py" 2>&1 | tail -3 && cd .. && python3 scripts/validate.py 2>&1 | tail -1`
Expected: `OK` and `PASS — 30 validator(s) green`. The `reference-doc-links` and `reference-files-exist` validators cover the new file automatically.

Pre-verified 2026-07-28: `verb-surface-parity` reads the verb list from
`command-metadata.json` and checks each name appears in plugin.json, README,
and the marketplace entry. It does not parse the SKILL.md router table, so the
`_(internals)_` row cannot trip it. **Do not edit any validator in this task.**
A validator failure here is a real signal, not something to tune away.

- [ ] **Step 6: Commit**

```bash
git add adjudant/skills/adjudant/SKILL.md adjudant/skills/adjudant/reference/internals.md adjudant/scripts/test_validate.py adjudant/scripts/validate.py
git commit -m "$(cat <<'EOF'
refactor(adjudant): SKILL.md sheds its background tables to reference/internals.md

The hooks table, verb-to-helper map, and environment probes are reference
material about how adjudant is built, not instructions for doing the current
job - and SKILL.md is loaded on every single invocation. Moving them takes
the always-loaded router from ~3050 to under 2000 tokens with no behaviour
change; the router gains one row pointing at the new file.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: vault-standards and voice trim

**Files:**
- Modify: `adjudant/skills/adjudant/reference/vault-standards.md`
- Modify: `adjudant/skills/adjudant/reference/voice.md`
- Modify: `adjudant/scripts/validate.py` (validator 24 owns the lexicon list)
- Test: `adjudant/scripts/test_validate.py`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing consumed by later tasks. Validator 24 keeps its existing name `voice-lexicon`.

- [ ] **Step 1: Write the failing test**

Append to `adjudant/scripts/test_validate.py`:

```python
class TestDocTrim(unittest.TestCase):
    """v0.17.0: enforceable detail lives with its enforcer, not in prose."""

    REF = Path(__file__).resolve().parent.parent / "skills" / "adjudant" / "reference"

    def test_vault_standards_within_budget(self):
        est = len((self.REF / "vault-standards.md").read_text()) // 4
        self.assertLess(est, 1800, f"vault-standards.md is ~{est} tok, budget 1800")

    def test_voice_within_budget(self):
        est = len((self.REF / "voice.md").read_text()) // 4
        self.assertLess(est, 600, f"voice.md is ~{est} tok, budget 600")

    def test_vault_standards_names_its_enforcers(self):
        text = (self.REF / "vault-standards.md").read_text()
        for enforcer in ("FIELD_SCHEMA", "tidy", "validate.py"):
            self.assertIn(enforcer, text)

    def test_voice_keeps_the_judgement_content(self):
        text = (self.REF / "voice.md").read_text()
        for keeper in ("ELI5", "ELI12", "ELICTO", "pushback"):
            self.assertIn(keeper, text)

    def test_lexicon_still_enforced_after_the_move(self):
        import validate
        self.assertTrue(hasattr(validate, "BANNED_LEXICON"))
        self.assertIn("delve", [w.lower() for w in validate.BANNED_LEXICON])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_validate.TestDocTrim -v`
Expected: FAIL on the budget assertions and on `BANNED_LEXICON` not existing.

- [ ] **Step 3: Move the lexicon into validate.py**

In `adjudant/scripts/validate.py`, find where `validate_voice_lexicon` currently gets its banned terms. Promote that list to a module-level constant immediately above the function, preserving every existing term:

```python
# The banned lexicon. Lives HERE, not in voice.md: this validator is the
# mechanical enforcer, so spending the list in model context every session
# bought nothing. voice.md points at this constant.
BANNED_LEXICON: tuple[str, ...] = (
    # ... every term currently in the validator, verbatim ...
)
```

Update `validate_voice_lexicon` to iterate `BANNED_LEXICON`.

- [ ] **Step 4: Trim voice.md**

Replace the enumerated banned-term list in `adjudant/skills/adjudant/reference/voice.md` with:

```markdown
## Banned lexicon

The machine-checkable list lives in `scripts/validate.py` as `BANNED_LEXICON`
and is enforced by validator 24 (`voice-lexicon`) on every commit. It is not
repeated here: a rule the build fails on does not need to be re-read every
session. The principle it encodes: no filler superlatives, no throat-clearing,
no self-congratulation. Write the sentence a competent colleague would write.
```

Keep every other section (tone, pushback contract, ELI modes, glazing ban, typography) unchanged.

- [ ] **Step 5: Trim vault-standards.md**

Rewrite so each rule states its shape once and names its enforcer. Keep in full: folder layout, file-naming patterns, wikilink form examples, and any hand-authoring guidance with no mechanical enforcer. Compress to shape-plus-pointer: the per-type frontmatter key lists (now in `FIELD_SCHEMA`), the tag bucket enumerations (enforced by `tidy.normalize_tags` and validator 1), and the status vocabularies (validators 23 and 28).

Add this near the top, after the existing intro:

```markdown
## What enforces what

This document states each rule's shape once. The detail is enforced
mechanically, so it is not restated here:

| rule area | enforcer |
|---|---|
| frontmatter keys per type | `FIELD_SCHEMA` in `scripts/_vault_walk.py`; validators 28 + 29; the PreToolUse schema gate at write time; `tidy` phase 5 for repair |
| tag taxonomy (buckets A-D) | `tidy.normalize_tags`; validator 1 (`templates-tag-schema`) |
| status vocabularies | validators 23 (`status-vocabulary`) + 28 (`decision-status-vocabulary`) |
| wikilink form | `tidy` phase 4 |
| folder shape, file naming | `ramasse_scan` |

A write that violates the schema is blocked before it lands, so the shapes
below are orientation, not a checklist to hold in your head.
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd adjudant/scripts && python3 -m unittest discover -s . -p "test_*.py" 2>&1 | tail -3 && cd .. && python3 scripts/validate.py 2>&1 | tail -1`
Expected: `OK` and `PASS — 30 validator(s) green`. Validator 24 must still fail on a banned term — confirm with:

```bash
cd adjudant && printf 'Let us delve into this.\n' >> skills/adjudant/reference/sync.md && python3 scripts/validate.py 2>&1 | grep voice-lexicon; git checkout skills/adjudant/reference/sync.md
```
Expected: the validator reports a failure, then the file is restored.

- [ ] **Step 7: Commit**

```bash
git add adjudant/skills/adjudant/reference/vault-standards.md adjudant/skills/adjudant/reference/voice.md adjudant/scripts/validate.py adjudant/scripts/test_validate.py
git commit -m "$(cat <<'EOF'
refactor(adjudant): standards and voice state the shape, the validators hold the detail

vault-standards.md was the fattest reference (~3539 tok) and is loaded for
essentially every vault write, while being the file whose rules are most
thoroughly enforced already - FIELD_SCHEMA, validators 23/28/29, tidy phases
4 and 5, and now the write gate. It now states each rule's shape once and
names its enforcer.

voice.md's banned-term list moves into validate.py as BANNED_LEXICON, where
validator 24 already enforced it. The judgement content - tone, pushback
contract, ELI modes, glazing ban - stays.

A rule the build fails on does not need to be spent in context every session.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Token budget report

**Files:**
- Create: `adjudant/scripts/token_budget.py`
- Create: `adjudant/scripts/test_token_budget.py`
- Modify: `adjudant/scripts/repo_scan.py`
- Modify: `adjudant/skills/adjudant/reference/check.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `token_budget.report(skill_root: Path) -> dict` returning
  `{"surfaces": [{"file": str, "tokens": int, "budget": Optional[int], "over": bool}], "total": int, "over_count": int}`.
  `repo_scan.run_scan` gains a `"token_budget"` key holding exactly that dict.

- [ ] **Step 1: Write the failing test**

Create `adjudant/scripts/test_token_budget.py`:

```python
"""Tests for token_budget.py — report-only context-cost accounting."""

import tempfile
import unittest
from pathlib import Path

import token_budget as tb


class TestReport(unittest.TestCase):

    def _skill(self, tmp: Path) -> Path:
        root = tmp / "adjudant"
        (root / "reference").mkdir(parents=True)
        (root / "SKILL.md").write_text("x" * 4000)          # ~1000 tok
        (root / "reference" / "sync.md").write_text("y" * 400)   # ~100 tok
        return root

    def test_counts_tokens_per_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._skill(Path(tmp))
            rep = tb.report(root)
            by = {s["file"]: s["tokens"] for s in rep["surfaces"]}
            self.assertEqual(by["SKILL.md"], 1000)
            self.assertEqual(by["reference/sync.md"], 100)
            self.assertEqual(rep["total"], 1100)

    def test_flags_over_budget_without_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._skill(Path(tmp))
            tb.BUDGETS["SKILL.md"] = 500          # deliberately low
            try:
                rep = tb.report(root)
                skill = [s for s in rep["surfaces"] if s["file"] == "SKILL.md"][0]
                self.assertTrue(skill["over"])
                self.assertEqual(rep["over_count"], 1)
            finally:
                tb.BUDGETS.pop("SKILL.md", None)

    def test_undeclared_surface_has_no_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._skill(Path(tmp))
            rep = tb.report(root)
            sync = [s for s in rep["surfaces"] if s["file"] == "reference/sync.md"][0]
            self.assertIsNone(sync["budget"])
            self.assertFalse(sync["over"])

    def test_missing_skill_root_is_empty_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            rep = tb.report(Path(tmp) / "nope")
            self.assertEqual(rep["surfaces"], [])
            self.assertEqual(rep["total"], 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adjudant/scripts && python3 -m unittest test_token_budget -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'token_budget'`

- [ ] **Step 3: Write minimal implementation**

Create `adjudant/scripts/token_budget.py`:

```python
#!/usr/bin/env python3
"""Adjudant token budget — report-only context-cost accounting.

Every reference file and SKILL.md is prose the model pays for on invocation.
This reports what each surface costs, using the repo's own `bytes // 4`
estimator, against declared budgets.

REPORT ONLY, by design. A hard ceiling would turn legitimate documentation
growth into a fight and become the thing people work around; visibility is
enough pressure. Nothing here fails a build.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

# Declared budgets, in estimated tokens. Surfaces with no entry are reported
# without a verdict. Lives here rather than in command-metadata.json, which
# is verb metadata and has no natural slot for per-document limits.
BUDGETS: dict[str, int] = {
    "SKILL.md": 2000,
    "reference/vault-standards.md": 1800,
    "reference/voice.md": 600,
}


def estimate_tokens(text: str) -> int:
    """The repo's own estimator, shared with _cost.py: 4 bytes per token."""
    return len(text) // 4


def report(skill_root: Path) -> dict[str, Any]:
    """Per-surface token cost for SKILL.md + reference/*.md."""
    surfaces: list[dict[str, Any]] = []
    if not skill_root.is_dir():
        return {"surfaces": [], "total": 0, "over_count": 0}
    paths = []
    skill = skill_root / "SKILL.md"
    if skill.is_file():
        paths.append(skill)
    ref = skill_root / "reference"
    if ref.is_dir():
        paths.extend(sorted(ref.glob("*.md")))
    for p in paths:
        try:
            tokens = estimate_tokens(p.read_text())
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(p.relative_to(skill_root))
        budget: Optional[int] = BUDGETS.get(rel)
        surfaces.append({
            "file": rel,
            "tokens": tokens,
            "budget": budget,
            "over": budget is not None and tokens > budget,
        })
    return {
        "surfaces": surfaces,
        "total": sum(s["tokens"] for s in surfaces),
        "over_count": sum(1 for s in surfaces if s["over"]),
    }


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="token_budget.py",
        description="Adjudant token budget — report-only (never fails).")
    parser.add_argument("--skill-root",
                        default=str(Path(__file__).resolve().parent.parent
                                    / "skills" / "adjudant"),
                        help="Path to skills/adjudant (default: this plugin's)")
    args = parser.parse_args(argv)
    print(json.dumps(report(Path(args.skill_root).expanduser()), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd adjudant/scripts && python3 -m unittest test_token_budget -v`
Expected: PASS, 4 tests.

- [ ] **Step 5: Wire into `check repo`**

In `adjudant/scripts/repo_scan.py`, import the module near the other local imports:

```python
from token_budget import report as token_budget_report
```

In `run_scan`, add the key to the returned dict (alongside the existing keys):

```python
        "token_budget": token_budget_report(
            Path(__file__).resolve().parent.parent / "skills" / "adjudant"),
```

- [ ] **Step 6: Document the section**

In `adjudant/skills/adjudant/reference/check.md`, under the `repo` target description, add:

```markdown
- `token_budget` — per-surface context cost (`file`, `tokens`, `budget`,
  `over`) plus `total` and `over_count`, from `token_budget.py`. Render as one
  line when `over_count` is 0 (`context: ~{total/1000}k tokens across
  {n} surfaces`), and list the offenders when it is not. Report only: it never
  fails a build, and an over-budget surface is a prompt to look, not an error.
```

- [ ] **Step 7: Run full suite and validators**

Run: `cd adjudant/scripts && python3 -m unittest discover -s . -p "test_*.py" 2>&1 | tail -3 && cd .. && python3 scripts/validate.py 2>&1 | tail -1`
Expected: `OK` and `PASS — 30 validator(s) green`.

- [ ] **Step 8: Commit**

```bash
git add adjudant/scripts/token_budget.py adjudant/scripts/test_token_budget.py adjudant/scripts/repo_scan.py adjudant/skills/adjudant/reference/check.md
git commit -m "$(cat <<'EOF'
feat(adjudant): token budget report in check repo

Reports what each context surface costs against declared budgets, using the
repo's own bytes//4 estimator. Report only by design: a hard ceiling would
turn documentation growth into a fight and become the thing people work
around, so this makes the cost visible and leaves the judgement human.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Truth pass and release

**Files:**
- Modify: `adjudant/README.md`
- Modify: `adjudant/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `docs/superpowers/specs/2026-07-28-adjudant-token-discipline-design.md`

**Interfaces:** none.

- [ ] **Step 1: Measure the real result**

```bash
cd adjudant && for f in skills/adjudant/SKILL.md skills/adjudant/reference/voice.md skills/adjudant/reference/vault-standards.md skills/adjudant/reference/check.md; do
  printf "%-46s ~%5d tok\n" "$f" "$(( $(wc -c < "$f") / 4 ))"
done
python3 scripts/token_budget.py | python3 -c "import json,sys; d=json.load(sys.stdin); print('total', d['total'], 'over', d['over_count'])"
```
Record the actual numbers; use them in the next step rather than the spec's estimates.

- [ ] **Step 2: Update the README surface table**

In `adjudant/README.md`, update the `Hooks` row to say **ten entries across nine events** (PreToolUse joins), and update the test count from the suite output. Add a row:

```markdown
| Context cost | `python3 scripts/token_budget.py`: per-surface token report, wired into `check repo` (report only) |
```

Add a `PreToolUse` row to the hooks table in the Hooks section:

```markdown
| PreToolUse (Write) | `hooks/scripts/pretooluse-schema-gate.py` | Validates proposed frontmatter against `FIELD_SCHEMA` before a vault write lands; blocks on missing required fields or a `type`/`node_type` conflict (stderr names the expected shape), warns on unknown fields, fails open on anything infrastructural. Write-only: an Edit payload carries no resulting file |
```

- [ ] **Step 3: Update plugin.json and marketplace.json descriptions**

In both `adjudant/.claude-plugin/plugin.json` and the adjudant entry in `.claude-plugin/marketplace.json`, replace the phrase `Nine vault-aware hook entries across eight events` with `Ten vault-aware hook entries across nine events, including a PreToolUse schema gate that checks a note's frontmatter before it lands`.

- [ ] **Step 4: Record the measured result in the spec**

Using the real numbers from Step 1 (do NOT write placeholder text to disk —
measure first, then write the finished table in a single edit), append to the
"Expected result" section of
`docs/superpowers/specs/2026-07-28-adjudant-token-discipline-design.md`:

```markdown
### Measured after implementation (2026-07-28)

| surface | before | after |
|---|---|---|
| SKILL.md | ~3050 | <measured> |
| reference/vault-standards.md | ~3539 | <measured> |
| reference/voice.md | ~853 | <measured> |

Totals from `token_budget.py`: <total> tokens across <n> surfaces,
<over_count> over budget.
```

Substitute every `<...>` with the Step 1 output as you write the block. A spec
that predicts without recording is half a document; a spec containing a
literal `<measured>` is worse than either.

- [ ] **Step 5: Bump the version**

```bash
python3 scripts/bump_plugin_version.py adjudant 0.17.0
```
This writes `plugin.json`, `scripts/command-metadata.json`, `SKILL.md` frontmatter, and the `marketplace.json` entry atomically.

- [ ] **Step 6: Final verification**

Run: `cd adjudant/scripts && python3 -m unittest discover -s . -p "test_*.py" 2>&1 | tail -3 && cd .. && python3 scripts/validate.py 2>&1 | tail -1`
Expected: `OK` and `PASS — 30 validator(s) green`.

- [ ] **Step 7: Commit the release**

```bash
git add -A adjudant/ .claude-plugin/ docs/
git commit -m "$(cat <<'EOF'
release(adjudant): v0.17.0 - token discipline: write gate, SKILL split, standards trim, budget report

93% of a verb's context cost was static prose that is byte-identical every
time, while the v0.14.0 cost gate guarded only the 7% that is actual data.
This release cuts the prose without trading away compliance, on the principle
that a rule enforced mechanically need not be spent in context.

- PreToolUse schema gate: vault writes are checked against FIELD_SCHEMA
  before they land, so the write path enforces what prose only reminded about
- SKILL.md sheds its background tables to reference/internals.md
- vault-standards.md and voice.md state each rule's shape and name its
  enforcer instead of restating enforceable detail
- token_budget.py reports per-surface cost in check repo (report only)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

**Spec coverage.** Component 1 (write gate) → Tasks 1 + 2. Component 2 (SKILL split) → Task 3. Component 3 (standards + voice trim) → Task 4. Component 4 (budget report) → Task 5. Testing section → tests inside each task, gate branches enumerated in Task 2. Truth pass → Task 6. The spec's follow-up (staged escalation for the four monster projects) is deliberately out of scope and stays in the spec's follow-up section.

**Placeholder scan.** One deliberate placeholder remains, in Task 6 Step 4, where the plan cannot know the post-trim byte counts in advance; the step instructs measuring first and states the numbers must be replaced before commit. Every code block elsewhere is complete.

**Type consistency.** `schema_drift_for_text(text, rel_path, aliases=None)` is defined in Task 1 and called in Task 2 with two positional arguments. `_schema_drift_core` is used only inside `_vault_walk.py`. `report(skill_root)` is defined in Task 5 and imported into `repo_scan.py` as `token_budget_report` in the same task. `BUDGETS` and `BANNED_LEXICON` are both module-level constants asserted by tests in the tasks that create them.
