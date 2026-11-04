# Viewer fix — {brand} · {avatar} (v2)

Five people from this avatar scrolled the ad below inside their real feed and
passed on it. You rewrite ONLY what made them pass on it, so the next five
believe it and move.

**What failed:** {fix_at}

**What the viewers said, and what the brand already has on file for it:**
{notes}

**What has worked on this avatar before:**
{learnings}

**How these people really talk** (their own words, from the brand's language bank):
{language}

## Rules

1. **Touch only what failed.** Leave every other line, frame and direction
   exactly as it is, word for word.
2. **The structure is locked.** Same scenes, same order, same people, same
   places, same camera. Adapt words and how a moment is played, never rebuild.
3. **Prices, guarantees and offer lines stay word for word.** They come from the
   website. If a viewer doubted one, answer the doubt around it: before it,
   after it, or in how it is shown. Never by rewording it.
4. **Answer the doubt the way the bank says to.** Where the bank has an answer,
   follow it. If it says "answer skepticism with real customers, not claims",
   do that, not a new claim.
5. **Nothing invented.** Every new spoken or on-screen word comes from the
   language bank, the objection bank's answer, or the viewers' own words, and
   you name which. No new facts, numbers, results, testimonials, people or
   promises that aren't in those sources.
6. **No pitch.** No feature lists, no benefit stacks, no lines that sound like
   an ad. Say it the way they would say it to a friend.
7. **Cut before you add.** Fewer words on a card reads less like an ad. Never
   stack more lines onto a card or frame that was already called a pitch. At most
   one change per doubt.
8. **Only point at what the ad shows.** Never write "a real customer", "day 90",
   "before and after" or any proof the ad doesn't actually show on screen. A
   reply line from the bank that refers to another asset doesn't belong here.
9. **No lists.** Never put more than one claim or benefit in one line.
10. If a doubt has no answer on file, or the only fix would break rule 3, leave it
   and list it under "open", saying what it would take.

## Return

First the whole brief, rewritten, in exactly the same format as below, between
`=== BRIEF ===` and `=== END BRIEF ===`.

Then JSON only, between `=== CHANGES ===` and `=== END CHANGES ===`:
{"changes": [{"where": "<frame / opening / line>", "was": "<old words>", "now": "<new words>",
  "why": "<the viewer doubt it answers>", "source": "<objection bank | language bank | viewer N>: <the exact words you used>"}],
 "open": ["<doubts with no answer on file>"]}

--- THE BRIEF ---
{brief}
