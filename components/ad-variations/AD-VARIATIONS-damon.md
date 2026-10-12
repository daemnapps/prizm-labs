# Ad Variations (damon)

Markdown mirror of the Ad Variations page. Rebuilt by `components/ad-variations/machine/page.py`.

## How it works

- **Variable Index** (index) — Every teardown the brand has, counted. _rule reads + a Sonnet coder per post, cached._
- **Measure** (stage0) — The file's own clock: cuts, loudness, fps. _ffmpeg — no model, $0._
- **Anatomy → elements** (stage1) — The ad by the second, on nineteen fixed elements. _Claude Opus._
- **Locks vs levers** (stage2) — Keep or test each element, ranked by estimated impact. _Claude Opus · numbers from the index._
- **Variation matrix** (stage3) — N variations, one lever each, highest impact first. _Claude Opus._
- **New formats** (stage4) — Proven parts recombined into formats not yet run. _Claude Opus._
- **Merge recipe** (stage5) — Seconds reused, what AI makes, route — the machine prices it. _Claude Opus · $ from routes.json._
- **QC gates** (stage6) — The gates each variation must pass. _Claude Opus · forced gates from routes._
- **Congruence** (stage7) — The static and page section each variation feeds. _Claude Opus._



## Test runs


## Variable Index


## Against the hand-made spec

The first prompts found the elements and the corpus numbers, but locked too much, bundled several changes into one variation and read the sound wrong. Three passes later the automatic plan covers seven of the hand spec's ten levers (not the problem line, the demo bodies or the pitcher swap) with the same structure (a paid base plus one-lever variations, cast from the roster), finds the music bed and the reveal hit, and finds post #3 as the same template. What it still cannot do is see the frames: the picture for each beat comes from the teardown record, so it cannot spot reused footage the way the hand spec did.

