# Sounds — tag v1

You are tagging TikTok sounds that are trending RIGHT NOW, so an editor can
pick one for an organic post by feel. These are organic posts, not ads.

The rule from the owner (2026-09-23): only sounds that are recent. Classic meme
sounds — vine boom, bruh, oh no no no, sad violin, metal pipe, emotional
damage, the Wii theme, Curb Your Enthusiasm, "directed by Robert B. Weide",
Among Us, any sound that has been a meme for a year or more — are OUT, even
if they show up on a chart. Mark them `classic_meme: true`.

For each sound below, give back:

- `kind`: `song` (a released track), `original` (someone's own audio: a voice,
  a skit line, a remix a creator made), or `meme` (a sound that is used as a
  joke punchline rather than a bed)
- `classic_meme`: true only for the old, worn-out meme sounds described above
- `mood`: ONE word — pick from: hype, happy, warm, calm, sad, moody, tense,
  funny, romantic, nostalgic, confident, eerie
- `energy`: `low`, `mid` or `high`
- `category`: ONE of: pop, hip-hop, r&b, edm, latin, country, rock, afro,
  k-pop, lo-fi, cinematic, speech, remix, other
- `use`: one short line (under 14 words) — what kind of post this sound gets
  put under on TikTok right now
- `why`: one short line — what you based the tags on (the title, the artist,
  what you know of the track). If you do not know the sound, say so and tag
  from the title only; do not invent facts about it.

Answer with JSON only, a list in the same order as the input:
`[{"id": "...", "kind": "...", "classic_meme": false, "mood": "...", "energy": "...", "category": "...", "use": "...", "why": "..."}]`

The sounds:

{sounds}
