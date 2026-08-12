# Data CLI Patterns

> Patterns for a helper CLI that wraps an external CLI/API: credential resolution,
> configurable output directory, paginated fetch → CSV, and config-driven definitions,
> recipes, and catalogs.

Read `design-language.md` first. See `python-helpers.md` for JSON parsing helpers
used in the fetch loop.

---

## Auth tiers & credential resolution

Three credential tiers in priority order: the vendor CLI's stored config, a token
file on disk, then failure. Resolve once at startup, then validate against the live
service before doing any work.

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

**`validate_token`** probes the cheapest read endpoint the service exposes — one
`curl`, short timeout, check for HTTP 200. This confirms the token is accepted, not
just present. A downstream 403 on a specific call is still possible (scope issue,
not auth issue); the probe is not the right place to catch that.

```bash
validate_token() {
  local token="$1" code
  code=$(curl -sS -o /dev/null -m 5 -w "%{http_code}" \
    -H "Authorization: Bearer ${token}" \
    "${SERVICE_PROBE_URL}" 2>/dev/null) || code="000"
  [[ "$code" == "200" ]]
}
```

Set `SERVICE_PROBE_URL` to whichever read endpoint the service documents as
requiring the minimum scope — typically an "account info" or "ping" endpoint.

**File shape check** (optional but catches obvious mistakes early):

```bash
# Reject tokens that don't pass a basic shape check before hitting the network.
if [[ ! "$TOKEN" =~ ^[A-Za-z0-9_-]{20,}$ ]]; then
  die "Token in $TOKEN_FILE looks malformed — check for whitespace or truncation."
fi
```

**Auth failure UI:** print a concrete fix list, not just an error string.

```bash
printf "\n  ${COLOR_ERROR}✗  Auth failed.${RESET}\n\n"
printf "  ${BOLD}Reason:${RESET}  %s\n\n" "$1"
printf "  ${BOLD}Fix:${RESET}\n"
printf "    1. Run ${BOLD}%s auth${RESET} and follow the prompts\n" "$VENDOR_CLI"
printf "    2. Or paste a token into ${BOLD}%s${RESET}\n\n" "$TOKEN_FILE"
```

**When `CLI_OK=false`:** the token came from the file, not the vendor CLI. Note
this in the failure UI so the operator knows which path was used.

*Seen in the wild: a nightly export tool that silently used a stale token file for
weeks after the vendor CLI had refreshed its own config; the two-tier probe stopped
the silent failures.*

---

## Output directory resolution

Resolve the output directory in precedence order: env var override → credentials
file → built-in default. Never hard-code a path.

```bash
OUT_DIR="${OUT_DIR:-$(cat "$CRED_DIR/out-dir" 2>/dev/null || echo "$HOME/Desktop")}"
```

The `$CRED_DIR/out-dir` file holds a single line — a directory path the operator
pasted in once. `cat … 2>/dev/null` silences the error when the file is absent and
falls through to the default.

**Full resolver pattern:**

```bash
CRED_DIR="${CRED_DIR:-$HOME/.config/${TOOL_NAME}}"
OUT_DIR="${OUT_DIR:-$(cat "$CRED_DIR/out-dir" 2>/dev/null || echo "$HOME/Desktop")}"
OUT_DIR="${OUT_DIR%/}"          # strip trailing slash
mkdir -p "$OUT_DIR" || die "Cannot create output directory: $OUT_DIR"
```

**Strip the trailing slash** so downstream path joins (`"$OUT_DIR/$filename"`) are
consistent regardless of how the operator typed the path.

**Confirm before a large write:**

```bash
printf "  ${COLOR_MUTED}Output:${RESET} %s\n" "$OUT_DIR"
```

Show the resolved path in the summary screen (see `interaction.md` → *Dry-run as a UX surface*)
so the operator can verify before confirming.

**Persist a preferred directory:**

```bash
save_out_dir() {
  mkdir -p "$CRED_DIR"
  printf '%s\n' "$1" > "$CRED_DIR/out-dir"
  printf "  ${COLOR_SUCCESS}✓${RESET} Saved output directory: %s\n" "$1"
}
```

Call this when the operator explicitly changes the output path through the TUI.

---

