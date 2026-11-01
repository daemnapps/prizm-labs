# briefs — ask for a brief by what it is

## How to use it → https://dashboard.the company.com/atlas#c-components-briefs

A brief is a **projection of a record**. The record is the expensive half; the
brief is what you print from it. A teardown run costs ~25 minutes, the brief off
the end of it 21 seconds — so a new brief style is one file that prints against
every record you already have.

```
python3 tools/briefs.py list                  every style, by status and state
python3 tools/briefs.py find --asset video    everything that makes a video
python3 tools/briefs.py find --asset video --actor creator
python3 tools/briefs.py path video--creator   where that prompt lives today
python3 tools/briefs.py records               what each style reads FROM
python3 tools/briefs.py check                 do the declared paths still exist
python3 tools/briefs.py retire                the kill list, with its evidence
```

Free — no model, no credential, no network.

## It registers; it does not move

Every style stays where its machine keeps it. Establishing this folder moved,
renamed and rewired **nothing** — the 8 lanes that produced 412 briefs in a
fortnight keep running untouched. Styles migrate in one at a time, on the owner's
word. Same precedent as `components/intake`, which reads every swipe as one
list while the swipe folders stay the tools they always were.

## The naming rule

    brief--<asset>--<actor>.md

The stage number leaves the filename. A brief is named for what it is and who
acts on it — not for where in some chain it sat. `copywriter` and
`email-production` both write `stage9--brief.md` today; that is the fault this
rule closes.

## What is in the register

20 styles: 18 approved and live, 2 draft and parked. Every `live` carries a run count and a date — a style that
has produced nothing in 30 days is `parked`, whatever its config claims.

`retire` lists superseded prompts still sitting in live folders. **the owner rules
that list.** Archive into the folder's own `archive/`, never delete — and note
the one marked ⚠: a byte-identical copy of it is pinned by
`components/chain-runner/chains/video-teardown/chain.json`.

Research is deliberately not here — it becomes its own component.
