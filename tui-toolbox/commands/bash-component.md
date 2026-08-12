---
description: Generate a single bash UI component — chevron menu, braille spinner, comet-tail loading bar, table with fixed columns, splash banner, or pixel-scatter transition — ready to drop into an existing script.
allowed-tools: Read
---

Generate a single bash UI component using the `bash-tui` skill.

Ask the user which component they need:
- **menu** — single-select chevron menu with arrow-key navigation loop
- **spinner** — braille spinner (timed) or breathing spinner (background/idle)
- **loading-bar** — comet-tail loading bar with configurable width
- **table** — fixed-width column table with `trunc()` cells and dim pipe separators
- **splash** — ASCII block-letter banner with optional loading bar
- **transition** — pixel-scatter screen transition

Ask for any configuration details (e.g. menu option names, column names and widths,
banner text). Then output the component as a ready-to-paste bash function using the
reference implementation from `${CLAUDE_PLUGIN_ROOT}/references/components.md`.
Include a brief usage comment above the function.
