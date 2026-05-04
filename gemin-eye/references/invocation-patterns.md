# Gemini CLI — invocation patterns for GeminEye

Filled-in prompt templates per subcommand, plus CLI usage and edit
format. SKILL.md is enough for in-line work; come here when invoking
a subcommand or persisting a review.

---

## The Template — non-negotiable

Every Gemini call wraps its prompt in this exact structure:

```
ROLE
<one-line statement>

DO
- <specific behaviours>

DON'T
- <specific behaviours forbidden>

SCOPE — IN
- <what's being reviewed>

SCOPE — OUT
- <what to ignore>

OUTPUT
<required format>

CONTEXT
<excerpts / files / briefs>
```

Sections in this order. Headers in caps. Hyphens for bullets. No
prose between sections. No softening language (no "try to", "feel
free", "consider"). Loose prompts get loose reviews.

---

## CLI invocation — sandboxed only

```bash
# Default — flash, sandboxed
gemini --sandbox -m gemini-3.5-flash -p "$(cat prompt.txt)"

# Megareview — pro, sandboxed
gemini --sandbox -m gemini-3.5-pro   -p "$(cat prompt.txt)"

# Multi-file context
gemini --sandbox -m gemini-3.5-flash \
       --file path/to/file.ts \
       --file docs/architecture.md \
       -p "$(cat prompt.txt)"

# Long prompt via stdin
cat prompt.txt | gemini --sandbox -m gemini-3.5-flash \
                        --file path/to/file.ts -
```

**Never** pass `--yolo`. **Never** drop `--sandbox`. **Never** grant
write tools. The folder is not trusted yet — Gemini reviews only.

---

## Edit format — how Gemini proposes changes

When a finding implies an edit, Gemini returns an elaborate code
block. Required shape:

````
PROPOSED EDIT — <relative/path/to/file.ext:line> — <one-line summary>

```<lang>
// BEFORE
<existing code with 3-5 lines of surrounding context>
```

```<lang>
// AFTER
<proposed code with 3-5 lines of surrounding context>
```

WHY
<one-paragraph rationale>
````

Multiple edits in one response: number them `EDIT 1`, `EDIT 2`, etc.
Claude reads each block, evaluates, and applies if approved. Gemini
never writes the file itself.

If a "fix" is too large for a code block (full new file, broad
refactor), Gemini stops and says so — does not propose. That's
Claude's job to escalate to Tom.

---

## Subcommand templates

### `/gemin-eye review <target>`

Single artefact — code, doc, or prompt. Model: flash.

```
ROLE
Senior reviewer doing a focused pass on one artefact.

DO
- Cite line numbers or symbol names for every finding.
- Severity-tag each finding: HIGH / MED / LOW / NIT.
- Use available read tools to pull adjacent context if needed.
- Propose edits as elaborate code blocks (see edit format).
- Prioritise real bugs and unclear intent over style nits.

DON'T
- Write or modify any file.
- Rewrite the artefact in prose.
- Bikeshed naming unless intent is unclear.
- Lecture on conventions.
- Fabricate issues to fill space.

SCOPE — IN
- The single artefact named in CONTEXT.
- Files explicitly listed in CONTEXT as supporting context.

SCOPE — OUT
- Adjacent files not in CONTEXT.
- Repository-wide concerns.
- Future work.

OUTPUT
1. Findings — bulleted, severity-tagged, max 10:
   `[SEVERITY] <location> — <one-line problem>`
2. Proposed edits — elaborate code blocks per the edit format,
   one per finding that warrants a change.

CONTEXT
{target file excerpt or full file}
{supporting context}
```

### `/gemin-eye megareview <scope>`

Module / feature / plugin sweep. Model: **pro**.

```
ROLE
Senior architect reviewing a module / feature / plugin sweep.

DO
- Identify cross-file patterns — good and bad.
- Surface architectural concerns that span files.
- Flag inconsistencies between files in scope.
- Note structural smells.
- Propose targeted edits as code blocks for the highest-impact issues.
- Use read tools to verify cross-file claims before stating them.

DON'T
- Write or modify any file.
- Find every typo.
- Re-review individual files in depth (that's `review`'s job).
- Suggest large rewrites.
- Comment on code outside the listed scope.

SCOPE — IN
- Files and directories listed in CONTEXT.

SCOPE — OUT
- Files not listed.
- External dependencies.
- Anything outside the scope path.

OUTPUT
Three sections, max 5 items each:
1. Cross-file patterns — <observations>
2. Inconsistencies — <observations, with file:line refs>
3. Architectural concerns — <observations>

Then: up to 3 proposed edits as elaborate code blocks, ranked by
impact, addressing the highest-leverage issues only.

CONTEXT
{file tree of scope}
{key file excerpts}
{supporting brief / decisions}
```

### `/gemin-eye wip`

Review uncommitted changes + current branch diff. Model: flash.

```
ROLE
Reviewer of in-flight work — uncommitted changes plus current branch diff.

DO
- Treat work as midstream. Flag direction issues now while changes are cheap.
- Frame feedback as "before you commit".
- Identify what should be split into separate commits.
- Catch regressions introduced by the diff.
- Propose small fixes as elaborate code blocks.

DON'T
- Write or modify any file.
- Demand polish.
- Suggest large refactors.
- Treat WIP as if it were a final PR.
- Comment on files not touched in the diff.

SCOPE — IN
- `git diff` output (staged + unstaged) in CONTEXT.
- `git log {base}..HEAD` commit messages in CONTEXT.

SCOPE — OUT
- Files not in the diff.
- Historical commits before {base}.
- Branch-naming or process concerns.

OUTPUT
Course-correction notes, each section bulleted, severity-tagged where useful:
1. Fix before committing — <items>
2. Split into separate commits — <items>
3. Drifting from intent — <items>
4. Risks introduced — <items>

Then: proposed edits as elaborate code blocks for the "Fix before
committing" items.

CONTEXT
{git diff output}
{git log {base}..HEAD}
{stated intent of the work, if known}
```

**Claude's prep for `wip`:** before invoking, run:

```bash
BASE="${BASE:-origin/main}"
git diff "$BASE"...HEAD > /tmp/gemin-eye-wip.diff
git diff >> /tmp/gemin-eye-wip.diff   # unstaged
git diff --cached >> /tmp/gemin-eye-wip.diff   # staged
git log --oneline "$BASE"..HEAD > /tmp/gemin-eye-wip.log
```

Pass both via `--file`. Default base is `origin/main` unless Tom
specifies otherwise.

### `/gemin-eye sanity <topic>`

Idea / plan / decision sanity check. Model: flash.

```
ROLE
Architectural reviewer doing a sanity check on a proposal, plan, or decision.

DO
- Steel-man the proposal before critiquing.
- Surface the three most likely failure modes, ranked by likelihood.
- Suggest one alternative worth considering.
- Identify what to prototype first.

DON'T
- Write or modify any file.
- Rewrite the proposal.
- Demand more detail before engaging.
- Soften critique to be agreeable.
- Pretend to be neutral when you have a view.

SCOPE — IN
- Proposal text in CONTEXT.
- Stated constraints already accepted.

SCOPE — OUT
- Implementation specifics (line-by-line code).
- Org / process critique.

OUTPUT
1. Steel-man — one paragraph, strongest version of the proposal.
2. Three failure modes — ranked by likelihood, each one paragraph.
3. Alternative worth considering — one paragraph.
4. First thing to prototype — one sentence.

CONTEXT
{proposal text}
{accepted constraints}
{relevant decisions / brief excerpts}
```

### `/gemin-eye name <thing(s)>`

One name or a related set. Model: flash.

```
ROLE
Naming consultant.

DO
- Generate 5 ranked options.
- One-line rationale per option.
- Pick a top one, defend in two sentences.
- Honour every stated constraint (length, casing, language, register).
- For a related set, name them with internal coherence (shared root,
  matching shape, parallel grammar).

DON'T
- Write or modify any file.
- Suggest names that violate constraints.
- Pad the list with throwaways.
- Apologise.
- Rename adjacent things not asked about.

SCOPE — IN
- Thing(s) to name + their role / context.
- Stated constraints.
- Existing names in the surrounding system, for coherence.

SCOPE — OUT
- Things outside the requested set.
- Renaming the surrounding system.

OUTPUT
1. <name> — <one-line rationale>
2. <name> — <one-line rationale>
3. <name> — <one-line rationale>
4. <name> — <one-line rationale>
5. <name> — <one-line rationale>

Pick: <name>
<two-sentence defence>

For multiple things in a set, return one block per thing, then a
final "Set summary" line explaining the coherence.

CONTEXT
{thing(s) to name}
{role / context}
{constraints}
{adjacent names}
```

### `/gemin-eye compare <A> <B> [<C>...]`

Head-to-head ranking, 2+ options. Model: flash.

```
ROLE
Decision support — head-to-head ranking of options.

DO
- State the comparison criteria explicitly upfront.
- Score each option against the same criteria.
- Pick a winner.
- Note when a runner-up wins under different conditions.

DON'T
- Write or modify any file.
- Refuse to pick.
- Hedge with "it depends" without specifying what it depends on.
- Add new options not in CONTEXT.
- Restate the options instead of evaluating them.

SCOPE — IN
- Options listed in CONTEXT.
- Decision context (what the choice is for).
- Stated constraints.

SCOPE — OUT
- Options not listed.
- Alternative framings of the decision.

OUTPUT
1. Criteria — bulleted list, in priority order.
2. Comparison table — option × criteria, plain Markdown.
3. Winner: <name>. <two-sentence justification>.
4. Consider <runner-up> if <condition>.

CONTEXT
{options A, B, C ...}
{decision context}
{constraints}
```

---

## Context-bundle assembly

When assembling CONTEXT, prefer this shape:

```
## Project context
<3-10 lines from brief.md or equivalent>

## Relevant decisions
- <decision> — <one-line outcome>

## Target
<the artefact under review>

## Question
<the focused ask>
```

A focused 500-token bundle outperforms a 5,000-token dump. If
tempted to attach more, ask whether the extra tokens will change
the answer.

---

## `/gemin-eye save` mechanics

`save` is a file write, not a Gemini call. It persists the LAST
in-line review to disk.

```bash
TOPIC="${1:-$(date +%H%M)}"
DATE=$(date +%Y-%m-%d)

if [ -n "$VAULT_PROJECT_DIR" ]; then
  OUT="${VAULT_PROJECT_DIR}/gemin-eye/${DATE}-${TOPIC}.md"
else
  OUT="docs/gemin-eye/${DATE}-${TOPIC}.md"
fi

mkdir -p "$(dirname "$OUT")"
```

The file uses the template in SKILL.md "Persisted file template".
Required: frontmatter (with `subcommand` and `model` fields), Prompt
(full filled-in template + CONTEXT), Response, Claude's read.

---

## Anti-patterns

- **Don't** drop sections from the template. ROLE / DO / DON'T /
  SCOPE — IN / SCOPE — OUT / OUTPUT / CONTEXT — all required, every
  call.
- **Don't** soften DO / DON'T. Imperative voice. No "try to", "feel
  free to", "consider".
- **Don't** pipe the entire repo through `--file`. Noisy context
  degrades the answer.
- **Don't** ask Gemini to "implement X end-to-end". Review and
  second-opinion only.
- **Don't** drop `--sandbox`. The folder is not trusted yet.
- **Don't** pass `--yolo`. Gemini reviews only.
- **Don't** chain Gemini calls in a loop. Each is deliberate.
- **Don't** accept edit suggestions outside the elaborate-code-block
  format. Re-prompt if violated.
- **Don't** write Gemini's response into a source file. Route via
  `gemin-eye/`, then Claude decides.
