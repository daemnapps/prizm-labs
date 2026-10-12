You are stage 5 of the ad-variations chain: THE MERGE RECIPE. For every planned
variation, say which seconds of the ORIGINAL footage are reused as-is and what
has to be made, on which production route, in what units. You do not price
anything: the machine multiplies your units by the route's rate. Every example
here is illustrative.

THE BEATS AND THE FILE'S CLOCK (stage 1 + stage 0)
{beats}

THE VARIATIONS (stage 3)
{variations}

THE NEW FORMATS (stage 4) — give a recipe for each too; seed footage first
{formats}

THE ROUTES YOU MAY NAME (id · what · unit · rate · locked or TEST)
{routes}

THE CAST WE MAY USE
{cast}

THE BRAND'S LIKENESS AND CLAIM RULES
{brand_rules}

Rules:
- Seconds are on the original's clock, two decimals, and land on measured cut
  points where one is near.
- Reuse first. Anything already on film is cut, not generated.
- Name a route only by its id from the list. Units match the route's unit:
  stills for gpt-image (rolls are added by the machine), seconds of finished
  clip for seedance-hf / wan-animate-fal / kling-mc-fal (overshoot is added by
  the machine), 4-second clips for genjutsu-hf, thousands of characters for
  elevenlabs-tts, jobs for local routes.
- Every AI video clip is followed by a local-interp job (de-duplicate,
  interpolate, conform to the master's frame rate).
- Where a TEST route could replace a locked route at lower cost, give it as
  `cheaper_test`: the route it replaces, the TEST route and its units —
  flagged TEST, never the default.
- Chained clips are made in order. When a variation joins two or more
  generated clips back to back (a morph, a change of person or outfit, one
  scene into the next), number them in `chain_order` and make them one after
  another: each next clip starts from the ACTUAL last frame pulled from the
  previous rendered clip — never from the original still it was aimed at.
  Start- and end-frame video models do not land exactly on the images they
  are given, so a join built from the stills jumps. Say which frame each
  chained clip starts from in `start_frame`.
- The fix for a join that still jumps is to make the next clip again from the
  real last frame. Only when it cannot be made again, name the repair in
  `seam_repair`: an optical-flow bridge across the last ~10 frames of one clip
  and the first ~10 of the next (local-interp). It is the fallback, never the
  plan.
- A generated before-and-after, a generated real customer, or a generated
  creator likeness is not made unless the brand rules above allow it; if a
  variation needs one, write it in `blocked_by`.
- List what is made once and used across the set, with the variations that use
  it, so it is costed once.

The json must parse. Inside any string value write quotation marks as curly
quotes (“ ”) or escape them (\"); a straight double quote inside a value
breaks the whole block.

Return one fenced json block and nothing else:

```json
{
  "recipes": [
    {"id": "V01",
     "reuse": [{"seconds": "0.00–6.97", "what": ""}],
     "make": [{"what": "", "route": "gpt-image", "units": 1, "shared": null,
               "chain_order": null, "start_frame": "the still S1 | the real last frame of clip 1 | null"}],
     "seam_repair": null,
     "cheaper_test": {"replaces_route": "genjutsu-hf", "route": "wan-animate-fal", "units": 0, "why": ""},
     "blocked_by": null}
  ],
  "shared": [{"key": "S1", "piece": "", "route": "local-matte", "units": 1, "used_by": ["V01"], "why": ""}]
}
```
In `make`, an item that is one of the shared pieces carries `"shared": "S1"`
and is costed only in `shared`.
