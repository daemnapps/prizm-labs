# The email line: think, concept, lay out, picture, check, build

the owner, 2026-10-09: *"think from a first-principles perspective about the designs of these emails
and what needs to actually go in them … propose the design per email … the layout itself, we check
for that first … we generate images if we need to, or we pull in images where it makes sense …
making sure the products are all right … same thing [as] the video editing process and the image
creation process."*

Six steps, in order. A step starts only when the one before it has the owner's OK.

| Step | What it makes | Checked by |
|---|---|---|
| 1 Think | A job card per email: who reads it (segment and what he already believes), its one job, the one belief it must create, what proves it, the one action, how we'll know, what was cut and why, the product facts it must get right | the owner, with step 2 |
| 1b Concept | **The creative pass, every email, no exceptions.** One concept per email, taken from the reader's own culture: read his sub-avatar's culture map (`brands/<brand>/core-avatars/<avatar>/culture-map.md` and the `*.hand-*.md` map) and borrow a format he already watches (a movie poster, a barbershop at midnight, a music-video street, a group chat). Write it on the job card as **concept** (one line: what he sees) and **culture** (the format borrowed and where in the culture map it comes from) | the machine holds any email without both (final check); the owner sees them on the card |
| 2 Layout | The sections top to bottom at phone scale, the first screen marked (everything above it must do the whole job alone), each section's words and where its picture will come from. No pictures | **the owner's OK** |
| 3 Pictures | Each picture slot filled, in this order: the real product (cut-outs, studio shots), what we own (the proof index: before/afters, reviews, UGC, our social posts), and only then made, from a real reference | **the owner's OK** |
| 4 Product check | Every product picture against its real product; every price against the offer bank; every claim against the product file and position.md's NEVER list; what's in the box against the product file | the machine, problems shown to the owner |
| 5 Build + approve | The Klaviyo email (designed sections as pictures, live text, buttons, GIFs, links with tracking, footer); the card on the Klaviyo approval page (`approve_klaviyo.py`) | **the owner's click**, which makes a DRAFT; a person schedules it in Klaviyo |

## Never generic (the owner, 9 Oct)

*"We should never have generic emails … people see the same type of shit all the time. It's better to
stand out within reason, of course, and be tasteful with what we create."*

Every email goes through step 1b, and these are how the concept gets made, every time:

1. **Borrow a format, never a person.** The concept is a format from his culture (an 80s horror
   poster, a barbershop after hours, a Thriller-style street, a graveyard hand). A real person's face,
   name or likeness never appears; a homage shows no face. Humour stays inside the culture map's
   off-limits list: no caricature, never mock the man, the villain is the problem.
2. **The moment gets its own colours.** A season or holiday email gets a palette pulled from its own
   pictures (`THEMES` in the week's `design_system.py`; Halloween: midnight purple, pumpkin buttons,
   toxic-green highlights) and its own header and divider. The brand palette is the default, never
   the only option.
3. **Show, don't list.** Anything the email names gets a picture: every product in a box or set is
   its own made picture in the moment's world (FLEX in a coffin, MIRO as a ghost), never a list of names.
4. **Made from the real thing.** Every made picture starts from the product's casting sheet as its
   reference, and a product at rest is a 3D set printed with it, the words set on top after
   (`design/picture_chain.py`, 2026-10-29: the picture-ad way). After it comes back, **read every label on it**: the generator invents product names
   ("anti-wrinkle", "retinol", "body serum"). Fix the label with an edit pass on that picture, never
   by re-rolling.
5. **Fresh faces.** Proof rotates: a customer's photo is used once a month at most (the final check
   holds repeats). Mix the kinds: before/afters, and real customers' own selfies with their own review
   words (verified buyers, words as written). A customer's words only ever sit with his own face.
6. **Copy in his voice, about the moment.** The headline plays the concept; the body is two or three
   short lines; the subject line names the concept, not the product.
7. **Lead with the page price** (the owner, 9 Oct): whatever price the product page preselects; the
   one-delivery price struck through. Never a deadline the offer doesn't have.

First run of 1b: the Halloween arc, 26 to 31 Oct 2026 (Night of the Bumps; the barbershop at
midnight; the graveyard hand; the Thriller-style street).

Layout rule (9 Oct): **a headline is followed straight away by its image**; badges and seals (the 90-day seal) sit with the section they prove, never as an opener.

Rules carried from the brand: one price, one offer, one button per email (`brand-identity/story.md`,
binding rules); lead with the mechanism, never a bare claim; the guarantee is a refund promise, never a
results claim (`position.md`). Pictures obey the product's own behaviour (FLEX is in a hand, its base or
its case, never loose), and the case is sold separately, so it never appears as if it were in the box.

First run: the week of 12 Oct 2026, `runs/email-production/<brand>/week-2026-10-12/layouts.py`
(steps 1 and 2), shown on the <brand> Email System page.
