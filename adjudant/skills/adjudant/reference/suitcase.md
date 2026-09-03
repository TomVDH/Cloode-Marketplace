# Suitcase and cockpit awareness

Run `suitcase-brief` for full orientation; this file is the standing summary.

The suitcase is a personal iCloud-synced terminal environment: a zsh + tmux cockpit
plus a two-tier agent system, `yap` (talk) and `agent-bus` (work: headless
dispatch, file-is-truth contract, multi-lane runs). It exists on both machines;
detection is a PATH probe for `suitcase-brief` (never executed automatically).
Paths inside the brief are emitted via `$HOME` at runtime, so its output is
correct on either machine.

## Division of canon

- The vault is canonical for decisions and project context. The suitcase docs
  (COMMANDS.md, CHANGELOG.md, AGENT-PROTOCOL.md under the iCloud IDE folder)
  are canonical for the tools themselves.
- Adjudant never duplicates suitcase documentation into the vault; it points.

## Ground rules when a session touches suitcase territory

1. Vault writes go through adjudant, always; the suitcase never writes the vault.
2. `agent-bus protocol` prints the binding collaboration contract (roles,
   disjoint lanes, BLOCKED/QUESTION, trifecta safety rules); it governs any
   bus participation. It ends with a paste-ready drop-in block for a
   project's AGENTS.md.
3. Run `snap` before editing suitcase files; run `suitcase doctor` when the
   environment misbehaves.
4. For real suitcase work, run `suitcase-brief` and read the docs it points
   to; this summary is not a substitute.

## Where adjudant surfaces it

- SessionStart hook: one pointer line on fresh `startup` when the CLI is on
  PATH (never the full brief; roughly 500 tokens saved per session).
- `check` JSON: `suitcase.present` (PATH probe only).
- `sitrep`: one environment line when present, skipped when absent.

Next step when the suitcase is relevant to the task at hand: run `suitcase-brief`.
