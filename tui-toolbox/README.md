# TUI Toolbox

The shared operating language for agent-built helper CLIs. One visual, interaction, and operational-safety language across interactive bash TUIs and Python helper scripts, so every tool an agent builds looks, feels, and behaves like it came from the same hand.

Ships as part of the `toolshed` marketplace. No binaries, no build step: two skills, five slash commands, and nine reference files.

The language has three layers:

| Layer | Question it answers | Makes generated tools... |
|---|---|---|
| Visual | What does it look like? | ...look same-handed |
| Interaction | How do you move through it? | ...feel same-handed |
| Operational / safety | How does it behave, and how does it avoid hurting you? | ...behave same-handed and trustworthy |

---

## The two skills

| Skill | Territory | Typical triggers |
|---|---|---|
| `bash-tui` | Interactive terminal tools: menus, spinners, splash banners, pickers, tables, dry-run UX, single-instance locks, manifests | "bash script", "TUI", "CLI menu", "dry-run mode", "make it safe to re-run" |
| `python-helper` | Read-and-report scripts: sqlite, JSON, CSV readers with clean formatted output, stdlib only | "python helper", "query sqlite", "csv reader", "data reporter" |

The boundary is mutual and explicit: each skill's trigger description points at the other. Interactive menus and animation belong to `bash-tui`; anything involving real string manipulation, date parsing, arithmetic, or structured-data parsing belongs to `python-helper`. Both inherit the same design-language spine (palette, two-space indent, status markers), so a bash tool and a Python helper sitting side by side read as one toolkit.

---

## Commands

```
/bash-new          Scaffold a new polished bash TUI script (strict mode, palette, cleanup trap, menu)
/bash-component    Generate a single bash UI component (menu, spinner, loading bar, table, splash, transition)
/py-new            Scaffold a new Python helper from the starter template (argparse, die(), section(), cell())
/py-sqlite         Scaffold a Python sqlite reader (row_factory, ? placeholders, formatted readout)
/py-csv            Scaffold a Python CSV reader (DictReader, filters, optional aggregation)
```

---

## Reference file map

Read in spine-to-detail order: `design-language.md` is the spine, everything else hangs off it.

| File | Concern |
|---|---|
| `references/design-language.md` | The spine: semantic color roles, the two-space-indent law, marker vocabulary, motion tiers, the extend-the-language method |
| `references/palette.md` | Raw ANSI + 256-color reference |
| `references/components.md` | Draw-a-widget catalog: splash, bootloader, tables, spinners, breathing indicator, comet-tail, transitions |
| `references/interaction.md` | Compose-a-flow grammar: wheelhouse menus, the picker family, typed-confirmation ceremonies, dry-run as a UX surface |
| `references/bash-safety.md` | bash 3.2 correctness floor: strict mode, FIFO-over-pipe, array quoting, trunc-before-color |
| `references/operations.md` | Runtime safety floor: dry-run stub layer, PID locks, manifest idempotency, logging, smoke tests |
| `references/data-cli.md` | Wrapping an external CLI/API: auth tiers, paginated fetch to CSV, recipes, catalogs |
| `references/architecture.md` | Project shape: `_lib`/`_helpers` split, `tools/`, the entry-point launcher, git hooks, the tool skeleton |
| `references/python-helpers.md` | Read-and-report patterns, plus python3 as a JSON-parse sidecar for bash |

### Evals

`evals/evals.json` is the plugin's behavioral spec: ten prompt / expected-output cases across both tracks (seven bash-tui, three python-helper), covering the visual, interaction, and operational layers. It is documentation of intent. There is no runner; the cases exist so a change to skills or references can be judged against concrete expected behavior.

---

## PROVENANCE

The v2.0.0 pattern body was harvested on 2026-06-15 from the `hubspot-nightly` repo's `_toolbox/` directory (branch `campaign-factory`, toolbox v1.0.0 / menu v1.6.1) and its gen1 demo/picker gallery (`_docs/_archive/gen1-scripts/`). Design spec: `docs/superpowers/specs/2026-06-15-cli-wrapper-helper-operating-language-design.md` at the marketplace root.

Every harvested pattern was generalized before landing: `zt_*` names went neutral, domain nouns became placeholders ("records", "the remote service", "the vendor CLI"), and HubSpot survives only in single italic "seen in the wild" illustration lines.

### De-flavor grep gate

The references must stay generic. This grep may match only italic "seen in the wild" illustration lines (the `\bhs ` term needs the word boundary; without it, ordinary words like "paths" and "widths" false-positive):

```bash
grep -riE '\bhs |ZT_|hubspot|zena|nightly|crm' tui-toolbox/references
```

### Re-harvest procedure

When the source toolbox grows a new pattern worth lifting:

1. Lift from the canonical source only: `hubspot-nightly` `_toolbox/` (branch `campaign-factory`), never a downstream copy.
2. Route it to the reference that owns the layer: visual to `components.md`, flow to `interaction.md`, runtime safety to `operations.md`, shell correctness to `bash-safety.md`, external-service wrapping to `data-cli.md`, project shape to `architecture.md`.
3. Generalize per the rule above: neutral names, placeholder domains, semantic color tokens (never raw ANSI in output statements), at most one italic "seen in the wild" line per pattern.
4. Run the de-flavor grep gate; anything matching outside an illustration line does not land.
5. New visual components additionally pass the Prototype → Preview → Promote → Prune cycle recorded in `design-language.md` before entering `components.md`.
