<!-- rendered from components/marketing-doctrine/frameworks.json by render.py — do not hand-edit -->

# Taste and delivery — the dials

Bound as `{delivery}`. Source: the doctrine component; refs are line pointers into the book, for verification only.

Taste and delivery — the labelled dials that say HOW a line is said, who the room laughs at and trusts, and what it cringes at. The sections say what an ad argues; the techniques say how the argument is built; these say how it is performed.

**The receipt rule.** Every dial value is RECEIPTED to the avatar's own world — a research line or a bank row — never to the writer's taste. A dial with no receipt is left at its plain default and the direction it would have supported is cut, exactly as an uncited spice item is cut. Taste that arrives from the writer is the one failure this layer can cause: it reads as craft and it is preference, and nobody downstream can tell which it was.

**Never a voice.** Nothing here is ever a voice. A reference is a direction for timing, cadence and world; the voice is always a cast voice, cloned and then adjusted, with rights on file in the brand's own cast folder. A dial that names a person names them as a direction, never as a likeness and never as a sound.

| Dial | What it sets | Values |
|---|---|---|
| **Humor level** (`humor`) | How funny the piece is allowed to be, and in which register the joke sits. | `none` · `dry` · `wry` · `self-deprecating` · `observational` · `absurd` · `broad` |
| **Delivery style** (`delivery_style`) | How the words are said — the camera, the line rhythm, the pace — and the technique that way of saying them serves. | `deadpan` · `confessional` · `teacher-explainer` · `rant` · `storyteller` · `hype` · `plain-testimonial` · `deadly-sincere` · `understatement` · `interview-consult` · `reaction-duet` · `hands-and-voiceover` |
| **Register** (`register`) | The rhythm and word-weight a beat runs on — mood, made choosable. | `staccato-urgent` · `plain-flat` · `warm-unhurried` · `clinical` · `playful` · `intimate-low` |
| **Pacing** (`pacing`) | The shape of the piece in time — where it moves, where it stops, and what the shape itself says. | `fast-open-slow-body` · `escalating` · `one-breath` · `beat-and-pause` · `list-stack` |
| **Reference world** (`reference_world`) | The world the avatar's taste actually comes from: who they laugh at, who they trust, what they watch, what they quote, what their world looks like and sounds like. | `laugh-at` · `trust` · `watch` · `quote` · `look` · `sound` |
| **Avoid** (`avoid`) | What gets stripped: the register this room cringes at, and the tells that mark a piece as an ad before a claim is heard. | `cringe-register` · `ad-voice-tells` |

## Humor level (`humor`) [L3253-3872]

How funny the piece is allowed to be, and in which register the joke sits.

**Rule.** Straight is the default: a testimonial, a before/after, a founder story, a demonstration and any piece about pain, health or money stays straight unless the source itself joked. Humor is chosen from what the avatar's world already laughs at, never from the writer's taste — a joke the room does not make is a joke about the room. A straight source may take a planted joke only when it comes from the room: a meme, format or reference the culture read or the avatar's culture map shows this audience already laughs at; the receipt is named, and a joke the writer invented is still a finding. The problem may be cast as a character (the spot, the breakout, the stubborn stain) — a PERSONIFIED PROBLEM, always the villain or the fool, never the customer. Humor stays off the proof and the offer: a laugh over a claim reads as a hedge on the claim. The twist beat may be the product doing its job, shown, not claimed, and a plain beat with the proof always follows it.

**Receipt.** A research line answering RQ-17 (who they laugh at), a bank row tagged `taste`, or the humor section of the avatar's culture map (`core-avatars/<avatar>/culture-map.md`: what they watch, who they trust, their references, what they care about, what they laugh at, what is off-limits), which counts as the RQ-17 receipt until the avatar's own research replaces it. No receipt means the dial reads `none`.

_Why that pointer:_ Identification — what a room laughs at is a role it claims, and borrowing the laugh of a different room is the same error as assigning a role nobody claims.

### `none`

- **What it is:** No joke anywhere. The piece is played straight from the first frame to the last.
- **When it fits:** Any beat carrying proof, the offer or the ask; any room whose subject is pain, money, health or loss; any piece whose speaker has to be believed more than liked.
  - levels: `most-aware`, `product-aware`, `solution-aware`, `problem-aware`, `unaware`
  - sections: `proof`, `offer`, `call-to-action`, `urgency`, `objections`, `root-cause`
  - formats: `any`
