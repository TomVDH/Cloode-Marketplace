# Interaction Reference

> How a user moves through a tool. `components.md` draws individual widgets;
> this file composes them into flows.

Use semantic color roles throughout — never raw ANSI. All role names map to
variables defined in `design-language.md`.

---

## Wheelhouse menus

A wheelhouse menu organises actions into top-level groups, each containing one
or more sub-groups. Arrow keys navigate; `q` exits. Items carry optional status
tags rendered with semantic roles.

### Tag vocabulary

| Tag | Rendered as | Role |
|-----|-------------|------|
| `COMING SOON` | dim badge after label | `COLOR_MUTED` |
| `deprecated` | dim badge after label | `COLOR_MUTED` |
| `⚠ destructive` | error badge after label | `COLOR_ERROR` |
| `read-only` | info badge after label | `COLOR_INFO` |

### Structure layout

```
# GROUP A #
  SUB-GROUP 1
    Action Alpha                  (tool-alpha)
    Action Beta                   (tool-beta · read-only)
    Action Gamma                  (tool-gamma · ⚠ destructive)
    Action Delta                  (tool-delta · deprecated)

# GROUP B #
  SUB-GROUP 2
    Action Echo                   (tool-echo)
    Action Foxtrot                (tool-foxtrot · COMING SOON)

# GROUP C #
  SUB-GROUP 3
    Action Golf                   (tool-golf)
  SUB-GROUP 4
    Action Hotel                  (tool-hotel · COMING SOON)

# MISCELLANEOUS #
    Action India                  (tool-india)
    Action Juliet                 (tool-juliet · COMING SOON)
```

Top-level group headers use `#` decorators and render in `COLOR_TITLE` (bold).
Sub-group labels are bold, not colored. Actions render as a single-select menu
(see `components.md` → Menus → Single Select) with the status tag appended
after `·`.

### Drawing tags inline

```bash
# Tag constants
TAG_SOON="${COLOR_MUTED}── COMING SOON${RESET}"
TAG_DEPR="${COLOR_MUTED}── deprecated${RESET}"
TAG_DESTR="${COLOR_ERROR}── ⚠ destructive${RESET}"
TAG_RO="${COLOR_INFO}── read-only${RESET}"

# In the draw function, after the label:
printf "  ${COLOR_MUTED}›  %s${RESET}  %s\n" "$label" "$TAG_SOON"
```

Navigation skips `COMING SOON` items (same pattern as `components.md` →
Coming Soon Items).

*seen in the wild: a four-wheelhouse interactive menu with 13 tools across CMS
actions, object actions, provisioning, and miscellaneous — each tool invocable
directly as a sub-script for automation*

---

## The picker family

Four picker shapes cover every selection need. All share the `›› / ›` chevron
focus convention from `components.md`.

### Single-select

Standard item list. `›› BOLD` = focused, `› DIM` = unfocused.
Full implementation in `components.md` → Menus → Single Select.

```
  ›  Option A
  ›› Option B          ← focused
  ›  Option C
```

### Boolean toggle

Circle fill indicates current state: `●` on, `○` off.
Full implementation in `components.md` → Menus → Boolean Toggle.

```
  ›› ● Export live      ← focused, on
  ›  ○ Dry run only
```

### Multi-select

Checkboxes persist across navigation. `[x]` selected, `[ ]` unselected.
Full implementation in `components.md` → Menus → Multi Select.

```
  ›› [x] Records        ← focused
  ›  [ ] Reports
  ›  [x] Snapshots
```

### Full-control catalog picker

For large, categorised field sets. Catalog rows are `value|Label` entries
interspersed with `HEADER|Category Name` separator rows. Defined externally —
see `data-cli.md` for the catalog file format.

**Globals:**

```bash
# Caller sets before calling parse_catalog:
CATALOG=()          # array of "value|Label" and "HEADER|Category" strings
DEFAULTS=",val1,val2,"   # comma-wrapped CSV of pre-selected values
```

**Parse:**

