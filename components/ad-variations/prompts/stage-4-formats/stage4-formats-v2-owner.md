You are stage 4 of the ad-variations chain: NEW FORMATS. The brand's whole
corpus has been counted into the Variable Index. Recombine elements the corpus
already proves into formats this brand has NOT run — for example the hook of
one family with the proof structure of another. Every example here is
illustrative.

THE SOURCE AD'S ELEMENTS (stage 1)
{elements}

THE PROVEN VALUES, family by family (from the Variable Index — the brand's
posts, weighted by views and saves)
{index_summary}

THE COMBINATIONS THE BRAND HAS ALREADY RUN (hook sub-type × proof type ×
format, with post counts and view share). A format that appears here is not
new.
{combos}

THE AVATARS
{avatars}

THE BRAND'S RULES
{brand_rules}

Propose {k} new formats. For each:
- a short name and one line on what the viewer sees;
- its parts: at least three, each a Variable Index id with a value the corpus
  shows, and that value's evidence exactly as the index gives it (posts, view
  share, save rate);
- `status`: always "NEW — untested". The combination has not run for this
  brand; say which existing combination it is closest to;
- why it might work, labelled INFERENCE;
- what owned footage could seed it (a post rank or id from the corpus, and the
  seconds, when the parts already exist on film), and what would have to be
  made;
- the avatar and sub-avatar it is aimed at.
Do not propose a combination listed as already run. Do not use a value the
index does not show.

The json must parse. Inside any string value write quotation marks as curly
quotes (“ ”) or escape them (\"); a straight double quote inside a value
breaks the whole block.

Return one fenced json block and nothing else:

```json
{
  "formats": [
    {"id": "F01", "name": "", "what_the_viewer_sees": "",
     "parts": [{"variable": "V-hook.04", "value": "", "evidence": ""}],
     "status": "NEW — untested", "closest_existing": "", "why": "INFERENCE — …",
     "seed_footage": "", "to_make": "", "audience": {"avatar": "", "sub_avatar": ""}}
  ]
}
```
