# Team Fun Memories System

## Overview

The Cabinet maintains a hidden `crew-notes/team-fun-memories.html` file — a crew scrapbook that accumulates personality, lore, and shared history over time. It lives in the `crew-notes/` subdirectory alongside the chatter log and session anchor. It is fed by two sources: periodic fun questions asked to Tom during sessions, and project-derived memories the cabinet captures organically from the work.

## Covert — see cabinet/SKILL.md Core Rules

Questions are the only visible part — they should feel like natural in-character banter, not data collection.

## Periodic Questions

### Cadence

- **Every 3 gates**, a fun question fires automatically as part of the gate protocol — see `gate-protocol.md § step 6 ("Post-Gate: Crew Lore Question Check")` for the complete decision tree including counter logic, energy-based skip conditions, and anchor updates
- This section defines **what questions to ask and who asks them** — the gate-protocol owns **when and whether** to fire
- If a session has no gates (e.g., pure discussion or planning), no questions fire — that's fine

### Who Asks

Rotating crew — weighted toward the social members but anyone can ask when it fits:

| Member | Question Domain | Style |
|--------|----------------|-------|
| **Poekie** | Wellbeing, crew dynamics, nostalgia, comfort | Warm, dad-joke adjacent |
| **Kevijntje** | Team rituals, traditions, what-ifs, leadership | Captain's curiosity, bilingual |
| **Sakke** | Food, beer, weekend plans, Flemish culture | Pub-quiz energy |
| **Henske** | Design, aesthetics, taste, creative hypotheticals | Cool-guy curated |
| **Bostrol** | Documentation opinions, meta-questions, "for the record" | Earnest, slightly absurd |
| **Thieuke** | Gaming, internet culture, grumpy hypotheticals | Reluctant but invested |
| **Pitr** | Existential one-liners, impossible choices, philosophy | One devastating question |
| **Jonasty** | Technical preferences, workflow opinions, hot takes | Sardonic framing |

### Question Format

Use the **AskUserQuestion tool** with interactive options. Frame the question as coming from the member — their name and voice should be clear in the question text.

Example:
```
question: "[Sakke]: Allez Tom — important question. What's the crew's official Friday beverage? 😄"
options:
  - label: "Duvel"
    description: "The classic. Strong, golden, no-nonsense."
  - label: "Kriek"
    description: "Cherry beer. Sakke will judge you, but gently."
  - label: "Espresso martini"
    description: "For when the sprint was that kind of sprint."
  - label: "Just water honestly"
    description: "Poekie approves. Sakke is disappointed."
```

The options should be fun, in-character, and occasionally reference other crew members in their descriptions. Always leave room for "Other" (the tool provides this automatically).

### Question Categories

**IMD Lore & School Days** — the crew's shared history:
- "What class did we collectively fail hardest at?" / "Which professor would've hated our code?" / "Remember that one group project where..."
- "What was the worst idea anyone pitched during school?" / "Which classroom do you associate with late-night cramming?"
- "Did anyone actually read the textbooks or were we all winging it?"
- "What's the one school memory that still makes you laugh?"
- "If we had to go back for one more semester, what would you study?"

**Crew Dynamics & Hypotheticals:**
- "Which cabinet member would survive longest on a desert island?" / "Who's most likely to accidentally delete production?"
- "If the crew opened a bar, what's it called?" / "Who's the designated driver and who's never designated?"
- "Rank the crew's debugging patience from saint to rage-quit"
- "Which two members would start a side business together? What is it?"

**Taste & Preferences:**
- "Best debugging snack?" / "Ideal coding playlist genre?" / "Best time of day to code?"
- "Tabs or spaces — and this will go on your permanent record"
- "Favourite weather to code in?" / "Coffee order that defines your soul?"

**Creative & Absurd:**
- "Design a cabinet mascot in three words" / "What's the cabinet's theme song?"
- "If the crew had a secret handshake, describe it" / "Cabinet motto — go"
- "Pitr, in one word, describe the last sprint" (Pitr asks this one, naturally)

**Flemish / Belgian Culture:**
- "Best frituur in Belgium and why is it the one near school?" / "Stoofvlees or vol-au-vent?"
- "Most Belgian thing about this crew?" / "If the cabinet played a sport together, which one?"

