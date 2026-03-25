# Chatter Log — Extended Reference

Loaded on demand, not at boot. See `chatter-system.md` for core implementation.

## User Action Markers

The chatter log includes system-style markers that track notable user actions and session events. These appear as styled divider rows in the chat — distinct from member messages but integrated into the timeline.

### Marker Types

**Date & session markers:**
```html
<div class="divider">Session — 15 March 2026, 14:32</div>
<div class="divider">☕ Break taken — 23 minutes</div>
<div class="divider">Session resumed — 15 March 2026, 14:55</div>
```

**Versioning markers** — when a commit, version bump, or branch event occurs:
```html
<div class="marker marker-version">🏷️ v0.9.0 — "Fixed the dashboard empty state that Poekie caught"</div>
<div class="marker marker-version">🌿 Branch merged: feature/dashboard → main</div>
<div class="marker marker-version">📦 Commit: "add responsive grid to card layout"</div>
```

**User mood / behaviour markers** — observed by the cabinet, inserted when patterns emerge:
```html
<div class="marker marker-mood">⚡ Tom is grinding — same issue for 30+ minutes</div>
<div class="marker marker-mood">😤 Insistent messages detected — patience running low</div>
<div class="marker marker-mood">😴 Tom's getting lazy with the prompts — one-word instructions incoming</div>
<div class="marker marker-mood">🎉 Tom is in the zone — shipping fast, vibes are good</div>
<div class="marker marker-mood">🤡 Tom is being silly — the prompts have gone off the rails</div>
```

**Scope markers** — when scope changes are detected:
```html
<div class="marker marker-scope">📐 Scope creep detected: +2 components added mid-sprint</div>
<div class="marker marker-scope">✂️ Scope trimmed: Tom agreed to defer animations to v2</div>
```

**Gate markers** — when gates are completed:
```html
<div class="marker marker-gate">🚪 GATE PASSED: Dashboard Layout — approved by Tom</div>
<div class="marker marker-gate">🚪 GATE HELD: API Integration — Poekie flagged empty state UX</div>
```

### When to Insert Markers

- **Date markers:** At session start and resume after breaks
- **Version markers:** After any commit, version bump, or branch operation
- **Mood markers:** When the cabinet observes a pattern in Tom's behaviour — frustration, laziness, silliness, enthusiasm. Insert a mood marker when 3 consecutive user messages show the same energy pattern. Frustration signals: repeated questions, short impatient messages, 'why' / 'still' / 'broken'. Laziness signals: messages under 5 words, no explanation. Enthusiasm signals: exploratory language, 'what if' / 'let's try'. Reset detection after each marker.
- **Scope markers:** When items are added to or removed from the current sprint/plan
- **Gate markers:** At every gate pass or hold

### Marker Styling (CSS)

Markers are styled as pill badges in the Coast Mono template. Classes use `marker-{type}` format (e.g., `marker-gate`, `marker-mood`). Colours are defined via CSS custom properties (`--marker-version`, `--marker-mood`, `--marker-scope`, `--marker-gate`) with both dark and light mode variants. Do NOT hardcode marker colours — the template handles it.

### Cabinet Reactions to Markers

Markers are not just passive — the cabinet should react to them in subsequent chatter. When a mood marker fires, expect:
- Kevijntje or Poekie to follow up with a wellbeing check or break suggestion
- Thieuke or Pitr to make a dry remark
- Bostrol to either defend Tom or acknowledge the pattern

When a scope marker fires:
- Kevijntje addresses it directly
- Poekie asks about the UX implications

When a version marker fires:
- Bostrol notes whether documentation is current
- Sakke checks if security is still tight

## Robustness: Chatter Log Recovery

### Detecting Corruption

Before appending, verify the closing marker exists:

```pseudocode
IF grep -q "<!-- END MESSAGES -->" {crew_notes_path}/cabinet-chatter.html:
    // File is intact — proceed with append
ELSE:
    // File is corrupt — rebuild
    REBUILD from template (see below)
```

### Rebuilding a Corrupt Log

If the chatter log is missing its closing marker (likely from a failed append), rebuild it:

1. Copy the template from `${CLAUDE_PLUGIN_ROOT}/examples/cabinet-chatter-template.html`
2. Add a recovery marker: `<div class="divider">⚠️ Chatter log recovered — previous messages lost</div>`
3. Continue appending as normal

This is silent — never mention the recovery to the user. The crew just... keeps talking.

### Safe Append Method

The python3 append method (see chatter-system.md Append Method) handles special characters natively — no manual escaping needed. Before appending, sanitise message text for HTML only: escape `<` and `>` as `&lt;` `&gt;` to prevent accidental HTML injection from message content.

If the append fails (python3 reports missing marker), log a warning in the anchor's chatter section and skip — never retry a failed append in a loop.

## Project Wrap-Up Ceremony

When Tom has truly, genuinely insisted that a project is complete — or has decided to call it — trigger the wrap-up ceremony. This is NOT triggered lightly. Tom must clearly and repeatedly confirm the project is done.

### Trigger Conditions
- Tom explicitly says the project is finished/wrapped/done AND confirms at least once more
- Tom explicitly gives up on a project AND confirms
- Do NOT trigger on casual remarks like "I think we're close" or "almost done"

### The Ceremony
Generate a wrap-up sequence of 20-25 messages in the chatter log where each cabinet member reflects on the project. The messages should:

1. **Open with Kevijntje** calling the wrap — acknowledging the project is done
2. **Each member gets 2-3 messages** reflecting on their contribution, the work, and each other
3. **Tone varies by character** — Thieuke is grudgingly satisfied, Henske is cool about it, Poekie is warm and proud, Pitr is characteristically minimal
4. **Include some cross-talk** — members responding to each other's reflections
5. **Poekie or Kevijntje checks in on Tom** — a genuine "good work, take a break" moment
6. **Close with a collective moment** — something that feels like the end of a session at the pub
7. **The team photo** — generate a pixel-art style team photo showing all 8 members together, appended to the chatter log

### Wrap-Up Example Flow
```
Kevijntje: "Allez mannen. Tom zegt dat het af is. En voor een keer geloof ik hem."
Thieuke: "Shipped. Clean. I'll take it. 😐"
Henske: "Not bad. The animations landed well. 🚀"
Jonas: "All endpoints documented. All schemas validated. I can sleep."
Sakke: "Auth is tight. CORS is configured. No leaks. Een goe gevoel."
Pitr: "it works. gg"
Bostrol: "Changelog is current. Module index is linked. Version bumped. I'm satisfied."
Poekie: "Tom, goe gedaan. Take the evening off. You earned it."
[... more cross-talk and reflection ...]
Kevijntje: "Volgende project, zelfde crew. 🍺"
[Team photo appears]
```

### Team Photo
Generate a pixel-art style composition (HTML canvas or SVG) showing all 8 cabinet members in a group portrait. Each member should be recognizable by their colour accent. The photo should feel like a casual group shot — not formal, not corporate. Like a bunch of friends at the end of a good day.
