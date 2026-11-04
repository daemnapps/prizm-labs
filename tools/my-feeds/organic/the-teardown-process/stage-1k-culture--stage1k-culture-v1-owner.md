*v1 (2026-10-05, the owner, after two organic swipes went viral on pop culture the machine never saw — the teardown named a famous film character "a player in a suit", so the brief, and the viewers in the viewer check, read the clip as AI junk): "The more we're aware of culture, what people watch, why they watch it, why they like it, and why they think it's funny or interesting or engaging, the easier all of this is. We can literally just leverage that authority." This read runs after the teardown record and before the doctrine read, on every swipe, for any brand and any kind of creative.*

**Every example in this prompt is illustrative.** Examples show the shape of an answer, never its content: no name, film, song, meme or audience below is a hint about the video in front of you. Work only from the video, the record and the post's own words.

Here is the teardown record of the video — the shot table, the cast, the sound, and at its end the verbatim transcript: {teardown_record}

Here is the post's own talk — its caption, its numbers and the comments the platform returned, numbered C1, C2 … so you can cite them: {post_talk}

The video itself is attached. Watch all of it, and listen to it.

## THE CULTURE READ

The teardown record says what is on screen. This pass says **what the people watching it recognize** — the film, show, song, sound, character, performer, catchphrase, meme, format or moment the video borrows — and **why that recognition is the reason it travels.** A clip of a stranger in a suit is nothing. The same clip, when a million viewers see a character they grew up quoting, is a hit. A record that misses the reference hands every later stage the wrong video.

**You are reading THEIR asset, not ours.** Nothing here is about a brand, a product or what we will make. Never name a brand that is not on screen in the source, and never suggest how to sell anything.

### How to find the references

1. **Read the comments first.** Viewers name what they recognize: they say a character's name (often misspelled), quote the character's line back, tag a friend with the catchphrase, or argue about it. A comment quoting a line nobody in the video says is a strong signal that the line is famous from somewhere else — find where.
2. **Then the screen and the sound.** The look (a costume, a hairstyle, a silhouette, a signature prop), the setting, an era's details, a song or sound, a line spoken in the video, words on screen.
3. **Then search — for every reference you name.** You have Google Search. Run at least one search for each reference before you name it: the quoted line, the misspelled name, the look plus the situation, the lyric. Use it to confirm, never to invent: the work, the year, the performer, and the scene, line or recording the video borrows. The machine files the searches you actually ran under your read, so a search receipt is only as good as a search that is listed there. If you cannot search, write `SEARCH: not available` and lower every confidence that depended on it.
4. **Weigh disagreement.** Comments can be wrong (a viewer names the wrong character, the wrong film). Count who says what, prefer the specific over the vague, and print the disagreement — never pick silently.
5. **AI-made likenesses count.** A generated clip of a known character is still that character to the viewer. Say whether the reference is the real footage, a performer, an impersonation, a costume, or a generated likeness.
6. **Format and comment-room culture counts too.** A trend format (a "what if" clip, a duet or reaction format, a known audio), a running argument the comments keep having (a rules call, a "who would win"), an in-joke the room keeps repeating — these are culture the video trades on, even with no famous person in it.

### The receipt rule

**Never write a name without a receipt.** A receipt is one of:

- a comment that names it or quotes it — print it verbatim with its number and its likes (`C7 · @handle · likes: 1,204 · "…"`; write `likes: n/a` when the platform gave none);
- something on screen or in the audio that names it or matches it point by point — with the time (`0:03.2 — …`);
- a search result that confirms the specific match — the search you ran, the page title and what it confirmed. A page proving the reference exists is not a receipt that THIS video uses it.

A resemblance with no receipt is not a name. A match you made yourself — "this sounds like that famous clip" — is a resemblance until a comment, the screen or a search ties it to this video. Write it as `UNIDENTIFIED` with what you see and what would settle it. A wrong name is worse than no name: every later stage will build on it.

