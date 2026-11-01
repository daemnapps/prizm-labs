# Feed plan — v3

**Guard, read first.** Nothing in this prompt is an example to copy. Every
search, hashtag and name you return must come from THE ASK below and from how
real people label that content on each platform — never from this prompt's own
wording, and never invented to fill a slot. An empty slot is a correct answer.

## WHAT THIS FEED IS — the standing rule, above any ask
**Pure entertainment.** The posts people watch because they want to watch
them — the scroll itself. Skits, memes, edits, stunts, fails, reactions,
oddly-satisfying, storytimes, chaos, brain rot. Things that get SENT to a
friend.

**Never:** anything selling a product, anything teaching, tips, tutorials,
routines, reviews, "problem → solution", before/after, brand accounts,
creators pitching. If a search would mostly return people solving a problem or
recommending a thing, it is the WRONG search — even if the ask mentions a
problem or a product. The ask tells you WHOSE scroll this is; your job is to
find what that person watches for fun, not content about their problem.

The marketer reading this feed rebuilds entertainment FORMATS as ads. He
already has every ad and every how-to he needs.

## THE ASK
{ask}

## How to think
- Start from the PERSON in the ask: their age, humor, subcultures, the
  in-jokes and slang of their corner of the internet. Search for that.
- Search the way the people who POST it label it. Meme pages and skit creators
  use their community's own tags and slang, never a marketer's description.
- Prefer the niche room over the head term. The head term returns everything.
- Hashtags are one word, no `#`, no spaces. Searches are 2–5 plain words.
- Instagram can only be searched by hashtag. YouTube and TikTok take phrases.
- When the ask is an avatar card, read it for WHO the person is — age, culture,
  city, music, sport, humor. Ignore its product, pain and angle lines entirely;
  they describe what we sell him, not what he watches.
- If the ask names accounts, put them in ACCOUNTS. Never guess a handle.

## Return — JSON only, these slots, nothing else
```json
{
 "NAME": "2-4 word kebab-case feed name, says whose scroll or what kind of entertainment",
 "TITLE": "the feed's plain-English title, under 8 words",
 "WHOSE_SCROLL": "one sentence: the person whose feed this imitates",
 "TIKTOK_SEARCHES": ["3-6 phrases"],
 "TIKTOK_HASHTAGS": ["3-6 hashtags"],
 "INSTAGRAM_HASHTAGS": ["3-6 hashtags"],
 "YOUTUBE_SEARCHES": ["2-4 phrases"],
 "ACCOUNTS": [{"platform": "tiktok|instagram", "handle": "only handles named in the ask"}],
 "LANGUAGES": ["2-letter codes of the languages this person actually scrolls in — from the ask only; English-only unless the ask says otherwise"],
 "KEEP_RULE": "one sentence: what a post must BE to belong — in entertainment terms",
 "DROP_RULE": "one sentence: the lookalike junk these searches will also return, to throw out"
}
```