## Paginated fetch → CSV (Ctrl+C-safe)

Loop pages until the service returns no cursor. Write to a temp file; `mv` into
place only on success so an interrupt never leaves a half-written CSV.

```bash
fetch_to_csv() {
  local object_type="$1" props_csv="$2" outfile="$3"

  local tmpfile; tmpfile="$(mktemp "${outfile}.tmp.XXXXXX")"
  trap 'rm -f "$tmpfile"' EXIT

  # Write header
  local header_line="id,${props_csv}"
  printf '%s\n' "$header_line" > "$tmpfile"

  local after="" page=1 count=0 batch

  # Ctrl+C leaves a partial tmpfile (cleaned by trap) — never touches outfile.
  trap 'printf "\n  ${COLOR_WARN}⚠  Fetch stopped at page %d (%d records). No output written.\n${RESET}" \
        "$page" "$count" >&2; exit 0' INT TERM

  while true; do
    local url="${SERVICE_BASE_URL}/objects/${object_type}?limit=100&properties=${props_csv}"
    [[ -n "$after" ]] && url="${url}&after=${after}"

    local full_response http_code response
    full_response=$(curl -s -w "\n%{http_code}" \
      -H "Authorization: Bearer ${TOKEN}" "$url")
    http_code=$(printf '%s' "$full_response" | tail -1)
    response=$(printf '%s' "$full_response" | sed '$d')

    if [[ "$http_code" != "200" ]]; then
      if [[ "$http_code" == "429" ]]; then
        printf "  ${COLOR_WARN}⚠  Rate limited — waiting 10s${RESET}\n" >&2
        sleep 10; continue
      fi
      printf "  ${COLOR_ERROR}✗  HTTP %s on page %d — aborting.${RESET}\n" "$http_code" "$page" >&2
      rm -f "$tmpfile"; exit 1
    fi

    # Parse rows and append to tmpfile (python3 — see python-helpers.md)
    printf '%s' "$response" | python3 -c "
import json, sys
data = json.load(sys.stdin)
fields = '${props_csv}'.split(',')
for r in data.get('results', []):
    p = r.get('properties', {})
    vals = [str(r.get('id', ''))]
    for f in fields:
        v = str(p.get(f) or '').replace('\"', '\"\"')
        if ',' in v or '\"' in v or '\n' in v:
            v = '\"' + v + '\"'
        vals.append(v)
    print(','.join(vals))
" >> "$tmpfile"

    batch=$(printf '%s' "$response" | python3 -c \
      "import json,sys;print(len(json.load(sys.stdin).get('results',[])))")
    count=$((count + batch))
    printf "\r  ${COLOR_INFO}ℹ  Page %d — %d records${RESET}" "$page" "$count" >&2

    # Next-page cursor
    after=$(printf '%s' "$response" | python3 -c "
import json, sys
print(json.load(sys.stdin).get('paging', {}).get('next', {}).get('after', ''))
" 2>/dev/null)
    [[ -z "$after" ]] && break

    page=$((page + 1))
    sleep 0.1    # brief pause — stay within rate limits
  done

  # Atomic: move tmpfile into final destination only on full success
  mv "$tmpfile" "$outfile"
  printf "\r\033[K  ${COLOR_SUCCESS}✓  %d records → %s${RESET}\n" "$count" "$outfile" >&2
}
```

**Key safety properties:**

| Property | Mechanism |
|---|---|
| Ctrl+C never corrupts output | `mv` happens only after the loop exits cleanly |
| Interrupt cleans up temp file | `trap 'rm -f "$tmpfile"' EXIT` |
| Rate-limit recovery | Retry on 429 after `sleep 10` |
| Hard abort on other errors | `rm -f "$tmpfile"; exit 1` |

**Why this is interrupt-safe:** the real CSV path is only ever written by the final `mv`, which sits *after* the loop. A Ctrl-C runs the INT handler, which calls `exit 0` *before* control can reach the `mv` — so the destination file is never half-written. The `EXIT` trap then removes the temp file. The invariant is "the `mv` is the last thing that runs on the success path, and every interrupt path exits before it." If you adapt this function, keep `mv` last and keep the interrupt handlers exiting before it.

