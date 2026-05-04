# Attributions

Third-party content redistributed under this plugin.

## Skills imported from upstream

| Skill (this plugin) | Upstream source | Redistribution path |
|---|---|---|
| `bases` | https://github.com/kepano/obsidian-skills | antigravity-awesome-skills |
| `markdown` | https://github.com/kepano/obsidian-skills | antigravity-awesome-skills |
| `cli` | https://github.com/kepano/obsidian-skills | antigravity-awesome-skills |
| `clipper-template` | community (per upstream metadata) | antigravity-awesome-skills |

Body content of each `SKILL.md` (and its `references/`, `assets/`) is verbatim from upstream. Frontmatter (`name`, `description`) was rewritten for this plugin's namespace.

A short **schema-gate preamble** has been added at the top of `bases`, `markdown`, and `clipper-template` SKILL.md (one blockquote line, between the closing `---` and the upstream H1) pointing at this plugin's canonical schema (`obsidian-bridge:vault-standards`) and, where relevant, the `obsidian-bridge:mermaid` skill. This is a plugin-level annotation; the upstream body and reference files remain untouched.

## Original skills (not imported)

These ship under `obsidian-bridge` and are original to this plugin:

| Skill | Notes |
|---|---|
| `vault-bridge` | Vault operations dispatched by `/vault-bridge` command. |
| `dream` | Two-pass vault analysis dispatched by `/dream` command. |
| `vault-standards` | Canonical schema (frontmatter, naming, tags, wikilinks, file-type templates). Promoted from `references/vault-standards.md` so it loads as active model knowledge whenever frontmatter is touched. |
| `mermaid` | Reference for Mermaid diagram syntax across all common types, with Obsidian-specific rendering notes and pitfalls. |
| `canvas` | Reference for the JSON Canvas v1 file format (`.canvas`) and Obsidian's Canvas plugin. Sourced from <https://help.obsidian.md/plugins/canvas> and <https://jsoncanvas.org/spec/1.0/>. |
| `search` | Reference for Obsidian's search query syntax (operators, property filters, regex, embedded `query` blocks). Sourced from <https://help.obsidian.md/plugins/search>. |

## Authoritative-reference pointers

The following per-skill `references/` files index official Obsidian documentation
(both online and within the user's local Obsidian Help vault, if present). They
are pointer files — content is by reference, not duplication:

- `skills/bases/references/AUTHORITATIVE_REFERENCE.md`
- `skills/markdown/references/AUTHORITATIVE_REFERENCE.md`
- `skills/vault-standards/references/OBSIDIAN_PROPERTIES_SPEC.md`

## Upstream: Obsidian Help vault

Several skills cite or quote the official Obsidian Help vault
(<https://github.com/obsidianmd/obsidian-help>), licensed under
**Creative Commons Attribution 4.0 International (CC BY 4.0)** — see
<https://creativecommons.org/licenses/by/4.0/>. Where this plugin paraphrases
or quotes from those docs (notably in `canvas` and `search` SKILL.md), the
source URL is in each skill's frontmatter `source:` field.

JSON Canvas spec is open-source under MIT — see <https://jsoncanvas.org/>.

## Licenses

Upstream content is dual-licensed by `antigravity-awesome-skills`:

- Code: **MIT License** — see https://github.com/jhillyerd/antigravity-awesome-skills/blob/main/LICENSE
- Documentation / SKILL.md text: **Creative Commons Attribution 4.0 International (CC BY 4.0)** — see https://creativecommons.org/licenses/by/4.0/

Original upstream (kepano) repository licensing:
- https://github.com/kepano/obsidian-skills

This plugin (`obsidian-bridge`) is licensed MIT. See `../LICENSE` at the marketplace root.

## How to refresh

To re-sync upstream changes:
1. Pull latest `antigravity-awesome-skills` (or `kepano/obsidian-skills` directly).
2. Diff against `skills/{bases,markdown,cli,clipper-template}/` — apply body changes.
3. Leave the rewritten frontmatter (`name`, `description`, `upstream_redistribution`) alone.
4. Preserve the schema-gate preamble blockquote between the frontmatter close and the upstream H1.