- **Risk:** The opposite risk, and it is real: a straight read in a room that jokes constantly marks the speaker as an outsider before a claim is heard.
- **Receipt it needs:** The default. This is the only value that needs no receipt; every other one does.
- **Source:** craft

### `dry`

- **What it is:** A true thing said flat, with the funny part left for the viewer to find. Nothing in the delivery signals that a joke happened.
- **When it fits:** Rooms that prize being unimpressed; the beats where an annoyance is admitted rather than performed.
  - levels: `problem-aware`, `solution-aware`, `product-aware`
  - sections: `hook`, `problem`, `failed-solutions`, `agitation`, `objections`
  - formats: `single-presenter`, `micro-drama`, `demonstration`
- **Risk:** Read as cold, or as a genuine complaint, by anyone who does not share the reference the flatness depends on.
- **Receipt it needs:** A research line where the room says the thing flat, or a bank row tagged `taste` showing the register.
- **Source:** craft

### `wry`

- **What it is:** The speaker is in on it — a half-smile inside the line, an acknowledgement that the situation is ridiculous and they are still standing in it.
- **When it fits:** Long-running annoyances the room has made peace with; the turn out of a failed-solutions beat.
  - levels: `problem-aware`, `solution-aware`, `product-aware`
  - sections: `identification`, `problem`, `failed-solutions`, `transformation`
  - formats: `single-presenter`, `testimonial-montage`, `micro-drama`
- **Risk:** A half-smile over a real cost reads as not taking the viewer's problem seriously; it belongs on the speaker's own situation, never on the viewer's.
- **Receipt it needs:** A research line where the room jokes about its own situation, quoted.
- **Source:** craft

### `self-deprecating` [L5575-5661]

- **What it is:** The speaker is the target. It buys the right to make a claim afterwards, because the worst has already been admitted by the person making it.
- **When it fits:** Openings into rooms that distrust advertising voice; identification beats; any beat immediately before a hard claim.
  - levels: `problem-aware`, `solution-aware`, `unaware`
  - sections: `hook`, `identification`, `failed-solutions`, `objections`
  - formats: `single-presenter`, `testimonial-montage`, `micro-drama`, `meme`
- **Risk:** Taken past the speaker it disqualifies them as a source. The admission is about the speaker, never about whether the product does the job.
- **Receipt it needs:** A research line or bank row where the room talks about itself this way.
- **Source:** schwartz — camouflage, the understatement register

### `observational`

- **What it is:** The joke is a detail out of the room's own daily life, named precisely enough that the recognition is the laugh.
- **When it fits:** Identification and problem beats, where being seen matters more than being amused.
  - levels: `problem-aware`, `solution-aware`, `unaware`
  - sections: `hook`, `identification`, `problem`, `transformation`
  - formats: `single-presenter`, `micro-drama`, `meme`
- **Risk:** A detail from the wrong room reads as research rather than recognition, which is worse than no joke at all.
- **Receipt it needs:** A verbatim bank row carrying the detail — this value cannot be written from a summary.
- **Source:** craft

### `absurd`

- **What it is:** The premise itself is impossible and it is played completely straight.
- **When it fits:** Rooms that already know the category cold and will not sit through another straight opening.
  - levels: `most-aware`, `product-aware`
  - sections: `hook`, `identification`
  - formats: `meme`, `micro-drama`
- **Risk:** It wins the attention and loses the claim. An absurd beat needs a plain beat immediately after it, or the piece is remembered and the product is not.
- **Receipt it needs:** A research line showing this room's own absurd formats — a shape it already watches, not one invented for it.
- **Source:** craft

### `broad`

- **What it is:** The joke is loud, physical and unmissable. Nobody has to work for it.
- **When it fits:** Placements with no shared in-words to rely on; the widest reach the piece is bought for.
  - levels: `unaware`, `problem-aware`
  - sections: `hook`, `problem`, `transformation`
  - formats: `meme`, `micro-drama`, `any`
- **Risk:** It flattens the speaker's authority, so it cannot sit next to the mechanism or the proof — those beats need a different speaker or a different register.
- **Receipt it needs:** A research line showing the room shares no narrower reference, or a format profile that names the placement as broad.
- **Source:** craft

## Delivery style (`delivery_style`) [L5436-5661]

