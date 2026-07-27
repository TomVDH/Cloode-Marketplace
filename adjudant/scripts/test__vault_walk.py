"""Tests for adjudant/scripts/_vault_walk.py."""

import tempfile
import unittest
from pathlib import Path

from _vault_walk import (
    Frontmatter,
    Wikilink,
    ProjectContext,
    parse_frontmatter,
    extract_wikilinks,
    extract_inline_tags,
    extract_markdown_md_links,
    walk_project,
    build_vault_index,
    resolve_wikilink,
    parse_breadcrumb,
    resolve_vault,
    resolve_project_from_cwd,
    smart_project_dir,
    VaultUnresolvableError,
    is_bucket_d_tag,
    is_bucket_b_migration,
    BUCKET_A_TYPES,
    BUCKET_B_MIGRATIONS,
)


# ============================================================
# parse_frontmatter
# ============================================================


class TestParseFrontmatter(unittest.TestCase):

    def test_simple_frontmatter(self):
        text = "---\ntype: note\ntitle: Hello\n---\n\nBody here."
        fm, body = parse_frontmatter(text)
        self.assertTrue(fm.has_block)
        self.assertEqual(fm.fields["type"], "note")
        self.assertEqual(fm.fields["title"], "Hello")
        self.assertEqual(body, "\nBody here.")
        self.assertIsNone(fm.parse_error)

    def test_no_frontmatter(self):
        text = "Just body, no frontmatter."
        fm, body = parse_frontmatter(text)
        self.assertFalse(fm.has_block)
        self.assertEqual(fm.fields, {})
        self.assertEqual(body, text)

    def test_missing_closing_delimiter(self):
        text = "---\ntype: note\nno closing delim follows"
        fm, body = parse_frontmatter(text)
        self.assertFalse(fm.has_block)
        self.assertIsNotNone(fm.parse_error)

    def test_quoted_value(self):
        text = '---\ntitle: "Hello: with colon"\nproject: \'simple-quoted\'\n---\n'
        fm, _ = parse_frontmatter(text)
        self.assertEqual(fm.fields["title"], "Hello: with colon")
        self.assertEqual(fm.fields["project"], "simple-quoted")

    def test_null_value_preserved_as_string(self):
        # Per vault-standards §1: `null` is drift (should omit the key).
        # The parser preserves the literal so drift detection can flag it.
        text = "---\ncodename: null\nstatus: active\n---\n"
        fm, _ = parse_frontmatter(text)
        self.assertEqual(fm.fields["codename"], "null")
        self.assertEqual(fm.fields["status"], "active")

    def test_list_value(self):
        text = "---\ntags:\n  - note\n  - decision\n  - ob/doc\n---\n"
        fm, _ = parse_frontmatter(text)
        self.assertEqual(fm.fields["tags"], ["note", "decision", "ob/doc"])

    def test_empty_value_becomes_None(self):
        text = "---\ncodename:\nstatus: active\n---\n"
        fm, _ = parse_frontmatter(text)
        self.assertIsNone(fm.fields["codename"])

    def test_comment_skipped(self):
        text = "---\n# this is a comment\ntype: note\n---\n"
        fm, _ = parse_frontmatter(text)
        self.assertEqual(fm.fields, {"type": "note"})

    def test_piped_wikilink_value_kept_raw(self):
        text = '---\nproject: "[[projects/hubspot-nightly/brief|hubspot-nightly]]"\n---\n'
        fm, _ = parse_frontmatter(text)
        self.assertEqual(fm.fields["project"], "[[projects/hubspot-nightly/brief|hubspot-nightly]]")


# ============================================================
# extract_wikilinks
# ============================================================


