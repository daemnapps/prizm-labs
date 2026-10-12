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

Target **2:30–3:15**. Every line moves the story; no filler line, no repeated verse.

## Flow is written, then measured

- **Rhyme and pocket:** end rhymes on every couplet, internal rhymes in rap verses,
  lines of similar length inside a section so the singer never stretches or rushes.
- **Sections are sized from their lines, never padded.** Leave `seconds` out or write
  `"fit"`: `song.py` gives each section `lines × beats_per_line + 1` beats at the row's
  tempo (a rapped line ≈ one bar; a sung ballad line ≈ 1½ bars — the style row's
  `beats_per_line`). A number written by hand is the exception and must be justified.
- **Every take is listened to** (`song.py flow()`, after the line check): the first
  word inside 1 s, no gap over 2 s between words (the last 4 s excepted), dead air
  under 5 % of the song. A take that fails is remade once with every section 15 %
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