How the words are said — the camera, the line rhythm, the pace — and the technique that way of saying them serves.

**Rule.** One style per section, named. A style is how a line is said and never which words are said. A piece that changes style every beat has no speaker; a piece that never changes has no shape — the change is the event, so it happens where the argument turns.

**Receipt.** The room's own register (RQ-20), the format profile, or the delivery read of the swipe. A style chosen because it sounded good is this dial's one failure.

_Why that pointer:_ Camouflage — the gear change between the medium's own voice and advertising voice is exactly what a delivery style either hides or announces.

### `deadpan`

- **What it is:** Everything said level, with nothing in the face or the voice selling it.
- **Camera:** Locked, eye-line straight to lens, no cutaway to sell the beat.
- **Line rhythm:** Even line lengths, no lift at the end of a sentence.
- **Pace:** Steady, one beat between lines, no acceleration anywhere.
- **Technique it serves:** `camouflage`
- **When it fits:** Rooms that punish enthusiasm; any beat where the claim has to sound like a fact rather than a pitch.
  - levels: `most-aware`, `product-aware`, `solution-aware`
  - sections: `hook`, `problem`, `failed-solutions`, `objections`, `product`
  - formats: `single-presenter`, `demonstration`, `meme`
- **Risk:** A room that expects energy reads it as flat, or as a speaker who does not believe their own line.
- **Receipt it needs:** RQ-20 — the room's own register, quoted.
- **Source:** craft

### `confessional`

- **What it is:** Said as an admission, to one person, as if it had not been planned.
- **Camera:** Handheld or at arm's length, close, slightly off-axis.
- **Line rhythm:** Uneven — starts mid-thought, breaks, restarts.
- **Pace:** Slow into the admission, faster out of it.
- **Technique it serves:** `identification`
- **When it fits:** The beat where the viewer has to see themselves in the speaker before anything is claimed.
  - levels: `problem-aware`, `unaware`, `solution-aware`
  - sections: `identification`, `problem`, `failed-solutions`, `transformation`
  - formats: `single-presenter`, `testimonial-montage`
- **Risk:** It is the style most easily performed rather than meant, and a performed confession is the loudest ad tell in a piece.
- **Receipt it needs:** RQ-18 — the delivery of someone this room already believes.
- **Source:** craft

### `teacher-explainer`

- **What it is:** One idea at a time, shown while it is said, with the viewer allowed to keep up.
- **Camera:** Steady mid, hands and the object in frame, cutting to whatever is being pointed at.
- **Line rhythm:** One idea per sentence, every sentence completing.
- **Pace:** Unhurried, with a pause after each step.
- **Technique it serves:** `mechanization`
- **When it fits:** A market sophisticated enough to demand a mechanism rather than a claim.
  - levels: `solution-aware`, `product-aware`, `problem-aware`
  - sections: `root-cause`, `unique-mechanism`, `solution`, `product`
  - formats: `demonstration`, `expert-consult`, `single-presenter`
- **Risk:** It slows the piece where a scroll is cheapest; it needs an opening in a faster style to have anyone left to teach.
- **Receipt it needs:** RQ-18 or RQ-12 — who explains things to this room, and at what depth the room takes it.
- **Source:** craft

### `rant`

- **What it is:** Said at speed and at pressure, with the annoyance plainly real.
- **Camera:** Handheld and moving, the speaker walking or gesturing.
- **Line rhythm:** Run-on, clauses stacking, few full stops.
- **Pace:** Fast and building, no pause offered.
- **Technique it serves:** `concentration`
- **When it fits:** The beat where the alternatives get taken apart.
  - levels: `problem-aware`, `solution-aware`, `product-aware`
  - sections: `failed-solutions`, `agitation`, `objections`
  - formats: `single-presenter`, `micro-drama`
- **Risk:** It reads as anger at the viewer unless the target is plainly the alternative and never the person watching.
- **Receipt it needs:** RQ-13 or RQ-20 — the room's own complaint, at the room's own volume.
- **Source:** craft

### `storyteller`

