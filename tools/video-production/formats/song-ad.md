# Format · song ad

**Shape.** The script is sung. A first-person story told as a song, one
lyric line per shot, the product arriving late and small. The words carry
the whole ad; the pictures illustrate them.

Proven end to end 2026-09-03 on fal and 2026-09-04 on Higgsfield; the
exact calls from those two runs are the provider pages
(`../providers/fal.md`, `../providers/higgsfield.md`) and this piece is
their worked example.

| | |
|---|---|
| **Cast** | One. The singer. Others appear only if the lyric names them. A built character — master plus skin references — is the precondition, and building her is a separate process (`../building-the-cast.md`). |
| **Places** | Several, one per shot. No continuous set, so no blocking to protect. |
| **Scenes** | One scene per song section (verse / pre-chorus / chorus / bridge). A scene never splits a section; its length is the section's. |
| **Sound** | The song IS the script. No voiceover, no dialogue, no separate bed. |
| **Aspect** | 9:16 always. |

**What a scene contains.** One song section, illustrated — the
section's lines play inside it; the product late and small. A scene
never splits a section; its length is the section's.

**The beat shape.** Section → section → section, in the order the song
sings them. Verse sections set the hiding; the chorus is the turn; the
product arrives in the last third — in the worked run, the section
before the close, as one small object among the everyday clutter; the
offer is a caption at the edit, never sung. A song that pitches early
stops being a song.

**The order this format runs in — words first, everything cut to them.**
In every other format the pictures are planned and sound is added; here
the song is recorded first and the shot list is derived from it.

1. **Write the lyrics.** Four to six words a line; `[verse]` / `[chorus]`
   markers; no claim the brand cannot make. Read them aloud — a line that
   cannot be sung slowly and understood on one listen is cut.
2. **Record the song.** Ask for the mix explicitly — vocal forward, sparse,
   no auto-tune. Keep the **timing sheet** it returns; it is the edit's
   spine. Read the motion model's duration ceiling *before* slicing the
   song to it. If a word is unintelligible, the lyric is too long before
   the model is wrong.
3. **Derive the shot list from the timing sheet at section level.** One
   scene per section; one ACTION clause per scene — the single thing
   that section shows. A scene never splits a section; if the motion
   model's duration cap forces a split, split at the section boundary
   only, never by line.
4. **Collect the references.** Her master and her own skin panels from her
   boards. Crop, never generate. Check her folder before generating
   anything about her.
5. **Stills.** One call per shot, every reference in every call, the five
   fixed blocks (identity · skin · camera · place · feeling) byte-identical
   throughout; only the ACTION clause changes.
6. **Motion.** One short movement line per approved still, movement only.
7. **Cut and mix.** Concatenate discarding the clips' own audio, lay the
   song over. Local and free. If shots × length ≈ song length, the cut
   lands on the words. Watch it: do the pictures still match the lines
   they sit under? A song-ad cut is LONGER takes, not faster cuts — a
   scene shorter than its section's length is a defect: extend it,
   don't intercut it.

Every gate between those steps — platform plan, preflight, QC, verify,
ledger, coverage, receipt, name — is `RUN-PROTOCOL.md`'s, not this page's.

**Stations used.** cast (the singer, once) · still · restyle (the
Higgsfield route only — the look is a second pass; the identity model
refuses to be styled) · motion · audio (the song). **No voice station** —
the song is the voice.

**The references it needs.** The singer's master and her own skin panels,
in every shot. The packshot in the one shot the product is in. The timing
sheet — not a picture, but the reference the whole cut is built against.
A song ad's realism comes almost entirely from three clauses — the phone
camera, the honest place, the refused smile — which is why they are fixed
blocks rather than per-shot writing.

**The sections that carry the weight.** The lyric, the character
references, and the camera-and-place language. Nothing else does much.

**Ledgers that apply.** None of the six. Different place every shot, one
person, no props handed between people — the lightest format the machine
supports. What replaces them is the reference set, carried into every
shot; that is the only continuity this format has, and it is enough.

**Post (edit-time).** The cut to the lyric timings, the song laid over
(the clips' own audio discarded), the offer caption. Nothing else.

**Gates it adds.** None — `RUN-PROTOCOL.md` carries them.

**The failure this format invites.** Too many words. The first draft of
the worked run had four long lines per verse and the vocal came back
unintelligible — not a model failure, too many syllables for the seconds
available. Halving the line length fixed it with no other change. The
second failure is the mix: left undirected the model buries the vocal and
adds auto-tune. The mix has to be asked for.

**The run it was proven on.** 2026-09-03 on fal and 2026-09-04 on
Higgsfield (the provider pages hold both, call by call); again 2026-09-16
on Higgsfield, record not in the repo. Not yet run under the protocol.

**What still fails.** From the Higgsfield run: no visible skin change
between the first and last shot (put it in as a reference, not a
sentence); a lyric that names a jar when the product is a tube; wardrobe
drifting between shots. From 16 Sep: singing lip-sync is a ceiling of the
motion model — it ships flagged, never re-rolled.

**Cost.** ≈ $__ for 30 seconds. Motion is 94% of it (~$__ a clip against
~$__ a still), which is why stills are approved before anything moves.

## Ruled 2026-10-10 — how a song ad runs straight through

the owner, after the first end-to-end song ad (`runs/video-production/<brand>/<run>`,
edit `runs/video-edit/<brand>/<run>`), which needed five hand workarounds. Each is
now in the machine:

| | the rule | where it lives |
|---|---|---|
| **Timing** | The storyboard is clocked from the song, not from voice lines (a song ad has none): one scene = one sung line = one section, starting on its line in `song/timing.json` (else the song transcript's word times). A scene with no line of its own shares the time before the next sung line; the last runs to the end of the song; a `make: "reuse:S11"` chorus plays the clip already made. `storyboard_plan.py <run>` needs no `--teardown` for a song ad. | `machine/storyboard_plan.py` `build_song` |
| **Every clip** | B-roll is ALL clips — no stills, no holds. A song-ad section with no clip stops the clip plan. | `providers.json` `direct.omni_route.by_format.song-ad.every_section_a_clip` |
| **Resolution** | Omni Flash at 360p (~$__/s), upscaled on this Mac to 1080×1920 by local-studio's `upscale` job — no fal upscale, no cost. | `providers.json` `direct.omni_route.by_format.song-ad`; `machine/omni_clips.py` `upscale_local` |
| **Prompts** | Every clip prompt starts with the run's style lock (the style row's STYLE LOCK line + its motion, `make_character.style_lock`) and carries each scene's action — its `happens`, else its first picture brought gently alive. | `machine/omni_clips.py` `style_line`, `build_prompt` |
| **Start pictures** | Sent to Omni at 9:16, centre-cropped (a 2:3 picture was refused as "third-party content" ~14 times at 360p); the approved picture in `media/` is untouched. | `providers.json` `direct.omni_route.start_picture`; `omni_clips.py` `to_aspect` |
| **Captions** | The sung word sits on a box that moves word to word. A song-ad kit starts on the `word-box` look unless the run's controls name another. | `tools/video-edit/looks/bank.json` `word-box`; `machine/defaults.json` `caption_look.by_format` |

Tests: `machine/test_song_ad.py`; `tools/video-edit/tests/test_word_box.py`;
`components/local-studio/test_esrgan_path.py`.
