"""Tests for adjudant/scripts/port.py."""

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from port import detect_flavor


class TestDetectFlavor(unittest.TestCase):
    def test_raw_repo_returns_x(self):
        """An empty project dir (no breadcrumb, no AGENTS.md) is flavor X."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_flavor(Path(tmp)), "X")

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

    def test_compliant_without_backup_dir_still_applied(self):
        """Regression: a compliant project whose backup dir was cleaned/gitignored
        must NOT be re-detected as legacy and re-migrated."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "adjudant").write_text("vault_path: /tmp/v\nvault_name: v\nslug: x\nmode: project\n")
            (root / "AGENTS.md").write_text("# Real Project\n\nAuthored content, not template.\n")
            (root / "CLAUDE.md").write_text("@AGENTS.md\n")
            self.assertEqual(detect_flavor(root), "applied")

    def test_obsidian_bridge_breadcrumb_returns_y(self):
        """If .claude/obsidian-bridge breadcrumb exists, flavor is Y."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text("vault: /tmp/v\nslug: legacy-proj\n")
            self.assertEqual(detect_flavor(root), "Y")

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

    def test_walk_up_accepts_the_v3_index_marker(self):
        """v3's templates/home.md declares `type: index`; port must still find
        the vault it marks."""
        with tempfile.TemporaryDirectory() as parent:
            vault_root = Path(parent)
            (vault_root / "Home.md").write_text("---\ntype: index\n---\n\n# Vault\n")
            child = vault_root / "projects" / "myproject"
            child.mkdir(parents=True)
            self.assertEqual(resolve_vault_path(child), vault_root)

    def test_none_returned_when_unresolvable(self):
        """No env var, no breadcrumbs, no Home.md anywhere up → returns None."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(resolve_vault_path(Path(tmp)))


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


from port import map_ob_sections


class TestMapObSections(unittest.TestCase):
    def test_working_tree_maps_to_where_things_live_row(self):
        ob_sections = {"working tree": "/path/to/repo"}
        result = map_ob_sections(ob_sections)
        self.assertIn("/path/to/repo", result["where_things_live_extra_rows"])

    def test_working_tree_formatted_as_table_row(self):
        result = map_ob_sections({"working tree": "/path/to/repo"})
        # Must be a complete markdown table row, not a raw path
        rows = result["where_things_live_extra_rows"].splitlines()
        self.assertTrue(any(r.startswith("|") and r.endswith("|") and "/path/to/repo" in r for r in rows),
                        f"Expected table row containing path, got: {result['where_things_live_extra_rows']!r}")

    def test_stack_maps_to_conventions(self):
        ob_sections = {"stack": "Node 22, pnpm, Vite"}
        result = map_ob_sections(ob_sections)
        self.assertIn("Node 22, pnpm, Vite", result["conventions"])

    def test_vault_rules_dropped(self):
        ob_sections = {"vault rules": "Use [[Title|Alias]] form"}
        result = map_ob_sections(ob_sections)
        self.assertEqual(result["conventions"], "")
        self.assertEqual(result["where_things_live_extra_rows"], "")
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
        self.assertIn("| Working tree | (this folder) |", result)


from port import generate_preview_y


