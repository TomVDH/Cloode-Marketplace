---
date: 2026-05-26
status: brief
audience: the other adjudant session
priority: ramasse > connect > sync; check/dream/draw stay runbook-only
---

# adjudant verb implementation gaps

## The state of play

Adjudant has **7 verbs**. After v0.2.4 (`port` end-to-end), the implementation matrix:

| Verb | Reference doc | Python | Runtime model |
|---|---|---|---|
| `port` | `reference/port.md` | **`scripts/port.py` (~700 lines, TDD)** | mechanical + AI classifier for Z; the reference implementation |
| `connect` | `reference/connect.md` | none | Claude reads runbook, executes by hand |
| `sync` | `reference/sync.md` | none | Claude reads runbook, executes by hand |
| `ramasse` | `reference/ramasse.md` | **none** | Claude reads runbook, executes by hand |
| `check` | `reference/check.md` | none | Naturally Claude-runtime (report generation) |
| `dream` | `reference/dream.md` | none | Naturally Claude-runtime (diagnostic crawl, report) |
| `draw` | `reference/draw.md` | none | Naturally Claude-runtime (content generation) |

**The router-to-runbook pattern is the original adjudant design** — most verbs were never planned to have Python. `port` got code because the Y-flavor OB→adjudant migration needed deterministic, testable logic.

But three verbs (`connect`, `sync`, **`ramasse`**) are fully mechanical and *should* have Python. They don't.

## Why this brief exists

The user tried `/adjudant:adjudant ramasse` on a duplicated vault project (`_port-test-hubspot/` in the Cabinet vault) and discovered there's no automation — Claude would have to interpret the 4 ramasse features by hand against ~80 files. They want this gap closed by **building `scripts/ramasse.py` the same way `port.py` was built**.

## What ramasse must do (locked spec — `reference/ramasse.md`)

Four features, full sweep, no flags, idempotent (second run = no-op):

1. **Rebuild `_index.md`** in every project subfolder that holds ≥2 sibling files of the same type. Chronological where filenames have date prefixes (`YYYY-MM-DD-*.md`), alphabetical otherwise. **Skip** these subfolders: `sessions/`, `images/`, `assets/`, `previews/`.

2. **Bump `updated:` frontmatter** on touched files where applicable (doc, project brief, note).

3. **Normalize tags** per the locked schema in `reference/vault-standards.md` § 2:
   - **Drop entirely (Bucket D):** all `#ob/*`, project-slug tags (e.g., `#hubspot-nightly`), vague topicals (`#architecture`, `#frontend`, `#cms`, `#toolbox`, `#moc`, `#scheduler`, `#campaign-request`, `#flow-c`, `#nightly`, `#hubspot`), crew names (`#bostrol`, `#kevijntje`, `#henske`, `#jonasty`).
   - **Drop most `#cabinet/*`** (cabinet sunset). **Migrate three specific ones (Bucket B):** `cabinet/recon → recon-item`, `cabinet/portal-concept → portal-concept`, `cabinet/preview → preview`, `cabinet/asset-index → index`, `cabinet/dev-doc → doc`.
   - **Leave alone:** Bucket A file-type tags (`#decision`, `#session`, etc.), Bucket C topical tags (specifically `#content/seafood-companies` and other namespaced `category/value`-form tags that meet the three criteria).
   - **Important non-tag:** `cssclasses: cabinet-sidecar` in frontmatter is an Obsidian CSS class — not a tag, do not touch.

4. **Fix wikilink form violations** — rewrite markdown-style links `[text](path)` to `[[wikilink|text]]` IFF `path` resolves to a `.md` file inside the vault. Leave external/code/heading-anchor links alone.

## Scope

- Default: operates on the project resolved from breadcrumb (`.claude/adjudant`)
- Vault-wide variant: `--vault` flag walks all projects
- Fail conditions: vault unresolvable → exit non-zero; unparseable YAML frontmatter → skip + log, continue

## Reference implementation pattern (follow port.py)

- Single file `adjudant/scripts/ramasse.py`, pure stdlib (no new deps)
- Paired tests `adjudant/scripts/test_ramasse.py` (unittest, TDD)
- CLI subcommands (`detect` if needed, plus main action)
- Wire into `reference/ramasse.md` runbook: it calls `python3 ramasse.py` for the mechanical work
- Update `scripts/validate.py` with any new invariants (probably none beyond version-consistency)
- Bump versions in all 4 files (`plugin.json`, `marketplace.json`, `command-metadata.json`, `SKILL.md`) — the `version-consistency` validator enforces this

## Test fixture already prepared

A duplicate of the real `hubspot-nightly` project lives at:

- **Working dupe (target):** `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Claude Cabinet/projects/_port-test-hubspot/`
- **Pre-ramasse snapshot (revert):** `/tmp/dupe-snapshot-pre-ramasse/` (2.8 MB cp -R from before any ramasse work)

The dupe has been `port`ed already (post-v0.2.4 conservative `_index.md` upsert). Current state:

- 11 subfolders: `decisions/` (17 md), `dreams/` (7), `gemini/` (1), `images/` (1), `memory/` (18 — **no _index.md**), `nightly/` (12), `notes/` (9), `references/` (1), `sessions/` (10), `tasks/` (1), `_legacy/` (0)
- **5 folders qualify for feature 1 rebuild:** `decisions/`, `dreams/`, `memory/`, `nightly/`, `notes/`
- **Tag normalization found in inventory:** `cabinet/decision`, `ob/decision`, `ob/doc`, `ob/dream`, `ob/handoff`, `ob/index`, `ob/note`, `ob/session` — all should be dropped per Bucket D
- **Markdown-style links found:** ~10+ matching `](...md)` pattern, e.g. `](feedback_audit_scope_full_repo.md)`, `](credentials/README.md)`, `](../../_docs/SPEC-012-CAMPAIGN-FACTORY.md)` — the last one points outside the vault, must be skipped

## Constraints / do not

- **Do not re-implement port.** It's done, tested, shipped. `port.py` is the pattern; copy the structure, not the content.
- **Do not implement `check`, `dream`, or `draw` in Python.** Those are intentionally Claude-runtime (report/content generation). Just confirm their runbooks are sane.
- **`connect` and `sync` are also gaps** but lower priority than `ramasse` — the user is actively trying to use ramasse right now.
- **The other session (this one, that produced this brief) is wrapping up.** Don't expect to coordinate — just take this brief and run.

## Recommended phasing

1. Build `ramasse.py` + tests (5–8 tasks TDD per the port.py pattern), bump to v0.3.0
2. Run ramasse on the dupe at `_port-test-hubspot/`, compare to `/tmp/dupe-snapshot-pre-ramasse/` to verify behavior
3. Optional: build `connect.py` and `sync.py` next (v0.4.0)
4. The runbook-only verbs (`check`, `dream`, `draw`) stay as docs — verify their reference files are still accurate

## Pointers

- Spec to implement: `adjudant/skills/adjudant/reference/ramasse.md`
- Standards reference: `adjudant/skills/adjudant/reference/vault-standards.md`
- Pattern reference: `adjudant/scripts/port.py` + `adjudant/scripts/test_port.py`
- Validator chain: `adjudant/scripts/validate.py` + `.pre-commit-config.yaml`
- Versioning: `version-consistency` validator covers `plugin.json` / `marketplace.json` / `command-metadata.json` / `SKILL.md` — keep all four in sync