**Confidence**, one word per reference:
- `CONFIRMED` — named in the comments or on screen AND matched by what is on screen or by a search.
- `LIKELY` — one strong receipt that ties this video to the reference, nothing against it.
- `POSSIBLE` — a resemblance, or a match only you made, plus at most a weak receipt; say what is missing. A POSSIBLE reference never goes on a KEEP or NAME IT AS line.
- `UNIDENTIFIED` — something clearly borrowed that you cannot name with a receipt.

### Print exactly this

First line, alone: `CULTURE LOAD: HEAVY` (the video's pull rests on a reference) · `CULTURE LOAD: LIGHT` (references present, not what carries it) · `CULTURE LOAD: NONE` (nothing borrowed you can find — say what you checked).

Second line: `POST TALK: <how many comments you read, of how many on the post> · <the one thing the comment room keeps saying, in a few words>` — or `POST TALK: none — <why>` when there was nothing to read.

Then one block per reference, most load-bearing first, numbered R1, R2 …:

```
### R<n> — <who or what, as the audience would say it> · <the work it comes from> (<year>)
- KIND: <character · performer · film · show · song · sound · meme · format · catchphrase · moment · trend · comment-room bit>
- WHO, PRECISELY: <character name> played by <performer> in <work> (<year>) — or "not a person"
- WHAT IS BORROWED: <the scene, the look, the line, the move — exactly which part of the original this video uses, and how it shows here>
- RECEIPTS:
  - <C-number · @handle · likes · "verbatim comment">
  - <time — what is on screen or in the audio that matches>
  - <search: page title — what it confirmed>
- CONFIDENCE: <CONFIRMED · LIKELY · POSSIBLE · UNIDENTIFIED> — <one line why>
- WHO RECOGNIZES IT: <which audience or generation, and from where they know it (the original release, reruns, quotes passed around online, a meme cycle). Mark what is your reasoning rather than a receipt.>
- WHY IT LANDS: <the mechanism(s), named — nostalgia x a new situation · incongruity (the character dropped somewhere they never were) · competence reveal (the one you'd expect to fail is great at it) · insider recognition (you had to have seen it) · a quotable line the room repeats · an argument the room keeps having · other: name it — then one or two sentences on how it works in THIS video>
- LOAD-BEARING (keep these or the reference stops landing): <the specific elements: the look in detail, the manner, the line, the setting, the pairing, the timing of the reveal>
- BREAKS IT: <what would kill the recognition — a generic stand-in, the wrong era, losing the signature item, explaining the joke>
```

Example of the shape only (illustrative — not a hint): `### R1 — <the coach everyone quotes> · <a sports comedy> (<year>)` … `RECEIPTS: C3 · @someone · likes: 812 · "<his famous line, misspelled>"` … `CONFIDENCE: CONFIRMED — the room says his line and the costume matches the film's poster`.

Then:

```
### UNIDENTIFIED
<anything clearly borrowed you could not name: what you see, the times, and what would settle it — or "none">

### WHAT THE TEARDOWN RECORD CALLED THEM
<for each person or element the record named generically ("a player in a suit", "an AI character"), the record's label → who the audience sees, with the R-number. The record is not edited; this is the correction every later stage reads. Only references with a receipt appear here; never coin a new label for anything else.>

### THE BORROWED AUTHORITY
<two to four sentences, in brand-free terms: what goodwill, credibility or attention the video borrows from the references — what the viewer already feels about them before the video says anything — and what that buys the video in the first seconds (the stop, the trust, the laugh, the share).>

### FOR EVERY LATER STAGE
- KEEP: <one line per load-bearing reference element a remake must carry for the reference to land>
- NEVER: <one line per thing that would break it>
- NAME IT AS: <the words a writer should use for each person or element, e.g. "<character> (<work>)", instead of the record's generic label>
```

If `CULTURE LOAD: NONE`, print the first two lines, `### UNIDENTIFIED`, and `### FOR EVERY LATER STAGE` with `KEEP: nothing cultural — the video stands on its own`, and stop.

Plain words, no hedging filler, no marketing. Every name carries its receipt.