class TestGeneratePreviewY(unittest.TestCase):
    def test_y_preview_writes_all_required_files(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text(
                f"vault: {vault}\nslug: legacy-proj\n"
            )
            (root / "AGENTS.md").write_text(
                "# Legacy Project\n\n## Working tree\n\n/path/to/legacy\n\n"
                "## Stack\n\nNode 22, pnpm\n\n## Vault rules\n\nUse wikilinks\n"
            )
            (root / "CLAUDE.md").write_text("# Old\n\n## Bash allowlist\n\n- npm, pnpm, git\n")
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
            self.assertNotIn("Use wikilinks", agents)

            summary = (preview / "summary.md").read_text()
            self.assertIn("Flavor: Y", summary)
            self.assertIn("Vault rules", summary)
            self.assertIn("DROPPED", summary)

    def test_y_brief_md_proposed_has_adjudant_shape(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text(f"vault: {vault}\nslug: p\n")
            (root / "AGENTS.md").write_text("# P\n")
            # Pre-populate OB-shaped vault brief
            (Path(vault) / "projects" / "p").mkdir(parents=True)
            (Path(vault) / "projects" / "p" / "brief.md").write_text(
                "---\ntype: project-brief-ob\nslug: p\n---\n\n# P Brief\n\nOriginal content.\n"
            )
            generate_preview_y(root, vault_path=Path(vault), project_type="coding", project_name="P")
            proposed_brief = (root / ".adjudant-port-preview" / "brief.md.proposed")
            self.assertTrue(proposed_brief.is_file())
            text = proposed_brief.read_text()
            self.assertIn("type: project", text)              # canonical template shape
            self.assertNotIn("type: project-brief-ob", text)
            self.assertIn("Original content.", text)
            # v3: the block comes from templates/brief.md, which declares
            # type/created/updated/verified/verified_by and nothing else. The
            # five fields port used to declare inline (project_type, slug,
            # aliases, status, a project tag) are not `project` fields.
            keys = {ln.split(":", 1)[0] for ln in text.split("---")[1].splitlines() if ":" in ln}
            self.assertEqual(keys, {"type", "created", "updated",
                                    "verified", "verified_by"})

    def test_y_apply_actually_replaces_brief_md(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text(f"vault: {vault}\nslug: p\n")
            (root / "AGENTS.md").write_text("# P\n")
            (root / "CLAUDE.md").write_text("# P claude\n")
            (Path(vault) / "projects" / "p").mkdir(parents=True)
            (Path(vault) / "projects" / "p" / "brief.md").write_text(
                "---\ntype: project-brief-ob\n---\n\n# P\n\nOld content.\n"
            )
            generate_preview_y(root, vault_path=Path(vault), project_type="coding", project_name="P")
            apply_preview(root)
            new_brief = (Path(vault) / "projects" / "p" / "brief.md").read_text()
            self.assertIn("type: project", new_brief)         # canonical template shape
            self.assertNotIn("type: project-brief-ob", new_brief)
            self.assertNotIn("project_type:", new_brief)      # v3 dropped it
            self.assertIn("Old content.", new_brief)

    def test_y_claude_md_heading_uses_first_letter_capitalization_only(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text(f"vault: {vault}\nslug: p\n")
            (root / "AGENTS.md").write_text("# P\n")
            (root / "CLAUDE.md").write_text("# Old\n\n## bash allowlist\n\n- npm\n")
            generate_preview_y(root, vault_path=Path(vault), project_type="coding", project_name="P")
            claude_proposed = (root / ".adjudant-port-preview" / "CLAUDE.md.proposed").read_text()
            self.assertIn("## Bash allowlist", claude_proposed)
            self.assertNotIn("## Bash Allowlist", claude_proposed)


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
            agents_proposed = (preview / "AGENTS.md.proposed")
            self.assertTrue(agents_proposed.is_file())
            self.assertIn("TODO: Claude AI classifier fills this", agents_proposed.read_text())
            self.assertTrue((preview / "legacy-AGENTS.md").is_file())
            self.assertIn("Go", (preview / "legacy-AGENTS.md").read_text())


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


class TestGeneratePreviewXBriefIsFile(unittest.TestCase):
    """Bug 1 regression: brief.md must be created as a FILE, not a directory."""

    def test_brief_md_created_as_file_not_directory(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            generate_preview_x(
                root,
                vault_path=Path(vault),
                slug="myproj",
                project_type="coding",
                project_name="My Project",
            )
            # Create the vault project dir so apply_preview has a parent to work in
            (Path(vault) / "projects" / "myproj").mkdir(parents=True)
            apply_preview(root)
            brief = Path(vault) / "projects" / "myproj" / "brief.md"
            self.assertTrue(brief.exists(), "brief.md should exist after apply_preview")
            self.assertTrue(brief.is_file(), "brief.md must be a FILE, not a directory")
            content = brief.read_text()
            self.assertIn("type: project", content)          # canonical template shape
            # v3: the regen stub is rendered from templates/brief.md. The copy
            # that used to stand in port.py stamped `project_type: coding` on
            # every project it regenerated, whatever the project was, and the
            # v3 `project` kind has no such field.
            self.assertNotIn("project_type:", content)
            self.assertIn("# myproj", content)
            self.assertIn("## Where things are", content)


from port import apply_preview, _apply_vault_change


class TestVaultSideBackup(unittest.TestCase):
    """Regression: REPLACE-FROM-PROPOSED overwrote existing vault files with no
    backup while the summary claimed 'Originals backed up'."""

    def test_replace_backs_up_existing_vault_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preview = root / ".adjudant-port-preview"
            preview.mkdir()
            (preview / "brief.md.proposed").write_text("# new brief\n")
            vault_proj = root / "vault" / "projects" / "demo"
            vault_proj.mkdir(parents=True)
            live = vault_proj / "brief.md"
            live.write_text("# ORIGINAL brief — must survive in backup\n")

            _apply_vault_change(f"REPLACE-FROM-PROPOSED:{live}:brief.md.proposed", preview_dir=preview)

            self.assertEqual(live.read_text(), "# new brief\n")
            backup = root / ".adjudant-port-backup" / "vault" / "demo__brief.md.legacy"
            self.assertTrue(backup.is_file(), "vault-side original must be backed up as .legacy")
            self.assertIn("ORIGINAL brief", backup.read_text())

    def test_replace_over_nonexistent_file_makes_no_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preview = root / ".adjudant-port-preview"
            preview.mkdir()
            (preview / "brief.md.proposed").write_text("# new brief\n")
            vault_proj = root / "vault" / "projects" / "demo"
            vault_proj.mkdir(parents=True)
            live = vault_proj / "brief.md"

            _apply_vault_change(f"REPLACE-FROM-PROPOSED:{live}:brief.md.proposed", preview_dir=preview)

            self.assertEqual(live.read_text(), "# new brief\n")
            self.assertFalse((root / ".adjudant-port-backup").exists())


class TestStalenessGuard(unittest.TestCase):
    """reference/port.md: 'AGENTS.md changed since preview generated → warn'."""

    def _preview(self, root: Path, vault: str) -> None:
        (root / ".claude").mkdir()
        (root / ".claude" / "obsidian-bridge").write_text(f"vault: {vault}\nslug: p\n")
        (root / "AGENTS.md").write_text("# P original\n")
        (root / "CLAUDE.md").write_text("# P claude\n")
        (Path(vault) / "projects" / "p").mkdir(parents=True)
        generate_preview_y(root, vault_path=Path(vault), project_type="coding", project_name="P")

    def test_preview_writes_source_hash(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            self._preview(root, vault)
            h = root / ".adjudant-port-preview" / "source-hash.txt"
            self.assertTrue(h.is_file())
            self.assertEqual(len(h.read_text().strip()), 64)  # sha256 hex

    def test_apply_aborts_when_agents_md_changed(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            self._preview(root, vault)
            (root / "AGENTS.md").write_text("# P EDITED after preview\n")
            with self.assertRaises(RuntimeError) as ctx:
                apply_preview(root)
            self.assertIn("re-run the preview", str(ctx.exception))
            self.assertIn("# P EDITED after preview", (root / "AGENTS.md").read_text())  # untouched

    def test_apply_proceeds_when_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            self._preview(root, vault)
            apply_preview(root)  # no raise
            self.assertFalse((root / ".adjudant-port-preview").exists())

    def test_old_preview_without_hash_still_applies(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            self._preview(root, vault)
            (root / ".adjudant-port-preview" / "source-hash.txt").unlink()  # legacy preview
            (root / "AGENTS.md").write_text("# P edited\n")
            apply_preview(root)  # backward compat: no guard, no raise

    def test_apply_aborts_when_claude_md_changed(self):
        # Audit 2026-07-27 finding 15: the guard hashed AGENTS.md only, so
        # CLAUDE.md edits between preview and apply were silently clobbered.
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            self._preview(root, vault)
            (root / "CLAUDE.md").write_text("# EDITED claude after preview\n")
            with self.assertRaises(RuntimeError) as ctx:
                apply_preview(root)
            self.assertIn("re-run the preview", str(ctx.exception))
            self.assertIn("# EDITED claude after preview",
                          (root / "CLAUDE.md").read_text())


class TestVaultChangePreflight(unittest.TestCase):
    """Audit 2026-07-27 finding 10: apply wrote project files first, then ran
    vault changes with no rollback. A colliding RENAME raised mid-loop and the
    vault stayed half-migrated — permanently, because the staleness guard then
    blocked retry and re-previewing reported 'Already ported'."""

    def _preview_with_rename(self, root: Path, vault: str) -> Path:
        (root / ".claude").mkdir()
        (root / ".claude" / "obsidian-bridge").write_text(f"vault: {vault}\nslug: p\n")
        (root / "AGENTS.md").write_text("# P original\n")
        (root / "CLAUDE.md").write_text("# P claude\n")
        proj = Path(vault) / "projects" / "p"
        (proj / "refs").mkdir(parents=True)
        (proj / "refs" / "a.md").write_text("ref\n")
        generate_preview_y(root, vault_path=Path(vault), project_type="coding",
                           project_name="P")
        return proj

    def test_colliding_rename_refuses_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            proj = self._preview_with_rename(root, vault)
            changes = root / ".adjudant-port-preview" / "vault-changes.txt"
            if "RENAME" not in changes.read_text():
                changes.write_text(
                    changes.read_text()
                    + f"RENAME:{proj / 'refs'}:{proj / 'references'}\n")
            (proj / "references").mkdir()
            (proj / "references" / "existing.md").write_text("do not lose me\n")

            agents_before = (root / "AGENTS.md").read_text()
            with self.assertRaises(RuntimeError) as ctx:
                apply_preview(root)
            self.assertIn("NOTHING was changed", str(ctx.exception))
            # Nothing touched, on either side.
            self.assertEqual((root / "AGENTS.md").read_text(), agents_before)
            self.assertTrue((proj / "refs").is_dir())
            self.assertEqual((proj / "references" / "existing.md").read_text(),
                             "do not lose me\n")
            # And the preview survives, so a retry is possible after fixing.
            self.assertTrue((root / ".adjudant-port-preview").is_dir())

    def test_retry_succeeds_once_the_conflict_is_resolved(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            proj = self._preview_with_rename(root, vault)
            changes = root / ".adjudant-port-preview" / "vault-changes.txt"
            if "RENAME" not in changes.read_text():
                changes.write_text(
                    changes.read_text()
                    + f"RENAME:{proj / 'refs'}:{proj / 'references'}\n")
            (proj / "references").mkdir()
            with self.assertRaises(RuntimeError):
                apply_preview(root)
            shutil.rmtree(proj / "references")   # resolve the conflict
            apply_preview(root)                  # no raise
            self.assertFalse((root / ".adjudant-port-preview").exists())


class TestSlugHandling(unittest.TestCase):

    def test_invalid_slug_rejected_in_preview_phase(self):
        from port import main as port_main
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            rc = port_main(["preview", "--project-root", tmp,
                            "--vault-path", vault, "--slug", "Bad Slug!"])
            self.assertEqual(rc, 1)

    def test_explicit_slug_overrides_ob_breadcrumb_for_y(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text(f"vault: {vault}\nslug: old-slug\n")
            (root / "AGENTS.md").write_text("# P\n")
            generate_preview_y(root, vault_path=Path(vault), project_type="coding",
                               project_name="P", slug="new-slug")
            summary = (root / ".adjudant-port-preview" / "summary.md").read_text()
            self.assertIn("new-slug", summary)
            self.assertNotIn("old-slug", summary)

    def _legacy_repo(self, root: Path, slug: str) -> tuple[Path, Path]:
        vault = root / "vault"
        (vault / "projects").mkdir(parents=True)
        repo = root / "repo"
        (repo / ".claude").mkdir(parents=True)
        (repo / ".claude" / "obsidian-bridge").write_text(
            f"vault: {vault}\nslug: {slug}\n")
        (repo / "AGENTS.md").write_text("# P\n\n## Stack\n\nNode\n")
        return repo, vault

    def test_traversal_slug_in_the_legacy_breadcrumb_is_refused(self):
        """The `--slug` CLI arg is validated but the LEGACY `obsidian-bridge`
        breadcrumb's slug was not, and it is the fallback when --slug is
        omitted. Unfixed, `slug: ../../escaped` made the preview emit CREATE
        and REGEN operations pointing outside the vault, and apply executed
        them with mkdir(parents=True) + write_text.
        """
        from port import main as port_main
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, vault = self._legacy_repo(root, "../../escaped")
            rc = port_main(["preview", "--project-root", str(repo),
                            "--vault-path", str(vault)])
            if rc == 0:
                port_main(["apply", "--project-root", str(repo)])
            self.assertFalse(
                (root / "escaped").exists(),
                "port created a directory outside the vault")
            self.assertEqual(rc, 1, "port accepted a traversal slug")

    def test_a_safe_legacy_slug_still_previews(self):
        from port import main as port_main
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, vault = self._legacy_repo(root, "legacy-proj")
            rc = port_main(["preview", "--project-root", str(repo),
                            "--vault-path", str(vault)])
            self.assertEqual(rc, 0)
            self.assertIn(
                "legacy-proj",
                (repo / ".adjudant-port-preview" / "summary.md").read_text())


class TestApplyPreviewGuards(unittest.TestCase):
    """Bug 2 regression: apply_preview must reject corrupt/unfilled previews."""

    def _make_valid_preview(self, root: Path, vault: str) -> None:
        """Write a complete, valid preview dir."""
        generate_preview_x(
            root,
            vault_path=Path(vault),
            slug="proj",
            project_type="coding",
            project_name="Proj",
        )

    def test_apply_raises_if_required_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            self._make_valid_preview(root, vault)
            # Remove one required file
            (root / ".adjudant-port-preview" / "summary.md").unlink()
            with self.assertRaises(RuntimeError) as ctx:
                apply_preview(root)
            self.assertIn("summary.md", str(ctx.exception))
            self.assertIn("corrupt", str(ctx.exception))

    def test_apply_raises_if_proposed_file_is_todo_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            self._make_valid_preview(root, vault)
            # Overwrite AGENTS.md.proposed with TODO placeholder (simulates skipped Z classifier)
            (root / ".adjudant-port-preview" / "AGENTS.md.proposed").write_text(
                "TODO: Claude AI classifier fills this. See reference/port.md for instructions.\n"
            )
            with self.assertRaises(RuntimeError) as ctx:
                apply_preview(root)
            self.assertIn("TODO", str(ctx.exception))
            self.assertIn("AI classifier", str(ctx.exception))


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


class TestApplyPreview(unittest.TestCase):
    def test_apply_writes_proposed_to_live_positions(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "obsidian-bridge").write_text("vault: " + vault + "\nslug: p\n")
            (root / "AGENTS.md").write_text("# Old\n\n## Stack\n\nGo\n")
            (root / "CLAUDE.md").write_text("# Old claude\n")

            generate_preview_y(root, vault_path=Path(vault), project_type="coding", project_name="P")
            (Path(vault) / "projects" / "p").mkdir(parents=True)

            apply_preview(root)

            self.assertIn("Go", (root / "AGENTS.md").read_text())
            self.assertTrue((root / ".claude" / "adjudant").is_file())
            self.assertFalse((root / ".claude" / "obsidian-bridge").exists())
            self.assertFalse((root / ".adjudant-port-preview").exists())
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


from port import _upsert_project_index_row


class TestUpsertProjectIndexRow(unittest.TestCase):
    """The vault projects/_index.md varies wildly across real vaults.
    These tests verify the conservative-write behavior."""

    SIX_COL_HEADER = "| Project | Type | Status | Decisions | Sessions | Last Session |"

    def test_creates_canonical_six_column_index_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            idx = Path(tmp) / "projects" / "_index.md"
            _upsert_project_index_row(idx, "newproj")
            self.assertTrue(idx.is_file())
            text = idx.read_text()
            self.assertIn(self.SIX_COL_HEADER, text)
            # connect's canonical form: index-relative link, escaped alias pipe
            self.assertIn("[[newproj/brief\\|newproj]]", text)
            self.assertNotIn("[[projects/newproj/brief|newproj]]", text)  # old broken-table form
            self.assertNotIn("| Slug | Brief |", text)  # never the legacy 2-column shape

    def test_idempotent_when_slug_already_referenced(self):
        with tempfile.TemporaryDirectory() as tmp:
            idx = Path(tmp) / "projects" / "_index.md"
            idx.parent.mkdir()
            original = (
                "# All Projects\n\n" + self.SIX_COL_HEADER + "\n|---|---|---|---|---|---|\n"
                "| [[projects/hubspot/brief|hubspot]] | coding | active | 3 | 5 | 2026-05-01 |\n"
            )
            idx.write_text(original)
            _upsert_project_index_row(idx, "hubspot")
            self.assertEqual(idx.read_text(), original)  # already listed -> no change

    def test_skips_write_on_unknown_format(self):
        """A richer/custom header is left untouched rather than corrupted."""
        with tempfile.TemporaryDirectory() as tmp:
            idx = Path(tmp) / "projects" / "_index.md"
            idx.parent.mkdir()
            original = "# Custom\n\n| Name | Owner |\n|---|---|\n| other | tom |\n"
            idx.write_text(original)
            _upsert_project_index_row(idx, "newproj")
            self.assertEqual(idx.read_text(), original)

    def test_appends_six_column_row_into_canonical_index(self):
        """The regression: appending into a real 6-column index adds ONE row, no second table."""
        with tempfile.TemporaryDirectory() as tmp:
            idx = Path(tmp) / "projects" / "_index.md"
            idx.parent.mkdir()
            original = (
                "# All Projects\n\n" + self.SIX_COL_HEADER + "\n|---|---|---|---|---|---|\n"
                "| [[projects/existing/brief|existing]] | coding | active | 2 | 4 | 2026-04-30 |\n"
            )
            idx.write_text(original)
            _upsert_project_index_row(idx, "newproj")
            text = idx.read_text()
            self.assertIn("[[projects/existing/brief|existing]]", text)   # existing preserved
            self.assertIn("[[newproj/brief\\|newproj]]", text)            # new row, escaped form
            self.assertEqual(text.count(self.SIX_COL_HEADER), 1)          # exactly one table
            self.assertNotIn("| Slug | Brief |", text)

    def test_idempotent_against_connect_written_row(self):
        """Cross-writer regression: connect writes `[[{slug}/brief\\|{slug}]]`
        (escaped, index-relative). port must recognize that row and not duplicate."""
        with tempfile.TemporaryDirectory() as tmp:
            idx = Path(tmp) / "projects" / "_index.md"
            idx.parent.mkdir()
            original = (
                "# All Projects\n\n" + self.SIX_COL_HEADER + "\n|---|---|---|---|---|---|\n"
                "| [[hubspot/brief\\|hubspot]] | coding | active | 3 | 5 | 2026-05-01 |\n"
            )
            idx.write_text(original)
            _upsert_project_index_row(idx, "hubspot")
            self.assertEqual(idx.read_text(), original)  # recognized -> no duplicate

    def test_row_never_contains_unescaped_pipe_in_wikilink(self):
        """Regression: an unescaped `|` inside the wikilink splits the table cell."""
        with tempfile.TemporaryDirectory() as tmp:
            idx = Path(tmp) / "projects" / "_index.md"
            _upsert_project_index_row(idx, "demo")
            row_line = next(ln for ln in idx.read_text().splitlines() if "demo" in ln)
            # 6 columns -> exactly 7 unescaped pipes
            unescaped = re.findall(r"(?<!\\)\|", row_line)
            self.assertEqual(len(unescaped), 7, row_line)


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


if __name__ == "__main__":
    unittest.main()
