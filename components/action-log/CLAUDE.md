# action-log — every change to the business, one entry, every brand

**action-log** — the one record of every change that touches the business: budget, bid, status, created or paused,
rule on/off, approved, went live, scheduled, price, offer, hand-off, desk call, queue change. Any brand: the brand id
is a field. Each entry: when · who or which tool · brand id · object (type, id, name, brief) · before → after · why
(the owner's own words when it was his go) · what the platform answered.

**The door:** `action_log.py add …` (or `append()` from code) is the only way in. Append-only: each entry carries the
hash of the one before it, so `action_log.py verify` catches any edit or deletion. Every tool can read it
(`action_log.py list`).

**Brought in, not started over:** `action_log.py ingest` reads the logs kept before it and adds only what is new:
media-buying `actions.jsonl` and `decisions.jsonl`, brief approvals (`runs/briefs/approved.json`), the queue's
`decisions.jsonl`, and cards that went live (a Drive mirror named in `~/.prizm/action-log.json`, never in the repo).

**Scored on its return:** `action_log.py score <id>` reads the object at 3 / 7 / 14 days from the warehouse copies
(`runs/funnel-tracking/<brand>/<date>/warehouse.json`): share of spend and how it moved, spend growth, CPA change,
and the brand's blended MER before and after (Outlier's warehouse feed). Never Meta. A launch is scored from zero.

**Named views:** the owner's own reads (filter + reads + window), saved in `runs/action-log/views.json`.

**Plane:** `runs/action-log/log.jsonl`, `runs/action-log/views.json`. **Runs by:** any writer, through the door; the
ingest runs on the job meter (switched off until the owner turns it on). **Role:** brand-operator.
**Shown:** the Studio, Ads → Ledger → "Every change, scored". **Tests:** `python3 -m unittest discover -s components/action-log/tests`.
