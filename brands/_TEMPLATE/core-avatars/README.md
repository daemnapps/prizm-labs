# core-avatars/

The customer types: one folder per core avatar, its sub-avatars, their exact words, objections and research.

---

## core-avatars — the WHO axis

One folder per **core avatar**, each holding `profile.md`. Sub-avatars live in
`<core>/sub-avatars/sub-NN-<slug>.md`.

```
core-avatars/
  <avatar-slug>/
    profile.md                  who they are
    sub-avatars/
      sub-01-<slug>.md          a narrower who, inside this core
    language/
      rules.md                  how they speak — instruction
      *.json                    verbatims — evidence, selected per source
```

**The folder name IS the avatar slug.** It is what an angle names, what a page
declares, and what a report groups on — so it is never renamed casually and
never invented: an avatar exists here or it does not exist.

## Where this sits in the model

`components/naming/MODEL.md`: **avatar × angle × channel × format**. This folder
is the first axis. An angle names exactly one core avatar from here, and may
serve several sub-avatars declared on the asset.

**A sub-avatar never gets its own angle.** The same claim aimed at a narrower
person is a sub-avatar, not a new row — two rows split the reporting on one
claim. This is checked: `components/naming/selfcheck.py` fails an angle whose
avatar is not a real folder here.

## Scale is not a target

<brand> has four cores; another brand has one. A core avatar earns its folder by
being genuinely a different person with a different problem, never by filling
out a column.

## rooms — where they talk

A sub-avatar file (or a core avatar's `profile.md` when there is no narrower
sub-avatar yet) carries one `### rooms` block, naming the real forums or
communities that avatar is actually in.

**NOBODY HAS TO WRITE THIS BLOCK.** Damon ruled it on 2026-09-18:
*"he should never have to write down rooms - the system finds where the avatar talks on its own"*.
The research gatherer (`components/research-gatherer/`) fills it: it takes the
avatar's own Core desire words off this file, fires ONE unrestricted search,
tallies which communities the results came from weighted by how loud each one
was, and writes the top five back here:

```
### rooms — found 2026-09-18 by the gatherer (edit freely; add "confirmed by: <your name>" to lock)
- r/subredditname — 12 post(s), 840 total score in the discovery pull
- r/another-room — 4 post(s), 96 total score in the discovery pull
```

**A person may edit that block freely, and locks it with one line.** Add
`confirmed by: <your name>` anywhere inside the block and it becomes a
ruling: the gatherer reads it as written and never runs discovery for this
avatar again. Without that line the block is provisional, and the next
discovery replaces it (every other byte of the file is left alone). That is
how a hand-written block works too — write the rooms you want and add the
confirm line, and they stand.

```
### rooms — Where they talk
confirmed by: Damon
- r/subredditname — one clause on why this room fits
- r/another-room — one clause
```

Read by the research gatherer, which every chain reaches through its own thin
shim (`components/video-teardown/machine/research.py`,
`copy/machine/research.py`). Reddit's own door only hits hard when a
room is named — a bare search wanders — so this is the field that makes a pull
land on the right community instead of the internet in general. **The tool
still never invents a room:** a discovery that comes back empty (no key, a
403) falls back to whatever this block already said, and an avatar with
neither gets `[UNFILLED: no rooms recorded for this avatar]`, not a guess.

A new brand plugs into the same research door by naming a Core desire on its
avatar files and letting the gatherer find the rest. Nothing about the tool
changes, ever (rule 7) — the room names are data, never code.

## demographics — who this avatar actually is, as labelled data

Ruled by Damon, 2026-09-18, after room discovery for a sun-damage sub-avatar
came back with communities for a different set of people entirely: **research
has to be reconciled against the avatar's demographics or it is irrelevant for
that avatar.** The prose "who they are" line stays where it is; this block is
the same facts in slots a machine can read.

One `### demographics` block on `profile.md`, five lines, plain words:

```
### demographics
age: <band, e.g. 55–70>
gender: <e.g. female>
skin tone / ethnicity: <e.g. majority Black/African-American>
region: <e.g. US Sun Belt>
language: <e.g. English (US)>
```

Rules:

1. **Only what the file already says.** Every line is taken from what this
   profile states in prose. Nothing is inferred from a name, a photo, a room
   name or a guess about the category.
2. **`unknown` is a real answer and the default.** A slot the profile does not
   state says `unknown`. An `unknown` slot never rules anything out — the
   research gatherer treats it as "no opinion", not as "no".
3. **A sub-avatar inherits, and may override.** A sub-avatar file with its own
   `### demographics` block overrides the core's, line for line; a sub-avatar
   without one is the core's.
4. **A working band stays a working band.** If the prose calls a figure
   unmeasured or inferred, keep that word in the slot — the block is a copy of
   what is known, never a promotion of it.

Read by the research gatherer (`components/research-gatherer/`), which judges
every discovered room against this block and **drops the ones that plainly
belong to a different set of people**, recording each drop and its reason in
the run rather than filing rows from it. The marker table it judges with
(room-name signal → demographic signal) lives in that component's
`research.json`, never here and never in a brand file — room names are data,
and the markers are config (rule 7).

## Schwartz slots (2026-09-18) — what `profile.md` adds under Desire

`profile.md`'s existing "1. Desire" section is where these land — extending
it, never replacing it. The framework behind each slot lives in
`components/marketing-doctrine/slices/` (bind by path; never restate the
framework here):

- **Lead desires, ranked on the three dimensions** — urgency, staying power,
  scope (`components/marketing-doctrine/slices/desire.md`). Only one desire
  leads a given angle; rank the candidates, never invent a new one.
- **Awareness level per desire** — one of the five named levels
  (`components/marketing-doctrine/slices/awareness.md`): most-aware ·
  product-aware · solution-aware · problem-aware · unaware.
- **Sophistication stage of the category** — one of the five named stages
  (`components/marketing-doctrine/slices/sophistication.md`): what the
  category has already claimed, and with what mechanism.
- **Roles claimed** — character (who the avatar says they are) and
  achievement (what the avatar says they've attained), taken from the
  avatar's own words (`components/marketing-doctrine/slices/techniques.md`,
  Identification).
- **Beliefs already accepted** — the fact(s) this avatar starts from, cited
  to a source. A Gradualization chain builds forward from these; it never
  invents a starting belief.

Sourced from the five research domains + synthesis
(`control-room/prompts/research/`), filled in per avatar. Agnostic
by rule: this file names no brand, product or avatar — only the slots.


## One home per sub-avatar (2026-09-18)

Beside each sub-avatar card `sub-avatars/<card>.md` sits its folder
`sub-avatars/<card>/` with `language/` (its clean research rows, filed by the
gatherer, read by every chain) and `research/<date>/` (the readable report).
Raw pulls never land here — they stay under `runs/research/`.
