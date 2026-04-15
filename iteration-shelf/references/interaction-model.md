# Interaction model — iteration-shelf

How the two shelves behave. The curated shelf is simple — cards are loaded and ready; you just look. The monster index is a resource management problem masquerading as a review UI, and its interaction model is where that problem is solved.

---

## 1. Curated shelf (`_iterations.html`)

**Loading:** Every iframe loads on page open. The user's browser is presumed capable of ~20 iframes at once. If the count is higher, the skill should emit the monster instead (or both).

**Controls per card:**

| Button | Effect |
|---|---|
| `Expand` | Card enters fixed-inset overlay, backdrop on. |
| `Reload` | iframe `src` cache-busts with `?r=${Date.now()}`. |
| `<a>` link | Opens the raw iteration in a new tab. |

**Global keyboard:**

| Key | Effect |
|---|---|
| `R` | Reload all loaded iframes (cache-busted). |
| `E` | Expand the focused card. |
| `Esc` | Collapse the expanded card. |

Skip keyboard handling when `e.target.tagName in ['INPUT', 'TEXTAREA']`.

---

## 2. Monster index (`_monster-index.html`)

Iframes never auto-load. Every load is deliberate, and every load is reversible.

### 2.1 Per-card

| Action | Effect |
|---|---|
| Click the placeholder | Load just that card. |
| Shift-click a loaded placeholder | Unload that card. |
| Click `Expand` | Auto-load if needed, then enter overlay. |
| Click `Open` | New tab to the raw iteration. |

### 2.2 Per-segment

Each segment header has one button that toggles between three states based on **actual loaded count in the segment** (not on how loading was triggered):

| State | Condition | Label | Class |
|---|---|---|---|
| idle | 0 loaded | `Load segment (N)` | _(none)_ |
| partial | 1 .. N-1 loaded | `Unload segment (k/N)` | `loaded partial` |
| full | all N loaded | `Unload segment (N)` | `loaded` |

Partial is ochre-accented (`--accent-hot`). Full is green-accented (`--accent-load`). Clicking in any non-idle state unloads the whole segment — that's how you reset a mixed-load.

The re-sync function is `syncSideSeg(segId)` and it runs every time a single card loads or unloads. The segment button never falls out of step with reality.

### 2.3 Sidebar outliner

Sticky left column, 240px wide. Collapses to a top row at `max-width: 900px`.

| Element | Click | Shift-click |
|---|---|---|
| Segment header (`.sb-t`) | Expand / collapse the item list | Jump to the segment + bulk-load it |
| Segment item (`.sb-item`) | Scroll the card into view + load it | Unload that card |

**Visual cues:**

- Item loaded → text goes green, `●` bullet replaces `·`
- Item starred → `★` bullet replaces `·`
- Segment header loaded → text goes green
- Segment header active (in viewport) → ochre background, ochre text

Active segment is driven by an `IntersectionObserver`:

```js
const spyOb = new IntersectionObserver((entries) => {
  entries.forEach(en => {
    if (!en.isIntersecting) return;
    const segId = en.target.id.replace('seg-', '');
    document.querySelectorAll('.sb-t').forEach(t =>
      t.classList.toggle('active', t.dataset.segToggle === segId)
    );
  });
}, { rootMargin: '-40% 0px -55% 0px' });
document.querySelectorAll('.seg').forEach(s => spyOb.observe(s));
```

Do not tweak the `rootMargin` — it's tuned for ~1920px tall viewports and still works on ~800px because the observer fires on any partial intersection within the band.

### 2.4 Global controls

Top bar, always visible:

- **Loaded counter** — reads `Currently loaded: N / T`. Turns red (`.hot` class, `--accent-warn`) when `N > 25`.
- **Column switcher** — `1×` / `2×` / `3×` pill group. Sets `--cols` on `<body>`, persists to `localStorage['iteration-shelf:cols']`. Keyboard `1` / `2` / `3` match the buttons. Mobile (`max-width: 680px`) forces 1 column regardless. **Default on first load: 3×.**
- **Unload all** (`.danger` button) — wipes every iframe.
- **Reload loaded** — cache-busts every live iframe without unloading.

### 2.5 Warn-gate

Before bulk-loading a segment when `loadedCount > 20`:

```js
if (loadedCount > 20) {
  if (!confirm(`${loadedCount} portals already loaded. Load more? (may stall the browser)`)) return;
}
```

The threshold is literal 20, not a computed function of available memory — deterministic behaviour matters more than precision.

### 2.6 Keyboard

| Key | Effect |
|---|---|
| `1` / `2` / `3` | Column switcher |
| `R` | Reload all loaded |
| `E` | Expand focused card (auto-loads if needed) |
| `U` | Unload all |
| `Esc` | Collapse expanded |

