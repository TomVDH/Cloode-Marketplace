# Obsidian Setup Guide

Bostrol walks Tom through this guide when he asks to set up or optimise the vault for Obsidian. The goal: a vault that feels native — graph view, queries, templates, and backlinks from day one.

---

## Core Plugins (Built Into Obsidian)

Settings → Core plugins. Enable:

1. **Templates** — Set template folder to `templates/`. The cabinet's project-brief, decision, and session-summary templates become one-click note creation.

2. **Backlinks** — Enable the backlinks pane (right sidebar). Every project brief shows all decisions and sessions linked to it.

3. **Graph View** — Filters:
   - `tag:#cabinet/project` — project nodes only
   - `tag:#cabinet/decision` — decision web
   - `path:projects/dff2026-web` — scope to one project
   - Colour groups by tag for visual clarity

4. **Tags** — Enable the tags pane. `#cabinet/` namespace keeps cabinet tags separate from personal tags.

5. **Page Preview** — Hover over wikilinks to see content without opening.

---

## Community Plugins (Recommended)

Settings → Community plugins → Browse:

1. **Dataview** — The single most valuable addition. Example queries for v2:

   ```dataview
   TABLE specialist, status, date
   FROM "projects/dff2026-web/decisions"
   SORT date DESC
   ```

   ```dataview
   TABLE gates_completed, specialists
   FROM #cabinet/session
   WHERE date >= date(today) - dur(30 days)
   SORT date DESC
   ```

   ```dataview
   TABLE status, rows.file.link AS "Projects"
   FROM #cabinet/project
   GROUP BY status
   ```

   ```dataview
   LIST
   FROM #cabinet/decision
   WHERE status = "active" AND specialist = "sakke"
   ```

2. **Templater** (optional) — More dynamic templates. Cabinet doesn't require it.

3. **Calendar** (optional) — Sessions are `YYYY-MM-DD.md` inside project folders, so they appear on the calendar.

4. **Kanban** (optional) — For manual parking lot or scope organisation.

---

## Vault Settings

Settings → Files & Links:

- **New link format:** "Shortest path when possible" — matches how the cabinet creates wikilinks
- **Default location for new notes:** "Same folder as current file"
- **Detect all file extensions:** Enable

Settings → Appearance:

- Any theme works — cabinet notes are plain markdown.

---

## Hotkeys

- `Cmd + O` — Quick switcher
- `Cmd + Shift + F` — Search across all notes
- `Cmd + G` — Graph view
- `Alt + Click` — Open wikilink in new pane

---

## First-Time Walkthrough

When Tom opens a freshly scaffolded vault:

1. Open `Home.md` — pin to sidebar for quick access
2. Open Graph View — sparse at first, grows with each session
3. Open Tags pane — see the `#cabinet/` namespace
4. (Optional) Create `Dashboard.md` in root with Dataview queries — Bostrol can generate these

---

## What the Cabinet Writes vs. What Tom Owns

**Cabinet writes (automated, covert):**
- `projects/{slug}/brief.md` — project briefs
- `projects/{slug}/decisions/{date}-{slug}.md` — decisions
- `projects/{slug}/sessions/{date}.md` — session summaries
- `projects/{slug}/decisions/_index.md` — per-project decision MOC
- `projects/_index.md` — master project index
- `crew/preferences.md` — preferences
- `crew/lessons-learned.md` — patterns and gotchas
- `Home.md` — updated at wrap-up

**Tom owns (manual, personal):**
- Dataview dashboards or query notes
- Kanban boards
- Personal annotations below `---` separators in cabinet notes
- Notes outside the cabinet folder structure
- Obsidian settings, themes, plugins

The cabinet never modifies Tom's manual additions. When updating Home.md or MOCs, it rewrites auto-generated sections and preserves content below a `---` separator.
