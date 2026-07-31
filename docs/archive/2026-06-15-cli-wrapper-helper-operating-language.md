# cli-wrapper-helper v2.0.0 Operating-Language Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Graduate `cli-wrapper-helper` from a two-skill visual pattern library into the written operating language for agent-built helper CLIs — visual + interaction + operational/safety — by harvesting the patterns proven in `hubspot-nightly` `_toolbox/`, generalized.

**Architecture:** Five new + four updated markdown reference files under `cli-wrapper-helper/references/`, anchored by a new `design-language.md` spine. Two skills (`bash-tui`, `python-helper`) reframed in place to reference the new material. Manifests bumped to v2.0.0 with a rewritten description; evals extended with trigger cases for the new layers. No code, no symlink topology (this plugin keeps `skills/` directly), no external dependencies.

**Tech Stack:** Markdown reference docs; bash 3.2 patterns (the subject matter); Claude Code plugin structure (skills + `${CLAUDE_PLUGIN_ROOT}/references` + commands + evals); git (direct commits to `main` per repo convention).

**Spec:** `docs/superpowers/specs/2026-06-15-cli-wrapper-helper-operating-language-design.md`

**Source-of-truth (read-only, for lifting patterns):** `/Users/tomlinson/repos/hubspot-nightly.git` (bare; branch `campaign-factory`). Read files with `git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:<path>`.

---

## Conventions for every task

- **Run all commands from the repo root:** `/Users/tomlinson/Projects/VIBE CODING/onnozelaer-claude-marketplace`. Let `CWH=cli-wrapper-helper`.
- **Generalization rule (applies to every harvested pattern):** rename `zt_*`/`ZT_*` → neutral (`ui_*`, `cli_*`, or unprefixed); replace domain nouns ("contacts/companies/deals" → "records/objects", "HubSpot Design Manager" → "the remote service", `hs` CLI → "the vendor CLI"); a HubSpot reference may appear ONLY as a single italic `*seen in the wild: …*` line, never in a pattern body; output statements always use semantic color tokens, never raw ANSI.
- **Leakage gate (run on every reference file you create/edit):**
  `grep -rinE 'hs |ZT_|hubspot|zena|nightly|\bcrm\b|deskflex' cli-wrapper-helper/references/<file>` → expected: no matches, OR only lines beginning with `*seen in the wild:`.
- **Commit trailer (every commit):** end the message with
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `references/design-language.md` | The spine: semantic roles, indent law, marker vocab, motion tiers, "same-handed" principle, extend-the-language method | Create (Task 1) |
| `references/components.md` | Draw-a-widget catalog (+ bootloader, FIFO breathing) | Modify (Task 2) |
| `references/interaction.md` | Compose-a-flow grammar: wheelhouse menus, pickers, ceremonies, dry-run UX | Create (Task 3) |
| `references/bash-safety.md` | bash 3.2 correctness floor | Create (Task 4) |
| `references/operations.md` | Runtime safety: dry-run stub, PID locks, manifest, logging, smoke tests | Create (Task 5) |
| `references/data-cli.md` | Wrapping an external CLI/API: auth tiers, fetch→CSV, recipes, catalogs | Create (Task 6) |
| `references/architecture.md` | Multi-file project shape, entry launcher, git-hooks, tool skeleton | Modify (Task 7) |
| `references/python-helpers.md` | + JSON-parse sidecar for bash | Modify (Task 8) |
| `references/palette.md` | Raw color reference; reconcile new named colors | Modify (Task 8) |
| `skills/bash-tui/SKILL.md` | Reframe as operating-language entry; reference all eight bash-side files | Modify (Task 9) |
| `skills/python-helper/SKILL.md` | Reference design-language spine + python-helpers | Modify (Task 10) |
| `.claude-plugin/plugin.json` + root `.claude-plugin/marketplace.json` | v2.0.0 + rewritten description | Modify (Task 11) |
| `evals/evals.json` | Trigger cases for new layers | Modify (Task 12) |

Dependency order: Task 1 (spine) first; Tasks 9–10 (skills) after all references exist; Task 13 (final sweep) last.

---

## Task 1: design-language.md (the spine)

**Files:**
- Create: `cli-wrapper-helper/references/design-language.md`

- [ ] **Step 1: Read the source palette + role definitions**

