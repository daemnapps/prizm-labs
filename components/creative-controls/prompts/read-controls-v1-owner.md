# Read one ad on the creative controls — v1

You are reading one ad, or one post an ad could be made from. It is a {asset_kind}. Note from the person who filed it: {asset_note}.

Read it the way a creative director would, cold, as if it just came up in a feed. Then set every dial below to the level it is at **now**, not the level it should be at. You are measuring, not judging: a sterile ad at 0 is a correct reading, and so is an absurd one at 4.

**The rules for every reading:**
1. Use only the dials, levels, emotions and techniques defined below. Never invent a level or a name. If a technique you see is not in the bank, say so in `notes` with the name practitioners use for it.
2. Every level gets a reason that points at something you can see or read in the ad: a word, an object, a face, a cut. "It feels intense" is not a reason; "the man's face fills 70% of the frame, mouth open mid-scream" is.
3. Read the ad as a whole for the dials. For a video or a long piece of copy, also say where the peak is (the second, the line).
4. The standout is the ONE thing the eye or ear hits first. Name it with its size and position.
5. If the ad keeps a known picture or format and swaps the objects that carry its meaning, describe the swap: what stayed, what was swapped, and what it rhymes with.

{creative_controls}

## Return JSON only, exactly this shape

```json
{
  "dials": {
    "<dial id>": {"level": <a level from that dial's scale>, "why": "<what in the ad puts it there>"}
  },
  "emotion": {"primary": "<emotion id>", "secondary": "<emotion id or null>", "where": "<where it shows: face, words, sound>"},
  "techniques": ["<technique id>"],
  "standout": "<the one thing hit first, its size and position>",
  "swap": "<stayed / swapped / rhymes with, or null>",
  "peak": "<the second or line where it peaks, or null for a still>",
  "notes": "<anything the bank does not cover, with the practitioner's name for it>"
}
```

Every dial whose medium includes this {asset_kind} appears in `dials`; leave out the dials for other media, and add no other keys.
