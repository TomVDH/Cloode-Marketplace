---
description: Two-pass vault analysis — structural sanitation (auto-fixable) + content review (report-only). Run on current project or vault-wide.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Deep analytical crawl of vault data. Pass 1 finds and fixes structural drift. Pass 2 surfaces content-level issues for human review.

## Usage

```
/dream                     Analyse current project (default)
/dream --vault-wide        Analyse all projects
/dream --save              Write report to projects/{slug}/dreams/YYYY-MM-DD.md
```

Dispatches to the `dream` skill.
