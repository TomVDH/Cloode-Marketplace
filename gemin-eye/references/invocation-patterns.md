# Gemini CLI — invocation patterns for GeminEye

Reusable patterns for calling Gemini from inside a Claude Code session. All
examples assume the `gemini` CLI is on `PATH` (verified in the SKILL.md
pre-flight). Read this file when scaffolding a new review pattern; the
SKILL.md alone is enough for one-shot reviews.

---

## Quick patterns

### One-shot prompt

```bash
gemini -p "Review this snippet for race conditions: $(cat snippet.ts)"
```

### Prompt with file context

```bash
gemini -p "Review for naming clarity and obvious bugs." \
       --file src/components/Pane.tsx \
       --file docs/architecture.md
```

### Multi-file with stdin prompt

For prompts longer than a shell line, pipe via stdin:

```bash
cat <<'PROMPT' | gemini --file src/auth.ts --file docs/threat-model.md -
You are reviewing a security-sensitive auth module.
Focus on: token handling, session fixation, replay protection.
Ignore: code style, naming.
Output: bulleted findings, severity-tagged (HIGH/MED/LOW).
PROMPT
```

### Selecting a model

```bash
gemini -m gemini-2.5-pro -p "..."   # deep reasoning, slower
gemini -m gemini-2.5-flash -p "..." # fast, lighter
```

Default to whatever the user's CLI config has set. Only override the model
when the task warrants it (e.g. flash for quick lint-like passes, pro for
architecture review).

---

## Reusable prompt scaffolds

### Code review

```
You are a senior reviewer doing a focused pass on the file(s) provided.

Constraints:
- Be specific: cite line numbers or symbol names.
- Severity-tag each finding: HIGH / MED / LOW / NIT.
- Do not rewrite the code. Suggest, don't replace.
- Skip style nits unless they obscure intent.

Focus areas:
- {focus_areas}

Project context:
{brief_excerpt}
```

### Doc review

```
You are reviewing a Markdown doc for clarity, accuracy, and audience fit.

Audience: {audience}
Goal of doc: {goal}

Find:
- Claims that need a source or example
- Sections that drift off-topic
- Jargon that won't land with the audience
- Missing prerequisites

Do not rewrite. Bullet your findings.
```

### Architecture sanity check

```
You are reviewing an architectural proposal. Steel-man it before you
critique it.

Proposal:
{proposal_text}

Constraints we already accept:
{constraints}

Output:
1. Strongest version of the proposal (one paragraph).
2. Three failure modes ranked by likelihood.
3. One alternative worth considering.
4. What you'd want to see prototyped first.
```

### Naming bikeshed

```
Help pick a name for {thing}.

Context: {one-paragraph context}
Constraints: {e.g. must be one word, lowercase, kebab-case, etc.}

Give me 5 options ranked, each with one-line rationale. Then pick your
top one and defend it in two sentences.
```

### Prompt review (meta)

```
You are reviewing a prompt that will be used with an LLM.

Prompt:
{prompt_text}

Find:
- Ambiguities the model will resolve in unwanted ways
- Missing constraints
- Conflicting instructions
- Format-of-output issues
```

---

## Context-bundle assembly

When assembling context for Gemini, prefer this shape:

```
## Project context
<3-10 lines from brief.md or equivalent>

## Recent decisions (relevant only)
- <decision title> — <one-line outcome>

## Target
<the thing we're asking Gemini to look at, in full or as the relevant excerpt>

## Question
<one focused question, not three>
```

A focused 500-token bundle outperforms a 5,000-token dump nine times out
of ten. If you're tempted to attach more, ask whether the extra tokens
will change the answer.

---

## Capturing output

For persisted reviews (see SKILL.md "Output protocol"), capture both the
prompt and the response. The cleanest pattern:

```bash
TOPIC="auth-module-race"
DATE=$(date +%Y-%m-%d)
OUT="${VAULT_PROJECT_DIR}/gemin-eye/${DATE}-${TOPIC}.md"

mkdir -p "$(dirname "$OUT")"

{
  echo "---"
  echo "type: gemin-eye-review"
  echo "date: ${DATE}"
  echo "topic: ${TOPIC}"
  echo "---"
  echo
  echo "## Prompt"
  cat prompt.txt
  echo
  echo "## Response"
  gemini -p "$(cat prompt.txt)" --file "${TARGET}"
} > "$OUT"
```

After writing, append "Claude's read" by editing the file — that section
is Claude's filter on Gemini's response and is required by the SKILL.md
output protocol.

---

## Anti-patterns

- **Don't** pipe the entire repo through `gemini --file` "for context".
  Gemini's context window is finite and noisy context degrades the answer.
- **Don't** ask Gemini to "implement X end-to-end". GeminEye is for review
  and second-opinion work; implementation stays with Claude unless Tom
  invokes the override clause.
- **Don't** write Gemini's response straight into a source file. Always
  route via `docs/gemin-eye/` or the vault's `gemin-eye/` subfolder, then
  let Claude decide what to act on.
- **Don't** chain Gemini calls in a loop without Tom's involvement. Each
  call is a deliberate ask, not a background process.
