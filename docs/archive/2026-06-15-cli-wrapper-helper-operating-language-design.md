---
date: 2026-06-15
status: design — ready for implementation
scope: cli-wrapper-helper plugin — graduate from a two-skill pattern library into the shared operating language for agent-built helper CLIs, harvesting the visual + interaction + operational/safety patterns proven in the hubspot-nightly _toolbox
plugin: cli-wrapper-helper
version-target: 2.0.0
source-of-truth: /Users/tomlinson/repos/hubspot-nightly.git (branch campaign-factory) — _toolbox/ + _docs/_archive/gen1-scripts/
---

# cli-wrapper-helper v2.0.0: the shared operating language for agent-built helper CLIs

## Problem statement

`cli-wrapper-helper` v1.0.0 is a two-skill pattern library (`bash-tui`, `python-helper`) that captures roughly the **visual** layer of a CLI — palette, menus, spinners, tables, splash banners — and the basics of interaction. It was extracted early, from a downstream copy of the toolbox (`hubspot-dev/scripts/hubspot-toolbox/`), before the language had finished forming.

The language finished forming somewhere else. The canonical source is **`hubspot-nightly` `_toolbox/`** ("Stream 1 — CLI Toolbox", v1.0.0, menu v1.6.1), and it carries three things the plugin never captured:

1. **The terminal language was never written up.** The repo's *web* form got a 540-line `DESIGN.md` (OKLCH paper palette, IBM Plex, the deskflex CSS world). The *terminal* language got nothing — it lives only in `_toolbox/_lib.sh`/`_helpers.sh` and the gen1 demo/picker gallery. There is no written articulation of it anywhere.

2. **A whole operational/safety layer is missing from the plugin.** dry-run stub layers, PID single-instance locks, manifest idempotency, auth tiers, `.logs/` logging, smoke tests, and the bash-3.2 correctness floor (FIFO-over-pipe, the picker-crash class). These are the genuinely hard-won patterns — the ones an agent should never have to re-derive or improvise.

3. **A method, not just an output.** The gen1 archive (`_docs/_archive/gen1-scripts/demos/demo-ui/sections/*` + `pickers/picker-*`) shows the language was *designed*: build many variants in a demo harness, preview them through pickers, promote the chosen one to canon. That method is itself worth recording so the language can be extended the same way.

The plugin's stated purpose — per the user — is to be **"a shared UI/UX language for helper CLI apps I produce using agents."** For that to hold across many future agent-built tools, the language has to be (a) written down in one place, (b) complete enough that generated tools *look, feel, and behave* same-handed, and (c) generic — the patterns, not the HubSpot domain they were proven in.

This spec makes `cli-wrapper-helper` that written language: the `DESIGN.md` the terminal side never got.

## Goals

1. **One operating language, three layers.** Encode the visual, interaction, and operational/safety layers as a coherent system any agent inherits on skill load. An agent building a helper CLI gets the look, the interaction grammar, *and* the safety floor by default.
2. **Harvest from canon, generalized.** Lift the real, battle-tested patterns from `hubspot-nightly` `_toolbox/` + the gen1 gallery — but strip every `hs`/CRM/Zena specific. The pattern body is generic; HubSpot survives only as one-line "seen in the wild" illustrations.
3. **Preserve the plugin's grain.** Keep one-file-one-concern (the existing palette/components/architecture split). Add focused reference files; don't bloat existing ones into grab-bags.
4. **One trigger, deep references.** Keep two skills (`bash-tui`, `python-helper`) with unchanged names and trigger surfaces. Depth lives in the references via progressive disclosure, not in a proliferation of skills.
5. **Additive, non-breaking.** Every v1.0.0 pattern stays valid. New material *extends*; the one supersede (FIFO-aware breathing) keeps the simple background form as the baseline case.
6. **A written method for extension.** Record the prototype-variants → preview → promote-to-canon method so the language grows deliberately, not by ad-hoc accretion.

## Non-goals

