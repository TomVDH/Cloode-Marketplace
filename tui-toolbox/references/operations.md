# Operations Reference

> These are the operational floor — an agent building any tool that writes, uploads, or mutates state applies them by default.

Read `design-language.md` first for the visual grammar. This file covers what happens *at runtime* when a tool changes state: how to run safely with concurrent invocations, how to stay idempotent across retries, and how to leave a paper trail.

---

## Dry-run stub layer

Any tool that mutates remote or local state must support a `--dry` flag. When dry mode is active, redefine the *mutating* helpers as no-ops that log what they would have done and return a plausible fake id. Leave read-only helpers live — they are safe to call for real, and their output keeps the dry trace realistic (the preview shows real data, not fabricated placeholders).

```bash
# When DRY_RUN=true, redefine the MUTATING helpers to log + return a plausible
# fake id; leave read-only helpers live so the dry trace stays realistic.
if $DRY_RUN; then
  remote_create() { log "DRY would create: $*"; printf 'fake-%s' "$RANDOM"; }
  remote_delete() { log "DRY would delete: $*"; }
  remote_upload() { log "DRY would upload: $*"; printf 'fake-file-%s' "$RANDOM"; }
  # remote_list / remote_get stay live — read-only, safe to run for real
fi
```

Define all mutating helpers before this block so the redefinitions take effect before any are called. The names `remote_create`, `remote_delete`, `remote_upload` are placeholders — name them after the actual operations (e.g. `record_create`, `file_upload`, `row_delete`).

**Every state-mutating helper must appear in this block.** A mutating helper added later but not stubbed here will execute for real while `--dry` is active — there is no safety net. Re-audit this block whenever you add a new write/upload/delete operation.

**When to apply:** every tool whose `--dry` trace should be safe to run in production without side effects. Wire up after flag parsing, before the main work loop.

`interaction.md` → *Dry-run as a UX surface* describes the user-facing output for this mode. The stub layer here is the mechanism that makes that output safe.

---

## PID single-instance lock

Tools that upload, sync, or modify shared state are dangerous when two instances run concurrently — duplicate writes, race conditions on shared files, or split manifest entries. Use a portable PID lock (macOS ships bash 3.2 without `flock`; this pattern is portable and requires no external dependencies).

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

The `kill -0` probe checks liveness without sending a signal — it succeeds only if the process with that PID is running *and* owned by the same user. A stale lock (file present, PID gone) is silently reclaimed; the comment makes this explicit so reviewers do not mistake it for a bug.

**This lock is cooperative, not atomic.** The `[[ -f "$LOCK" ]]` check and the `printf … > "$LOCK"` write are two steps, not one — two processes that probe at the same instant can both find no lock and both proceed, the second write simply winning. For tools where a simultaneous race is genuinely dangerous, layer in an atomic primitive (`mkdir "$LOCK.d"` succeeds for exactly one racer, or `flock` where available). For most upload/sync tools the cooperative lock is enough: the race window is tiny and the worst case is a second instance running, not corrupted state.

`trap … EXIT INT TERM` releases the lock on normal exit and on Ctrl-C/termination, but **SIGKILL cannot be trapped** — if the process is killed hard, the lock file survives and is reclaimed as a stale lock (PID no longer alive) on the next run. That stale-lock reclaim is the crash-recovery path.

**When to apply:** any tool that touches a shared resource — a remote API, a shared directory, a manifest file — where a second concurrent run would corrupt state or waste rate-limit budget. Place after the `LOG_DIR` setup and before the main work begins.

*Seen in the wild: a file-manager upload tool rejected a second terminal window mid-run, rather than letting both instances race and produce duplicate remote folders.*

---

## Manifest idempotency

Expensive operations — uploads, API writes, file conversions — should be skippable on re-run. A manifest file records each completed item by a stable key (path, id, checksum). On re-run, already-done items are skipped unless `--force` is passed.

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

`grep -qxF` matches the exact full line (`-x`) and treats the search string as a literal (`-F`), so keys containing regex metacharacters (slashes, dots, brackets) are safe. The `2>/dev/null` makes the check succeed silently when the manifest does not yet exist.

**Key choice:** use the item's stable identity, not a generated id. A remote path, a local file path relative to the project root, or a content hash are all good keys. A random id from a previous run is not — it changes on re-upload and defeats idempotency.

