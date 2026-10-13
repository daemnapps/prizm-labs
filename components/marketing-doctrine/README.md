# components/marketing-doctrine — the marketing doctrine every machine cites

**Owner: the owner** (definitions), engine shared. Resident since 2026-09-18.

The creative layer runs on one doctrine, and this folder is where it lives:
mass desire, the five awareness levels, the five sophistication stages, the
seven techniques, mood, proof placement, the close, the sections, and the
research questions that answer the judgment calls. It is brand-agnostic and
always will be — no brand, product, avatar, model or platform name appears in
any file here.

| File | What it is |
|---|---|
| `frameworks.json` | **the truth.** The labelled slots, every row carrying its `[L####]` line pointer |
| `delivery.json` | **the taste layer.** The labelled delivery dials — humor level, delivery style, register, pacing, reference world, avoid — each value carrying what it does, when it fits, its risk and the receipt it needs |
| `emotion.json` | **the emotional layer.** The emotional map — the feelings a beat is spelled in, intensity 1–5, the five points every map names (open · low · turn · peak · end), the arcs a whole piece runs, the director's levers that carry a feeling, the rules, and the receipts behind them |
| `spoken.json` | **the spoken layer.** The rules of spoken copy (written-vs-spoken, each with its receipt URL), the five colloquialism levels as a dial, a register recipe per delivery style with the voice-model settings that match it, the punctuation map for the voice model the track is made on, and the demographic bands a colloquialism is keyed to — options tied to the profile's `### demographics` block, researched, and measured against the brand's own creators |
| `ad-frameworks.json` | **the second door.** Assembled frameworks — an ad's plan, chosen rather than read off a swipe — each row naming its sections, in order, with the technique that builds each one and the scene shape that beat takes |
| `SCHWARTZ.md` | the human-readable doctrine, in our words, in chain order — for people, not machines |
| `slices/*.md` | one rendered block per framework, which is what a prompt actually binds. **Never hand-edited** |
| `render.py` | renders every slice from the JSON; `--check` fails if a slice on disk has drifted |
| `lint_prompts.py` | the pronoun gate, usable from any machine's test suite |
| `test_doctrine.py` | the declared test — counts, ids, pointers, idempotence, lint |

