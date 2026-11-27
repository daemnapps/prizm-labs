# Design step 1 + 1b · the job card and the concept

BRAND VISUAL DNA: the signature elements that make this brand look like itself; every email uses them.
PRODUCT TRUTH IS LAW: every product appears exactly as its product file describes it (its container, colour,
proportion and how it is held); never call it or draw it as anything else.

THE EXAMPLES BELOW ARE INVENTED. They show the shape of an answer, never its content. Every
word you write comes from the INPUTS: this brand, this product, this reader, this culture map.
Never borrow a product, a person, a price, a place or a joke from an example.

You are planning ONE email before anyone designs it (the owner, 2026-10-09: "think from a
first-principles perspective about the designs of these emails and what needs to actually go
in them"). The copy is already written and signed off. Your job is to decide what this email
must do, and the one concept from the reader's own culture that makes it impossible to mistake
for every other email he gets.

## INPUTS

<learnings>
{learnings}
</learnings>
LEARNINGS are every correction and every win from past reviews. They outrank everything below except
PRODUCT TRUTH: a NEVER never happens again, a DO always does.

<send>
{send}
</send>

<kind>
{kind}
</kind>

<copy>
{copy}
</copy>

<brand_position>
{position}
</brand_position>

<product_truth>
{product_truth}
</product_truth>

<brand_visual_dna>
{visual_dna}
</brand_visual_dna>

<avatar_profile>
{avatar}
</avatar_profile>

<culture_map>
{culture}
</culture_map>

<moment_world>
{moment_world}
</moment_world>

<brand_design_rules>
{design_rules}
</brand_design_rules>

<brand_moment_looks>
{themes}
</brand_moment_looks>

<concepts_already_used_in_this_batch>
{used_concepts}
</concepts_already_used_in_this_batch>

## FILL EVERY SLOT. One line each unless the slot says otherwise.

READER: who opens this (the segment, and the avatar's own profile) and what he or she already believes about us.
JOB: the email's one job, in one sentence.
BELIEF: the one belief it has to create.
PROOF: what proves it, from what the brand owns (a real customer, a real result, the product's
  own facts). Never a statistic the copy does not carry.
ACTION: the one action. One button.
MEASURE: how we will know it worked.
CUT: what from the copy or the obvious design you are leaving out, and why.
PRODUCT_FACTS: every price, product name, claim and in-the-box fact this email must get exactly
  right, each with where it comes from in the inputs.
CONCEPT: one line, what the reader SEES. A format borrowed from the culture map (a poster, a
  show, a group chat, a ritual, a place), never a real person's face, name or likeness. The
  villain is the problem, never the reader.
CULTURE: the format borrowed and the exact line of the culture map it comes from, quoted.
THEME: REQUIRED when the send's `occasion` is a named moment (a holiday, a sale event such as
  black-friday or cyber-monday, a season): the moment's key, taken from BRAND MOMENT LOOKS when the
  brand has one for it. When the brand has no look for that moment, still write the moment's key: the
  line holds the email until the look is made. `none` only for a send on no moment.
SUBJECT: a subject line that names the concept, not the product. 30 to 50 characters.
PREVIEW: the preview line, 30 to 50 characters.
OPEN_QUESTION: anything only a person can decide (who signs it, a fact that is not on file), or
  `none`.

## RULES (each one came from a review)

1. A letter is a note from a person: one photo, three or four short paragraphs, one ask. A
   design email is a short landing page: five to eight pictures, no block over 30 words.
   Follow the KIND you are given; do not change it.
2. Lead with the page price the inputs give; the one-delivery price struck through. Never a
   deadline the offer does not have.
3. One price, one offer, one button.
4. Nothing in the brand design rules may be broken by the concept.
5. If the copy has no product, the concept still comes from the culture map.
6. A send on a moment is built from the MOMENT WORLD: the concept is one of its seeds or is made from its
   scenes and objects, and it must FEEL like that moment on its first screen: the concept lives inside the
   moment (Black Friday is an event, after dark, the one weekend of the year), the eyebrow names it,
   the hero picture is set in it. A concept that would read the same on any ordinary week has failed.
7. Never a concept already used in this batch: each email in a run gets its own borrowed format.

## ANSWER

Return ONLY a JSON object with the slots above as lower-case keys (`reader`, `job`, `belief`,
`proof`, `action`, `measure`, `cut`, `product_facts` as a list of strings, `concept`, `culture`,
`theme`, `subject`, `preview`, `open_question`). No prose before or after it.

Invented example of the SHAPE only:
{"reader": "Bought once, months ago; thinks it was fine but forgot it.", "job": "...", "belief": "...", "proof": "...", "action": "...", "measure": "...", "cut": "...", "product_facts": ["..."], "concept": "...", "culture": "...", "theme": "none", "subject": "...", "preview": "...", "open_question": "none"}
