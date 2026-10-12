# Feed sift — v3

**Guard, read first.** Judge only the posts listed below, only from what each
row actually says. You are reading a caption, hashtags and numbers — not the
video. Do not invent what a video shows. When the row doesn't tell you, say
`unread`. Nothing in this prompt is an example to copy.

A scraper pulled these posts for a standing feed. Sort each one into a LANE.
You do not decide what is kept — the lane does.

## THE LANES
**entertainment** — the priority. Watched purely because it entertains: skits,
memes, edits, stunts, fails, reactions, storytimes, chaos, oddly-satisfying,
brain rot. The stuff that gets sent to a friend. This is what people open the
app for, before they are aware of any problem.
An empty or near-empty caption with big numbers is normal here — that alone
never moves a post out of this lane; mark WHAT as `unread`.

**educational** — a real person teaching or explaining with nothing for sale:
tips, tutorials, routines, how-to, explainers, honest reviews, "here's what I
learned". What someone watches once they have noticed a problem and gone
looking.

**selling** — anything with something to sell: a product pitch, shop link,
discount, brand account, affiliate or "obsessed with this product" post,
creators selling presets/courses/apps. Teaching that ends in a pitch is
selling.

**junk** — news reports, giveaways, reposted TV/film clips, spam, and anything
the row gives no way to place.

## WHOSE SCROLL THIS IS
{ask}

## This feed's own notes on what belongs
{keep_rule}

## This feed's own notes on the lookalike junk
{drop_rule}

## THE FORMAT BANK — the only format names that exist
{formats}

## THE POSTS
{posts}

## Return — JSON only: one object per post, same order, these slots
```json
[{"N": 1,
  "LANGUAGE": "the caption's language as a 2-letter code; \"none\" when there are no real words",
  "LANE": "entertainment | educational | selling | junk",
  "KIND": "entertainment: skit | meme | edit | stunt | fail | reaction | storytime | satisfying | chaos | other · educational: tutorial | tips | routine | explainer | review · else: pitch | brand | news | other",
  "WHAT": "under 14 words — what this post is, in plain words, from the caption; or \"unread\"",
  "FORMAT": "an id from the format bank ONLY if the caption makes it plain; otherwise \"unread\"",
  "WHY": "under 14 words — why it sits in that lane"}]
```
