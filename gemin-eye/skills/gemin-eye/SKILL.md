---
name: gemin-eye
description: >
  Invoke Gemini as a second-opinion review and coding partner from inside
  Claude Code. Use when the user says "ask Gemini", "second opinion",
  "Gemini review", "Gemini take", "let's get Gemini's eye on this",
  "/gemin-eye", or otherwise asks for Gemini to weigh in on code, docs,
  architecture, or design. Sources primarily from Claude-provided context,
  generated Markdown, and existing docs in the project or Obsidian vault.
  DOES NOT scaffold new project files unless an explicit override is given.
  All Gemini-specific artefacts go under `gemin-eye/` subfolders inside the
  vault or `docs/` — never scattered across the codebase.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
version: 0.1.0
---

# GeminEye

Gemini as a review and coding partner — invoked from inside Claude Code,
fed deliberate context, and contained to a small writable footprint.

The mental model: **Claude is the architect on the project; Gemini is the
visiting reviewer.** The reviewer reads what's been prepared for them
(briefs, decisions, generated docs, the file under review). They do not
wander the codebase. They do not leave drawings on the walls. Their notes
go in a guest-book folder.

---

## When to use this skill

Trigger on any of:

- Direct command: `/gemin-eye`, `/ask-gemini`
- Phrases: "ask Gemini", "Gemini's take", "second opinion from Gemini",
  "Gemini review", "let's see what Gemini thinks", "run this past Gemini"
- Reviewer scenarios: code review, doc review, architecture sanity check,
  prompt review, design critique, naming bikeshed, "is this approach sane"

Do **not** trigger on:

- General questions about Gemini-the-product, the company, or APIs
- "Gemini" as an astrological sign
- File names that happen to contain "gemini"

---

## Pre-flight

Before the first invocation in a session, verify the CLI is available:

```bash
command -v gemini >/dev/null 2>&1 || {
  echo "gemini CLI not found. Install: https://github.com/google-gemini/gemini-cli"
  exit 1
}
```

If the CLI is missing, do **not** silently fall back to anything else. Tell
Tom and stop. He'll either install it or redirect.

---

## Operating modes

### 1. In-line review (default)

Claude prepares a focused prompt + context bundle, runs `gemini -p "..."`,
captures the response, and presents it inline in the conversation. No file
is written unless the response is substantial enough to be worth keeping.

### 2. CLI review with file context

Pass specific files via Gemini's file flags so Gemini reads them directly:

```bash
gemini -p "Review this for race conditions and naming clarity." \
       --file path/to/file.ts \
       --file path/to/related-spec.md
```

### 3. Persisted review

When the review is meaningful (architectural call, full PR review, repeated
reference material), write the response to the `gemin-eye/` subfolder
(see Output protocol below) and link to it from the vault session log if
vault-bridge is active.

---

## Context sourcing protocol

GeminEye is **context-disciplined**. Always source in this order:

1. **Claude-prepared context** — anything Claude has just generated, written,
   or pasted into the conversation. This is the primary feed. Bundle it
   into the Gemini prompt.

2. **Project-level Markdown** — `docs/`, `README.md`, `CHANGELOG.md`,
   architecture notes, any `*.md` Claude has been working with. Read first,
   then pass the relevant excerpts.

3. **Vault context (if vault-bridge active)** — read from
   `${VAULT}/projects/{slug}/`:
   - `brief.md` — project overview, stack, scope
   - `decisions/` — architectural decisions already taken
   - `sessions/` — recent work history
   - `references/` — domain references collected for this project
   - `gemin-eye/` — prior Gemini reviews on this project (load on demand)

4. **Source code** — only when Tom explicitly names files, or when the
   review target *is* the source. Do not crawl the codebase to "give Gemini
   full context." Keep the bundle tight; Gemini works better with a
   focused prompt than a sprawling dump.

5. **Cross-project context** — if `${VAULT}/gemin-eye/` exists at the vault
   root, treat it as cross-cutting Gemini reference material (style
   preferences, recurring critique patterns Tom has agreed with). Optional.

**Token discipline:** prefer summaries and excerpts over raw dumps. If a
file is over ~200 lines and only one section is relevant, paste the
section, not the file.

---

## Output protocol

Where Gemini's output goes:

