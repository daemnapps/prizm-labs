# The Edit Line — cut and dress

Updated 2026-09-23. Artifact: see `context/artifacts.md`. Printed by `machine/edit_line_page.py` from `context/edit-line.json` — edit the JSON, not this file.

The brief folder is done (clips, voice, handoff doc). These stages turn it into a finished ad with no editor. Each open decision has a code so it can be answered in one line.
## Where everything stands

The whole machine on one page, swipe to finished ad. Each stage does its own job cleanly so the next one just runs: the teardown names every element, the brief carries it, production makes it and checks it, the edit only assembles. Everything here is judged by one thing: does it hold attention and win a customer?

| Stage | What it does | Today |
|---|---|---|
| 1 · Teardown | Watches the swipe and names every element on its timeline: talking, B-roll, cards, screens, splits, green-screen, end card, the scroll-stopper, transitions, text layers, sounds, music feel, and the doctrine section of every row. Fixed today: It was being handed a blank prompt, so it never saw your 15 sections. Fixed, and any label that isn't one of the 15 now gets one re-read, then the run stops. | built |
| 2 · Spice | Rewrites the script for the mouth so it sounds like a real person talking. Sets the pace once for the whole piece, kept from the swipe. Fixed today: Pace was being dropped here. Fixed. (The language-line add-on was withdrawn: not what you meant.) | built |
| 3 · Brief | Carries every element to production in a fixed order: talking scenes, B-roll, cards, screens, splits, green-screen, end card, layers and sound, a song block when sung, then the check that every swipe shot is accounted for. Every scene has its section and says whether it's to camera. Right after it's written: every hole in a line is filled automatically, from the brand's folder first, then the web, then a sensible inference, with the source noted. The brand's own price, guarantee and claims only ever come from its files. Then every scene's section is checked and corrected. Fixed today: Holes no longer reach you or the voice. On Nova's brief it researched the receipt ($__ for kojic acid soap, from the web) and inferred the dose line. | built |
| 4 · Production checks (before any money) | Section fit (the words do the section's job) · the roll sheet (no swipe shot lost) · every label is a real doctrine section. Fixed today: Section fit is new. It caught 4 wrong labels on Nova's brief. | built |
| 5 · Voice & song | One continuous voice read, with numbers spoken by our rules and brand words by the pronunciation list, set to one volume. Then the audio gate: says its line, finishes it, brand words and numbers heard right, sound not broken. Sung pieces go through the song chain (ElevenLabs v2.5, lyrics only from the script). Open: 5 words being re-picked by ear · June's saved voice settings aren't sent (your call) · Brand B has no cast voice yet | built |
| 6 · Pictures | First and last frames, then clips timed to the voice. Plates for cards, screens and split sides, green-screen backgrounds, the end card edited from the real packshot. Every frame checked for the centre 4:5 zone, with the face position recorded. Every clip colour-matched to the first frame. | built |
| 7 · Remake | A broken scene is remade surgically: only the broken element (voice, frame or clip), then what's built on it, from the same originals. Two tries, then a person. | built |
| 8 · Edit: cut | Listens first. Trims start and end silence, keeps breaths, a 7% punch-in after cut pauses, the scenes in order, B-roll placed by the words it covers. Every piece is labelled with its doctrine section. Open: your review stop for mid-clip pauses isn't built yet | built |
| 9 · Edit: dress | Hook on frame one, captions, cards, screens, splits, green-screen, end card, name tags, arrows and circles, platform bubbles, icons and emoji, disclaimers, transitions, one colour grade. Music ducked under the voice, sound effects, room tone, the mix. Text moves off the face. Open: captions should use the script's spelling, not the transcriber's · the green-screen cut-out is made but not placed yet | built |
| 10 · Retention checks | Flags where a video would lose attention: a shot held too long, not enough visual change, dead air, text pops with no sound, no zoom on key words, B-roll rhythm, loop ending. All warnings and scores with numbers you tune, nothing blocks. Shown on the live timeline. | built |
| 11 · Versions | One video per hook on the same body, 15/30/60-second cutdowns, a cover per hook, every file named. 9:16 only. | built |
| 12 · Variation engine | Swap any doctrine section, hook, headline, scroll-stopper, style, framework or sound as named parts. Pay for parts once and assemble combinations for free, with results joining back to the part that won. Open: your V-2 to V-4 calls | planned |

**Libraries:**

- **Doctrine sections:** 15, from your marketing doctrine (every stage reads the same list)
- **Ad frameworks:** 8: PAS, AIDA, BAB, story/testimonial, mechanism-led, us-vs-them, direct offer, identification-only
- **Fonts:** 15 open-licence, all installed (TikTok Sans, Montserrat, Inter, Anton, Bebas Neue…)
- **Text zones:** 9 named spots for TikTok and Reels (organic), headline a touch lower, captions toward the bottom, text moved off the face
- **Platform bubbles:** 16 styles: TikTok reply, IG/YouTube comment, X post, iMessage, WhatsApp, DM, stitch, duet, search, likes, views, review
- **Icons & elements:** 52: UI icons, emoji, stickers, arrows, circles, stars, badges, price tags, bursts, progress bars, sparkles
- **Transitions:** 19 listed with what triggers each, plus 8 shader transitions (cube, warp, pixelize, swirl…)
- **HyperFrames blocks:** 382 ready-made blocks indexed, installable by name
- **Music:** ElevenLabs won your blind test; bank rows ready to make; song chain on v2.5; 90s neo-soul style approved
- **Sound effects:** 16 rows ready to make (whoosh, pop, riser, ka-ching, room tones…); trending sounds pool being built in your organic swipe tool
- **Pronunciation:** Brand A 80 words (all spoken ones confirmed by your ear), Brand B 48; numbers by our own rules
- **Caption looks:** 3 (bold highlight, clean lower, one word)

**Waiting on the owner:**

- Say "go" to make Nova's ad for real (a few dollars of pictures + Higgsfield credits for ~60s of clips)
- June's saved voice settings: send them? (changes her sound going forward)
- The music and sound-effect bank files: approve the spend at the permission prompt (about $__)
- Variation engine: V-2 (which combinations), V-3 (where extra sections come from), V-4 (thumbnails)
- Pause review: its own quick stop, or part of the timeline review?

**Known gaps:**

- Holes and wrong section labels are now fixed automatically at the brief. Production checks both again before it spends.
- The Apify research account is out of credit (the spare took over). Research on the Nova run came back empty.
- The teardown and brief prompts don't know the new bubble kinds, icons, zones and fonts yet. That's the repo-wide sync pass.
- Nothing from today is committed yet.


## Cut

Turns the clips into one clean run of picture and sound. Nothing gets added here, it only gets cut and ordered.

### CUT-1 · Trim the dead air — rules settled · remake wired

- **Tracks:** V1, A1 · **Done by:** machine
- **Takes in:** Each clip's own sound track. The edit listens to the sound, not the video and not the written-out words.
- **Makes:** Each clip with its start and end silence gone and its breaths kept. Every longer pause is marked for your review, and every clip that stops mid-line is sent back to production.

Rules today:

- Listen first. Silence is found in the sound itself (anything quieter than −35 dB for 0.15s or longer). The written-out words only say WHAT is said. The word tool stretches words across silences and even past the end of a clip, and that broke the an-earlier-run test.
- Silence at the start and end of a clip is always cut.
- Breaths (pauses under about 0.35s) are always kept. Cutting them makes the voice sound robotic.
- Mid-clip pauses (0.35s or longer) are proposed by the machine and checked by you. Some are dead air, and some are a beat that makes the line land (the 2.2s before Nova's “No.” in an-earlier-run clip 6).
- After a cut pause, the next piece zooms in 7% so the jump reads like a second camera in the room.
- A clip that stops mid-line is an error, not something to edit around. It's marked clearly, goes back to production to be made again, and the production prompt that let it through gets fixed.

**What listening found:** an-earlier-run, 8 clips, 76.7s: about 50s talking · 6.8s start/end silence · 15.5s mid-clip pauses · 4.7s breaths. Two clips stop mid-line: clip 5 ends “…said taking the” (the script goes on “…top layer off is a cop out”), and clip 1 ends at “which is crazy” (the script goes on “because I'm going to ask them…”). Tested on 23 Sep: the edit's new check flagged clips 1 and 5 as cut off and passed clip 7 (whole line).

**Fix:** Cut from the sound, not the word timings, and the clips-running-past-their-end problem goes away. Before, the breath after the last word was measured from the word tool, which put clip 9's last word at 15.7s on a 14.1s clip.

Open decisions:

- **T-3** Your pause review is decided but not built: today the edit still cuts every pause longer than the pace setting on its own. Should marked pauses be their own quick stop (listen, keep or cut) before anything else is laid on? _Not built yet._
- **T-2** The punch-in (zoom 7% on the piece after a cut pause)? — settled: Keep it. It gives real camera-movement vibes, like someone is actually in the room with her. (23 Sep)
- **T-1** Pace: one setting or per format? — settled: Per format, from the brief. FIXED at the source on 23 Sep. The teardown heard the swipe's pace (e.g. “escalating”), but the spice sheet (stage 4g) dropped it, treating pace as something each section needed separately. Spice v5 sets pace ONCE for the whole piece, KEEPs the swipe's value, and never leaves it blank when the teardown named one. Every scene in the brief now carries it. The teardown now runs v5.
- **T-4** Start and end silence? — settled: Always cut. (23 Sep)
- **T-5** Breaths? — settled: Always kept. (23 Sep)
- **T-6** Mid-clip pauses? — settled: You review them a second time to check the pacing is right. (23 Sep)
- **T-7** A clip that stops mid-line? — settled: Reproduce it, clearly marked as an error, and fix it upstream. BUILT 23 Sep. (1) Production's words check now asks whether the line FINISHED, not just whether the words were similar. A cut-off clip is CUT_OFF and never ships. (2) The edit listens to every talking clip before cutting, and a cut-off clip stops the edit and is sent back. (3) A remake order lands on the production run, and the remake-clip skill carries it out.
- **T-8** How is a sent-back clip remade? — settled: Surgically (your words, 23 Sep). Name the broken element and remake only that, then rebuild what depends on it from the same originals. Voice broken: remake that scene's voice slice, then re-clip from the SAME frames with the new voice. Frame broken: fix the frame with one change, then re-clip with the SAME voice. Only the clip broken: re-clip with the same frames and voice. For a cut-off clip the machine listens to the voice slice first to tell which one it is. Two tries at most, then a person.
- **T-9** Where is a cut-off line caught? — settled: At production, on the AUDIO, before any picture is paid for (your call, 23 Sep). BUILT: an audio check runs right after the voice is made. Each scene's slice is heard. It must say its line, finish it, and not be silent or clipping. A failing slice is remade once, voice only, then the run stops. The edit's own listen stays only as a backstop. First real test (pigment-memory): every line whole, but the read drifts in volume by 17 LU between scenes (warned, not stopped).

The spice sheet, stage 4g · v5 (pace fix): the full prompt: `tools/copywriter/prompts/video/stage-4-loop/4g-spice/stage4g-spice-v5-damon.md` (verbatim on the page)

The remake-clip skill, word for word: `.claude/skills/remake-clip/SKILL.md` (verbatim on the page)

### CUT-2 · Assemble — built

- **Tracks:** V1, A1 · **Done by:** machine
- **Takes in:** The trimmed pieces and the handoff's scene order.
- **Makes:** One continuous run, scene after scene, with hard cuts.

Rules today:

- Scenes go in the handoff's order.
- Hard cuts only, no dissolves or wipes.
- A clip that QC held back is left out and named on the review page.

Open decisions:

- **A-1** Should the edit ever drop or shorten a scene to hit a length, or always play the whole script? If there's a target length, what is it per format? _Now: every approved scene plays, and the length is whatever's left after the dead air is out (an-earlier-run ≈ 76s before trimming)._
- **A-2** The teardown writes a control hook plus 5 variations. Should the edit make one video per hook at this stage, or build one video now and swap hooks later in Variants? _Now: one video, from the hook the handoff names._

### CUT-3 · Lay the B-roll — wired through brief + production · first real run next

- **Tracks:** V2 · **Done by:** production makes it; the cut prompt places it
- **Takes in:** The B-roll clips production made (scenes that aren't to camera), each with the words it covers.
- **Makes:** Each B-roll clip placed over the exact words it shows, with one sentence on why.

Rules today:

- B-roll goes where the words name something the viewer should see: the problem, the product, the proof.
- It's placed by the words it covers, not by seconds, so it stays right when the timing changes.
- A scroll stopper opens the video and runs the length of the hook line.
- Two B-roll clips never touch, the offer is never covered, and the first words after a B-roll run are never covered.
- Your rules in learned.json outrank the prompt's own rules.

**What listening found:** Checked 23 Sep. The idea for each B-roll shot comes from the swipe: the teardown labels every shot A-roll or B-roll and lists the B-roll as a make-list, and the brief must carry each one or say why it dropped it. The brief can also ADD B-roll (any line that shows proof, product or mechanism; at least a third of scenes). Production makes B-roll as its own scene with its own clip. What makes a scene B-roll in our data is one field: to_camera = false. A new camera angle inside a scene is NOT B-roll; it's a beat within one clip, because a scene is two frames and one continuous clip, and anything needing a hard cut must be its own scene. Nova (an-earlier-run): NO B-roll footage. Its brief predates the A/B labels. The swipe's non-talking shots were graphics and cards (the SPOTS map ×3, receipts ×3, the CTA grid), carried only as edit layers, and two real inserts (a tight shot of the leg, the scrub on skin) were written INSIDE talking scenes, where they can't cut. So no clip exists for them.

Open decisions:

- **B-1** Run the next brief end to end so we see real B-roll and card plates get made (nothing has been spent on it yet)? _Proven on test briefs only._
- **B-5** One rule clash in the brief prompt: it already says “a brand fact not in the files: cut the line”, but a card with a price nobody has approved is marked [UNFILLED] (so the run stops and asks you) instead of the line being cut. That exception applies only inside card words. Keep it? _Built as the exception._
- **B-0** Where is B-roll decided and made? — settled: Named in the teardown, carried in the brief, made at production. It has nothing to do with the edit. (the owner, 23 Sep.)
- **B-2** How much B-roll? — settled: Set by the swipe: every swipe B-roll shot is carried, plus any line that shows proof, product or mechanism, and at least a third of the scenes.
- **B-6** How it's carried (BUILT 23 Sep) — settled: AI brief v13 writes the talking scenes first, then a B-ROLL table (which swipe shot each comes from, what it shows, the exact words it plays over), then a CARDS table, then a roll-sheet check: every swipe shot mapped to a scene of ours or dropped with a reason. Every scene must say to_camera true/false, and one that doesn't is refused. No B-roll inside a talking scene. Production refuses a brief whose roll sheet leaves a swipe shot unaccounted for, or maps it to the wrong kind of scene. Old briefs only get a warning.

Prompt: `prompts/stage-2-cut/stage2-cut-v2-damon.md` (verbatim on the page)

The teardown, stage 1: labels every row with its roll, section, layers and sound: `tools/video-teardown/prompts/stage-1-teardown/stage1-teardown-v13-damon.md` (verbatim on the page)

The AI brief, stage 5 · v14: the full prompt: `tools/copywriter/prompts/video/stage-5-brief/ai-lane/stage5-ai-brief-v14-damon.md` (verbatim on the page)

## Dress

Everything laid on top of the cut: words, graphics and sound. Each layer is a setting, so changing one never re-cuts the footage.

### DRESS-1 · Text: hook, cards, captions — built · face-blind

- **Tracks:** T1, T2 · **Done by:** machine
- **Takes in:** The cut, the handoff's card words, and the caption look.
- **Makes:** The hook on screen from frame one, each card on its clip, and word-by-word captions.

Rules today:

- The hook is on screen from the very first frame, with no fade, and lasts as long as the clip under it (your rule, 20 Sep).
- Cards use the handoff's exact words and line breaks. Type is always a layer, never generated into the clip.
- Captions show 2–4 words at a time, and the spoken word lights up.
- Nothing sits where the app's buttons cover the frame: the top 12%, the bottom 25% or the sides.

Open decisions:

- **X-1** Text doesn't know where the face is yet (you flagged this on the first proof). Does it need to move off the face automatically before the next test, or is that fine for now? _Now: the hook and cards sit at 16% from the top, wherever the face is._
- **X-2** Should the hook and cards have one house style, or copy each swipe's own text style? _Now: one style, black heavy type on a white plate._
- **X-3** Captions on every ad? And which look is the default: bold highlight, clean lower, or one word? _Now: on, with bold highlight (white caps, the spoken word turns yellow)._
- **X-0** When does the opening text start? — settled: The opening caption always starts at the very beginning of the video, on frame one. (23 Sep, restating 20 Sep)

### DRESS-2 · Inserts: receipts, graphics, end cards — card pictures made at production

- **Tracks:** V3 · **Done by:** production makes the picture; the edit sets the words
- **Takes in:** The handoff's insert list (in an-earlier-run: three receipts, three “THE SPOTS” maps, a 4-panel end grid) and the offer bank for any price.
- **Makes:** Each insert built as a designed graphic and cut in where the handoff puts it.

Rules today:

- Every card is its own scene in the brief: a picture with no words in it, plus the exact words, where they land, and their sound cue.
- Production makes the picture (one still, the same image model as every first frame) and no clip.
- The edit only sets the words on top, because type is a layer, never generated into a picture.
- A price only comes from the offer bank. An unapproved figure is [UNFILLED], and the run stops and asks.

Open decisions:

- **I-1** The edit doesn't read the card data yet (the words, where they land, their sound). That's the next edit build. Which other inserts should get templates: name tags, arrows/circles, platform UI (see “Every element of a video”)? _Card pictures come from production; the edit's side isn't built._

### DRESS-3 · Sound: music and effects — not built

- **Tracks:** A2, A3 · **Done by:** machine, from a sound bank
- **Takes in:** The cut and the handoff's sound cues (an-earlier-run: one cash-register sound, identical each of the 3 times, plus an upbeat stinger at the end).
- **Makes:** A music bed under the voice and each effect on its moment.

Rules today:

- The music sits 18 dB under the voice.
- An effect lands 2 frames before its picture.
- A fixed cue is the same file every time.

Open decisions:

- **S-1** Music on every ad, or only on some formats? For example, none under a talking vlog and music under a demo. _Not decided. No music is laid today._
- **S-2** Where should sounds come from: a licensed library we bank on the Drive once (a fixed set of whoosh, pop, ka-ching and stinger, reused forever), or generated per ad? _Not decided. There are no sound files today._

## Before the cut — reading the handoff (built, parked)

Prompt: `prompts/stage-1-read-pack/stage1-read-pack-v1-damon.md` (verbatim on the page).

## Every element of a video

Every element a finished ad can carry. The rule (your words, 23 Sep): the teardown names every element, the brief carries all of them, production makes all of them, and the edit only assembles. At extreme scale each element is a typed, reusable part with an id. The teardown marks it on the swipe's timeline, production makes it once as a file, banks (music, SFX, templates, disclaimers) are made once and reused forever, and the edit becomes a deterministic assembly of parts. A new version is just swapping parts: hook × body × CTA × music × caption look × ratio.

| Group | Element | What it is | Teardown | Production | Edit | Today |
|---|---|---|---|---|---|---|
| Picture | A-roll | The person talking to camera. The spine the whole ad hangs on. | labels it | makes it (talking clip on the voice) | trims, orders | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Picture | B-roll: demonstration | What the words describe: the product in use, the problem, the proof. | labels it (B-roll + what it shows) | makes it (its own scene) | lays it over its words | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Picture | Inserts / close-ups | Tight detail shots: texture, the label, the tube in hand, skin up close. | labels it as B-roll | makes it (its own scene, never inside a talking one) | cuts it in | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Picture | Scroll-stopper opener | A visual pattern-interrupt in the first 1–2 seconds, before or under the hook line. | labels it | makes it | opens on it | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Picture | Screens & receipts | Screenshots: reviews, comments, a website, a text thread, an order confirmation. | labels it (S / X / G / E) | should make it as a plate | drifts it (never a frozen still) | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Picture | Before / after & split screen | Two states side by side or wiped: before/after, us vs them, two options. | labels it (S / X / G / E) | makes both sides | builds the split as a layout | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Picture | Green-screen / picture-in-picture | Creator over a background (an article, a post, a product page), or a small face over footage. | labels it (S / X / G / E) | makes the background and the talker | composites them | partly — picture-in-picture works; a true cut-out needs a keyed clip from production |
| Picture | Camera moves in post | Punch-ins on cut pauses, slow push on stills, a shake on an impact. | n/a | n/a | applies them by rule | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Picture | Transitions | How one shot hands to the next. Hard cut by default; whip, match cut or zoom only when the swipe does it. | should label non-cuts | n/a | applies them | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Picture | Colour match | Every AI clip looks like it came from the same camera on the same day. | n/a | matches every still AND every clip to the first frame | one grade over the whole piece | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Graphics | Hook headline | The big line on screen from frame one. | labels it (with the swipe's text look) | n/a | composes it | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Graphics | Captions | Word-by-word subtitles in a set look. | reads the swipe's caption style | n/a | composes them off the voice timing | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Graphics | Cards | Receipts, price, stats, a claim, a list, a map with circles: the words on a designed picture. | labels it (C row) | makes the picture, text-free | lays the words on it | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Graphics | Lower-thirds / name tags | “Dr. …, dermatologist”, “Nova, 64”: who is speaking. | labels it | n/a (template) | composes it | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Graphics | Annotation | Arrows, circles, highlights, underlines pointing at the thing. | labels it | n/a (template) | draws it on its moment | partly — arrows and circles land on their words, but at a fixed spot; nothing tracks a moving thing yet |
| Graphics | Platform UI | A comment-reply bubble, a stitch or duet frame, a search bar, a like count. | labels it | n/a (template) | composes it | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Graphics | End card & CTA | Product, offer, guarantee, “shop now”, logo. | labels it (S / X / G / E) | makes the packshot plate | composes the offer words | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Graphics | Disclaimers | “Results may vary”, #ad / paid partnership, claim footnotes. | n/a | n/a | adds by brand and claim rule | partly — the edit adds them by rule, but each brand needs its compliance file (brands/<brand>/compliance.json), and none exist yet |
| Sound | Voice / dialogue | The one continuous read. It drives everything. | reads the swipe's delivery | makes it, levels it, checks it | keeps each clip's own sound | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Sound | Music bed | A licensed track under the voice, ducked 18 dB, cut to its beat. | labels it | picks it from the bank (bank built; files not made yet) | lays it and ducks it | building — everything is built; the bank files aren't made yet (your go at the permission prompt) |
| Sound | Sound effects | Whooshes on moves, pops on text, a riser into the reveal, a ka-ching on a price. | labels it | picks it from the bank (bank built; files not made yet) | lands it 2 frames early | building — built; bank files not made yet, plus a meme & viral sound bank to seed (see below) |
| Sound | Room tone | Quiet background air under every cut so a trimmed pause never drops to dead digital silence. | labels it | picks it from the bank (bank built; files not made yet) | fills the gaps | building — built; bank files not made yet |
| Sound | Final mix | Everything balanced and delivered at the platform level (about −14 LUFS). | n/a | n/a | masters it | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Versions | Hook variants | The control hook plus 5 variations on the same body. | writes the 5 hooks | makes each hook's opening | swaps the opening, keeps the body | have — one video per hook on the same body |
| Versions | Body / CTA modules | The ad as blocks (hook, problem, proof, offer, CTA) that recombine. | sections every swipe | makes each block | assembles combinations | missing — this is the variation engine: sections by the doctrine (planned, below) |
| Versions | Length cutdowns | 15 / 30 / 60-second versions from one master. | n/a | n/a | cuts them by priority | have — 15/30/60, whole low-priority scenes out first; a line is never cut mid-scene |
| Versions | Ratio | 9:16 only. No 4:5, no 1:1 (the owner, 23 Sep). Content kept in the centre 4:5 zone. | n/a | makes 9:16 with content in a 4:5 zone | one 9:16 render with its safe zones | have — built end to end 23 Sep: teardown names it, brief carries it, production makes it, edit assembles it; proven on a no-spend test render |
| Versions | Cover frame & name | The thumbnail frame, plus the file name that ties it back to spend. | n/a | n/a | picks the cover, names it | have — a cover per hook plus naming; designed thumbnails come with the variation engine |

## The variation engine (planned)

Your words, 23 Sep: “full control of our creative output and variation process down to the word spoken, all the way to pumping out 100 variations at a time with different formats and styles.” The trick at scale: every variation is a set of PARTS. Each part is made once, and the edit assembles combinations for free. Money is spent on parts, never on combinations.

| What varies | Level | What gets made |
|---|---|---|
| Hook line — The first spoken words. | words | voice + the opening clip |
| Headline — The on-screen text from frame one. | words | nothing (text layer), free |
| Scroll-stopper — The opening visual that stops the thumb. | picture | one clip |
| Sections (the doctrine's 15) — Swap any section for another version of the same job: hook, identification, problem, agitation, failed solutions, root cause, unique mechanism, solution, product, proof, transformation, objections, offer, urgency, call to action. The vocabulary comes from your marketing doctrine, never a list we made up. | section | voice + its scenes, per version |
| Framework — The same parts in a different order: PAS, AIDA, BAB, story/testimonial, mechanism-led, us-vs-them, direct offer, identification-only (the doctrine's ad frameworks). | structure | only the sections that framework adds |
| Style — The same film in a different look (the format library's restyle chain: screenplay, blocking and words frozen; only the rendering swaps). | style | re-rendered frames and clips per style |
| Format — A different show format for the same argument. | format | a new production (it changes what the film says) |
| Thumbnail / cover — A custom designed cover, not just a frame grab. | picture | one designed still each |
| Sound — Music bed, trend sound, SFX set. | sound | picked from banks, free |

Example: 6 hooks × 3 scroll-stoppers × 3 problem sections × 3 unique-mechanism sections × 2 offers = 324 combinations, from 17 parts, and each can run as PAS, mechanism-led or us-vs-them. Add 3 headlines and 2 music beds (free) and it's thousands, still from the same paid parts. The doctrine check removes any combination the awareness level forbids.

- The doctrine decides what's allowed. The awareness level decides which sections an ad may use and what the opening must not do (an unaware opening never names the product or price). The sophistication stage decides whether the mechanism leads. Every combination is checked against those rules before it renders, so a bad combo never gets made.
- Sections must join cleanly in any order. Each section starts and ends on a shared anchor: the same presenter, wardrobe, setting and a neutral in/out frame. So any opening can sit before any body.
- The voice stays one person, one read: each section version is voiced stitched to what plays before it, so the tone never jumps. Then it's heard by the audio gate.
- Every part has an id, and every render's name carries its part ids. Spend and results join back to the PART, so you learn which hook, problem or style wins, not just which ad.
- Structure is swapped at the section level, never mid-sentence. Words can change inside a section only by making a new version of that section.
- No 4:5 and no 1:1. Every render is 9:16.

- **V-2** Which combinations get rendered? All of them, a set number per batch (e.g. 100), or a designed test where each part appears equally often so the results say which PART wins?
- **V-3** Where do the alternative sections come from? The swipe gives one of each, so the extras would be written by the brief stage (new problem angles from the avatar research, new mechanisms from the product file), all from the same research, nothing invented. OK?
- **V-4** Thumbnails: designed covers made at production as their own element (a still with the headline composed on top, like a card), with several per ad?