class TestExtractWikilinks(unittest.TestCase):

    def test_simple(self):
        body = "Refer to [[my-note]] for details."
        links = extract_wikilinks(body)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].target, "my-note")
        self.assertIsNone(links[0].alias)

    def test_with_alias(self):
        body = "See [[my-note|the note]]."
        links = extract_wikilinks(body)
        self.assertEqual(links[0].target, "my-note")
        self.assertEqual(links[0].alias, "the note")

    def test_escaped_pipe_in_table(self):
        # `[[README\|README]]` is an Obsidian-table escape: target=README, alias=README
        body = "| [[README\\|README]] | description |"
        links = extract_wikilinks(body)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].target, "README")
        self.assertEqual(links[0].alias, "README")

    def test_heading_anchor(self):
        body = "Jump to [[note#Section Two]]."
        links = extract_wikilinks(body)
        self.assertEqual(links[0].target, "note")
        self.assertEqual(links[0].heading, "Section Two")

    def test_inside_fenced_code_block_skipped(self):
        body = (
            "Real [[link-one]]\n"
            "```python\n"
            "x = [[fake-link]]\n"
            "```\n"
            "Real [[link-two]]"
        )
        links = extract_wikilinks(body)
        targets = [l.target for l in links]
        self.assertEqual(targets, ["link-one", "link-two"])

    def test_inside_indented_code_block_skipped(self):
        body = "Real [[a]]\n    x = [[fake]]\n[[b]]"
        links = extract_wikilinks(body)
        targets = [l.target for l in links]
        self.assertEqual(targets, ["a", "b"])

    def test_multiple_on_line(self):
        body = "Compare [[one]] and [[two|the second]]."
        links = extract_wikilinks(body)
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].target, "one")
        self.assertEqual(links[1].target, "two")
        self.assertEqual(links[1].alias, "the second")

    def test_line_numbers(self):
        body = "first\n[[a]]\nthird\n[[b]]\n"
        links = extract_wikilinks(body)
        self.assertEqual(links[0].line, 2)
        self.assertEqual(links[1].line, 4)


# ============================================================
# extract_inline_tags
# ============================================================


class TestExtractInlineTags(unittest.TestCase):

    def test_simple_tag(self):
        body = "Some text with #cool-tag in it."
        self.assertEqual(extract_inline_tags(body), ["cool-tag"])

    def test_namespaced_tag(self):
        body = "Use #content/seafood-companies for that."
        self.assertEqual(extract_inline_tags(body), ["content/seafood-companies"])

    def test_url_not_a_tag(self):
        body = "Visit https://example.com/page#anchor for more."
        self.assertEqual(extract_inline_tags(body), [])

    def test_inside_code_block_skipped(self):
        body = "Tag #real here.\n```\n#fake\n```\n#also-real"
        tags = extract_inline_tags(body)
        self.assertEqual(set(tags), {"real", "also-real"})

    def test_heading_anchor_not_a_tag(self):
        # `#Section` mid-prose IS sometimes a tag-looking heading anchor.
        # We treat it as a tag — there's no reliable disambiguation; vault
        # convention is heading anchors only appear inside wikilinks.
        body = "See section #Section above."
        self.assertEqual(extract_inline_tags(body), ["Section"])


# ============================================================
# extract_markdown_md_links
# ============================================================


class TestExtractMarkdownMdLinks(unittest.TestCase):

    def test_finds_md_link(self):
        body = "See [the note](path/to/note.md) for context."
        out = extract_markdown_md_links(body)
        self.assertEqual(len(out), 1)
        text, path, line = out[0]
        self.assertEqual(text, "the note")
        self.assertEqual(path, "path/to/note.md")

    def test_ignores_non_md_links(self):
        body = "See [docs](https://example.com) and [image](pic.png)."
        out = extract_markdown_md_links(body)
        self.assertEqual(out, [])

    def test_skips_code_blocks(self):
        body = "Real [a](a.md)\n```\n[fake](fake.md)\n```\n[b](b.md)"
        out = extract_markdown_md_links(body)
        paths = [p for _, p, _ in out]
        self.assertEqual(paths, ["a.md", "b.md"])


# ============================================================
# walk_project
# ============================================================


class TestWalkProject(unittest.TestCase):

    def _make_project(self, tmp: Path) -> None:
        (tmp / "brief.md").write_text(
            "---\ntype: project\nslug: test\n---\n\n# Test\n\nBody."
        )
        (tmp / "decisions").mkdir()
        (tmp / "decisions" / "2026-05-26-decide.md").write_text(
            "---\ntype: decision\n---\n\n## Decision\n\nDo X."
        )
        (tmp / "sessions").mkdir()
        (tmp / "sessions" / "2026-05-26.md").write_text(
            "---\ntype: session\n---\n\n## Log\n\n- 10:00 start"
        )
        # _legacy should be skipped by default
        (tmp / "_legacy").mkdir()
        (tmp / "_legacy" / "old.md").write_text(
            "---\ntype: doc\n---\n\nLegacy."
        )
        # .git should be skipped
        (tmp / ".git").mkdir()
        (tmp / ".git" / "ignored.md").write_text("# ignored")

    def test_skips_legacy_and_git_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_project(root)
            files = list(walk_project(root))
            rels = sorted(str(f.rel_path) for f in files)
            self.assertEqual(rels, [
                "brief.md",
                "decisions/2026-05-26-decide.md",
                "sessions/2026-05-26.md",
            ])

    def test_include_legacy_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_project(root)
            files = list(walk_project(root, include_legacy=True))
            rels = sorted(str(f.rel_path) for f in files)
            self.assertIn("_legacy/old.md", rels)
            self.assertNotIn(".git/ignored.md", rels)

    def test_frontmatter_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_project(root)
            files = list(walk_project(root))
            briefs = [f for f in files if f.rel_path.name == "brief.md"]
            self.assertEqual(len(briefs), 1)
            self.assertEqual(briefs[0].frontmatter.fields["type"], "project")
            self.assertEqual(briefs[0].file_type, "project")

    def test_tags_collected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "note.md").write_text(
                "---\ntype: note\ntags:\n  - alpha\n  - beta\n---\n\n"
                "Body with #inline-tag."
            )
            files = list(walk_project(root))
            self.assertEqual(set(files[0].tags), {"alpha", "beta", "inline-tag"})


