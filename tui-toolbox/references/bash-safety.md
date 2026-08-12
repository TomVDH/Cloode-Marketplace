# Bash Safety Reference

> The correctness floor. Every pattern in this toolkit runs on bash 3.2 (macOS default). The six rules below are the hard-won ones — the failures are silent, the debugging is painful.

Read `design-language.md` first for the visual grammar. This file is about not breaking at the shell level.

---

## Strict mode + cleanup trap

Every script starts with two things: strict mode and a cleanup trap. No exceptions.

```bash
#!/usr/bin/env bash
set -euo pipefail
```

- `#!/usr/bin/env bash` — resolves bash from PATH rather than hardcoding `/bin/bash`, which is only 3.2 on macOS.
- `set -e` — exit immediately on any unhandled non-zero return.
- `set -u` — unset variables are errors, not silent empty strings.
- `set -o pipefail` — a pipeline fails if *any* stage fails, not just the last.

The cleanup trap restores the terminal to a known state on any exit path — including Ctrl+C and unhandled errors:

```bash
cleanup() {
  printf "\033[?25h"   # restore cursor (show_cur)
  printf "\033[0m\n"   # reset ANSI + newline
}
trap cleanup EXIT INT TERM
```

Without the trap, a crashed script leaves the user with an invisible cursor and a terminal in an unknown color state. This trap fires on `EXIT` (normal exit), `INT` (Ctrl+C), and `TERM` (kill signal).

Use the semantic cleanup pattern from `design-language.md` instead of raw ANSI in application code — but the trap itself must use raw escape sequences because it runs before the palette is guaranteed to be defined.

---

## Subshell-eats-state (use a FIFO)

**The bug:** piping into `while read` runs the loop body in a subshell. Any variables set inside the loop — counters, accumulator arrays, display state — are invisible to the parent shell once the pipe closes.

```bash
# BROKEN: counter is always 0 after the loop
count=0
some_producer | while IFS= read -r line; do
  count=$((count + 1))
  process "$line"
done
printf "Processed %d lines\n" "$count"   # prints 0
```

The assignment to `count` happens inside a subshell forked for the pipeline right side. The parent never sees it.

**The fix:** route the producer through a FIFO (named pipe) and read from it in the **main shell**. The main shell reads the FIFO directly — no subshell is forked:

```bash
fifo_dir="$(mktemp -d)"
fifo="${fifo_dir}/pipe"
mkfifo "$fifo"

cleanup_fifo() { rm -f "$fifo"; rmdir "$fifo_dir" 2>/dev/null || true; }
trap cleanup_fifo EXIT INT TERM

count=0
some_producer > "$fifo" 2>&1 &   # 2>&1 merges stderr into the data stream — only do this when the producer's stderr is meaningful progress you want the loop to render; otherwise drop 2>&1 so errors don't arrive as fake data lines
producer_pid=$!

while IFS= read -r -t 1 line || kill -0 "$producer_pid" 2>/dev/null; do
  [[ -n "${line:-}" ]] && { count=$((count + 1)); process "$line"; }
  redraw_status "$count"   # main-shell state — always current
done < "$fifo"

printf "  ${COLOR_SUCCESS}✓${RESET} %s\n" "Processed ${count} lines"
```

The `read -t 1` timeout also gives the breathing animation a clock tick on each second the producer is idle — the frame counter advances in the main shell and the display stays live. See `components.md` → *Breathing that survives a read loop* for the full animation pattern.

**Why mkfifo beats process substitution:** `while IFS= read -r line; do … done < <(producer_cmd)` uses bash process substitution, which also avoids the subshell problem. Process substitution `< <(...)` also keeps the read loop in the main shell and works on bash 3.2 — but there is no reliable way to capture the background producer's PID from it, so you cannot do `kill -0` liveness checks or clean shutdown. The FIFO + explicit background PID is the portable, manageable choice when the loop must track a long-lived producer.

*Seen in the wild: a watch loop that counted uploaded files and fed a live counter to the scroll region — piped version always showed 0; FIFO version worked.*

---

## Array quoting under set -u

With `set -u` active, referencing an unset variable is a fatal error. Arrays have an additional pitfall in bash 3.2: an empty array referenced as `"${arr[@]}"` expands to nothing, but under `set -u` this triggers *"unbound variable"*.

**Always quote array expansions:**

```bash
items=("alpha" "beta" "gamma")
for item in "${items[@]}"; do
  printf "  %s\n" "$item"
done
```

**Guard possibly-empty arrays** with the `:-` default:

```bash
# Safe even when items=()
for item in "${items[@]:-}"; do
  [[ -n "$item" ]] && printf "  %s\n" "$item"
done
```

The `:-` syntax makes an empty array expand to an empty string rather than triggering the unbound-variable error. The `[[ -n "$item" ]]` guard skips the empty-string iteration.

**Never use `$arr` instead of `${arr[@]}`** — `$arr` is bash shorthand for `${arr[0]}` (first element only). It silently skips every element after the first.

**Counting array length** is always `${#arr[@]}`, never `${#arr}` (which is the string length of element 0):