- **What it is:** A thing that happened, told in order, with the turn kept until it earns its place.
- **Camera:** One setup, the speaker seated or still, cutaways to the scene being told.
- **Line rhythm:** Past tense, ordered, each sentence handing off to the next.
- **Pace:** Slow open, quickening at the turn.
- **Technique it serves:** `gradualization`
- **When it fits:** A claim the room will not accept stated, but will accept arrived at.
  - levels: `unaware`, `problem-aware`, `solution-aware`
  - sections: `problem`, `failed-solutions`, `transformation`, `proof`
  - formats: `single-presenter`, `testimonial-montage`, `micro-drama`
- **Risk:** A story with no turn is an anecdote, and an anecdote spends the piece's whole runtime on nothing.
- **Receipt it needs:** RQ-10 — the accepted fact the story can start from.
- **Source:** craft

### `hype`

- **What it is:** Everything said at volume and at speed, with the energy carrying the claim.
- **Camera:** Close, energetic, quick cuts on the beat.
- **Line rhythm:** Short stacked lines, each one a claim.
- **Pace:** Fast throughout, no pause.
- **Technique it serves:** `intensification`
- **When it fits:** A room that runs hot itself, and only where the claim is already believed.
  - levels: `most-aware`, `product-aware`
  - sections: `hook`, `solution`, `offer`, `urgency`, `call-to-action`
  - formats: `meme`, `single-presenter`, `testimonial-montage`
- **Risk:** It is the advertising voice camouflage exists to avoid. In a sceptical room it is the tell, and it is the first one heard.
- **Receipt it needs:** RQ-20 — the room itself running at this volume, quoted, or the format profile naming it.
- **Source:** craft

### `plain-testimonial`

- **What it is:** A person saying what happened to them, in their own words, with nothing tightened.
- **Camera:** Static, the speaker sitting where they actually are, one take, no grade.
- **Line rhythm:** Ordinary sentences, unpolished, self-corrections kept in.
- **Pace:** The speaker's own — never edited to be tighter than they were.
- **Technique it serves:** `camouflage`
- **When it fits:** The proof beat, and any room whose scepticism is aimed at production value itself.
  - levels: `solution-aware`, `product-aware`, `most-aware`
  - sections: `proof`, `transformation`, `objections`, `product`
  - formats: `testimonial-montage`, `single-presenter`
- **Risk:** Polished, it becomes the thing it is imitating and loses the only advantage it had.
- **Receipt it needs:** The rights entry for the speaker, plus RQ-16 — the proof that is actually verifiable.
- **Source:** craft

### `deadly-sincere` [L5575-5661]

- **What it is:** A real limitation admitted openly and without softening, so the claim that follows lands harder.
- **Camera:** Locked, no cutaway, nothing to hide behind.
- **Line rhythm:** Short declaratives, no qualifiers.
- **Pace:** Slow, with the pause left standing after the admission.
- **Technique it serves:** `camouflage`
- **When it fits:** A market that has heard every claim in the category and believes none of them.
  - levels: `product-aware`, `most-aware`, `solution-aware`
  - sections: `objections`, `proof`, `product`, `offer`
  - formats: `single-presenter`, `expert-consult`, `demonstration`
- **Risk:** The admission has to be real and material. A decorative flaw is read instantly and costs the whole piece, not just the beat.
- **Receipt it needs:** RQ-11 — the objection in the room's own wording, and the limitation the product genuinely has.
- **Source:** schwartz — camouflage, deadly sincerity

### `understatement` [L5575-5661]

- **What it is:** Plain, short, adjective-light — the claim stated smaller than it is and then left alone.
- **Camera:** Wide enough that nothing is being pushed at the viewer.
- **Line rhythm:** Short sentences, few adjectives, no superlative anywhere.
- **Pace:** Even, no build.
- **Technique it serves:** `camouflage`
- **When it fits:** Any room where the size of a claim is itself the reason it is disbelieved.
  - levels: `product-aware`, `most-aware`, `solution-aware`
  - sections: `product`, `proof`, `solution`, `offer`
  - formats: `single-presenter`, `demonstration`, `expert-consult`
- **Risk:** Against a stage-4 or stage-5 market it can read as no claim at all; it needs one hard specific for the viewer to hold on to.
- **Receipt it needs:** RQ-14 — what the organic content in this placement actually sounds like.
- **Source:** schwartz — camouflage, understatement

### `interview-consult`

