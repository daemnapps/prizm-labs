# The picture prompt — one skeleton, every picture

This is the whole prompting structure. An email hero, an ad frame, a page
section and a scene still are all sent as this, in this order, with different
values in the slots. Nothing anywhere else assembles a picture prompt.

The order IS the contract: a prompt rendered in a different order is a
different prompt even when every value matches. A slot with nothing in it is
left out entirely — never sent as an empty line, never filled with a guess.

Lifted from `tools/image-production/static/tools/prompt.py` (slots, not prose;
the order is fixed; the pack owns how a frame is rendered and never what is in
it) and `components/email-production/simple_email.py` (the caller's words,
then the frame, then the standing rules, then the reference clause).

---

{purpose_frame}

{direction}

{style}

{format}

{template}

{product}

{brand_ground}

{references}

{aspect_line}

{standing_rules}
