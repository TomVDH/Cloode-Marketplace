# Cabinet Code Conventions

All cabinet-generated code markers follow a single, consistent format that is instantly greppable and scrapable. **No cabinet artifacts survive to production.**

## The Universal Pattern

Every cabinet code marker starts with `## CABINET @` followed by a keyword. One grep catches them all:

```bash
grep -rn "## CABINET @" .
```

## Marker Types

### @TODO — Action Items and Notes

When a specialist leaves a note, flags an assumption, or marks work for another member:

```javascript
// ## CABINET @TODO -- THIEUKE -- container max-width assumes 4-col grid, check before adding 5th card ##
```

For assumptions about fragile code (known dependencies, expected input shapes):

```javascript
// ## CABINET @TODO -- SAKKE -- [ASSUMES] API always returns an array; will break on null response ##
```

### @SECTION / @ENDSECTION — File Ownership

When multiple specialists touch the same file, each marks their section:

```javascript
// ## CABINET @SECTION -- THIEUKE -- Layout ##
const CardGrid = () => {
  // ...
};
// ## CABINET @ENDSECTION -- THIEUKE ##

// ## CABINET @SECTION -- HENSKE -- Animations ##
const fadeIn = keyframes`...`;
// ## CABINET @ENDSECTION -- HENSKE ##
```

### @KNOWLEDGE — Inline Knowledge Drops

When a specialist uses a non-obvious technique and wants to share context:

```javascript
// ## CABINET @KNOWLEDGE -- SAKKE -- Using SameSite=Strict here because this cookie never needs cross-origin access. Lax would work too but Strict is safer for auth tokens. ##
res.cookie('session', token, { sameSite: 'strict' });
```

## Scraping Rules

### During Development
All markers are visible and informative. They help the team understand ownership, assumptions, and open items.

### At the Build Prep Gate
Bostrol scrapes ALL `## CABINET @` markers from the codebase:

1. **Inventory:** List every marker with file, line number, member, and content
2. **Categorise:** TODOs (resolved vs. deferred), sections (still needed?), knowledge drops (promote to docs or remove?)
3. **Present:** A checklist to Tom for review
4. **Jonas QA pass:** Jonasty validates no marker hides a real issue
5. **Kevijntje scope check:** Are deferred TODOs tracked in the parking lot?
6. **Strip:** After Tom approves, all `## CABINET @` markers are removed from the codebase

### Strip Command
```bash
# Remove all cabinet markers (single-line comments)
sed -i '/## CABINET @/d' $(grep -rl "## CABINET @" .)
```

## Guiding Principles

- Every marker must be a single-line comment (no multi-line blocks)
- The `##` bookends and `@KEYWORD` make them unmistakable — they'll never collide with real code comments
- Member names are always UPPERCASE in markers for consistency
- Keep marker content concise — one line, one thought
- If a marker needs more context, the specialist explains in a crew note (user-facing output), not in the marker itself
