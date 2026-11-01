# intake

## How to use it → https://dashboard.the company.com/atlas#c-components-intake

One front door for every swipe. It reads the paid swipes and the organic swipes
where they already live and presents them as **one list**, each swipe saying
where it came from, what kind of asset it is, and which teardown it goes to.

It does not tear anything down, fetch anything, or label anything — and it
costs nothing to run.

## Run it

```
python3 components/intake/tools/run.py --brand <brand> --dry-run      # counts only, writes nothing
python3 components/intake/tools/run.py --brand <brand>                # files the index
```

| flag | what it does |
|---|---|
| `--brand` | required — a real folder under `brands/`. No default. |
| `--source` | `paid` · `organic` · `own` · `competitor` |
| `--kind` | `video` · `image` · `carousel` · `copy` · `page` · `email` |
| `--label` | the run's name; default is today's date |
| `--limit N` | only the first N swipes |
| `--gates` | the elements gate: `warn` (default — files and says HELD) or `hold` (stops) |
| `--dry-run` | writes nothing; prints the counts and where it would file |

The index for a brand is **that brand's swipes plus every `shared` one** — a
competitor's ad library or a general feed belongs to no single brand, and the
pools do not say otherwise.

## What it files

`runs/intake/<brand>/<label>/`

| file | what |
|---|---|
| `summary.md` | the counts to read: source × kind × teardown, how many have no format, how many point at no asset, which labels the library does not know |
| `swipes.jsonl` | one swipe record per line |
| `check.json` | the two gates — inputs, elements |
| `run.json` | what ran, which pools it read, the counts; `model_calls: 0` |

On a hold, an earlier index in the same label folder is renamed `*.superseded` (intake#7 (same-label hold)).

## Where things go

| kind | goes to |
|---|---|
| video | video-teardown |
| image, carousel | image-teardown |
| copy (a competitor's locked copy block) | copy-teardown |
| page (a competitor's landing page) | page-teardown |
| email | email-teardown — neither pool holds an email swipe today |
| unknown (the link does not say what it is) | unrouted — counted, never guessed |

## What it reads (and never writes)

| pool file | becomes |
|---|---|
| `swipe-paid/<advertiser>/blocks.json` | one `copy` swipe per block + one `video`/`image` swipe per ad |
| `swipe-paid/<advertiser>/pages.json` | one `page` swipe per landing page, its page type as the format |
| `swipe-paid/own/<account>/ads.json` | our own ads (`source: own`); the account is matched to a brand through `brands/<brand>/meta/account.json`. A cache rebuilt by `own/ingest.py`, not in git; a default run without it skips the lane with one line, `--source own` holds |
| `swipe-paid/judgements.json` | a person's format call, laid over the ad it names |
| `swipe-organic/records/avatar-feeds/<feed>/items.json` | one swipe per post; `<brand>--…` feeds belong to that brand |
| `swipe-organic/records/swipe-videos/<code>/format.json` | the structure read for a pulled post |
| `swipe-organic/<name>/posts.json` | a pulled set of posts (images, slideshows) |

## Shape

```
intake/
  CLAUDE.md   README.md
  tools/      run.py (the one entry) · pools.py (the readers) · gates.py · paths.py
  tests/      test_intake.py · test_label_guard.py · test_pool_fixes.py
```

No `prompts/` — nothing here talks to a model.