The book itself is in the repo at `components/marketing-doctrine/source/breakthrough-advertising-eugene-schwartz.txt` (the owner's ruling, 2026-09-18: "put the book in the repo too"); every `[L####]` pointer below is a line number in that file.
never committed — it is a copyrighted book. The `[L####]` pointers exist so a
claim can be checked against it in seconds. Nothing is copied out of it; quotes
stay under 12 words.

## The one rule

**A machine reads its frameworks from here and never restates them in a
prompt.** The moment a stage re-types the five awareness levels in its own
words, there are two doctrines, and the second one drifts silently. A prompt
binds the slice by path; the words arrive at run time.

Corollary: a framework changes in `frameworks.json`, then `render.py` runs.
Editing a slice by hand is the same defect in miniature — the next render
erases it.

## Binding a slice

The var resolver already takes a repo path, so a stage binds a slice with zero
code change. The variable names are fixed and mean the same thing in every
lane (lane doctrine §2, one vocabulary):

| Variable | Slice |
|---|---|
| `{desire_dimensions}` | `components/marketing-doctrine/slices/desire.md` |
| `{awareness_levels}` | `components/marketing-doctrine/slices/awareness.md` |
| `{sophistication_stages}` | `components/marketing-doctrine/slices/sophistication.md` |
| `{techniques}` | `components/marketing-doctrine/slices/techniques.md` |
| `{sections}` | `components/marketing-doctrine/slices/sections.md` |
| `{mood}` | `components/marketing-doctrine/slices/mood.md` |
| `{verification}` | `components/marketing-doctrine/slices/verification.md` |
| `{offer_close}` | `components/marketing-doctrine/slices/offer-close.md` |
| `{research_questions}` | `components/marketing-doctrine/slices/research-questions.md` |
| `{ad_frameworks}` | `components/marketing-doctrine/slices/ad-frameworks.md` |
| `{delivery}` | `components/marketing-doctrine/slices/delivery.md` |
| `{spoken}` | `components/marketing-doctrine/slices/spoken.md` |
| `{emotion}` | `components/marketing-doctrine/slices/emotion.md` |

Three more names travel with them and are NOT served from here: `{research}`
(the run's own gathered answers), `{spice_sheet}` (the creative pass's
output) and `{voiceprint}` (the brand's measured creator voiceprints,
`brands/<brand>/creators/VOICEPRINTS.md`, bound as `~voiceprint` and
`[UNFILLED]` for a brand with none). They are listed so nobody mints a
second name for any of them.

## The taste layer — delivery.json

the owner's ruling, 2026-09-18: *"at the spice level — do we have levels of
humor, delivery styles? I want to get deeper into taste and actual
creativity with delivery."*

The sections say what an ad argues and the techniques say how the argument
is built. `delivery.json` says how it is **performed** — six dials, each
with its allowed values, and each value carrying four things a direction
is useless without: what it does, when it fits (levels, sections, formats),
its risk, and the receipt it needs.

| Dial | Values |
|---|---|
| `humor` | none · dry · wry · self-deprecating · observational · absurd · broad |
| `delivery_style` | deadpan · confessional · teacher-explainer · rant · storyteller · hype · plain-testimonial · deadly-sincere · understatement · interview-consult · reaction-duet · hands-and-voiceover |
| `register` | staccato-urgent · plain-flat · warm-unhurried · clinical · playful · intimate-low |
| `pacing` | fast-open-slow-body · escalating · one-breath · beat-and-pause · list-stack |
| `reference_world` | laugh-at · trust · watch · quote · look · sound |
| `avoid` | cringe-register · ad-voice-tells |

Three rules travel with it and none of them is negotiable:

- **Receipted to the avatar's own world, never the writer's taste.** A dial
  with no receipt sits at its plain default and the direction it would have
  supported is cut — the same gate the spice pass already applies to every
  other item. Taste that arrives from the writer reads as craft and is
  preference, and nobody downstream can tell which it was.
- **A reference is never a voice.** `reference_world` names a direction for
  timing, cadence and world — never a likeness, never a sound. The voice is
  always a cast voice, cloned then adjusted, rights on file.
- **Humor never sits over a claim.** It stays out of the proof and offer
  beats unless the room itself jokes there. The twist beat may be the
  product doing its job, shown, not claimed, and a plain beat with the
  proof always follows it.

The humor rules, ruled by the owner 2026-10-06 ("All six", on the humor
research):

- **A planted joke comes from the room.** A straight source may take one only
  when the culture read or the avatar's culture map shows this audience already
  laughs at that meme, format or reference. The receipt is named. A joke the
  writer invented is still a finding.
- **The problem may be a character.** The spot, the breakout, the stubborn
  stain, cast as a PERSONIFIED PROBLEM: the problem given a face, not a new
  person. Always the villain or the fool, never the customer.
- **The humor rung.** 0 straight · 1 problem only · 2 product as a prop · 3
  product is the punchline · 4 full ad wearing the meme. **0 is the default**
  (the owner, later the same day: "not every ad is funny"). A piece leaves 0 only
  when the swipe itself is funny, or the culture read names a meme or format
  this audience already laughs at and the problem fits in it. Rung 1 and 2
  pieces are organic posts and may carry no product. Rung 3 and 4 are ads.
- **Culture is the foundation; humor is one use of it.** Each avatar has a
  culture map, `core-avatars/<avatar>/culture-map.md`: what they watch, who
  they trust, their references and slang, what they care about, what they
  laugh at, what is off-limits. Its humor section counts as the RQ-17 receipt
  until the avatar's own research replaces it. The culture read tags every
  reference by what it does: laugh · trust · belonging · nostalgia ·
  aspiration · authority · relief · rebellion.

Where Schwartz names a row it carries the pointer — camouflage
`[L5436-5661]` for the styles that hide the gear change, mood
`[L6260-6361]` for the registers, identification `[L3253-3872]` for the
reference world. Everything else is craft, marked `source: "craft"`, and
carries no pointer it has not earned.

Five research questions feed it — `RQ-17` to `RQ-21` in `frameworks.json`:
who they laugh at, who they trust, what they watch and quote and wear, how
the room itself talks, and what makes them cringe. Two new language tags
carry the answers, `taste` and `cringe` (`brands/language-schema.md`).

## The spoken layer — spoken.json

the owner's ruling, 2026-09-19: *"humans don't use em dashes when speaking —
trigger deeper research on actual English-speaking human speech patterns
and round up levels of colloquialisms that we can use per sub-avatar as
well to ensure we are matching the delivery of these voices precisely."*
Measured the same day: a paragraph written with em-dashes was read by the
voice model with 1.3–1.7 s of silence at every dash; a 7 s paragraph took
11 s. The copy was written as prose and read as prose.

`spoken.json` is what turns a paragraph written for the eye into one
written for the mouth, and it is bound as `{spoken}` by the spice pass
(which writes THE SPOKEN SCRIPT) and the AI brief (whose `voice` field IS
that script's paragraph, never re-flattened). Five parts:

| Part | What it is |
|---|---|
| `written_vs_spoken` | the rules — no em-dash, no semicolon, no parenthesis, no ellipsis, one idea per sentence, fragments allowed, contractions on, a pause is a full stop or a comma, direct address, questions to the viewer, one restart, fillers at the start of a thought — each with its receipt URL |
| `levels` | the colloquialism dial: `0 plain` · `1 conversational` · `2 casual` · `3 slang` · `4 in-group`, each with what it allows, a structural pattern, where it fits, and its receipt rule. **Level 3 and above is quoted from the room's own rows, never invented.** Level 4 never sits on a claim |
| `register_recipes` | per delivery style: sentence length, filler set, pause density, question use, restart, levels, words per minute, and the `eleven_multilingual_v2` `voice_settings` range (stability · style · speed) inside the model's stated limits |
| `punctuation_map` | what each mark does on the voice model and what the take does with it. `voice.py`'s `for_reading()` reads the `take` column, so the safety net for older briefs is data, not code; the brief's gate refuses every mark whose take is `replace` |
| `demographic_bands` | how colloquialism differs by age band, region and language community — as options keyed to the profile's `### demographics` block, each band's markers researched with sources, and each pointing at the brand's own measured creators |

**Our creators outrank the web.** `components/research-gatherer/
research_gatherer/voiceprint.py` (`gather.py voiceprint --brand B --all`)
measures every selected creator post off its own audio — words per minute,
sentence length, fragment rate, contraction rate, marker inventory,
openers, sign-offs, questions, pauses, energy, in-words with receipts — and
writes `brands/<brand>/creators/<handle>/voiceprint.{json,md}` plus the
roll-up `VOICEPRINTS.md` keyed per avatar. Where a band has a measured
creator, that measurement is the band; the web sources are the frame.

Three research questions feed it — `RQ-22` to `RQ-24`: how the room phrases
things out loud, what it calls things, how it reacts — under the tags
`in-word`, `subculture`, `community-voice` and `taste`, and a `spoken` key
in both `language.py` STAGE_USE maps.

## The emotional layer — emotion.json

the owner, 2026-10-13: *"let's install a full map proper fundamentally in the
system similar to the marketing doctrine."* The sections say what an ad
argues, the techniques how it is built, the dials how it is performed;
`emotion.json` says what each beat must make the viewer **feel**. A director
plans a commercial this way: the feeling first, the picture second.

| Part | What it is |
|---|---|
| `feelings` | the 15 words a beat's feeling is spelled in — curiosity · surprise · recognition · frustration · unease · empathy · amusement · relief · hope · desire · trust · belonging · satisfaction · urgency · calm — each with what on screen makes it, where it fits and its risk |
| `intensity` | 1 trace · 2 noticed · 3 felt · 4 strong · 5 the peak (exactly one beat) |
| `points` | open · low · turn · peak · end — the five every map names |
| `arcs` | dip-and-rise · steady-climb · reveal · held-warmth · contrast, each tied to the ad frameworks it fits |
| `carriers` | the director's levers: performance, framing, camera move, light and colour, sound, cut rhythm, the held beat, words and voice |
| `map_format` | the exact block a stage prints |

**Where it runs.** Stage 1c (doctrine read v5) reads the swipe's map and files
it in `doctrine.json` as `emotional_map`; the element library carries the
feelings and arcs (`emotion/feeling`, `emotion/arc`) and the elements check
records any unknown one. The script step (injection v23) keeps it — a
`Feeling:` line on every scene, the five points on the same beats, and a
feeling that cannot be kept is a structure question. The AI brief (v28)
spells every scene's `emotion` from it and names the piece's `arc`.

**The rule that outranks the rest:** the map is read off the swipe and kept;
where the swipe breaks a rule, the swipe wins. Receipts: Fredrickson &
Kahneman 1993 (peak-end), Teixeira, Wedel & Pieters 2012 (emotion and
attention in video ads), Reagan et al. 2016 (emotional arcs), McKee 1997 (a
scene turns), Binet & Field 2013 (emotional advertising and long-term effect).

## The second door — ad-frameworks.json

the owner's ruling, 2026-09-18: *"with all of the different sections we should
begin to assemble actual frameworks to create ads strategically. We use
swipes as the baseline, but since we have a fundamental system and
understanding of who we are speaking to and how and what formats they're
receptive to, we can pump out mounds of video and photo ads."*

`frameworks.json` is read for a swipe; `ad-frameworks.json` is read to
COMPOSE one. Each row is a framework expanded to full per-section shape —
`{id, name, what, sections: [{id, technique, shape}], awareness: {entry,
exit}, sophistication, formats_fit, source, status, ref}` — where every
section id is a section `frameworks.json` still carries and every technique
is one of the seven. A framework is a PLAN, never a law: the market state
outranks its order, and a section the chosen awareness level does not call
for is dropped, with the drop stated.

Two ways a row gets here:

- **Seeded** — the eight `frameworks_crosswalk` rows in `frameworks.json`,
  expanded to full shape by hand. `source: "seed — crosswalk row <name>"`.
- **Promoted** — `python3 components/video-teardown/machine/framework_bank.py
  --promote <run-label>` copies the framework a run OBSERVED (its
  `doctrine.json`) in as a new row, `status: "seed"`, `source: "observed —
  <label>"`. **Run this only on the owner's own word.** This file is curated
  doctrine; the framework bank is a compiled projection of runs, and a bank
  row walking in unasked is how the two stop being different things.

Only the owner moves a row's `status` from `seed` to `proven` — after the ads it
produced were judged. No coined names anywhere in this file: a promoted row
takes its crosswalk row's name or a plain description, never an invented one.

`components/video-teardown/machine/compose.py` is the consumer — `plan` /
`run` / `grid` open a run on the FRAMEWORK lane from a chosen `{avatar,
awareness, format, framework}`, with no swipe and no model call until every
stage resolves. See `components/video-teardown/machine/README.md` ("The
second door") and `prompts/README.md` ("Stage 2f") for the chain side.

Each slice is self-contained — it names the variable it is bound as, states its
own rule, and needs no other slice to make sense — so a stage binds only the
block it needs and the token cost stays flat.

## Running it

```
python3 components/marketing-doctrine/render.py            # rewrite every slice
python3 components/marketing-doctrine/render.py --check    # fail if a slice drifted
python3 components/marketing-doctrine/lint_prompts.py <files...>
python3 components/marketing-doctrine/test_doctrine.py
```

`lint_prompts.py` exits 1 and prints `file:line:col` for every generic gendered
pronoun outside a fenced block or double quotes. A generic person is "the
viewer", "the avatar", "the speaker", "they" — a gendered pronoun narrows an
agnostic system to one reader for no reason. Any chain can add the linter to
its own test suite over its own current prompt files; stdlib only, no
dependency, no network.

## New-resident checklist (components/CLAUDE.md, ruled 2026-09-01)

Answered here rather than in a CLAUDE.md because the contract fixes this
component's file set.

| question | answer |
|---|---|
| **engine + owner** | `render.py` + `lint_prompts.py` — two stdlib scripts, no state, no credential. Shared engine; the owner's chain is the first caller |
| **definitions + curator** | `frameworks.json` — **the owner curates.** It is doctrine, so a change to a framework is a ruling, not a maker's judgment. The line pointers are the audit trail |
| **the plane it emits** | **none — `slices/` is a rendered projection of the definitions, not a run record.** Nothing here writes outside this folder and there is no run to file |
| **what the manifest declares per entry** | every row carries `ref` (its `[L####]` pointer), and every technique additionally carries `when`, `owning_stage`, `research_question` and `scene_shape`; every research question carries `framework`, `tags` and the `stages` it feeds |

## Kill-condition

If prompts start restating frameworks inline again — two doctrines, drifting —
the slices are too coarse or too expensive to bind, and the split gets fixed
here rather than worked around there.

## How a composed workflow pulls a slice (chain-runner)

The OS composes workflows by pulling components into chains. A person's
machine binds a slice by repo path in its stage vars (above). A
`components/chain-runner` chain takes inputs only as run-config values, so
there the slice enters as `@config.<var>` with the slice's TEXT as the value —
the caller reads `slices/<name>.md` and passes it with `--var` or in
`--config`, the same way it passes the avatar or the language bank. Nothing in
the runner names this component; it is one more content input. The runner's
own `chains/video-teardown/` is a snapshot of the teardown prompts at a recorded
sha and picks up new prompt versions and the doctrine inputs when its owner
resyncs it.