- **What it is:** A question the room actually asks, asked out loud, and answered at length.
- **Camera:** Two-shot or over-shoulder, the question audible.
- **Line rhythm:** Question, then answer, with the answer allowed to run.
- **Pace:** Conversational; interruptions and overlaps kept.
- **Technique it serves:** `mechanization`
- **When it fits:** Where the mechanism needs an authority and the authority needs someone to speak to.
  - levels: `solution-aware`, `product-aware`, `problem-aware`
  - sections: `root-cause`, `unique-mechanism`, `proof`, `objections`
  - formats: `expert-consult`, `demonstration`
- **Risk:** A scripted question reads as a scripted answer. The question has to be one the room asks, in the room's words.
- **Receipt it needs:** RQ-07 or RQ-11 — the unresolved objection, verbatim, plus the rights entry for anyone on camera.
- **Source:** craft

### `reaction-duet`

- **What it is:** The reaction is on screen beside the thing being reacted to — a second frame, a second voice.
- **Camera:** Split or picture-in-picture, the reactor smaller and off-centre.
- **Line rhythm:** The source runs; the reaction interrupts it.
- **Pace:** The source's pace, punctuated.
- **Technique it serves:** `camouflage`
- **When it fits:** Where the room's own native format is commentary rather than address.
  - levels: `most-aware`, `product-aware`, `solution-aware`
  - sections: `hook`, `objections`, `proof`, `failed-solutions`
  - formats: `meme`, `single-presenter`
- **Risk:** It borrows the source's credibility, so the source's rights AND the source's own claim both have to hold — a reaction to a false claim inherits the claim.
- **Receipt it needs:** RQ-14 — the format observed in this placement — and the rights entry for the source.
- **Source:** craft

### `hands-and-voiceover`

- **What it is:** No face. Hands doing the thing, a voice over the top of it.
- **Camera:** Top-down or close over the hands, the object always the subject.
- **Line rhythm:** Narration tracking the action, never running ahead of it.
- **Pace:** The action's own pace.
- **Technique it serves:** `mechanization`
- **When it fits:** Where the thing itself is more persuasive than anyone describing it, and where no cast face is cleared.
  - levels: `solution-aware`, `product-aware`, `most-aware`
  - sections: `unique-mechanism`, `product`, `solution`, `proof`
  - formats: `demonstration`, `any`
- **Risk:** With no face there is nobody to identify with; the piece needs an identification beat somewhere else or it persuades nobody in particular.
- **Receipt it needs:** RQ-12 — whether the mechanism can be shown at all, and at what depth.
- **Source:** craft

## Register (`register`) [L6260-6361]

The rhythm and word-weight a beat runs on — mood, made choosable.

**Rule.** The register is chosen against the swipe, not inherited by accident: either match its rhythm or diverge from it on purpose, and say which. If the viewer consciously notices the register, it has failed and the beat gets rewritten.

**Receipt.** RQ-15 (the swipe's own rhythm) or RQ-20 (the room's own register). A register with neither is the writer's ear, not the room's.

_Why that pointer:_ Mood — rhythm carries feeling independently of content, and the mechanism has to stay invisible.

### `staccato-urgent` [L6260-6361]

- **What it is:** Short lines, hard stops, stacking. The rhythm itself says hurry.
- **When it fits:** The opening seconds and the close; anywhere the cost of waiting is the argument.
  - levels: `most-aware`, `product-aware`, `problem-aware`
  - sections: `hook`, `agitation`, `urgency`, `offer`, `call-to-action`
  - formats: `meme`, `single-presenter`, `testimonial-montage`
- **Risk:** Held across a whole piece it stops meaning urgency and starts meaning advertisement.
- **Receipt it needs:** RQ-15 or RQ-20, quoted.
- **Source:** schwartz — mood

### `plain-flat` [L6260-6361]

- **What it is:** Ordinary sentence length, no lift, no adjective doing work the fact should do.
- **When it fits:** Where the claim has to carry itself — the mechanism, the proof, the product.
  - levels: `solution-aware`, `product-aware`, `most-aware`
  - sections: `product`, `proof`, `unique-mechanism`, `root-cause`
  - formats: `demonstration`, `single-presenter`, `expert-consult`
- **Risk:** In a room that runs hot it reads as disinterest rather than confidence.
- **Receipt it needs:** RQ-15 or RQ-20, quoted.
- **Source:** schwartz — mood

### `warm-unhurried` [L6260-6361]