| What | Hand-made | Automatic, first prompts | What changed | Automatic, after |
|---|---|---|---|---|
| Cuts and beats | 12 beats from ffmpeg scene detection — hard cuts at 2.13, 4.09, 6.34, 6.97, 9.93, 10.80, 11.64, 14.89, 16.02 s and a dissolve at 13.37 s; a thumbnail on every beat. | 10 hard cuts measured — every hand-spec hard cut except 4.09 (found as a soft change) and the 13.37 dissolve, plus one at 0.46 s. Pictures come from the record: 6.34–6.97 s was placed in the store aisle, where the hand spec shows the in-stitch payoff. No thumbnails. | Stage 1 v2 is told it cannot see: never move a picture across a measured cut the record does not support; mark uncertain placement. | Same cuts; the 6.34–6.97 s picture is still read from the record. Seeing frames needs a vision step — not built. |
| Sound | Music stem: a quiet bed 7.0–10.8 s, near silence 11–14 s, the loudest hit of the video at 14.5–15.5 s on the reveal. | Mix loudness only — concluded there was no music bed. | Stage 0 now separates the music stem on the local Demucs and measures it; stage 1 reads the stem before the record's Music line. | Bed found at 7.0–10.5 s and the hit at 14.5–15.0 s; the record's own contradiction (header says phonk, rows say none) is reported. |
| The brand's own test | Post #3 (9.4M) is the same template with a different reactor — the brand already moved the reactor and went 9.4M → 16.4M. The hook's background is post #6's footage. | Not found. | A computed 'closest posts' table — same values on what a viewer sees and hears, the same first line or sticker wording counted four times — goes to stages 2 and 3. | #3 is the closest post (73%), with #10 (the same 'heck is that' opener) also listed. Reuse of #6's footage is not visible without frames. |
| Locks and levers | 10 ranked levers (reactor, sticker text, stitched clip, problem line, captions, end frame + paid ask, demo bodies, pitcher, SKU, benchmark line), 14 locks. | 7 levers. Locked the whole hook layout including who reacts, and locked captions, SKU, talent and end frame on corpus counts alone. | v2: call the parts (who reacts, the sticker words, the clip behind the PIP), call organic and paid separately, and a value everyone shares is not proof it works. That swung to 33 ranked levers, so v3: ten ranked levers, the rest 'later', the nineteen fixed keys only. | Ten ranked levers: the borrowed clip, the first line, who reacts, the PIP layout, the named public figure, product in frame one, the sticker wording, the dominant roll, captions, the product naming. |
| The variations | A paid base plus 10, each moving one lever; two reactor swaps cast from the roster (Marcus 29, Ray 61); captions; an offer end card; the King Set; faceless inserts; a motion-transfer pitch swap. | A control plus 10, but 8 of 11 changed three variables and two were really new formats. | v2/v3: at most two variables per variation, no format changes in the matrix, check the paid cut's needs (sound-off, 4:5, one offer), cast person-levers from the roster by name, and test a second hero SKU. | A paid base (4:5, captions, one offer) plus 10: new borrowed clip, new first line, Marcus as reactor, Omar as reactor, the benchmark swapped for a customer's own aspiration, product out of frame one, new sticker wording, the dominant roll, captions, the Vitals Set named early. Not planned: the problem line (the v2 run had it), faceless demo inserts, the motion-transfer pitch swap. Added that the hand spec did not have: the dominant-roll test and the product held out of frame one. |
| Cost of the set | $__ machine cost; $__ if the cheaper motion route passes; ≈15 h. | $__ ($__ with TEST routes), priced by the machine from routes.json. | Rates written into routes.json once; the model gives units only. | $__ on the locked routes — the two reactor swaps run on Genjutsu at ≈$__ each — or $__ when the TEST motion routes (Wan 2.2 Animate, Kling Motion Control) replace it; ≈18 h. |
| Gates | 8 gates, each tied to a check that exists (safezone.py, claimfix.py, syncheck.py, voice_qc.py, gates 4/5). | The same 8, with variation-specific pass lines; gates forced by the routes a recipe uses. | the owner's seam rule added (27 Sep): chained clips are made in order from the real last frame, a seams gate at every join (≤ ~2× the median frame step), an optical-flow bridge only as the fallback. | 9 gates; the seams gate is forced wherever a recipe chains generated clips. |
| the owner decides | 10 open calls (order, hero SKU, likeness, motion from a creator, voice cloning, the comment handle, 'Will Smith', the store shelf, the offer, organic vs paid). | 5 — the public figure, a real result vs the gag, the close's blame line, the close technique, the borrowed clip. | No prompt change aimed here. | 6, overlapping the hand spec on the borrowed clip, the public figure and the offer; adds the read style, the market stage and the signature neck asset. |
| New formats | Not in Asset 01's scope. | 5 per ad, each part an index value with its evidence, marked NEW — untested. | — | 5 per ad. |
| Time and spend to plan | A working session with frame pulls and hand analysis. | ≈20 minutes, ≈$__ of Claude per ad. | — | ≈20–25 minutes, ≈$__ of Claude per ad at list price; the Variable Index was $__ once for the 60 posts. |

## Every stage prompt, verbatim

### Variable Index — `prompts/stage-0c-coder/stage0c-coder-v1-damon.md`

````
You are coding one finished video teardown into fixed values, so that every
video a brand has posted can be counted the same way. You read; you do not
judge. Every example below is illustrative — none of it names a real brand.

Here is the teardown record (the objective record, the shot table, the
verbatim transcript, the voices):
{teardown_record}

Here is the replication spec written from it:
{replication_spec}

Here is the doctrine read, as filed:
{doctrine_json}

Here are the variables to code. Each line is `key — what it means — allowed
values`. For a categorical key, give one of the allowed values exactly as
written. If none fits, write `other: <two to four words>` — never force the
nearest value; a new value is how the list learns. For a numeric key, give a
number of seconds or a count, or `null` if the record does not show it. For a
text key, quote the record's own words.
{coder_vocabulary}

Rules:
- Read only what the record shows. If the record does not show a thing, the
  value is `null` and the evidence says "not in the record".
- Seconds come from the shot table's timestamps or the transcript's T-number
  times — never estimated from pacing prose.
- "Product" means the thing the video sells. A competitor's product in frame
  is not it.
- The lead is the person with the most screen time speaking; if nobody
  speaks, the person with the most screen time.

