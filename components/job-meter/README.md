# job-meter

Runs the jobs that should happen on their own every night, holds each to a money cap, and keeps one record of every run: when, how long, the model, what it spent.

You say "run the nightly jobs" or "what did the jobs cost this month". Claude runs it. You never type a command.

## What it gives you

| | |
|---|---|
| **One list** | Every scheduled job in one private file: what it does, when, the model, the cap |
| **Caps** | A job that spends reads its meter first. Meter unreadable, or not enough left this month: it does not run |
| **One ledger** | One line per job per brand per run: minutes, how it ended, what it spent |
| **The bill** | `show` adds it up per job for the last N days |
| **Model per job** | `model-map.json`: the cheapest model that does each kind of job well |
| **GPU** | `gpu.json`: rented graphics machines and whether any job needs one yet |

## Meters it reads

| Meter | What it reads |
|---|---|
| `apify` | The scraping account's own used and allowed dollars this cycle |
| `adplexity` | The ad-library client's own call log, this calendar month, priced per the plan |

## The job list

Private: it names brands and folders, so it lives with the person's own machine setup, never here.

```json
{
 "where": "this Mac", "at": "04:00 daily", "ledger": "~/somewhere/ledger.jsonl",
 "jobs": [
  {"id": "signals", "what": "What good looks like", "brands": ["brand_a"], "model": "none",
   "cwd": "<repo>", "cmd": ["{python}", "components/meta-upload/signals.py", "--brand", "{brand}"], "timeout_min": 20},
  {"id": "organic-feeds", "model": "claude-haiku-5-5", "meter": {"kind": "apify"}, "cap_usd": 5, "floor_usd": 20,
   "cwd": "<repo>/components/swipe-organic", "cmd": ["{python}", "daily.py", "--cap", "{cap}"]}
 ]
}
```

Fill-ins: `{brand}`, `{today}`, `{yesterday}`, `{days_ago:N}`, `{cap}`, `{python}`. `every`: `daily`, `weekly:mon`, `monthly:1`. `off: true` keeps a job listed but stopped.

A job ends 0 (done), 3 (skipped on purpose) or anything else (failed).

## Rules

- Numbers come from the warehouse inside each job. Nothing here calls an ad platform.
- No key value is read, printed or stored here. The launcher fills the environment by name.
- Never spends blind: no meter reading, no run.

## Keys this tool needs

None of its own. `APIFY_TOKEN` is read only to check the scraping meter.