**`--force`:** always expose a `--force` flag that bypasses `already_done()` for the item being processed (but does not delete the manifest). This lets an operator re-process one failed item without blowing away the record of everything else.

**The manifest is local-only.** It records what *this* working copy did on *this* machine. It knows nothing about operations performed from another machine, a CI run, a teammate's copy, or changes made directly in the remote service's UI. If external state has diverged, the manifest will still report those items as done — use `--force` (or delete the manifest) to force a full re-run when you know the remote has changed underneath you.

**When to apply:** any tool that processes a list of items where each item's work is expensive or has remote side effects. Wire up after `acquire_lock`, before the loop.

---

## Logging to .logs/

Every run should leave a timestamped log in `.logs/` alongside the lock and manifest. The log captures the full machine-readable record of what happened, independent of terminal color state.

```bash
LOG_DIR="${LOG_DIR:-.logs}"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/${TOOL_NAME}.log"

log() {
  local ts; ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '%s  %s\n' "$ts" "$1" >> "$LOG_FILE"
}

info() {
  log "$1"
  printf "  ${COLOR_INFO}ℹ${RESET} %s\n" "$1"
}
```

`log()` writes only to the file — use it for internal bookkeeping lines that would be noise on the terminal. `info()` writes to both — use it for lines the operator should see and that should also appear in the log.

Use a single `LOG_FILE` path per run rather than per-invocation timestamps. Appending to a stable path means `tail -f .logs/tool-name.log` works across re-runs during development. For audit trails where runs must not intermingle, append a datestamp: `${LOG_DIR}/${TOOL_NAME}-$(date +%Y%m%d-%H%M%S).log`.

**`die()`** should log before exiting:

```bash
die() {
  log "FATAL: $*"
  printf "  ${COLOR_ERROR}✗${RESET} %s\n" "$*" >&2
  exit 1
}
```

**When to apply:** always. Every tool that runs unattended (cron, CI, multi-step wizard) needs a file log. Even interactive tools benefit — the log is the first thing reached for when a user reports unexpected behavior.

---

## Smoke tests

A smoke test is a script in `_examples/<tool-name>-smoke.sh` that exercises the real tool with `--dry` and asserts the expected behavior. It must be strictly read-only: it should be safe to run against any environment, including production, without mutating state.

### Pattern

```bash
#!/usr/bin/env bash
# _examples/upload-smoke.sh — smoke test for the upload tool (read-only, always --dry)
set -euo pipefail

TOOL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/upload.sh"

run() {
  local label="$1"; shift
  local out; out=$(bash "$TOOL" "$@" 2>&1)
  local exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    printf "  FAIL [%s] — exited %d\n" "$label" "$exit_code"
    printf "%s\n" "$out"
    exit 1
  fi
  printf "  OK   [%s]\n" "$label"
}

assert_contains() {
  local label="$1" needle="$2"
  local out; out=$(bash "$TOOL" --dry 2>&1)
  if ! printf '%s' "$out" | grep -qF "$needle"; then
    printf "  FAIL [%s] — expected output to contain: %s\n" "$label" "$needle"
    printf "%s\n" "$out"
    exit 1
  fi
  printf "  OK   [%s]\n" "$label"
}

printf "\nSmoke: upload.sh\n"
run         "exits 0 with --dry"            --dry
assert_contains "dry prefix present"        "DRY would"
assert_contains "no mutations in dry trace" "DRY would upload"

printf "\nAll smoke checks passed.\n"
```

### Keeping smoke tests read-only

- Always pass `--dry` (or the tool's equivalent no-op flag). Never call the tool without it.
- Do not create, modify, or delete files outside a temp directory.
- Do not write to shared manifests or lock files — the tool under test should handle its own locking; the test merely invokes it.
- Assert on stdout/stderr content with `grep -qF` (fixed string, no regex footguns).
- Assert on exit code, not on exact output lines — output wording changes; exit codes are a contract.
- The `assert_contains` helper invokes the tool independently on each call, so a smoke run may launch the tool several times — this is fine because every invocation passes `--dry` and is read-only.

**When to apply:** every tool in the kit should have a smoke test before it is considered complete. The smoke test is the minimum viable verification that the dry-run stub layer is wired up correctly and the tool exits cleanly. Run it before committing changes to the tool.
