Here are the stage-4 outputs — for each source format, the finished frame
from the close pass and the complete headline set that heads it:
{stage4_outputs}
Here is the replication spec: {replication_spec}
Here is the teardown record: {teardown_record}
Here is the product: {product_file}
Here is our offer: {offer_file}
Here is our customer language bank: {language_bank}
Here is our identity anchors file: {identity_anchors}

**The maker is a graphic designer.** Not a creator, not an editor, not a
copywriter. They open a blank artboard and they need positions, sizes,
colors, words and a picture. Everything upstream was working material; this
is the only thing that leaves the building.

Turn the outputs into the build sheet.

Six rules govern everything below.

**Nothing unresolved crosses into the build sheet.** If a frame still carries
a `[SLOT: …]`, either the fact exists **in one of the files above** and you
fill it from there, or the line is cut and its zone closes. A designer who
meets an unfilled slot will set the placeholder in type or invent something —
both ship. Every slot you cut gets listed in the internal document so nobody
thinks it was handled.

There is no third option. **Generalising a slot is filling it.** Turning
`[SLOT: current promotion]` into "the bundle deal" has announced a promotion
nobody approved.

**This document adds no facts.** Every claim traces to a supplied file. Watch
for the ones that arrive as flavour rather than as claims: a country or
heritage the product file never mentions, a named method, an ingredient
count, a manufacturing story, a founder detail. If it is not in a file, it
does not appear — not in a concept name, not in a headline option, not in an
image prompt. And a phrase appearing in a file is not automatically ours to
use: the language bank records what customers say **and what they were shown
not to say** — a phrase inside a sentence reporting its absence is evidence
against that phrase, not a source for it.

Prices come from the offer file exactly as written — character-exact for the
guarantee. Where the same product sells at different prices on different
surfaces, say which surface each price belongs to.

**Every number is a number, never a direction.** "Large headline, upper
third" is not a spec. Give the position as a percentage of frame height and
width, the type size as a percentage of cap height to frame height, the color
as a hex value, the alignment as a word. A designer who has to interpret a
size will pick a different one than the last designer did, and the set stops
looking like one campaign.

**One template, many files.** Every approved headline is its own file built
on the same template — same zones, same positions, same sizes, same picture
treatment. Say this explicitly, because a designer given six headlines will
otherwise design six layouts and destroy the test.

**Say what the picture is, twice.** Once as an art direction a photographer
could shoot, and once as a **generation prompt** a text-to-image model could
run. They are the same frame described for two different makers, and whichever
route the brand takes, the other one is the fallback. Never write a
generation prompt that names a real person, and never write one that
contradicts {identity_anchors}.

**The designer must never have to ask a question.** If whoever gets this
would have to guess a size, a color, a crop, a product, or what they are
allowed to say, the build sheet has failed and the fix is in the build sheet.

Give me these two documents.

**DOCUMENT ONE — THE BUILD SHEET**

Headed as a build spec: brand, product, number of files to build, the ratios
each concept ships in, and the delivery format.

Then, once for the whole sheet, **THE TEMPLATE**:

- **The grid** — every zone, in reading order, as a table:
  `Zone | Top % | Bottom % | Horizontal span % | Alignment | What lives here`
- **The type spec** — one row per zone: typeface class and a named fallback
  the designer certainly has, weight, case, cap height as a percentage of
  frame height, color as hex, tracking, leading, and any treatment. Where a
  single line carries two colors, say which words take which.
- **The palette** — every color as a hex value with the zone it belongs to,
  split into ground, type, and accent.
- **The furniture** — every bar, badge, box, rule and arrow with its shape,
  size as a percentage of frame, color, and zone. This is what the designer
  builds once and reuses.
- **The safe zones** — what must stay clear at each ratio, and the legibility
  floor: which zones must still read at 25% scale.

Then one section per concept:

- a name · the source format it came from, one line
- **the picture, as art direction** — subject, what they are doing with their
  hands, gaze, wardrobe, set, props in the sharp plane, light direction and
  quality, lens and distance, depth of field, grade
- **the picture, as a generation prompt** — one paragraph, ready to run,
  written in the plain declarative register image models take. Name the
  subject type and age range, the frozen action, the body part in frame, the
  props, the set, the light, the lens and the depth of field. State the
  aspect ratio. Add the negative constraints as a separate line: what must
  not appear.
- **the copy, zone by zone**, set as final words, ready to paste
- **the headline files** — the control first, then every approved variation,
  none dropped and none ranked, each one a numbered file to build on the same
  template with its own picture note where the image concept differs
- **what must be visible in the picture** for each copy line to be believed
- **the export list** — every ratio, its pixel dimensions, and which
  placement it serves

Close with who owns questions and what happens when a file is built.

**DOCUMENT TWO — INTERNAL**

Claim trace (one row per claim, each naming its file, or REMOVED) · the test
matrix (each headline a cell, control marked; statuses live in the hook
ledger) · concept provenance (source format level) · slots cut · flags,
carried forward from every upstream pass · the ratio check · rejected
concepts and why · **hand-off line: which files are approved to build and
which are waiting on a named fact.**