Return one fenced json block and nothing else:

```json
{
  "codes": {
    "<key>": {"value": <value>, "evidence": "<the row time or T-number and a few quoted words>"}
  }
}
```
````

### Anatomy → elements — `prompts/stage-1-elements/stage1-elements-v3-damon.md`

````
You are stage 1 of the ad-variations chain: ANATOMY → ELEMENTS. One proven ad
has already been torn down. Your job is to map it onto a fixed list of
elements, by the second, so every ad from any brand lands in the same shape.
You describe; you do not recommend. Every example in this prompt is
illustrative and names no real brand or product.

THE AD'S METRICS
{metrics}

THE TEARDOWN RECORD (objective record, shot table, verbatim transcript, voices)
{teardown_record}

THE REPLICATION SPEC (the reusable construct)
{replication_spec}

THE DOCTRINE READ
{doctrine_read}

THE AUDIENCE READ
{audience_read}

THE FILE'S OWN CLOCK (stage 0 — measured with ffmpeg and a music stem; no model)
{measurement}

You cannot see the video. The measurement gives you WHERE the cuts are and HOW
LOUD each half-second is; the record gives you WHAT is on screen. So:
- A measured cut that falls inside one record row splits that row's picture;
  a measured shot that spans several record rows merges them. Never move a
  picture across a measured cut the record's own times do not support — when
  you cannot tell which side of a cut a picture belongs to, say so in `why`
  and mark the beat's picture "from the record, placement uncertain".
- Sound comes from the measurement first. The music stem is the truth about
  music: where it is at or above −45 dB there is a bed or a hit, whatever the
  record's Music line says. Name the stem's loudest window and any window
  where the stem hits while the voice is silent — that is usually a planned
  sound hit on a reveal.

THIS AD'S VALUES IN THE VARIABLE INDEX (the shared vocabulary — id · name · value)
{ad_values}

THE FIXED ELEMENT LIST (key · name · the index variables it covers)
{element_list}

Do three things.

