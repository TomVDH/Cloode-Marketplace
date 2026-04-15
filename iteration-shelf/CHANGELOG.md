# Changelog — iteration-shelf

All notable changes to this plugin are documented here. The format follows Keep a Changelog, and the version numbers follow semantic versioning.

---

## [0.1.0] — 2026-04-14

First release. Extracts the iteration-shelf pattern from the DutchBC portal project into a reusable plugin.

### Added
- Main skill `iteration-shelf` with explicit invocation (`/iteration-shelf`)
- Two HTML templates — curated shelf and monster index — both self-contained, zero-dependency, zero build step
- Terminal-aesthetic design tokens hard-coded into the templates (dark, monospace, hairline-bordered)
- Tag palette with nine shipped slugs: `original`, `draft`, `star`, `locked`, `quarantined`, `quiet`, `og-rich`, `og-true`, `reset`
- Card schema shared across both shelves (id, tag, optional quote, optional note, frame slot, actions)
- Monster-index browser-safety protocol — never auto-load, warn at 20+, lazy iframes, inject-don't-hide, cache-bust on reload
- Sticky sidebar outliner with scrollspy, segment counters, click-to-jump-and-load, shift-click-to-unload
- Three-state segment button (idle / partial / full) that re-syncs on every single-card load
- Column switcher (1× / 2× / 3×) with `localStorage` persistence and keyboard shortcuts
- Global controls: loaded counter (red at >25), unload all, reload loaded
- Optional top-of-page note banners with four tones (info / warning / success / danger)
- Reference docs:
  - `design-tokens.md` — CSS custom properties, typography, anti-slop rules
  - `card-anatomy.md` — card schema and tag palette
  - `interaction-model.md` — loading, keyboard, sidebar, warn-gate, safety rules
  - `manifest-schema.md` — JSON manifest spec with validation rules
  - `integration.md` — Superpowers and Cabinet plugin hookups
- Worked example manifest with four segments (star, fc, hi, fy)
- Auto-manifest init heuristic (family grouping by filename prefix)

### Integration
- Superpowers: mandatory `full-output-enforcement`, chrome-override for aesthetic skills
- Cabinet: Bostrol owns shelf operations; session-noted; decision-logged on tag changes
- Standalone mode works cleanly without either

### Known limitations
- Era-grouping variant (`layout: "era"`) is not yet shipped. Falls back to `"family"` with a warning.
- Theme params are hard-coded (no `--accent` / `--bg` override). Deferred until a reuse project asks.
- Init subflow drafts a manifest but does not auto-generate shelves — always hands back for user refinement first.

### Provenance
Pattern extracted from the DutchBC portal repo, `concepts/directions/_monster-index.html` at commit `54d4957`. Spec filed under Tom's direction, 2026-04-14.
