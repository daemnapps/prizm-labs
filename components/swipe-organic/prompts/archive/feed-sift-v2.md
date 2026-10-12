# Feed sift — v2

**Guard, read first.** Judge only the posts listed below, only from what each
row actually says. You are reading a caption, hashtags and numbers — not the
video. Do not invent what a video shows. When the row doesn't tell you, say
`unread`. Nothing in this prompt is an example to copy.

A scraper pulled these posts for a standing feed. Sift them.

## THE ONE TEST — above everything else
**Would a person watch this purely because it entertains them?**
KEEP: skits, memes, edits, stunts, fails, reactions, storytimes, chaos,
oddly-satisfying, brain rot — the stuff that gets sent to a friend.

DROP, always, no matter how big the numbers:
- anything selling: a product, a shop link, a discount, a brand account, a
  creator pitching or "obsessed with" a product
- anything teaching: tips, tutorials, routines, how-to, advice, reviews,
  "problem → solution", before/after, transformations with a method
- news, giveaways, reposted TV/film clips
- posts not in English (the LANGUAGE slot decides this, not you — just fill it honestly)

A post ABOUT the ask's topic that teaches or sells is a DROP. A post with
nothing to do with the topic that the ask's person would laugh at is a KEEP.
An empty or near-empty caption with big numbers is normal for entertainment —
that alone is never a reason to drop; mark WHAT as `unread` and keep it.

## WHOSE SCROLL THIS IS
{ask}

## KEEP (this feed's own rule)
{keep_rule}

## DROP (this feed's own rule)
{drop_rule}

## THE FORMAT BANK — the only format names that exist
{formats}

## THE POSTS
{posts}

## Return — JSON only: one object per post, same order, these slots
```json
[{"N": 1,
  "LANGUAGE": "the caption's language as a 2-letter code; \"none\" when there are no real words",
  "KEEP": true,
  "KIND": "one of: skit | meme | edit | stunt | fail | reaction | storytime | satisfying | chaos | other-entertainment | selling | teaching | other-junk",
  "WHAT": "under 14 words — what this post is, in plain words, from the caption; or \"unread\"",
  "FORMAT": "an id from the format bank ONLY if the caption makes it plain; otherwise \"unread\"",
  "WHY": "under 14 words — why it's in, or why it's out"}]
```
