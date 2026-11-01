# Tag one ad on the creative-diversity dimensions — v1

You are reading one {BRAND} ad that is running on Meta (Facebook and Instagram). You get the ad itself (video or image) plus the copy that runs with it. Read the ad the way a creative strategist would, then tag it on every dimension below.

**The rule for every tag:** pick the value from the list given. If nothing on the list fits, write `new:<short-kebab-name>` and say why in `notes`. Never stretch a list value to fit. If you can't tell, write `unclear`.

## What is fixed for this brand
- **The one offer:** {OFFER}
- **The core message every ad should carry:** "{CORE}"
- **The market's sophistication stage:** {STAGE}

## The lists

**Who (sub-avatar: the person this ad is for, with their desire):**
{AVATARS}

**Awareness level (Schwartz): where the ad begins:**
{AWARENESS}

**Angle (the argument):**
{ANGLES}

**Format: what kind of asset it is.** Pick the ONE list that matches the media, then one id from it.
- Video format (who carries it): {VIDEO_FORMATS}
- Video structure (its beats): {VIDEO_STRUCTURES}
- Image format: {IMAGE_FORMATS}
- Carousel format: {CAROUSEL_FORMATS}

**Visual style:**
- Video: {VIDEO_STYLES}
- Image: {IMAGE_STYLES}

**Setting: where it takes place:**
{SETTINGS}

**Face / talent:** describe the lead person on screen with gender (`male` · `female`), age-band (`18-24` · `25-34` · `35-44` · `45-54` · `55-64` · `65-plus`), ethnic-appearance (`black` · `white` · `latino` · `east-asian` · `southeast-asian` · `south-asian` · `middle-eastern` · `mixed`) and role (`ugc` · `authority` · `customer` · `founder` · `interviewer`). If no person is on screen, use `none`.

## Return JSON only, exactly this shape

```json
{
  "media": "video | image | carousel",
  "what_happens": "one plain sentence: what the viewer sees and hears",
  "hook": "the first line said or shown, verbatim",
  "sub_avatar": "<id from the list>",
  "desire": "the desire the ad speaks to, in the avatar's words",
  "awareness": "<id>",
  "awareness_why": "where the ad begins, one line",
  "sophistication": "<stage id the ad is written for>",
  "sophistication_lead": "claim | bigger-claim | mechanism | new-mechanism | identification",
  "angle": "<id>",
  "format_list": "video-format | video-structure | image-format | carousel-format",
  "format": "<id>",
  "style": "<id>",
  "setting": "<id>",
  "face": {"people": 0, "gender": "", "age_band": "", "ethnic_appearance": "", "role": ""},
  "core_message": "full | partial | missing",
  "core_message_quote": "the line that carries it, verbatim, or empty",
  "product_shown": "the product the ad sells, as named",
  "their_words": "yes | mixed | no: does it sound like the avatar or like a brand",
  "looks_ai": "no | some | obvious",
  "slop_risk": "low | medium | high: generic, recycled, or off-brand",
  "notes": "anything the lists could not hold"
}
```
