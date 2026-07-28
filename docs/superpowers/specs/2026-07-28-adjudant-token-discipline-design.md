# Adjudant token discipline - design (v0.17.0)

Cut what adjudant costs in model context per invocation, without trading away
rule compliance. Companion to the 2026-07-27 audit findings; the audit's
tier 4 and tier 5 remain queued separately.

## The measurement that reframed the problem

Measured 2026-07-28 against this repo's own vault project (8 files), token
estimates at the repo's own `bytes // 4` convention:

| surface | tokens | kind |
|---|---|---|
| `SKILL.md` (router, every invocation) | ~3050 | static prose |
| `reference/voice.md` (every verb) | ~853 | static prose |
| `reference/check.md` (the verb's doc) | ~1470 | static prose |
| `check.py` JSON (the actual project data) | ~397 | data |

**93% of a verb's cost is static prose that is byte-identical every time.**
The helper-layer doctrine worked exactly as designed - the data really is
small. But the cost gate built in v0.14.0 (`--estimate-only`, verb weights,
30k warn threshold) guards only that 7%. On a normal project it never fires,
while the unguarded 93% is paid on every invocation.

The heavy verbs invert the same way: `dream` emits ~441 tokens of findings
here and costs ~2271 tokens of `dream.md` to explain how to read them.

### Two regimes, not one

The vault holds 27 projects. Four are enormous:

| project | files | tokens if fully read |
|---|---|---|
| tf-renewal | 594 | ~614k |
| hubspot-nightly | 564 | ~1.18M |
| _port-test-hubspot | 195 | ~609k |
| dutchbc-poc | 283 | ~61k |

A full `dream` on hubspot-nightly is not expensive, it is impossible: roughly
40x the warn threshold and far past any context window. So:

- **Everyday projects**: cost is dominated by static docs. Fixed by this spec.
- **The four monsters**: cost is dominated by data. Needs staged escalation,
  scoped as follow-up work below.

## Governing principle

**A rule enforced mechanically does not need to be spent in context.**

This is the same mechanical-versus-attentional split that explains why
adjudant compliance runs 80-100% rather than 100%: hooks and validators fire
every time, prose reminders decay with session length. Every release so far
has moved rules down into the mechanical channel. This one continues that,
and takes the token refund.

Where a rule has no mechanical enforcer, it stays inline - or gains one.

## Components

Dependency order. Component 1 is what makes component 3 safe rather than a
trade.

### 1. PreToolUse schema gate

New hook `hooks/scripts/pretooluse-schema-gate.py`, wired on `PreToolUse`
with matcher `Write`.

Fires only for writes landing under the resolved vault project. Parses the
proposed frontmatter out of `tool_input.content` and validates it by calling
`schema_drift_for_file` - the same detector `check` renders and `tidy` phase 5
repairs, so there is exactly one copy of the schema rules.

Behaviour:

- **Block** (exit 2, stderr naming the expected shape) on `missing_required`
  or `type_conflict`. PreToolUse exit 2 stops the tool and feeds stderr back,
  so the model corrects within the same turn.
- **Warn** (exit 0, stderr note) on `unknown_fields`. Tidy phase 5 strips
  those safely after the fact; blocking would be disproportionate.
- **Fail open** on everything infrastructural: no breadcrumb, unresolvable
  vault, unparseable payload, import failure. A write must never be blocked
  because a hook had a bad day.

Reuses the hardening primitives from tiers 1 and 2: `is_safe_slug` before any
path build, `find_project_dir` for zone-aware resolution. Imports lazily,
after the breadcrumb check, so the no-op path stays cheap (audit finding 21
measured the eager-import cost on the sibling PostToolUse hook).

**Known limitation.** `Edit` payloads carry `old_string`/`new_string`, not the
resulting file, so the gate cannot judge the outcome without simulating the
edit. The gate is Write-only; edits keep tidy as their backstop. Documented
rather than silently partial.

### 2. SKILL.md split

Move three sections into a new `reference/internals.md`, loaded only when the
question is how adjudant itself is built:

| section | tokens |
|---|---|
| Hooks (the nine-entry table) | ~683 |
| Python helper layer (verb-to-helper table) | ~531 |
| Environment awareness | ~114 |

`SKILL.md` keeps the verb router, the locked three-tier model, the cost gate
rules, and the pointers. Router table gains one row for `internals.md`.

Result: **~3050 -> ~1700**.

### 3. vault-standards and voice trim

`reference/vault-standards.md` is the fattest reference at ~3539 tokens and is
loaded for essentially every vault write. It is also the file whose rules are
most thoroughly enforced already:

| rule area | mechanical enforcer |
|---|---|
| tag taxonomy (buckets A-D) | `tidy.normalize_tags`, validator 1 |
| frontmatter per type | `FIELD_SCHEMA`, validators 28/29, tidy phase 5, and now the write gate |
| status vocabulary | validators 23, 28 |
| wikilink form | tidy phase 4 |
| folder shape, file naming | `ramasse_scan` |

Rewrite so each rule states its shape once and names its enforcer, instead of
restating enforceable detail. Hand-authoring guidance that has no enforcer
stays in full. Target **~3539 -> ~1500**.

`reference/voice.md` keeps the judgment content - tone, the pushback contract,
the ELI5/ELI12/ELICTO modes, the glazing ban, typography. The banned-lexicon
LIST moves into validator 24, which already enforces it, with voice.md
pointing there. Target **~853 -> ~500**.

### 4. Token budget report (report-only)

`scripts/token_budget.py` walks `SKILL.md` and `reference/*.md`, computes
`bytes // 4` per file, compares against a `BUDGETS` constant table declared in
that same module (not `command-metadata.json`, which is verb metadata and has
no natural slot for per-document limits), and renders a section inside
`check repo`. Files with no declared budget are reported without a verdict.

**Never fails the build** - deliberate choice. A hard ceiling would make
legitimate documentation growth a fight; visibility is enough pressure, and it
keeps the mechanism from becoming the thing people work around.

## Expected result

| flow | before | after | cut |
|---|---|---|---|
| read-only verb (`check`) | ~5770 | ~4070 | 29% |
| vault write flow (+ vault-standards) | ~7800 | ~4100 | 47% |

Read-only: 1700 + 500 + 1470 (check.md, untouched) + 397 data.
Write flow: 1700 + 500 + 1500 (trimmed vault-standards) + ~400 verb doc.

The write flow gains more because vault-standards.md is the single fattest
reference and the one this spec actually trims; per-verb references are left
alone deliberately (splitting them was approach B, rejected for reintroducing
a per-verb judgement call).

Compliance is expected to improve, not regress: the write gate catches at
write time what the prose only reminded about and tidy only repaired
afterwards.

## Testing

- **Gate**: unit tests per branch - blocks on missing required, blocks on
  type conflict, warns but allows unknown fields, fails open with no
  breadcrumb / bad payload / unresolvable vault, ignores writes outside the
  vault project, respects zone-aware resolution and the slug guard. Plus an
  end-to-end through the `__main__` guard.
- **Split**: existing validators `reference-files-exist` and
  `reference-doc-links` cover `internals.md` automatically; add a test that
  the moved sections are gone from SKILL.md and present in internals.md.
- **Trim**: validator 24 keeps enforcing the lexicon after the list moves;
  add a test that the lexicon still fails on a banned term.
- **Budget**: computation tests plus a `check repo` integration test.
- **Truth pass**: README, plugin.json, marketplace entry.

## Risks

1. **A blocked write is a real behaviour change.** Mitigated by blocking only
   the two unambiguous cases, warning on the third, and failing open
   everywhere else. If it proves noisy in practice, the block set narrows.
2. **Trimming vault-standards could weaken hand-authored writes.** This is
   why the gate lands first: the write path enforces the schema before the
   prose is trimmed, so the trim removes redundancy rather than protection.
3. **Edit writes stay ungated.** Accepted; tidy remains the backstop.

## Follow-up, not in this spec

**Staged escalation for the four monster projects.** Decided narrowing
strategies, all four wanted: a recency window from mtimes; folder or note-type
scoping; sample-then-extrapolate with a confidence note; and a frontmatter-only
first pass (the audit measured frontmatter at ~4% of vault bytes, so structural
drift surfaces for pennies before any body is read). Needs its own design pass;
`dream` and `ramasse` on hubspot-nightly are currently impossible, not merely
expensive.
