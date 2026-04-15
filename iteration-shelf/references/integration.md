# Integration — iteration-shelf

How this skill behaves when other plugins are active, and how it degrades cleanly when they are not.

---

## 1. Superpowers

Claude Code's Superpowers skill pack supplies several process skills that the shelf generator plugs into.

### 1.1 `full-output-enforcement` — mandatory

When active, every shelf generation follows it. The practical effects:

- **No placeholders in the emitted HTML.** Not `// ...rest of segments`, not `// truncated for brevity`, not `// similarly for the remaining items`. Every segment, every card, every handler attaches in full.
- **No skeleton output.** If the shelf has 130 items, the emitted file has 130 `<div class="card">` blocks. Period.
- **Token-limit handling.** If a single generation would exceed the response budget, use the split protocol:

  ```
  [PAUSED — X of Y segments emitted. Send "continue" to resume from: next segment name]
  ```

  Resume from exactly the next segment boundary. Do not recap what was already emitted.

If Superpowers is not installed, enforce these rules anyway — they are the shelf's deliverable contract, not Superpowers-specific.

### 1.2 `design-taste-frontend`

This skill is the designer behind the iterations. The shelf chrome **overrides** its defaults (terminal aesthetic, not premium). But the indexed iterations themselves may have been produced by `design-taste-frontend` and are not constrained.

Practical rule: do not apply this skill's tokens, motion paradigms, or structural recommendations to the shelf chrome. Apply them to new iterations in their own files.

### 1.3 `high-end-visual-design`

**Explicitly suppressed for the shelf chrome.** The shelf is intentionally terminal-flavoured — no Ethereal Glass, no Editorial Luxury, no Soft Structuralism. If the user asks for a "premium-looking shelf", ask once to confirm they understand the shelf is deliberately not that, and offer to apply the aesthetic to their iteration files instead.

### 1.4 `redesign-existing-projects`

If the target folder already has an index file (`_index.html`, `index.html`, `_iterations.html`), invoke this skill's audit-first pattern before generating a new shelf. The flow:

1. Read the existing file.
2. Identify which patterns are reusable (e.g. segment structure, useful banners).
3. Propose a diff: "keep X, replace Y with the canonical shelf chrome."
4. Generate only after user approval.

### 1.5 `minimalist-ui` / `industrial-brutalist-ui`

The industrial-brutalist skill's aesthetic is close in spirit to the shelf (mono, hairlines, utilitarian) but has different tokens. Do not blend — the shelf has its own palette and it is the source of truth for shelf output.

If the user wants an industrial-brutalist _iteration_ (inside the indexed set), that skill applies to the iteration file, not to the shelf chrome.

---

## 2. Cabinet plugin

When the Cabinet of IMD is active, **Bostrol** owns shelf operations. Bostrol is the documentation-and-process specialist; the shelf is infrastructure, so it falls under his executive authority.

### 2.1 Attribution in chat

Every user-facing line about shelf generation is prefixed with `[Bostrol]:`. Keep it short and factual — Bostrol is dry and organisational.

```
[Bostrol]: Scanning concepts/directions/ — 132 HTML files, 11 prefix families.
[Bostrol]: No manifest found. Drafting iteration-shelf.json from the scan.
[Bostrol]: Emitting _monster-index.html — 12 segments · 132 items.
[Bostrol]: Emitted. Cross-linked to _iterations.html. Done.
```

Do not narrate every file read — just the generation events.

### 2.2 Session note

Writing a shelf is a **session-notable event**. Append to the vault chatter log under `## What we did`:

```markdown
## What we did — {HH:MM}

- Generated iteration shelves for `{target_folder}`
  - `_iterations.html` — {curated_count} items across {segments_with_curated} segments
  - `_monster-index.html` — {total_items} items across {all_segments} segments
- Manifest: `iteration-shelf.json` ({new | updated})
- Cross-linked: `{curated}` ↔ `{monster}`
```

### 2.3 Decision logs