- **What it is:** Longer sentences, soft landings, room left standing after each thought.
- **When it fits:** Identification and transformation beats, where the viewer has to feel unhurried to feel seen.
  - levels: `unaware`, `problem-aware`, `solution-aware`
  - sections: `identification`, `transformation`, `solution`, `problem`
  - formats: `single-presenter`, `testimonial-montage`, `micro-drama`
- **Risk:** It drains urgency out of a close; it cannot be the register the ask is made in.
- **Receipt it needs:** RQ-15 or RQ-20, quoted.
- **Source:** schwartz — mood

### `clinical` [L6260-6361]

- **What it is:** Precise, quantified, no colour. It sounds like a measurement, because it is one.
- **When it fits:** Proof and mechanism beats in a market that has stopped believing adjectives.
  - levels: `solution-aware`, `product-aware`, `most-aware`
  - sections: `proof`, `unique-mechanism`, `root-cause`, `objections`
  - formats: `expert-consult`, `demonstration`
- **Risk:** It distances. The beat before it or after it has to be human, or the piece reads as a datasheet nobody asked for.
- **Receipt it needs:** RQ-16 — the proof that is independently verifiable, with its source.
- **Source:** schwartz — mood

### `playful` [L6260-6361]

- **What it is:** Light, quick, the speaker plainly enjoying themselves.
- **When it fits:** Hooks and identification beats in rooms that enjoy their own subject.
  - levels: `most-aware`, `product-aware`, `problem-aware`
  - sections: `hook`, `identification`, `transformation`
  - formats: `meme`, `single-presenter`, `micro-drama`
- **Risk:** It cannot carry a proof or an offer beat — enjoyment sitting over a claim reads as a hedge on the claim.
- **Receipt it needs:** RQ-17 or RQ-20, quoted.
- **Source:** schwartz — mood

### `intimate-low` [L6260-6361]

- **What it is:** Quiet, close, said as though to one person who is already listening.
- **When it fits:** The admission, the objection answered honestly, the moment the piece stops addressing a market.
  - levels: `problem-aware`, `solution-aware`, `unaware`
  - sections: `identification`, `problem`, `objections`, `transformation`
  - formats: `single-presenter`, `testimonial-montage`
- **Risk:** It is the register most easily faked, and a faked one is louder than any claim in the piece.
- **Receipt it needs:** RQ-18 or RQ-20, quoted.
- **Source:** schwartz — mood

## Pacing (`pacing`) [L6260-6361]

The shape of the piece in time — where it moves, where it stops, and what the shape itself says.

**Rule.** Pacing is a shape across the whole piece, not a setting on one beat: it is named once and the sections are cut to it. It is never written as a number of seconds anywhere.

**Receipt.** The format profile, or RQ-14 — how the organic content in this placement is actually cut.

_Why that pointer:_ Mood — rhythm carries the feeling, and a piece's rhythm across time is the largest rhythm it has.

### `fast-open-slow-body`

- **What it is:** The first beats move hard, then the piece slows down where the thinking has to happen.
- **When it fits:** A mechanism or a proof that needs room, in a placement that gives nothing away for free.
  - levels: `problem-aware`, `solution-aware`, `product-aware`
  - sections: `hook`, `root-cause`, `unique-mechanism`, `proof`
  - formats: `demonstration`, `expert-consult`, `single-presenter`
- **Risk:** The slow half loses everyone the fast half attracted for the wrong reason; the open has to promise the thing the body delivers.
- **Receipt it needs:** The format profile, or RQ-14.
- **Source:** craft

### `escalating`

- **What it is:** Each beat shorter and closer than the one before, all the way to the close.
- **When it fits:** Agitation into the offer, where the pressure is the argument.
  - levels: `problem-aware`, `product-aware`, `most-aware`
  - sections: `problem`, `agitation`, `solution`, `offer`, `urgency`, `call-to-action`
  - formats: `single-presenter`, `testimonial-montage`, `meme`
- **Risk:** An escalation that never releases is exhausting; it needs one flat beat immediately before the ask or the ask is not heard.
- **Receipt it needs:** RQ-15 — the swipe's own build, or the format profile.
- **Source:** craft

### `one-breath`

- **What it is:** The whole piece delivered as a single unbroken run — no cut, no pause, nowhere to get off.
- **When it fits:** Short pieces whose whole appeal is that nothing was edited.
  - levels: `most-aware`, `product-aware`, `problem-aware`
  - sections: `hook`, `problem`, `identification`, `offer`
  - formats: `single-presenter`, `meme`
