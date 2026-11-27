# Drama Ads

A 9:16 micro drama story ad, 30-60 s: two or three characters act and speak on screen in their own voices, the conflict is the avatar's problem, the product turns it, the ending is a visible action. Live action by default; any catalog style (claymation, doll, crochet, 3D cartoon, talking object, inside the body, storytime narration) on the card's word.

Higgsfield original: `/drama-ads` · built from `sources/higgsfield/commands/drama-ads.md`, `sources/higgsfield/drama-ads/SKILL.md`, `sources/higgsfield/drama-ads/references/story-rules.md`, `sources/higgsfield/drama-ads/references/script-format.md`, `sources/higgsfield/drama-ads/references/characters.md`, `sources/higgsfield/drama-ads/references/formats.md`, `sources/higgsfield/drama-ads/references/styles.md`, `sources/higgsfield/drama-ads/references/style-master.md`, `sources/higgsfield/drama-ads/references/sheet-realism.md`, `sources/higgsfield/drama-ads/references/sheet-stylized.md`, `sources/higgsfield/drama-ads/references/location.md`, `sources/higgsfield/drama-ads/references/plan-and-effects.md`, `sources/higgsfield/drama-ads/references/clips.md`, `sources/higgsfield/drama-ads/references/models.md`, `sources/higgsfield/drama-ads/scripts/styles/live-action.md`, `sources/higgsfield/drama-ads/scripts/styles/*.md (the chosen style's file only)`, `sources/higgsfield/drama-ads/catalog/_cards.md`, `sources/higgsfield/drama-ads/catalog/<card>.md (e.g. failed-remedies.md)`, `sources/higgsfield/_prices.md`, `sources/higgsfield/_models-video.md`

## Price

| | |
|---|---|
| higgsfield | ≈500 credits at 1080p (2 clips of 15 s = 480 + ~7 sheets/plates ≈ 18); +240 per 15 s remake; ≈110 at 480p |
| house | ≈90 credits (Seedance 2.5 480p, banked sheets and voices, ~2 per missing sheet, free local upscale) + ElevenLabs v3 reads and music, metered off Higgsfield |
| cheap | ≈23 credits (Wan 3.0 480p with our voice samples as audio refs, banked sheets, Seedream Flash 0.5 for a gap, free upscale): about a quarter of the house, a twentieth of Higgsfield's 1080p |
| basis | 30 s live-action dialogue ad: 3 characters, 1 place, 2 props, 2 clips of 15 s, no remake; prices quoted 2026-11-21 |

## Inputs

