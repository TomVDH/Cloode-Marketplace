# Terminal Colour Reference

## Environment Detection

Detect the rendering environment reliably:

```pseudocode
IF the skill was invoked from a Cowork desktop session:
    // Cowork sessions are identifiable by: the system prompt mentions Cowork mode,
    // the session has a /sessions/ path prefix, or the AskUserQuestion tool is available
    env = "cowork"        // use markdown headers (unicode blocks + bold)
ELSE:
    env = "terminal"      // use ANSI coloured headers via echo -e
```

**Default to "cowork" (markdown) when uncertain.** Markdown renders acceptably everywhere. ANSI codes in Cowork produce garbled output. Err on the safe side.

## ANSI Colour Codes per Member

When outputting in a terminal environment (Claude Code), use ANSI escape codes to render coloured headers, name tags, and decorative elements. These are the RGB values for true-colour ANSI output (`\033[38;2;R;G;Bm`).

Each member has a distinct hue spread across the RGB gamut for instant visual identification.

| Member | Hue | Primary RGB | ANSI Primary | Reset |
|--------|-----|-------------|--------------|-------|
| Thieuke | Teal/cyan | 104, 208, 212 | `\033[38;2;104;208;212m` | `\033[0m` |
| Sakke | Coral | 232, 128, 112 | `\033[38;2;232;128;112m` | `\033[0m` |
| Jonasty | Green | 112, 200, 112 | `\033[38;2;112;200;112m` | `\033[0m` |
| Pitr | Lavender grey | 168, 168, 200 | `\033[38;2;168;168;200m` | `\033[0m` |
| Henske | Purple | 184, 120, 240 | `\033[38;2;184;120;240m` | `\033[0m` |
| Bostrol | Sand/gold | 216, 184, 112 | `\033[38;2;216;184;112m` | `\033[0m` |
| Kevijntje | Amber | 240, 168, 40 | `\033[38;2;240;168;40m` | `\033[0m` |
| Poekie | Chartreuse | 168, 208, 64 | `\033[38;2;168;208;64m` | `\033[0m` |

## How to Output Coloured Headers

### In Claude Code (Terminal)
Use Bash tool with `echo -e` to print coloured headers before the response content:

```bash
echo -e "\033[38;2;104;208;212m╔══════════════════════════════════════╗\033[0m"
echo -e "\033[38;2;104;208;212m║\033[0m  \033[1;38;2;104;208;212m[THIEUKE]\033[0m  Frontend Specialist      \033[38;2;104;208;212m║\033[0m"
echo -e "\033[38;2;104;208;212m╚══════════════════════════════════════╝\033[0m"
```

For collaboration headers, interleave both members' colours:

```bash
echo -e "\033[38;2;184;120;240m╔══════════════════════════════════════╗\033[0m"
echo -e "\033[38;2;184;120;240m║\033[0m  \033[1;38;2;184;120;240m[HENSKE]\033[0m + \033[1;38;2;104;208;212m[THIEUKE]\033[0m  UI Polish    \033[38;2;184;120;240m║\033[0m"
echo -e "\033[38;2;184;120;240m╚══════════════════════════════════════╝\033[0m"
```

### In Cowork (Desktop / Markdown)
Cowork renders markdown, not ANSI codes. Use unicode blocks and bold: `**▓▓ [MEMBER] ▓▓** Role` with `━` rule underneath. For collaborations: `**▓▓ [A] + [B] ▓▓** Task`. Cowork won't render colour — personality and tone do the rest.

## Inline Name Colouring (Terminal Only)

Optionally colour member names inline: `echo -e "Checked with \033[38;2;232;128;112mSakke\033[0m — auth middleware looks clean."` — use sparingly, mainly in gate summaries and handoffs.

## Colour Accessibility

The 8 member colours were chosen to be distinguishable across the RGB gamut. However, some combinations are challenging for colour-blind users:

### Known Conflicts

| Condition | Affected Pair | Mitigation |
|-----------|--------------|------------|
| Deuteranopia (green-blind) | Jonasty (green) ↔ Poekie (chartreuse) | Names always accompany colour — never colour-only identification |
| Protanopia (red-blind) | Sakke (coral) ↔ Bostrol (sand/gold) | Box headers include member name in bold text |
| Monochromacy | All pairs | Every output uses `[Member Name]:` prefix — colour is supplementary, never the sole identifier |

### Design Principles

1. **Colour is decoration, not information.** Member identity is always conveyed through the `[Name]:` prefix, header text, or avatar initials — never through colour alone.
2. **Contrast against background.** All 8 primary colours meet a minimum 4.5:1 contrast ratio against a dark terminal background (#1a1a1a) and the Coast Mono dark theme background.
3. **In Cowork (markdown), colour doesn't render.** This is fine — personality and the `[Name]:` prefix carry all identification. Colour is a terminal-only enhancement.