**Cursor pagination:** the service's `paging.next.after` field holds the opaque
cursor for the next page. When absent (last page), the loop exits. Services that
use `offset` or `page` integers instead follow the same shape — replace the
`paging.next.after` extraction with whichever field the API returns.

**Progress line:** `\r` + count overwrites the same terminal line each page.
Use `\r\033[K` on the final line to clear the spinner before printing the summary.

**Dry-run stub:** wrap `fetch_to_csv` in the dry-run stub layer (`operations.md`)
so `--dry` shows what would be fetched without writing anything.

```bash
if $DRY_RUN; then
  fetch_to_csv() {
    local object_type="$1" props_csv="$2" outfile="$3"
    local field_count; field_count=$(printf '%s' "$props_csv" | awk -F',' '{print NF}')
    printf "  ${COLOR_WARN}●  DRY — would fetch %s  (%d fields → %s)\n${RESET}" \
      "$object_type" "$field_count" "$outfile"
  }
fi
```

---

## Config-driven definitions & recipes

### Catalog format

A definition file declares the full set of available fields for an object type.
The `CATALOG` array holds one entry per row:

- **Value row:** `"value|Label"` — the API field name and its human-readable label.
- **Category header:** `"HEADER|Category Name"` — a separator that groups the rows
  below it. The full-control picker (`interaction.md` → *Full-control catalog picker*)
  renders headers as `── Category Name ──` and toggles the whole group on Space/Enter.

```bash
# Example definition file: records.def.sh
OBJECT_TYPE="records"
DISPLAY_NAME="Records"

CATALOG=(
  "HEADER|Identity"
  "name|Full Name"
  "email|Email Address"
  "phone|Phone Number"

  "HEADER|Location"
  "city|City"
  "state|State / Region"
  "country|Country"

  "HEADER|Status"
  "lifecycle_stage|Lifecycle Stage"
  "owner_id|Record Owner"
  "create_date|Created Date"
)

# Pre-selected fields — comma-wrapped, must match CATALOG value entries exactly.
DEFAULTS=",name,email,phone,city,country,lifecycle_stage,"
```

**Parse:** call `parse_catalog` (defined in `interaction.md`) immediately after
sourcing the definition file. It populates `NAMES`, `LABELS`, `IS_HEADER`, and `ON`
from the `CATALOG` array and pre-selects entries whose values appear in `DEFAULTS`.

**The `DEFAULTS` convention:** comma-wrapped (`",val1,val2,"`) so a simple
`[[ "$DEFAULTS" == *",$name,"* ]]` test handles edge cases where one value name
is a prefix of another.

**Loading a definition at runtime:**

```bash
load_definition() {
  local object="$1"
  local def_file="${DATA_DIR}/${object}.def.sh"
  if [[ -f "$def_file" ]]; then
    # shellcheck source=/dev/null
    source "$def_file"
    HAS_DEFINITION=true
    return 0
  fi
  HAS_DEFINITION=false
  return 1
}
```

Fall back to a generic property list when no definition file exists for the
requested object type.

---

### Recipes

A recipe is a named, saved set of export parameters: object type, selected columns,
filters, output path. Save once, replay by name.

**Recipe file format** (one JSON file per recipe, stored in `$DATA_DIR/recipes/`):

```json
{
  "name": "weekly-active",
  "object": "records",
  "columns": ["name", "email", "lifecycle_stage", "owner_id", "create_date"],
  "filters": {
    "stage": "customer",
    "since": "2025-01-01",
    "limit": null
  },
  "format": "csv",
  "output": "~/Desktop/exports/weekly-active.csv"
}
```

**Save a recipe:**

