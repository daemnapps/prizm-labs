# Reaction-panel repost — rebuild sheet

A podcast reposts another creator's clothespin speed-feat clip with three of its hosts reacting in a fixed strip underneath — 79.8s, 12,018,394 views, 434,032 likes, caption "Exhilarating!"

## Why it works

The whole frame is borrowed spectacle with a live clock on it — a stranger doing something absurd against a running timer, so the proof of difficulty is on screen the entire time and can't be faked. The reactor strip underneath never leaves, which converts a stranger's clip into permission: you watch the faces to know how impressed to be, and you stay because they haven't finished being impressed.

## The beats

| Time | What happens | On-screen text |
|---|---|---|
| 6.39s | Top band: bald man in glasses, dark patterned sweater, behind a floral-tablecloth table in a modest apartment. Open doorway behind, an orange lighter standing on the table. Chest-height handheld, warm interior daylight. | SPED UP ABOUT THAT |
| 19.16s | Cut to a **different setup** — patterned knit sweater, checked tablecloth, nine blue clothespins stood upright. Wide, camera back at table height. | 9 MOLLETTE 😱👽⚡ / 1 MANO 🤚 · watermark "KEN LEE LIVE" |
| 31.93s | Cut to a **third setup** — plaid shirt, teal tablecloth, green pegs. Camera now propped low **on** the table, a black digital timer on the near edge reading 00:00. He's hunched in close, hands at the pegs. | SUPERHERO SPEED!⚡ |
| 44.7s | Identical framing — same door, same table line. Timer 00:08, hands clasped mid-action. | SUPERHERO SPEED!⚡ |
| 57.48s | Identical framing. Timer 00:21, arm sweeping across the table. A glowing badge appears top-right. | KEN LEE ⚡ 70% · SUPERHERO **STRENGTH** (in green) |
| 70.25s | Identical framing. Timer 00:33, he leans back from the table. The badge has climbed and gained two cartoon character heads. | KEN LEE 100% · SUPERHERO **HE IS** (in red) |

Present in **every** frame and not listed above: the three reactor faces on microphones against black in a fixed row under the clip, and the "LAST STREAM ON THE LEFT" banner locked at the bottom.

Two escalations run across the timer beats: a fixed word plus a swapping word (SPEED → STRENGTH → HE IS, colour changing each time), and a corner power meter climbing 70% → 100%.

**Not visible in the frames:** there is no audio here, so nothing is known about what is said, whether the reactors speak, or what the music is — "SPED UP ABOUT THAT" is a burned-in speech caption, not a title, so someone is talking. It is not knowable from stills whether the SUPERHERO and KEN LEE overlays were made by the source creator or added by the podcast's editor. Nothing shows the feat being completed or how many pegs were placed. "MOLLETTE" and "MANO" are Italian for clothespins and hand. The exact emoji glyphs are read off a compressed frame and are approximate.

## What carries the value

Somebody else's escalating feat with a live clock on it. The timer is the proof device — it makes time and difficulty visible without a word of explanation — and the three faces underneath are the licence to keep watching. Nothing in the top band was shot for this post; the reaction strip is the entire contribution.

**This one is not talent-free.** The top band costs nothing to make because it isn't yours, but the bottom band only works if the faces are people an audience already wants to watch. Rebuilding this means having reactors worth cutting to, and having settled who owns the clip you're putting above them.

## Shoot it

You only shoot two things: the feat and the faces.

**The feat.** Prop the phone flat on the table surface itself, lens at table height, aimed slightly up so it looks past a digital timer placed on the near edge. Don't hold it. Lock that position and don't move it between attempts — the whole escalation reads because the door, the table line and the timer sit in exactly the same place every beat. The timer is not decoration; it's the proof, so it must be a real object in the shot, facing camera, legible.

**The faces.** Three people, filmed separately, chest-up, mic in frame, plain black behind them, framed identically to each other. Stack them in a fixed row beneath the clip. They never cut away and never take the full frame.

**Light.** Whatever daylight is already in the room, from one unseen window. No lamps, no fill, no bounce. A real, unstyled apartment with a doorway visible behind — the plainness is what makes it read as found footage rather than an ad.

**Wardrobe.** Whatever the person owns. Plaid shirt, knit sweater. No styling, no colour coordination. The rule for the whole top band is that it must not look shot.

**Layout.** Clip on top, pillarboxed if the aspect doesn't fit — leave the black bars, they signal borrowed. Reactor row beneath. Show banner locked at the bottom, identical every frame.

## Or generate it

The one beat worth generating is the locked timer shot — the reactor strip and banner are a layout you assemble, not something you generate.

```
vertical 9:16 phone-camera photograph, {SUBJECT} behind a plain dining table in a
modest apartment, leaning in with both hands working at {PRODUCT} standing upright
on the tablecloth, a black digital countdown timer sitting on the near table edge
facing camera and dominating the lower third, camera propped ON the table at table
height so the lens looks slightly up past the timer, an open doorway and a pale
interior door on the back wall, warm even daylight from an unseen window, plain
painted walls, no set dressing and no styling, slight compression softness and
handheld phone-video look, no on-screen text
```

**Motion:** camera propped on the table and locked for the whole attempt — no zoom, no push, no reframe; only {SUBJECT}'s hands and the timer digits change, with slight drift between attempts. Generate every timer beat from the same seed frame so the room matches exactly.

**Text overlay:** bottom-centre, sitting over the timer — `{CONSTANT} {ESCALATING}`, where the first word is identical at every beat and the second swaps each stage and changes colour (white → green → red). Top-right corner badge climbing across the run: `{NAME} {PERCENT}%`.

**Reference:** https://www.instagram.com/p/DVRfuQLkXZN/