| Mode | Destination |
|------|-------------|
| In-line review | Conversation only — no file written |
| Persisted, vault-bridge active | `${VAULT}/projects/{slug}/gemin-eye/{YYYY-MM-DD}-{topic-slug}.md` |
| Persisted, no vault | `docs/gemin-eye/{YYYY-MM-DD}-{topic-slug}.md` |
| Cross-project pattern | `${VAULT}/gemin-eye/{topic}.md` (only on Tom's request) |

**Hard rule:** never write Gemini outputs into source folders, component
folders, or anywhere outside `docs/gemin-eye/` or the vault's `gemin-eye/`
subfolders. If `docs/` does not exist on a non-vault project, create
`docs/gemin-eye/` — this is the one scaffolding action GeminEye is allowed
to take by default.

### File template

```markdown
---
type: gemin-eye-review
date: YYYY-MM-DD
topic: <one-line topic>
target: <file or area reviewed>
model: gemini-<version>
prompt-summary: <one-line summary of what we asked>
---

# Gemini review — <topic>

## Prompt
<verbatim or summarised prompt sent to Gemini>

## Context provided
- <list of files / excerpts / vault refs included>

## Response
<Gemini's response, lightly cleaned of preamble if any>

## Claude's read
<one-paragraph synthesis: what to act on, what to discard, open questions>
```

The "Claude's read" section is required — never persist a raw Gemini
response without Claude's filter on it.

---

## What GeminEye is NOT for

- **Not a code generator for the project.** Gemini does not write source
  files that ship. If Gemini suggests an implementation, Claude evaluates
  and implements it (or doesn't). Gemini's text never lands directly in a
  source file unless Tom explicitly approves.
- **Not a project scaffolder.** No `mkdir`-ing component folders, no
  generating boilerplate files, no creating a `gemini/` config. The only
  scaffold permitted is `docs/gemin-eye/` for outputs.
- **Not a replacement for Claude.** It's a second pair of eyes. Disagreements
  are surfaced to Tom, not silently resolved either way.
- **Not an autonomous agent.** Every Gemini call is initiated by Claude in
  response to a Tom request. No background polling, no "let me also ask
  Gemini" without being asked.

---

## Override clauses

Default containment can be relaxed when Tom explicitly says so. Recognised
overrides:

| Override phrase | What it allows |
|-----------------|----------------|
| "let Gemini scaffold X" | Gemini's output may create files inside `X` (still routed via Claude) |
| "Gemini full project review" | Read across the codebase, not just prepared context |
| "have Gemini write the X file" | A single source file may be written from Gemini's response (Claude reviews first) |
| "skip the gemin-eye folder, just paste it" | In-line only, no persistence |

When an override is invoked, log it in the output file's frontmatter
(`override: <phrase>`) so the relaxation is auditable later.

---

## Pairing with vault-bridge

When `vault-bridge` is active in the same session:

1. **Read** — pull project brief, recent decisions, and last session note
   into the Gemini context bundle automatically.
2. **Write** — persisted reviews go into the project's `gemin-eye/`
   subfolder; create it if missing.
3. **Cross-link** — after persisting, append a one-line link to the current
   session note (`sessions/{date}.md`) under a `## Gemini reviews` heading.
4. **Bostrol's domain.** If the cabinet plugin is also active, treat
   GeminEye outputs as documentation artefacts — Bostrol owns their
   indexing, the same way he owns vault ops. Link Gemini reviews from the
   project decisions index when they materially influence a decision.

If vault-bridge is not active, GeminEye works fine standalone — outputs
just route to `docs/gemin-eye/` instead.

---

## Invocation reference

For full prompt patterns, file-flag usage, model selection, and reusable
prompt scaffolds, read `${CLAUDE_PLUGIN_ROOT}/references/invocation-patterns.md`.

---

## Failure modes

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `gemini: command not found` | CLI not installed | Tell Tom, link install docs, stop |
| Empty / very short response | Prompt too vague or context bundle too thin | Re-prompt with sharper question + more excerpts |
| Response contradicts Claude | Genuine disagreement | Surface both views to Tom; do not auto-resolve |
| Response wants to scaffold | Gemini ignored the constraint | Filter it out in the persisted file's "Claude's read" section |
| Output file would land in src | Bug — stop and ask | Never silently overwrite source paths |

---

## Dependencies

- `gemini` CLI (Google's official Gemini CLI, on `PATH`)
- Optional: `vault-bridge` skill (for vault context auto-loading)
- Optional: `cabinet-of-imd` plugin (for Bostrol-mediated indexing)
