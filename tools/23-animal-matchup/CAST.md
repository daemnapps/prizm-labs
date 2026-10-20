# The cast — built once, attached to every render

A character is a folder, made once with `../video-production/prompts/stage-0f-cast/` and used by every post:

    brands/<brand>/ai-cast/<name>/
      character.md      who it is, the core elements, the identity block (paste-ready — runs paste THIS, never re-describe)
      master.png        the face/identity reference (for an animal: a frame of its approved hero look)
      turnaround.png    front, three-quarter, side profile, back
      angles.png        head angles: both profiles, three-quarters, close-ups, from above
      reference/        the REAL frames it was built from

## Core elements

From the SOURCE frames, list everything that would make it look like a different animal or person if it went
missing: horns, antlers, tusks, ears, mane, markings, tail, size; for a person the hair (and what it must never
become), beard, glasses, build. Every one must be visible in every view of the sheets before the sheets are approved.

## How a render uses it

1. Attach `master.png`, plus the sheet panel for the shot's angle (a profile shot gets the profile panel, a
   close-up gets the close-up).
2. Paste the identity block word for word as `{CORE_ANIMAL}` / `{CORE_LEAD}` in the prompt.
3. Check the take against the PICTURES, one core element at a time (stage-5 QC check 1). One missing = reject.
4. The final cut: `machine/qc.py core CUT.mp4` — one sheet of frames from every second — checked again.

## Outfits ride separately

The identity carries the face; the text (and the master's outfit, taken from the finished hero shot) carries the
clothes. Copy the outfit's words from what the hero shot actually shows, and say what it is not
("no herringbone, no tweed") when the look is plain.
