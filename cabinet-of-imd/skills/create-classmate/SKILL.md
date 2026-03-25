---
name: create-classmate
description: Add a new guest specialist to the Cabinet of IMD
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
argument-hint: "[name]"
version: 1.0.0
---

Walk Tom through the classmate creation questionnaire to define a new guest specialist for the Cabinet of IMD Agents. New members join as guest specialists — they contribute expertise but participate lighter in chatter, gates, and crew dynamics.

If a name was provided as $ARGUMENTS, use that as the starting point. Otherwise, ask for one.

## Questionnaire Flow

Ask these questions one at a time using AskUserQuestion. Keep it conversational, not clinical.

1. **Name & Nickname** — What's their name? What does the crew call them?
2. **Real basis** — Are they based on a real person? (optional, can skip)
3. **Role** — What's their speciality? What do they bring to the cabinet?
4. **Personality** — How do they come across? What's their vibe? Memorable habits, attitude, quirks.
5. **Quirks & catchphrases** — Things they always say, habits the crew would recognise.
6. **Terminal/output style** — How do they write? Terse, verbose, emoji-heavy, dry, enthusiastic? Give examples.
7. **Colour & aesthetic** — Their terminal accent colour and visual identity. Reminder: cosmetic only, no bearing on project output.
8. **Expertise** — Specific technologies, frameworks, or domains they're known for.
9. **Relationships** — How do they relate to existing cabinet members? Who do they get along with? Any friction?

## Output

After completing the questionnaire, generate a YAML character file at:
`${CLAUDE_PLUGIN_ROOT}/references/characters/[nickname-lowercase].yaml`

Follow the exact format of existing character files. Include:
- `status: guest_specialist` (not `full_member`)
- All personality, expertise, output_style, colour, and relationship fields
- A note in relationships that they joined through the `/create-classmate` process

Present the completed character file to Tom for review before saving. Allow edits.

After saving, confirm the new member has been added and give a brief "welcome to the cabinet" message in the character's own voice.