# ============================================================
# build_vault_index + resolve_wikilink
# ============================================================


class TestVaultIndex(unittest.TestCase):

    def test_resolves_relative_and_bare(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "projects").mkdir()
            (vault / "projects" / "x").mkdir()
            (vault / "projects" / "x" / "brief.md").write_text("# brief")
            idx = build_vault_index(vault)
            # Relative path with extension
            self.assertTrue(resolve_wikilink("projects/x/brief.md", idx))
            # Without extension
            self.assertTrue(resolve_wikilink("projects/x/brief", idx))
            # Bare basename
            self.assertTrue(resolve_wikilink("brief", idx))
            # Non-existent
            self.assertFalse(resolve_wikilink("does/not/exist", idx))

    def test_canvas_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "art.canvas").write_text("{}")
            idx = build_vault_index(vault)
            self.assertTrue(resolve_wikilink("art.canvas", idx))
            self.assertTrue(resolve_wikilink("art", idx))


# ============================================================
# breadcrumb + vault resolution
# ============================================================


class TestBreadcrumb(unittest.TestCase):

    def test_parse_breadcrumb(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "adjudant").write_text(
                "vault_path: /v\nvault_name: v\nslug: x\nmode: project\n"
            )
            bc = parse_breadcrumb(root)
            self.assertEqual(bc["slug"], "x")
            self.assertEqual(bc["vault_path"], "/v")

    def test_resolve_vault_via_breadcrumb(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "adjudant").write_text(
                f"vault_path: {vault}\nvault_name: v\nslug: x\nmode: project\n"
            )
            resolved = resolve_vault(root)
            self.assertEqual(resolved, Path(vault))

    def test_resolve_vault_via_walk_up_to_home_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            (vault / "Home.md").write_text("---\ntype: vault-home\n---\n# Home\n")
            (vault / "projects").mkdir()
            (vault / "projects" / "x").mkdir()
            self.assertEqual(resolve_vault(vault / "projects" / "x"), vault.resolve())

    def test_resolve_vault_env_override(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as vault:
            self.assertEqual(resolve_vault(Path(tmp), env_vault=vault), Path(vault))


# ============================================================
# Schema constants + Bucket D classification
# ============================================================


class TestBucketDClassification(unittest.TestCase):

    def test_ob_prefix_is_bucket_d(self):
        self.assertTrue(is_bucket_d_tag("ob/doc"))
        self.assertTrue(is_bucket_d_tag("ob/session"))
        self.assertTrue(is_bucket_d_tag("ob/project"))

    def test_cabinet_prefix_drops_unless_bucket_b(self):
        # Other cabinet/* — drop
        self.assertTrue(is_bucket_d_tag("cabinet/random"))
        self.assertTrue(is_bucket_d_tag("cabinet/old"))
        # Bucket B migration sources — NOT Bucket D (they survive via migration)
        self.assertFalse(is_bucket_d_tag("cabinet/decision"))
        self.assertFalse(is_bucket_d_tag("cabinet/recon"))

    def test_vague_topicals_dropped(self):
        for t in ["architecture", "frontend", "moc", "scheduler"]:
            self.assertTrue(is_bucket_d_tag(t), f"{t} should be Bucket D")

    def test_crew_names_dropped(self):
        for t in ["bostrol", "kevijntje", "jonasty"]:
            self.assertTrue(is_bucket_d_tag(t))

    def test_project_type_tag_dropped(self):
        self.assertTrue(is_bucket_d_tag("type/coding"))
        self.assertTrue(is_bucket_d_tag("type/plugin"))

    def test_project_slug_self_tag_dropped(self):
        self.assertTrue(is_bucket_d_tag("hubspot-nightly", project_slug="hubspot-nightly"))
        # slug-variant: "slug/sub"
        self.assertTrue(is_bucket_d_tag("hubspot-nightly/sub", project_slug="hubspot-nightly"))
        # slug-variant: "slug-suffix"
        self.assertTrue(is_bucket_d_tag("hubspot-nightly-thing", project_slug="hubspot-nightly"))
        # unrelated tag with no slug context
        self.assertFalse(is_bucket_d_tag("project"))  # Bucket A

    def test_bucket_a_passes_through(self):
        for t in ["decision", "session", "note", "project"]:
            self.assertFalse(is_bucket_d_tag(t))

    def test_bucket_b_migration_lookup(self):
        self.assertEqual(is_bucket_b_migration("cabinet/decision"), "decision")
        self.assertEqual(is_bucket_b_migration("cabinet/recon"), "recon-item")
        self.assertIsNone(is_bucket_b_migration("cabinet/random"))
        self.assertIsNone(is_bucket_b_migration("project"))

    def test_task_type_in_schema(self):
        # task is a first-class file type; its bare #task tag is Bucket A
        self.assertIn("task", BUCKET_A_TYPES)
        self.assertFalse(is_bucket_d_tag("task"))


# ============================================================
# Inline-code wikilink skip (regression: false positive in release notes)
# ============================================================


class TestInlineCodeSkip(unittest.TestCase):

    def test_wikilink_inside_backticks_skipped(self):
        body = "Rewrite `[[stem|text]]` to the canonical form."
        links = extract_wikilinks(body)
        self.assertEqual(links, [])

    def test_wikilink_outside_backticks_kept(self):
        body = "Real [[link]] here."
        links = extract_wikilinks(body)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].target, "link")

    def test_mixed_inline_code_and_real_link(self):
        body = "Use `[[code-example]]` but see [[real-link]]."
        links = extract_wikilinks(body)
        self.assertEqual([l.target for l in links], ["real-link"])

    def test_tag_inside_backticks_skipped(self):
        body = "Use `#sample-tag` as literal; real tag is #real-tag."
        tags = extract_inline_tags(body)
        self.assertEqual(tags, ["real-tag"])

    def test_md_link_inside_backticks_skipped(self):
        body = "Don't link `[a](b.md)` from inside code; do link [c](c.md) outside."
        out = extract_markdown_md_links(body)
        paths = [p for _, p, _ in out]
        self.assertEqual(paths, ["c.md"])


