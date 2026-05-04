# Bases — Authoritative reference

Beyond what the kepano-imported SKILL.md and `FUNCTIONS_REFERENCE.md` cover, the official Obsidian docs go deeper. Consult these when designing a complex base, debugging filter behavior, or constructing nested formulas.

## Topic map

| Topic | Online | If you have the Obsidian Help vault locally |
|---|---|---|
| Introduction & concept | <https://help.obsidian.md/bases> | `Bases/Introduction to Bases.md` |
| Creating a base from scratch | <https://help.obsidian.md/bases/create> | `Bases/Create a base.md` |
| Full `.base` YAML syntax (filters, formulas, views, sources) | <https://help.obsidian.md/bases/syntax> | `Bases/Bases syntax.md` |
| Formula language (operators, precedence, type coercion) | <https://help.obsidian.md/bases/formulas> | `Bases/Formulas.md` |
| Function library (full list with signatures + examples) | <https://help.obsidian.md/bases/functions> | `Bases/Functions.md` |
| View types (table, card, gallery) and their config | <https://help.obsidian.md/bases/views> | `Bases/Views.md` |
| Layouts & per-view ordering | <https://help.obsidian.md/bases/layouts> | `Bases/Layouts/` (folder) |

## When the kepano SKILL.md isn't enough

Reach for the official docs above when:
- Designing a filter that needs property comparisons across types (string ↔ number ↔ date)
- Combining multiple `where:` clauses with AND/OR precedence you're unsure about
- Writing formulas that call functions on optional/null values (the official functions doc specifies null behaviour per function)
- Building a view that needs grouping or summary rows
- Resolving a "filter returns nothing / returns everything" mystery — the syntax doc has the canonical operator semantics

## Search semantics overlap

Bases filter expressions share semantics with Obsidian's Search syntax. When unsure how a filter will match, run the equivalent Search query first to validate. See `obsidian-bridge:search`.