Skip when `e.target.tagName in ['INPUT', 'TEXTAREA']`.

---

## 3. Column switcher — CSS and JS

Both shelves expose the switcher (optional for curated; standard for monster). The implementation:

```css
.grid {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(var(--cols, 3), 1fr);
}
@media (max-width: 680px) {
  .grid { grid-template-columns: 1fr !important; }
}

.cols { display: inline-flex; border: 1px solid #333; overflow: hidden; }
.cols button {
  background: #121212; color: #888;
  padding: 0.3rem 0.7rem;
  border: 0; border-left: 1px solid #2a2a2a;
  cursor: pointer;
}
.cols button:first-child { border-left: 0; }
.cols button.on { background: #1a1612; color: #d4a017; border-color: #3a2f12; }
```

```js
const COLS_KEY = 'iteration-shelf:cols';
function setCols(n) {
  document.body.style.setProperty('--cols', n);
  document.body.dataset.cols = n;
  document.querySelectorAll('.cols button').forEach(b =>
    b.classList.toggle('on', b.dataset.cols === String(n))
  );
  try { localStorage.setItem(COLS_KEY, String(n)); } catch (e) {}
}
document.querySelectorAll('.cols button').forEach(b => {
  b.addEventListener('click', () => setCols(parseInt(b.dataset.cols, 10)));
});
(function () {
  let saved = 3;
  try { const v = localStorage.getItem(COLS_KEY); if (v) saved = parseInt(v, 10); } catch (e) {}
  setCols(saved);
})();
```

The `try/catch` around `localStorage` guards against file:// origin quirks — when the user opens the shelf directly from disk without a server, some browsers throw on access. The fallback is silent.

---

## 4. Expand / collapse

Shared across both shelves, with slightly different class names.

```js
function collapseAll() {
  document.querySelectorAll('.card.expanded, .iter.expanded').forEach(c => c.classList.remove('expanded'));
  document.querySelectorAll('.backdrop, .expand-backdrop').forEach(b => b.classList.remove('on'));
  document.body.style.overflow = '';
}

document.addEventListener('click', e => {
  const btn = e.target.closest('.expand-btn, .expand');
  if (!btn) return;
  const card = btn.closest('.card, .iter');

  // Monster: auto-load this one card before expanding
  if (card.classList.contains('card') && !card.querySelector('iframe')) loadCard(card);

  const was = card.classList.contains('expanded');
  collapseAll();
  if (!was) {
    card.classList.add('expanded');
    document.querySelector('.backdrop, .expand-backdrop').classList.add('on');
    document.body.style.overflow = 'hidden';
  }
});

document.querySelector('.backdrop, .expand-backdrop').addEventListener('click', collapseAll);
```

Backdrop click always collapses. `Esc` collapses via the keyboard handler. Body scroll locks while expanded.

---

## 5. Browser-safety rules (OOM guard)

These are the same rules listed in `SKILL.md § Browser-Safety Rules`, repeated here because they're the core of the interaction model:

1. **Never auto-load iframes in the monster index.** Placeholders only until explicit user action.
2. **Warn at 20+ loaded.** `confirm()` before bulk-loading another segment.
3. **Use `loading="lazy"`** on every injected iframe.
4. **Inject, don't hide.** Create iframe on load, `.remove()` on unload — never `display:none` on a live iframe. (Hidden iframe still runs its JS and holds memory.)
5. **Cache-bust reloads** with `?r=${Date.now()}` so dev-mode iterations reflect instantly.

The monster template's JS implements all five. If you parameterise the template and find yourself tempted to simplify any of them, stop — they are load-bearing.

---

## 6. Event delegation pattern

The templates attach **one document-level click handler per event class**, matched via `e.target.closest(selector)`. This is preferred over per-card listeners for two reasons:

1. Cards are injected dynamically (monster sidebar items + cards both come from the same `SEGMENTS` array); a delegation pattern means no re-wiring after a re-render.
2. Cleaner unload — unloading a card `.remove()`s the iframe but keeps the outer `.card` shell, so the same delegated handler still fires for its placeholder clicks.

Do not convert to per-element listeners when parameterising. The delegation pattern is deliberate.

---

## 7. Accessibility behaviours

- Every button is keyboard-focusable with a visible focus ring (browser default against `#0a0a0a` is sufficient).
- Sidebar `<nav>`, segment `<nav>`, global controls group, and column switcher carry `aria-label`.
- `prefers-reduced-motion` → drop `behavior: 'smooth'` on `scrollIntoView`, drop the card expand transition. Nothing else in the UI animates ambiently.
- The outliner collapses to a top row at `≤900px` so no horizontal scroll on mobile.
- Loaded counter is `font-variant-numeric: tabular-nums` so the count doesn't jitter horizontally as it climbs through single-to-double-digit territory.