# ============================================================
# Breadcrumb auto-follow (smart_project_dir + resolve_project_from_cwd)
# ============================================================


class TestSmartProjectDir(unittest.TestCase):

    def test_passes_through_when_no_breadcrumb(self):
        with tempfile.TemporaryDirectory() as tmp:
            # No .claude/adjudant — should treat arg as the vault project itself
            scan_dir, vault_hint = smart_project_dir(tmp)
            self.assertEqual(scan_dir, Path(tmp).resolve())
            self.assertIsNone(vault_hint)

    def test_follows_breadcrumb_to_vault_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = Path(tmp) / "code"; code.mkdir()
            vault = Path(tmp) / "vault"; vault.mkdir()
            (vault / "projects").mkdir()
            (vault / "projects" / "p").mkdir()
            (code / ".claude").mkdir()
            (code / ".claude" / "adjudant").write_text(
                f"vault_path: {vault}\nvault_name: vault\nslug: p\nmode: project\n"
            )
            scan_dir, vault_hint = smart_project_dir(str(code))
            self.assertEqual(scan_dir.resolve(), (vault / "projects" / "p").resolve())
            self.assertEqual(vault_hint.resolve(), vault.resolve())

    def test_raises_when_breadcrumb_present_but_vault_unresolvable(self):
        # Regression: this used to fall through and return the CODE REPO as the
        # scan dir, letting write-path verbs (tidy apply) rewrite the repository.
        with tempfile.TemporaryDirectory() as tmp:
            code = Path(tmp) / "code"; code.mkdir()
            (code / ".claude").mkdir()
            (code / ".claude" / "adjudant").write_text(
                f"vault_path: {tmp}/does-not-exist\nvault_name: no-such-vault\nslug: p\nmode: project\n"
            )
            with self.assertRaises(VaultUnresolvableError):
                smart_project_dir(str(code))


