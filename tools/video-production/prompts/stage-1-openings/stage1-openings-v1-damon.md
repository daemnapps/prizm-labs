# Stage 1 · Openings — the hook set

**Generate every opening the brief writes. All of them, every time.**

This is the scale mechanism and it is the stage that got skipped. A tested
body can carry a dozen fronts: the back ninety seconds stay frozen and only
scene one is replaced, so six openings is six ads for the price of six four-
second clips. The brief for `ser-01` specified six — Control, The bag on the
counter, Come back in a week, The collar, The blackness, One swipe — and none
were made, because the plan was built from an old working file instead of from
the brief.

An opening is a **first scene**, not an insert. It carries the hook line, so
it is spoken: `generate_audio` true, then `voice_change`, exactly like A-roll.

```shape
{film}

{who} says, {delivery}:

"{line}"

The action is already underway in the first frame — nothing starts from rest. \
Locked frame unless the film says otherwise, no cuts. \
{text_rule} No filming equipment in shot.
```

## Why `already underway` is in the shape and not optional

A hook has under a second to stop a thumb. A clip that opens on a held pose
and then begins spends that second on nothing. The brief's own openings are
written this way throughout — *"both hands are already up and moving, the
camera catches her at the top of a gesture, not at rest"*, *"the motion is
already underway in frame one"*, *"already in motion at frame one"* — so the
shape enforces it rather than trusting each one to repeat it.

## `{film}` comes from the brief verbatim

The brief writes a full **Film:** paragraph for every opening, and it is
already a shot description: the room, the framing, the light, what moves.
Paste it. Do not paraphrase it, do not improve it, do not trim it for length.
It was written by the stage that read the source and it is the specification.

Attach the elements it implies — the presenter, her hands if they enter frame,
the room, and any product named — and the facts ride along automatically.

## Openings that show no face

Several are macro or object shots: a bag tipping, a razor pass, a collar
pulled down, a phone mid-scroll. Where nobody is on camera the line is still
spoken over it, so the clip is still generated with audio and still revoiced.
`{who}` is then the voice, not a figure in frame — write it as *"She says,
over this:"* and keep the picture to what the brief describes.

## Naming

Openings are `O1`…`ON` in the order the brief lists them, and they live in
`cinema/openings/`. Each one is a complete alternative first scene: the cut
swaps `O<n>` in ahead of the spine, and everything downstream is untouched.