```bash
recipe_save() {
  local name="$1" object="$2" cols_csv="$3" stage="$4" since="$5" limit="$6" outfile="$7"
  local dir="${DATA_DIR}/recipes"; mkdir -p "$dir"
  local file="${dir}/${name}.json"
  NAME="$name" OBJ="$object" COLS="$cols_csv" STAGE="$stage" \
  SINCE="$since" LIMIT="$limit" OUTFILE="$outfile" \
  python3 -c "
import json, os
cols = [c for c in os.environ['COLS'].split(',') if c]
r = {
  'name':    os.environ['NAME'],
  'object':  os.environ['OBJ'],
  'columns': cols,
  'filters': {
    'stage':  os.environ['STAGE']  or None,
    'since':  os.environ['SINCE']  or None,
    'limit':  int(os.environ['LIMIT']) if os.environ['LIMIT'] else None,
  },
  'format':  'csv',
  'output':  os.environ['OUTFILE'],
}
open('${file}', 'w').write(json.dumps(r, indent=2) + '\n')
"
  printf "  ${COLOR_SUCCESS}✓  Saved recipe: %s${RESET}\n" "$name"
}
```

**List recipes** (tab-delimited for display):

```bash
recipe_list() {
  local dir="${DATA_DIR}/recipes"
  local f
  for f in "$dir"/*.json; do
    [[ -e "$f" ]] || { printf "  ${COLOR_MUTED}No saved recipes.${RESET}\n"; return; }
    python3 -c "
import json
r = json.load(open('$f'))
print('\t'.join([
  r['name'],
  r['object'],
  str(len(r['columns'])) + ' cols',
  str(r['filters'].get('stage') or 'all'),
]))
"
  done
}
```

**Load and validate a recipe:**

```bash
recipe_load() {
  local name="$1"
  local file="${DATA_DIR}/recipes/${name}.json"
  if [[ ! -f "$file" ]]; then
    printf "  ${COLOR_ERROR}✗  Recipe '%s' not found.${RESET}\n" "$name" >&2
    printf "  Available: %s\n" "$(recipe_list | cut -f1 | tr '\n' ' ')" >&2
    return 1
  fi
  local parsed
  parsed=$(python3 -c "
import json, sys
try:
    r = json.load(open('$file'))
except Exception as e:
    print('ERR ' + str(e)); sys.exit(0)
for k in ('name', 'object', 'columns'):
    if not r.get(k): print('ERR missing field: ' + k); sys.exit(0)
if not isinstance(r['columns'], list) or not r['columns']:
    print('ERR columns must be a non-empty list'); sys.exit(0)
f = r.get('filters', {})
print('OK')
print(r['object'])
print(','.join(r['columns']))
print(f.get('stage') or '')
print(f.get('since') or '')
print(str(f.get('limit') or ''))
print(r.get('output', ''))
")
  if [[ "$(printf '%s' "$parsed" | head -1)" != "OK" ]]; then
    printf "  ${COLOR_ERROR}✗  %s${RESET}\n" "$(printf '%s' "$parsed" | head -1 | sed 's/^ERR //')" >&2
    return 1
  fi
  R_OBJECT=$(printf '%s' "$parsed" | sed -n '2p')
  R_COLS=$(printf  '%s' "$parsed" | sed -n '3p')
  R_STAGE=$(printf '%s' "$parsed" | sed -n '4p')
  R_SINCE=$(printf '%s' "$parsed" | sed -n '5p')
  R_LIMIT=$(printf '%s' "$parsed" | sed -n '6p')
  R_OUTPUT=$(printf '%s' "$parsed" | sed -n '7p')
  return 0
}
```

**Run a recipe by name:**

```bash
run() {
  local name="$1"
  recipe_load "$name" || return 1
  load_definition "$R_OBJECT"
  # Apply loaded columns as DEFAULTS override, then fetch
  DEFAULTS=",$R_COLS,"
  fetch_to_csv "$R_OBJECT" "$R_COLS" "${R_OUTPUT:-$OUT_DIR/${name}.csv}"
}
```

Call as `run weekly-active`. The TUI menu can list saved recipes and call `run
<name>` on selection — no re-entering of parameters required.

**Recipe names must be shell-and-Python-safe** (alphanumerics, dashes, underscores — no single quotes or path separators). They become filenames and are interpolated into a `python3 -c` literal; a stray quote breaks the parse. Validate names on save, or use the env-var passing pattern (as `recipe_save` does for its data) if you must accept arbitrary names.

**Catalog ↔ picker contract:** the catalog format defined above (`value|Label` rows
and `HEADER|Category Name` separators) is the exact format consumed by
`parse_catalog` in `interaction.md`. A definition file's `CATALOG` array feeds
directly into the full-control catalog picker without transformation.
