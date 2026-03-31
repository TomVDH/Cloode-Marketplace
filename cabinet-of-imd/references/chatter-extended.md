# Chatter Log — Extended Reference

Loaded on demand, not at boot. See `chatter-system.md` for core implementation.

## User Action Markers

The chatter log includes system-style markers that track notable user actions and session events. These appear as styled divider rows in the chat — distinct from member messages but integrated into the timeline.

### Marker Types

Markers use horizontal rules and emoji headers in Markdown. They're visually distinct from member messages in the vault.

**Date & session markers:**
```markdown
---
*Session — 15 March 2026, 14:32*

---
*☕ Break taken — 23 minutes*

---
*Session resumed — 15 March 2026, 14:55*
```

**Versioning markers** — when a commit, version bump, or branch event occurs:
```markdown
---
🏷️ *v0.9.0 — "Fixed the dashboard empty state that Poekie caught"*
🌿 *Branch merged: feature/dashboard → main*
📦 *Commit: "add responsive grid to card layout"*
```

**User mood / behaviour markers** — observed by the cabinet, inserted when patterns emerge:
```markdown
---
⚡ *Tom is grinding — same issue for 30+ minutes*
😤 *Insistent messages detected — patience running low*
😴 *Tom's getting lazy with the prompts — one-word instructions incoming*
🎉 *Tom is in the zone — shipping fast, vibes are good*
🤡 *Tom is being silly — the prompts have gone off the rails*
```

**Scope markers** — when scope changes are detected:
```markdown
---
📐 *Scope creep detected: +2 components added mid-sprint*
✂️ *Scope trimmed: Tom agreed to defer animations to v2*
```

**Gate markers** — when gates are completed:
```markdown
---
🚪 *GATE PASSED: Dashboard Layout — approved by Tom*
🚪 *GATE HELD: API Integration — Poekie flagged empty state UX*
```

### When to Insert Markers

- **Date markers:** At session start and resume after breaks
- **Version markers:** After any commit, version bump, or branch operation
- **Mood markers:** When the cabinet observes a pattern in Tom's behaviour — frustration, laziness, silliness, enthusiasm. Insert a mood marker when 3 consecutive user messages show the same energy pattern. Frustration signals: repeated questions, short impatient messages, 'why' / 'still' / 'broken'. Laziness signals: messages under 5 words, no explanation. Enthusiasm signals: exploratory language, 'what if' / 'let's try'. Reset detection after each marker.
- **Scope markers:** When items are added to or removed from the current sprint/plan
- **Gate markers:** At every gate pass or hold

### Marker Styling

Markers are plain Markdown — horizontal rules (`---`) followed by emoji-prefixed italicised text. No CSS needed. Obsidian renders these cleanly as visual breaks in the chatter timeline.

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

### Detecting a Missing File

Before appending, verify the chatter file exists for today's date:

```pseudocode
chatter_path = vault_base + "/projects/" + project_slug + "/chatter/" + TODAY + ".md"
IF NOT exists(chatter_path):
    // Create from template
    COPY template from ${CLAUDE_PLUGIN_ROOT}/examples/vault-templates/chatter.md
    FILL frontmatter (project, date, specialists)
    APPEND: "\n---\n*⚠️ Chatter log recovered — previous messages from today may be lost*\n"
    CONTINUE appending as normal
```

This is silent — never mention the recovery to the user. The crew just... keeps talking.

### Safe Append Method

Appending to the Markdown chatter is a simple file append — no markers, no HTML escaping needed. Use `vault.append()` (see `chatter-system.md`). If the append fails, log a warning in the anchor's chatter section and skip — never retry in a loop.

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
