# The editing standard

the owner, 3 Oct 2026: *"document everything I'm saying and what we're doing because this becomes the standard process
for editing videos and we'll roll everything together logically at the end."* 4 Oct: *"go piece by piece … make it
ultra clean and clear so we can just run that process over and over … ultra agnostic — product, brand, avatar,
concept, everything."*

**Part A** is how to run it. **Part B** is every rule, in his words, with what the machine does about it. Nothing
in the tools belongs to one ad: an ad's own choices live in its `decisions.json`, the caption looks in
`looks/bank.json` (the one registry, picked by format — 2026-10-21), the text looks in `looks/edit-looks.json`, the
levels in `machine/defaults.json` `sound`, and the brand, product, avatar and angle come from the brief and
`brands/<brand>/`. Every rule here is checked against the video rulings register
(`../video-production/VIDEO-RULINGS.md`, V1–V20); where they disagree, the register wins and the line here is marked.
(First ad through it: Creator-A's three doctors, `runs/video-edit/<brand>/kzn03-face-scrub-clean`.)

> Which model does what: `../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20).

# Part A · Run it

## A1 · One command

    python3 machine/line.py <video-production-run> [--brief brief-NNNN] [--batch batch-YYYY-MM-DD-x] [--links <link id> …]

**In:** a finished production run (approved pictures, clips, cloned voices, `plan.json`, `brief.md`) and the ad's
`runs/video-edit/<brand>/<label>/decisions.json`. **Out:** six-or-so finished 9:16 versions (the control and one
per hook opening), named, with their card in Drive `meta/<brand>/1-check/video/<ad name>/`, waiting for Approve.
Every step's check **stops** the line, and nothing is filed past a red check. `line.json` in the edit run records
every step.

## A2 · The line, step by step

| # | Step | Tool | What it checks | If it fails |
|---|---|---|---|---|
| 1 | **Plan** the cut: every line at its real sound length, one breath apart, the swipe's cuts, punch-ins, close-ups, B-roll, text, music | `edit_map.py --hooks` | notes what needs a cover | notes it (fix in decisions) |
| 2 | **Mouths**: the lead's mouth only moves when the lead is heard, and the lead's voice only plays over the mouth saying it | `mouths.py` (every version) | 10 times a second over what is on screen | **stops** |
| 3 | **Words**: the soundtrack transcribed and held against the script, before a frame is made | `render_map.py` → `listen.py` | every scripted word is heard | **stops** (unless `cut_words` names it) |
| 4 | **Render**: picture and sound assembled (`render_map.py`), lips held, then **every word drawn by `compose.py`** (`map_sheet.py`: captions in the look picked by format, headline, option pops, badges, end-card words, the brief's whip/match hand-offs, the realism finish) — one renderer for the whole system (2026-10-21, C13) | `render_map.py` → `map_sheet.py` → `compose.py` | lips within a frame of the voice, every talking shot (on the picture with no words on it) | **stops** (the file is set aside as `.held.mp4`) |
| 4b | **Audit**, every version | `audit.py` | every word whole · lips on every word · the right shot · sync · **no caption on a face or a mouth, read off the finished frame** · the swipe's music and SFX there | **stops** |
| 5 | **Scan** each finished file | `line.py` | 0 black frames · no dead air (with room tone: no silence at all) · −14 LUFS (±1.5) · 9:16 | **stops** |
| 6 | **Deliver**: names (components/naming), the card, the manifest | `deliver.py` | brand, product, brief, ratio, versions, copy, page, avatar, angle | **stops** on a gap |
| 7 | **File** the card and videos into 1-check (refiled in place: the Drive link never changes) | `meta-upload/to_check.py` | the 9 card checks (media, 9:16, words, name, page live, product = page, ad set, campaign, page cap) | card shows red; Approve stays off |
| 8 | **Approve** → Meta: campaign and ad set found by name or made paused, videos uploaded, one flexible ad | the approval page | the owner's click is the only go | — |

The frame-by-frame sweep (`sweep.py`) and the timeline page are for looking: run them while settling decisions.

## A3 · The decisions: the ad's own choices (`decisions.json`)

The tools decide nothing about one ad. Everything specific to an ad is written here by the editor (a session),
with a `why` that quotes the ruling:

**The edit cuts, it does not repair** (V15, 2026-10-20; verify 2026-10-21 row 6). The REPAIR keys below — `cut_out`,
`add_lines` (and word_fix's `auto-fixes.json`), `closeups`, `fixes.<clip>.crop` and the `clean_baked` paint-over — are
laid only when a person runs `edit_map.py --repairs` on one ad. `line.py` (the runner path) never passes it and no
longer runs `word_fix.py auto`: a map that was asked for a repair names it in its notes and lays nothing; a take that
cuts a line off goes back to production, and the audit stops the line on it (WORD CUT).

| Key | What it says | Tool that helps |
|---|---|---|
| `story.lead` | whose mouth is held to the sound | — |
| `story.lead_only_until` | the section until which the screen is only the lead's own experience | — |
| `drop_sections`, `drop_picture`, `trim_line` | what is taken out, and where a cut-off line is trimmed | `listen.py` |
| `add_lines`, `audio_patches`, `cut_words` | words said again in the speaker's cloned voice, and words the owner has said to cut | `word_fix.py` |
| `closeups` | covers on the lead (mouth kept out while it moves with no words); `frames` names a part outright | `mouths.py`, `sweep.py` |
| `fixes` | per-clip moves, e.g. a punch-in past words a clip wrote on screen | `sweep.py` |
| `broll.place` | each B-roll piece, the words it covers, why | — |
| `text_keep`, `text_looks`, `option_cards`, `captions` | which on-screen words stay, and which look from `looks/edit-looks.json` | — |
| `music` | the bed (made to the full length), its style words and levels | `music_bed.py` |
| `cut_out` | a stumble or a dead pause INSIDE a clip's line cut as a jump cut on the same take (`{clip, from, to}`, clip seconds; the caption text splits itself by the clip's own words). Cut from 0.1 s after the word before to 0.08 s before the word after — never on a word | `audit.py` |
| `trim_start`, `line_text` | start a line later in its clip (its first word moved elsewhere), and the words a line really says when a clip dropped some — captions follow what is heard | `audit.py` |
| `audio_patches` | a clean word in the speaker's own cloned voice laid where the lips SAY it (a mispronounced brand name, a word the clip's end cut); the lip check counts it synced only on its own clip | `word_fix.py` |
| `broll.place` `calm` | under the other voice's read, a quiet moment of the lead from the same set, full frame (`seconds`, `avoid`) — fitted only into the gap where the lead is not heard. **Never a zoom to hide lips** (the owner, 20 Oct: "that was hella unneeded") | `mouths.py` |
| `track_len`, `no_breath_before` | an off-camera read cut at its last word, and the answer that follows with no breath — the "awkward pause after Moringa" | — |
| `headline_y`, `items_y_shift`, `items_scale`, `text_replace`, `cutout_files` | the headline inside the safe zone, items and their score badges below the chin and clear of the captions, the ad's own headline words, the ad's own item picture (a blank badge with its words set as type) | — |
| `clean`, `clean_pad` | `clean: false` for frames made clean (a swipe edit): no patch over baked items and no "already held" guess that takes an item away. `clean_pad` grows the patch when a baked item shows round its edges | — |

**The audit, on every cut before anyone watches it** (the owner, 20 Oct: "check every single frame for lip and sound"): `python3 machine/audit.py <edit run>` — every word whole (no cut, trim or clip edge inside it), lips moving on every word heard, never another shot over a word, the picture set on its own voice (a "nudge" that moves the picture off its voice is a fault, not a fix), and every talking shot found in its source a look every 0.15 s (a 24 fps clip in a 30 fps cut reads on whole clip frames — the MEAN is the slip). A word flagged LIPS STILL on a held shape ("oo", "f") is looked at by eye before it is called a fault.

## A4 · Settings

- `looks/bank.json` — **the caption looks, one registry for both routes** (2026-10-21, E6), and `pick`: the look a
  piece starts on by its format (song ad → word box, remedy reel → edits-glow), else by the app it pretends to be made
  in (TikTok → tiktok-native, Instagram/Facebook → ig-fb-native), else the default, ig-fb-native, low in the frame.
- `looks/edit-looks.json` — the text looks (`headline-plain` default, `headline-white-box`, `headline-pink-box`,
  `native-pop`, `swipe-card`, `thumb-bold`) and default timings.
- `machine/defaults.json` — **the one loudness table** (`sound`: music −18 dB under the voice, −12 dB in the pauses,
  room tone −50 dB only when called for, master −14 LUFS / −1 dBTP — 2026-10-21, E27), the pace per format (`pace`)
  and the moves the edit may add per format (`moves`, off by default).
- Read through `machine/looks.py`. A new look is a new row; an ad picks it by id.

## A5 · Still done by hand (named, so nothing hides)

Picking B-roll and writing its `broll.place` rows · deciding which words need re-saying · the music's lift point ·
the ad copy (`words.json`) and the angle. Each is a decisions entry, a file, or one tool call. Nothing here changes
code.

# Part B · The rules, in the owner's words

## 1 · The principle: one thing sets the clock

> "We should be able to build videos in any way… music videos will obviously be audio first then
> content second. This applies for b-roll / with voice over only style videos. Think about the principle."

- In every piece, ONE thing sets the time and everything else is fitted to it:
  - **Audio first:** music videos, and B-roll with a voice-over. The track is laid down, then the pictures are cut to it.
  - **Picture first:** anyone talking on camera with lip sync. The clip's own speech can't be re-timed, so the clip sets the time.
- A talking ad mixes the two piece by piece. In the edit map (`machine/edit_map.py`), every line sets its own time: its real sound, end to end, one breath apart. An on-camera line is the clip's own span. An off-camera line or a sound is its own track.

## 2 · The swipe is the template

> "The editing style / format needs to mimic the swipes."

- The swipe sets the cuts inside a section, where it goes to a second angle, the punch-ins, the words on screen and the sound cues.
- **Words on screen are only what the swipe shows** (3 Oct: *"I don't even know how you put all those different headlines on the words on the screen… how did you think that was correct?"*).
  - For Creator-A that is one opening headline (top centre, white caps with a cyan outline on a pink box), plus captions.
  - Text the brief added that the swipe doesn't have is NOT put on screen (`decisions.json → text_keep`).
- **Captions look like the app the piece pretends to be made in, picked by format** (V13, 2026-10-20: *"It can never
  look like it's being edited off of the phone"*; 3 Oct: *"these will mostly be on instagram and facebook so we need
  caption style that fits those platforms"*). The look comes from `looks/bank.json` `pick`: a format with its own look
  keeps it (edits-glow for a remedy reel, aimed at the neck; the word box for a song ad), else the app's native look
  (Instagram/Facebook: sentence case, white on a soft dark rounded box; TikTok: white words, black edge), low in the
  frame by default, above the feed buttons. They sit above everything, B-roll included (*"captions need to be on top
  of the b-roll too"*). **Never on a face or a mouth** (V13: *"you need awareness of the subject to ensure their mouths
  are never covered"*): placement holds the look's own height and moves a line only off a face or mouth it reads in
  the picture; the audit reads the finished frames and stops the line on a caption over one (2026-10-21, E8).
- **Section beats are native text pops, not graphics** (*"in between each of these doctors we need to have something
  like option 1, option 2, option 3 … let's not do the paper thing just do something that looks natively edited"*):
  a short bold word on a dark rounded box that pops in at the start of the section (Creator-A: OPTION 1 · 2 · 3).
- **Music only when the swipe or the brief calls for it** (V14, 2026-10-20: *"Music and sound effects are only
  relevant if that's what's being called for … don't just assume"* — this replaces "every ad gets its bed", C10,
  2026-10-21). When it is called for, the bed comes from the brief's music line on the Model House's music model, sits
  18 dB under the voice, comes up a little in the pauses, lifts where the brief says, and **runs the whole edit, first
  frame to last** (4 Oct: *"we need the music for the whole edit"*). The edit lays the bank row production picked
  (plan.json `music` {bank_id, file}), looped to the last frame when it is shorter; when production picked none,
  `line.py` runs `machine/music_bed.py` (the edit's length plus a second) and plans again. Sound effects the same way:
  each of the brief's cues (plan.json `sfx`: cue · at_words · scene) is laid from its bank file at the moment its words
  are said, two frames early, at `defaults.json` `sound.sfx_db` (verify 2026-10-21 row 5 — they were never mixed). A
  swipe that has music or effects and a cut that has none fails the audit (E26).
- **Hooks become versions** (*"you need to generate the hook variations … cut up as the variations, and then that's
  what is delivered to the final folder"*). Every opening in the brief gets its own clip, and the edit cuts one
  version per opening (`edit_map.py --hooks`).
- **Titles and names keep their capitals** inside lowercase captions (*"Dr. should be uppercase D"*): Dr., Mr., Mrs., I/I'm, brand names, and any word the script capitalises mid-sentence.
- **Structure changes need his call.** The swipe structure is locked, and a section is only removed on his word. For Creator-A he removed:
  - the receipt cards (*"pretty trash, I'd just remove those"*);
  - the doctors' thumbs-up end card (*"Remove the doctor putting their thumb up thing"*);
  - the phone shots (*"we can remove that clip and just keep the talking going to the next"*). The talking carries on, and the next shot comes in early.

## 3 · The edit cuts; it does not repair (V15, 2026-10-20 — replaces "edit moves first, remakes last")

> "I don't want it to look mechanical at all." (V15: the swipe's own shot count, cuts between shots — never
> mid-breath — no unneeded zoom-ins or punch-ins, calm cutaways; the edit cuts, it does not repair.)

- A take is laid **whole**: the cut falls between shots, never inside a breath (the format's pace, `defaults.json`
  `pace`; the old pause cutter runs only for a run that names a `max_pause`).
- **No punch-in by itself.** A punch-in happens only where the swipe itself pushes in (`frame_control.push_in`), and
  realism's imperfect-zoom gives it a thumb's overshoot. No 6% push on a still-looking shot unless the format asks
  (`moves.push_stills`); a still PICTURE drifts 3% so it is never frozen.
- A fault in a take is fixed where it was made: production makes three takes and picks the best (V5); the edit does
  not cover it. Until worker 2's take pick is proven, the repair moves below still exist in the code (they are listed
  for removal, E30) — each is a decision an editor writes in `decisions.json`, never something the edit does alone.

**Superseded 2026-10-21 (kept for the record — 3 Oct, *"see what editing moves can be done first"*):**

| Problem | The old edit move | Where it is fixed now |
|---|---|---|
| The clip model invented off-camera speech | Keep the clip's sound only across its scripted words | still done — it is the clock, not a repair; production: "listens in silence" (V8) |
| A line cut off in one clip | Take it whole from another angle that says it | production: three takes, the pick (V5) |
| Words burned into a clip | Punch in past them | production: the pick refuses it |
| Lips moving with no words | Cover them (§5) | production: the clip judge, "lips closed while listening" (P5) |
| Two takes of the same set-up joined | Alternate a 7% punch-in | gone: a punch-in only where the swipe pushes in (V15) |
| A shot needs to run longer than its clip | Play it a touch slower (never below 0.75×) | production: the take's length is the locked read's (V7) |
| A clip grew a third hand | Cover the whole stretch with B-roll | production: picture QC catches slop (V12) |

## 4 · Sound

- Non-word sounds ("mm-hmm", "um") are never said inside a clip. The person nods, and the sound is its own track (*"keep her head nod, but we don't need to put in the vocals with it"*).
- Each line's sound starts a hair early (0.08 s) and rings out (0.18 s), so no syllable is clipped between clips (*"some audio is getting cut from clip to clip"*).
- The player has a volume control (*"give me a volume option"*).
- **Room tone only when the swipe has room sound** (V14; C10, 2026-10-21 — replaces "a quiet room under the whole
  edit"). When it is called for (the brief's `room_tone` cue, production's room-tone file) a quiet room sits under
  the edit at −50 dB; without it the voices' own tails carry the joins and the scan holds only real dead air (half a
  second of silence). Every piece of sound still fades in and out over 12 ms so no join clicks (4 Oct: *"less choppy
  … the insert of new clips, captions, and sounds"*).

## 4b · Flow: lips, shots, movement, captions (4 Oct: *"actual flow and movement"*)

- **The lips are measured on every render.** Each talking shot's frames are found in its source clip
  (`syncheck.picture_lag`); more than one frame off anywhere = HELD (*"that whole pitch lipsync is off, why?"* —
  shots overlapped by a couple of frames at each cut and the overlap was played twice, so the picture slid 12 frames
  behind her voice by the pitch. Now each shot starts where the last ends, its source moved on with it).
- **No shot shorter than half a second** (the swipe's shortest is 0.6 s). A sliver left between two B-roll pieces
  goes to the B-roll beside it (Creator-A had 17, the shortest 2 frames).
- **The hand-held feel comes from the realism index, not from zooms** (V9, V15; 2026-10-21, E21 + E29). A shot that
  measures as still (40%+ of its frames barely change) gets realism's digital-micro-shake when the piece's filming
  format has it; the phone grain, a crooked hold, an exposure shift and a reframe nudge come from the same index
  (`machine/realism.py` picks; compose draws). The old automatic 6% push-in is off unless the format turns it on.
  **A punch-in is applied once** (verify 2026-10-21 row 1): on the edit-map line render_map crops it into the
  assembled picture and the cut sheet only records it (`punched`) — compose never scales it again. **The crooked hold
  never zooms**: it tilts only a shot the swipe already punches in on, inside the room that punch leaves
  (`compose.tilt_room`); every other shot is held level.
- **The product where the brief puts it** (V16; verify 2026-10-21 row 20). The real product photo (the product
  folder's packshot, never drawn) is laid in the space a scene's frame composition names for it — a clear space, the
  space in the hands, a cut-out box — while that scene is on screen (`edit_map.placed_box`, `item_cutouts`). A paid
  piece (the line files a Meta ad card, so paid unless the run says organic — `looks.placement_of`) keeps it and every
  caption inside Meta's Reels-ads safe zone (top 14 %, bottom 35 % clear); a move is named on the row.
- **Captions change on the spoken words, at production's own word times** (2026-10-21, E9 + E10). An on-camera line's
  words come from the take's own transcript (`clips/calls/<clip>/transcript-words.json`, a voice slice's from
  `vo/timing.json`) — never transcribed again; the listen (`listen.py`) stays a check and times only an own-track line.
  Each line breaks where it breathes (a comma, a full stop), never split evenly by the clock. A line's `emphasis`
  words are set in the look's accent face (E11).
- **Never a cut-off word** (4 Oct: *"We should never be cutting off words unless I'm discreetly describing to cut it
  out"*). Before a single frame is rendered, each version's soundtrack is transcribed and held against the script;
  a scripted word that is not heard refuses the render, naming it. The only way past is fixing it, or the owner naming
  the cut (`decisions.json` `cut_words`). ("Guaranteed" went out cut off at the clip's last frame while the check had
  already flagged it — a flag nobody had to act on is not a check.)
- **Words said again are made by `machine/word_fix.py`**: the speaker's cloned voice, 3 takes, each transcribed (a
  take missing a word is thrown out), the winner cut with room both sides (0.08 s before, 0.18 s after). Under a fix
  the clip's own words stay muted to the end of the line. (The hand-made "they'll … full refund" was cut 0.03 s
  after "refund" and lost its end.)
- **A close-up frames the part being talked about** — a close-up is a COVER, written only in `decisions.json` and
  listed for removal with the other repairs once the take pick is proven (V15, E22, E30) (4 Oct: *"we were talking about her lips, so you're supposed to
  zoom into the lips … when we're talking about her temples, you zoom into the temples"*). The part named nearest the
  close-up — in the line over it, else earlier in its section — sets the frame: upper lip, lips, chin, jawline,
  cheeks, temples, forehead, eyes, nose, neck. Nothing named: her cheeks, where the spots are. Only when her lips
  would move with no sound of hers is the mouth kept out — never a random forehead.
- **The lead talks only when the lead is heard** (4 Oct: *"you're showing her talking when she should not be
  talking … we already talked about putting [covers] over things that were already broken, so we just go back to
  that"*). `mouths.py` checks what is on screen 10 times a second: the lead's mouth moving while someone else talks
  or nobody does, or the lead's voice over a mouth that isn't saying it, stops the render. A close-up that would
  show the mouth in that moment frames above it instead, and a too-short shot stays on its own take.
- **Mm-hmms go under the other person's words** (4 Oct: *"the overlays of the umms and the MHMMs"*; the swipe:
  "Surgeon 1 speaks, Creator murmurs"). A listener's murmur starts before the speaker's line ends and never takes a
  gap of its own (Creator-A: 3.4 s shorter, the talk runs on).

## 5 · B-roll

> "We need to put actual b-roll on here and show real before and afters… especially when he's describing
> how to use the scrub and the results to expect… we can solve some of this with putting b-roll on top of
> mess ups."
> "b-roll and such should be about 4 seconds each."
> "When we're talking about the other options you need to actually insert those too. So get images from
> the internet or TikTok then we need to pull them as b-roll."

- **Length:** about 4 s per piece. Never a flash under ~1.5 s; the piece before runs on instead.
- **Real footage only.** Product B-roll comes from our own creators' raw clips on the brand's shared drive.
- **What gets covered:**
  - how-to moments (scoop, apply, the timing);
  - results;
  - the offer;
  - what a speaker names: when a doctor names another treatment (hydroquinone, peel, laser, bleaching), show that treatment;
  - every mess-up: lips moving with no words, clip restarts, glitches.
- **When the speaker is holding up the product, keep it** (*"at the beginning when he's holding the product and showing it, keep that"*). Then the B-roll rolls on through the line and any following stretch that has no picture of its own (*"keep rolling b-roll"*).
- **Never another person's full face over a moment about our lead.** It reads as a different patient. Use a quiet moment of the lead from the same room instead (lips closed, found by measuring the mouth), or a close-up with no face.
- **B-roll sits on top; the clip under it keeps playing,** so its sound carries on.
- **Be intentional; never reuse a piece** (3 Oct: *"you're reusing b-roll and such that's awkward be
  intentional with the b-roll itself you should have a clear look at what's actually there … ensure there
  is movement throughout this edit"*).
  - Look at the footage first, then match each piece to the exact words over it.
  - Each piece appears once in the ad, and that includes "quiet moment" inserts.
  - Every piece moves: real motion, or a slow push-in on a still.
- **The story decides what may be on screen** (3 Oct: *"you put broll on top early in the video when doctor 1 is
  speaking of another woman do not do that at all. that definitely makes it jump out as an ad… think critically
  around the concept of the video itself and what's being depicted … we're focusing on the woman in the chair's
  experience. we don't really show anything results related of other people or product until much later"*).
  - Until the product comes in (Creator-A: Section 13, when the third doctor brings out the scrub), the screen is the lead's own experience. No other people, no product, no results.
  - Covers there are the lead's own footage: a **close-up on her** (a tight crop of the very moment on screen, framed on her cheek and spots above the mouth, so it reads as the camera pushing in and hides lips that move with no words — a zoom used as a cover, so a repair: written only in `decisions.json`, out with E30 once the take pick is proven, V15), or a quiet moment of her from the same room.
  - The edit map refuses any outside B-roll before that point (`decisions.json → story.lead_only_until`).
- **Failed-solution lines cut in the thing named, always allowed** (3 Oct: *"cutting in a hydroquinone is fine
  that's what we're seeking"* … *"all the failed solution lines can do this by the way. bank this for future
  editing reference"*).
  - When a line names a failed solution (hydroquinone, a peel, a laser, bleaching cream, whatever the swipe's competitors are), cut in a shot of that solution, early in the ad too.
  - Show the solution itself: the tube or cream, the treatment, the device. Never another woman's face, which would break the lead's story.
  - It must look like the ad (phone-grade, not stock).
- **When a speaker names an option, show it** (*"when we're talking about the other options you need to
  actually insert those too… get images from the internet or tiktok"*). Creator-A: hydroquinone being dabbed
  on, a glycolic peel being brushed on, a laser passing over a face and neck. Pulled from TikTok and the
  web (not our footage; usage to settle).
- **B-roll looks like the ad, not like stock** (3 Oct: *"no they look too high quality"*). A phone-grade
  UGC ad gets phone-grade B-roll: real people's TikTok/Reels-style videos, not polished stock footage.
  Found with web search; downloaded link by link with yt-dlp, the same thing Snaptik does (*"I literally get
  videos then put them in snaptik.com"*). Apify is not needed for this.
- **The people in B-roll match the ad's avatar** (*"no reason to pull black women"*). For Creator-A: older
  women with fair, spotted skin. No young models and no other demographics. Whatever the ad's avatar is,
  the B-roll people read as her world.
- **Before/afters are shown on the results lines** (*"Where are the before and after scenes???"*).
  - A 4:5 still is set on a soft blurred extension of itself to fill 9:16, with a slow push-in.
  - A paired photo can be cut into a true before → after: each half close up, 2 s each.
  - Two versions of the same photo count as one piece. Use it once.
- **A glitch inside a clip is covered by the clip's own time.** A third hand appeared at 1.5–5.0 s of the
  offer clip (*"that last scene still doesn't have any covering when the 3rd hand pops in"*). The piece
  over it fits the words: a big heaped scoop on "a big tablespoon".
  - Glitches are found by eye in the sweep. The automatic hand counter missed hands that were holding things.

## 6 · Looking at it: the frame-by-frame sweep

> "You need to do a frame by frame sweep at this stage of editing, this is how we ensure it's ultra smooth."

- `machine/sweep.py` runs before anyone is shown a cut. Nothing is rendered: it pulls the frame that is on screen at every step (4 a second), straight from the sources.
- It writes a strip per 10 s, every cut as before | after, and a list of black and frozen frames.
- A person then LOOKS at every cut and the strips. The machine only finds the frames worth looking at. Faces are checked by eye; automated face checks proved unreliable on 3 Oct.

## 7 · The timeline, not the render

> "I just need you to build the timeline, don't render."

- The timeline is the review surface: a player that plays the cut straight from the clips, with every layer on one clock below it (like the DÆMN carousel's edit map). Tap a lane to jump there.
- Words are placed clear of the face, measured frame by frame.
- Rendering comes after the timeline is approved.

## 8 · Fix it upstream: every edit fix, and the station that should have prevented it

> "Make sure that this is all being established in our proper editing log as well, because all these little
> things, where upstream could they have been fixed in the overall chain of any of these stages, right? At the
> highest level possible. That way, for future generations, it just runs smoother and smoother and smoother,
> to the point we can just literally print video ads."

One row per problem the Creator-A edit had to fix. Since V15 (2026-10-20, *"the edit cuts, it does not repair"*) the edit
column is history: every one of these is fixed at its station, and the edit no longer covers it (E31, 2026-10-21).
**Station** is the earliest place in the chain (teardown ·
writing · elements · pictures · clips · edit) that could stop it. Status: **fixed** = in the chain on main ·
**to fix** = not yet.

| Problem the edit fixed | How the edit fixed it | Fix it at | Status |
|---|---|---|---|
| Her face drifted (paler, older, brown eyes) across clips | remade from the approved picture | **clips**: every person clip starts from the approved picture, never a handed-on frame | fixed (PR 138/139) |
| A clip made from a picture with **her eyes closed** came out with brown eyes (Section 18) | remade from the same set-up's eyes-open picture | **pictures**: refuse to approve a talking-clip start picture with the eyes closed | to fix |
| Omni **made up off-camera lines** (4 clips) | clip sound kept only on the scripted words | **clips**: prompt says nobody else speaks; the words check flags extra speech | prompt fixed (PR 140); check to fix |
| A clip **stopped before its line ended** ("Use all three", "Literally", "Guaranteed") | trimmed, the words added in her cloned voice, covered | **clips**: plan each clip's length from the line's real spoken length plus a margin; the words check must hear the LAST word, or remake | to fix |
| **Lips moving with no words** (8 stretches) | close-up on her above the mouth; a quiet moment of her | **clips**: mouth check after each clip (the clip checker has it) flags it before the edit | to fix |
| **Words burned into a clip** ("So how long?") | punch-in past them | **clips**: read the frames for text (the text reader exists) and remake | to fix |
| **A third hand** in the offer clip | B-roll over it | **pictures/clips**: prompt names each hand and what it holds; the sweep catches it | sweep in place; prompt to fix |
| A voice line in the **wrong person's voice** | — | **writing/clips**: the brief's `speaker` decides; planning refuses without it | fixed (PR 137/139) |
| A customer saying the brand's **"we'll gladly issue"** | "they'll" patched in her voice, covered | **writing**: a brand promise in a customer's mouth is in the third person (they'll / they put it in writing) | to fix |
| **Headline stacks** taken from the brief, not the swipe | only the swipe's text kept | **writing**: the brief's on-screen text lists only what the swipe shows | edit fixed; brief to fix |
| **Receipt cards / thumbs-up end card** felt fake | removed; native "Option 1/2/3" text pops | **writing**: no paper-graphic cards; between-section beats are native text pops | to fix |
| **Phone insert shots** added nothing | removed; the talking runs on | **writing/storyboard**: an insert must show something the line needs | to fix |
| **B-roll** had to be found during the edit | found, pulled and placed by hand | **writing**: the brief names every B-roll moment (failed solutions, how-to, results, offer) and what fits the story; **production** pulls it (creators' raw clips; TikTok via yt-dlp) | to build |
| **Hook variations** never got made | 5 opening clips made at the edit | **clips**: the planner makes one opening clip per hook in the brief | to fix |
| Caption look was TikTok-style | IG/FB native captions | **edit**: caption look picked by format, else the app the piece pretends to be made in (`looks/bank.json` `pick`, 2026-10-21) | edit fixed |
| Ours runs **2:25** against the swipe's **1:21** | — | **writing**: hold the brief to the swipe's length (±20%); every extra second is paid for twice (clip + edit) | to fix |
| Picture spend not recorded | — | **pictures**: the picture door writes its cost to the ledger | to fix |
| **Lips off in the pitch** (picture 12 frames behind the voice) | renderer fixed: shots end to end, lips measured on every render | **edit** (render): it was the renderer, not the clips | fixed |
| **Music stopped** at 1:59 | bed remade to the full length | **edit**: the music tool makes the bed to the edit's length | fixed |
| A clip **ended inside its last word** ("Guaranteed") and the check's flag was ignored | "Guaranteed." made in her voice, covered; render refuses a cut word | **clips**: plan each clip's length from the line's spoken length plus a margin; **edit**: the render stop (built) | edit fixed; clips to fix |
| **Close-ups on her forehead** | close-ups framed on the part the words name | **edit**: the close-up reads the words (built) | fixed |
| A card filed by hand had **no ad set** (avatar/angle missing) | written onto the card | **delivery**: the card writer takes avatar and angle | fixed (PR 152) |

## 9 · What it cost, and what it should cost

> "Technically we spent almost $100 making this video… The next generation should cost a clean $25 between the
> images and the videos, and then the version after that, ideally, we're getting it even lower… This was a
> 2-minute-long video. These types of edits would take a week-plus for one version."

**Creator-A, as made**, from the run's spend ledger:

| What | Spend |
|---|---|
| Clips, Omni on fal | $61.38 |
| Old upscale route | $1.34 |
| Picture checks | $5.23 |
| **Logged total** | **$67.95** |
| Pictures (108 × GPT Image 2.5, not logged; ~$0.11 each) | ~$12 |
| Hook openings | +$7.20 |
| **Total** | **~$80**, plus the voices |

**Where the money went that a clean run won't spend:**
- the 360p tests, the remakes for face drift (10 clips), the eye remakes and the needless remakes from the old eye gate;
- clip time later covered by B-roll or taken out (the offer clip, the phone shots).

**A clean run of this same ad:**
- 22 pictures, one take each: about $2.50;
- clips with no remakes: 178 billed seconds × $0.15 = $26.70.

**To get to $25 all-in:**
- write it to the swipe's length (≈ 80–100 s): about $15 of clips;
- don't make clips for stretches the brief already marks for B-roll.

## Open, to fill in at the roll-up
- Before/after: the landing-page card (live on our site, no person/permission on file) is in the Creator-A
  edit; no real before/after of spots fading over weeks exists yet.
- Usage terms for the creators' raw clips, and for TikTok/web B-roll.
- Sound effects: laid from production's SFX bank (2026-10-21, row 5); a cue whose bank row is not made yet is named
  in the map's notes and the audit holds NO SOUND FX.
- Re-drawing a clip's last frame from the approved picture for scenes that must continue (tested, waiting on his yes).
