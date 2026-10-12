# My Feeds, hosted — the plan (2026-09-22)

Artifact: (team page)

the owner, 2026-09-22: *"how can I make my feeds a hosted tool? so that my editors
and content creators have infinite inspiration and I focus more on researching
and prompt engineering to get these outputs / briefs more on point?"*

## LIVE: route A, a static export (the owner, 1 Oct 2026; confirmed by the developer, 7 Oct 2026, triage page 10)

`feedsexport.py` writes the static, read-only export behind daemn.co/feeds/ —
no keys, so nothing on it can spend; a no-secrets scan and a size check
refuse a bad export. `desk.py` re-exports into the local site checkout after
each successful Pull; `feeds-publish.sh` commits and pushes it to the site,
by hand only — releasing to the public is a person's act, never a schedule
(O5b (export replace is deploy)). Routes B and C below (a live board behind
a URL) are not built.

## History: RULED NOT NOW (the owner, 2026-09-22) — reversed 1 Oct 2026

*"don't worry about it now then — I'll use it for brief creation at this point,
other people just need my briefs."*

That day nothing here was to be built until he said so, and hosting was not
to be re-pitched; he said so on 1 Oct (above). The plan below is the 22 Sep
plan, kept as written.

## The answer

Don't host the whole board. Split it:

| Team view — hosted, read-only | His cockpit — stays private |
|---|---|
| every feed and post, with covers | dig · pull · sift |
| search across all 5,283 posts | tear down + inject into a brand |
| the rebuild sheet on any swipe | every stage's prompt as sent, beside what came back |
| the format library | yes/no on briefs, and the team's requests |
| finished briefs, once he has said yes | the Apify spend meter |
| **Request teardown** — queues it for him, never runs | |

No keys on the team side, so nothing there can spend. That matters: Apify is at
**$__ of $__** this month, and a hosted board with live buttons is a way for
eleven people to empty it in an afternoon.

## Routes

| | What they get | Cost | Where it breaks |
|---|---|---|---|
| A · publish a page | a frozen snapshot, no video | free | never updates; 850 MB of covers will not fit |
| **B · a real URL off a Mac we own** (recommended) | the live board, behind an email allow-list | free to 50 people; the Cloudflare key is already in his Keychain | only up while that Mac is up → run it on the mini |
| C · fully off his machines | up regardless, fast anywhere | ~10¢/month for ~5 GB | nothing; just more parts — do it after B proves used |

## Steps

1. **Team view** — same board, spending buttons replaced by *Request teardown*;
   one switch decides cockpit vs team by who is looking. *An afternoon, no
   decisions needed.*
2. **An address** — Cloudflare tunnel + email allow-list. *An hour; needs his
   go-ahead, because this is the moment it is on the internet.*
3. **Move to the mini** — off the laptop. *Half a day; needs the model call below.*
4. **Let it fill itself** — nightly pull back on under a spend cap; requested
   teardowns run overnight and wait for his yes. *A day; this is where his hours
   come back.*
5. **Files to object storage** — covers and reference videos off the disk. *A day,
   once the team uses it daily.*

## The two calls only the owner can make

1. **Whose AI account do unattended runs use?** Every teardown calls a model and
   today it goes through his signed-in Claude on the laptop (`desklib.ask_model`
   shells out to the `claude` CLI). Either sign in as him on the mini, or add a
   company API key — there is no `ANTHROPIC_API_KEY` in the Keychain today.
2. **Who gets in?** The work email addresses for the allow-list.

## Inventory behind the plan

| Piece | Today | Hosted |
|---|---|---|
| posts across 25 feeds | 5,283 | as is |
| his saves | 541 | as is |
| cover images | 4,616 · 850 MB | object storage at step 5 |
| reference videos + beat strips | 519 · 4.0 GB | object storage at step 5 |
| Cloudflare account + key | in the Keychain | ready |
| scraping account | $__ of $__ | cap before the team can request |
| model login for unattended runs | his, on the laptop | his call |
| sweeping his IG saves | his own browser | stays manual — Instagram allows no other door |

Source page: `context/artifacts.md` records the artifact; this file is its mirror.
