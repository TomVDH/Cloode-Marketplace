# Card anatomy — iteration-shelf

Every card in every shelf follows this exact schema. The two shelf flavours differ in how cards load (eager vs on-demand), but card structure is shared — cards are the unit of review and they read the same everywhere.

---

## 1. Schema

```html
<div class="card" data-file="portal-x.html">
  <div class="head">
    <span class="id">FC · v2 — Three Doors</span>
    <span class="tag star">★ STAR</span>
  </div>

  <!-- Optional: one italic poetic line -->
  <div class="quote">three doors · locked plate champion.</div>

  <!-- Optional: comma-separated technical summary, rendered uppercase -->
  <div class="note">geometric triptych · paper + cobalt · hover invert</div>

  <div class="frame-slot" data-slot>
    <!-- Curated shelf: iframe inlined at generation time -->
    <!-- Monster index: placeholder until loaded, iframe injected on click -->
  </div>

  <div class="foot">
    <a href="portal-x.html" target="_blank" rel="noopener">portal-x.html</a>
    <button class="expand-btn">Expand</button>
    <button class="reload-btn">Reload</button>  <!-- curated only; monster has "Open" instead -->
  </div>
</div>
```

The class attribute is `card` for the monster index and `iter` for the curated shelf (legacy carryover). The children use the same semantic roles but with BEM-ish names in the curated (`iter__head`, `iter__id`, `iter__frame`). Keep this distinction — the templates rely on it for scoping.

---

## 2. Required vs optional

| Element | Curated | Monster | Notes |
|---|---|---|---|
| `.head` | Required | Required | Always carries `id` + `tag` |
| `.head .id` | Required | Required | Display label; shows in sidebar too (monster) |
| `.head .tag` | Required | Required | Falls back to `○` for "no tag" in monster |
| `.quote` | Optional | Optional | Omit the div entirely if no quote |
| `.note` | Optional | Optional | Omit the div entirely if no note |
| `.frame-slot` | Required | Required | Inline iframe (curated) or placeholder (monster) |
| `.foot` | Required | Required | |
| `.foot a` | Required | Required | Opens the iteration in a new tab |
| `.expand-btn` | Required | Required | Keyboard `E` targets the focused card |
| `.reload-btn` | Required | — | Curated cards only |
| `.open-btn` | — | Required | Monster replaces reload with "Open" |

Empty divs are not acceptable — if the value is not supplied in the manifest, remove the element. An empty `.quote` breaks the spacing rhythm.

---

## 3. Tag palette

Tags live in `.head .tag` (or `.iter__tag` in the curated shelf). Every tag slug ships a matching CSS class and a colour token. Introducing a new slug requires adding both.

| Tag slug | Chip colour | Meaning |
|---|---|---|
| `original` | `#777` | Untouched baseline / first version |
| `draft`    | `#8bb6e8` | Work-in-progress iteration |
| `star`     | `#f2f0eb` bold | Max-effort / shortlisted |
| `locked`   | `#d4a017` bold | Decision-locked champion |
| `quarantined` | `#a44` | Preserved on disk but not in play |
| `quiet`    | `#999` | Intentionally stripped variant |
| `og-rich`  | `#c8a34a` | Density-restored iteration |
| `og-true`  | `#e6c34a` | Returns to original DNA |
| `reset`    | `#d4a017` italic | Fresh start within a branch |

**Default** when no tag is specified: `original`.

### CSS for the palette

```css
.tag { font-size: 9px; letter-spacing: 0.14em; text-transform: uppercase; color: #777; }
.tag.star        { color: #f2f0eb; font-weight: 700; letter-spacing: 0.16em; }
.tag.locked      { color: #d4a017; font-weight: 700; letter-spacing: 0.16em; }
.tag.original    { color: #777; }
.tag.draft       { color: #8bb6e8; }
.tag.quarantined { color: #a44; }
.tag.quiet       { color: #999; }
.tag.og-rich     { color: #c8a34a; }
.tag.og-true     { color: #e6c34a; font-weight: 700; }
.tag.reset       { color: #d4a017; font-style: italic; }
```

The curated shelf uses `.iter__tag.{slug}` with the same colour values. Both shelves ship all slugs so that a user can retag a card without touching CSS.

### Glyphs paired with tags

| Tag | Glyph prefix (used in `.tag` text) |
|---|---|
| `star` | `★ STAR` |
| `locked` | `🔒 LOCKED` → replace with `★ LOCKED` (no emoji). Actual rendered text: `★ LOCKED` |
| everything else | uppercase slug, no glyph |

The monster index uses `★ STAR` for star cards and a bare `○` for untagged/"original" cards (the circle signals "card has no assigned status yet").

---

## 4. Card borders and fills

The card is the only surface besides the sidebar that varies its chrome. Two states affect the whole card:

```css
.card { background: #141414; border: 1px solid #222; }
.card.star { border-color: #4a4a4a; }           /* slightly brighter border */
.card.star .head { background: #1a1a1a; }       /* warmer header bar */

.iter.locked {                                  /* curated only */
  border: 1px solid #4a3815;
  box-shadow: 0 0 0 1px #2a2010;
}
.iter.locked .iter__head {
  background: #1a1612;
  border-bottom-color: #4a3815;
}
```

`star` is visual shortlisting. `locked` is a decision — only the curated shelf uses locked as a full-card treatment (because monster cards are reviewed, not decided).

---

## 5. Frame slot behaviour

### Curated (eager)

```html
<iframe class="iter__frame" src="portal-x.html" loading="lazy" title="FC · v2 — Three Doors"></iframe>
```

Inlined at generation time. `loading="lazy"` is a defence-in-depth hint — the curated shelf assumes the browser can handle all iframes at once, but there is no harm in also letting the browser defer off-screen ones.

### Monster (on-demand)

```html
<div class="frame-slot" data-slot>
  <div class="placeholder">
    <b>not loaded</b>
    <span class="note-text">optional short note here</span>
  </div>
</div>
```

The placeholder renders the tiled gradient from `design-tokens.md § 3`. On click (or on a sidebar item click, or on the segment "Load" action), the handler injects the iframe inline. On unload, `iframe.remove()` — never `display:none`.

See `interaction-model.md § 2` for the full lifecycle.

---

## 6. Expanded card

Any card (curated or monster) can be expanded to a fixed-inset overlay. The class is the same: `.card.expanded` on monster, `.iter.expanded` on curated.

```css
.card.expanded {
  position: fixed;
  inset: 1.2rem;         /* 2rem on curated */
  z-index: 120;
  box-shadow: 0 30px 80px rgba(0,0,0,0.9);
}
.card.expanded .frame-slot { aspect-ratio: auto; flex: 1; }

.backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 119; display: none; }
.backdrop.on { display: block; }
```

Only one card expands at a time. The backdrop click and `Esc` both collapse. The monster auto-loads the card (if not already) before expanding — expanding an empty placeholder is never a valid state.

---

## 7. ID conventions

Manifest `id` fields are the user-facing label. Keep them short (≤ 40 chars):

- Prefix · version: `FC · v2`, `HC · v18`
- Prefix · version · qualifier: `FY · v3 (quar.)`, `HC · v19 (OG-rich)`
- Standalone name for sets: `fa-type-wall`, `ea-industrial-archive`

The ID should sort readably in the sidebar. Avoid IDs that begin with the same 10 characters across many items — the sidebar truncates with ellipsis.