- **Risk:** Nothing can be repaired in the edit — one fluffed line costs the take, and the take is the piece.
- **Receipt it needs:** RQ-14, or the format profile naming the uncut read.
- **Source:** craft

### `beat-and-pause`

- **What it is:** A line, then a held silence long enough to be uncomfortable, then the next line.
- **When it fits:** Deadpan and deadly-sincere reads, where the silence is what makes the line land.
  - levels: `product-aware`, `most-aware`, `solution-aware`
  - sections: `hook`, `objections`, `proof`, `product`
  - formats: `single-presenter`, `demonstration`, `micro-drama`
- **Risk:** A pause with nothing happening in frame is dead air. The pause needs a look, a hand, a change — something for the silence to sit on.
- **Receipt it needs:** RQ-15 or RQ-20 — the room's own timing.
- **Source:** craft

### `list-stack`

- **What it is:** Items delivered in a run, the same shape each time, the repetition doing the work.
- **When it fits:** Failed solutions, proof and the offer, where quantity is itself the argument.
  - levels: `solution-aware`, `product-aware`, `most-aware`
  - sections: `failed-solutions`, `proof`, `offer`, `objections`
  - formats: `testimonial-montage`, `single-presenter`, `demonstration`
- **Risk:** The stack has to be real items. An invented fourth added to complete the rhythm is the failure this value causes, and it is invisible until someone checks.
- **Receipt it needs:** One receipt per item in the stack — this value cannot be half-receipted.
- **Source:** craft

## Reference world (`reference_world`) [L3253-3872]

The world the avatar's taste actually comes from: who they laugh at, who they trust, what they watch, what they quote, what their world looks like and sounds like.

**Rule.** Every slot is filled ONLY from research about this avatar. A slot the research did not answer is `[UNFILLED]` and the direction it would have supported is left out — never filled from general culture, and never from the writer's own shelf. A reference is a direction for timing, cadence and world; it is never a likeness and never a voice. The voice is always a cast voice, cloned and then adjusted, with rights on file.

**Receipt.** A research line answering RQ-17 to RQ-19, or a bank row tagged `taste`, `subculture` or `in-word`. A name with no receipt is the writer's taste wearing a receipt's clothes.

_Why that pointer:_ Identification — the roles a market already claims, and the figures it claims them alongside.

### `laugh-at`

- **What it is:** The comedians, creators and formats this room actually laughs at.
- **When it fits:** Read for TIMING and CADENCE — where the beat sits, how long the pause runs, how the joke is set up. Used to set the humor dial, never to write a line.
  - levels: `most-aware`, `product-aware`, `solution-aware`, `problem-aware`, `unaware`
  - sections: `hook`, `identification`, `problem`, `transformation`
  - formats: `any`
- **Risk:** A name pulled from general culture rather than from this room's own is the writer's taste with a receipt stapled to it.
- **Receipt it needs:** RQ-17, quoted with its source, or a bank row tagged `taste`.
- **Source:** craft

### `trust` [L3253-3872]

- **What it is:** The creators, experts and peers this room believes when it believes anyone.
- **When it fits:** Read for the SHAPE of trusted delivery — how they open, whether they hedge, whether they show or tell. Used to set the delivery style.
  - levels: `solution-aware`, `product-aware`, `problem-aware`, `most-aware`
  - sections: `proof`, `unique-mechanism`, `objections`, `identification`
  - formats: `expert-consult`, `testimonial-montage`, `single-presenter`
- **Risk:** Trust does not transfer by imitation. Copying a trusted person's manner without their evidence produces a counterfeit, and a counterfeit is caught by exactly the people whose trust was the point.
- **Receipt it needs:** RQ-18, quoted with its source, or a bank row tagged `trust-language` or `community-voice`.
- **Source:** schwartz — identification

### `watch` [L5474-5542]

- **What it is:** The shows, channels and content formats this room watches without being sold to.
- **When it fits:** Read for FORMAT — the host medium the piece has to stop looking like an ad inside.
  - levels: `most-aware`, `product-aware`, `solution-aware`, `problem-aware`, `unaware`
  - sections: `hook`, `problem`, `proof`, `product`
  - formats: `any`
