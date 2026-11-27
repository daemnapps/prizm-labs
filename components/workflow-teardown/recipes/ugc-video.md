# UGC Video

A 9:16 creator video: our own cast member talks to camera about a product (or tells a story with none), cut eight ways per clip from a storyboard sheet, speaking the avatar's words in a voice we own. Five other formats change the board, the creator and the clip prompt (see formats).

Higgsfield original: `ugc-video` · built from `sources/higgsfield/ugc-video/SKILL.md`, `sources/higgsfield/ugc-video/references/formats/review.md`, `sources/higgsfield/ugc-video/references/duration.md`, `sources/higgsfield/ugc-video/references/boards.md`, `sources/higgsfield/ugc-video/references/product-intake.md`, `sources/higgsfield/ugc-video/references/ugc-character.md`, `sources/higgsfield/ugc-video/references/monologue-craft.md`, `sources/higgsfield/ugc-video/references/ugc-board.md`, `sources/higgsfield/ugc-video/references/ugc-clip.md`, `sources/higgsfield/ugc-video/scripts/plan_duration.py.md`

## Price

| | |
|---|---|
| higgsfield | ≈490 credits plus the Soul creator picture (2 boards ≈4.5 + 2 cleanups 5 + 2 clips at 1080p 480) |
| house | ≈90 credits (2 Seedance 480p clips with our voice read, 45 each) + GPT Image boards and cleanups and the ElevenLabs read on metered keys (cents); banked creator 0; upscale free |
| cheap | ≈25 credits (2 Wan 3.0 480p clips with the read as audio reference 22.5 + Flare 1k boards 1.5 + Seedream Flash cleanups 1; banked creator, free local upscale): about a twentieth of Higgsfield |
| basis | 30 s review video = 2 clips of 15 s, 2 boards; prices quoted 2026-11-21 |

## Inputs

