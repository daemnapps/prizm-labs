# The handoff — a cut-ready set, and the edit

The scenes arrive with dialogue locked, wardrobe consistent and sound
already on every beat, because the director's cut and the prompt structure
did that work upstream. **So the edit's job is pace and shape, not
rescue.** If you find yourself editing to hide a generation problem, the
fix belongs upstream — except continuity, which is often cheaper to fix at
the cut than to regenerate.

---

## The philosophy — six rules the finals obey

1. **Kill the air.** Long beats, movement without dialogue and reaction
   chases get trimmed. Every second before the offer either advances the
   dialogue or sells the emotion.
2. **Hyper-compress the setup.** Shot length through setup and
   confrontation averages about **1.5 seconds** — that is the pacing the
   format's audience is trained on, and it is what keeps the skip rate
   down.
3. **Cut movement, keep spatial intent.** The walk-in, the advance, the
   handoff — trim them to their endpoints. Don't show the walk; show the
   arrival.
4. **Audio leads the cut.** Start the next line over the tail of the
   previous shot, then cut to the speaker. The film feels continuous and
   breathless instead of assembled.
5. **Every beat keeps its speaker.** The source already puts the camera on
   whoever is talking; the edit must not break that.
6. **The offer is a block, not a beat.** The final direct address runs
   longer, with the ambience lowered and the voice dominant.

## The decision list

Map source to final before you cut anything. One row per final segment:

| Final segment | Source | Action |
|---|---|---|
| Cold open | alternate intro, or scene 1's opener | Keep ~1.3s; start the first line over it |
| The catch | scene 1 | Start on the reveal; trim to the frozen moment |
| Confrontation volley | scenes 1–2 | Intercut close-ups — keep only the lines, cut the reaction tails, ~1.5s a shot |
| The block | scene 2 | Keep the entrance and the stop; trim the approach |
| The reveal | scene 3 | Keep the full explanation, camera holding the speaker; trim the exit tail |
| The admission | scene 3 | Keep the reaction — this is where the emotion is |
| The heritage beat | scene 3–4 | Keep it whole; let the music turn warm |
| **The proof** | scene 4 | The payoff. Keep it readable. **Do not over-trim.** |
| The truce | scenes 4–5 | Quick, settling |
| **The offer** | scene 5 | Slower, ambience down, caption reinforced |

**Trim rules:** remove walking and approach footage, reaction holds
without dialogue, breathing pauses over half a second, and duplicated
lines. Keep every dialogue line, the proof sequence entire, each
character's single entrance, and every shot where the product's label is
legible.

## The scene arc

One row per final segment, mapping the emotional curve of the piece:

| Segment | Emotion carried | Outcome reached | Where it breathes |
|---|---|---|---|

The edit's job is to preserve the arc: seam count and scene length are
authored choices serving it, never generation limits. If the final cut's
lengths are not explained by this table, the edit drifted from the
scenes as authored — fix the edit, not the scenes.

## Audio

- **Keep the room tone** — it is the connective texture across hard cuts.
- **One underscore** that builds through the confrontation and resolves
  warm at the reveal.
- **Lead cuts with dialogue** for continuity across the visual joins.
- **The offer block** drops the ambience and holds the voice clear.
- **No silent stretches**, ever — the same rule the generation obeys.

## On-screen text

Burn captions for every dialogue beat — white, outlined; most of this
audience watches with the sound off. The offer gets its own caption
carrying the terms. No title cards, no watermarks: the generation locks
ban them and the edit must not reintroduce them.

## Output

9:16 vertical, 1080×1920, source frame rate. Hard cuts throughout — the
scenes carry their own internal motion, so dissolves fight them. Only the
caption burn needs a re-encode.

## The QC gate — before anything ships

1. **Dialogue** — every line present, in order, on the right speaker.
2. **Blocking continuity** — check each character's screen position across
   every join. A character flipping sides between scenes is the most common
   break; fix it by matching the incoming scene's first frame to the
   outgoing scene's last, or by choosing a different cut point.
3. **Wardrobe** — each character's locked outfit, in every segment.
4. **Product** — label legible, texture right, no morphing hands on it.
5. **Colour** — white balance drifts between scenes; grade-match every
   segment to the master look.
6. **The offer** — the claim boundary respected, terms correct.

## The loop, every ad

```
1. WRITE the director's cut — story, cast locks, ledgers, mechanics.
2. ASSEMBLE prompts from the eleven-section template.
3. GENERATE the whole film in one batch.
4. ASSESS each scene: what does this beat actually contain?
5. BUILD the decision list: source → final, with trims marked.
6. ASSEMBLE: hard cuts, audio-led joins, ~1.5s through setup,
   slower through the proof and the offer.
7. AUDIO: room tone, underscore, ambience dip on the offer, caption sync.
8. CAPTIONS: dialogue plus the offer terms.
9. QC GATE — fix continuity at the cut where you can, regenerate only
   the scenes that truly failed.
10. DELIVER 9:16 1080p; keep the source scenes for versioning.
```
