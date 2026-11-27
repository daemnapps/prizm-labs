# Interface walkthrough, recipient payoff — rebuild sheet

A 14-second, person-free product film: a headline card, a walkthrough of the ad-buying interface, then a hard cut to the customer's side where the same ad turns up inside their answer — 69,000 views, 479 likes, posted by `chatgpt` with the caption "Open a new path to growth with ChatGPT Ads".

**Why it works** — The buyer watches an ad get made and then watches that *exact* ad arrive in someone else's conversation, so the placement is witnessed instead of asserted; nothing has to be claimed because the artifact is the same one on both sides of the cut. The middle of the video carries no overlay at all, which makes it read as a product being shown rather than a product being sold — the only two authored lines are the promise at the head and the ask at the tail.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 1.13s | Flat off-white title card. Logo lockup upper left, benefit line large in black beneath it. A small grey disclaimer sits bottom-centre and stays there the whole runtime. | "ChatGPT Ads" · "Create your campaign in minutes" · "AI-generated image" |
| 3.38s | Rendered interface on white — an ads-manager panel with a tab row and an ad/status column, one sponsored ad card floating in front of it: advertiser name, headline, yellow armchair thumbnail. | Interface words only: "Ads Manager", "Campaigns / Ad groups / Ads", "Ad", "Status", "Simple Home Designs · Sponsored", "Best Pet Friendly Modern Lounge Chairs" |
| 5.63s | Same interface, reframed tighter and higher: a Create button top right, dropdown open, four options, the third highlighted dark. | Interface words only: "+ Create", "Create Campaign", "Create Ad Group", "Create Ad", "Upload Bulk CSV" |
| 7.88s | Hard cut to the other side of the product — a near-empty chat surface, one grey user bubble right-aligned near the top. | "i just adopted my first cat and it's destroying my apartment. Help!" |
| 10.14s | The chat, answered: user bubble above, a two-paragraph reply with the message action icons under it, and the **same ad card from beat 2** — same advertiser, same headline, same chair — sitting inside the answer. | The reply, then the identical ad card: "Simple Home Designs · Sponsored" / "Best Pet Friendly Modern Lounge Chairs" |
| 12.39s | Hard cut to the only photographic frame in the piece: warm dim living room, bookshelves and a lamp behind, a woman in a black sleeveless top and cream trousers sitting sideways in the yellow chair from the ad, a tabby cat reaching up at her from frame right. | "Advertise on ChatGPT today" |

Note on the middle four beats: the video puts **no caption of its own** on screen between the opening card and the closing CTA. Every word there is the product's own interface. Rebuild it that way — adding a caption track breaks the format.

**What carries the value**

One identical artifact recurring across the seam. The ad card built at beat 2 is the ad card that appears at beat 5 — same advertiser line, same headline, same image. If a rebuild lets those two differ, there is nothing left holding the video together.

**Shoot it**

Only the last beat is shot; beats 1–5 are screen work, not camera work. Be plain about that when planning it.

- **Beats 1–5:** screen capture or a rebuilt mock of the interface, flat white ground, no camera and no depth. Two reframes only — the wide panel, then tighter on the menu with it open. Nothing animates except the interface state. The transition from the operator's console to the customer's screen is a straight hard cut, no device, no transition.
- **Beat 6 (the shootable one):** a real living room after dark. One warm practical light — a table lamp — as the only visible source, everything else falling off into shadow. Camera at seated height, square-ish on, subject placed off-centre in the chair with the room's depth (shelves, lamp) reading behind them. Wardrobe: plain and dark on top, light and loose below, no logo, nothing that competes with the product's colour. The product is the brightest object in the frame.
- The frames do not show whether the camera moves at any point in the video — a contact sheet is stills. Assume locked, and check the source before committing to a move.
- The bottom-centre disclaimer sits in the same position in all six frames.

**Or generate it**

The only generatable beat is the closing scene; the five screen beats have to be built, not prompted.

```
vertical 9:16 photograph, {SUBJECT} seated sideways in {PRODUCT} in a warm
lived-in living room, bookshelves and a lit table lamp behind them, dark
sleeveless top with cream wide-leg trousers and white sneakers, low warm
interior light with the lamp as the only visible source and the rest of the
room falling into shadow, shallow depth, film-still look, no on-screen text —
the thing the question beat named is present in frame with them (in the
source, a tabby cat up on its hind legs reaching toward the chair)
```

**Motion:** the contact sheet is stills only and cannot show whether this frame moves — treat it as locked, or a very slow drift, with only {SUBJECT} and the animal moving while the CTA sits centred and unchanged.

**Text-overlay pattern:**

- Opening card: `{benefit} in {timeframe}` under the logo lockup
- Beats 2–5: nothing at all — every word on screen belongs to the product's own interface
- Closing frame: `{action} on {PRODUCT} today`, centred, white
- Every frame: a fixed `{disclaimer}` line bottom-centre, same position throughout

**Reference:** https://www.instagram.com/p/DcJOO-5sV8Y/