```bash
parse_catalog() {
  NAMES=() LABELS=() IS_HEADER=() ON=()
  local name label entry
  for entry in "${CATALOG[@]}"; do
    name="${entry%%|*}"; label="${entry#*|}"
    if [[ "$name" == "HEADER" ]]; then
      NAMES+=("HEADER"); LABELS+=("$label"); IS_HEADER+=(1); ON+=(0)
    else
      NAMES+=("$name"); LABELS+=("$label"); IS_HEADER+=(0)
      if [[ "$DEFAULTS" == *",$name,"* ]]; then ON+=(1); else ON+=(0); fi
    fi
  done
}
```

**Draw viewport** (scrollable window, `VIEWPORT` rows visible):

```bash
draw_catalog_viewport() {
  local end=$(( scroll + VIEWPORT ))
  (( end > ${#NAMES[@]} )) && end=${#NAMES[@]}
  local r check
  for (( r=scroll; r<end; r++ )); do
    if [[ "${IS_HEADER[$r]}" -eq 1 ]]; then
      if [[ $r -eq $pos ]]; then
        printf "  ${COLOR_ACTIVE}› ── %s ──${RESET}\n" "${LABELS[$r]}"
      else
        printf "    ${COLOR_MUTED}── %s ──${RESET}\n" "${LABELS[$r]}"
      fi
    else
      check="${COLOR_MUTED}[ ]${RESET}"
      [[ "${ON[$r]}" -eq 1 ]] && check="${COLOR_SUCCESS}[x]${RESET}"
      if [[ $r -eq $pos ]]; then
        printf "  ${COLOR_ACTIVE}›${RESET} %s ${BOLD}%-32s${RESET} ${COLOR_MUTED}(%s)${RESET}\n" \
          "$check" "${LABELS[$r]}" "${NAMES[$r]}"
      else
        printf "    %s %-32s ${COLOR_MUTED}(%s)${RESET}\n" \
          "$check" "${LABELS[$r]}" "${NAMES[$r]}"
      fi
    fi
  done
}
```

**Live count** — display below the viewport, updated on every redraw:

```bash
count_selected() {
  TOTAL=0; SELECTED=0
  local i
  for (( i=0; i<${#IS_HEADER[@]}; i++ )); do
    [[ "${IS_HEADER[$i]}" -eq 0 ]] || continue
    TOTAL=$(( TOTAL + 1 ))
    [[ "${ON[$i]}" -eq 1 ]] && SELECTED=$(( SELECTED + 1 ))
  done
}
# After draw_catalog_viewport:
count_selected
printf "  ${COLOR_MUTED}%d of %d selected${RESET}\n" "$SELECTED" "$TOTAL"
```

**Header row toggles the whole category** — pressing Space/Enter on a `HEADER`
row flips all items in the category below it (all on → all off; any on → all off):

```bash
toggle_category() {
  local hdr=$1 p=$(( hdr + 1 )) any_on=0
  while [[ $p -lt ${#NAMES[@]} ]] && [[ "${IS_HEADER[$p]}" -eq 0 ]]; do
    [[ "${ON[$p]}" -eq 1 ]] && any_on=1; p=$(( p + 1 ))
  done
  local new_val=$(( any_on == 1 ? 0 : 1 ))
  p=$(( hdr + 1 ))
  while [[ $p -lt ${#NAMES[@]} ]] && [[ "${IS_HEADER[$p]}" -eq 0 ]]; do
    ON[$p]=$new_val; p=$(( p + 1 ))
  done
}
```

**Back navigation** — pressing `b` returns to the previous screen. Callers
check for a sentinel value:

```bash
read -rsn1 key
[[ "$key" == "b" || "$key" == "B" ]] && { PICKER_RESULT="__BACK__"; return; }
```

**Selection preview** — after the picker exits, print the resulting value list
before proceeding:

```bash
printf "  ${COLOR_MUTED}Selected fields:${RESET}\n"
for (( i=0; i<${#NAMES[@]}; i++ )); do
  [[ "${IS_HEADER[$i]}" -eq 0 ]] && [[ "${ON[$i]}" -eq 1 ]] || continue
  printf "  ${COLOR_MUTED}·${RESET} %s\n" "${LABELS[$i]}"
done
```

---

## Confirmation ceremonies

Destructive actions require the user to type a literal word before proceeding.
The word is passed by the caller so the ceremony is reusable across tools.

```bash
confirm_destructive() {
  local word="$1"
  printf "  ${COLOR_ERROR}${BOLD}This is destructive.${RESET} Type ${BOLD}%s${RESET} to proceed: " "$word"
  read -r reply
  [[ "$reply" == "$word" ]] || { printf "  ${COLOR_MUTED}Aborted.${RESET}\n"; return 1; }
}
```

**Usage pattern:**

```bash
confirm_destructive "PURGE" || exit 0
# ... destructive action follows ...
```

**Before the ceremony** — always show a preview of exactly what will be
affected. Structure:

1. `cls` — clear screen.
2. Section header: `${COLOR_TITLE}${BOLD}━━ Action preview ━━${RESET}`.
3. Scope summary: count, size, date range, oldest/newest.
4. First 10 targets listed with `${COLOR_MUTED}-${RESET} <name>` markers; `… N more` if truncated.
5. Warning block using `${COLOR_WARN}${BOLD}⚠  WARNING${RESET}` followed by consequence lines in `COLOR_MUTED`.
6. `confirm_destructive` call.

**Dry-run short-circuits the ceremony** — if `DRY_RUN` is true, print the
dry-run banner (see below) and exit before reaching `confirm_destructive`.

*seen in the wild: snapshot purge requiring the user to type `PURGE` after a
preview listing affected folders with count, size, and age scope*

---

## Dry-run as a UX surface

`--dry` / `--dry-run` activates a preview mode: the tool runs its full flow
(pickers, summaries, confirmations) but stubs out every write. The stub-layer
mechanics live in `operations.md`; this section covers the
visual contract.

### Banner

Print immediately after the splash, before any other output:

```bash
$DRY_RUN && printf "  ${COLOR_WARN}${BOLD}DRY RUN${RESET}${COLOR_MUTED} — no data will be written${RESET}\n"
```

The banner is the single persistent signal that the session is safe. Display it
wherever the tool clears the screen (once per `cls` call that enters a new
phase).

### Simulated action labels

In dry-run, prefix every would-be write line with `${COLOR_WARN}[dry]${RESET}`:

```bash
if $DRY_RUN; then
  printf "  ${COLOR_WARN}[dry]${RESET} Would delete: %s\n" "$target"
else
  rm -rf "$target"
  printf "  ${COLOR_SUCCESS}✓${RESET} Deleted: %s\n" "$target"
fi
```

### Early exit at the execution boundary

After pickers and summaries are shown, the tool reaches the write phase.
In dry-run, stop here with a summary and exit cleanly — do not enter the write
loop:

```bash
if $DRY_RUN; then
  printf "  ${COLOR_WARN}${BOLD}DRY RUN — nothing written.${RESET}\n"
  printf "  ${COLOR_MUTED}%d item(s) would be processed.${RESET}\n\n" "$COUNT"
  exit 0
fi
```

### Flag wiring

Parse `--dry` and `--dry-run` as equivalent at the top of every tool:

```bash
DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --dry|--dry-run) DRY_RUN=true ;;
  esac
done
```

Dry-run mode may also be offered as a toggle on the summary screen (a
boolean-toggle picker item), letting the user flip it interactively before
confirming. The pattern: after selection, the tool draws a summary screen
listing what will run (item count, destination, active flags) and includes a
boolean-toggle row (`›› ● Export live` / `›  ○ Dry run only`) among the items.
Toggling flips `DRY_RUN` in place and redraws the screen; confirming proceeds
with whatever state the toggle currently shows.

*seen in the wild: dry-run offered both as a CLI flag and as a toggle in the
export summary screen; the toggle updates `DRY_RUN` before the write phase*
