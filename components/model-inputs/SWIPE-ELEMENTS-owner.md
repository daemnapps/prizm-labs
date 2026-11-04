# What goes into a picture ad (26 Oct 2026)

Page: (private page)

For every swipe: what stays, what we swap, and which picture each swap needs. A picture goes in only when a swap
needs a real thing of ours; everything else is drawn from words.

## The matrix (step 2 of the Prompt Bench, built 26 Oct)

One screen with every choice for one ad. Nothing is made until Make is pressed.

- **The elements.** Every part of the swipe is a row: Keep or Swap. A swap row says what it becomes and its kind: our
  cast (pick who), our product, drawn from words, words, or a library photo. The kind decides which picture goes in.
  "+ Swap something else" adds a row. If any row changes, the swap words sent to the model are rebuilt from the rows,
  one line each ("X in IMAGE 1 becomes Y."). A swap turned back to Keep is sent as "Keep X exactly as in IMAGE 1."
  Untouched rows mean the brief's own swap words go out. Code: `preview.matrix_list`, `matrix_text`, `swap_key`; the
  brief's `swap_list` field.
- **The dials.** Every dial shows three columns: the swipe's level (read by the teardown, `out/controls-swipe.json`),
  ours, and the winners' level. Tap a number to copy it to ours. Presets: the four presets, "As the brief has it",
  "Same as the swipe" and "Like the winners". Each dial says whether it changes the picture or the writing.
- **The ad itself:** product in or out, words set on top or drawn, who is in it (our cast, a lookalike or made-up), and
  add any picture.
- **Everything else:** what the swipe is (format, style, framework and awareness from `out/elements.json`, with their
  scores), the feeling (12), the technique (43), and the guards, which are always on.
- The first problem that stops the make (for example a dial under the system's floor) shows at the top of the screen.

## What the winning swipes do (`runs/ad-anatomy/scoreboard.json`, built by `ad_anatomy.py`)

Each swipe's real number (organic: views, or likes; paid: days the ad ran, else how many times it was rebuilt) is ranked
against swipes of the same brand, kind and number type, giving a 0-1 score. 218 of 222 swipes have a score. Only 94
have their dials read, so the dial results rest on those 94; the 96 older teardowns would add to it.

| Dial | Average score by level (0-100) | Winners |
|---|---|---|
| Humor | none 34 · wry 48 · playful 52 · edged 57 | wry (the swipes overall: none) |
| Dramatisation | literal 33 · emphasis 40 · dramatised 53 · hyperbole 63 · heightened 58 | dramatised |
| Realism | stylised 24 · polished 34 · casual pro 48 · lo-fi real 46 · documentary 58 | lo-fi real |
| Ad-likeness | native 46 · native + product 34 · hybrid 32 · ad-coded 43 · commercial 39 | native |
| Density | sparse 37 · balanced 47 | balanced |

Product in the frame or not: 49 vs 51. Words drawn vs set on top: 54 vs 49. Neither moves the score much.

## Example: "Grandma Yai, three spots" (<brand>-batch-grandma-dark-spots-not-growing-old)

Stays: 9:16 crop, high phone angle from her right, head tilted back and turned away, one hard top-left light, the wavy
grey wall, black fur at the bottom, caption band.

| In the swipe | Becomes | Picture needed |
|---|---|---|
| The woman | Grandma Yai (cast) | Yai's cast photo (`runs/ai-elements/<brand>/casting/yai/master.jpg`) |
| Swollen lips and cheek | three raised dark spots | none, drawn from words |
| Silver pendant | "K-GLOW 12 STEP" foil pouch (parody) | none |
| Skin shine, stray hairs | turmeric dust at the jaw | none |
| The caption | our words | none, set on top after |
| Product | not in this frame ("No product tube in frame. There is no place for one in this post.") | none |

## Today versus the brief

- Product: the tool sends 3 product photos and "draw it at true size"; the brief has no product in the frame.
- Person: no cast photo is sent and the people rule says "lookalike of the woman in the ad"; the brief swaps her for
  Grandma Yai, whose cast photo exists.
- Words: GPT is asked to write the caption; the brief makes the plate without words and sets the caption on top.

Across 232 picture briefs: 22 say in words there is no product in the frame, 11 say it is; 199 do not say it in a
form the tool can read.

## The rule to build

1. The teardown lists every swap as its own line: in the swipe, becomes, and whether it is a real thing of ours (cast,
   product, library set or prop) or drawn from words.
2. The teardown answers "is the product in this frame?" yes or no, and if yes where it sits and which side shows.
3. The pictures that go in are worked out from that list: the swipe, a cast photo per cast swap, product photos only on
   yes, a library photo per library prop. Nothing else.
4. Step 2 of the Bench shows that table with the needed pictures ticked and a reason beside any left out.
5. The words are set on top after, as the brief already says.
