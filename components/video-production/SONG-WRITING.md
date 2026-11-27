# Writing a song ad — the songwriter's rules

the owner, 2026-10-10, after the first eight song ads: *"the opening line needs to start
with the punch as always … these songs need to be shorter … there's awkward space in
the song … I don't think you're actually listening to the track at all … the songs
need to flow. That's what keeps people captivated … think as if we're a professional
songwriter that's using these dramatic stories to create the response ads."*

Measured on those songs: 35–90 s of dead air each, single gaps up to 22 s, two that
sang their first word 12 s in, every one 5½–6 minutes. The edit then filled the
silence with B-roll that had nothing to follow.

## The shape (a song first, an ad inside it)

| part | what it does | length |
|---|---|---|
| **The punch** | the story's most shocking line, sung in the first second — no intro, no humming, no beat-only bar | 1–2 lines |
| **Verse 1** | the setup to the first twist, every line a specific (who, where, how long, what it cost) | 8 lines |
| **Hook** | the line people repeat; short, sung, the same every time | 4 lines |
| **Verse 2** | the shock scene | 6–8 lines |
| **Hook** | | 4 lines |
| **Bridge** | the mirror (the brand's problem, hidden for years) + the sibling hands over the product — the product line said plainly, once | 4–6 lines |
| **Verse 3** | the weeks of change, then the payoff/revenge with a cold last line | 6–8 lines |
| **Outro** | the hook, then "<product> by <brand>. Link below." | 2–3 lines |

Target **as long as the full story needs, ≈3:00–3:30** (see The balance). **Not rushed** (the owner, on the first tight take at 1:44: "too fast") — a rapped line gets about 1½ bars (`beats_per_line` 6), a sung ballad line 2 bars (8); tight means no long empty stretches, never crammed. **It must sound like a song** (the owner: "it needs to actually sound like a song, just efficient"): a melody you could hum, a hook sung on a melody, fewer syllables per line so it can be sung, rhythm that varies between verse and hook, and a short musical break (a beat drop, a held note) between sections is part of the song. Every line moves the story; no filler line, no repeated verse.

## The balance (the owner, 2026-10-10, after hearing v1 → v4)

*"The version one was still the best. There was just a little bit too much space in
between … the lines … so you could never really get into a flow. Now these new ones
have way better flow, but the story plot line doesn't make sense fully … there's a
fine balance between the two."*

- **The story is never cut to make time.** Every plot beat of the swipe's story stays,
  in order, with its specifics — length follows the story (≈3:00–3:30 for a full
  Resilia-style plot), it is not a target to squeeze to.
- **Flow comes from the engine, not from deleting lines:** sections fit to their lines
  (`"fit"`, rap 6 beats/line, ballad 8), first word ≤ 1 s, no gap over 3.5 s, dead air
  ≤ 10 %. Tighten syllables inside a line so it sings; never drop the line.
- Start from the full-story lyric (v1) and make it singable; don't start from a short
  draft and hope the story survives.

## Flow is written, then measured

- **Rhyme and pocket:** end rhymes on every couplet, internal rhymes in rap verses,
  lines of similar length inside a section so the singer never stretches or rushes.
- **Sections are sized from their lines, never padded.** Leave `seconds` out or write
  `"fit"`: `song.py` gives each section `lines × beats_per_line + 1` beats at the row's
  tempo (a rapped line ≈ 1½ bars; a sung ballad line ≈ 2 bars — the style row's
  `beats_per_line`). A number written by hand is the exception and must be justified.
- **Every take is listened to** (`song.py flow()`, after the line check): the first
  word inside 1 s, no gap over 3.5 s between words (a short musical break between
  sections is allowed; the last 4 s excepted), dead air under 10 % of the song. A take that fails is remade once with every section 15 %
  tighter; still failing, it stops and names the gap. Thresholds:
  `providers.json gates.song_flow` (defaults in `song.py FLOW_DEFAULTS`).
- **The edit follows the song:** with no gaps there is no "awkward B-roll" — every
  shot sits under a sung line.

## How to make one

    python3 machine/song.py runs/video-production/<brand>/<label> --spec <song-spec.json>

The spec is the song: `title, brand, style_id, vocal, bpm, sections: [{name, lines,
style?}]` (section names: intro · verse · pre-chorus · chorus · hook · bridge · outro,
numbered freely — "verse 2"). Brand words and figures are swapped for how they are
said (`lexicon.for_model`). Artist names are refused by the music model — describe the
sound in the style row, never name the artist.
