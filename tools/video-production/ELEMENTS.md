# Every element of a video: the one contract

the owner, 2026-09-23: *"b-roll and inserts need to clearly be identified in teardown and communicated through to production briefs so ALL elements of a video are ready for assembly … we are designing this system for extreme scale … all these elements need to be green."*

**The rule.** The teardown **names** every element on the swipe's timeline. The AI brief **carries** it. Production **makes** it, or pulls it from a bank that was made once. The edit **assembles** it and decides nothing. A new version is a swap of parts.

This file is the shared shape. The teardown prompts, the brief prompt, `plan.json` and the edit kit all use these ids and fields. A stage may add a field. It never renames one. The map the owner reads is "Every element of a video" on **The Edit Line**.

## 1. Scenes: pictures that are made (in `plan.scenes`, in play order)

| kind | teardown row | what production makes | fields beyond the scene basics |
|---|---|---|---|
| `talking` | A | a first frame + a last frame, and one clip lip-synced to the voice slice | `to_camera: true` |
| `broll` | B-over / B-vo / B-silent | a first frame + a last frame, and one silent clip, with the voice slice under it | `to_camera: false`, `covers` (the exact words) |
| `card` | C | one text-free **plate** (a still) and no clip | `card: {plate, lines, lands_on, sfx, refs}`. *Built 2026-09-23.* |
| `screen` | S | one plate of a screen: review, comment, text thread, site, order page. The legible text is set by the edit | `screen: {plate, surface, lines, lands_on}`, where surface is `review\|comment\|dm\|site\|order\|search` |
| `split` | X | two frames, one for each side; each side animated like B-roll | `split: {left, right, layout: "side\|top-bottom\|wipe", labels}` |
| `greenscreen` | G | a background plate (article, post, product page) + a talking clip of the presenter | `greenscreen: {background, talker_scene, layout: "cutout\|pip"}` |
| `endcard` | E | a packshot plate from the REAL packshot | `endcard: {plate, offer_lines, cta, guarantee}`. The words come from the offer bank only |

`opens: true` on the first picture scene makes it the **scroll-stopper**. The teardown marks it (`opener: true` on the row) and the brief carries it.

## 2. Layers: set by the edit on top (in `plan.layers`)

| id | teardown names it as | fields |
|---|---|---|
| `hook` | the on-screen hook text and its look | `{text, look}`. It is on screen from frame one |
| `captions` | the swipe's caption style | `{look}` from `looks/bank.json`, or `match-swipe` |
| `lower_thirds` | a name or title strap | `[{scene, name, title}]` |
| `annotations` | an arrow, circle, underline or highlight | `[{scene, kind: "arrow\|circle\|underline\|highlight", target, at_words}]` |
| `platform_ui` | a comment bubble, post, message, stitch or duet frame, search bar, counter or review card | `[{scene, kind, style?, text, handle}]`, where kind is comment_reply \| dm_generic \| duet \| ig_comment \| imessage \| likes \| review \| search \| stitch \| views \| whatsapp \| x_post \| youtube_comment. The styles are `tools/video-edit/looks/platform_ui.json` |
| `disclaimers` | nothing (the edit adds these by rule) | read from `brands/<brand>/brand-identity/compliance.json`, by claim type and platform |
| `transitions` | any hand-off that is NOT a hard cut | `[{after_scene, kind: "cut\|whip\|match\|zoom\|flash"}]`. Hard cut is the default. The catalogue, with what triggers each one, is `tools/video-edit/looks/transitions.json` |
| `icons` | an icon, emoji, sticker or drawn mark (arrow, circle, star rating, badge, burst, etc.) | `[{scene, icon, zone, at_words, size}]`, where icon is an id from `tools/video-edit/looks/icons.json` (52 rows) |
| `zones` | where text sits | every text layer names a zone id from `tools/video-edit/looks/placement.json` (top-headline, upper-third, center, center-block, lower-third, caption-band, fine-print, left-rail, top-left); the edit moves text off the face using production's `subject_box` |
| `fonts` | the swipe's type style | font ids from `tools/video-edit/looks/fonts.json` (15 open-licence fonts) |

## 3. Sound

