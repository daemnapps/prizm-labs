# The editing standard

the owner, 3 Oct 2026: *"document everything I'm saying and what we're doing because this becomes the standard process
for editing videos and we'll roll everything together logically at the end."* 4 Oct: *"go piece by piece … make it
ultra clean and clear so we can just run that process over and over … ultra agnostic — product, brand, avatar,
concept, everything."*

**Part A** is how to run it. **Part B** is every rule, in his words, with what the machine does about it. Nothing
in the tools belongs to one ad: an ad's own choices live in its `decisions.json`, the looks and levels live in
`looks/edit-looks.json`, and the brand, product, avatar and angle come from the brief and `brands/<brand>/`.
(First ad through it: Nova's three doctors, `runs/video-edit/brand-a/an-earlier-run`.)

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
| 4 | **Render**: picture, room tone, music, captions on the spoken words | `render_map.py` | lips within a frame of the voice, every talking shot | **stops** (the file is set aside as `.held.mp4`) |
| 5 | **Scan** each finished file | `line.py` | 0 black frames · 0 dead silences · −14 LUFS (±1.5) · 9:16 | **stops** |
| 6 | **Deliver**: names (components/naming), the card, the manifest | `deliver.py` | brand, product, brief, ratio, versions, copy, page, avatar, angle | **stops** on a gap |
| 7 | **File** the card and videos into 1-check (refiled in place: the Drive link never changes) | `meta-upload/to_check.py` | the 9 card checks (media, 9:16, words, name, page live, product = page, ad set, campaign, page cap) | card shows red; Approve stays off |
| 8 | **Approve** → Meta: campaign and ad set found by name or made paused, videos uploaded, one flexible ad | the approval page | the owner's click is the only go | — |

The frame-by-frame sweep (`sweep.py`) and the timeline page are for looking: run them while settling decisions.

## A3 · The decisions: the ad's own choices (`decisions.json`)

The tools decide nothing about one ad. Everything specific to an ad is written here by the editor (a session),
with a `why` that quotes the ruling:

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

## A4 · Settings (`looks/edit-looks.json`)

Text looks (`headline-plain` default, `headline-pink-box`, `native-pop`), caption looks (`ig-fb-native`), default
timings, the mix (music −19 dB under the voice, −12 dB in the pauses, room −50 dB, master −14 LUFS / −1 dBTP) and
fonts. A new look is a new row; an ad picks it by id.

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
  - For Nova that is one opening headline (top centre, white caps with a cyan outline on a pink box), plus captions.
  - Text the brief added that the swipe doesn't have is NOT put on screen (`decisions.json → text_keep`).
- **Captions fit the platform the ad runs on** (*"these will mostly be on instagram and facebook so we need
  caption style that fits those platforms"*). Instagram/Facebook native look: sentence case, white on a soft dark
  rounded box, 3–5 words at a time, set above the Reels/feed buttons (bottom fifth kept clear). They sit above
  everything, B-roll included (*"captions need to be on top of the b-roll too"*), and drop low over a close-up.
- **Section beats are native text pops, not graphics** (*"in between each of these doctors we need to have something
  like option 1, option 2, option 3 … let's not do the paper thing just do something that looks natively edited"*):
  a short bold word on a dark rounded box that pops in at the start of the section (Nova: OPTION 1 · 2 · 3).
- **Music**: every ad gets its bed from the brief's music line on ElevenLabs Music, the ruled model (*"you need to
  generate music too"*). It sits ~18 dB under the voice, comes up a little in the pauses, and lifts where the brief
  says (Nova: at the product reveal). **It runs the whole edit, first frame to last** (4 Oct: *"the music also
  stopped, we need the music for the whole edit"*) — a brief's drop-out is not followed. `machine/music_bed.py`
  makes it at the edit's length plus a second, and refuses a bed shorter than the edit.
- **Hooks become versions** (*"you need to generate the hook variations … cut up as the variations, and then that's
  what is delivered to the final folder"*). Every opening in the brief gets its own clip, and the edit cuts one
  version per opening (`edit_map.py --hooks`).
- **Titles and names keep their capitals** inside lowercase captions (*"Dr. should be uppercase D"*): Dr., Mr., Mrs., I/I'm, brand names, and any word the script capitalises mid-sentence.
- **Structure changes need his call.** The swipe structure is locked, and a section is only removed on his word. For Nova he removed:
  - the receipt cards (*"pretty trash, I'd just remove those"*);
  - the doctors' thumbs-up end card (*"Remove the doctor putting their thumb up thing"*);
  - the phone shots (*"we can remove that clip and just keep the talking going to the next"*). The talking carries on, and the next shot comes in early.

## 3 · Edit moves first, remakes last

> "Do not regenerate clips right away if there is an issue, see what editing moves can be done first."
> "At this stage we're only looking to make deep moves on editing to make this come to life."

| Problem | The edit move |
|---|---|
| The clip model invented off-camera speech | Keep the clip's sound only across its scripted words; the real line is its own track |
| A line cut off in one clip | Take it whole from another angle that says it |
| Words burned into a clip | Punch in past them |
| Lips moving with no words | Cover them (§5) |
| Two takes of the same set-up joined | Alternate a 7% punch-in so the cut reads as a jump cut |
| A shot needs to run longer than its clip | Play it a touch slower (never below 0.75×, never on a lip-synced line). Never freeze, never black. |
| A clip grew a third hand | Cover the whole stretch with B-roll |

## 4 · Sound

- Non-word sounds ("mm-hmm", "um") are never said inside a clip. The person nods, and the sound is its own track (*"keep her head nod, but we don't need to put in the vocals with it"*).
- Each line's sound starts a hair early (0.08 s) and rings out (0.18 s), so no syllable is clipped between clips (*"some audio is getting cut from clip to clip"*).
- The player has a volume control (*"give me a volume option"*).
- **Never digital silence.** The clips are dead silent between words; a phone never is. A quiet room sits under the
  whole edit (-50 dB) and every piece of sound fades in and out over 12 ms so no join clicks (4 Oct: *"less choppy
  … the insert of new clips, captions, and sounds"* — Nova had 79 dead-silent moments; the swipe has none).

## 4b · Flow: lips, shots, movement, captions (4 Oct: *"actual flow and movement"*)

- **The lips are measured on every render.** Each talking shot's frames are found in its source clip
  (`syncheck.picture_lag`); more than one frame off anywhere = HELD (*"that whole pitch lipsync is off, why?"* —
  shots overlapped by a couple of frames at each cut and the overlap was played twice, so the picture slid 12 frames
  behind her voice by the pitch. Now each shot starts where the last ends, its source moved on with it).
- **No shot shorter than half a second** (the swipe's shortest is 0.6 s). A sliver left between two B-roll pieces
  goes to the B-roll beside it (Nova had 17, the shortest 2 frames).
- **Nothing sits still.** A shot that measures as still (40%+ of its frames barely change) gets a slow 6% push-in
  across its length, eased — the hand-held feel of the swipe.
- **Captions change on the spoken words.** Each piece comes up on its first word as heard by the clean pass
  (`listen.py`) and breaks where the line breathes (a comma, a full stop), never split evenly by the clock.
- **Never a cut-off word** (4 Oct: *"We should never be cutting off words unless I'm discreetly describing to cut it
  out"*). Before a single frame is rendered, each version's soundtrack is transcribed and held against the script;
  a scripted word that is not heard refuses the render, naming it. The only way past is fixing it, or the owner naming
  the cut (`decisions.json` `cut_words`). ("Guaranteed" went out cut off at the clip's last frame while the check had
  already flagged it — a flag nobody had to act on is not a check.)
- **Words said again are made by `machine/word_fix.py`**: the speaker's cloned voice, 3 takes, each transcribed (a
  take missing a word is thrown out), the winner cut with room both sides (0.08 s before, 0.18 s after). Under a fix
  the clip's own words stay muted to the end of the line. (The hand-made "they'll … full refund" was cut 0.03 s
  after "refund" and lost its end.)
- **A close-up frames the part being talked about** (4 Oct: *"we were talking about her lips, so you're supposed to
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
  gap of its own (Nova: 3.4 s shorter, the talk runs on).

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
  - Until the product comes in (Nova: Section 13, when the third doctor brings out the scrub), the screen is the lead's own experience. No other people, no product, no results.
  - Covers there are the lead's own footage: a **close-up on her** (a tight crop of the very moment on screen, framed on her cheek and spots above the mouth, so it reads as the camera pushing in and hides lips that move with no words), or a quiet moment of her from the same room.
  - The edit map refuses any outside B-roll before that point (`decisions.json → story.lead_only_until`).
- **Failed-solution lines cut in the thing named, always allowed** (3 Oct: *"cutting in a hydroquinone is fine
  that's what we're seeking"* … *"all the failed solution lines can do this by the way. bank this for future
  editing reference"*).
  - When a line names a failed solution (hydroquinone, a peel, a laser, bleaching cream, whatever the swipe's competitors are), cut in a shot of that solution, early in the ad too.
  - Show the solution itself: the tube or cream, the treatment, the device. Never another woman's face, which would break the lead's story.
  - It must look like the ad (phone-grade, not stock).
- **When a speaker names an option, show it** (*"when we're talking about the other options you need to
  actually insert those too… get images from the internet or tiktok"*). Nova: hydroquinone being dabbed
  on, a glycolic peel being brushed on, a laser passing over a face and neck. Pulled from TikTok and the
  web (not our footage; usage to settle).
- **B-roll looks like the ad, not like stock** (3 Oct: *"no they look too high quality"*). A phone-grade
  UGC ad gets phone-grade B-roll: real people's TikTok/Reels-style videos, not polished stock footage.
  Found with web search; downloaded link by link with yt-dlp, the same thing Snaptik does (*"I literally get
  videos then put them in snaptik.com"*). Apify is not needed for this.
- **The people in B-roll match the ad's avatar** (*"no reason to pull black women"*). For Nova: older
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

One row per problem the Nova edit had to fix. **Station** is the earliest place in the chain (teardown ·
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
| Caption look was TikTok-style | IG/FB native captions | **edit**: caption look set per platform by default | edit fixed |
| Ours runs **2:25** against the swipe's **1:21** | — | **writing**: hold the brief to the swipe's length (±20%); every extra second is paid for twice (clip + edit) | to fix |
| Picture spend not recorded | — | **pictures**: the picture door writes its cost to the ledger | to fix |
| **Lips off in the pitch** (picture 12 frames behind the voice) | renderer fixed: shots end to end, lips measured on every render | **edit** (render): it was the renderer, not the clips | fixed |
| **Music stopped** at 1:59 | bed remade to the full length | **edit**: the music tool makes the bed to the edit's length | fixed |
| A clip **ended inside its last word** ("Guaranteed") and the check's flag was ignored | "Guaranteed." made in her voice, covered; render refuses a cut word | **clips**: plan each clip's length from the line's spoken length plus a margin; **edit**: the render stop (built) | edit fixed; clips to fix |
| **Close-ups on her forehead** | close-ups framed on the part the words name | **edit**: the close-up reads the words (built) | fixed |
| A card filed by hand had **no ad set** (avatar/angle missing) | written onto the card | **delivery**: the card writer takes avatar and angle | fixed (PR 152) |

## 9 · What it cost, and what it should cost

> "Technically we spent almost $__ making this video… The next generation should cost a clean $__ between the
> images and the videos, and then the version after that, ideally, we're getting it even lower… This was a
> 2-minute-long video. These types of edits would take a week-plus for one version."

**Nova, as made**, from the run's spend ledger:

| What | Spend |
|---|---|
| Clips, Omni on fal | $__ |
| Old upscale route | $__ |
| Picture checks | $__ |
| **Logged total** | **$__** |
| Pictures (108 × GPT Image 2.5, not logged; ~$__ each) | ~$__ |
| Hook openings | +$__ |
| **Total** | **~$__**, plus the voices |

**Where the money went that a clean run won't spend:**
- the 360p tests, the remakes for face drift (10 clips), the eye remakes and the needless remakes from the old eye gate;
- clip time later covered by B-roll or taken out (the offer clip, the phone shots).

**A clean run of this same ad:**
- 22 pictures, one take each: about $__;
- clips with no remakes: 178 billed seconds × $__ = $__.

**To get to $__ all-in:**
- write it to the swipe's length (≈ 80–100 s): about $__ of clips;
- don't make clips for stretches the brief already marks for B-roll.

## Open, to fill in at the roll-up
- Before/after: the landing-page card (live on our site, no person/permission on file) is in the Nova
  edit; no real before/after of spots fading over weeks exists yet.
- Usage terms for the creators' raw clips, and for TikTok/web B-roll.
- Sound effects: still to make (the music bed is made: `machine/music_bed.py`).
- Re-drawing a clip's last frame from the approved picture for scenes that must continue (tested, waiting on his yes).