- **No HubSpot domain logic.** CRM export schemas, the nightly campaign seeder (`_toolbox/nightly/`), `hs`-specific endpoints, brand catalogs — none of it. Out of scope.
- **No web/email design system.** The root `DESIGN.md`, the deskflex CSS, the `__file-mounts__/_design-manager/` DnD email world are a *different* design system (browser, not terminal). Untouched.
- **No ERD/diagram tooling.** `_toolbox/tools/_examples/erd/*` (mermaid/graphviz/elk) is a domain tool, not part of the CLI language.
- **No bundled example scripts.** Per the earlier scoping decision, this is *harvest into the skills*, not *bundle a worked example*. The gen1 gallery and `_toolbox/` libs are sources to lift FROM, not copied IN.
- **No new skills, no skill renames.** Avoids symlink/eval churn. `bash-tui` is reframed in place.
- **No external frameworks.** No ncurses, no `tput` for color, no TUI library. bash 3.2 + coreutils + optional `python3`/`curl`, as today.
- **No `/bash-harden` build this round.** Retrofitting the safety floor onto an existing script is a compelling command but is flagged as future work, not built here.

## The three-layer model

| Layer | Question it answers | Makes generated tools… |
|---|---|---|
| **Visual** | What does it look like? | …*look* same-handed |
| **Interaction** | How do you move through it? | …*feel* same-handed |
| **Operational / safety** | How does it behave, and how does it avoid hurting you? | …*behave* same-handed and trustworthy |

The visual layer is mostly present in v1.0.0. The interaction layer is partial. The operational/safety layer is absent. v2.0.0 completes all three.

## Reference structure

Same grain the plugin already uses. **★ = new file; ↑ = existing file, expanded.**

```
references/
  design-language.md  ★  SPINE. The shared vocabulary every skill inherits: semantic color
                          roles (not raw hex — that's palette.md), the two-space-indent law,
                          the marker vocabulary (✓ ✗ ⚠ ℹ), motion/speed tiers, the
                          "same-handed" principle, and an "Extending the language" section
                          recording the gen1 prototype→preview→promote method.
  palette.md             ↑ raw ANSI + 256-color reference. Scope unchanged; reconcile any
                          new named colors present in nightly's _lib.sh.
  components.md          ↑ draw-a-widget catalog: splash + bootloader (the poc-spinning-z
                          depth-shaded rotating logo as canon), tables, spinners, breathing
                          (FIFO-aware; old background form kept as the simple case), comet-tail,
                          pixel-scatter transitions, status markers, section headers.
  interaction.md      ★  compose-a-flow grammar: "wheelhouse" menus (top-level groups +
                          sub-groups + per-item status tags COMING SOON / deprecated /
                          ⚠ destructive / read-only), the arrow-key nav loop, the picker
                          family (single / boolean / multi / full-control catalog with
                          HEADER| rows, live count, preview, back-nav), typed-confirmation
                          ceremonies (e.g. type PURGE), and dry-run as a visible UX surface.
  bash-safety.md      ★  bash 3.2 correctness floor: strict mode + cleanup trap; the
                          subshell-eats-state trap and its FIFO fix; the full-control-picker
                          crash class; array quoting / ${arr[@]:-} under set -u; printf-not-
                          echo -e; the ANSI-width / trunc-before-color rule; CSV-preview safety.
  operations.md       ★  runtime safety floor: the dry-run convention + STUB LAYER (redefine
                          mutating functions to log + return plausible fake IDs when $DRY,
                          leave read-only helpers live); PID single-instance locks (.lock with
                          stale-PID auto-clear, released on EXIT/INT/TERM); manifest idempotency
                          (skip-unless---force); .logs/ logging; smoke-test + boilerplate-test pattern.
  data-cli.md         ★  wrapping an external CLI/API: auth TIERS (vendor CLI / API key / none)
                          with credential resolution (CLI-first → file fallback → validate) and
                          a configurable output dir (env → credentials file → default); paginated
                          fetch → Ctrl+C-safe CSV write; config-driven definitions + saved
                          "recipes" (run <name>); name|Label data catalogs driving pickers.
  architecture.md        ↑ multi-file project shape: _lib / _helpers / _<domain>-helpers split,
                          tools/, _data/, one-shots/, a single entry-point launcher (zt.sh-style
                          menu dispatcher with --dry / --quiet), git-hooks, and the consistent
                          tool skeleton that makes "scaffold a new tool" mechanical.
  python-helpers.md      ↑ read-and-report patterns + "python3 as a JSON-parse sidecar for bash"
                          (the micro-pattern bash uses to parse API JSON without jq).
skills/
  bash-tui/SKILL.md      ↑ reframed intro: "build a helper CLI in the shared operating
                          language." References the eight bash-side files above (every
                          reference except python-helpers.md), ordered spine → visual →
                          interaction → safety → operational → external → structure. Trigger
                          surface extended with operational phrases ("dry-run mode", "make it
                          safe to re-run", "single-instance lock", "grouped menu").
  python-helper/SKILL.md ↑ light touch: inherit the design-language spine + the JSON-sidecar
                          pattern; otherwise unchanged.
```

