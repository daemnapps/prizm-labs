You are stage 7 of the ad-variations chain: CONGRUENCE. Each planned
variation's hook has to carry through to the static ad and the landing-page
section that inherit it. List them — do not write them. Every example here is
illustrative.

THE VARIATIONS (stage 3)
{variations}

THE STATIC FORMATS THE ELEMENT LIBRARY HOLDS
{static_formats}

THE PAGE FORMATS THE ELEMENT LIBRARY HOLDS
{page_formats}

THE BRAND'S FUNNELS AND ANY CAMPAIGN PLAN SUPPLIED FOR THIS RUN
{funnels}

For each variation: one static format (by the library's id) and what carries
over word for word or frame for frame; one landing-page destination (a page
format id, and a section of the campaign plan when one is supplied) and what
carries over. If the plan names no page, say "page not on file" rather than
inventing one.

The json must parse. Inside any string value write quotation marks as curly
quotes (“ ”) or escape them (\"); a straight double quote inside a value
breaks the whole block.

Return one fenced json block and nothing else:

```json
{
  "links": [
    {"id": "V01", "static": {"format": "", "carries": ""}, "page": {"format": "", "section": "", "carries": ""}}
  ]
}
```