Run:
```
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/_lib.sh | sed -n '1,160p'
```
Note the palette block and the semantic-role aliases (`*_COLOR_TITLE`, `_SUCCESS`, `_WARN`, `_ERROR`, `_MUTED`, `_ACTIVE`, `_INFO`). Also re-read the existing `cli-wrapper-helper/skills/bash-tui/SKILL.md` sections "Color palette with semantic tokens", "Two-space indent", "Status markers", and "Speed Tiers" — these are the seeds of the spine.

- [ ] **Step 2: Write `design-language.md` with these required sections**

The file MUST contain these `##` headers, in this order, each with concrete content:

1. `## The one principle` — every tool an agent builds must look, feel, and behave as if it came from the same hand. State the three layers (visual / interaction / operational) in one line each.
2. `## Semantic color roles` — the role table (TITLE, SUCCESS, WARN, ERROR, MUTED/INFO, ACTIVE) mapped to intent, with the rule "output statements use role names, never raw ANSI." Point to `palette.md` for the hex/ANSI values. Generalized (no `ZT_` prefix).
3. `## The two-space indent law` — every user-visible line starts with ≥2 spaces; leaves room for status markers. Show a 3-line example.
4. `## Marker vocabulary` — `✓ ✗ ⚠ ℹ` with their semantic roles; "no emoji in headers or status."
5. `## Motion & speed tiers` — the Slow/Medium/Fast table (frame/row delays) with Fast as default; one sentence on when motion is appropriate.
6. `## Extending the language` — record the method observed in the gen1 gallery: prototype variants in a demo harness (`demo-ui/sections/<thing>.sh`), preview them through a picker (`pickers/picker-<thing>.sh`), promote exactly one to canon, then delete the rest. New language elements enter the same way: *prototype → preview → promote → prune.*

Add a one-line header note: "Both skills inherit this file. `palette.md` holds the raw colors; this file holds the grammar."

- [ ] **Step 3: Verify required sections + no leakage**

Run:
```
for h in "The one principle" "Semantic color roles" "The two-space indent law" "Marker vocabulary" "Motion & speed tiers" "Extending the language"; do grep -q "## $h" cli-wrapper-helper/references/design-language.md && echo "OK: $h" || echo "MISSING: $h"; done
grep -rinE 'hs |ZT_|hubspot|zena|nightly|\bcrm\b' cli-wrapper-helper/references/design-language.md
```
Expected: six `OK:` lines; the second grep prints nothing (or only `*seen in the wild:` lines).

- [ ] **Step 4: Commit**

```
git add cli-wrapper-helper/references/design-language.md
git commit -m "feat(cli-wrapper-helper): add design-language.md spine — semantic roles, indent law, marker vocab, motion tiers, extend method" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: components.md — bootloader + FIFO breathing

**Files:**
- Modify: `cli-wrapper-helper/references/components.md`

- [ ] **Step 1: Read the source components**

Run:
```
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/bootloader.sh
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_docs/_archive/gen1-scripts/demos/poc-spinning-z.sh
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/_watch-helpers.sh
```
The bootloader is a depth-shaded (`░▒▓█`) rotating-logo boot animation; `poc-spinning-z.sh` is its canonical origin. `_watch-helpers.sh` carries the FIFO/breathing pattern.

- [ ] **Step 2: Append a `## Bootloader (depth-shaded rotating logo)` section**

Document the pattern generically: a sequence of rotation frames of a block-character glyph, depth-shaded with `░ ▒ ▓ █`, cycled with a short frame delay before the splash. Lift the frame-construction approach from `bootloader.sh`/`poc-spinning-z.sh`, replacing the "Z" glyph with a neutral placeholder and noting "swap the glyph for the tool's mark." Include a `*seen in the wild: a spinning "Z" boot logo*` line.

- [ ] **Step 3: Add/replace the breathing section with the FIFO-aware form**

Find the existing `breathe()` material (background-`&` form). Keep it as "the simple case (no read loop)", then add `### Breathing that survives a read loop` with this exact generalized skeleton:

```bash
# A `producer | while read` loop runs in a SUBSHELL — counters and the
# breathing redraw die with it. Route the producer through a FIFO and read
# in the MAIN shell so state persists and the frame advances on each timeout.
fifo_dir="$(mktemp -d)"; fifo="$fifo_dir/pipe"; mkfifo "$fifo"
cleanup_fifo() { rm -f "$fifo"; rmdir "$fifo_dir" 2>/dev/null || true; }
trap cleanup_fifo EXIT INT TERM

producer_cmd > "$fifo" 2>&1 &
producer_pid=$!

while IFS= read -r -t 1 line || kill -0 "$producer_pid" 2>/dev/null; do
  [[ -n "${line:-}" ]] && handle_line "$line"
  draw_breathing_frame      # advances once per 1s read timeout
done < "$fifo"
```
Add a cross-reference line: "Why the FIFO (not a pipe): see `bash-safety.md` → Subshell-eats-state."