- **Risk:** A format named from the platform in general rather than this room in particular camouflages the piece into a medium the avatar is not in.
- **Receipt it needs:** RQ-19, or RQ-14's observation of the placement.
- **Source:** schwartz — camouflage, match the host medium

### `quote` [L5544-5574]

- **What it is:** The lines, catchphrases and running jokes this room repeats to each other.
- **When it fits:** Read for register and in-words — what the room sounds like when it is talking to itself.
  - levels: `most-aware`, `product-aware`, `solution-aware`, `problem-aware`
  - sections: `hook`, `identification`, `objections`, `transformation`
  - formats: `meme`, `single-presenter`, `micro-drama`
- **Risk:** A borrowed line sitting under a claim reads as a borrowed claim. These are never lifted verbatim into the sell; they set the register and stop there.
- **Receipt it needs:** A verbatim bank row tagged `in-word` or `subculture`, or RQ-19.
- **Source:** schwartz — camouflage, adopt the host medium's phraseology

### `look`

- **What it is:** The visual world: wardrobe, setting, the objects around, the actual state of the room.
- **When it fits:** Read for WHAT IS IN FRAME — styling, location, props.
  - levels: `most-aware`, `product-aware`, `solution-aware`, `problem-aware`, `unaware`
  - sections: `hook`, `identification`, `problem`, `transformation`, `product`
  - formats: `any`
- **Risk:** A styled version of the room is more alien to it than a plain one. Tidied, lit and colour-matched is a different room.
- **Receipt it needs:** RQ-19, or a bank row tagged `subculture`.
- **Source:** craft

### `sound`

- **What it is:** The sound world: what is playing, what the room sounds like, what a person there would have on in the background.
- **When it fits:** Read for the bed, the room tone and what the piece must NOT sound like.
  - levels: `most-aware`, `product-aware`, `solution-aware`, `problem-aware`, `unaware`
  - sections: `hook`, `identification`, `transformation`, `urgency`
  - formats: `any`
- **Risk:** Music chosen for the piece rather than for the room says 'advertisement' before a single word is heard, and no line recovers it.
- **Receipt it needs:** RQ-19, or RQ-14's observation of the placement.
- **Source:** craft

## Avoid (`avoid`) [L5436-5661]

What gets stripped: the register this room cringes at, and the tells that mark a piece as an ad before a claim is heard.

**Rule.** Both rows are STRIPPED, never softened. And an avoid item is only an avoid item when the room named it or the placement showed it — otherwise it is the writer's taste again, this time wearing a ban.

**Receipt.** RQ-21 (what makes them cringe), a bank row tagged `cringe`, or RQ-14's observation of what organic content in this placement does not do.

_Why that pointer:_ Camouflage — the gear change between editorial voice and advertising voice is exactly what these two rows name.

### `cringe-register`

- **What it is:** The register this room mocks, named by the room, in the room's own words.
- **When it fits:** Every section, every level. It is checked against the chosen register and delivery style before anything is written.
  - levels: `most-aware`, `product-aware`, `solution-aware`, `problem-aware`, `unaware`
  - sections: `hook`, `problem`, `failed-solutions`, `root-cause`, `unique-mechanism`, `solution`, `product`, `offer`, `call-to-action`, `identification`, `agitation`, `proof`, `transformation`, `objections`, `urgency`
  - formats: `any`
- **Risk:** Banning a register the room never named removes a tool for nothing, and the ban outlives the session that invented it.
- **Receipt it needs:** RQ-21, quoted with its source, or a bank row tagged `cringe`.
- **Source:** craft

### `ad-voice-tells` [L5436-5661]

- **What it is:** The tells that mark a piece as an ad before a claim is heard: the announcer lift at the end of a line, stacked superlatives, the too-clean read, the sell turn in the first seconds, the smile held past the end of the sentence, the grade that matches no room anyone lives in.
- **When it fits:** Every piece, and hardest wherever the room's scepticism toward advertising is the main barrier.
  - levels: `most-aware`, `product-aware`, `solution-aware`, `problem-aware`, `unaware`
  - sections: `hook`, `problem`, `product`, `proof`, `offer`, `call-to-action`
  - formats: `any`
- **Risk:** Stripping every tell can strip the claim with it. The piece still has to say the thing — just not in that voice.
- **Receipt it needs:** RQ-14 — what genuinely top-performing organic content in this placement sounds like, observed rather than assumed.
- **Source:** schwartz — camouflage
