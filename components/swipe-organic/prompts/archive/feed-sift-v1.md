# Feed sift — v1

**Guard, read first.** Judge only the posts listed below, only from what each
row actually says. Do not invent what a video shows — you are reading a
caption, hashtags and numbers, not the video. When the row doesn't tell you,
say `unread`. Nothing in this prompt is an example to copy.

A scraper pulled these posts for a standing feed. Searches return junk.
Sift them.

## WHAT THE FEED IS FOR
{ask}

## KEEP
{keep_rule}

## DROP
{drop_rule}

Also always drop: ads and shop posts, reposts of TV/film clips, giveaways,
posts not in English unless the ask says otherwise, and anything where the
caption gives no sign it belongs.

## THE FORMAT BANK — the only format names that exist
{formats}

## THE POSTS
{posts}

## Return — JSON only: one object per post, same order, these slots
```json
[{"N": 1,
  "KEEP": true,
  "WHAT": "under 14 words — what this post is, in plain words, from the caption",
  "FORMAT": "an id from the format bank ONLY if the caption makes it plain; otherwise \"unread\"",
  "WHY": "under 14 words — why it belongs in this feed, or why it's out"}]
```
