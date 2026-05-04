# Obsidian-flavored Markdown — Authoritative reference

Beyond what the kepano-imported SKILL.md, `CALLOUTS.md`, `EMBEDS.md`, and `PROPERTIES.md` cover, the official Obsidian docs go deeper.

## Topic map

| Topic | Online | If you have the Obsidian Help vault locally |
|---|---|---|
| Obsidian Flavored Markdown overview | <https://help.obsidian.md/syntax> | `Editing and formatting/Obsidian Flavored Markdown.md` |
| Basic syntax (headings, emphasis, lists, code, tables, math) | <https://help.obsidian.md/syntax/basic> | `Editing and formatting/Basic formatting syntax.md` |
| Advanced syntax (footnotes, comments, escape chars, math blocks, diagrams) | <https://help.obsidian.md/syntax/advanced> | `Editing and formatting/Advanced formatting syntax.md` |
| Callouts (full type list, nesting, foldable) | <https://help.obsidian.md/callouts> | `Editing and formatting/Callouts.md` |
| Properties (full property type spec, list vs single, validation) | <https://help.obsidian.md/properties> | `Editing and formatting/Properties.md` |
| Tags (nesting, where they're parsed, restrictions) | <https://help.obsidian.md/tags> | `Editing and formatting/Tags.md` |
| HTML inside notes (allowed elements, sandboxing) | <https://help.obsidian.md/syntax/html> | `Editing and formatting/HTML content.md` |
| Embed web pages | <https://help.obsidian.md/syntax/embed-web-pages> | `Editing and formatting/Embed web pages.md` |
| Internal links (`[[wikilinks]]`, anchors, embeds) | <https://help.obsidian.md/links> | `Linking notes and files/Internal links.md` |
| Embed files (`![[...]]` syntax for notes, images, audio, PDF) | <https://help.obsidian.md/links/embed-files> | `Linking notes and files/Embed files.md` |
| Aliases | <https://help.obsidian.md/links/aliases> | `Linking notes and files/Aliases.md` |
| Attachments (paths, attachment folder, drag-and-drop) | <https://help.obsidian.md/syntax/attachments> | `Editing and formatting/Attachments.md` |

## When the kepano SKILL.md isn't enough

Reach for the official docs above when:
- The user wants a callout type the kepano callouts reference doesn't list
- Authoring a property that needs a specific type (date, list of links, checkbox) — Properties.md spec is canonical
- Reconciling tag behavior in code blocks vs body vs frontmatter
- Embedding files that need a specific subpath (heading anchor, block reference)
- Validating that an HTML element will actually render in reading view

## Cross-references

- For diagrams in fenced ```` ```mermaid ```` blocks: `obsidian-bridge:mermaid`
- For canonical vault frontmatter schema: `obsidian-bridge:vault-standards`
- For search query syntax: `obsidian-bridge:search`