1. BEATS. Walk the ad beat by beat on the MEASURED shots when they exist (the
   record's rows when they do not). One beat per measured shot; merge only
   shots that are one continuous action. For each: start and end in seconds
   (two decimals, the file's clock), the section, what is on screen, the words
   (T-number and verbatim), the sound (mix and music stem — name the loudest
   and the quietest stretches, and where the music enters, drops and hits),
   and the share of the runtime the beat starts at, and an attention call: WON (the first
   beat that stops the scroll), HELD, RE-WON (a new cut, place, sound or
   register that re-earns attention), or CLOSE.

2. ELEMENTS. Fill every key of the fixed list — all nineteen, no more, no
   fewer. For each: what this ad does, in plain words, with the seconds; the
   variable ids it covers with this ad's value for each (copy the index value;
   if the index value is wrong for this ad — the measurement contradicts it,
   or the record contradicts itself — give the right one and say why in
   `note`); and `source`: record, measured, or both. Where an element is made
   of parts production could change separately (who is on screen, the words
   on a sticker, the clip behind a picture-in-picture, a public figure named
   in a line), list each part in `parts` with its own seconds.

3. RECORD VS FILE. List every place where the teardown record and the
   measurement disagree (a cut the record does not have, a music line the
   loudness contradicts, a speaker the voice card contradicts, a timestamp off
   by more than 0.3 s). State both sides; do not resolve them.

The json must parse. Inside any string value write quotation marks as curly
quotes (“ ”) or escape them (\"); a straight double quote inside a value
breaks the whole block.

Return one fenced json block and nothing else:

```json
{
  "beats": [
    {"n": 1, "start": 0.0, "end": 0.0, "section": "", "picture": "", "words": "", "sound": "", "attention": "WON | HELD | RE-WON | CLOSE", "why": ""}
  ],
  "elements": [
    {"key": "hook_visual", "what": "", "seconds": "0.00–0.00", "variables": {"V-hook.01": ""}, "source": "record | measured | both", "note": "",
     "parts": [{"part": "", "seconds": "", "what": ""}]}
  ],
  "record_vs_file": ["the record says … ; the file shows …"]
}
```
````

### Locks vs levers — `prompts/stage-2-locks/stage2-locks-v3-damon.md`

````
You are stage 2 of the ad-variations chain: LOCKS VS LEVERS. Every element of
one proven ad is on the table below. For each one, say whether it is a proven
LOCK (keep it exactly) or a LEVER (a variation may move it), and rank the
levers by estimated impact. Every example here is illustrative.

THE AD'S METRICS
{metrics}

THE ELEMENTS (stage 1)
{elements}

THE EVIDENCE — computed by the machine from the brand's whole teardown corpus
(the Variable Index), not by a model. For each variable: this ad's value, how
many of the brand's posts share it, the share of all views and saves those
posts hold, their save rate against the rest, and the index's lock/lever
tendency.
{evidence}

THE CLOSEST POSTS IN THE BRAND'S OWN CORPUS — computed: the posts that share
the most of what a viewer sees and hears with this ad, their views, and every
variable they differ on. A near-twin that differs on one or two variables is
the brand's own half-run test of those variables: if its views differ a lot,
those variables have been seen to move results.
{siblings}

THE BRAND'S RULES (position, story, likeness, compliance)
{brand_rules}

Call the PARTS, not only the elements. Where stage 1 split an element into
parts (who reacts, the sticker's words, the clip behind a picture-in-picture,
a named public figure), give each part its own row: the layout can be a lock
while the person in it is a lever.

Call it twice when the cuts differ. The brand's corpus is organic posts. A
paid cut plays muted by default, is cropped to 4:5, and has to carry an
offer; an element that is a lock for the organic cut can be a lever for the
paid cut (captions, the end frame, the ask, a subject outside the 4:5 zone).
Say which cut each call is for: `cut` = both, organic or paid.

The element key is always one of the nineteen keys in the elements above.
A call about order, awareness or framing goes under the nearest key
(problem_line, ask_placement, camouflage) with the part named.

How to call it:
- LOCK when the corpus shows the brand's top posts converge on this ad's value
  (tendency lock-leaning) AND no near-twin moved results by changing it, or
  when changing it would break what the replication spec marks load-bearing,
  or when a brand rule fixes it.
- LEVER when the top posts vary on it; when a near-twin differs on it and its
  views differ (quote the twin's rank and views); when this ad's value
  conflicts with the audience read or a brand rule; or when the paid cut
  needs it moved. A value the whole corpus shares is not evidence that it
  works — only that nothing else was tried; say so rather than calling it a
  lock on count alone.
- Evidence is quoted ONLY from the evidence table and the records above —
  numbers exactly as given, with the variable id. Never invent a number.
- Rank the ten levers with the highest estimated impact, 1 to 10. Every
  other lever keeps `impact_rank` null and `impact` "later" — it is still a
  lever, just not in the first set.
- Nothing in the corpus isolates one variable at a time. The impact rank is
  therefore an ESTIMATE, and says what it weighs: how much of the first three
  seconds the element controls, whether the brand's posts show it moving
  results, and what it costs to test (cost class from the evidence table).
- If a lever needs a ruling before it can move (a real person's likeness, a
  voice clone, a public figure, a claim), name the ruling in `needs_ruling`.
  Do not decide it.

The json must parse. Inside any string value write quotation marks as curly
quotes (“ ”) or escape them (\"); a straight double quote inside a value
breaks the whole block.

Return one fenced json block and nothing else:

```json
{
  "calls": [
    {"element": "hook_visual", "part": "who reacts | null", "cut": "both | organic | paid", "call": "LOCK | LEVER", "variables": ["V-hook.07"], "what_this_ad_does": "",
     "evidence": "V-hook.07 comment-reply: 17 posts, 41.3% of views, save rate 0.85% vs …",
     "needs_ruling": null, "impact_rank": null, "impact": "high | medium | low | null",
     "impact_basis": "ESTIMATE — …"}
  ],
  "lever_order": ["element keys, highest estimated impact first"],
  "damon_decides": ["a question only the owner can answer, with the fact that raises it"]
}
```
````

### Variation matrix — `prompts/stage-3-matrix/stage3-matrix-v3-damon.md`

````
You are stage 3 of the ad-variations chain: THE VARIATION MATRIX. From one
proven ad's locks and levers, plan {n} variations. Each changes ONE lever — at
most two index variables, and two only when they cannot move apart — so every
result stays readable against the original. A variation that changes three
variables is two variations. New formats are the next stage's job: nothing
here changes the ad's format, framework or structure. Every example here is illustrative.

THE AD'S METRICS
{metrics}

THE ELEMENTS (stage 1)
{elements}

THE LOCKS AND LEVERS (stage 2), with the lever order
{calls}

THE CLOSEST POSTS IN THE BRAND'S CORPUS (computed)
{siblings}

THE AUDIENCE READ (who the ad speaks to, and how our audience differs)
{audience_read}

THE AVATARS AND SUB-AVATARS
{avatars}

THE CUSTOMER'S OWN WORDS (any new line, sticker or caption is taken from here
verbatim, with its id)
{language}

THE CAST WE MAY USE (synthetic, cleared) 
{cast}

THE PRODUCTS
{products}

THE BRAND'S RULES
{brand_rules}

Rules:
- Start with V00, the CONTROL: the original rebuilt only as much as paid
  placement needs (safe zones, a clean plate). Every variation is read against
  it. If the original needs no rebuild, V00 is the original as-is.
- Then V01…V{n}, highest estimated impact first, following the lever order —
  cheaper tests of an equal lever go first. Cover the levers, not one lever
  many ways: no two variations move the same variable unless they aim it at
  different sub-avatars (two different cast members for the same person-lever
  is the one common case).
- Check the paid cut's needs before planning: sound-off viewing (captions),
  the 4:5 zone, one offer and one button at the end, the hero SKU. Each need
  the original does not meet is a lever and gets its own variation.
- Read the products: when the brand names more than one hero SKU and the ad
  shows only one, one variation tests the ad on another hero, and says which
  lines stay true.
- A person-lever (who reacts, who pitches, who demonstrates) is cast from the
  cleared cast list above by name, matched to a sub-avatar. A real
  creator's or customer's likeness is never regenerated — it goes in
  `needs_ruling`.
- Each change is written against the Variable Index: variable id, from (this
  ad's value), to (the new value). A change with no variable id is not
  allowed; if the lever has no index variable, use the closest id and say so.
- New words are verbatim from the customer's words above, with their ids. If
  nothing there fits, write [BANK LINE NEEDED: what it must say] — never
  invent customer language.
- A variation that needs a ruling (a real person's likeness, a cloned voice, a
  public figure, a retail claim) says so in `needs_ruling` and still gets
  planned; the ruling is the owner's.
- Name the avatar and sub-avatar each variation is aimed at, and whether it is
  a paid cut, an organic cut, or both.
- Hypotheses are INFERENCE: say what result would confirm or kill each one.

The json must parse. Inside any string value write quotation marks as curly
quotes (“ ”) or escape them (\"); a straight double quote inside a value
breaks the whole block.

Return one fenced json block and nothing else:

```json
{
  "variations": [
    {"id": "V00", "title": "", "kind": "control | variation",
     "changes": [{"variable": "V-hook.11", "element": "on_screen_text", "from": "", "to": "", "bank_ids": []}],
     "locked": ["element keys that must not move"],
     "hypothesis": "INFERENCE — …", "confirms_if": "", "kills_if": "",
     "audience": {"avatar": "", "sub_avatar": "", "cut": "paid | organic | both"},
     "order_reason": "", "needs_ruling": null}
  ]
}
```
````

### New formats — `prompts/stage-4-formats/stage4-formats-v2-damon.md`

````
You are stage 4 of the ad-variations chain: NEW FORMATS. The brand's whole
corpus has been counted into the Variable Index. Recombine elements the corpus
already proves into formats this brand has NOT run — for example the hook of
one family with the proof structure of another. Every example here is
illustrative.

THE SOURCE AD'S ELEMENTS (stage 1)
{elements}

THE PROVEN VALUES, family by family (from the Variable Index — the brand's
posts, weighted by views and saves)
{index_summary}

THE COMBINATIONS THE BRAND HAS ALREADY RUN (hook sub-type × proof type ×
format, with post counts and view share). A format that appears here is not
new.
{combos}

THE AVATARS
{avatars}

THE BRAND'S RULES
{brand_rules}

Propose {k} new formats. For each:
- a short name and one line on what the viewer sees;
- its parts: at least three, each a Variable Index id with a value the corpus
  shows, and that value's evidence exactly as the index gives it (posts, view
  share, save rate);
- `status`: always "NEW — untested". The combination has not run for this
  brand; say which existing combination it is closest to;
- why it might work, labelled INFERENCE;
- what owned footage could seed it (a post rank or id from the corpus, and the
  seconds, when the parts already exist on film), and what would have to be
  made;
- the avatar and sub-avatar it is aimed at.
Do not propose a combination listed as already run. Do not use a value the
index does not show.

The json must parse. Inside any string value write quotation marks as curly
quotes (“ ”) or escape them (\"); a straight double quote inside a value
breaks the whole block.

Return one fenced json block and nothing else:

```json
{
  "formats": [
    {"id": "F01", "name": "", "what_the_viewer_sees": "",
     "parts": [{"variable": "V-hook.04", "value": "", "evidence": ""}],
     "status": "NEW — untested", "closest_existing": "", "why": "INFERENCE — …",
     "seed_footage": "", "to_make": "", "audience": {"avatar": "", "sub_avatar": ""}}
  ]
}
```
````

### Merge recipe — `prompts/stage-5-recipe/stage5-recipe-v3-damon.md`

````
You are stage 5 of the ad-variations chain: THE MERGE RECIPE. For every planned
variation, say which seconds of the ORIGINAL footage are reused as-is and what
has to be made, on which production route, in what units. You do not price
anything: the machine multiplies your units by the route's rate. Every example
here is illustrative.

THE BEATS AND THE FILE'S CLOCK (stage 1 + stage 0)
{beats}

THE VARIATIONS (stage 3)
{variations}

THE NEW FORMATS (stage 4) — give a recipe for each too; seed footage first
{formats}

THE ROUTES YOU MAY NAME (id · what · unit · rate · locked or TEST)
{routes}

THE CAST WE MAY USE
{cast}

THE BRAND'S LIKENESS AND CLAIM RULES
{brand_rules}

Rules:
- Seconds are on the original's clock, two decimals, and land on measured cut
  points where one is near.
- Reuse first. Anything already on film is cut, not generated.
- Name a route only by its id from the list. Units match the route's unit:
  stills for gpt-image (rolls are added by the machine), seconds of finished
  clip for seedance-hf / wan-animate-fal / kling-mc-fal (overshoot is added by
  the machine), 4-second clips for genjutsu-hf, thousands of characters for
  elevenlabs-tts, jobs for local routes.
- Every AI video clip is followed by a local-interp job (de-duplicate,
  interpolate, conform to the master's frame rate).
- Where a TEST route could replace a locked route at lower cost, give it as
  `cheaper_test`: the route it replaces, the TEST route and its units —
  flagged TEST, never the default.
- Chained clips are made in order. When a variation joins two or more
  generated clips back to back (a morph, a change of person or outfit, one
  scene into the next), number them in `chain_order` and make them one after
  another: each next clip starts from the ACTUAL last frame pulled from the
  previous rendered clip — never from the original still it was aimed at.
  Start- and end-frame video models do not land exactly on the images they
  are given, so a join built from the stills jumps. Say which frame each
  chained clip starts from in `start_frame`.
- The fix for a join that still jumps is to make the next clip again from the
  real last frame. Only when it cannot be made again, name the repair in
  `seam_repair`: an optical-flow bridge across the last ~10 frames of one clip
  and the first ~10 of the next (local-interp). It is the fallback, never the
  plan.
- A generated before-and-after, a generated real customer, or a generated
  creator likeness is not made unless the brand rules above allow it; if a
  variation needs one, write it in `blocked_by`.
- List what is made once and used across the set, with the variations that use
  it, so it is costed once.

The json must parse. Inside any string value write quotation marks as curly
quotes (“ ”) or escape them (\"); a straight double quote inside a value
breaks the whole block.

Return one fenced json block and nothing else:

```json
{
  "recipes": [
    {"id": "V01",
     "reuse": [{"seconds": "0.00–6.97", "what": ""}],
     "make": [{"what": "", "route": "gpt-image", "units": 1, "shared": null,
               "chain_order": null, "start_frame": "the still S1 | the real last frame of clip 1 | null"}],
     "seam_repair": null,
     "cheaper_test": {"replaces_route": "genjutsu-hf", "route": "wan-animate-fal", "units": 0, "why": ""},
     "blocked_by": null}
  ],
  "shared": [{"key": "S1", "piece": "", "route": "local-matte", "units": 1, "used_by": ["V01"], "why": ""}]
}
```
In `make`, an item that is one of the shared pieces carries `"shared": "S1"`
and is costed only in `shared`.
````

### QC gates — `prompts/stage-6-gates/stage6-gates-v3-damon.md`

````
You are stage 6 of the ad-variations chain: QC GATES. Each planned variation
must pass the gates that apply to it before it ships. Write, per variation,
which gates apply and the pass line for THIS variation — what exactly is
checked, on which seconds. Every example here is illustrative.

THE VARIATIONS AND THEIR RECIPES (stages 3 and 5)
{variations}

THE GATES (id · what passes · the automatic check that exists today)
{gates}

GATES THE MACHINE ALREADY FORCES (from the routes each recipe uses — keep
every one of these)
{forced}

THE BRAND'S RULES
{brand_rules}

Rules:
- Keep every forced gate. Add any other gate the variation needs; say why.
- "Doesn't look like an ad" applies to every cut meant to pass as native
  content.
- The pass line names the seconds and the thing checked ("the new reactor's
  face in 0.00–6.97 matches his cast sheet"), not the gate's general wording.
- Every join between two generated clips (items with a `chain_order`) gets
  the seams gate, with its pass line naming the join: the frame-to-frame
  change across the cut stays within about twice the clip's own median frame
  step. Say which clips meet at which second.
- If no automatic check exists for something that must be checked, say
  "manual" and what a person looks at.

The json must parse. Inside any string value write quotation marks as curly
quotes (“ ”) or escape them (\"); a straight double quote inside a value
breaks the whole block.

Return one fenced json block and nothing else:

```json
{
  "gates": [
    {"id": "V01", "apply": [{"gate": "safe-zones", "pass_line": "", "check": "automatic | manual"}]}
  ]
}
```
````

### Congruence — `prompts/stage-7-congruence/stage7-congruence-v2-damon.md`

````
You are stage 7 of the ad-variations chain: CONGRUENCE. Each planned
variation's hook has to carry through to the static ad and the landing-page
section that inherit it. List them — do not write them. Every example here is
illustrative.

THE VARIATIONS (stage 3)
{variations}

THE STATIC FORMATS THE ELEMENT LIBRARY HOLDS
{static_formats}

THE PAGE FORMATS THE ELEMENT LIBRARY HOLDS
{page_formats}

THE BRAND'S FUNNELS AND ANY CAMPAIGN PLAN SUPPLIED FOR THIS RUN
{funnels}

For each variation: one static format (by the library's id) and what carries
over word for word or frame for frame; one landing-page destination (a page
format id, and a section of the campaign plan when one is supplied) and what
carries over. If the plan names no page, say "page not on file" rather than
inventing one.

The json must parse. Inside any string value write quotation marks as curly
quotes (“ ”) or escape them (\"); a straight double quote inside a value
breaks the whole block.

Return one fenced json block and nothing else:

```json
{
  "links": [
    {"id": "V01", "static": {"format": "", "carries": ""}, "page": {"format": "", "section": "", "carries": ""}}
  ]
}
```
````

## How to run it on any ad

Say: “Run ad variations on <brand> post <id>.” The session checks the teardown exists, refreshes the Variable Index, dry-runs, runs the seven stages, and republishes the page. Anything under “the owner decides” waits for the owner.
