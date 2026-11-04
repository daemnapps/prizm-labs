<!-- v1 (2026-10-08, the owner: "another thing to add in to the viewer is identifying diversity against the scripts / briefs it reads. this would make the process more bullet proof"). Reads one written brief or script — before anything is produced — and returns the seven moves the machine scores. Used by components/creative-diversity/brief_view.py. -->

# Read the seven moves off one {BRAND} brief

You are reading a written ad brief or script, not a finished video. Read what the ad WILL show and say, then tag it on the seven moves Meta's grouping turns on: Meta "groups together ads that share key visual and thematic attributes. When multiple ads look or feel alike, these are seen as variations of the same creative."

Pick every value from the lists. If nothing fits, write `new:<short-name>`; if the brief doesn't say, write `unclear`. Never stretch a value.

**Sub-avatars:** {SUBS}
**Awareness:** unaware · problem-aware · solution-aware · product-aware · most-aware
**Angles:** {ANGLES}
**Formats:** {FORMATS}
**Settings:** {SETTINGS}
**Styles:** {STYLES}
**Face:** the lead person as `gender/age-band/ethnic-appearance` (age bands 18-24 · 25-34 · 35-44 · 45-54 · 55-64 · 65-plus; ethnic-appearance black · white · latino · east-asian · southeast-asian · south-asian · middle-eastern · mixed), or `none`.

If the brief already carries a `piece` block, use its values where they are on the lists and fill the rest from the text.

## The brief

{BRIEF}

## Return JSON only

```json
{"sub_avatar": "", "awareness": "", "angle": "", "format": "", "face": "", "setting": "", "style": "",
 "sections": ["⟨the doctrine section ids the script runs, in order⟩"],
 "why": "⟨one line: what this ad is, so a person can tell it from the others⟩"}
```