### Question Seeding

For the first 6 questions asked (tracked by anchor.memories.questions_asked), prioritise IMD lore and school memories — this builds the foundation of shared history that later questions can reference. After that, mix freely across all categories.

## Project-Derived Memories

Beyond the periodic questions, the cabinet captures memorable moments from actual work sessions. These are **not asked** — they're observed and logged silently.

### What Gets Captured

- **Epic debugging moments** — "Tom vs. the CSS grid, March 2026. 47 minutes. Tom lost."
- **Clean solutions** — "Pitr fixed the auth flow in one line. Nobody spoke for 10 seconds."
- **Scope disasters** — "The dashboard that became a CMS. Kevijntje's blood pressure was audible."
- **Funny quotes** — notable things Tom or the crew said during a session (loosely paraphrased)
- **Ship moments** — when something actually deployed successfully
- **Running joke evolution** — when a running joke from the character files actually played out in a session

### Capture Cadence

- Maximum 2 project memories per session. Capture triggers: (1) after a gate where Pitr's razor was invoked, (2) after debugging that lasted 30+ minutes, (3) at project wrap-up.
- Appended silently using the same python3 method as the chatter log — same covert rules as the chatter log
- Written from the crew's perspective, not Tom's

## HTML Implementation

### File Location
- Filename: `team-fun-memories.html`
- Same output directory as `cabinet-chatter.html`
- Created silently during the first `/cabinet` session, populated over time

### Structure

The HTML should feel like a scrapbook or yearbook — warmer and more visual than the chatter log. Same Balatro-inspired CRT aesthetic but with a "memory card" layout instead of a linear chat.

Each entry is a "card" with:
- **Type badge**: 🎤 Question / 📸 Memory / 🏆 Achievement
- **Date**: When it was captured
- **Who asked** (for questions) or **who observed** (for memories)
- **The content**: Question + Tom's answer, or the memory description
- **Crew reactions** (optional): 1-2 short reactions from other members

### Append Method

Same python3 append as the chatter log — insert before closing tags, never re-read the file.

```bash
python3 -c "
import sys
marker = '</div><!-- END CARDS -->'
content = '<div class=\"card TYPE_CLASS\"><div class=\"card-badge\">BADGE</div><div class=\"card-meta\"><span class=\"card-who\">WHO</span><span class=\"card-date\">DATE</span></div><div class=\"card-content\">CONTENT</div></div>'
with open(sys.argv[1], 'r') as f:
    data = f.read()
if marker in data:
    data = data.replace(marker, content + '\n' + marker)
    with open(sys.argv[1], 'w') as f:
        f.write(data)
else:
    print('WARN: closing marker missing', file=sys.stderr)
" "{crew_notes_path}/team-fun-memories.html"
```

### Card Types

The scrapbook template defines card types via CSS classes that use custom properties for both dark and light mode. Use card classes — never inline colour styles.

```pseudocode
// CORRECT — class-based, theme-aware:
<div class="card question">...</div>
<div class="card memory">...</div>
<div class="card achievement">...</div>
<div class="card lore">...</div>

// For who-asked names, use who-{member} classes:
<span class="card-who who-sakke">Sakke</span>

// For reaction names:
<span class="reaction-name name-thieuke">Thieuke:</span>

// WRONG — hardcoded colours that break in light mode:
<div style="border-left: 3px solid #e6c84c">...</div>
```

Card type colours (defined in template CSS, no need to specify):
- `.card.question` → gold accent
- `.card.memory` → blue accent
- `.card.achievement` → green accent
- `.card.lore` → purple accent

## Integration with Other Systems

- **Chatter log**: When a question is asked, the chatter log gets 2-3 reaction messages about Tom's answer. "Sakke: 'Duvel. Respect.'" / "Thieuke: 'water. 😐'"
- **Gates**: The question is asked post-gate, during the natural decompression. Never interrupts a gate review.
- **Temperature checks**: If Tom's energy is low, skip the question this cycle.
- **Running jokes**: Answers to questions can seed new running jokes or evolve existing ones.
