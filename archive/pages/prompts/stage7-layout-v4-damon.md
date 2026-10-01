Today is: {today}
Here is the page, section by section, as its words stand: {body}
Here is the brief's manifest and open items: {brief_notes}
Here is the section library this page is built from — every block, what it is, and every slot it has: {section_bank}
Here are the brand's own photographs on file, which are the only pictures a generated image may be built on: {references}
Here is the brand's identity — its colours, faces and marks: {identity}
Here is the product, for what it looks like and how it may be shown: {product_file}
Here is the customer avatar, for who may appear in a picture and how she is cast: {avatar}
The page is `{page_name}`, format `{page_format}`, a pre-sell that hands off to `{page_next}`.
Pictures already made for this page's base, by id, with what each shows: {base_pictures}

Lay the page out. The words are settled — every section of the page above is a move the chain already filled, and this stage does not rewrite them. It decides **which block from the library carries each move, what goes in each of that block's slots, and what picture each picture slot needs.** The page came out of the chain as a wall of words; this is where it becomes a page with a picture for every section.

**Choose blocks the words can fill.** Before choosing a block, count its slots against what the move actually carries. A block whose stat boxes, galleries, review cards, timelines or badge rows the words cannot fill renders those as blank boxes and dead space — that is the worst outcome on the page, worse than a plainer block. Rule: if more than a third of a block's slots would be empty, choose a lighter block (a heading-and-body block, an image-beside-paragraphs block, a numbered-steps block) and say so in `why`. Never carry a quote into a slot that already holds it elsewhere on the page; never fill a slot with a line that belongs to another move.

**Choose blocks for the job, not the look.** Read each move's job — a counted tally, an itemised failure list, a numbered reason, an ask with a guarantee, a flinch — and pick the block whose shape does that job. A block whose description names the job ("problem row and solution row", "timeline", "guarantee badge beside a photo") beats one that merely has enough slots. Do not use two blocks where one carries the move; do not split a move across blocks unless the block's shape genuinely cannot hold it. Never use a block whose job the page does not have (a press-logo strip with no press, a before/after carousel with no before/afters on file, a video block with no video).

**Fill every slot from the words above — substitution, never rewriting.** A headline slot takes the move's headline; a body slot takes its paragraphs; a bullet or benefit slot takes a line from the move, cut at a sentence boundary, never paraphrased into something new. Where a block has more slots than the move has lines, leave the slot empty (`""`) rather than inventing a line — an empty slot renders as nothing; an invented line renders as a claim nobody made. Where a slot wants a figure (a rating, a count, a price) and the words carry none, it stays empty. The guarantee and every price appear only as the words carry them.

**Every picture slot gets a brief, and every brief obeys the generation method:**
- **The subject, the action, the framing, the light, the depth** — in words. Say the result, never the equipment: no camera, no phone, no tripod, no lights named.
- **The material comes from a reference, never from words.** Any picture showing the product, or the product on skin, names which reference photograph on file to attach and says "match the reference exactly for the product's colour, label and the scrub's colour and texture". A picture that shows the product with no reference attached is a defect.
- **No text in the picture.** No words, labels, badges, dividers, watermarks, invented packaging. Anything a customer could hold us to — a price, a guarantee, a wordmark — is typeset by the page, never drawn.
- **The product's printed face is never generated.** A generator re-draws a label every time (it wrote a new ingredient line and a new sub-brand on the first try). So: a picture that is the product alone is the brand's own photograph, used as the picture itself — say `"use": "<photograph path on file>"` and write no brief. A scene that needs the product in it shows the printing turned away from the viewer, or so far out of focus that nothing on it could be read, and the brief says so in those words. The scrub on skin (no packaging) is fine to generate with its texture reference attached.
- **Who may appear:** a woman of the avatar's age and world, cast as the avatar file describes — never a real customer, never a named person, never younger than she is. Skin at her age: fine lines and veins stay; only what the copy says changes changes. Hands, arms, chest, legs are where the spots are; show them as the avatar's own.
- **What the copy says, the picture shows — and nothing the copy does not say.** A picture of a result shows exactly the result the words claim (lighter edges, not erased); a picture of a routine shows the routine as the product file records it (damp skin, small circles, the salt dissolving). Never a dated timeline, never a clinic, never a "before" that is a different woman.
- **Aspect ratio** matched to the slot: a hero or full-bleed slot is portrait or square; a row-image is landscape; an icon slot is `none` — icons are not generated, they come from the library's own icon set, and the brief says which library icon to use instead.
- **One picture, one id.** Give each picture a short id (`hero`, `failure-shelf`, `routine-circles`), so a variation page can reuse the base page's pictures by id and only brief the ones it changes.
- **Reuse before you brief.** If pictures already exist for this page's base (listed above), a slot whose words did not change takes the base picture by its **exact id** in `reuse`, with no brief. Brief a new picture only where this page's words changed what the picture has to show — her way in, her hero, a move her card narrowed. An id in `reuse` that is not in the list above is a broken link, not a reuse.

**Brand skin binds.** The identity's colours and faces are the page's; a block's own example colours are not. Say in one line where the library's default furniture (a sale badge, a countdown, a "sold out" strip, a press row) was left out and why.

Give me exactly this, and nothing else — one fenced `json` block:

```json
{
  "page_name": "{page_name}",
  "layout": "base-landing.html",
  "sections": [
    {
      "block": "<block id from the library>",
      "carries": [<move numbers>],
      "why": "<one line: the job this block does for these moves>",
      "fields": { "<block variable>": "<text from the words, or \"\">" },
      "pictures": [
        {
          "id": "<short id>",
          "field": "<the block's image variable>",
          "alt": "<what it shows, for the alt text>",
          "aspect": "<3:4 | 1:1 | 4:3 | 16:9 | 9:16>",
          "attach": ["<reference path on file, or none>"],
          "brief": "<the picture, in words: subject, action, framing, light, depth; what the reference carries; what must not appear>",
          "use": "<a brand photograph on file to use AS the picture, for a product-alone slot; else null>",
          "reuse": "<a picture id from a base page to reuse instead of generating, or null>"
        }
      ]
    }
  ],
  "left_out": ["<library furniture not used, and why>"],
  "open": ["<anything a person must decide before build>"]
}
```