```bash
total=${#items[@]}
for ((i=0; i<total; i++)); do
  printf "  [%d] %s\n" "$i" "${items[$i]}"
done
```

*Seen in the wild: a multi-select picker that worked when items were pre-populated at startup but crashed on first run (empty catalog) with "unbound variable: EX_NAMES[@]".*

---

## printf, never echo -e

`echo -e` is not portable across shells. On POSIX `/bin/sh` (dash, macOS `sh`), `echo -e` prints the literal `-e` flag instead of interpreting escape sequences. bash's builtin `echo -e` happens to work, but relying on it ties your script to bash and hides portability bugs the moment it's sourced or run under `/bin/sh`. Use `printf` — it behaves identically everywhere.

```bash
# BROKEN on some systems — may print: -e  \033[32mGreen text\033[0m
echo -e "\033[32mGreen text\033[0m"

# Correct — printf interprets \033 consistently on all POSIX systems
printf "\033[32mGreen text\033[0m\n"
```

Use `printf` for all output that includes escape sequences, color codes, or format specifiers. Use `echo ""` only for bare blank lines where no interpolation is needed.

For multi-line static text with no variables, use a here-doc to avoid escaping:

```bash
cat << 'MSG'
  No colors here, just plain text.
  Safe from all escape interpretation.
MSG
```

**Never mix `echo -e` and `printf` in the same script** — the inconsistency is a maintenance trap.

---

## ANSI width: truncate before you color

ANSI escape sequences are invisible bytes that `printf` counts as printable characters when computing column widths. Coloring a string before passing it to a `%-Ns` format specifier will misalign every column to the right of it.

```bash
# BROKEN: columns misalign because ANSI bytes inflate the width count
printf "  %-20s %-12s\n" "${COLOR_SUCCESS}Done${RESET}" "$timestamp"

# Correct: truncate the raw text, THEN wrap in color
name_cell=$(trunc "$name" 20)
printf "  ${COLOR_SUCCESS}%-20s${RESET} %-12s\n" "$name_cell" "$timestamp"
```

The `trunc()` helper operates on raw text only — no color codes inside its input:

```bash
trunc() {
  local str="$1" max="$2"
  if (( ${#str} > max )); then
    printf "%s" "${str:0:$((max-1))}…"
  else
    printf "%-${max}s" "$str"
  fi
}
```

`trunc` pads short strings to exactly `max` characters and truncates long ones, appending `…` (a single terminal-column ellipsis (U+2026, 3 bytes in UTF-8)). `${#str}` counts bytes in bash 3.2 (not Unicode characters), which is correct for plain ASCII input. Non-ASCII field values are measured in bytes and may truncate early — normalize data to ASCII before it reaches `trunc()`.

**Rule:** raw text in, raw text out of `trunc()`. Apply color in the `printf` format string, not in the value being truncated:

```bash
# Pattern: build cell, then color in the format string
label_cell=$(trunc "$label" $W_LABEL)
status_cell=$(trunc "$status" $W_STATUS)
printf "  ${COLOR_TITLE}%-${W_LABEL}s${RESET}  ${COLOR_SUCCESS}%-${W_STATUS}s${RESET}\n" \
  "$label_cell" "$status_cell"
```

---

## CSV / preview safety

Variable data — user input, API responses, file paths — must never be interpolated unquoted. The two failure modes are word-splitting and empty-expansion crashes.

**Word-splitting in preview rows:**

```bash
# BROKEN: if $record contains spaces, printf gets extra positional args
printf "  %-20s\n" $record

# Correct: always double-quote variable expansions
printf "  %-20s\n" "$record"
```

**CSV field quoting** — when building a comma-separated line from an array, quote each field individually:

```bash
fields=("Alice Smith" "alice@example.com" "active")
row=""
for field in "${fields[@]}"; do
  # Escape any embedded commas or double-quotes in the field value
  escaped="${field//\"/\"\"}"
  row+="\"${escaped}\","
done
row="${row%,}"   # strip trailing comma
printf "%s\n" "$row"
```

**Picker crash class — unguarded array index:**

```bash
# BROKEN: crashes when items array is empty (index 0 doesn't exist)
selected=0
printf "  Selected: %s\n" "${items[$selected]}"

# Correct: guard before indexing
selected=0
if [[ ${#items[@]} -gt 0 ]]; then
  printf "  Selected: %s\n" "${items[$selected]}"
fi
```

**Unquoted expansion in conditionals** — under `set -u`, an unset optional variable used unquoted in a test causes a fatal error:

```bash
# BROKEN under set -u if FILTER is unset
if [[ $FILTER == "active" ]]; then ...

# Correct: use parameter expansion default
if [[ "${FILTER:-}" == "active" ]]; then ...
```

Use `"${VAR:-}"` as the default form for optional string variables throughout. The empty-string default makes the intent explicit and keeps `set -u` from firing.

*Seen in the wild: a preview picker that crashed on fields containing commas — the unquoted expansion split the field value into multiple printf arguments, misaligning every column after it.*
