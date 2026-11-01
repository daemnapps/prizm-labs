# Stage 2 — Voices (speech + cloning)

Status: **baseline only** — to be built out in detail.

## Job

One consistent voice per character across a whole ad. The voice is a
written paragraph, then cloned from its own best take, line after line.

## Baseline (from the proven run)

- Three-step recipe: (1) **base take** from a prose persona (or a real
  uploaded recording as seed); (2) **chain** every next line off the base
  take — "SAME speaker, identical voice"; (3) **lock** a drifting accent by
  stacking the two best takes and naming the phonetics explicitly.
- Slower-than-neutral speaking rate reads dramatically better.
- Punctuation in the line is the pacing direction.
- Hard lines take up to ~14 takes; escalating clone scaffolding across
  retries is normal.

## The slot

Any voice model that can: generate speech from a text persona, clone from
one or more reference recordings (same-speaker continuity), and control
rate and expressiveness.

**Audition:** ten chained lines that still sound like one person, accent
intact on line ten.

## To build out

- [ ] The persona-paragraph template (which attributes actually steer the
      voice)
- [ ] Take management: how many takes, how to pick, what gets banked
- [ ] Accent-lock playbook: the phonetics vocabulary that works
- [ ] Seed-from-real-recording route: consent, quality floor, prep
- [ ] Candidates for the local slot (proven / testing / rejected)