Adding a **new tag slug** (beyond the nine shipped in `card-anatomy.md`) is a decision — not a cosmetic tweak. Log under `decisions/YYYY-MM-DD-shelf-tag-{slug}.md` with:

```markdown
---
type: decision
date: {YYYY-MM-DD}
project: {project}
tags: [iteration-shelf, tag-palette, decision]
---

# Added tag slug: `{slug}`

## Why
{reason the user gave}

## Colour
`{hex}` — lands between {existing slug} and {existing slug} on the palette.

## When to use
{user's written criterion}

## CSS
\`\`\`css
.tag.{slug} { color: {hex}; {optional modifiers}; }
.iter__tag.{slug} { color: {hex}; {optional modifiers}; }
\`\`\`
```

This kicks a decision into the Chroniclers loop. Bostrol announces it:

```
[Bostrol]: New tag slug `{slug}` logged as a decision.
```

### 2.4 Manifest provenance

The manifest (`iteration-shelf.json`) lives at the **project root**, not inside the vault. It is vault-adjacent, not vault-interior — the vault holds session notes and decisions, the project holds generated artefacts.

If the user asks "where does the manifest live?", the answer is always the project root.

### 2.5 Vault-less mode

If the Cabinet is active but no vault is connected, operate silently:

- Still prefix chat lines with `[Bostrol]:`.
- Skip session-note appends (no file to write to).
- Skip decision logs (same).
- Never prompt the user to set up a vault — that's outside the shelf's remit.

### 2.6 Auto-log skeleton

When both the Cabinet and a vault are active, append this to the chatter log at the end of each shelf generation:

```markdown
## Iteration shelf operation — {HH:MM}

- Target: `{target_folder}`
- Segments: {n_segments}
- Items: {n_items}
- Loaded files: `{curated_filename}`, `{monster_filename}`
- New tags added: {list or "none"}
- See: [[iteration-shelf.json]] for manifest
```

The `[[iteration-shelf.json]]` Obsidian link only resolves if the manifest is symlinked into the vault. If not, leave the line as-is — the broken link is a visible reminder to the user to decide where provenance lives.

---

## 3. Standalone mode

No Superpowers, no Cabinet, no vault. The skill runs fine:

- No `[Bostrol]:` prefixes in chat.
- No session notes or decision logs written.
- Still emits both artefact types per the manifest.
- Still follows the deliverable rules (no placeholders, complete output).
- Still respects the browser-safety rules in the monster template.

Standalone is the default path. Integrations are enhancements, not prerequisites.

---

## 4. Conflict resolution

If two plugins each have an opinion on an operation the shelf is performing:

| Opinion source | Priority |
|---|---|
| User's direct instruction | 1 (always wins) |
| `iteration-shelf` skill rules (this plugin) | 2 |
| Superpowers `full-output-enforcement` | 3 (never conflicts; reinforces 2) |
| Superpowers `design-taste-frontend` / aesthetic skills | 4 (applies to iterations, not chrome) |
| Cabinet specialist preferences | 5 (Bostrol is the only active specialist here) |

In practice, conflicts are rare — the shelf owns its chrome; aesthetic skills own their iterations; the Cabinet just narrates.

---

## 5. Multi-plugin examples

### All three active (Superpowers + Cabinet + vault)

```
[Bostrol]: Reading iteration-shelf.json — project dutchbc-portal, 12 segments.
[Bostrol]: Writing _monster-index.html — full output, no placeholders.
{… generation …}
[Bostrol]: Emitted. 132 cards wired. Logged to vault chatter and manifest updated.
```

### Superpowers only, no Cabinet

```
I'll generate both shelves from iteration-shelf.json. Following full-output-enforcement
— the output will be complete, no truncation. Generating _iterations.html first, then
_monster-index.html.

{… generation …}

Done. Wrote 23 cards to the curated shelf and 132 cards to the monster index. Both
cross-linked in their headers.
```

### Pure standalone

```
Reading iteration-shelf.json. Generating both shelves.

{… generation …}

Done — 23 curated cards, 132 monster cards, cross-linked.
```

The behavioural differences are in the narration, not the output.