Five new reference files. The split is deliberate: `bash-safety` (language-level correctness on old bash) and `operations` (runtime behaviour: locks, dry-run, idempotency, logging) are distinct concerns with distinct audiences; `interaction` (compose-a-flow) is distinct from `components` (draw-a-widget). They cross-link rather than merge.

## Harvest inventory: what → where → source

Each pattern, its destination reference, and where to lift it from in the source-of-truth repo. Implementation pulls exact code from these locations and generalizes it.

| Layer | Pattern | Destination | Lift from (hubspot-nightly) |
|---|---|---|---|
| Visual | depth-shaded rotating-logo bootloader | `components.md` | `_toolbox/bootloader.sh`; canon origin `_docs/_archive/gen1-scripts/demos/poc-spinning-z.sh` |
| Visual | FIFO-aware breathing indicator | `components.md` (+ rationale in `bash-safety.md`) | `_toolbox/_watch-helpers.sh`, `_toolbox/tools/cms-watch.sh` (FIFO setup + read-in-main-shell) |
| Visual | tables, comet-tail, pixel-scatter transitions, spinners | `components.md` | `_toolbox/_helpers.sh`; gen1 `demo-ui/sections/{tables,progress,spinners,transitions}.sh` |
| Visual | semantic color roles, indent law, markers, motion tiers, **extend-the-language method** | `design-language.md` | `_toolbox/_lib.sh` (palette + roles); gen1 `demo-ui/sections/*` + `pickers/picker-*` (the method) |
| Interaction | wheelhouse menus + sub-groups + status tags | `interaction.md` | `_toolbox/main.sh`; menu structure documented in `_toolbox/README.md` |
| Interaction | full-control catalog picker (HEADER\| rows, live count, preview, back-nav) | `interaction.md` | `_toolbox/_export-helpers.sh` |
| Interaction | typed-confirmation ceremony | `interaction.md` | `_toolbox/tools/fm-snapshots-purge.sh` (typed PURGE) |
| Operational | dry-run convention + stub layer | `operations.md` | `_toolbox/nightly/_core.sh` (redefines mutating helpers when `$ZT_DRY`); `--dry` flag in `zt.sh` |
| Operational | PID single-instance lock + stale-clear | `operations.md` | `_toolbox/tools/fm-upload.sh` (`.logs/fm-upload.lock`) |
| Operational | manifest idempotency (skip-unless-`--force`) | `operations.md` | `_toolbox/tools/fm-upload.sh` (`.logs/fm-manifest.txt`) |
| Operational | logging | `operations.md` | `_toolbox/_logging.sh`, `.logs/` |
| Operational | smoke tests + boilerplate | `operations.md` | `_toolbox/_boilerplate_test.sh`, `_toolbox/_examples/*smoke*.sh` |
| Safety | bash 3.2 floor (FIFO, picker crash, array quoting, CSV-preview) | `bash-safety.md` | `_toolbox/_lib.sh`, `_toolbox/_export-helpers.sh`, `_toolbox/_watch-helpers.sh` |
| External | auth tiers + credential resolution + output-dir resolution | `data-cli.md` | `_toolbox/_lib.sh` (`zt_resolve_token`); auth-tier table + `ZT_EXPORTS_DIR` in `_toolbox/README.md` |
| External | paginated fetch → CSV; config-driven defs + recipes; name\|Label catalogs | `data-cli.md` | `_toolbox/_export-helpers.sh`, `_toolbox/tools/crm-export.sh`, `_data/crm-exports/*.def.sh` |
| Structure | multi-file layout, entry launcher, git-hooks, tool skeleton | `architecture.md` | `_toolbox/` tree; `zt.sh`; `_toolbox/git-hooks/pre-push`, `tools/install-git-hooks.sh` |
| Python | JSON-parse sidecar for bash | `python-helpers.md` | python3 inline-parse calls inside `_toolbox/_export-helpers.sh` |

