# Stage 3 · B-roll — the cutaways

An insert laid over the take it covers. Her voice never stops, so
`generate_audio` is **false**: a cutaway carrying its own dialogue fights the
take underneath it.

Notated under its beat with the second it lands on, and made after the A-roll
exists. Near a third of runtime is the ratio.

```shape
{place}

{subject}

{action}

{look} {text_rule} No filming equipment in shot.
```

`{text_rule}` has two forms and `prompt.py` picks by whether the row is marked
`products`. Sending the wrong one breaks the shot:

| row | line sent |
|---|---|
| no product in frame | nothing in frame carries any text, label copy, price tag or writing |
| real product in frame | the only writing is the real label each product actually carries; no invented lettering |

Forbidding all text over a product shot fights the element that finally put the
real wordmark on the bottle. Saying nothing at all lets the model invent a
price tag.

## What each field is for

**`{place}`** — where it is. Attach the set element *unless real product must
read*: `set-shop-counter` dresses its own shot with invented white shampoo
bottles. When the product is the point, describe the surface plainly and
attach the product elements by name, saying nothing else is in frame.

**`{subject}`** — what is in it. A named product arrives as its **prop
element**, never as a description. That is what put the real label on the
bottle; no amount of adjectives did.

**`{action}`** — ONE action, with a beginning and an end. An insert told only
what is in frame comes back as a still with a slow push on it.

**`{look}`** — how close, how shallow, how lit. Never name the camera.

## Two failures worth keeping

**An unstated quantity comes back maximal.** "Two fingertips glossy with a
warm amber oil" produced honey being smeared on a jaw. Name the amount and
forbid the failure: *only the faintest trace, already worked in, nothing
pooled* — and drop the colour word that is driving it.

**Motion needs something to shake.** "The bristles break into a fast tight
shimmer" on a product filling frame came back a still hero render on a
seamless black background. Put the product in a hand under practical light and
put **water beads on the bristles** — now the movement has a witness.

## Cast it. Do not let the model choose who it is

"A man's jaw at the beard line" returns whoever the model reaches for, and it
reached for a white man four times in one set, for a base that reads Black
33%. **Every shot of a customer's skin attaches the core avatar as an
element**, the way every talking beat attaches Nina. The roster is
`brands/<brand>/core-avatars/casting/roster.json`; a face is cast from it,
never left to the prompt.
