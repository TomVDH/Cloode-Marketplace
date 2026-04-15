# Design tokens — iteration-shelf

The visual DNA of the shelf chrome. These values are **non-negotiable**. The templates bake them in; do not edit them away when parameterising.

The aesthetic is a terminal reviewer, not a portfolio. Every colour, typeface and spacing decision below exists to reinforce that. If your output starts looking like a landing page, you have drifted.

---

## 1. CSS custom properties

Paste this token block verbatim into the `:root` of every generated shelf:

```css
:root {
  --bg:        #0a0a0a;   /* page ground */
  --panel:     #0c0c0c;   /* sidebar, secondary surfaces */
  --card:      #141414;   /* card body */
  --card-star: #1a1a1a;   /* star-flagged card */
  --rule:      #222;      /* hairlines */
  --rule-soft: #1e1e1e;   /* sidebar borders */

  --ink:       #aaa;      /* body text */
  --ink-hi:    #ccc;      /* emphasised text */
  --ink-top:   #fff;      /* hover-revealed text */
  --ink-dim:   #555;      /* captions */
  --ink-mute:  #777;      /* tertiary */

  --accent:       #e6c34a; /* section headers, h1 */
  --accent-hot:   #d4a017; /* locked state, active */
  --accent-load:  #8fc98f; /* loaded-state green */
  --accent-warn:  #e88;    /* danger / unload */
  --accent-link:  #7ab;    /* interactive links */
  --accent-link-hi:#adf;

  --font-mono: 'SF Mono','Cascadia Mono','Consolas',monospace;
}
```

The reference templates inline these directly in selectors (for compactness) rather than via `var(--*)`. Either pattern is fine — the **values** must match exactly. Do not round, re-hex, or substitute "similar" colours. #e6c34a is #e6c34a.

---

## 2. Typography

| Role | Rule |
|---|---|
| Font family | `'SF Mono','Cascadia Mono','Consolas',monospace` — always. |
| Body size | `12.5px / 1.5` |
| Headers | `font: 700 14px/1.4 inherit` — i.e. keep mono, only weight + size change |
| Captions | `10–11px`, `--ink-dim` |
| All-caps labels | `letter-spacing: 0.1–0.2em`, `text-transform: uppercase` |
| Italics | Rare; reserved for **one-line poetic quotes** inside cards, lowercase, `--ink-mute`, never used for emphasis |

Never introduce variable-width fonts. Never introduce italic *for emphasis* — the single use-case is the card quote line.

Weight scale is binary: `400` (body) and `700` (labels/headers). Do not use `500`, `600`, or any weight between.

---

## 3. Decorative patterns

### Not-loaded placeholder (monster index only)

```css
.frame-slot {
  background: repeating-linear-gradient(45deg, #0e0e0e 0 10px, #0a0a0a 10px 20px);
}
.frame-slot:not(.loaded):hover {
  background: repeating-linear-gradient(45deg, #121212 0 10px, #0e0e0e 10px 20px);
}
```

Dashed 45° stripe with a one-step-brighter hover state. This is the only "texture" the shelf ever shows. No noise, no grain, no images.

### Loaded-state glow

```css
.frame-slot.loaded { /* iframe is visible; no decoration change beyond that */ }
.sb-item.loaded     { color: var(--accent-load); }
.sb-item.loaded::before { content: "●"; color: #5a7a5a; }
```

Green dot in the sidebar (`●`, not a custom icon), green-tinged text. Segment counter reads `3/19` when partially loaded. Never use a progress bar — the counter is the progress indicator.

### Star / locked emphasis

```css
.card.star { border-color: #4a4a4a; }
.card.star .head { background: var(--card-star); }
.tag.star { color: #f2f0eb; font-weight: 700; letter-spacing: 0.16em; }

.iter.locked { border: 1px solid #4a3815; box-shadow: 0 0 0 1px #2a2010; }
.iter.locked .iter__head { background: #1a1612; border-bottom-color: #4a3815; }
.iter__tag.locked { color: var(--accent-hot); font-weight: 700; letter-spacing: 0.16em; }
```

Orange star (`★`) for locked plates, slightly warmer card surface for both starred and locked cards. This is the only outline glow the shelf ever shows (and even then it's flat, not blurred).

---

## 4. Anti-slop rules

These are the defaults to **actively resist**. Every one of them is a landing-page tic. The shelf is not a landing page.

| Default to resist | What to do instead |
|---|---|
| Purple / blue AI gradients | Solid flat colour. Token values only. |
| Rounded corners > 4px | Zero radius. `border-radius: 2px` maximum, reserved for segment-group pills. |
| `box-shadow` beyond the expand backdrop | One shadow: `0 30px 80px rgba(0,0,0,0.9)` on the expanded card, nowhere else. |
| Soft borders (`rgba(…, 0.1)`) | Hairlines only. `#222`, `#2a2a2a`, or `#1e1e1e`. |
| Emoji for status | ASCII glyphs: `·`, `●`, `○`, `★`, `→`. No 🚀 / 🎨 / ✨ / anything from a Slack integration. |
| Custom icons | System glyphs and the `kbd` element. No SVG icons in the chrome. |
| Animated loaders | A static "click to load" label. If you need feedback, change the colour — do not spin. |
| Drop-shadow on text | Text never has shadow. |
| Background images | None. Token colours only. Placeholder is the striped gradient; otherwise solid. |
| Tailwind-style utility soup | Scoped class names: `.card`, `.head`, `.tag`, `.sb-item`, `.seg-h`. Don't litter the HTML with `px-4 py-2 bg-neutral-900`. |

---

## 5. Spacing scale

| Context | Value |
|---|---|
| Page padding | `1.4rem` (main area), `1.2rem 0.9rem` (sidebar) |
| Card internal pad | `0.45rem 0.7rem` (head, foot), `0.4rem 0.9rem` (quote/note) |
| Grid gap | `0.9rem` (monster), `1.2rem` (curated) |
| Segment top margin | `1.6rem` |
| Segment header bottom | `0.7rem` |

Do not invent in-between values. If the template uses `0.35rem`, keep it at `0.35rem` — do not "improve it" to `0.5rem`.

---

## 6. Accessibility constants

- Focus ring: browser default, sufficient against `#0a0a0a`. Do not strip it.
- `aria-label` required on: sidebar `<nav>`, segment `<nav>`, global controls group, column switcher.
- `prefers-reduced-motion`:
  - Drop `behavior: 'smooth'` on `scrollIntoView` calls
  - Drop card expand transitions
  - No other motion is ambient, so nothing else to disable
- Breakpoints:
  - `max-width: 900px` — sidebar collapses to top row, grid to 1 column
  - `max-width: 680px` — force 1 column regardless of column switcher state
  - `max-width: 1100px` — default auto-fit behaviour if `data-cols` not set (monster)

The shelf is keyboard-navigable end-to-end. Every button is tab-able and has a visible focus ring at default styling.