| id | teardown | production | edit |
|---|---|---|---|
| `voice` | the delivery read | one read, levelled to −16 LUFS, heard by the audio gate | each clip keeps its own sound |
| `song` | the sung lyrics (sound form SUNG / RAPPED) | the brief's `song: {style_id, vocal, bpm?, sections: [{name, scene, seconds, lines}]}`, every line one of the scenes' `lyrics`, printed on ElevenLabs Music `music_v2_5` by `song.py`, heard by the song gate, timed from speech-to-text. `song/song.mp3` + `song/timing.json` + a −14 LUFS copy. The chain: `SONG-CHAIN.md` | lays the song, cuts to its line times; no voice, no separate bed |
| `music` | `{energy: "low\|mid\|high", tempo_bpm, mood}` | picks a track from the **music bank** by those tags. `plan.music = {bank_id, file}` | lays it, ducks it 18 dB under the voice, cuts it to the beat |
| `sfx` | itemised cues | picks each cue from the **SFX bank**. `plan.sfx = [{cue, bank_id, file, at_words\|scene}]` | lands each 2 frames early. A fixed cue is the same file every time |
| `room_tone` | nothing | one bed per setting, from the SFX bank's `room-tone-*` rows | fills every trimmed gap under the cut |
| `mix` | nothing | nothing | masters to −14 LUFS integrated, −1 dBTP |

The voice-over's chain, step by step and with what is pinned, is `VOICE-CHAIN.md`. A song's sound is never words: it is one row of `banks/music-styles/index.json`, by id.

Banks live on the Drive, with the index in the repo (`tools/video-production/banks/<bank>/index.json`, one row per file: id, tags, seconds, source, licence). A bank is made once and reused forever. A missing row is an error, never a silent fallback.

## 4. Versions: parts swapped, never re-made

| id | where it comes from | edit |
|---|---|---|
| `hooks` | the teardown's control + 5 hooks. The brief carries each one as `{id, text, opener_scene?}` | one render per hook, with the same body |
| `sections` | every scene's `section` — a section id from the marketing doctrine (`components/marketing-doctrine/frameworks.json`, bound in the prompts as `{sections}`), read at run time and never listed here. v14's six-word `module` is retired: a brief that still carries it is read with a warning, filling a missing `section` only (`mechanism` → `unique-mechanism`, `cta` → `call-to-action`, the rest as themselves) | swaps whole sections between versions and assembles the combinations that are listed |
| `framework` | the piece's `framework` — an ad-framework id from `components/marketing-doctrine/ad-frameworks.json` (`{ad_frameworks}`), which names the sections a piece runs and their order; or `observed — <a plain description>` for a piece that follows none, never a coined name. An id off the list is a gate finding naming the real ids | reads which sections the piece runs, in which order, when it assembles a version |
| `cutdowns` | the brief's `priority` (1 = never cut) on each scene | 15 / 30 / 60 s, cutting the lowest priority first. The line is never cut mid-scene |
| `ratios` | **9:16 only** (the owner, 2026-09-23: "I do not want 4:5 or 1:1 videos at all"). The frame is 9:16 with the content kept in a 4:5 zone (the 22 Sep rule) | one 9:16 render with its safe zones. No 4:5, no 1:1 |
| `cover` | nothing | the cover frame is the hook's first frame, with the hook text on |
| `name` | nothing | the naming convention (`components/naming`) |

## 5. Colour

Every clip is matched to the piece's first frame. Production's `colour_match.py` already does this for stills. The edit applies one grade over the whole piece.

## 6. Safe zones

The frame is 9:16; the zone is its centred 4:5 window — the middle 70% of the height (the 22 Sep rule). Two halves, two owners:

- **The subject zone is production's** (the owner, 2026-09-23: "this should mostly be handled at the production level"). Every still this machine makes — first and last frames, card / screen / split / greenscreen plates, the endcard packshot — is measured by `machine/safezone.py`: a vision call says WHERE the face, the product and the hands are (prompt `prompts/stage-5-qc/stage5-subject-zone-v1-damon.md`), and the box is compared with the zone by geometry, never by asking the model to stay inside it (image-production's 13-of-13 finding). Outside → ONE fix edit (the frame first, the cast sheet second, "move the face into the centre", the keep-line) and one more check; still outside → held: no clip, `pack` refuses. The measured box goes into the frame's record as `subject_box: {x_pct, y_pct, w_pct, h_pct, what}` on the 9:16 frame — face first, else the product, else the hands — in `direct.json`, in `plan.json` (`subject_boxes`, and on the scene's own frame) and in `verdicts.json` (`subject_zone`). Mid-clip drift is Motion QC's check 7.
- **The text zone is the edit's.** Captions, hooks, card and endcard words are set inside the same 4:5 zone and kept off `subject_box` when it is present.