- **card** (optional): a catalog card's structure: sources/higgsfield/drama-ads/catalog/<card>.md (prompt + settings); else the swipe's teardown structure (runs/video-teardown/<brand>/<slug>/)
- **reference swipe** (optional): runs/video-teardown/<brand>/<slug>/ (the swipe's read: shots, cuts, words a minute, beat times) and its audio teardown sound sheet
- **hero and conflict**: brands/<brand>/core-avatars/<avatar>/profile.md and culture-map.md
- **her words**: brands/<brand>/core-avatars/<avatar>/language/
- **objections**: brands/<brand>/core-avatars/objection-bank.md
- **offer**: brands/<brand>/products/offer-bank.md (the product's claims and the spoken last line; never on screen)
- **angle** (optional): brands/<brand>/strategy/angles.json (active angles only) or the ask: runs/creative-strategist/<brand>/<ask>/ask.json
- **product photos**: brands/<brand>/products/<product>/images/ (some brands keep one flat brands/<brand>/products/images/)
- **product sheet** (optional): runs/ai-elements/<brand>/products/<product>/model/ (banked product sheet; the label kept exact)
- **cast**: runs/ai-elements/<brand>/casting/<role>/full/master.png + sheets/ (banked, signed-off faces)
- **cast voices**: runs/ai-elements/<brand>/casting/<role>/voice.json (ElevenLabs voice_id per character, our own voices only)
- **places** (optional): runs/ai-elements/<brand>/sets/<set>/ (picture.png + element.json)
- **house rules**: brands/<brand>/CLAUDE.md + the owner's hard rules (no disclaimers on screen, men never kiss or hug men, clothed cast, no brands but ours)

## Steps

### 0. The ad's record — `none`

Higgsfield opens a Drama Ads record (ads_studio_story_recipe / the first get_drama_ads_config) and stamps drama_ads_id on every call. Ours: the run folder and lane.json are the record.

| | model | credits |
|---|---|---|
| Higgsfield | ads_studio_story_recipe + get_drama_ads_config | 0 |
| our house | runs/higgsfield/<brand>/<label>/ + lane.json + jobs.json | 0 |

**Higgsfield, word for word**

```
- **The film's id:** `drama_ads_id` comes from `get_drama_ads_config`: the film's first quote starts its story and answers the
  id; a card's id from `ads_studio_story_recipe` goes into that first quote and comes back the same. Keep it in `jobs.json`.
  Pass `drama_ads_id` in `params` of EVERY generation and batch item, every `get_drama_ads_config` call, every
  `ads_studio_story_stage` call and the final `show_result` meta. A generation sent without it is missing from the film's record.
```

Check: lane.json carries the owner's go and a credit cap before any paid step; every job id lands in jobs.json the moment it returns.

### 1. Intake, settings and the price — `plan.quote`

Read the card (length, shape, style, format), fix 9:16 and the resolution, count sheets, plates and clips, quote the whole film before the first paid call.

| | model | credits |
|---|---|---|
| Higgsfield | get_drama_ads_config (purpose film / stage / remake), balance | 0 |
| our house | estimate_image_cost / estimate_video_cost quotes (they submit nothing) | 0 |

**Higgsfield, word for word**

```
## 0. Intake: the card, the one question, the plan

The command `/drama-ads` brings one of three things: the user's own words, a card they named, or the catalog card's
line `card <card id> «…» (…); mode: <ask|hands-off>; product <product id> «…»; characters <kind>:<id>,…; idea: <words>` (every
part but `card` and `mode` optional, everything after `idea:` the user's words). `mode: ask` runs the stages of «Stages in ask
mode»; `mode: hands-off` runs «Hands-off mode».

In this order, nothing before its turn:

1. **The card:** call `ads_studio_story_recipe({ preset_id })` once, with `product_id` too when the line has a product. When it
   answers no `drama_ads_id` and its `instructions` name another command, the card is not a micro drama: stop this workflow and
   follow them. Its `drama_ads_id`,
   when present, goes into every `ads_studio_story_stage` call and into the final `show_result`'s `meta`, and the first
   `get_drama_ads_config` takes it (The film's id). Its `prompt`
   is the film's brief: follow it as this workflow's brief (its first line names the skill it was written for; ignore that line).
   Its `script.text`, when present, is the film's screenplay: a script the user gave, made as written. Its `settings` give the
   length (`duration_seconds`), the shape (`aspect_ratio`) and the resolution when set. Its `product`, `presenter` and `location`
   are the card's own slots, used as below unless the user picked others. The user's own words (`idea:` or their message) win
   over the card wherever they differ, as the brief itself says.
   In 3D and 2D the style master is a role of its own (`master`) in the film quote (Cost). A missing amount never counts as
   zero or as spending approval.
2. **The one intake question**, asked before any bundle read, model check or sandbox call, and only for what is still unknown, in
   one message:
   - the resolution, each option one number for the whole film at that resolution, `480p · film ≈ <total> credits` (720p and
     1080p the same), never a rate to multiply: the three totals of one `get_drama_ads_config` call with purpose `film` made right before the question,
     `get_drama_ads_config({ purpose: "film", style, resolutions: ["480p", "720p", "1080p"], requests: [{ role: "sheet", count }, { role: "clip", count, seconds }, …] })`: `style` the film's style id (the card's or the user's; `live-action` when nobody names one), its roles the reference sheets (and in 3D and 2D the `master`), the frame plates, the clips at the film's length (the
     card's `duration_seconds` or the length the user named) and a `score` (its `seconds` the film's length plus 5) when the brief has one, counted on the cast, places,
     props and clips the plan (step 3) will name; with `narration: true` or `song: true` when the film has one, its «… not included: priced when the text is written» repeated in the question; so the plan's «≈ <total>» is the number the user clicked, never a second one; with no length known yet, two such calls, the film at 30 and at 60 seconds, the second with the `drama_ads_id` the first returned; 1080p as the default; skip it when the user or the card named one;
   - when the message had no `mode:`: stop after each stage or run hands-off (stages: references, clips round 1, clips round 2).

   Wait for the answer. A message that already settles both asks nothing and goes on at once.

3. **The plan, before money:** right after the answer (at once when nothing needed asking), built from the recipe alone: its
   brief, script, settings and slots and the user's words (the words alone with no card), with no bundle read, model check or sandbox call before it. In ask
   mode it is a question that ends the turn:

   ```
   Plan: <cast>, <locations>, <props>, <N> clips · ≈ <total> credits. First step: references — <N> jobs ≈ <X> credits. Approve?
   ```

   The plan is the question's body, asked through `ask_user_question` with exactly two options,
   `Approve references · <N> sheets ≈ <X> credits` and `Change something`, so the host shows them as buttons and the one that
   spends says what it buys, the count and the price with no formula behind them (Stages in ask mode). In 3D and 2D the yes
   sends the style master alone (Stop 1), so there the first step reads `the style master — 1 job ≈ <master quote> credits` and the
   option `Approve the master · 1 sheet ≈ <master quote> credits`. A reply typed instead is a change request (Stages in ask mode).
   `<cast>` gives each name with one line about them. The clips are the film's length in clips of about 15 seconds. `<total>` is
   the film's estimate, the total of a `get_drama_ads_config` call with purpose `film` made right before the plan with the
   film's style and the roles of this cast, places, props and clips at the picked resolution: when the intake asked, the same
   roles, so the number the user clicked, never a second one; `<X>` is the total of a `film` call holding only the first step's
   roles. A film with a narration or a song carries the answer's «… not included» clause in the plan too. Before the plan call `balance` once
   and compare it with that `get_drama_ads_config` film total: credits below it put `balance <B> < ≈ <total> credits` at the
   start of the plan, question or statement, and otherwise the balance is not mentioned (the user needs the number only when it
   stops them). In a narrated film ask the
   narrator's voice (`list_voices`) as a second question of the same call. In hands-off the plan is a statement and the work
   goes on.

4. **Only after the plan's yes:** the availability check (`models_explore`, `references/models.md`), the sandbox preflight
   (RUNTIME CONTRACT), the references each step names, read with `get_workflow_bundle_file`, the imports below, then steps 1-2
   and Stop 1's calls in the same turn. When the script needs more than the plan said, or the chosen style file warns about the
   picked resolution, say so with the new total before the first paid call (Cost).

- **The product** comes only from the recipe:
  - a `product <id>` part: call the recipe as `ads_studio_story_recipe({ preset_id, product_id })`; its `product` is then the
    product the user picked, with its `name`, `description` and `image_url` (the card's own product when that id is the card's);
  - no `product` part: the recipe's `product` is the card's own product;
  - a `status` other than `completed` means Ads Studio is still reading that product's page: tell the user in one line and make
    it from what the recipe gives;
  - either way, import its `image_url` with `media_import_url` and use it as the user's product photo; a product with no
    `image_url`, or one the user only names in words, is a product described in words only (above).
- **The cast:** `characters avatar:<id>,…` (or the recipe's `presenter` when there is none) are the people to cast, the first the
  main person. Find each `avatar` id in `ads_studio_list_avatars` (pages of `size: 60`, following `user_cursor` and
  `preset_cursor` while `has_more`), import its `preview_url` with `media_import_url`, and use the media id as that character's
  face photo (`faceImage`). An id not found after 10 pages, or a kind other than `avatar`, is cast from the story instead; tell the
  user in one line.
- **The place:** the recipe's `location.image_url`, imported the same way, is the main place's photo; its `text` is that place's
  description.
```

**Ours**

```
Card {card} sets: length {seconds} s, shape 9:16, style {style}, format {format} (dialogue unless the card says storytime). Cast {cast} (banked), places {places}, product {product}. Clips: {seconds} s in clips of 10-15 s at {resolution} with {clip_model}. Quote every distinct sheet, plate and clip length, add them up, write the total and the cap into lane.json, stop for the go.
```

Check: Total under the cap in lane.json; a plan that grows is quoted again before the next paid call.

### 2. Reference video (when there is a swipe) — `read.reference`

Take the swipe apart before the script: a frame a second, its cuts, its words with times; write what it sets (pacing, beat shares, words a minute, captions) into reference.md. Its story and lines are never copied.

| | model | credits |
|---|---|---|
| Higgsfield | ffmpeg scene filter + faster-whisper small (sandbox) | 0 |
| our house | video-teardown run + audio-teardown sound sheet (ElevenLabs Scribe, scribe_v1) | metered (Scribe) |
| cheapest | whisper-large-v3-turbo (local-studio stt) + ffmpeg cuts | 0 |

Cheap swap: No speaker labels and no judged read of the shots; enough for cut times, words a minute and beat shares. Registry: whisper-large-v3-turbo.

On this Mac: `python3 components/local-studio/local.py stt swipe.mp4 -o words.json; ffmpeg -vf "select='gt(scene,0.1)',metadata=print"`

**Higgsfield, word for word**

```
### A reference video

Take it apart before the script, in the sandbox:

- **The picture:** a frame a second (`ffmpeg -i ref.mp4 -vf fps=1,scale=-2:480 r%03d.jpg`) and its cuts (`ffmpeg -i ref.mp4 -vf
  "select='gt(scene,0.1)',metadata=print" -f null - 2>&1 | grep -E 'pts_time|scene_score'`, a candidate under 0.3 confirmed by its
  frames: `references/clips.md`, Order of work, Stubs). Look at the frames, and at the ones around each cut.
- **The sound:** its words with their times (faster-whisper, `references/clips.md`, Order of work, never with `vad_filter` on a
  song: on a sung take it dropped 25 of 177 words): who speaks, to whom, how fast, and what plays under them.

Write what it shows into `reference.md` in the film's folder, each item as the setting it becomes:

| It shows                                                                                                                                                        | It sets                                                                                                                                      |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| The look, when they ask for it or name no look                                                                                                                  | A style of `references/styles.md`, or a style file of your own written from it                                                               |
| Its captions: case, words at a time, outline, shadow or label, size, height                                                                                     | The film is captioned (step 7) with these as the Captions flags, in the caption tools' nearest look where they cannot draw it                |
| Who speaks, to whom, on camera or over the picture, spoken or sung                                                                                              | `format` (`references/formats.md`)                                                                                                           |
| Its length and shape                                                                                                                                            | `durationSeconds`, `aspectRatio`                                                                                                             |
| Its pacing: average shot length, cuts in every ten seconds, close shots against wide ones, the seconds the first action and the first line land, words a minute | The shot timing of the clip prompts, in place of the base numbers of `references/story-rules.md`; its words a minute, `asked.wordsPerMinute` |
| Text on screen                                                                                                                                                  | `asked.texts`, laid over the film at assembly (`references/clips.md`, Text on screen)                                                        |
| Its structure: where the hook, the turn and the ending fall, as shares of its length                                                                            | The skeleton's beat times                                                                                                                    |
| Its sound: music under the voices, a narration, effects                                                                                                         | Assembly (`references/clips.md`)                                                                                                             |

The reference wins over this workflow's defaults in these settings, as the user's words do. It never wins over NO SENSITIVE
CONTENT, the children rule (`references/characters.md`), WHAT THE VIDEO MODEL CAN SHOW (`references/story-rules.md`) or a model's limits. Its content is
never copied: the story, the characters, their names and their lines are the film's own, and the COPYRIGHT CHECK compares the film
with the reference too.
```

**Ours**

```
From the teardown of {swipe}: average shot length, cuts per 10 s, close vs wide share, the second the first action and first line land, words a minute, beat shares (hook, turn, ending), captions look. These replace the base numbers. The story, characters, names and lines are ours.
```

Check: reference.md lists each setting with its source second; nothing of the swipe's story copied.

### 3. Script — `write.script`

Skeleton first (hook, friction, jolts, spike, ending at the card's shares), then lines of at most 10 words, 2-3 characters, one place for a film under 60 s, the product as the turn; script.json with cast, places, props and the clip plan.

| | model | credits |
|---|---|---|
| Higgsfield | the chat model directing the run + checks.py script | 0 |
| our house | Claude on the signed-in plan | 0 |
| cheapest | Claude on the plan (writing costs don't count) | 0 |

Cheap swap: Writing is free to us; spend nothing here. Registry: claude-sonnet-5.

**Higgsfield, word for word**

```
## 1. Script

Read `references/story-rules.md` (how to write the film), `references/script-format.md` (the length, the skeleton and `script.json`),
`references/characters.md` (designing the characters), `references/styles.md` (the film's look: pick the style, then read only its
file in `scripts/styles/`), `references/formats.md` (how the film is told and heard: dialogue by default, or narrated, sung, a
talking object, inside a body) and, of `references/clips.md`, Cutting the film into clips, Generations, Extend or make fresh and The
clip entry (the rest of it is for step 4).

- Write the skeleton before the dialogue: the beats for the film's length first, then the lines.
- A script the user or the card gave is reviewed and rewritten as The user's own material says.
- If the user asks for several films, write each one as its own film and follow the batch rules in `story-rules.md`.

Write `script.json` as `script-format.md` specifies, with its `clips`, then:

```
sandbox_exec({ command:"cd ~/films/<film name> && python3 \"${HF_WORKFLOWS}/drama-ads/scripts/checks.py\" script script.json --faces <number of face photos>" })
```

**Then review it as a stranger would** (the script review). These are the places where scripts fail most and the film can't recover;
the other rules you apply while writing. Fix it and check again if any answer is no:

1. **Hook:** is the first frame a conflict between two characters that reads in 3 seconds with no context (not atmosphere, not a
   document or a screen)?
2. **Obvious:** does a viewer recognise the kind of situation in 5 seconds, and know within 10 who each character is to the others,
   in the plain words of their world?
3. **On screen:** is every conflict shown, with at most one world rule the viewer must learn (what the style makes normal is not
   one)?
4. **Exposition:** does no line carry more than two facts about the world, no villain confess for the viewer's sake, and no
   character explain their feelings?
5. **Agency:** does every turn in the protagonist's favour, and the twist, come from their own deliberate act, and does nothing the
   ending turns on appear for the first time in the ending?
6. **Mute test:** do the twist and the ending read with the sound off and no readable text?
7. **Ending:** does the film end on a concrete, visible action that answers the hook?
8. **Physics:** does every move that changes where or how a character is (gets up, sits, enters, picks up) happen once, each
   later beat starting from its result (`references/clips.md`, Physical continuity); can every action happen by the world's own physics, with the objects as the script sizes and places them (each fits
   where it goes, each moves the way it is pushed), and can the video model show it: at most two bodily contacts and one
   change of state in 30 seconds, each across a cut (WHAT THE VIDEO MODEL CAN SHOW in `story-rules.md`)?
9. **Moderation:** no brands but the user's own product, no existing characters, celebrities or real people; nothing sexualised;
   human and humanlike characters clothed; a child only in an everyday scene, never in a situation the children rule forbids
   (`references/characters.md`)?

The skeleton is the same at every length; its beats fall at these shares of the running time (the 60-second times in brackets),
unless a reference video sets its own (`SKILL.md`, A reference video):

```
0%    HOOK      visual conflict, readable without context                                   [:00]
~13%  FRICTION  who vs who, where; the micro-vulnerability lands here                      [:08]
~27%  JOLT 1    pressure rises                                                              [:16]
~43%  JOLT 2    point of no return                                                          [:26]
~67%  SPIKE     re-evaluation, triggered by the protagonist's deliberate action             [:40]
~83%  ENDING    the final beat; the last spoken line starts at least 5 s before the end    [:50]
      (DWELL)   only when the story needs it: reaction on faces, in motion, at most 3 seconds, between SPIKE and ENDING
```

### OBVIOUS FIRST (above everything else in this file)

The format works because the situation is instantly obvious; the viewer stays for the emotion, never to decode a puzzle.

1. **A familiar kind of situation, a new story.** Before writing, name the ONE kind of conflict the user's idea is, in the plain
   words a viewer of any genre already knows, so it reads in five seconds. Everything inside it (who, where, the jolts, the twist,
   the ending) is invented for this user's idea and is no existing show's story.
2. **5-second read: the hook carries the relationship.** The conflict in the first sentence shows who the two characters are to
   each other, made visible in an action or said in the first line. Within the first 5 seconds a first-time viewer knows who is
   threatened or wronged, by whom, and what the protagonist wants. The :03 freeze-frame test of HOOK still applies.
3. **Relationships said plainly.** Within the first 10 seconds a line or an action makes clear who each character is to the others,
   in the plain words of their world.
4. **One-rule lore budget:** WORLD RULES.
5. **Only characters and events on screen.** Do not build the conflict on someone or something the viewer never sees.
6. **Simple, strong emotions** (fear, anger, shame, desire, grief, triumph, laughter) played big and readable. The twist reverses
   power; the ending is a concrete, visible final beat.
```

**Ours**

```
Write ONE {seconds}-second micro drama ad for {product}. Structure: {card_structure}. The kind of conflict, in plain words: {conflict} (from {avatar_profile} and {culture_map}). The hero is {hero}, the avatar, wronged or stuck by {problem}; the other side is {antagonist}. Her lines use her own words: {her_words}. The turn comes from the hero's own deliberate act: she uses {product}, and it does only what the offer bank says: {claims}. It answers the objection {objection}. Skeleton before lines: HOOK (a conflict between two characters readable in 3 s, both faces in frame, action before the first line at 1.5 s), FRICTION, JOLT, SPIKE (the product's visible result), ENDING (a concrete visible action that answers the hook; last line at least 5 s before the end; the last line may say {offer_line}). Every line at most 10 words; 70-110 words a minute. Cast {cast} only (banked), places {places}, props {props}. Clips of 10-15 s, each line ending 4 s before its clip ends. {house_rules}
```

Check: checks.py-equivalent script check passes; the nine-question script review (hook, obvious, on screen, exposition, agency, mute test, ending, physics, moderation) all yes; every claim is in the offer bank.

### 4. Viewer plan and effects — `write.plan`

3-5 points a first-time viewer must get, each with one proving shot held 1.5 s+; every visible transformation listed with its one owner.

| | model | credits |
|---|---|---|
| Higgsfield | the chat model + checks.py plan / effects | 0 |
| our house | Claude on the signed-in plan | 0 |
| cheapest | Claude on the plan | 0 |

Cheap swap: Free to us. Registry: claude-sonnet-5.

**Higgsfield, word for word**

```
## 2. Viewer plan and effects

Read `references/plan-and-effects.md`. Write `plan.json`: the points a first-time viewer must understand, each with the one shot that
proves it; and `effects.json`: every visible transformation or distinctive mark, each with its single owner.

```
sandbox_exec({ command:"cd ~/films/<film name> && python3 \"${HF_WORKFLOWS}/drama-ads/scripts/checks.py\" plan plan.json script.json && python3 \"${HF_WORKFLOWS}/drama-ads/scripts/checks.py\" effects effects.json script.json" })
```

Why: early films were "impossible to follow": the key moments were in the script but lasted a second on screen. Every plan point
becomes a required shot in its clip's prompt: `checks.py clip` refuses a clip whose prompt has no timed beat covering a plan item's
second for its held seconds (three of four films' prompts had shrunk or dropped one). A video model puts an effect on whoever is in
frame (an effect once landed on the wrong character); with its owner named in the prompt, it stays on them.
```

**Ours**

```
From script.json: list 3-5 points in story order (who {hero} is and what she wants by second 10; the threat {antagonist}; the twist {product_result}; the ending, last 10 s), each with ONE camera shot that proves it, '<framing> on <who>: <what visibly happens>; held <n> seconds', its clip and second. Effects: each visible change on a body (the problem clearing, a mark) with its one owner and a 'look' written by form and shading, never colour.
```

Check: Every plan item becomes a timed beat in its clip's prompt, held its seconds plus 0.8.

### 5. Voices — `sound.voice`

Each speaking character keeps one voice. Higgsfield lets the first clip a character speaks in make the voice, then cuts a 3-10 s sample and sends it as an audio reference to every later clip. Ours: the character's own ElevenLabs v3 voice reads a calm line in their register; that read is the sample from the very first clip on.

| | model | credits |
|---|---|---|
| Higgsfield | seedance_2_5 makes the voice in the voice clip; sample cut in the sandbox | 0 extra (inside the clip's price) |
| our house | ElevenLabs v3, one custom voice per character (eleven-v3), each line its own read; a narrated card: ElevenLabs Multilingual v2 | metered (ElevenLabs, off Higgsfield) |
| cheapest | the banked voice's existing sample (runs/ai-elements/<brand>/casting/<role>/voice/) re-used as is; else Kokoro-82M stock voice (kokoro-82m) | 0 |

Cheap swap: A banked sample costs nothing and keeps the voice across ads. Kokoro has stock voices only, no cloning: loses our own voices, use only for a test cut. Registry: eleven-v3.

On this Mac: `python3 components/local-studio/local.py tts "<line>" -o sample.wav --voice <stock> (test cut only)`

**Higgsfield, word for word**

```
## Voices

The model invents a new voice for every character it does not hear, so a voice made in one clip is lost in the next. Every clip in
which a character speaks a `dialogue` or `thought` line either hears them in its reference videos (the extension's source part or a
reference video that contains one of their lines) or gets their voice sample as an audio reference.

- **The voice clip:** of the clips in which a character speaks, the one made first (the lowest generation; among equals, the first in
  film order) makes their voice from their `voice` (script.json). Generate it before every other clip in which they speak. Give each
  speaker at least 3 seconds of speech in it, in a calm line in their normal register: a sample cut from a shout made every calm line
  of that character sound off, and a 1-second line left nothing to join. A first clip of 15 seconds holds about two voices (the hook's action
  first, the 4-second tail last), so a third speaker's voice clip is another clip of the first round. When another checked take made
  the voice (a remake, a take left out of the film), name it in that character's `voiceFrom` (`script-format.md`). A narrator
  of a narrated format has no voice clip: the narration track is their voice, and their sample is cut from it (`formats.md`).
- **The voice sample:** once the voice clip is checked, cut 3-10 seconds of that character speaking alone from it: no other voice,
  no loud effect. One sample per character, used in every later clip; never a sample cut from a clip that itself got the sample (a
  copy of a copy drifts). A single line shorter than 3 seconds is joined with another line of theirs from the same clip; with none,
  repeat it or pad it with room tone to 3 seconds (both held the voice).
- **Finding the moment:** the line's `startSeconds` minus its clip's `start` says roughly where it is; the word times from faster-whisper `medium` (Order of work) say roughly where it starts and ends: against the voice's onset on a spectrogram, a line's first word in its clip's own pass started a median 0.15 s early, 32 of 100 lines more than 0.3 s off; after 2 s or more of silence in the clip 12 of 62 lines started 0.5-2.0 s early (the word stamped where the silence began), and the whole-film pass still put 23 of those 62 more than 0.3 s off. Its last word ended a median 0.06 s off on 40 lines (`small`: first words 0.29 s early, 19 of 40 more than 0.3 s), the worst 0.8 s late, so listen to a sample's last half second for the next line's first word. A frame at its middle shows whose mouth moves.
- **In the prompt:** bind each sample to its character by both tags: "@Audio1 is the voice of @Image2, <the character by its look>:
  every line <he | she | it> speaks is in this voice." Then write each line under its character, never under the audio.
```

**Ours**

```
@Audio{n} is the voice of @Image{m}, {NAME}, {voice_register_words}: every line {he_she} speaks is in this voice. (Sample: 3-10 s of {NAME} alone, a calm line in the normal register, read by voice_id {voice_id}.)
```

Check: Sample 3-10 s, one speaker, no effect; heard back (Scribe) word for word; median pitch matches the voice record.

### 6. Narration track (storytime cards only) — `sound.narration`

Only when the card is storytime, song or inside-the-body: one narration track in one fixed voice, made before the clips; its slices go to the clips as audio references.

| | model | credits |
|---|---|---|
| Higgsfield | seed_audio (generate_audio_batch), preset voice, speech_rate | priced at its stage (not quoted here) |
| our house | ElevenLabs Multilingual v2, voice record job: narration (one stitched storyteller read) | metered (ElevenLabs) |
| cheapest | Kokoro-82M local tts, stock voice (kokoro-82m) | 0 |

Cheap swap: Free, stock voices only: fine for a timing draft, not for a finished ad in our narrator's voice. Registry: kokoro-82m.

On this Mac: `python3 components/local-studio/local.py tts "<narration>" -o narration.wav --voice <stock>`

**Higgsfield, word for word**

```
**A narration track or an a-cappella song: `seed_audio`** (`generate_audio_batch`). This concerns only an off-screen narrator; the characters' own voices are
made in the clips and carried by voice samples (`clips.md`, Voices).

- **The same voice on every call.** Each call sends `voice_type` (`preset` for a catalogue voice, `element` for one the user
  saved) and `voice_id`, the same on every call. Without them the provider picks a voice per request, and every take comes back in a different
  timbre (the narration workflow measured six voices in one video).
- **Choosing the voice.** `list_voices` lists them.
  - The user picks the narrator from that list. This is the one question a narrated film asks.
  - When the user named a voice, take it from that list; when nobody can answer, a preset voice whose gender fits.
  - Tell the user about a name the catalogue lacks, and never replace it silently.
- **Speed.** `speech_rate` 30 speeds a narration up, but one preset at 30 read 140-197 words a minute from film to film
  and one request 146 and 237 in two takes: measure every take (`formats.md`).
- **A song.** Put the singing direction in brackets, where it is not sung, then the lyrics: "(singing a slow folk melody, long held
  notes on every line, slow tempo) <lyrics>".
```

**Ours**

```
{narrator_lines in order, nothing else}, read by {narrator_voice_id} at 160-175 words a minute.
```

Check: Words a minute measured on the take; every line present in order.

### 7. Reference pictures — `pictures.sheets`

Live action: a three-panel sheet per character, a two-panel location sheet per place, a two-view prop sheet per prop (the product's label exact). 3D/2D: the style master first, then every sheet from it.

| | model | credits |
|---|---|---|
| Higgsfield | live action: seedream_5_5 / seedream_v5_pro, 2k, 16:9; 3D and 2D: gpt_image_2_6_flare 2k (master high, the rest medium) | 2.5 each (seedream_v5_pro); master 2.25, others 1.75 (flare); ~6-8 sheets = 15-20 |
| our house | our banked cast sheets, sets and product sheet (0); a missing sheet only: GPT Image 2.5 (gpt-image-2.5) | 0 for banked, ~2 per gap |
| cheapest | Seedream 5.0 Flash, 2k (seedream_5_0_flash) | 0.5 |

Cheap swap: Only for a sheet we have no bank for. Banked sheets cost nothing and keep the cast the same across ads. Registry: missing.

**Higgsfield, word for word**

```
## 3. Reference images

The template's family (`references/styles.md`) decides how they are made; the models and settings are in `references/models.md`.

**Live action.** For each character, write a sheet prompt:

- `references/sheet-realism.md`: human characters; its face-photo section applies when they have a face photo, and its
  same-face section to a double or twin (both `--photo`; make the original's sheet first).
- `references/sheet-stylized.md`: a non-human character, as a real, photographed thing of its kind.

For each location the user gave no photo of, write its prompt with `references/location.md` from that location's `description` and
`light`. For each prop the user gave no photo of, a prop sheet from its `description`, made with the film's live-action image model (16:9, 2k, `references/models.md`): "A
prop reference sheet of <the prop>, as a prop of a photographed live-action film: <its description>. Photographed for real: true
texture, true colour, the true state it is kept in. Two views side by side on a plain light-grey background: a front view at eye
level and a three-quarter view from above. Soft, even studio light from the front, the same in both views. One object only. No
text, labels, logos or watermarks." (one film's prop kept its shape and colour in every shot this way); every clip that shows it
sends it (`clips.md`).

**3D and 2D.** Follow `references/style-master.md`. First the style master: the film's main place with its characters and props in
it, its prompt opening with the style file's style block. Then, with the master attached and the style block copied into each: a
sheet per character (`references/sheet-stylized.md`); per place a two-panel location sheet (`references/location.md`) and a prop
sheet per prop in 3D, or background plates with the props in them and a prop sheet per prop that moves in 2D. In 2D every sheet
shows the character or prop from all sides (`--2d`). The user's photos go where The user's own material says.

Check every prompt before its call (`<checks>` is `python3 "${HF_WORKFLOWS}/drama-ads/scripts/checks.py"`, run with
`sandbox_exec` from the film's folder; `<style>` is `"${HF_WORKFLOWS}/drama-ads/scripts/styles/<template>.md"`):

```
<checks> sheet sheet-<id>.txt [--photo] [--stylized] [--2d] [--style <style>]
<checks> location location-<id>.txt [--style <style>]
<checks> master master.txt --style <style>
<checks> prop prop-<id>.txt [--2d] --style <style>
<checks> plate plate-<id>-<n>.txt --style <style>
```

`--style` goes on every image of a 3D or 2D film made from the master: the style block must be in it word for word. An edit of the
film's own frame (`clips.md`, References from the film's own frames) keeps the frame's look and takes none.

Generate them through `generate_image_batch` as the Generations bullet says (in 3D and 2D the master alone first, then the rest
with the master's job id attached), a double's sheet after its original's, each item as Sending says. **Look at every image before going on:** one
character, the sheet's panels, everything the facts give (for a human the right gender, age, skin, hair and clothes; for any other
character its form, size, material and colours), the template's look, no text, nothing odd; look at each image beside the master or
the photo it must match. Remake an image that fails (the master at most once: `references/style-master.md`, Order of work): every
clip is built on it, so a bad sheet is paid for in every clip. A face that looks like a celebrity gets clips stopped by moderation
(`ip_detected`). This is Stop 1 (Stages in ask mode).
```

**Ours**

```
Character (only when not banked): a {age}-year-old {gender}, {ethnicity}, {skin}, {eyes}, {hair}, {marks}; wearing {wardrobe}; three panels on a plain light-grey backdrop (front costume view, rear costume view, head-and-shoulders face), soft even studio light from the front, empty relaxed hands. Place: two panels, the camera view toward {anchor} and the reverse view, no people, {light}. Prop: A prop reference sheet of {product}, as a prop of a photographed live-action film: {product_shape_words}. Photographed for real: true texture, true colour. Two views side by side on a plain light-grey background: front at eye level and three-quarter from above. Soft, even studio light from the front. One object only. The label exactly as {product_photo} shows it.
```

Check: Look at every sheet beside its master or photo: right age, skin, hair, clothes; one character; the label exact; no celebrity likeness. Banked sheets are already signed off.

### 8. Frame plates — `pictures.plates`

Round 2 clips in a place an earlier clip filmed take that clip's frame as a plate (edited to remove the cast, relit for a time jump), so the place keeps its layout.

| | model | credits |
|---|---|---|
| Higgsfield | seedream_5_5 / seedream_v5_pro edit of the frame, 16:9 or the film's shape | 2.5 each |
| our house | GPT Image 2.5 edit (gpt-image-2.5), image-to-image from the frame | ~2 each |
| cheapest | Seedream 5.0 Flash edit (seedream_5_0_flash) | 0.5 |

Cheap swap: A cheaper edit can leave a ghost of a lead in the plate; look at it before it goes to a clip. Registry: missing.

On this Mac: `ffmpeg -ss <second> -i k1.mp4 -frames:v 1 frame-k1@<second>.png`

**Higgsfield, word for word**

```
## References from the film's own frames

The reference images set the design before any clip; after that, a clip's place, its changed states and the props a clip drew first
are taken from the film's own frames. A fresh clip made from such references matched its source clip as closely as an extension did
(four tests in four looks), while separately drawn references drift (two plates of one place came out as two places).

- **Frame plates.** When a clip returns to a place already filmed, or must carry where things stand or what state they are in, take
  the frame of the earliest clip there that shows it, one per direction the new clip's shots face (a direction no earlier clip faced
  keeps the location sheet's panel), remove from it every character and the props that move or are carried in the new clip (in 3D
  a prop the new clip's first frame shows in its place stays even when it moves later in the clip: removed, a prop that stood in its place
  at the first frame and fell later was missing or did not fall in 2 of 3 takes; kept, it stood and fell as written in 3 of 3 and was never
  drawn twice, judged blind; a prop that only sits still there stays: it held its size best in its place; so does a crowd still there in the new clip: kept in the
  plate, a crowd stayed the same people, while a plate cleared of it gave one clip other people, a row of look-alikes,
  and one film's next two clips nobody where the crowd had been), and send it first in `images`, with the location sheet in
  3D and in place of the background plate in 2D (`images`: `frame:k1@8.0`; generation + 1; in 2D the plate it replaces is left out
  and the other is named by position, `["frame:k1@0.0", "l1#2", …]`, `script-format.md`). A 2D clip's first frame reproduces its
  plate almost exactly, so its second 0 is the cleanest source. A frame from inside a clip comes from the shot itself, not from the
  prompt's timing: the model's cuts land up to a second off the written seconds (a frame taken by the timing showed the shot
  before). Find the cuts as Order of work, Stubs, says, take the
  frame about 0.3 seconds after one, and look at it before the edit. When the edit fails, the clip keeps the location
  sheet alone, with the positions written against its anchor. When the new clip comes earlier in the story, the edit also restores
  the earlier state of what changed. Check it with `python3 "${HF_WORKFLOWS}/drama-ads/scripts/checks.py" plate plate-<id>.txt` (a tagged
  frame's edit: `plate-k1@0.5-morning.txt` for `frame:k1@0.5/morning`). A plate a lead will stand in has nobody in it who shares
  that lead's age, hair or clothes colour, and nobody where the lead will stand: a figure in the plate the edit aged into the lead's look took the lead's place and clothes (2 of 2);
  edited into someone unlike the lead in sex and clothes, the lead came back in their own clothes (2 of 2, judged blind). The
  edit: "Edit the attached reference image, one frame of a <template name> film: remove <each character by its look and its place in
  the frame> and <each such prop>, and fill what they covered with the place itself, continuing exactly what surrounds it:
  <surfaces>. Keep everything else exactly as it is: the same framing, <the objects whose place or state matters>, the light and the
  look. No people, figures, silhouettes or animals anywhere, in windows and reflections too; the place stands empty. No text, labels,
  logos or watermarks." A plate that keeps its crowd writes "<the crowd> stays exactly as it is; no other people, figures,
  silhouettes or animals anywhere, in windows and reflections too." in place of the empty-place sentence, and it is edited from a
  frame where the characters it removes cover none of the crowd: removing two leads who stood in front of it, the edit drew 5-8 new
  people where they stood, a child among them (2 of 2); from a frame where they covered none, it added nobody (2 of 2). Look at it: a second edit naming whatever was left removes it. A change of time of day goes in the same edit
  ("show this same place at <the time of day>; relight it in <the light and its side>").
- **Sheets from frames.** A prop a clip drew first, and a character or prop after it changes on screen, gets its sheet from that clip's frames: crop the frames that show it best, the face close first and then full-figure
  crops, tile them at one height into one composite (`ffmpeg -i a.png -i b.png -i c.png -filter_complex hstack composite.png`; in
  pixel art scale with `-sws_flags neighbor`), and edit it with the sheet wording of `sheet-realism.md`, `sheet-stylized.md` or
  `style-master.md` (prop sheets), adding "The attached reference image is <n> film frames of this one <character>, side by side: keep
  the face as in the close frame" and the finish sentence of a prop sheet or the sheet words of the style file (without it clay
  props came back as product photographs).
  Frames from two clips: name which frames give the face and which the body. Frames lit at night: "draw it in its true daytime
  colours: the night light belongs to the frames". Name the size of what changed against a part of the character, and how much of it shows: the edit shrinks what the frames
  half hide. Check it: `checks.py sheet … --stylized` for a
  character in 3D or 2D or a non-human in live action, `checks.py sheet … --photo` for a live-action human (the composite is its
  attached reference image), `checks.py prop …` for a prop; a sheet from frames may run to 2,600 characters. A sheet made from a clip's frames counts as a
  frame of that clip: write the clip in the prop's `sheetFrom`, or in the character's form in `forms` (`script-format.md`).
- **The first clip in a place** holds one wide shot per direction later clips will face, showing every prop they will need there:
  frame plates carry only what it framed (an object it never showed drifted to another spot in one clip and was drawn twice in
  another). In 2D `checks.py clip` refuses a place's first clip without a wide or medium-wide beat on each plate it sends, and a
  wide beat that also names a body crop ("from the chest up") does not count: written so, one first clip framed only the figure and the furniture in front of it.
- **The first frame takes its state and its camera height from the plate sent first, never from the words.** Make the plate in
  the state the shot opens in and at the camera height its shots need, and write no move the plate has already made: written "at
  standing eye height" over a high plate, the camera stayed high in 6 of 6; the plate remade at eye height (a new photograph of the
  same place from that camera position, not an inpaint edit: the inpaint edit kept the high camera), 3 of 3 at eye height (judged
  blind). A clip after something in the place was opened, sent the half-open plate with the opening move written again, opened on it shut in
  4 of 4; sent a plate with it fully open and the state written as it is
  ("<the changed thing> stands <in its new state>, as in @Image1, from the first frame"), every shot stayed open (3 of 3,
  measured and judged blind). A closing move went the way its first frame allowed in 8 of
  8, and a change of state drawn on an object in the plate stayed on it (2 of 2; 0 of 2 without).
- **Frame-plate edits keep the frame's own look:** they take no style block, and `checks.py` skips `--style` on a prompt that begins
  "Edit the attached reference image".
- **Remaking a part of a clip** (Cutting the film into clips): the remade part is a clip of its own with a new id, placed in film
  order in `clips`; the kept part and the remake each carry `kept`.
- **The edit model:** `gpt_image_2_6_flare` (medium, 2k) in 3D and 2D, in live action the film's live-action image model as an
  edit of the frame (`models.md`).
- **The frames' faults become canon:** check a frame before deriving from it. No extra video to show a back view: a text-only
  turnaround drew another face and another room, and the edit draws a believable back. A location plate comes from the frames of one
  clip: two clips' frames gave two rooms in one sheet.
```

**Ours**

```
Edit this frame of {place}: keep the place, its light and every fixture exactly; remove {cast_in_frame}; {relight_if_time_jump}.
```

Check: Nobody who looks like a lead left in the plate; layout matches the clip it came from.

### 9. Clips, round 1 — `clips.scene`

The first clip in each place and each speaker's first clip, 10-15 s each, up to 9 images (plates, place, cast, props) bound by @Image, voice samples bound by @Audio, timed beats, sound on (the clips carry the dialogue).

| | model | credits |
|---|---|---|
| Higgsfield | seedance_2_5 omni_reference, generate_audio true, 9:16, the film's resolution (1080p default) | 160 per 10 s at 1080p; 30 per 10 s at 480p |
| our house | Seedance 2.5 (seedance-2.5@higgsfield, clips.take) at 480p, upscaled on this Mac; our ElevenLabs v3 voice samples as audio references | 30 per 10 s (45 for 15 s) |
| cheapest | Wan 3.0, 480p, reference-to-video with native audio (wan-3.0@higgsfield) | 7.5 per 10 s |

Cheap swap: Takes up to 10 image, 5 video and 5 audio references (our voice samples), 2-30 s, the same @Image/@Audio binding and timed beats. Lose: Seedance's tested lip sync to a bound sample and its cut timing; Wan's dialogue lips are untested in our runs. Gemini Omni Flash 1.2 (7.5) takes no audio references, so it loses our voices: not for dialogue. Registry: wan-3.0.

**Higgsfield, word for word**

```
## 4. Clips

Follow `references/clips.md`: write each clip's prompt and check it
(`python3 "${HF_WORKFLOWS}/drama-ads/scripts/checks.py" clip clip-<id>.txt script.json <id>`), generate the originals
first through `generate_video_batch` as the Generations bullet says, look at and listen to each one (step 6's checks, clip by clip) before anything is built on it,
then the clips made from them, generation by generation.

- A character keeps one voice through the film: the first clip they speak in makes it, and every later clip that does not hear them
  in its reference videos carries their voice sample (`clips.md`, Voices), uploaded from the sandbox with `media_upload` → PUT →
  `media_confirm` and attached by its media id.
- Later clips take their place, the changed states and the props a clip drew first from the film's own frames (`clips.md`,
  References from the film's own frames).
- Every clip call carries what Sending lists, and every take is measured as Checking a result says.
- In a narrated format the narration track or the song is made before the clips (`references/formats.md`), with
  `generate_audio_batch`.
- Model settings are in `references/models.md`. Save every job id in `jobs.json` the moment you get it. Each round is a stage
  (Stages in ask mode).

## The clip's prompt

Write it into `clip-<id>.txt` and check it with `python3 "${HF_WORKFLOWS}/drama-ads/scripts/checks.py" clip clip-<id>.txt script.json <clip id>`.

- **The order:**
  1. the film's `style` line;
  2. its style file's video words (`scripts/styles/<template>.md`);
  3. the clip's action beat by beat, in literal camera terms, each beat its own paragraph opening with its seconds
     ("<from>-<to> s: <framing> …"): `checks.py clip` reads only those, and a prompt without them is refused;
  4. its dialogue (speaker, words, delivery);
  5. its effects (`effects.json`, `plan-and-effects.md`), each named only on its owner.

  In a clip where nobody speaks on screen, leave out the video words' sentences about mouths and voices.

- **The hold sentence**, where the style file's video words have one, goes to the end of the prompt, not after the style line. It names every element of that clip the look must cover:
  - its characters, in close-up and in motion;
  - its props and effects;
  - its sky and light (stars and lamplight at night, clouds and sunlight by day).

  It says what each element is, never what it must not become: "nothing turns into a 3D render" drew a 3D-render preset suggestion on
  every clip. A clip that cuts between places adds "in both places".

- The language, word for word, in every clip with speech: "Every spoken line is in American English, exactly the words in quotes;
  nobody speaks any other language." Without it a whole clip came back spoken in Mandarin.
- No music, word for word, in every clip's prompt: "No music and no score." The video model sometimes adds a score of its own,
  and music belongs over the joined film (Assembly). A clip that lip-syncs its part of the song has its own sound sentence instead
  (`formats.md`).
- The hook's physical action comes at 1-3 seconds with both characters in frame through second 3, and the first line only after it
  lands: an action written at second 0 was played in half a second, and a line at 0.5 seconds turned a shove into a touch. In the
  hook's shot neither has their back to the camera or stands between the camera and the other, so both faces and the action between
  them read in one frame through second 3: written with one's back to the lens, both faces showed at second 3 in 0 of 3 takes (and
  one brief opened on a back in three runs); written so, in 3 of 3, and the conflict was retold from that one frame (judged blind).
- Lines land from 1 second early to 1.5 seconds late, and later after a long stretch before them in their clip: up to 3.7 seconds late after an opening action of several seconds, 2-4 seconds late after an action of the speaker's own written before the line in its shot or a long insert before it, 2.65 seconds late after a silent reaction shot that ran 1.9 seconds over its writing, and the next line late with a late one, 4.7 seconds (nine lines in three films; an insert written 2.8 seconds ran 5.3). Time
  the beats by the take, never by the plan, and time the clip's last line so it ends at least 4 seconds before the
  clip's end, and put the ending's action after it. Every shot after a clip's last line says so in its own words ("in silence, <the
  action>"): a silent 4-second shot written without it came back with the last line said a second time over it.
- Every shot says each character's posture (`checks.py clip` refuses a beat that names one without it; a name or tag inside the description of a depiction, from "photo", "portrait", "picture", "drawing", "painting" or "poster" to the end of its clause, is not read as the character in the shot, so a character who is in the shot is named before it or in a sentence of their own) and, at a door, a window or any edge the action turns on (a curb, a threshold, a
  counter), which side of it and on which surface they are ("<the character> stands <inside | outside> <the opening>,
  <behind | in front of> <its edge>"; "<the prop> <in the place> <below | above> <the edge>, on <the surface it stands on>,
  <the edge> and <the surface beyond it> behind <her | him | it>": a prop written only by the space it stood in was set on the
  surface beyond the edge 2 of 2 times, written so on its own surface 2 of 2, judged blind), and where a prop out of frame is ("<the prop> on <the surface> to the <side>, below the
  frame"): a background plate that shows seats sat a standing character down, a character came out drawn outside their own door,
  and a prop left unplaced moved in front of two close-ups. In a close-up, write where the table or counter in front of them ends and what lies on it out of frame ("<the furniture>'s
  edge at <the part of the body it reaches>, below the frame; <what lies on it> out of frame"): a close-up over a counter drew what
  lay on it as a mound filling the lower third of the frame, the body sunk into it.
  A face wanted from a character who stands on the camera's side of a table or counter comes with the camera turned around: behind
  the furniture, looking across it at them, toward what is behind them, named by its location-sheet panel ("from behind <the table>,
  looking across it at <the character>, toward <what that panel shows>"). With the camera facing the furniture and the character
  written "in front of it", the face was given by drawing the character behind it or beside its end (3 of 3); written so, the character stayed on their own
  side, face to the camera (3 of 3, judged blind), though the plate sent first still faced the furniture from their side. A shot that shows a piece of
  furniture together with a character standing on the camera's side of it, from a medium shot to a wide, writes that character seen
  from behind or at three-quarters from behind, on <their> side of it, and turns <their> face to the camera only after <their> action
  there ("<the character> stands on the camera's side of <the furniture>, seen from behind at three-quarters, <their> back half to the
  camera; <the action>, then <they turn> <their> face over <their> shoulder to the camera"); a close-up, or a shot that leaves the
  furniture out of frame, keeps the face to the camera as written. Written turned three-quarters toward the camera, the characters
  were drawn behind the furniture in 4 of 6 takes of a test (and 3 of 4 takes over two films); written so, on the camera's side in
  6 of 6, and a close-up written after it kept the face (6 of 6, judged blind).
  A door, gate or window a character opens is two shots: their hand on the key or the handle (an insert), then the opening seen
  from their side, their back to the camera, the features of their side of it named around them in frame and what lies beyond only
  through the opening ("from behind <the character>, on <their> side of <the door>, <their> back to the camera, <the features of this
  side> around <them> in frame; through the opening, <what lies beyond>"): written as one shot facing the door, the opener was drawn
  on its far side in 2 of 2; as the two shots alone, on the camera's side, but with their own side drawn again beyond the door in 3 of 5;
  with this side's features named around them, on their own side in 3 of 3 (judged blind).
- **Every shot has its subject in frame from its first frame,** and a clip opens and ends on a character or a story prop, never on a
  surface: the model likes to open and close a clip on a transition. Written as an entrance through something the character first moves aside, one clip opened
  and closed on a second of it filling the frame, nobody in it. Write an entrance with the character
  already in frame ("<the character> steps through <the opening>, in frame from the shot's first frame").
- **The last frame is written by who and what are in it.** A shot that ends on a flash, a glow or a whiteout names what is seen when
  it clears, every subject in it: written as the white "fading on <one subject>", one film's last shot showed that subject alone on
  black, the others in it gone.
- In the film's last shot, a character who leaves is written by the frame side they leave by: <the one who leaves> at that side of
  the frame and whoever stays at the other, <the one who leaves> walking out of frame <side> in a straight line along <a feature
  that shot's view shows>, past <a landmark on that side>; whoever stays is written still, in full view from the first frame to the
  last. Written as a walk toward a place the view does not show, the one who left crossed in front of the one who stayed and hid
  them (1 of 1 in a film), and stayed in frame to the end in 2 of 3 takes; written so, they left by the named side with the other in
  full view in 3 of 3 (judged blind). Exits in other shots follow their own action.
- A delivery never asks for a pitch against the character's `voice` ("low, slow" for a high voice, "a wail" for a bass): it swapped
  or replaced the voice. A shouted or panicked line of a low voice restates its register in the voice's own words, never "yells", "screams", "shrieks" or
  "loud": an "outraged" delivery flipped a bass to a shriek even with the voice sample, and "loud and rough" with the register named
  still lifted a line an octave. Put the register in the voice binding too ("@Audio<n> is the voice of @Image<n>, <name>: <the voice's
  register words>"): together they brought the line back down.
- Each prop at the moment it acts is named again by its tag with the detail that tells it apart ("@Image<n>, <the prop>, <the
  detail>"), with its size against a part of a character; every shot that shows it names it so. A prop told apart by its container
  is written with the container ("<the prop> in the <container's colour> <container>"), never with the container's colour on the
  thing ("the <container's colour> <prop>"), and a part of it in its own colours ("<a portion> of <its own colour> <its part>"):
  written with the container's colour on it, the prop came out in that colour in 2 of 2 takes (and in 4 of 4 shots of one film),
  written so in 0 of 2 (judged blind); so is a place feature the action uses, with its size against the
  character. A change that must stay is written to the end: "from <second> to the last frame <the changed state> stays". A part of
  a character is never named alone: it is drawn as a separate thing. A mark the story turns on holds only on a prop with its own
  sheet, shown in an insert: among alike things without one it came back as other marks.
- **One of each person.** A character drawn twice in one shot (a twin beside them, their double in the background) came from
  their sheet's several views, a figure left in a frame plate, or a beat that named them twice in two places. So the sheet's
  reference sentence says it is one person ("@Image2 is Marco, one man, shown from several angles"), every beat with people in
  it says how many are in frame and who ("two people in frame: Marco and Ana", "Marco alone in frame"), each character named in a
  beat in one place only, and a frame plate keeps nobody who looks like a lead. Look at the middle frame of every shot for a
  repeated face or outfit (step 6 of `SKILL.md`); a shot with one is cut out through `kept` when silent, else remade.
- What makes a character recognisable (an accessory, a mark) is named in their reference sentence ("@Image<n> is <name>, always
  <the feature>") and in every shot of them: named once per clip, the feature was gone from every shot of two clips, and named so it
  held in every later clip.
- Two identical objects the story turns on merge into one: show both in one shot, or make them differ visibly.
- Machines, packs and signs get printed words and badges: write them as "a plain unbranded <thing>" in every prompt. The user's own
  product is the exception: it keeps its name and label as its prop sheet shows them (`style-master.md`, Prop sheets); written
  plain, an ad's product came back with its name nowhere on screen.
- **The user's product's label reads only in a close insert** where the product fills the frame, upright and whole: at 480p small
  or tilted lettering is redrawn as look-alike letters, and in a medium shot a two-line label did not read.
- **Every prop in frame sends its sheet** in `images`, in every clip that shows it: sent only the place and the characters, one clip
  drew a prop in its case as another object. `checks.py clip` refuses a prompt that names a prop whose sheet the clip does not
  send.
- **A crowd is written by how it fills the place, never by a number,** with the ages of its `groups` entry written as what shows
  them ("every one an adult of <their ages>: <the hair and the lines of those ages>, adult height and build"), behind the action and
  out of focus: a film that wrote its crowd as a dozen people showed four in one clip and a changing crowd in another, its far faces smeared at
  480p; written without ages, two crowds meant as a <number>-year-old lead's age-mates came out decades younger.
  With the ages alone, a 3D crowd of that age still had members younger than written in 1 of 3 takes (2 of 6 clips of one film), and
  with the group's whole description (its hair colours, its clothes colours) in 3 of 3; with the ages and their marks, none in 3 of 3
  crowd-only shots (judged blind), but in films with the cast in front the same wording gave a crowd decades younger in one take and an
  older one in the next, and a child in another: ages written in words drift from take to take, so the first take that shows a crowd is judged face by face
  before its frame becomes a plate. Nothing else of the description goes with them: written with its mix and its clothes colours added, 3 of 3 takes had
  members younger than written again (one to seven each), and with the marks written for every member and the mix kept, 2 of 3 still had
  one (judged blind); the marks alone keep the ages and can lose the mix. Anyone the story singles out of a
  crowd is a cast member with a sheet. A shot that shows none of the cast is a clip of its own that sends no cast sheet: in a
  clip that sent them, a crowd shot drew a double of a cast member (2 of 2, and 2 of 2 with "<name> is not in this shot");
  sent none, it drew nobody like that cast member (2 of 2).
- **Spell out the shot and the face.** The model frames wider and plays milder than asked: a line marked only "firm" was played with a
  smile. So write:
  - each shot's size and framing, and the size of each gesture;
  - every expression in face words: what the brows, eyes and mouth do;
  - a gesture as its own beat rather than timed to a single word, where it may not show;
  - a hand one character holds out toward another framed over the receiver's shoulder, both in shot ("over <the receiver>'s
    shoulder onto <the giver>: <the receiver>'s shoulder and the back of <their> head soft at the near <side> edge of the frame"):
    in a close-up on the giver alone, the hand came in from the frame's edge on the receiver's arm (1 of 1 in a film, 1 of 3
    in a test); framed so, the giver's own arm in 3 of 3 (judged blind);
  - a look as the face that looks ("<the character> looks down"), never as its target: a look written as its target became a
    camera tilt down to the looker's own body. A glance at something behind the camera is a direction ("glances to <their> left, past
    the camera"), and in a clip whose shots all face away from it, nothing behind the camera is named anywhere in the prompt (its
    @Image sentence says only "<the place> seen toward its far end"; its light and sky are left out): named, even "out of frame
    behind the camera", it was drawn behind the character in 6 of 6; named nowhere, the plate's view in 3 of 3 (judged blind).
- One physical action per shot. A bodily contact is a wind-up, a cut and the aftermath; a change of state is a shot before, a cut and
  a shot after (WHAT THE VIDEO MODEL CAN SHOW, `story-rules.md`), the after shot opening a clip of its own that sends the
  after-state's form sheet: inside one clip, a face between them or not, the after shot opened in the before state and changed on
  screen (4 of 4 for a prop joined to a piece of it that had come off, one fused into one piece); opening its own clip, it was right from the first
  frame (2 of 2, judged blind). That clip opens on a close insert of the changed thing or on the reverse view, never on the view the
  clip before ends on: opened on the same view, the cut read as a jump, someone moved (2 of 2); opened so, it did not (0 of 2,
  judged blind). A move that opens or changes a place's light (a window covering drawn back, a door flung wide) is written as a
  slow pull ("<the action> <the place's light-changing fixture>, the gap widening over <seconds>"): written as a fling it opened in 3-5
  frames in two films; written so it moved over 33 and 69 frames, though one take still cut away a third open. Write every state as it is, never the failure to avoid ("it stays
  joined", "it never comes back"): the model draws what the words name.
- A state of a fixture a character works by hand (open, shut, on, off) that a later shot names is changed on screen in the shot
  before, by a hand, as that shot's last action ("<the hand> pushes <the fixture> shut, and from <second> to the end of the shot
  <the fixture> stays shut"), or the later shot opens its own clip from a plate in that state; it is never written only as the later
  state. This is for fixtures a character works by hand, not for light or weather: written only as the later state, the fixture moved
  with nobody touching it in 3 of 3 takes; changed by a hand in the shot before, in 0 of 3, and the shot's own action still played in
  3 of 3 (judged blind).
- After a prop or a character changes, the clips that show the after-state send that
  state's sheet in place of the before one (`style-master.md`, one entry per form), and every shot names the after-state or keeps it
  out of frame: a shot after a prop changed showed it in its before state again, and a framing that left it out fixed it.
- A character's voice clip carries their `voice` words with their first line ("in <his | her | its> <voice words>").
- **Name the references by their tags:** "@Image1 is <the place>: its left panel faces <its far end>, its right panel faces back
  to <its near end>; @Image2 is <name>, <the character by its look>; @Image3 is <the next one, by name>…". The tags count the
  clip's `images` in order, so adding or dropping one moves every tag after it (dropping one reference renumbered four prompts of
  one film): `checks.py clip` refuses a reference sentence that does not name the character or prop its number sends.
- **The background.** The model may take a shot's background from the wrong panel or plate, whatever the tags say. Name the
  landmarks it must show inside the shot, each with its side, and check each shot's background.
- **An extension:** "@Video1 is the clip being continued: keep <what stays exactly>; this clip adds <what is new>". Never restage
  what the source already shows.
- **Voice samples:** bind each one to its character as Voices says.
- **In 2D:**
  - Name the plates: "@Image1 is <the place> seen toward <a landmark>; @Image2 is the same place seen the other way, toward
    <a landmark>".
  - Write each shot as "the view of @Image1, static camera", with its framing in words, or with the camera move its style file
    allows. A plate sets the place, never the framing.
  - In a flat world, with one backdrop, write "@Image1 seen straight on, static camera".
- Write `positions` and `stateIn` as present facts of the first frame. A fresh clip never says "continuing from the previous shot":
  the model replays the old ending as the clip's first second. Only an extension refers back, and only through `@Video1`.
- Time the beats in the clip's own seconds, 0 being its first frame, an extension's included.
- Leave music out of the clips: music made in separate clips drifts when they are joined; add a score at assembly if the film wants one.
  The one exception is a clip that lip-syncs its part of the song (`formats.md`).
- Only what a camera films goes into a prompt. A fade, a dissolve, slow motion or a title is made at assembly: a fade to black
  written into a clip was ignored.
```

**Ours**

```
{style_line} (live action: Cinematic live action, camera-ready faces in soft, bright, flattering light from the scene's own sources, natural colour.)
{video_words}
@Image1 is {place}: its left panel faces {far_end}, its right panel faces back to {near_end}. @Image2 is {NAME1}, one {person}, shown from several angles, always {signature}. @Image3 is {NAME2}, ... @Image{p} is {product}, {label_detail}, {size_against_hand}.
@Audio1 is the voice of @Image2, {NAME1}: {voice_register_words}: every line {he_she} speaks is in this voice. @Audio2 ...
0-{t1} s: {framing} on {who}, {posture}; {n} people in frame: {names}; {action with its cause and result}.
{t1}-{t2} s: ...
{NAME1} ({delivery in face words}): "{line, at most 10 words}"
{effects, each on its owner}
Every spoken line is in American English, exactly the words in quotes; nobody speaks any other language. No music and no score. No subtitles or on-screen text.
```

Check: Send the first clip alone and check it (9:16, resolution, length, ffprobe). Then per clip: contact sheet at 2 fps, every line heard in its speaker's voice (Scribe + pitch), no stray music, one of each person, the label legible in its insert.

### 10. Clips, round 2, extensions and remakes — `clips.extend`

Every other clip in one batch with the round 1 frame plates and voice samples; extensions continue a clip forward or backward; remakes of a failed beat join this round.

| | model | credits |
|---|---|---|
| Higgsfield | seedance_2_5 omni_reference or video_extension (forward/backward), same settings | 160 per 10 s at 1080p; 30 per 10 s at 480p |
| our house | Seedance 2.5 at 480p (seedance-2.5@higgsfield); a refusal moves down the take routes (Wan 3.0 start-frame, then fal) | 30 per 10 s |
| cheapest | Wan 3.0, 480p (wan-3.0@higgsfield) | 7.5 per 10 s |

Cheap swap: No video_extension mode tested here: a continuation is a fresh clip from the frame plate. Retry ladder still caps at about 6 tries. Registry: wan-3.0.

**Higgsfield, word for word**

```
## Planning the rounds

Clips that need nothing from each other run in one batch, so a film takes as many rounds as its longest chain of waiting. Plan that
chain before the first paid call, while writing `stateIn` and `stateOut`.

**1. List the states.** For every clip, write down:

- its place;
- its time of day and light;
- the state of every prop and character at its first and last frame.

**2. Prepare every state in step 3.** Some states a later clip opens in would otherwise exist only once an earlier clip shows them on
screen: a prop or a character after it changes, a place in another light. Make each such state's reference
with the other images, from the master:

- a form sheet for a prop or a character (`forms`, one entry per form);
- a plate or a location sheet for a place in another light.

The later clip sends that reference and none of the old state's, so it no longer waits for the clip that shows the change and runs in
the same batch. The change itself is still shown on screen, as a shot before, a cut and a shot after (`story-rules.md`).

**3. Know what still waits.** A clip waits only for what no image made ahead can give it:

- a voice: the speaker's voice clip and sample;
- the place as it was filmed: every clip in a place an earlier clip filmed sends that clip's frame plate (References from the
  film's own frames). With the location sheet alone, one place's layout changed between clips.

**4. Plan the rounds.**

- **Round 1:** the first clip in each place and each speaker's voice clip, often the same clips, in one batch.
- **Round 2:** every other clip in one batch, with the frame plates and samples from round 1 and the prepared states.
- **Remakes** join the next round.

Four 2-minute films of nine or ten clips ran this way: one clip, then a batch of eight, then remakes, in 53 to 63 minutes each. A
state prepared ahead and sent to a clip running beside the one that shows the change is untested as a pair: look at both before
building on them.
```

**Ours**

```
Round 2 = {clip_ids}: each sends {frame_plate_of_its_place}, the prepared state sheets {forms}, and every speaker's sample. An extension: @Video1 is the clip being continued: keep {what_stays}; this clip adds {what_is_new}.
```

Check: Each take against its stateIn/stateOut; seams checked at 4 fps; a stub under 0.5 s cut through kept.

### 11. Score — `sound.music`

Only when the card wants music under the dialogue: one instrumental, the film's length plus 5 s, laid about 10 LU under the voices.

| | model | credits |
|---|---|---|
| Higgsfield | elevenlabs_music_v2, force_instrumental true | priced at its stage (not quoted here) |
| our house | ElevenLabs Music (eleven-music-v2.5), the music bed | metered (ElevenLabs) |
| cheapest | no score (the card's own sound carries it), or a banked bed already made | 0 |

Cheap swap: Many cards run no score; a reused bed costs nothing. Registry: eleven-music-v2.5.

**Higgsfield, word for word**

```
**The score: `elevenlabs_music_v2`** (`generate_audio_batch`, `force_instrumental: true`).

- Write the prompt into `score-prompt.txt`; the call sends it word for word.
- Instrumental, its `duration` the film's length plus 5 seconds: a take opens on up to a second of silence and its
  last seconds ring out quietly (tested: 32 seconds asked, music from 0.74 to 29.3 s; a 123-second take ended its music 4.3
  seconds early, where every 125-second take covered a 120-second film).
- The prompt: "Instrumental film score, no lyrics.", then the film's world and mood, the key and tempo, the instruments, and how
  it ends. Describe the sound, never name a composer, artist, film or series: a name fails the job (a drama-editor test).
- Measure the take before it goes under the film: some come back far longer than asked (a drama-editor test), and it
  plays 9-10 LU quieter than a sung track (tested: -23.5 against -14.5 and -13.0 LUFS), so its level is set by measure (`clips.md`,
  Assembly).
```

**Ours**

```
Instrumental film score, no lyrics. {world_and_mood}. {key} at {bpm} bpm. {instruments}. It ends {ending}. Duration {seconds_plus_5} s.
```

Check: Measured length covers the film; no named artist; whispered again after the mix, every line still reads.

### 12. Assembly — `edit.assemble`

Hard cuts in film order at each clip's measured kept ranges, frame and sample exact; the clips' own room tone under everything; score and narration laid over; loudness last at -14 LUFS, true peak -1.5 dBTP.

| | model | credits |
|---|---|---|
| Higgsfield | assemble.py join / loudness in the sandbox (ffmpeg) | 0 |
| our house | Video Edit (components/video-edit), the Studio's edit line | 0 |

On this Mac: `ffmpeg; ebur128 + loudnorm linear; Real-ESRGAN upscale of 480p clips before the join (local-studio upscale)`

**Higgsfield, word for word**

```
## 5. Assembly

Join the clips as the Assembly section of `references/clips.md` says, with `assemble.py` in the sandbox: hard cuts in film order,
each clip at the `kept` ranges written from its own measured cuts (never the planned seconds blind: a seam cut there flashed the
next shot for under a second), music over the whole film if it wants any (a score under dialogue: `clips.md`,
Assembly), and in a narrated format the narration track or the song laid over at its timeline. A fade or any other edit is made
there with ffmpeg, never asked of the video model, and the film's loudness last
(`python3 "${HF_WORKFLOWS}/drama-ads/scripts/assemble.py" loudness …`). Text the user asked to see (`asked.texts`)
goes on after the loudness, before captions (`references/clips.md`, Text on screen). The join and the loudness run with
`background: true`. Before each sandbox call that joins, mixes or probes the film, write one plain line to the chat,
«Assembly: joining <N> clips · mixing the score · ~1 min», then «Assembly: checking the film» before step 6's probes: assembly
runs in the sandbox with no job to poll, and the chat otherwise shows nothing for a minute or two.

## Assembly

- Assembly runs in the sandbox (`sandbox_exec`), in the film's folder. Download every clip there (`curl -fL --retry 3 -o`) from
  its result URL in `jobs.json`. An extension comes back as the new part only, at the length you asked for, and its first frame repeats the
  source's last frame, so the two join without a visible seam (tested: a 15 s forward extension of a 15 s clip returned 15.0 s). If a
  clip ever comes back longer than planned, the extra is the source part: cut it off.
- Join them with `python3 "${HF_WORKFLOWS}/drama-ads/scripts/assemble.py" join script.json --clips <dir> -o joined.mp4`, each clip downloaded as
  `<dir>/<id>.mp4`: it cuts every clip to its `kept` ranges or else to its planned length (trim points: Cutting the film into
  clips), the picture by frames and the sound by samples, and joins them in film order with hard cuts and one encode. It first
  scans each range for cuts and refuses one inside the range's first or last second, a flash at the seam, printing the second
  to start or end the range at; fix that clip's `kept` and join again. A candidate the frames either side show is no cut (a lamp
  switched on, a fast move) passes with `--not-cut <take>@<second>`, never to keep a flash. Every clip
  comes back one frame longer than asked (40 of 40 six-second clips: 145 frames at 24 fps), so uncut clips drift off a song; and
  each clip cut to its own file and joined with `-c copy` put the sound 23-43 ms later at every seam, the last clip of four films
  118-226 ms behind its lips, where the script kept every clip within a millisecond.
- Add music, if any, now, over the joined film. A score under dialogue: one instrumental (`elevenlabs_music_v2` through
  `generate_audio_batch`, `models.md`, Voices, songs and the score), made with clips round 2 (`SKILL.md`, Stages in ask
  mode) and only laid over the joined film here, started at its first sound (the end of its opening
  silence, `silencedetect=n=-45dB`), cut at the film's end and faded in and out. Its level is set by measure, about 10 LU under the
  clips' sound: `ebur128` on the joined film and on the take, then `volume=<film I - 10 - take I>dB` on the take into
  `amix … normalize=0`. Then whisper the film again: every line must still read word for word (tested on a 2-minute film, the
  score 10.7 LU under). In a narrated format lay the narration track or the song over it at its timeline, the music under the
  voice; keep a lip-synced sung clip's own sound for its length, and mute a silent clip that came back with a voice (`formats.md`).
- The clips' own sound stays under everything: their room tone and effects fill the gaps between lines and sung phrases. Every
  clip is made with its sound on; a film whose clips were made silent, so that nobody would sing along, had nothing between its sung
  phrases. A voice a clip adds is muted only where it is (`formats.md`, Silent clips), with `--mute <clip id>:<from>-<to>` (its
  take's own seconds) on the join, and its music taken out (Order of work, Music); where no track or score plays over a muted
  span, `--fill` lays the clip's own room tone there instead: a mute alone left 2 seconds of digital silence in one dialogue film.
- Every edit beyond the hard cuts (a fade at the end, a dissolve) is made here with ffmpeg, never asked of the video model.
- Last, the film's loudness: `python3 "${HF_WORKFLOWS}/drama-ads/scripts/assemble.py" loudness mixed.mp4 -o film.mp4` (the joined film with its music,
  narration or song laid over). It holds loudnorm linear, raising the sound into a limiter while its peaks leave no room, and
  measures the encoded file: -14 LUFS, true peak -1.5 dBTP or lower, or it refuses. Run as two plain passes, loudnorm silently
  compressed all four films of one test instead, lifting the room tone between lines up to 4 dB more than the lines, and the
  AAC encode left their peaks over -1.5.
- Deliver, after the captions when the film gets them (below), as `SKILL.md` step 8 says: `media_upload`, the PUT in the sandbox,
  `media_confirm`, and the user gets the link `media_confirm` returns, exactly, with the report.
```

**Ours**

```
Join {clip_ids} in film order at their kept ranges, hard cuts, one encode; score {score} at film I - 10 LU, faded; mute {muted_spans} with room tone fill; loudness -14 LUFS, true peak -1.5 dBTP. No offer, price, disclaimer or call to action on screen.
```

Check: No flash at any seam; every line plays whole; length = the script's length.

### 13. Look and listen before handing it over — `behind.judge`

Every shot's middle frame (one of each person, no empty shot), every seam at 4 fps, a frame a second tiled; a whole-film transcription for every line by its speaker; silent spans and stray music.

| | model | credits |
|---|---|---|
| Higgsfield | the directing chat model looks at tiles; faster-whisper small listens | 0 |
| our house | Gemini 3.1 Pro judge + ElevenLabs Scribe | metered, cents |
| cheapest | Gemini 3 Flash fast read (gemini-3-flash-preview) + whisper-large-v3-turbo local | cents |

Cheap swap: House rule: every read inside a run is the judge; Flash is a person's pick only. Local whisper is free and as good for the line check. Registry: gemini-3-flash-preview.

On this Mac: `python3 components/local-studio/local.py stt film.mp4 -o heard.json; ffmpeg -vf fps=1,scale=-2:480,tile=5x2`

**Higgsfield, word for word**

```
## 6. Look before you hand it over

Measure the joined film's shots first: its cuts are every seam between clips, at the seconds the clip plan gives, and each clip's
own cuts (found as `references/clips.md`, Order of work, Stubs, says) at their place in the film, and the seconds between them.
The filter run on the joined film missed both seams of one film, cuts between two dark shots, and so missed the jump at one. A stub
still there (a shot under 0.5 seconds, under 1 second at a seam) goes out in its clip's `kept`, and the clips are joined again.
In the middle frame of every shot, count the people: one character drawn twice (a twin, their double behind them) is a broken
shot (`references/clips.md`, One of each person). The film is continuous footage: no still, screenshot, page or card laid over or
cut into it (`references/clips.md`, Text on screen). Every line plays whole: no first or last word lost at a trim or a seam.
At every seam look at the last second of the clip before and the first second of the next at 4 frames a second: the same moment
or move twice (he stands up, then stands up again), a character in another posture or place than the clip before left them, or
a flash of the old scene is a continuity break (`references/clips.md`, Physical continuity), fixed through `kept` or a remake.

Look at a frame every second of the joined film (`ffmpeg -i film.mp4 -vf fps=1,scale=-2:480 f%03d.jpg`, tiled ten to an image with
`tile=5x2` and the last frames with `tile=<their count>x1`: ffmpeg fills a short tile with black cells, and one was taken for a
black frame in the film; each tile scaled to at most 1024 pixels wide and looked at with `image_paths`, knowing its frames'
seconds), and at 4 frames a second over the first 4 seconds, around every `plan.json` second, the spike and the last 5 seconds:
shots of a second or less fall between sparser frames. Look at the middle frame of every shot too: a shot with nobody and no story
prop in it is an empty shot (`clips.md`, Order of work), and two of them reached one finished film unseen at 480p. In a narrated or
sung film, ask of every line whether the picture shows what it says while it plays. Look as a first-time viewer who never read the
script. Who is who? What do they want? What is the twist? How does it end? Where would you get lost? Check every seam, the effect
moments and the action for broken faces, swapped characters, drifting looks and props, and smeared motion.

Listen with faster-whisper in the sandbox (`references/models.md`, The sandbox; `references/clips.md`, Order of work):

- **One pass over the whole film:** cut into windows under 30 seconds, 6 of 66 lines came out more than 0.5 seconds off, against
  3 in whole-file passes, and clip by clip 10 (eight films). When the whole pass stops on an `IndexError` in whisper's
  `find_alignment`, keep the words it printed before it: the stop comes in a last window one frame (0.01 s) long, after a full
  30-second window, when the decoded sound runs a frame past a multiple of 30 seconds, and every line had been printed. Do not pad
  the sound or cut it into windows to avoid it: a padded tail of 0.1-2 seconds drew invented words, and a window's first word was
  pinned to its cut, 1.05 seconds early.
- **The lines:** every line in American English, in its words, by its speaker, near its time.
- **The voices:** measure each speaker's median pitch over whole lines, never single words: whisper's word times run up to 0.6-0.9
  seconds off on some words, and a pitch taken on one short word pinned a line on the wrong speaker.
  - A calm line far from the speaker's sample (about 1.5 times off) may be a swapped voice: an "outraged" delivery turned a low
    voice into a shriek.
  - A shout or a call rises 1.5 to 2 times on its own, and two voices can share a pitch range. So before you call a swap, compare
    the line's timbre with each speaker's sample (the mean MFCCs, by cosine similarity) and look at whose mouth moves in a frame at
    its middle. Timbre matched a line to its own speaker where pitch pointed at another.
- **Silent spans:** a clip that should be silent is checked for speech with the voice-activity detector
  (`faster_whisper.vad.get_speech_timestamps`) and the transcript's words together. Use each word's own `probability`, not the
  segment's `no_speech_prob`, which covers a whole window: real lines scored 0.63-0.82 there, while an invented word scored 0.15.
  - A span is speech when its words are probable and the detector agrees. Transcribe a doubtful span again on its own: whisper
    invents words from noise and loops a real word.
  - Check the energy before you mute anything.
- **Music:** check each clip also for music it was told to leave out. Look for it on a spectrogram of the clip's sound (0-2 kHz):
  held tonal lines of half a second or more that step in pitch or sound together as a chord (whisper's sound tags miss short held
  tones). After the join, look again over each muted span and the second after it. Where the sandbox has Demucs, take it out of the
  clip rather than remake it (`references/clips.md`, Order of work, Music).

Remake a broken clip, or only its broken part, within the generation limits rather than patching it from itself. Report honestly
what works and what does not; don't call a broken film done.
```

**Ours**

```
As a first-time viewer: who is who, what does {hero} want, what is the twist, how does it end, where would you get lost? Every line of script.json heard in order by its speaker; the product's label legible in its insert; nothing the offer bank does not claim; no disclaimer, men never kiss or hug men, clothed cast.
```

Check: A broken clip is a paid remake, priced and approved like a stage; never call a broken film done.

### 14. Captions — `edit.captions`

Burned-in captions in the style's look, the script's own words, timed on the joined film before the score; the uncaptioned film is kept.

| | model | credits |
|---|---|---|
| Higgsfield | video-montage workflow (audio_to_captions.py + subtitle_paper_burn.py) | 0 |
| our house | Video Edit captions on ElevenLabs Scribe word times | metered (Scribe) |
| cheapest | whisper-large-v3-turbo word times (local-studio stt) | 0 |

Cheap swap: Free on this Mac; the words come from script.json, whisper only times them. Registry: whisper-large-v3-turbo.

On this Mac: `python3 components/local-studio/local.py stt joined.mp4 -o words.json`

**Higgsfield, word for word**

```
## 7. Captions, when asked for

Captions are optional. When the user asks for them (in the request, with a frame of captions they like, or with a reference video
that has them), load the `video-montage` workflow with `get_workflow_instructions` and have it caption the film in the look of the
style file's Captions, with the script's lines as their words (`references/clips.md`, Captions). Otherwise the film goes out
without them.

## Captions

Captions are optional: a film with lines gets burned-in captions in its style's look (its style file, Captions) only when the user
asks for them (`SKILL.md`, step 7); a look the user shows is written as the same flags. They are made by the `video-montage` workflow
(load it with `get_workflow_instructions`; its `references/subtitles.md`), which owns their timing, placement, burning and
checks. This workflow is its caller and hands it, once step 6 of `SKILL.md` has passed:

- **the film:** the finished film, and for the timing the joined film before the score went under it;
- **the lines:** `script_manifest.json`, `{"blocks": [{"vo_line": "<the line's text>"}, …]}`, one block per entry of `lines` in
  film order, every kind (dialogue, thought, narration, sung), so the captions carry the script's words;
- **the language**, `en`, and **the look:** the style file's Captions flags, `--max-words` for `audio_to_captions.py` and the rest
  for `subtitle_paper_burn.py`.

Before the burn, read the caption file it times: in the test films the first word of a line sometimes stood alone 4 to 7 seconds
before the rest of it. Move such a word into the caption that follows it. Keep the film without captions. Captions are burned
last, on the film at the resolution it goes out at: an upscale after the burn softens them (one film's captions were burned 30
pixels high into a 480-pixel-wide frame).
```

**Ours**

```
Captions: the lines of script.json in film order, {caption_style} (the card's or the style file's), clear of faces, the product and the Reels buttons.
```

Check: Captions against the words; burned last at the delivery resolution.

### 15. Finish to 1080x1920 — `behind.upscale`

Higgsfield renders every clip at the picked resolution (1080p by default) from the start. Ours: made at 480p, upscaled on this Mac.

| | model | credits |
|---|---|---|
| Higgsfield | seedance_2_5 at 1080p from the first take (no draft step in this workflow) | the 1080p clip price (160 per 10 s) instead of 30 |
| our house | Real-ESRGAN upscale on this Mac (house: 480p made, upscaled locally) | 0 |
| cheapest | Real-ESRGAN animevideov3, local (real-esrgan) | 0 |

Cheap swap: ~11 s of compute per video-second. Pay for 1080p clips only on a proven winner. Registry: real-esrgan.

On this Mac: `python3 components/local-studio/local.py upscale clip.mp4 -o out.mp4 --esrgan-model realesr-animevideov3`

**Higgsfield, word for word**

```
The shape is vertical 9:16
unless the user asks for another: horizontal 16:9, square 1:1, or 4:3, 3:4, 21:9 (the clip model's shapes). The resolution is the one
the user picks from those the clip model lists, 1080p when they pick none (`SKILL.md`, step 0, the one intake question), for every style alike.
```

Check: 1080x1920, same length, faces not smeared.

### 16. Deliver — `none`

Higgsfield uploads the film and shows it in a widget with every generation. Ours: the film and the captioned copy go to the Studio and Drive, then an approval card; never to Meta from here.

| | model | credits |
|---|---|---|
| Higgsfield | media_upload -> PUT -> media_confirm -> show_result(microdrama_film) + show_generation_by_ids | 0 |
| our house | Video Studio production folder + Drive (Shared Assets) + meta-upload 1-check approval card | 0 |

On this Mac: `ffprobe (duration, video, audio, shape, size)`

**Higgsfield, word for word**

```
## 8. Deliver the finished file

The film leaves the sandbox as an upload, never as a path:

1. Probe `film.mp4` one last time: duration, video stream, audio stream, the film's shape, non-zero size.
2. `media_upload({ filename:"<film name>.mp4", content_type:"video/mp4" })` for the upload URL.
3. The PUT runs in the same call as the file's guard, and checks both ends:
   ```
   set -e
   cd ~/films/<film name>
   [ -s film.mp4 ] || { echo "film.mp4 gone: rebuild before uploading"; exit 1; }
   code=$(curl -sS -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: video/mp4' -H 'If-None-Match: *' --upload-file film.mp4 '<upload_url>')
   echo "PUT -> $code"; [ "$code" = "200" ] || exit 1
   ```
   `--upload-file`, never `--data-binary @file`: a PUT of a vanished file with `--data-binary` answered 200 and stored nothing.
   Without `Content-Type` the PUT answers 403.
   If the guard trips, rebuild the file from `jobs.json` in that same call and PUT again.
4. Only after the PUT returned 200: `media_confirm({ type:"video", media_id:"<media_id>" })`.
5. The first call after `media_confirm`, before a word of the report: `show_result({ action: "microdrama_film", media_id: "<media_id>", meta: { drama_ads_id } })`,
   the media id `media_confirm` confirmed. The widget is the delivery, and a link alone is a failed delivery (a film ended
   as a bare link, the widget written as «the last call» after the prose and never called).
6. Then every generation of the film once, in one `show_generation_by_ids` gallery (its jobs from `jobs.json`, up to 60).

Report to the user under those two calls; its link line is the link `media_confirm` returned, exactly, never a job id, an upload
URL or a sandbox path:

- the title and logline;
- the film's link, captioned when the user asked for captions (the film without them is kept); otherwise without them, with one
  line offering captions in the style's look;
- the cost, ending with the line «spent X of ≈ Y credits»;
- what of their request the film changed to fit a model's limit, and why;
- a short, honest note on how it reads: what a stranger would get, and where it may lose them; and which clips had their own music
  taken out, with which mode.

On a failure no retry fixes (the retry ladder spent, an assembly that will not pass, no file), say so plainly, name the step and what
was tried, and never hand over a partial or patched film as the result. Captions failing is not a failed film: deliver it without
them and say so in one line.
```

**Ours**

```
Report: title and logline; the film's link; credits spent of the quote; what was changed to fit a model's limit; an honest read of where a stranger gets lost; which clips had music taken out.
```

Check: Delivered to the Studio and Drive, never to Meta from here.

## Checks

- Price quoted and under the lane.json cap before the first paid call; re-quoted when the plan grows
- Script review: hook in 3 s with both faces, obvious in 5 s, agency, mute test, visible ending, physics, moderation
- Every claim the product makes is in the offer bank; the offer is spoken, never on screen
- First clip of each model and mode sent alone and checked (shape, resolution, length) before the batch
- Each character keeps one voice: our ElevenLabs v3 sample bound by @Audio in every clip they speak
- Contact sheet per clip: one of each person, identity, beat, the label legible in its insert, no stray text or brands
- Every line heard in order by its speaker; no stray music in the clips
- No flash at any seam; loudness -14 LUFS, true peak -1.5 dBTP
- No disclaimers, price or call to action on screen

## Rules

- Story from our avatar, her words and an objection; the swipe or card gives the structure only, never its story or lines
- The product does only what the offer bank says; its label kept exact
- Every character speaks in our own ElevenLabs v3 voice, one voice per character for the whole film
- Clothed cast, no brands but ours, no celebrities, men never kiss or hug men
- No offer, price, disclaimer or call to action on screen
- Retry ladder: ip_detected resent once unchanged; nsfw restaged, never reworded past moderation; about 6 tries then stop and report
