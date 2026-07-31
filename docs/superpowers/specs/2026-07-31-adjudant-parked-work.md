# Adjudant parked work, as of v0.26.0

Two things are decided but unbuilt. Both are recorded here rather than in a
gitignored scratch directory, because that is exactly how the board and draw
audit stayed invisible across four releases.

---

## 1. The archive verb: BUILD IT

Tom's original request, from 2026-07-27: automatically archive context older
than 30 days into a standardized folder, excluding specs and references.

Decisions locked with him during that brainstorm:

- **Perma-memory** is a new per-project `MEMORY.md` (all caps, sitting beside
  `AGENTS.md` in spirit). Schema-typed, never archived, never staled. The
  deep-analysis pass appends dated, sourced entries under themed headings, and
  `check` / `sitrep` can surface it.
- **Destination** is a project-root `archived-context/` mirroring the original
  structure (`archived-context/sessions/2026-05-27.md`), added to the walker
  skip set so `check`, `dream`, `ramasse`, `board` and the cost estimator stop
  paying for it. Still greppable, still searchable in Obsidian. A manifest
  `_index.md` records what moved and when.
- **Scope**: `sessions/`, `dreams/`, `notes/` (by `updated:`), and `tasks/` in
  terminal states (done, icebox) untouched for 30+ days. NEVER `references/`,
  `specs/`, `releases/`, `decisions/`, `brief.md`, `_handoff.md`, `MEMORY.md`,
  or board files.
- **Trigger**: a verb with two-phase preview then apply, plus an ambient nudge
  from `check`, `sitrep` and SessionStart when eligible files pile up.
  Automatic awareness, human-confirmed action.
- **Deep analysis before the move**: a judgment pass over the outgoing set
  proposes durable facts for promotion into `MEMORY.md`, so archiving is
  lossless in substance even when it is lossy in volume.

Still open: the verb name, whether the 30-day threshold is a breadcrumb knob or
a flag, and the exact analysis-to-promotion contract.

**Design constraint, non-negotiable.** The archive verb is a MOVER, the most
destructive shape in the plugin. It must inherit `shelf`'s transaction pattern
(re-plan at apply, abort before any write, manifest backup), NOT `tidy`'s, or
it inherits the stale-preview clobber by construction. Plus containment checks,
the `atomic_write_text` / `file_lock` primitives in `_vault_walk`, and zone
awareness from birth. Every guard mutation-proven, per the standard set in
v0.18.0.

---

## 2. Staged escalation for large projects: DO NOT BUILD

Scoped on 2026-07-28 after measuring `dream` as impossible on the biggest
projects. Re-measured on 2026-07-31, and the measurement dissolved most of the
case.

**The earlier figure was wrong.** hubspot-nightly was reported at ~1.18M
tokens. What `dream` actually estimates is **455k**: 435k of that project is
`_legacy/`, which `walk_project` already skips. The original number counted
files the verb never reads, and overstated by 2.6x.

**What the corpus really looks like:**

| project | dream estimate | composition |
|---|---|---|
| tf-renewal | 613k | 90% is `content-recon`; 592 of 594 files untouched 30+ days |
| hubspot-nightly | 455k | 137 of 590 files dormant; `_legacy` already skipped |
| `_port-test-hubspot` | 608k | 195 of 195 files dormant. A port TEST ARTIFACT |
| next four | 51k to 119k | expensive, not impossible |

**Why the four proposed narrowing strategies do not hold up:**

- A **recency window** infers that recent equals relevant. True for staleness,
  false for contradictions, and an old decision contradicting a new one is
  precisely what `dream` exists to find. It is the one filter guaranteed to
  hide the target.
- **Folder scoping** infers nothing; the operator chooses it. That is a flag,
  not an architecture.
- **Sampling** is epistemically unsound here. `dream` is a needle hunt, so
  reading 20% finds roughly 20% of contradictions with no way to know which 80%
  were missed. That is worse than not running, because the output looks
  complete.
- A **frontmatter-only pass** infers structure, not semantics, and structure is
  already `check`'s and `ramasse`'s job.

**Cheaper interventions that dissolve the problem instead:**

1. Delete `_port-test-hubspot`. 608k of dead test artefact, every file dormant.
   A third of the problem, removed by `rm`.
2. Ship the archive verb. It takes tf-renewal's 592 dormant files and
   hubspot-nightly's 137 out of the walk permanently. It was designed for this.
3. Add a `--folder` flag to `dream` for deliberate scoping, without pretending
   to infer relevance.

Nothing is currently broken: the cost gate already warns rather than letting
anyone walk into a wall blind. The verb is expensive on three projects, which
is a different claim from impossible.

**Reassess only after the archive verb ships.** The one case surviving all
three interventions is auditing tf-renewal's `content-recon` wholesale, and
that corpus is a bulk scrape rather than knowledge, so it probably does not
want semantic auditing at all.