- **creator**: brands/<brand>/ai-cast/<name>/ masters (master-sheet.png); else runs/ai-elements/<brand>/casting/<role>/full/master.png
- **script words**: brands/<brand>/core-avatars/<avatar>/language/ (customers, evidence, churned: verbatim lines with source)
- **product** (optional): brands/<brand>/products/<product>/images/ (some brands keep brands/<brand>/products/images/<product>-*.jpg)
- **product facts and approved claims** (optional): brands/<brand>/products/<product>/product.md or brands/<brand>/products/<product>.md
- **voice**: brands/<brand>/ai-elements/voices.json (the creator's <sex>/<age band>/<ethnicity> row)
- **duration and angle**: the brief: brands/<brand>/briefs/briefs.json
- **house rules**: brands/<brand>/CLAUDE.md + brands/<brand>/rulings.md + the owner's hard rules (no disclaimers on screen, clothed cast, men never kiss or hug men)
- **site URL (website format only)** (optional): brands/<brand>/products/store.json site where present; any other site: no home yet
- **package picture (unboxing format only)** (optional): no home yet (a product image of the packed box, if one sits in the product's images/)

## Steps

### 0. Safety, truth and intake gate — `none`

Higgsfield's gate before any spend: an adult authorized creator, an allowed product, claims only from an allowlist, no fake testimonials; then one bundled question for duration and creator. Ours: the brief and lane.json answer every intake question, so nothing is asked.

| | model | credits |
|---|---|---|
| Higgsfield | the chat model directing the run | 0 |
| our house | brief + lane.json (owner's go and credit cap) + brands/<brand>/CLAUDE.md and rulings.md | 0 |

**Higgsfield, word for word**

```
## Safety and truth gate — before intake or generation

If any item below fails, do not generate and do not route around the gate:

- **Creator authorization:** use only a generated adult age 21+ or a consenting
  adult non-public person whose image the user is authorized to use. A supplied
  photo is not permission to impersonate its subject. If third-party consent is
  unclear, ask once; decline public figures, celebrities, minors, and deceptive
  identity use. Never clone or imitate a supplied person's voice.
- **Allowed promotion:** decline political persuasion and promotion of prohibited
  or age-restricted goods or services, including adult sexual content, products,
  or services; gambling; illegal or regulated drugs, drug paraphernalia, and
  prescription medication; tobacco or nicotine; weapons, explosives, or harmful
  materials; counterfeit or illicit goods; extremist goods; deceptive or
  high-risk financial services; malware or spyware; fraud; and covert
  surveillance. A neutral educational mention is not a product promotion and
  belongs outside this workflow.
- **Truthful claims:** `approved_claims` is the complete allowlist of product
  claims supplied by the user. Preserve each allowed claim verbatim; never
  strengthen, combine, infer, or derive another claim. With no allowlist, create
  claim-free copy about visible materials, controls, application, packaging, and
  other directly observable mechanics.
- **No synthetic testimonials:** a generated creator is a host or demonstrator,
  never a real customer. Do not invent purchase, ownership, use, results,
  before/after outcomes, ratings, reviews, social proof, relationships, or lived
  experience. First-person experience is allowed only when a consenting user
  supplies the exact script and confirms it describes their own experience.
- **Transparent framing:** describe product-present output as a brand demo,
  creator concept, or sponsored creative—not an organic customer review. When a
  post package is requested, include an appropriate ad/sponsorship disclosure.

## Phase 0 — Intake

After the safety and truth gate passes, parse an optional product photo or URL,
duration, creator photo or requested gender, and
explicit overrides for location, hair, ethnicity, outfit register, mood, props,
language, accent, music, `approved_claims`, and on-video text.

Classify specificity:

- `auto`: 1–5 words with no scenario; choose the complete treatment.
- `guided`: 1–3 sentences of tone or rough flow; preserve that direction.
- `director`: 4+ sentences, scenario, shot list, or location sequence; map the
  supplied beats one-to-one to slots.

Ask only for real gaps, bundled into one question: duration (offer 10s, 15s,
30s, 45s) and creator photo/gender when absent. Never ask for a product merely
because none was supplied; lock `product_reference:null` and
`product_description:null` and continue with creator-led, scenario-driven UGC. Include
an accent or physical quirk option only when the brief already signals origin or
deliberately unusual character energy. Never ask about locked models, aspect
ratios, boards, resolution, audio, batching, or identity training.

Do not start paid generation until the required creator input and duration are
resolved. The later text/post-package choice is the only sanctioned second ask.
```

**Ours**

```
Creator = our own generated adult cast member {creator_name} (brands/<brand>/ai-cast/{creator_name}/), never a real person. Product = {product} or none. Claims allowed = only these lines, verbatim: {approved_claims}; with none, say only what can be seen (materials, how it opens, how it is applied). The creator is a host, never a customer: no 'I've used it for weeks', no results, ratings or reviews unless the words are a real customer line from {language_folder} said as a quote. Duration {seconds} s, 9:16. {house_rules}
```

Check: lane.json carries the owner's go and a credit cap; claims list resolved; creator is an ai-cast master.

### 1. Duration plan and the price — `plan.quote`

Split the length into 4-15 s Seedance clips with no short tail (30 s = 15 + 15; 31 s = 15 + 12 + 4), then quote every picture and clip before the first paid call.

| | model | credits |
|---|---|---|
| Higgsfield | plan_duration.py in the sandbox; quotes via estimate_image_cost / estimate_video_cost | 0 |
| our house | same planner rule in the run folder; same quotes (they submit nothing) | 0 |

On this Mac: `python3 -c the planner (count = ceil(s/15), tail borrowed up to 4 s); ffprobe later for actual lengths`

**Higgsfield, word for word**

```
# Duration planning

Require an integer target duration of at least four seconds; do not silently round
or assume 15 seconds. Each Seedance clip is 4–15 seconds. In sandbox_exec create
an input JSON such as {"duration_seconds":31} in the task working directory and run:

```bash
python3 "${HF_WORKFLOWS}/ugc-video/scripts/plan_duration.py" --input output/ugc-duration.json
```

Use the returned clip_durations and clip_count for every board, script and request.
The planner preserves total duration with the minimum number of clips:
16 → 12+4; 19 → 15+4; 31 → 15+12+4; 46 → 15+15+12+4.
Tutorial has four global step slots per board. Website uses this same planner
without boards. Do not put Pi-only duration_policy fields into the MCP schema.
```

**Ours**

```
Target {seconds} s. Clips = {clip_durations} (planner: 15 s each, last clip at least 4 s). Quote one board, one cleanup and one clip per distinct length; add up; write total and cap into lane.json; stop for the go.
```

Check: Sum of clip_durations = target; total quote under the lane.json cap.

### 2. Product facts — `write.product`

One canonical product description, tier from packaging, category and the exact opening/use mechanic, plus the approved claims list. Skipped when the video has no product.

| | model | credits |
|---|---|---|
| Higgsfield | the chat model reads the photo or product page | 0 |
| our house | Claude on the plan, from brands/<brand>/products/ (product file + images) | 0 |
| cheapest | Claude on the plan (writing costs don't count) | 0 |

Cheap swap: Nothing lost: our product files already hold the real description and the label photos. Registry: claude-sonnet-5.

**Higgsfield, word for word**

```
## Phase 1 — Normalize the optional product

If a product photo or URL was supplied, read `references/product-intake.md` and
follow it exactly. Resolve once:

- `product_reference`: confirmed attachment or imported HTTPS image `media_id`;
- canonical `product_description`;
- `tier`: `luxury`, `premium`, or `drugstore` from visual packaging cues only;
- `category` and exact usage/opening mechanic.
- `approved_claims`: exact user-supplied strings, or an empty list.

Reuse those values verbatim downstream. Never infer price, invent claims or
creator experience, or
replace a blocked/thin product page with a stock or generated product. If no
product was supplied, skip the reference, keep both product fields null, and
use the no-product branches in `ugc-board.md`, `ugc-clip.md`, and monologue craft.
```

**Ours**

```
product_reference = {product_image} (real label photo, front). product_description = {product_description}. tier = from the packaging only. category = {category}; opening/use mechanic = {mechanic}. approved_claims = {approved_claims} (verbatim, or empty).
```

Check: Reference is a real photo of our product, never generated; label readable.

### 3. Lock the creator — `pictures.cast`

One creator picture that seeds every board and clip. Higgsfield generates a fresh Soul 2 selfie; we use our banked ai-cast master so the same face runs across ads.

| | model | credits |
|---|---|---|
| Higgsfield | soul_2, 3:4, 2k | not quoted (re-quote before a run) |
| our house | banked master from brands/<brand>/ai-cast/<name>/ (0); a new cast member only through the casting chain, GPT Image 2.5 (gpt-image-2.5) | 0 banked |
| cheapest | banked master (0); a missing one: GPT Image 2.6 Flare 1k low (gpt_image_2_6_flare) | 0 banked; 0.75 for a gap |

Cheap swap: A banked master costs nothing and keeps one face across every ad; Flare at 1k low is softer and needs the cleanup pass. Registry: missing.

**Higgsfield, word for word**

```
A [age band from Variety pool] [man/woman], [expression — pick one from the Approved mid-action expressions list], [hair color + length from Variety pool], [build vibe], with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a [specific location with architectural details].
[Light direction and quality — MUST be cool/neutral daylight, NEVER golden hour, NEVER warm sunset, NEVER orange/amber cast] falls across her face — neutral, clean, no warm cast, no retouched glow. Skin texture is real, with visible pores and natural unevenness.
[He/She] wears [outfit matching category × tier from the matrix — pick a non-default option from the matrix's list; a dressed option realizes as the Wardrobe Bank recipe — layered with the Universal modesty triplet and any per-garment specifics]. Body in a calm neutral pose — relaxed standing, one hand resting naturally.
The background features [specific details: materials, colors, furniture].
Color palette dominated by [space colors — keep neutrals; avoid amber/orange dominance].
Casual handheld iPhone selfie taken by [her/him] at arm's length — head and shoulders fill the frame, slight natural tilt, slightly off-center, intuitive composition, captured mid-moment. Subject in clear focus with the background naturally falling out as in any phone photo.
Shot on iPhone front-facing camera. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. No fisheye lens, no ultra-wide distortion. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.

Self-portrait selfie shot on iPhone front-facing camera held by the subject at arm's length — head and shoulders fill the frame, casual handheld framing, slight natural tilt, slightly off-center, slightly imperfect, not posed. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. No fisheye lens, no ultra-wide distortion. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

**Ours**

```
Use {creator_master} unchanged as character_media_id. Only if no master exists: A {age_band} {sex}, {expression}, {hair}, {build}, standing in {location}. Cool neutral daylight across the face; real skin texture with visible pores. Wears {outfit}. Calm neutral pose. Background: {background}. Casual handheld iPhone selfie at arm's length, head and shoulders fill the frame. No product in the picture.
```

Check: Same face as the cast sheet; adult; no product in frame; filed back to ai-cast if new.

### 4. Monologue — `write.script`

What the creator says, split into one segment per clip: a hook, a story shape, the avatar's own words, the anti-slop pass. Ours writes from the avatar's language bank instead of inventing lines.

| | model | credits |
|---|---|---|
| Higgsfield | the chat model | 0 |
| our house | Claude on the signed-in plan, from brands/<brand>/core-avatars/<avatar>/language/ | 0 |
| cheapest | Claude on the plan (writing costs don't count) | 0 |

Cheap swap: Nothing lost; spend nothing here. Registry: claude-sonnet-5.

**Higgsfield, word for word**

```
## Truth contract — mandatory for every run

The parent skill's safety and truth gate always applies. `approved_claims` is the complete claim
allowlist, including when it is empty. Never invent or imply purchase, ownership, use, results,
before/after outcomes, ratings, reviews, social proof, relationships, or lived experience.

- **Generated creator:** write a host/demonstrator script using observable product mechanics and exact
  allowlisted claims only. Never give the fictional creator a customer history.
- **Authorized user as creator:** first-person experience is legal only when the user supplied the
  exact first-person script and confirmed it is their own experience. Do not embellish it.
- **Productless mode:** fictional storytelling is allowed, but do not impersonate a real person or
  invent claims about a real person, organization, product, or service.
- Quoted lines and pattern examples below are structural examples, never factual source material.

**Productless mode:** when both product fields are null, the creator's topic, routine, experience,
or story carries the whole arc. Never invent a product, brand, review claim, product entrance, or
sales CTA. Ignore every product-entry, product-pressure, product-mechanic, and product-claim rule in
this reference; choose a story shape that works without an object and end on the human resolution.

## Voice archetype (a default, not a question — state it for veto)

Every video gets ONE performance persona that colours HOW the creator talks. It is picked from the
tier of the already-resolved register and NEVER changes that register. Resolve the register FIRST
(NATURAL by default; HYPED or CALM only on an explicit signal), THEN pick a persona from its tier:

- **NATURAL tier (the default — use unless a signal says otherwise):** a warm, genuine, engaged
  creator — girl-next-door / easy-going relatable / dry-witty. Lively and real, ONE honest
  human-scale peak (a real grin, a delighted "oh"), NEVER squealing or screaming. Beauty, fashion,
  and most briefs get THIS by default — not It-Girl.
- **HYPED tier (only on a hyped signal):** 2000s It-Girl (stretched vowels, squeals on the reveal),
  Hype Beast (explosive bursts), Drama Queen.
- **CALM tier (only on a calm signal):** Deadpan Contrast (flat, one micro-crack at the peak), quiet
  Gossip Whisperer, Southern Sweetheart (soft warm).

HARD RULE: under the NATURAL default the persona sentence carries NO energy words — never `squeal`,
`scream`, `stretched vowels`, `explosive`, `screaming`. Energy comes from the REGISTER; the persona
adds only attitude, melody, and cadence, never volume. Write the chosen persona as ONE sentence and
carry it verbatim into the character prompt, every board prompt, and every clip prompt — restated
each time, or it drifts. Archetype and accent stack independently.

## Accent and quirk (opt-in)

If the brief names an identifiable origin for the creator, or asks for "weird" / "viral" character
energy, offer it inside the single intake question (accent consent + one quirk). Never add an accent
the user did not approve; the default is neutral English with no quirk. If opted in, write the
persona/quirk sentence once (identity + attitude, e.g. "a young Korean it-girl — English is her
second language and you hear it in every sentence") and restate it verbatim everywhere downstream.
Text-only accent enforcement lands roughly one render in three: if the user can drop a 5-10s voice
sample, attach it to the clip generation as an audio reference ("accent and vocal delivery reference
only — do not copy words, only the accent, melody, and timbre"). Offer that once; never block on it.

## Story mode is the default

ONE scenario spans the whole video: situational stakes first, framed without claiming that a
generated creator really experienced them. If
a product is present, it enters as a SUPPORTING ACTOR at 40-60% of total runtime, mapped onto the arc roles —
stakes live in the HOOK board, the single "but then" twist opens the mid arc, and the CTA rides
INSIDE the closer's resolution, never as an outro beat. The story must survive with the product
deleted. Plain review structure only on explicit request.

**Story-shape menu — pick ONE spine (it decides WHAT happens; the hook pattern decides how it
OPENS). Brainstorm at least 3 candidates, then choose; combine two only if it deepens the gap
without clutter:**

- S1 Demonstration Discovery (problem appears → feature is demonstrated)
- S2 Mechanism Loop (open on an observable action, then show how it works)
- S3 Alternate Use (show a second visible use without claiming personal ownership)
- S4 Guided Comparison (compare only visible mechanics or exact allowlisted claims)
- S5 Behind-the-Concept (explain the creative or product setup without a testimonial)
- S6 Interrupted Storytime (a story about something else; the product interrupts, the story never
  quite finishes)
- S7 GRWM With Stakes (getting ready FOR a charged thing; the stakes carry it)
- S8 New-Place Mini-Vlog
- S9 Day-in-the-Life With a Twist
- S10 Product Reveal (clearly staged reveal, no claimed first reaction)
- S11 POV Frame (talks TO the viewer as a character)
- S12 Process Win (real work, one small win — native for B2B and small business)
- S13 FAQ Reply (answer a product question with observable evidence)
- S14 Green-Screen Commentary (talk over on-screen evidence)
- S15 Feature Checklist (show a set of observable attributes)
- S16 Host Question (one direct question answered by the demonstrator)
- S17 Baseline-to-Demo (show an observable setup change without invented results)
- S18 Silent Flex
- S19 ASMR (see the silent/ASMR mode below)

Every shape carries exactly ONE "but then" twist (the mid-arc peak) — no twist is a flat anecdote,
two will not fit in 15s. Realize the shape through the arc-role boards, never as a new field.

**Review-style / demo mode** (only on an explicit "review it / plain demo" ask): convert the request
into a truthful demonstration, not a customer testimonial. Give the body ONE
compact skeleton — PAS (Problem → Agitate → Solve), BAB (Before → After → Bridge),
Hook-Story-Offer, Us-vs-Them (against a lazy pricey default), or Demonstration ("watch this" — the
product does something visible in ~5s). Two or three spoken lines; even here the FIRST line carries
one observable detail or exact allowlisted claim. Do not invent a before/after result.

## Hook-pattern menu — the HOOK board's opener

Pick ONE pattern per video, never blend. The pattern decides what KIND of moment the opener is; the
first-word constraint below still governs its words. H2/H5/H7 are text-led — the opener LINE
embodies them. H1/H3/H4 are visual-led — the line lands mid-event and the staging carries it.

- **H1 Impact Action** — frame one is something physical mid-peak (box mid-rip, product mid-catch,
  mid-stumble); the first word lands DURING the action.
- **H2 Mid-Sentence Confession** — opens on word four of a sentence, as if the viewer walked in on
  it; confessional volume.
- **H3 Pattern Interrupt** — a normal setting with one thing deeply wrong, delivered with total
  normalcy; the wrongness is visual, the voice ignores it.
- **H4 Freeze-Reaction** — frame one: the face already in full reaction, locked on something; a
  performed hold (<=0.7s), THEN the first line.
- **H5 Hostile Open** — the first line is a challenge or accusation aimed at the viewer; slight
  lean-in, finger already pointing.
- **H6 Quirk-First** — the quirk IS the literal first event, before any context. Only when a quirk
  was opted into.
- **H7 Mechanism-First** — an observable product action is already underway in frame one; the first
  line names that visible action or repeats an exact allowlisted claim. Never imply a personal
  outcome, transformation, or before/after result.
- **H8 Product Cold Open** (advanced, story mode only, needs a product image) — board 1 slot 1 is
  clearly staged product-only footage (rougher light, slight compression, no face); ONE hard cut
  into slot 2 where the creator is mid-reaction with the product already in hand and the first line
  lands on the cut. The character enters one slot later than usual. Never frame the opening as
  found/reposted third-party footage and never add social proof. The slot-1 footage is a produced
  cold open, not the product's story entrance, so the 40-60% product entry still stands.

Write the chosen pattern into the HOOK board's prompt as ONE plain visual staging sentence — same
mechanism as the persona sentence, on board 1 only, never a pattern code.

## Anti-slop pass on every line

- The first words are never `Okay wait / Okay so / OMG / Hey guys / So basically / Stop scrolling /
  You NEED this / Story time`.
- Banned anywhere: "literally", "obsessed", "game-changer", "holy grail", "changed my life", "hits
  different", and corporate words (elevate / seamless / effortless).
- Demonstration-first openers beat unsupported enthusiasm ("Here is the part that twists open.").
- Every product claim must be an exact `approved_claims` string. With an empty allowlist, use only
  observable mechanics or sensory descriptions visible from the supplied product; never invent a
  number, duration, comparison, result, purchase count, or measurement for specificity.
- At most ONE peak reaction per clip in the monologue (the clip prompt may stage up to two — the arc
  peak plus an optional product-motivated closer beat).
- Echoes and repeats count toward the word budget but carry no information — cut them first.

**First-word constraint (positional, every board's segment):** the literal FIRST WORD must be hook
content — never `OK / Okay / Okay so / Alright / Alright so / So / Yeah so / Right so / Um / Well /
Like / Wait / Wait what / Hold on`. Those read as recording warmup. They are fine mid-sentence
later; the constraint is the first word only.

**Performed dialogue** (emotion lives IN the words — the video model under-renders flat prose):
vowel-stretch on the peak word ("it's SO good"), 1-2 CAPS volume spikes per line max, one broken
sentence at the peak ("it's— okay wait. LOOK."), a whisper-to-spike swing, and a flat → spike →
settle arc across the clip. Under the NATURAL default the peak stays human-scale (a real gasp, a
breaking grin), never staged screaming. NEVER write engineered or dramatic pauses — they bloat the
line and break the render.
```

**Ours**

```
Write {seconds} s of talk for {creator_name}, a host (never a customer), to {avatar} about {problem}. Hook in the first 1-2 s from the avatar's own words: {language_lines} (verbatim, with source). Story mode: the moment, the problem, what the product does that can be seen, one action. Claims only from {approved_claims}. About 2.5 words a second; split into {clip_count} segments of {clip_durations} s; segment 2 onward continues mid-thought, no greeting, no re-introducing the product. Ban AI-tell words (obsessed, game-changer, holy grail, literally, elevate, seamless). No disclaimers.
```

Check: Every line traces to the language folder or the product file; no invented use, results or reviews; word count fits each clip.

### 5. Voice read — `sound.voice`

Higgsfield has no voice step: Seedance speaks the lines itself (generate_audio true, no TTS). The house reads each segment in our own voice first and hands that read to the clip, so the creator speaks in a voice we own.

| | model | credits |
|---|---|---|
| Higgsfield | none: Seedance native speech | 0 |
| our house | ElevenLabs v3 (eleven-v3), the creator's voice from brands/<brand>/ai-elements/voices.json, one read per segment with a delivery tag | metered (cents) |
| cheapest | Kokoro-82M stock voice on this Mac (local-studio tts) | 0 |

Cheap swap: Free, but stock voices only: no voice of our own, flatter delivery. Or skip the read and let the clip model speak in its own voice (loses voice consistency across ads). Registry: kokoro-82m.

On this Mac: `python3 components/local-studio/local.py tts "{segment}" -o read.wav --voice am_michael`

**Higgsfield, word for word**

```
5. Compile every clip prompt before submission. Use the selected format's ordered
   reference roles, native audio, `seedance_2_5`, `mode:"omni_reference"`, and
   `generate_audio:true`. Do not add a separate narration/TTS job. Follow batch
   and upload limits in the runtime contract above, not another host's schema.
```

**Ours**

```
[{delivery_tag}] {segment_text}
```

Check: Heard back (Scribe): every word, in order; read length fits its clip (<= clip seconds).

### 6. Storyboard sheets — `pictures.board`

One 21:9 sheet per clip with eight 9:16 slots in one row, each slot a different camera setup; sheet K carries the cleaned sheet K-1 forward. Made one after another.

| | model | credits |
|---|---|---|
| Higgsfield | gpt_image_2_6 (Sunburst), 21:9, 2k, quality high; product + creator (+ previous clean board) as image refs | ≈2.25 each (Flare 2k high quote; Sunburst not quoted) |
| our house | GPT Image 2.5 (gpt-image-2.5), quality high, from the cast master and product photo | metered (OpenAI direct), about 2 credits' worth |
| cheapest | GPT Image 2.6 Flare 1k low (gpt_image_2_6_flare) | 0.75 |

Cheap swap: Eight slots at 1k are small; faces and labels blur, so the cleanup and the check carry more weight. Seedream 5.0 Flash at 0.5 is the other pick (registry: missing). Registry: missing.

**Higgsfield, word for word**

```
[@Image1 product reference + ANGLE LOCK if product is present.] [@Image2 character reference, or @Image1 if no product.] [@Image3 previous-board reference if K > 1, with explicit instruction to preserve identity / location / lighting / wardrobe / product from this reference.] The same person appears in every slot with identical face, hair, body, and identity — no changes to features, hair, or proportions between slots.

A single horizontal storyboard sheet composed of exactly EIGHT equal-size 9:16 vertical slots arranged in ONE HORIZONTAL ROW, separated by thin white gutters on a clean white background, total sheet aspect 21:9. Do NOT make two rows and do NOT make a grid — exactly eight panels in one row, never ten, never twelve. All eight slots are active photorealistic UGC iPhone-style stills that tell one continuous [clip_duration]-second video clip as eight sequential beats — slot 1 is beat 1 (opening), slot 8 is beat 8 (closing). There are no placeholder slots. Each adjacent pair of slots is a DIFFERENT camera setup — a different POV (selfie vs static camera), a different distance band (tight/macro vs medium vs wide), and a different action — so every beat boundary reads as a crisp hard cut, never a morph.

Setting and lighting in all eight slots default to the same environment, time of day, and light direction visible in the character reference image (and previous-board reference if provided), unless the story requires a different location. Outfit stays identical across slots within the same location.

Product (if present) appears at realistic real-world scale, approximately [X cm] in real size, fitting naturally in the character's hand without enlargement. Exactly one [product] appears in frame in every slot where it is visible — never a duplicate, never a look-alike clone. Product placement in every slot is clean: either fully visible held in one hand, fully hidden inside a closed bag/box/pocket, or absent from the frame — never half-sticking out, never balancing awkwardly, never partial.

The character has exactly two hands. In selfie POV slots, one hand is occupied by the phone (off-frame or visible at edge), so only one hand is available for action — never two objects in selfie POV. Every slot names what EACH hand is doing — one role per hand, the idle hand parked explicitly (holding the phone, resting at her side, flat on the counter) — never more than two simultaneous hand-roles. Slots requiring two free hands are static camera POV with the phone not in frame. POV may change between slots — every POV change aligns with a hard cut between slots, never a smooth transition.

Slot 1 — exact 9:16 vertical photorealistic UGC iPhone still, [selfie/static camera POV], [distance band]: [camera framing, character action, product placement (visible in hand / hidden inside X / absent), explicit hand allocation naming BOTH hands' roles (e.g. "left hand holds phone off-frame, right hand holds product"; an idle hand is parked — resting at her side, flat on the counter), micro-behavior, light/setting note].

Slot 2 — exact 9:16 vertical still, [POV — different framing from slot 1], [distance band — different from slot 1]: [...].

Slot 3 — exact 9:16 vertical still, [POV/band different from slot 2]: [...].

Slot 4 — exact 9:16 vertical still, [POV/band different from slot 3]: [...].

Slot 5 — exact 9:16 vertical still, [POV/band different from slot 4]: [...].

Slot 6 — exact 9:16 vertical still, [POV/band different from slot 5]: [...].

Slot 7 — exact 9:16 vertical still, [POV/band different from slot 6]: [...].

Slot 8 — exact 9:16 vertical still, [POV/band different from slot 7]: [...].

Rendering rules: every slot is an exact 9:16 vertical rectangle, all eight slots identical in size, arranged in ONE HORIZONTAL ROW (do NOT make two rows or a grid — exactly eight panels in one row, never ten, never twelve) with thin white gutters on a clean white background, total sheet aspect 21:9. All eight slots are active — there are no placeholder slots. No two adjacent slots share both their POV and their distance band. Active slots are photorealistic iPhone-style UGC stills with natural light and casual real-life feel. The character's identity is identical across all eight panels. The character has exactly two hands; selfie POV occupies one hand with the phone, leaving one hand for action; two-handed actions are static camera POV; every slot names each hand's single role, the idle hand parked explicitly, and the total simultaneous hand-roles never exceed two. POV may change between slots; every POV change aligns with a hard cut, never a smooth transition. The product (if present) appears at realistic real-world scale relative to the character's hand and body, never enlarged for visibility, and keeps the same visible angle from the reference image across all appearances. Product placement is always clean: fully held in hand, fully hidden inside a closed container, or absent — never partial, never sticking out, never balancing awkwardly. Exactly one product in frame wherever it appears — never duplicated. Each prop holds exactly one state per slot — a cap is on or off, never both. No on-image text of any kind: no header, no metadata, no captions, no pop-text, no badges, no numbers, no subtitles, no watermarks. No legible text or numbers on any prop beyond the product's own label and the garment's own large fictional print. No shallow depth of field, no bokeh, no lens flare, no beauty filter, no cinematic color grade [omit these negatives when user_request explicitly asks for a cinematic look]. No fisheye lens, no ultra-wide distortion. No mirror or reflection shots (unavoidable mirror = partial reflection only, matching the subject exactly). No deformed hands. No third arm, no extra hands, no duplicated limbs. No additional brands or logos beyond the user's product. No invented product claims.
```

**Ours**

```
@Image1 {product} reference, ANGLE LOCK (omit when no product, renumber). @Image2 {creator_name}. @Image3 the cleaned board {K_minus_1} when K > 1: keep identity, place, light, wardrobe and product state. The same person in every slot. One horizontal sheet of exactly EIGHT 9:16 slots in one row, thin white gutters, 21:9. Slot 1 = the hook: {hook_visual}. Slots 2-8 = {beats}, each a different POV and distance from the one before, each naming what both hands do. Setting {location}. Product at real size, about {size_cm} cm, one only. No on-image text, no other brands, no shallow depth of field, no beauty filter. {house_rules}
```

Check: Eight slots in one row; same face; real label; no text; distinct beats.

### 7. Board cleanup — `pictures.edit`

A realism pass over each raw board: same layout, poses, identity and label; only skin, material, light and phone grain change. Mandatory: the raw board never seeds anything.

| | model | credits |
|---|---|---|
| Higgsfield | seedream_5_5 (now seedream_v5_pro), 21:9, 2k, raw board as image input | 2.5 |
| our house | GPT Image 2.5 edit (gpt-image-2.5); Seedream (seedream-5-pro-edit) when GPT refuses | metered, about 2 credits' worth |
| cheapest | Seedream 5.0 Flash 2k (seedream_5_0_flash) | 0.5 |

Cheap swap: Same job at a fifth of the price; texture is lighter and it drifts faces more often, so inspect harder. Registry: missing.

**Higgsfield, word for word**

```
After every raw board, submit generate_image_batch with a stable index and params:
model seedream_5_5, count 1, aspect_ratio 21:9, resolution 2k, the raw board's
completed result_url as image input in full-profile (full: import that URL once with
media_import_url and use its confirmed media ID), and this prompt:

> KEEP EXACTLY the framing, composition, slot layout, camera distances, poses,
> identity, body, product geometry and real label. Change only micro-realism:
> natural skin/material texture, gentle daylight and fine sensor noise, authentic
> phone photo, deep focus. Preserve face proportions exactly. Avoid waxy skin,
> beauty filters, oversaturation, HDR glow, oversharpening and cinematic bokeh.
> No added watermark or text. Preserve existing tutorial Step N headings exactly.
```

**Ours**

```
KEEP EXACTLY the framing, composition, slot layout, camera distances, poses, identity, body, product geometry and real label. Change only micro-realism: natural skin/material texture, gentle daylight and fine sensor noise, authentic phone photo, deep focus. Preserve face proportions exactly. Avoid waxy skin, beauty filters, oversaturation, HDR glow, oversharpening and cinematic bokeh. No added watermark or text.
```

Check: Raw and cleaned kept separately; only the cleaned board moves on.

### 8. Board check — `behind.judge`

Look at each cleaned board: identity, product shape and state, slot count, distinct beats, no text. A failed check stops the clips that depend on it.

| | model | credits |
|---|---|---|
| Higgsfield | the directing chat model looks at the image | 0 |
| our house | Gemini 3.1 Pro judge (gemini-3.1-pro-preview) | metered, cents |
| cheapest | Gemini 3 Flash fast read (gemini-3-flash-preview) | cents |

Cheap swap: House rule: every read inside a run is the judge; Flash is a person's pick only. Registry: gemini-3-flash-preview.

**Higgsfield, word for word**

```
Poll the cleanup to completion, retain its job ID and URL separately from the raw
board, then inspect its encoded image for identity, product anatomy/state, slot
count, distinct beats and text. Use the current host's image inspection capability;
if unavailable, stop before dependent generation and report the missing check.
Only the inspected cleaned result seeds board K+1 and video. Never erase real
branding or relabel raw input as cleaned. On failure follow the entrypoint's
failure rules; no provider-hopping or raw-board fallback.
```

**Ours**

```
Board {K} of {N}: is it {creator_name} in all eight slots, is the {product} label real and readable, eight slots in one row, eight different beats, no text? Pass or name the slot that fails.
```

Check: Pass, or remake that board only.

### 9. Talking clips — `clips.talking`

One clip per board: the eight slots become eight hard cuts while the creator speaks that segment. Higgsfield lets Seedance invent the voice; the house sends our voice read in the same call so the lips follow it.

| | model | credits |
|---|---|---|
| Higgsfield | seedance_2_5 omni_reference, 9:16, 1080p, generate_audio true, 15 s; clean board + creator + product as image refs | 160 per 10 s (240 per 15 s clip) |
| our house | Seedance 2.5 (seedance-2.5) reference-to-video at 480p with the ElevenLabs v3 read as the voice reference, upscaled on this Mac | 30 per 10 s (45 per 15 s clip) |
| cheapest | Wan 3.0, 480p, image references + the read as audio_references (wan-3.0@higgsfield) | 7.5 per 10 s (11.25 per 15 s clip) |

Cheap swap: Takes up to 10 image refs and 5 audio refs, clips to 30 s; lip-sync and cut timing are looser than Seedance and Alibaba moderates it harder. Second pick: Gemini Omni Flash 1.2 at 360p, 7.5 per 10 s, max 10 s per clip, no audio reference (registry: missing). Registry: wan-3.0.

On this Mac: `RIFE interpolation if motion stutters (local-studio interp)`

**Higgsfield, word for word**

```
Style & Mood: UGC iPhone aesthetic, [light description matching the board], [SELFIE: front-facing camera, intimate handheld feel | STATIC: locked-off static camera, completely static, frozen frame | MIXED: starts SELFIE handheld, hard-cuts to STATIC locked-off, hard-cuts back to SELFIE handheld — POV alternates per cut], social media vertical format.

Narrative Summary: [1 sentence stating what happens in this clip — references the arc_role and the throughline of the 8 cuts. Close it with a register calibration phrase, gated THREE ways by `user_request`: NATURAL (DEFAULT — no signals needed) — close with `performed by a natural, engaged creator — genuine reactions, lively but human, never staged screaming energy` (or near-equivalent). HYPED (opt-in ONLY) — when `user_request` carries an explicit energy signal (`hyped` / `hype` / `energetic` / `explosive` / `high-energy` / `viral energy` / `insane energy`), close with `performed by an INSANELY hyped creator with explosive screaming energy throughout` (or near-equivalent). CALM — skip the calibration phrase entirely when `user_request` signals a calm-tone aesthetic (`goth` / `vampire` / `cinematic noir` / `cold` / `passive` / `deadpan` / `clinical` / `refined` / `luxury-passive` / `minimal` / `somber` / `serious` / `dark` / `shadowy` / `quiet` / `GRWM` / `routine` / `process-led`). The explicit `user_request` word always wins].

Dynamic Description:
Cut 1 (0-Xs) — [framing distance per board slot 1, e.g. MEDIUM CLOSE-UP, TIGHT CLOSE-UP, MACRO, WIDER, PRODUCT-EXTENDED] [POV per slot 1]: [action from slot 1, explicit hand allocation (role of EACH hand, ≤ 2 simultaneous hand roles), 2+ micro-behaviors, expression, and — only when present — product placement]. Hard cut to.
Cut 2 (...) — [framing distance / POV per slot 2, a DIFFERENT framing from cut 1]: [action from slot 2, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 3 (...) — [per slot 3, different framing from cut 2]: [action from slot 3, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 4 (...) — [per slot 4, different from cut 3]: [action from slot 4, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 5 (...) — [per slot 5, different from cut 4]: [action from slot 5, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 6 (...) — [per slot 6, different from cut 5]: [action from slot 6, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 7 (...) — [per slot 7, different from cut 6]: [action from slot 7, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 8 (Ys-end) — [per slot 8, different from cut 7]: [action from slot 8, hand allocation, 2+ micro-behaviors, expression, and optional product placement].

Static Description: [1-2 sentences: setting, ambient details, props, light direction — match the board image's environment].

Audio: She speaks to camera, iPhone microphone audio with natural room tone[, IF K==1 AND non-verbal cues used: include bracketed sounds at the start of Cut 1, e.g. [*small bright laugh*] [*soft gasp*] [*delighted 'oh!'*] (HYPED register only: [*explosive gasp*] [*hyped yelp*])]: "[monologue_segment, distributed across the 8 cuts at natural phrase boundaries]"

[ONLY when user_request explicitly asks for music or names a genre/mood — Music: [genre/mood], low in the mix under the voice, swells at [the peak beat], returns under the closer.]

Facial features clear and undistorted, consistent clothing throughout. Shot on iPhone, natural lighting, social media aesthetic. [SELFIE-only: slight natural handheld micro-shake from her grip | STATIC-only: locked-off static camera, absolutely static, zero camera movement of any kind, no shake, no drift, no breathing wobble | MIXED: handheld micro-shake during selfie cuts, locked-off frozen frame during static-camera cuts]. No on-screen text, no subtitles, no captions, no watermarks, no legible text on any object except [when a product exists: the product's own label and] the garment's own large fictional print, no real brand logos anywhere, no cinematic grade, no film grain, no bokeh, no lens flare, no fisheye lens, no ultra-wide distortion, no slow motion, no beauty filter, no third arm, no extra hands, no duplicated limbs, no deformed hands.
```

**Ours**

```
Style & Mood: UGC iPhone aesthetic, {light}, {pov_mode}, social media vertical format.
Narrative Summary: {one_sentence_arc}, performed by a natural, engaged creator — genuine reactions, lively but human, never staged screaming energy.
Dynamic Description:
Cut 1 (0-{t1}s) — {framing_1} {pov_1}: {action_1}, {hands_1}, {micro_1}, {expression_1}. Hard cut to.
... Cut 8 ({t7}s-end) — {framing_8} {pov_8}: {action_8}.
Static Description: {setting}.
Audio: {He/She} speaks to camera in the attached voice, iPhone microphone audio with natural room tone: "{segment_text}"
Facial features clear and undistorted, consistent clothing throughout. Shot on iPhone, natural lighting. No on-screen text, no subtitles, no captions, no watermarks, no legible text except the {product}'s own label, no other brand logos, no cinematic grade, no slow motion, no beauty filter, no extra hands, no deformed hands.
```

Check: Send clip 1 alone and check it first; then the rest as a batch.

### 10. Clip check — `behind.judge`

Each clip: same face and product, real length, 9:16, every word of the segment spoken, no stray text. Remake only a clip that fails.

| | model | credits |
|---|---|---|
| Higgsfield | the directing chat model + ffprobe | 0 |
| our house | Gemini 3.1 Pro judge (gemini-3.1-pro-preview) + Scribe heard-back (scribe_v1) | metered, cents |
| cheapest | Whisper on this Mac for the words + Gemini 3 Flash (gemini-3-flash-preview) | cents |

Cheap swap: Whisper is free and good enough for the words; the picture read stays the judge inside a run. Registry: whisper-large-v3-turbo.

On this Mac: `python3 components/local-studio/local.py stt clip.mp4 -o words.json; ffprobe; 2 fps contact sheet`

**Higgsfield, word for word**

```
6. Inspect completed clips for identity/product continuity, actual duration,
   framing, speech and intended text. Tutorial Step N labels are required;
   other generated text is forbidden. Correct only identified failed clips.
```

**Ours**

```
Clip {K}: {creator_name}'s face in every cut, the {product} label real, {clip_seconds} s, 9:16, the words "{segment_text}" all heard in order, no text on screen. Pass or name the cut that fails.
```

Check: Every segment heard in order; contact sheet clean; remake only failed indices.

### 11. Upscale — `behind.upscale`

House clips are made at 480p and upscaled here; Higgsfield renders 1080p directly, so it has no such step.

| | model | credits |
|---|---|---|
| Higgsfield | none (1080p rendered) | 0 |
| our house | Real-ESRGAN on this Mac (real-esrgan) | 0 |
| cheapest | Real-ESRGAN animevideov3, local (real-esrgan) | 0 |

Cheap swap: About 11 s of compute per video-second; skin is smoother than a native 1080p render. Registry: real-esrgan.

On this Mac: `python3 components/local-studio/local.py upscale clip.mp4 -o out.mp4 --esrgan-model realesr-animevideov3`

Check: 1080x1920, faces not waxy.

### 12. Assembly and captions — `edit.assemble`

Join the accepted clips in order, keep their sound, add captions only when asked (tutorial keeps its Step labels). Higgsfield hands this to its video-montage workflow.

| | model | credits |
|---|---|---|
| Higgsfield | video-montage workflow, ffmpeg in the sandbox | 0 |
| our house | Video Edit (components/video-edit), the Studio's edit line; word timings from Scribe (scribe_v1) | 0 |
| cheapest | ffmpeg + Whisper captions on this Mac | 0 |

Cheap swap: Nothing lost for a straight join. Registry: whisper-large-v3-turbo.

On this Mac: `ffmpeg concat; python3 components/local-studio/local.py stt final.mp4 -o words.json for captions`

**Higgsfield, word for word**

```
7. For assembly and requested captions load video-montage directly, passing ordered
   accepted clip URLs, authored words, language, look and any website hook/card
   clearance. Physical captions/post package are opt-in; website retains its
   upfront selection. Caption scripts belong exclusively to video-montage.
```

**Ours**

```
Clips 1..{N} in order, their own sound, 1080x1920. Captions only if the brief asks: the monologue words, timed from the read. No offer, price, disclaimer or call to action burned in unless the brief's own words ask for it.
```

Check: Length = {seconds} s within 0.1 s; audio present; captions match the words.

### 13. Check and deliver — `behind.judge`

Check the finished file's real metadata and frames, then deliver to the Studio and Drive. Retry only failed pieces; never switch models silently.

| | model | credits |
|---|---|---|
| Higgsfield | the directing chat model; media_upload + show_result | 0 |
| our house | Gemini 3.1 Pro judge (gemini-3.1-pro-preview); delivered to the Studio and Drive | metered, cents |
| cheapest | Gemini 3 Flash fast read (gemini-3-flash-preview) | cents |

Cheap swap: House rule: every read inside a run is the judge; Flash is a person's pick only. Registry: gemini-3-flash-preview.

On this Mac: `ffprobe + 0.5 fps contact sheet`

**Higgsfield, word for word**

```
## Failures and delivery

A timeout or unknown outcome is not a failed submission: poll existing IDs first.
Never resubmit a whole batch because one index failed. An explicit technical
failure may be retried once within authorized spending; a bare failed status with
no reason remains unknown. Moderation stops the dependent path; do not switch
providers, regenerate identities, remove references or use text-to-video to bypass it.
Never replace a locked model silently. Retain successful artifacts for recovery.
Return the confirmed finished video and requested chat-only post package. Check
actual output metadata and encoded frames; job completion alone is not quality proof.
```

**Ours**

```
Check: the hook in second 1-2; same face start to end; product label readable; every seam; every word heard; no disclaimer or stray text. Report the credits spent and any line that is not from the language folder or the product file.
```

Check: Delivered to the Studio and Drive, never to Meta from here.

## Checks

- Price quoted and under the lane.json cap before the first paid call
- Creator is our banked adult cast member; the same face in every board and clip
- Claims only from the product file's approved list; the creator never claims personal use or results
- Only cleaned, checked boards seed the next board or a clip
- First clip checked alone before the batch
- Every monologue word heard in order
- No text on screen except tutorial Step labels and the product's own label
- Length = target within 0.1 s; 1080x1920; audio present

## Rules

- One creator, our own banked adult cast member, every board and clip
- Words from the avatar's language folder; claims only from the approved list; the creator is a host, never a customer
- Our voice (voices.json), never the clip model's invented one
- Raw boards never seed anything; only cleaned, checked boards
- No disclaimers, offer, price or call to action on screen unless the brief's own words ask
- Clothed cast, no brands but ours, men never kiss or hug men
- A failed clip is remade alone; never switch models silently

## Formats

```
[
 {
  "id": "review",
  "name": "Review (default)",
  "when": "A creator talks to camera about a product, or tells a story with no product.",
  "file": "sources/higgsfield/ugc-video/references/formats/review.md",
  "slots_per_board": 8,
  "changes": "The steps above as written: product optional, on-camera speech, eight slots per board.",
  "board": {
   "file": "sources/higgsfield/ugc-video/references/ugc-board.md",
   "key_prompt_line": "[@Image1 product reference + ANGLE LOCK if product is present.] [@Image2 character reference, or @Image1 if no product.] [@Image3 previous-board reference if K > 1, with explicit instruction to preserve identity / location / lighting / wardrobe / product from this reference.] The same person appears in every slot with identical face, hair, body, and identity — no changes to features, hair, or proportions between slots."
  },
  "character": {
   "file": "sources/higgsfield/ugc-video/references/ugc-character.md",
   "key_prompt_line": "A [age band from Variety pool] [man/woman], [expression — pick one from the Approved mid-action expressions list], [hair color + length from Variety pool], [build vibe], with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a [specific location with architectural details]."
  },
  "clip": {
   "file": "sources/higgsfield/ugc-video/references/ugc-clip.md",
   "key_prompt_line": "Style & Mood: UGC iPhone aesthetic, [light description matching the board], [SELFIE: front-facing camera, intimate handheld feel | STATIC: locked-off static camera, completely static, frozen frame | MIXED: starts SELFIE handheld, hard-cuts to STATIC locked-off, hard-cuts back to SELFIE handheld — POV alternates per cut], social media vertical format."
  },
  "extra": [
   {
    "file": "sources/higgsfield/ugc-video/references/monologue-craft.md",
    "key_prompt_line": "ONE scenario spans the whole video: situational stakes first, framed without claiming that a"
   },
   {
    "file": "sources/higgsfield/ugc-video/references/product-intake.md",
    "key_prompt_line": "Write ONE canonical `product_description` and reuse it verbatim in every downstream prompt:"
   }
  ]
 },
 {
  "id": "product",
  "name": "Product (voiceover)",
  "when": "The product is the hero; an off-screen voice talks; any person is hands-only and silent. Needs a real product photo.",
  "file": "sources/higgsfield/ugc-video/references/formats/product.md",
  "slots_per_board": 4,
  "changes": "Skip step 3 (no creator). Product photo required. Boards have four slots. The voice is off-screen: the house read becomes the narrator voice (voices.json, narrator row) and no mouth is shown; for Wan the read goes in as audio_references, or the clip is made silent and the read laid on.",
  "board": {
   "file": "sources/higgsfield/ugc-video/references/ugc-product-boards.md",
   "key_prompt_line": "[@Image1 product reference + ANGLE LOCK.] [@Image2 previous-board reference if K > 1, with explicit instruction to preserve product / location / lighting from this reference.] The product is the hero of every slot. The person, when present in any slot, is auxiliary — cropped, hands-only, partial body, or first-person POV — never the focal subject. Person's mouth is closed; no on-camera dialogue. Auxiliary person's gender, when present, is [female | male — derived from voice_gender], consistent within this board."
  },
  "character": null,
  "clip": {
   "file": "sources/higgsfield/ugc-video/references/ugc-product-clip-prompt.md",
   "key_prompt_line": "Style & Mood: UGC iPhone aesthetic — phone-sensor grain, natural ambient light typical of a phone photo (NOT studio strobes, NOT moody side-light, NOT dramatic mood lighting, NOT golden hour), NOT editorial product photography, NOT studio shoot, NOT magazine commercial; [light description matching the board — soft neutral daylight or even ambient room light], [STATIC: locked-off static camera, completely static, frozen frame | FIRST-PERSON-POV: handheld first-person, slight natural micro-shake, only the operator's hand or forearm at frame edge if natural, phone object NEVER visible | MIXED: starts STATIC locked-off, hard-cuts to FIRST-PERSON-POV handheld, hard-cuts to MACRO locked-off, hard-cuts back to STATIC locked-off — POV alternates per cut], social media vertical format."
  },
  "extra": [
   {
    "file": "sources/higgsfield/ugc-video/references/product-product-intake.md",
    "key_prompt_line": "Both input forms (a photo the user attached, or a product URL) must end in the SAME structured"
   }
  ]
 },
 {
  "id": "unboxing",
  "name": "Unboxing",
  "when": "A visible creator opens the package and reacts. Only when the brief asks for a creator-led reveal.",
  "file": "sources/higgsfield/ugc-video/references/formats/unboxing.md",
  "slots_per_board": 4,
  "changes": "Product required, plus a package picture if we have one (else a plain brown delivery box). Four slots per board: packed, opening, reveal, react/use. Same creator and voice steps.",
  "board": {
   "file": "sources/higgsfield/ugc-video/references/ugc-unboxing-board.md",
   "key_prompt_line": "[@Image1 product reference + ANGLE LOCK if product is present.] [@Image2 character reference, or @Image1 if no product.] [@Image3 package reference if provided — Slot 1 PACKED depicts THIS exact package. Otherwise Slot 1 uses a generic plain brown taped delivery box.] [@Image4 (or @Image3 if no package) previous-board reference if K > 1, with explicit instruction to preserve identity / location / lighting / wardrobe / product from this reference.] The same person appears in every slot with identical face, hair, body, and identity — no changes to features, hair, or proportions between slots."
  },
  "character": {
   "file": "sources/higgsfield/ugc-video/references/unboxing-ugc-character.md",
   "key_prompt_line": "A [age band from Variety pool] [man/woman], [expression — pick one from the Approved mid-action expressions list], [hair color + length from Variety pool], [build vibe], with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a [specific location with architectural details]."
  },
  "clip": {
   "file": "sources/higgsfield/ugc-video/references/ugc-unboxing-clip.md",
   "key_prompt_line": "Style & Mood: UGC iPhone aesthetic, [light description matching the board], [SELFIE: front-facing camera, intimate handheld feel | STATIC: locked-off static camera, completely static, frozen frame | MIXED: starts SELFIE handheld, hard-cuts to STATIC locked-off, hard-cuts back to SELFIE handheld — POV alternates per cut], social media vertical format."
  },
  "extra": [
   {
    "file": "sources/higgsfield/ugc-video/references/product-product-intake.md",
    "key_prompt_line": "Both input forms (a photo the user attached, or a product URL) must end in the SAME structured"
   }
  ]
 },
 {
  "id": "try-on",
  "name": "Try-on",
  "when": "A creator wears the item and shows fit and texture. Wearables only.",
  "file": "sources/higgsfield/ugc-video/references/formats/try-on.md",
  "slots_per_board": 8,
  "changes": "Product must be wearable; the board uses a GARMENT CONSISTENCY LOCK instead of the angle lock. Eight slots, seven hard cuts. Same creator and voice steps.",
  "board": {
   "file": "sources/higgsfield/ugc-video/references/ugc-try-board.md",
   "key_prompt_line": "[@Image1 product reference + GARMENT CONSISTENCY LOCK if product is present.] [@Image2 character reference, or @Image1 if no product.] [@Image3 previous-board reference if K > 1, with explicit instruction to preserve identity / location / lighting / wardrobe / product / hairstyle from this reference.] The same person appears in every slot with identical face, hair, body, and identity — no changes to features, hair, or proportions between slots."
  },
  "character": {
   "file": "sources/higgsfield/ugc-video/references/try-on-ugc-character.md",
   "key_prompt_line": "A [age band from Variety pool] [man/woman], [expression — pick one from the Approved mid-action expressions list], [hair color + length from Variety pool], [build vibe], with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a [specific location with architectural details]."
  },
  "clip": {
   "file": "sources/higgsfield/ugc-video/references/ugc-try-clip.md",
   "key_prompt_line": "Style & Mood: UGC iPhone aesthetic, [light description matching the board, tier-matched], [SELFIE: front-facing camera, intimate handheld feel | STATIC: locked-off static camera, completely static, frozen frame | MIXED: starts SELFIE handheld, hard-cuts to STATIC locked-off, then alternates POV per cut across the eight beats], social media vertical format."
  },
  "extra": [
   {
    "file": "sources/higgsfield/ugc-video/references/product-product-intake.md",
    "key_prompt_line": "Both input forms (a photo the user attached, or a product URL) must end in the SAME structured"
   }
  ]
 },
 {
  "id": "tutorial",
  "name": "Tutorial",
  "when": "A creator shows real use, step by step, with a 'Step N — Heading' label in every slot.",
  "file": "sources/higgsfield/ugc-video/references/formats/tutorial.md",
  "slots_per_board": 4,
  "changes": "Product required. Four step slots per board, each with exactly one Step N label: the only format where generated text is allowed, and the cleanup keeps the labels. Clips are mostly static camera.",
  "board": {
   "file": "sources/higgsfield/ugc-video/references/ugc-tutorial-boards.md",
   "key_prompt_line": "[@Image1 product reference + ANGLE LOCK if product is present.] [@Image2 character reference, or @Image1 if no product.] [@Image3 previous-board reference if K > 1, with explicit instruction to preserve identity / location / lighting / wardrobe / product from this reference.] The same person appears in every slot with identical face, hair, body, and identity — no changes to features, hair, or proportions between slots."
  },
  "character": {
   "file": "sources/higgsfield/ugc-video/references/soul-v2-ugc-character.md",
   "key_prompt_line": "A [age band from Variety pool] [man/woman], [expression — pick one from the Approved mid-action expressions list], [hair color + length from Variety pool, build vibe], with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a [specific location with architectural details]."
  },
  "clip": {
   "file": "sources/higgsfield/ugc-video/references/ugc-tutorial-clip-prompt.md",
   "key_prompt_line": "Style & Mood: UGC iPhone aesthetic, [light description matching the board], [SELFIE: front-facing camera, intimate handheld feel | STATIC: locked-off static camera, completely static, frozen frame | MIXED: starts STATIC locked-off, hard-cuts to STATIC locked-off, hard-cuts to STATIC locked-off, hard-cuts to SELFIE handheld — POV alternates per cut as specified], social media vertical format. Each cut shows the on-screen text caption \"Step N — Heading\" baked into the frame in [font vibe] style, identical typography across cuts in this clip."
  },
  "extra": [
   {
    "file": "sources/higgsfield/ugc-video/references/product-product-intake.md",
    "key_prompt_line": "Both input forms (a photo the user attached, or a product URL) must end in the SAME structured"
   }
  ]
 },
 {
  "id": "website",
  "name": "Website tour",
  "when": "A talking-head creator with real screenshots of a site as cards. Only when the page itself must appear; a product link alone is not this format.",
  "file": "sources/higgsfield/ugc-video/references/formats/website.md",
  "slots_per_board": 0,
  "changes": "No boards: skip steps 6-8. Capture real mobile screenshots of the URL first (free, headless browser on this Mac). Each clip is one continuous talking-head shot (no cuts); the screenshots are laid over at word times in assembly. 22-40 words per clip by length.",
  "board": null,
  "character": {
   "file": "sources/higgsfield/ugc-video/references/saas-ugc-character.md",
   "key_prompt_line": "This is the **step-5 Seedance target**, not something you compose in the seed: the `soul_2` seed is a"
  },
  "clip": {
   "file": "sources/higgsfield/ugc-video/references/saas-clip-prompt.md",
   "key_prompt_line": "Compose each clip prompt from these parts, in this order:"
  },
  "extra": [
   {
    "file": "sources/higgsfield/ugc-video/references/saas-monologue.md",
    "key_prompt_line": "The creator never cuts away; the site appears as overlay cards during the body. Write the body so it"
   },
   {
    "file": "sources/higgsfield/ugc-video/references/website-capture.md",
    "key_prompt_line": "Produce `output/site_full.png` (one mobile full-page capture → the section map) plus dedicated stills"
   },
   {
    "file": "sources/higgsfield/ugc-video/references/screen-broll-and-composite.md",
    "key_prompt_line": "The creator is on camera the whole video (the clips are the base picture and the continuous voice)."
   }
  ]
 }
]
```