class TestRoundThreeRegressions(unittest.TestCase):
    """v0.11.0 primitives fixes."""

    def test_md_link_re_ignores_external_urls(self):
        from _vault_walk import MD_LINK_RE
        line = "see [readme](https://github.com/x/y/blob/main/README.md) and [n](notes/n.md)"
        paths = [m.group(2) for m in MD_LINK_RE.finditer(line)]
        self.assertEqual(paths, ["notes/n.md"])

    def test_embed_flag_set(self):
        links = extract_wikilinks("An embed ![[diagram.png]] and a link [[note]].")
        by_target = {l.target: l for l in links}
        self.assertTrue(by_target["diagram.png"].is_embed)
        self.assertFalse(by_target["note"].is_embed)

    def test_is_checkable_wikilink(self):
        from _vault_walk import is_checkable_wikilink
        links = extract_wikilinks(
            "![[img.png]] [[#Heading]] [[attach.pdf]] [[real-note]] [[art.canvas]]")
        checkable = [l.target for l in links if is_checkable_wikilink(l)]
        self.assertEqual(checkable, ["real-note", "art.canvas"])

    def test_flow_style_tags_parse_as_list(self):
        fm, _ = parse_frontmatter("---\ntags: [project, adjudant]\n---\n")
        self.assertEqual(fm.fields["tags"], ["project", "adjudant"])

    def test_flow_style_empty_list(self):
        fm, _ = parse_frontmatter("---\nstack: []\n---\n")
        self.assertEqual(fm.fields["stack"], [])

    def test_zero_indent_block_list(self):
        fm, _ = parse_frontmatter("---\ntags:\n- a\n- b\n---\n")
        self.assertEqual(fm.fields["tags"], ["a", "b"])

    def test_ob_vault_env_override(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["OB_VAULT"] = tmp
            try:
                self.assertEqual(resolve_vault(Path("/nonexistent-project")), Path(tmp))
            finally:
                del os.environ["OB_VAULT"]

    def test_walk_project_skips_scratch_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes").mkdir()
            (root / "notes" / "real.md").write_text("# real")
            scratch = root / ".adjudant-tidy-preview" / "files" / "notes"
            scratch.mkdir(parents=True)
            (scratch / "pending.md").write_text("# pending")
            names = [f.rel_path.name for f in walk_project(root)]
            self.assertEqual(names, ["real.md"])


class TestResolveProjectFromCwd(unittest.TestCase):

    def test_returns_context_when_breadcrumb_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = Path(tmp) / "code"; code.mkdir()
            vault = Path(tmp) / "vault"; vault.mkdir()
            (vault / "projects" / "p").mkdir(parents=True)
            (code / ".claude").mkdir()
            (code / ".claude" / "adjudant").write_text(
                f"vault_path: {vault}\nvault_name: vault\nslug: p\nmode: project\n"
            )
            ctx = resolve_project_from_cwd(code)
            self.assertIsNotNone(ctx)
            self.assertEqual(ctx.slug, "p")
            self.assertTrue(ctx.is_connected)

    def test_returns_none_without_breadcrumb(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(resolve_project_from_cwd(Path(tmp)))


# ============================================================
# Vault-name cross-machine resolution
# ============================================================


class TestVaultNameResolution(unittest.TestCase):

    def test_vault_name_resolves_when_abs_path_fails(self):
        """If breadcrumb's vault_path is missing/wrong but vault_name matches a
        standard-location vault, resolve_vault should still find it."""
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import patch

            home = Path(tmp)
            (home / "Documents").mkdir()
            vault = home / "Documents" / "MyVault"
            vault.mkdir()

            code = home / "code"; code.mkdir()
            (code / ".claude").mkdir()
            # Absolute path is bogus, vault_name should rescue
            (code / ".claude" / "adjudant").write_text(
                "vault_path: /nope/missing\nvault_name: MyVault\nslug: p\nmode: project\n"
            )

            with patch("pathlib.Path.home", return_value=home):
                resolved = resolve_vault(code)
            self.assertEqual(resolved.resolve(), vault.resolve())


from datetime import date

from _vault_walk import (
    DEFAULT_STALE_DAYS,
    PROJECT_STATUS_VALUES,
    PROJECT_ZONES,
    ZONE_FOR_STATUS,
    enumerate_projects_all_zones,
    find_project_dir,
    newest_dated_stem,
    resolve_project_from_cwd,
    suggest_status,
    zone_matches_status,
    zone_of,
)


def _mk_project(vault: Path, slug: str, zone: str = "", status: str = "active",
                sessions: list = ()) -> Path:
    pdir = vault / "projects" / zone / slug if zone else vault / "projects" / slug
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "brief.md").write_text(
        f"---\ntype: project\nslug: {slug}\nproject_type: coding\nstatus: {status}\n---\n\n# {slug}\n")
    if sessions:
        (pdir / "sessions").mkdir(exist_ok=True)
        for d in sessions:
            (pdir / "sessions" / f"{d}.md").write_text("---\ntype: session\n---\n")
    return pdir


class TestStatusVocabulary(unittest.TestCase):

    def test_locked_values(self):
        self.assertEqual(PROJECT_STATUS_VALUES,
                         ("active", "stale", "fridge", "done", "dead", "seed"))

    def test_zone_map_total(self):
        self.assertEqual(set(ZONE_FOR_STATUS), set(PROJECT_STATUS_VALUES))
        self.assertEqual(ZONE_FOR_STATUS["fridge"], "_fridge")
        self.assertEqual(ZONE_FOR_STATUS["done"], "_archive")
        self.assertEqual(ZONE_FOR_STATUS["dead"], "_archive")
        self.assertEqual(ZONE_FOR_STATUS["active"], "")


class TestSuggestStatus(unittest.TestCase):

    def test_active_goes_stale_after_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _mk_project(Path(tmp), "p", sessions=["2026-05-01"])
            out = suggest_status("active", pdir, date(2026, 7, 16))
            self.assertEqual(out["suggested"], "stale")
            self.assertEqual(out["days_quiet"], 76)
            self.assertIn("76 days", out["reason"])

    def test_active_stays_when_recent(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _mk_project(Path(tmp), "p", sessions=["2026-07-10"])
            out = suggest_status("active", pdir, date(2026, 7, 16))
            self.assertIsNone(out["suggested"])

    def test_stale_suggests_active_on_new_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _mk_project(Path(tmp), "p", status="stale", sessions=["2026-07-15"])
            out = suggest_status("stale", pdir, date(2026, 7, 16))
            self.assertEqual(out["suggested"], "active")

    def test_deliberate_states_never_suggested_away(self):
        with tempfile.TemporaryDirectory() as tmp:
            for status in ("seed", "done", "dead"):
                pdir = _mk_project(Path(tmp), f"p-{status}", status=status,
                                   sessions=["2020-01-01"])
                out = suggest_status(status, pdir, date(2026, 7, 16))
                self.assertIsNone(out["suggested"], status)

    def test_fridge_nudges_after_180_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _mk_project(Path(tmp), "p", status="fridge", sessions=["2025-06-01"])
            out = suggest_status("fridge", pdir, date(2026, 7, 16))
            self.assertIsNone(out["suggested"])
            self.assertIn("still intentional", out["nudge"])

    def test_invalid_declared_flagged_and_treated_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _mk_project(Path(tmp), "p", status="paused", sessions=["2026-01-01"])
            out = suggest_status("paused", pdir, date(2026, 7, 16))
            self.assertFalse(out["declared_valid"])
            self.assertEqual(out["suggested"], "stale")

    def test_no_sessions_no_suggestion(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _mk_project(Path(tmp), "p")
            out = suggest_status("active", pdir, date(2026, 7, 16))
            self.assertIsNone(out["days_quiet"])
            self.assertIsNone(out["suggested"])

    def test_custom_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _mk_project(Path(tmp), "p", sessions=["2026-07-06"])
            out = suggest_status("active", pdir, date(2026, 7, 16), stale_after_days=7)
            self.assertEqual(out["suggested"], "stale")

    def test_malformed_date_cannot_mask_staleness(self):
        # Regression: a lexicographically-larger malformed stem (month 99) must
        # not beat a valid older date and collapse days_quiet to None.
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _mk_project(Path(tmp), "p",
                               sessions=["2026-06-01", "2026-99-01-broken"])
            out = suggest_status("active", pdir, date(2026, 7, 16))
            self.assertEqual(out["last_session"], "2026-06-01")
            self.assertEqual(out["days_quiet"], 45)
            self.assertEqual(out["suggested"], "stale")

    def test_boundary_exactly_at_threshold_goes_stale(self):
        # days_quiet == stale_after_days is the >= edge: suggest stale.
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _mk_project(Path(tmp), "p", sessions=["2026-06-16"])
            out = suggest_status("active", pdir, date(2026, 7, 16))
            self.assertEqual(out["days_quiet"], 30)
            self.assertEqual(out["suggested"], "stale")

    def test_declared_none_flagged_and_treated_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = _mk_project(Path(tmp), "p", sessions=["2026-01-01"])
            out = suggest_status(None, pdir, date(2026, 7, 16))
            self.assertFalse(out["declared_valid"])
            self.assertEqual(out["suggested"], "stale")


class TestZones(unittest.TestCase):

    def test_find_project_dir_across_zones(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "alive")
            _mk_project(vault, "cold", zone="_fridge", status="fridge")
            _mk_project(vault, "gone", zone="_archive", status="dead")
            self.assertEqual(zone_of(find_project_dir(vault, "alive")), "")
            self.assertEqual(zone_of(find_project_dir(vault, "cold")), "_fridge")
            self.assertEqual(zone_of(find_project_dir(vault, "gone")), "_archive")
            self.assertIsNone(find_project_dir(vault, "nope"))

    def test_zone_matches_status(self):
        self.assertTrue(zone_matches_status("fridge", "_fridge"))
        self.assertFalse(zone_matches_status("fridge", ""))
        self.assertTrue(zone_matches_status("active", ""))
        self.assertFalse(zone_matches_status("dead", ""))
        self.assertTrue(zone_matches_status("not-a-status", "_archive"))

    def test_enumerate_all_zones(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            _mk_project(vault, "a")
            _mk_project(vault, "b", zone="_fridge", status="fridge")
            (vault / "projects" / "_index.md").write_text("idx")
            rows = enumerate_projects_all_zones(vault)
            self.assertEqual([(s, z) for s, _p, z in rows], [("a", ""), ("b", "_fridge")])

    def test_resolve_project_from_cwd_finds_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            _mk_project(vault, "proj", zone="_archive", status="done")
            code = root / "code"
            (code / ".claude").mkdir(parents=True)
            (code / ".claude" / "adjudant").write_text(
                f"vault_path: {vault}\nvault_name: vault\nslug: proj\nmode: project\n")
            ctx = resolve_project_from_cwd(code)
            self.assertTrue(ctx.is_connected)
            self.assertEqual(ctx.vault_project_dir,
                             vault / "projects" / "_archive" / "proj")


from _vault_walk import (
    BUCKET_A_TYPES,
    DECISION_STATUS_VALUES,
    FIELD_SCHEMA,
    ITERATION_STATUS_VALUES,
    STATUS_VALUES_FOR_TYPE,
    TASK_STATUS_VALUES,
)


class TestFieldSchema(unittest.TestCase):

    def test_decision_status_values_locked(self):
        self.assertEqual(DECISION_STATUS_VALUES,
                         ("active", "superseded", "reversed", "implemented", "deferred"))

    def test_task_status_values_locked(self):
        self.assertEqual(TASK_STATUS_VALUES,
                         ("todo", "doing", "review", "blocked", "done", "icebox"))

    def test_iteration_status_values_locked(self):
        self.assertEqual(ITERATION_STATUS_VALUES,
                         ("drafting", "on-shelf", "picked", "parked", "rejected", "superseded"))

    def test_status_values_for_type_keys(self):
        self.assertEqual(set(STATUS_VALUES_FOR_TYPE),
                         {"decision", "task", "project", "iteration"})
        self.assertIs(STATUS_VALUES_FOR_TYPE["decision"], DECISION_STATUS_VALUES)
        self.assertIs(STATUS_VALUES_FOR_TYPE["project"], PROJECT_STATUS_VALUES)

    def test_schema_covers_every_bucket_a_type_plus_home(self):
        self.assertEqual(set(FIELD_SCHEMA), set(BUCKET_A_TYPES) | {"vault-home"})

    def test_every_entry_has_required_and_optional_frozensets(self):
        for ftype, spec in FIELD_SCHEMA.items():
            self.assertEqual(set(spec), {"required", "optional"}, ftype)
            self.assertIsInstance(spec["required"], frozenset, ftype)
            self.assertIsInstance(spec["optional"], frozenset, ftype)
            self.assertIn("type", spec["required"], ftype)

    def test_required_and_optional_disjoint(self):
        for ftype, spec in FIELD_SCHEMA.items():
            self.assertFalse(spec["required"] & spec["optional"], ftype)

    def test_project_field_absent_everywhere(self):
        for ftype, spec in FIELD_SCHEMA.items():
            self.assertNotIn("project", spec["required"], ftype)
            self.assertNotIn("project", spec["optional"], ftype)

    def test_decision_shape(self):
        self.assertEqual(FIELD_SCHEMA["decision"]["required"],
                         frozenset({"type", "status", "date", "tags"}))
        self.assertEqual(FIELD_SCHEMA["decision"]["optional"],
                         frozenset({"supersedes", "source_session"}))

    def test_session_requires_session_id(self):
        self.assertIn("session_id", FIELD_SCHEMA["session"]["required"])
        self.assertEqual(FIELD_SCHEMA["session"]["optional"], frozenset())

    def test_project_brief_shape(self):
        self.assertEqual(FIELD_SCHEMA["project"]["required"],
                         frozenset({"type", "project_type", "slug", "aliases",
                                    "status", "created", "updated", "tags"}))
        self.assertIn("codename", FIELD_SCHEMA["project"]["optional"])
        self.assertIn("marketplace", FIELD_SCHEMA["project"]["optional"])


from _vault_walk import (
    DECISION_STATUS_ALIASES,
    VaultFile,
    schema_drift,
    schema_drift_for_file,
)


def _vf(text: str, rel: str = "notes/x.md") -> VaultFile:
    fm, body = parse_frontmatter(text)
    return VaultFile(path=Path("/tmp") / rel, rel_path=Path(rel), frontmatter=fm,
                     body=body, tags_frontmatter=[], tags_inline=[],
                     wikilinks=[], markdown_md_links=[])


_CLEAN_DECISION = (
    "---\ntype: decision\nstatus: active\ndate: 2026-07-27\ntags:\n  - decision\n---\n\nBody\n")


class TestSchemaDrift(unittest.TestCase):

    def test_clean_decision_returns_none(self):
        self.assertIsNone(schema_drift_for_file(_vf(_CLEAN_DECISION)))

    def test_missing_required_flagged(self):
        d = schema_drift_for_file(_vf(_CLEAN_DECISION.replace("date: 2026-07-27\n", "")))
        self.assertEqual(d["missing_required"], ["date"])

    def test_project_field_is_unknown(self):
        d = schema_drift_for_file(_vf(_CLEAN_DECISION.replace(
            "type: decision\n", 'type: decision\nproject: "[[projects/x/brief|x]]"\n')))
        self.assertEqual(d["unknown_fields"], ["project"])

    def test_node_type_beside_type_is_conflict(self):
        d = schema_drift_for_file(_vf(_CLEAN_DECISION.replace(
            "type: decision\n", "type: decision\nnode_type: decision\n")))
        self.assertTrue(d["type_conflict"])
        self.assertIn("node_type", d["unknown_fields"])

    def test_metadata_nest_surfaces_as_single_unknown(self):
        d = schema_drift_for_file(_vf(_CLEAN_DECISION.replace(
            "type: decision\n", "type: decision\nmetadata:\n  node_type: memory\n  foo: bar\n")))
        self.assertEqual(d["unknown_fields"], ["metadata"])

    def test_decision_alias_status_normalizable(self):
        d = schema_drift_for_file(_vf(_CLEAN_DECISION.replace("status: active", "status: accepted")))
        self.assertEqual(d["status_invalid"]["value"], "accepted")
        self.assertTrue(d["status_invalid"]["normalizable"])

    def test_decision_bogus_status_not_normalizable(self):
        d = schema_drift_for_file(_vf(_CLEAN_DECISION.replace("status: active", "status: banana")))
        self.assertFalse(d["status_invalid"]["normalizable"])

    def test_task_alias_status_accepted_with_alias_set(self):
        # Aliases are accepted input (vault-standards section 4): with the
        # alias set supplied a wip task is clean; without it, flagged but
        # never normalizable (tidy must not rewrite lane information).
        task = "---\ntype: task\nstatus: wip\ntags:\n  - task\n---\n"
        self.assertIsNone(schema_drift_for_file(_vf(task), aliases={"wip", "parked"}))
        d = schema_drift_for_file(_vf(task))
        self.assertFalse(d["status_invalid"]["normalizable"])

    def test_session_with_empty_id_list_clean(self):
        s = ("---\ntype: session\ndate: 2026-07-27\nstarted: \"09:00\"\n"
             "session_id: []\ntags:\n  - session\n---\n")
        self.assertIsNone(schema_drift_for_file(_vf(s)))

    def test_decision_alias_map_locked(self):
        self.assertEqual(DECISION_STATUS_ALIASES,
                         {"accepted": "active", "locked": "active", "current": "active"})

    def test_aggregate_counts_and_skips(self):
        files = [
            _vf(_CLEAN_DECISION),                                     # clean
            _vf(_CLEAN_DECISION.replace("date: 2026-07-27\n", "")),   # flagged
            _vf("no frontmatter at all\n"),                           # unchecked
            _vf("---\ntype: tasks\n---\n"),                           # non-canonical type
            _vf("---\ntype: decision\nbroken"),                       # parse error
        ]
        agg = schema_drift(files)
        self.assertEqual(agg["checked"], 2)
        self.assertEqual(agg["unchecked"], 3)
        self.assertEqual(agg["flagged"], 1)
        self.assertEqual(agg["counts"]["missing_required"], 1)
        self.assertEqual(len(agg["samples"]), 1)
        self.assertEqual(agg["samples"][0]["file"], "notes/x.md")


if __name__ == "__main__":
    unittest.main()
