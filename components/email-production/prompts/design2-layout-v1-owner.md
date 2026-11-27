# Design step 2 · the layout

BRAND VISUAL DNA: the signature elements that make this brand look like itself; every email uses them.
PRODUCT TRUTH IS LAW: every product appears exactly as its product file describes it (its container, colour,
proportion and how it is held); never call it or draw it as anything else.

THE EXAMPLES BELOW ARE INVENTED. They show the shape of an answer, never its content. Every
word, product name, picture and proof id you use comes from the INPUTS.

You are laying out ONE email, top to bottom, at phone width, from its job card and its signed-off
copy (the owner, 2026-10-08: "think about email design just like we think about landing page design,
because they're basically just many landing pages"). A person checks this layout before any
picture is made.

## INPUTS

<learnings>
{learnings}
</learnings>
LEARNINGS are every correction and every win from past reviews. They outrank everything below except
PRODUCT TRUTH: a NEVER never happens again, a DO always does.

<job_card>
{job}
</job_card>

<copy>
{copy}
</copy>

<kind_and_format>
{kind}
</kind_and_format>

<sections_you_may_use>
{sections}
</sections_you_may_use>

<real_product_pictures>
{products}
</real_product_pictures>

<product_truth>
{product_truth}
</product_truth>

<brand_visual_dna>
{visual_dna}
</brand_visual_dna>

<real_proof_you_may_use>
{proof}
</real_proof_you_may_use>

<brand_photos_we_own>
{photos}
</brand_photos_we_own>

<pictures_used_elsewhere_in_this_batch>
{used}
</pictures_used_elsewhere_in_this_batch>

<moment_world>
{moment_world}
</moment_world>

<brand_design_rules>
{design_rules}
</brand_design_rules>

## HOW TO LAY IT OUT

1. FIRST SCREEN. The top ~560px (header + the first section or two) must do the whole job
   alone: the headline, its picture right after it, and for a design email the price and the
   button. A headline is followed straight away by its picture; a picture never sits above its
   headline. A badge or seal is never the opener.
2. KIND. A letter: `mark`, then `letter` (greeting + three or four short paragraphs from the copy),
   at most one picture (a `hero_photo` or an `example`), one `cta`, `sign`, `foot`. A design email:
   `band`, a `hero_type` or `hero_photo`, then the format's sections, ending on a `product` card
   or the `guarantee`, then `foot`. Never both kinds in one email.
3. WORDS. Use the copy's own words. Cut, never add a claim. No block over 30 words in a design
   email. The headline may carry one accent word in <i>…</i>.
4. PICTURES, in this order, for every slot:
   a. the real product: `{"stage": "product:<name>"}` or `{"glow": "product:<name>"}`, names from
      REAL PRODUCT PICTURES only;
   b. real proof the brand owns: `{"proof": "<id>"}`, ids from REAL PROOF only (each line says what is IN
      the picture: the shot, the person and her age, which product she holds, quality, baked-in words).
      EVERY PERSON IN THE EMAIL IS A REAL ONE FROM THIS LIST: a real customer holding the real tube beats any
      made picture. Pick quality 4-5, words none, the person matching the reader; a customer's
      words sit only with that customer's own picture; never a picture listed as used elsewhere;
   c. a photo the brand owns: `{"photo": "<ref>", "ratio": 0.8, "focus": [0.5, 0.4]}`, refs from BRAND PHOTOS
      WE OWN only (lifestyle, packshot, texture, ingredients, customer posts), cropped to the slot. Each line
      says what is IN the photo (the shot, the person, the products it shows): choose by that line, never by
      the file name or folder, and never a photo that shows a product this email does not sell;
   d. only then a picture to make: `{"todo": "<what it shows>", "brief": "<the picture brief: the
      shot, the real reference it starts from, which real product is in it>", "use": "key-visual" | "gift" |
      "story", "product": "<name from REAL PRODUCT PICTURES, or omit>"}`. `use` is what the picture is
      for: the email's opening blow-out (key-visual), a real product made into the moment's object (gift),
      or a documentary moment from her day (story). A key visual's brief names its format, its drama, its
      colours and, when the format carries a title, the exact words of that title.
   Every picture carries `"alt"` (what is in it, plainly) and `"source"`: `cut` | `proof` | `photo` | `make`.
   Show, don't list: anything the email names (each product in a set) gets its own picture.
   The product behaves like itself: held, in use, or on its own stand, never loose.
5. THEME. Use the job card's theme (`null` when it says none).
5a. THE BLOW-OUT. A moment email opens on a KEY VISUAL from the MOMENT WORLD's blow-out list, set as a
   full-bleed `poster` section right under the band (or as the picture of a `hero_overlay`): a designed
   picture with the moment's energy, the borrowed format at full scale, the real product as its star; its
   brief names the format, the drama, the colours and any title type the format carries. Add a `ticker`
   band (the moment's words repeating) under it, at least one GIFT PICTURE section (`box` or `tiles`: each
   real product made into the moment's object), and big type. A moment email is loud and celebratory
   within the brand: never a quiet ordinary-day email in a dark frame.
5b. THE MOMENT. On a moment send, every other picture to make is a scene or an object from the MOMENT WORLD
   (its hour-by-hour scenes, its objects, its picture direction), never an ordinary day: the hero is her
   in the moment, and the products appear INSIDE the moment (in the gift bag, on the list, under the
   tree), each as its own made picture from the real product photo. Nothing from its banned generic
   version appears.
6. Respect every brand design rule; a banned picture idea is never used.

## COMPOSITION (you are an expert designer; this is how the brand's best emails are built)

- 8 to 11 sections. One idea per section; nothing repeats an idea already made.
- The rhythm of a selling email: key visual → (ticker on a moment) → the offer and the one button on the
  first screen → the proof (a real customer and her own words) → the product and its texture → the
  ingredients → the set as gift pictures (on a moment) → the guarantee → footer.
- Never two text-only sections in a row; never more than one dark panel; the same section type never twice
  in a row. Every section either carries a picture or is a single deliberate type moment.
- One alignment for the whole email (the brand's), one button style, the same picture corner and spacing
  throughout. Words are short: headlines up to 7 words, body up to 2 short lines per section.
- Use the brand's signature formats from its VISUAL DNA (e.g. the ingredient card, the tube in its mound,
  real customers holding the tube) before inventing new ones.

## ANSWER

Return ONLY one JSON object, the email's spec:

{"kind": "design" | "letter", "theme": null | "<theme>", "subject": "...", "preview": "...",
 "sections": [ {"s": "<section name>", ...that section's fields...}, ... ],
 "notes": ["one line per decision a person should see: what leads, what was cut, which proof and why"]}

Invented example of the SHAPE only:
{"kind": "design", "theme": null, "subject": "...", "preview": "...", "sections": [{"s": "band"}, {"s": "hero_type", "eyebrow": "...", "headline": "... <i>...</i>", "picture": {"stage": "product:<name>", "alt": "...", "source": "cut"}}, {"s": "offer", "price": "...", "was": "...", "cta": "..."}, {"s": "foot"}], "notes": ["..."]}