- [ ] **Step 4: Verify + commit**

Run:
```
for h in "Bootloader (depth-shaded rotating logo)" "Breathing that survives a read loop"; do grep -q "$h" cli-wrapper-helper/references/components.md && echo "OK: $h" || echo "MISSING: $h"; done
grep -rinE 'hs |ZT_|hubspot|zena|nightly|\bcrm\b' cli-wrapper-helper/references/components.md
```
Expected: two `OK:` lines; no leakage.
```
git add cli-wrapper-helper/references/components.md
git commit -m "feat(cli-wrapper-helper): components.md — bootloader + FIFO-aware breathing" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: interaction.md (new)

**Files:**
- Create: `cli-wrapper-helper/references/interaction.md`

- [ ] **Step 1: Read sources**

Run:
```
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/README.md | sed -n '1,80p'
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/_export-helpers.sh
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/tools/fm-snapshots-purge.sh
```
The README shows the "wheelhouse" menu (top-level groups + sub-groups + status tags). `_export-helpers.sh` has the full-control catalog picker. `fm-snapshots-purge.sh` has the typed-confirmation ceremony.

- [ ] **Step 2: Write `interaction.md` with these required `##` sections**

1. `## Wheelhouse menus` — arrow-key menu organized into top-level groups, each with sub-groups; per-item status tags rendered with semantic roles: `COMING SOON` (muted), `deprecated` (muted), `⚠ destructive` (error), `read-only` (info). Show the group/sub-group/tag layout (lift structure from the README's menu block; strip CMS/CRM/HubSpot labels → generic "Group A / Action").
2. `## The picker family` — single-select (`›› / ›`), boolean toggle (`›● / ○`), multi-select (`›› [x] / › [ ]`), and the full-control catalog picker. For the catalog picker, document: catalog rows of `value|Label` plus `HEADER|Category` separator rows, arrow-key toggle, a live "N selected" count, a preview of the resulting selection, and back-navigation. Reference the catalog file format in `data-cli.md`.
3. `## Confirmation ceremonies` — for destructive actions, require the user to type a literal word. Exact generalized skeleton:

```bash
confirm_destructive() {
  local word="$1"
  printf "  ${COLOR_ERROR}${BOLD}This is destructive.${RESET} Type ${BOLD}%s${RESET} to proceed: " "$word"
  read -r reply
  [[ "$reply" == "$word" ]] || { printf "  ${COLOR_MUTED}Aborted.${RESET}\n"; return 1; }
}
```
4. `## Dry-run as a UX surface` — when `--dry`/`--dry-run` is set, show a prominent banner and label simulated actions; cross-reference `operations.md` for the stub-layer mechanics. Show the banner line:
```bash
$DRY_RUN && printf "  ${COLOR_WARN}${BOLD}DRY RUN${RESET}${COLOR_MUTED} — no data will be written${RESET}\n"
```

- [ ] **Step 3: Verify + commit**

```
for h in "Wheelhouse menus" "The picker family" "Confirmation ceremonies" "Dry-run as a UX surface"; do grep -q "## $h" cli-wrapper-helper/references/interaction.md && echo "OK: $h" || echo "MISSING: $h"; done
grep -rinE 'hs |ZT_|hubspot|zena|nightly|\bcrm\b' cli-wrapper-helper/references/interaction.md
git add cli-wrapper-helper/references/interaction.md
git commit -m "feat(cli-wrapper-helper): add interaction.md — wheelhouse menus, picker family, ceremonies, dry-run UX" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: four `OK:` lines; no leakage.

---

## Task 4: bash-safety.md (new)

**Files:**
- Create: `cli-wrapper-helper/references/bash-safety.md`

- [ ] **Step 1: Read sources for the gotchas**

Run:
```
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/_export-helpers.sh | sed -n '1,120p'
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/_watch-helpers.sh | sed -n '1,80p'
```
Also reuse the existing `bash-tui/SKILL.md` "What NOT to Do" and `trunc()` sections.

- [ ] **Step 2: Write `bash-safety.md` with these required `##` sections**

1. `## Strict mode + cleanup trap` — `#!/usr/bin/env bash` + `set -euo pipefail` + a `cleanup` trap that restores cursor and resets ANSI on `EXIT INT TERM`.
2. `## Subshell-eats-state (use a FIFO)` — the core lesson: `cmd | while read` runs the loop in a subshell, so counters and redraws are lost; route through `mkfifo` and read in the main shell. Cross-reference `components.md` breathing.
3. `## Array quoting under set -u` — always `"${arr[@]}"`, guard possibly-empty expansions with `"${arr[@]:-}"`, and the bash 3.2 empty-array pitfall.
4. `## printf, never echo -e` — portability; one example of the bug `echo -e` causes.
5. `## ANSI width: truncate before you color` — the `trunc()` helper and why color codes break `printf` width math (raw text first, then wrap in color).
6. `## CSV / preview safety` — quoting fields, avoiding word-splitting when previewing variable data; the picker-crash class (unguarded array index / unquoted expansion) and its fix.

- [ ] **Step 3: Verify + commit**

```
for h in "Strict mode + cleanup trap" "Subshell-eats-state (use a FIFO)" "Array quoting under set -u" "printf, never echo -e" "ANSI width: truncate before you color" "CSV / preview safety"; do grep -q "## $h" cli-wrapper-helper/references/bash-safety.md && echo "OK: $h" || echo "MISSING: $h"; done
grep -rinE 'hs |ZT_|hubspot|zena|nightly|\bcrm\b' cli-wrapper-helper/references/bash-safety.md
git add cli-wrapper-helper/references/bash-safety.md
git commit -m "feat(cli-wrapper-helper): add bash-safety.md — bash 3.2 correctness floor (FIFO, array quoting, trunc, printf)" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: six `OK:` lines; no leakage.

---

## Task 5: operations.md (new)

**Files:**
- Create: `cli-wrapper-helper/references/operations.md`

- [ ] **Step 1: Read sources**

Run:
```
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/tools/fm-upload.sh | sed -n '1,140p'
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/nightly/_core.sh | sed -n '1,120p'
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/_logging.sh
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/_boilerplate_test.sh
```
`fm-upload.sh` holds the PID lock + manifest. `nightly/_core.sh` holds the dry-run stub layer (redefines mutating helpers when dry). `_logging.sh` + `_boilerplate_test.sh` for logging + smoke tests.

- [ ] **Step 2: Write `operations.md` with these required `##` sections (embed these exact generalized skeletons)**

1. `## Dry-run stub layer`
```bash
# When DRY=true, redefine the MUTATING helpers to log + return a plausible
# fake id; leave read-only helpers live so the dry trace stays realistic.
if $DRY; then
  remote_create() { log "DRY would create: $*"; printf 'fake-%s' "$RANDOM"; }
  remote_delete() { log "DRY would delete: $*"; }
  remote_upload() { log "DRY would upload: $*"; printf 'fake-file-%s' "$RANDOM"; }
  # remote_list / remote_get stay live — read-only, safe to run for real
fi
```
2. `## PID single-instance lock`
```bash
LOCK="${LOG_DIR}/${TOOL_NAME}.lock"
acquire_lock() {
  if [[ -f "$LOCK" ]]; then
    local pid; pid="$(cat "$LOCK" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      die "Another ${TOOL_NAME} is running (pid $pid). Refusing to race."
    fi
    # else: stale lock (owner gone) — fall through and reclaim it
  fi
  printf '%s' "$$" > "$LOCK"
}
release_lock() { rm -f "$LOCK"; }
trap release_lock EXIT INT TERM
acquire_lock
```
3. `## Manifest idempotency`
```bash
MANIFEST="${LOG_DIR}/${TOOL_NAME}-manifest.txt"
already_done() { grep -qxF "$1" "$MANIFEST" 2>/dev/null; }
mark_done()    { printf '%s\n' "$1" >> "$MANIFEST"; }
for item in "${items[@]}"; do
  if already_done "$item" && ! $FORCE; then
    info "skip: $item (in manifest; --force to redo)"; continue
  fi
  process "$item" && mark_done "$item"
done
```
4. `## Logging to .logs/` — a `log()` helper writing timestamped lines to `${LOG_DIR}/${TOOL_NAME}.log`; `LOG_DIR` defaults to `.logs/`.
5. `## Smoke tests` — the boilerplate-test pattern: a `_examples/<tool>-smoke.sh` that runs the tool with `--dry` and asserts exit 0 + expected markers in output; how to keep smoke tests read-only.

Add a header note: "These are the operational floor — an agent building any tool that writes, uploads, or mutates state applies them by default."

- [ ] **Step 3: Verify + commit**

```
for h in "Dry-run stub layer" "PID single-instance lock" "Manifest idempotency" "Logging to .logs/" "Smoke tests"; do grep -q "## $h" cli-wrapper-helper/references/operations.md && echo "OK: $h" || echo "MISSING: $h"; done
grep -rinE 'hs |ZT_|hubspot|zena|nightly|\bcrm\b' cli-wrapper-helper/references/operations.md
git add cli-wrapper-helper/references/operations.md
git commit -m "feat(cli-wrapper-helper): add operations.md — dry-run stub, PID lock, manifest idempotency, logging, smoke tests" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: five `OK:` lines; no leakage.

---

## Task 6: data-cli.md (new)

**Files:**
- Create: `cli-wrapper-helper/references/data-cli.md`

- [ ] **Step 1: Read sources**

Run:
```
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/_lib.sh | sed -n '440,560p'
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/_export-helpers.sh | sed -n '150,260p'
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_data/crm-exports/contacts.def.sh
```
`_lib.sh` ~440–560 is the auth/credential resolver. `_export-helpers.sh` ~150–260 is the paginated fetch→CSV. `*.def.sh` is a config-driven definition / catalog.

- [ ] **Step 2: Write `data-cli.md` with these required `##` sections**

1. `## Auth tiers & credential resolution` — three tiers (vendor CLI config → token file → none), resolve then validate. Exact generalized skeleton:
```bash
# Tier 1: vendor CLI config.  Tier 2: token file.  Then validate against the service.
resolve_token() {
  TOKEN=""; CLI_OK=false
  if command -v "$VENDOR_CLI" >/dev/null 2>&1; then
    TOKEN="$("$VENDOR_CLI" config get-token 2>/dev/null || true)"
    [[ -n "$TOKEN" ]] && CLI_OK=true
  fi
  if [[ -z "$TOKEN" && -f "$TOKEN_FILE" ]]; then
    TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"
  fi
  [[ -z "$TOKEN" ]] && die "No credentials. Run '$VENDOR_CLI auth' or place a token in $TOKEN_FILE"
  validate_token "$TOKEN" || die "Credentials present but rejected by the service."
}
```
2. `## Output directory resolution` — resolve an output dir in precedence order: env var → credentials file → default (e.g. `~/Desktop`). Show the `${OUT_DIR:-$(cat "$CRED_DIR/out-dir" 2>/dev/null || echo "$HOME/Desktop")}` style.
3. `## Paginated fetch → CSV (Ctrl+C-safe)` — loop pages until empty, append rows, flush to CSV; write to a temp file and `mv` into place on success so an interrupt never leaves a half-written CSV. Use `python3` for JSON parsing (cross-reference `python-helpers.md`).
4. `## Config-driven definitions & recipes` — a definition file format (`value|Label` columns + `HEADER|Category`) and saved "recipes" runnable by name (`run <name>`). Show the catalog row format that the full-control picker (`interaction.md`) consumes.

- [ ] **Step 3: Verify + commit**

```
for h in "Auth tiers & credential resolution" "Output directory resolution" "Paginated fetch → CSV (Ctrl+C-safe)" "Config-driven definitions & recipes"; do grep -q "## $h" cli-wrapper-helper/references/data-cli.md && echo "OK: $h" || echo "MISSING: $h"; done
grep -rinE 'hs |ZT_|hubspot|zena|nightly|\bcrm\b' cli-wrapper-helper/references/data-cli.md
git add cli-wrapper-helper/references/data-cli.md
git commit -m "feat(cli-wrapper-helper): add data-cli.md — auth tiers, output-dir resolution, paginated fetch→CSV, recipes/catalogs" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: four `OK:` lines; no leakage.

---

## Task 7: architecture.md — project shape, launcher, hooks, tool skeleton

**Files:**
- Modify: `cli-wrapper-helper/references/architecture.md`

- [ ] **Step 1: Read sources**

Run:
```
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/README.md | sed -n '80,200p'
git -C /Users/tomlinson/repos/hubspot-nightly.git ls-tree -r --name-only HEAD _toolbox | grep -vE '_examples|nightly/|tools/_examples'
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/git-hooks/pre-push
```

- [ ] **Step 2: Append these `##` sections**

1. `## Multi-file toolbox layout` — the canonical split: `_lib.sh` (palette/auth/core), `_helpers.sh` (UI), `_<domain>-helpers.sh` (feature libs), `tools/<verb>.sh` (one file per tool), `_data/` (catalogs/definitions), `one-shots/` (ceremonial scripts), `.logs/` (lock/manifest/log). Generic names.
2. `## Entry-point launcher` — a single `launcher.sh` (zt.sh-style) that renders the wheelhouse menu and dispatches to `tools/<verb>.sh`, accepting global `--dry` / `--quiet`. Tools remain directly invokable for automation.
3. `## The tool skeleton` — the shared shape every `tools/<verb>.sh` follows (strict mode, source `_lib`/`_helpers`, parse flags incl. `--help`/`--dry`, resolve creds if it touches a service, acquire lock if it writes, do work, log). This shared skeleton is what makes "scaffold a new tool" mechanical. *Note: nightly's `nightly-scaffold.sh` is a stub — there is no working scaffolder to copy; this section codifies the skeleton tools already share.*
4. `## Repo hygiene hooks` — a `git-hooks/pre-push` + `install-git-hooks.sh` pattern for keeping a toolbox honest (lint/smoke before push). Generalize from `pre-push`.

- [ ] **Step 3: Verify + commit**

```
for h in "Multi-file toolbox layout" "Entry-point launcher" "The tool skeleton" "Repo hygiene hooks"; do grep -q "## $h" cli-wrapper-helper/references/architecture.md && echo "OK: $h" || echo "MISSING: $h"; done
grep -rinE 'hs |ZT_|hubspot|zena|nightly|\bcrm\b' cli-wrapper-helper/references/architecture.md
git add cli-wrapper-helper/references/architecture.md
git commit -m "feat(cli-wrapper-helper): architecture.md — toolbox layout, entry launcher, tool skeleton, repo-hygiene hooks" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: four `OK:` lines; no leakage (the italic stub note about the scaffolder is allowed — it is not a pattern body).

---

## Task 8: python-helpers.md (JSON sidecar) + palette.md reconcile

**Files:**
- Modify: `cli-wrapper-helper/references/python-helpers.md`
- Modify: `cli-wrapper-helper/references/palette.md`

- [ ] **Step 1: Add the JSON-sidecar section to python-helpers.md**

Append `## python3 as a JSON-parse sidecar for bash`: when a bash tool must parse API JSON without `jq`, pipe it to a one-line `python3 -c` that reads `sys.stdin`, walks the structure, and prints tab/CSV-ready rows. Show a concrete generic example (parse a list of objects → print selected fields). Note: stdlib only, `json` module.

- [ ] **Step 2: Reconcile palette.md**

Run:
```
git -C /Users/tomlinson/repos/hubspot-nightly.git show HEAD:_toolbox/_lib.sh | grep -nE "\\\\033\\[|38;5;" | sed -n '1,40p'
```
Compare named 256-colors in the source palette against `cli-wrapper-helper/references/palette.md`. If the source defines named colors not already present (e.g. `TEAL`, `SLATE`, or others), add them to `palette.md` with their ANSI codes. If everything is already covered, leave `palette.md` unchanged and note "palette already complete" in the commit body.

- [ ] **Step 3: Verify + commit**

```
grep -q "## python3 as a JSON-parse sidecar for bash" cli-wrapper-helper/references/python-helpers.md && echo "OK: sidecar" || echo "MISSING: sidecar"
grep -rinE 'hs |ZT_|hubspot|zena|nightly|\bcrm\b' cli-wrapper-helper/references/python-helpers.md cli-wrapper-helper/references/palette.md
git add cli-wrapper-helper/references/python-helpers.md cli-wrapper-helper/references/palette.md
git commit -m "feat(cli-wrapper-helper): python-helpers JSON sidecar + palette reconcile" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: `OK: sidecar`; no leakage.

---

## Task 9: bash-tui/SKILL.md — reframe as the operating-language entry

**Files:**
- Modify: `cli-wrapper-helper/skills/bash-tui/SKILL.md`

- [ ] **Step 1: Reframe the intro + References block**

Edit the prose under `# Bash TUI Toolkit` (keep the frontmatter `name:`/`description:` triggers, but extend `description` with operational phrases: "dry-run mode", "make it safe to re-run", "single-instance lock", "grouped menu"). Change the opening sentence to frame this as **the operating language for bash helper CLIs** (visual + interaction + operational/safety), not just a TUI look.

Replace the `## References` list so it links all eight bash-side files in spine→…→structure order:
```
- `${CLAUDE_PLUGIN_ROOT}/references/design-language.md` — the shared spine (read first)
- `${CLAUDE_PLUGIN_ROOT}/references/palette.md` — raw color reference
- `${CLAUDE_PLUGIN_ROOT}/references/components.md` — draw-a-widget catalog
- `${CLAUDE_PLUGIN_ROOT}/references/interaction.md` — menus, pickers, ceremonies, dry-run UX
- `${CLAUDE_PLUGIN_ROOT}/references/bash-safety.md` — bash 3.2 correctness floor
- `${CLAUDE_PLUGIN_ROOT}/references/operations.md` — dry-run, locks, manifest, logging, smoke tests
- `${CLAUDE_PLUGIN_ROOT}/references/data-cli.md` — auth tiers, fetch→CSV, recipes, catalogs
- `${CLAUDE_PLUGIN_ROOT}/references/architecture.md` — project shape, launcher, hooks, tool skeleton
```

- [ ] **Step 2: Add an operating-language checklist pointer**

In the "Mandatory Checklist" area, add a short note: tools that **write/upload/mutate** must also apply the operational floor (dry-run, lock, manifest, logging) per `operations.md`; tools that **talk to a service** apply the auth tiers per `data-cli.md`.

- [ ] **Step 3: Verify all eight links present + commit**

```
for f in design-language palette components interaction bash-safety operations data-cli architecture; do grep -q "references/$f.md" cli-wrapper-helper/skills/bash-tui/SKILL.md && echo "OK: $f" || echo "MISSING: $f"; done
git add cli-wrapper-helper/skills/bash-tui/SKILL.md
git commit -m "feat(cli-wrapper-helper): reframe bash-tui as the operating-language entry; link all 8 references" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: eight `OK:` lines.

---

## Task 10: python-helper/SKILL.md — inherit the spine

**Files:**
- Modify: `cli-wrapper-helper/skills/python-helper/SKILL.md`

- [ ] **Step 1: Add references to the spine + sidecar**

In the `## Reference` section, add links to `${CLAUDE_PLUGIN_ROOT}/references/design-language.md` ("inherit the shared visual language") and confirm `${CLAUDE_PLUGIN_ROOT}/references/python-helpers.md` is linked (it holds the new JSON-sidecar pattern). One sentence: python helpers share the same palette/markers/indent law as bash tools.

- [ ] **Step 2: Verify + commit**

```
for f in design-language python-helpers; do grep -q "references/$f.md" cli-wrapper-helper/skills/python-helper/SKILL.md && echo "OK: $f" || echo "MISSING: $f"; done
git add cli-wrapper-helper/skills/python-helper/SKILL.md
git commit -m "feat(cli-wrapper-helper): python-helper inherits design-language spine" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: two `OK:` lines.

---

## Task 11: manifests → v2.0.0 + rewritten description

**Files:**
- Modify: `cli-wrapper-helper/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Bump plugin.json**

Set `"version": "2.0.0"` and replace `"description"` with:
`"The shared operating language for agent-built helper CLIs — one visual + interaction + safety language across interactive bash TUIs and python helper scripts, so every tool an agent builds looks, feels, and behaves the same."`

- [ ] **Step 2: Update marketplace.json**

In `.claude-plugin/marketplace.json`, find the `cli-wrapper-helper` entry and set its `"version"` to `2.0.0` and `"description"` to the exact same string as Step 1.

- [ ] **Step 3: Verify versions match + JSON valid + commit**

```
python3 -c "import json; a=json.load(open('cli-wrapper-helper/.claude-plugin/plugin.json')); m=[p for p in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if p['name']=='cli-wrapper-helper'][0]; assert a['version']=='2.0.0'==m['version'], (a['version'], m['version']); assert a['description']==m['description']; print('OK versions+desc match:', a['version'])"
git add cli-wrapper-helper/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "release(cli-wrapper-helper): v2.0.0 — operating language for agent-built helper CLIs" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: `OK versions+desc match: 2.0.0`.

---

## Task 12: evals.json — trigger cases for the new layers

**Files:**
- Modify: `cli-wrapper-helper/evals/evals.json`

- [ ] **Step 1: Read the existing structure**

Run: `cat cli-wrapper-helper/evals/evals.json` — note the exact shape of each eval case (keys, which skill it expects).

- [ ] **Step 2: Add additive cases matching that shape**

Add at least one case per new layer, expecting the `bash-tui` skill to trigger:
- interaction: prompt "build a grouped arrow-key menu with destructive-action confirmation"
- operational: prompt "add a dry-run mode and make this CLI safe to re-run"
- safety: prompt "this watch loop loses its counter — make the breathing animation work"
- data: prompt "wrap this CLI's API with token auth and export records to CSV"

Match the existing JSON key names exactly; do not restructure existing cases.

- [ ] **Step 3: Verify JSON valid + commit**

```
python3 -c "import json; d=json.load(open('cli-wrapper-helper/evals/evals.json')); print('OK evals parse,', len(d) if isinstance(d,list) else len(d.get('evals', d)), 'top-level')"
git add cli-wrapper-helper/evals/evals.json
git commit -m "test(cli-wrapper-helper): eval triggers for interaction/operational/safety/data layers" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: `OK evals parse, …`.

---

## Task 13: final acceptance sweep

**Files:** none created — verification only.

- [ ] **Step 1: All nine reference files present & non-empty**

```
for f in design-language palette components interaction bash-safety operations data-cli architecture python-helpers; do test -s "cli-wrapper-helper/references/$f.md" && echo "OK: $f" || echo "MISSING/EMPTY: $f"; done
```
Expected: nine `OK:` lines.

- [ ] **Step 2: Global leakage sweep (acceptance criterion #3)**

```
grep -rinE 'hs |ZT_|hubspot|zena|nightly|\bcrm\b|deskflex' cli-wrapper-helper/references/ | grep -vi 'seen in the wild'
```
Expected: no output. Any line printed is a leak to fix (re-open that file, generalize, re-commit).

- [ ] **Step 3: Operational patterns present (acceptance criterion #2)**

```
grep -q "PID single-instance lock" cli-wrapper-helper/references/operations.md && grep -q "Dry-run stub layer" cli-wrapper-helper/references/operations.md && grep -q "Manifest idempotency" cli-wrapper-helper/references/operations.md && grep -q "Subshell-eats-state" cli-wrapper-helper/references/bash-safety.md && grep -q "FIFO" cli-wrapper-helper/references/components.md && echo "OK: operational/safety patterns present"
```
Expected: `OK: operational/safety patterns present`.

- [ ] **Step 4: Skill wiring + version (acceptance criteria #4, #6)**

```
for f in design-language palette components interaction bash-safety operations data-cli architecture; do grep -q "references/$f.md" cli-wrapper-helper/skills/bash-tui/SKILL.md || echo "bash-tui MISSING link: $f"; done; echo "bash-tui link check done"
python3 -c "import json; a=json.load(open('cli-wrapper-helper/.claude-plugin/plugin.json'))['version']; print('plugin version', a); assert a=='2.0.0'"
```
Expected: "bash-tui link check done" with no MISSING lines; `plugin version 2.0.0`.

- [ ] **Step 5: Confirm clean tree (all work committed)**

```
git -C "/Users/tomlinson/Projects/VIBE CODING/onnozelaer-claude-marketplace" status --porcelain cli-wrapper-helper .claude-plugin/marketplace.json
```
Expected: no output (everything committed). If anything shows, commit it.

No commit for Task 13 (verification only). If any check fails, fix in the owning task's file and re-commit there.

---

## Self-Review (completed by plan author)

**Spec coverage** — every spec section maps to a task:
- 5 new references → Tasks 1, 3, 4, 5, 6. ✓
- 4 updated references → Tasks 2 (components), 7 (architecture), 8 (python-helpers + palette). ✓
- Two skills reframed → Tasks 9, 10. ✓
- Harvest inventory rows → distributed across Tasks 1–8 with exact source paths. ✓
- Generalization rule → "Conventions" block + per-task leakage gate + Task 13 global sweep. ✓
- Version & manifest → Task 11. ✓ Evals → Task 12. ✓
- Acceptance criteria #1–#8 → Task 13 steps 1–5 (file presence, leakage, operational presence, skill wiring, version, clean tree) + per-task section checks. ✓
- `nightly-scaffold` stub accuracy note → Task 7 Step 2 §3. ✓

**Placeholder scan** — the six hard patterns (FIFO breathing, dry-run stub, PID lock, manifest, auth resolver, confirmation ceremony) have complete embedded code. Visual/structural sections specify exact source paths + required section outlines rather than inventing frames that must match real source — this is deliberate (faithful lift > invented code), not a placeholder.

**Type/name consistency** — skeletons share a consistent vocabulary across files: `LOG_DIR`, `TOOL_NAME`, `$DRY`/`$DRY_RUN`, `die()`, `log()`, `info()`, `COLOR_ERROR`/`COLOR_MUTED`/`COLOR_WARN` semantic tokens, `VENDOR_CLI`/`TOKEN_FILE`. `--dry-run`/`--dry` both accepted (matches existing SKILL flag-parsing). The full-control picker's `value|Label` + `HEADER|Category` catalog format is defined once in `data-cli.md` and referenced from `interaction.md`. ✓