**Accuracy note for implementation:** `_toolbox/tools/nightly-scaffold.sh` is a stub ("not yet implemented" per README). The "scaffold a new tool" material in `architecture.md` is therefore derived from the *consistent shape* of the existing tools (their shared skeleton), not lifted from a working scaffolder.

## Generalization rule

Every harvested pattern is rewritten generic before it lands:

- **Names:** `zt_*` → neutral (`ui_*`, `cli_*`, or unprefixed). No `ZT_`, `hs`, `HubSpot`, `Zena`, `nightly`, `campaign`.
- **Domain → placeholder:** "contacts/companies/deals" → "records/objects"; "HubSpot Design Manager" → "the remote service"; `hs` CLI → "the vendor CLI."
- **Illustration, not lift:** where a HubSpot reference clarifies a pattern, it appears as a single italic "seen in the wild: …" line, never in the pattern body.
- **Semantic tokens always:** harvested code uses the design-language semantic roles, never raw ANSI in output statements — even if the source did otherwise.

## Skills, commands, evals

- **Skills (2, names unchanged).** `bash-tui` reframed as the operating-language entry point; its reference list and trigger surface expand. `python-helper` gets the spine + JSON-sidecar pattern. One trigger pulls one skill; depth is in references.
- **Commands.** No new slash commands. `/bash-new` and `/bash-component` begin applying the language (strict mode, palette, dry-run/help scaffolding, the new components). *Future (not this round):* `/bash-harden` to retrofit the safety + operational floor onto an existing script.
- **Evals.** Add light trigger cases for the new layers so the skill still fires: e.g. "add a dry-run mode to this script", "make this CLI safe to re-run", "build a grouped arrow-key menu", "lock this so it can't run twice at once". Keep `evals/evals.json` additive; no restructuring.

## Version & manifest

- **v1.0.0 → v2.0.0** in `cli-wrapper-helper/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. The major bump signals the identity shift (pattern library → operating language) and the rewritten description, not a breaking change — back-compat is preserved.
- **Description rewrite** (both manifests), foregrounding the new identity. Direction: *"The shared operating language for agent-built helper CLIs — one visual + interaction + safety language across interactive bash TUIs and python helper scripts, so every tool an agent builds looks, feels, and behaves the same."*
- **Commit:** `release(cli-wrapper-helper): v2.0.0 — operating language harvest from hubspot-nightly _toolbox`.

## Acceptance criteria

1. Five new reference files exist and are non-empty: `design-language.md`, `interaction.md`, `bash-safety.md`, `operations.md`, `data-cli.md`. Four existing files updated: `components.md`, `architecture.md`, `python-helpers.md`, `palette.md` (if reconciled).
2. Every operational/safety pattern in the harvest inventory appears in a reference with a generic, copy-paste-ready implementation: dry-run stub layer, PID lock, manifest idempotency, logging, smoke test, FIFO breathing, bash-3.2 safety set.
3. No `hs`, `ZT_`, `HubSpot`, `Zena`, `nightly`, or CRM-domain identifier appears in any pattern body. Spot-check: `grep -riE 'hs |ZT_|hubspot|zena|nightly|crm' cli-wrapper-helper/references` returns only italic "seen in the wild" illustration lines, if any.
4. `bash-tui/SKILL.md` references the eight bash-side reference files (all except `python-helpers.md`) in spine→…→structure order, and its intro states the operating-language framing. `python-helper/SKILL.md` references `design-language.md` and `python-helpers.md`.
5. `design-language.md` includes the "Extending the language" method section.
6. Both manifests read `2.0.0` with the rewritten description; versions match (no drift).
7. `evals/evals.json` contains at least one new trigger case per new layer (interaction, operational/safety).
8. Every v1.0.0 pattern still present and valid; FIFO breathing documents the simple background form as the baseline case.

## Open questions

None blocking. Two judgment calls were resolved with the user: **v2.0.0** (over additive v1.1.0) to mark the identity shift; **five new reference files** (over merging to ~three) to preserve one-file-one-concern.
