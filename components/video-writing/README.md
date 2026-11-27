# video-writing

Station 2 of the video line: a finished teardown in, our version written for the brand out
(injection, hooks, script, audit, spice, the brief production takes).

Owner: the owner


## Winner match

Every swipe is matched with a banked winner before writing: the winner gives what we say, the swipe gives the form.
Both sides are read from their own teardowns on the same trait sheet (`machine/winner_index.py`): awareness in and
out, format, cast, framework, sections in order, sophistication, length, pace, tone, hook, sound.

- `machine/winner_index.py build --brand <b>` writes `runs/winners/<b>/winner-index.json` and `.md`: one record per
  banked winner (what it sells and argues, hook, traits, proof from the registry and the bank — sales, spend, cost
  per sale, return, months it ran — post date) and a call: keep · watch (lost money, still matched) · fold (a copy of
  another winner, removed from the bank) · retire (not a winner: no sales on record). Age retires nothing. No model
  call, no spend.
- `machine/winner_match.py rank <swipe run>` marks every winner ✓ / ~ / ✗ per trait, scores the matrix out of 100
  (`WEIGHTS`), gives one plain reason per winner and never picks (`pick` stays empty; under 55 it says no banked
  winner carries the shape). The owner picks; `switch <swipe run> <winner run> --why "..."` then opens
  `<swipe run>--w-<winner>` and runs the writing chain (spends model money).
- **On the chain (stage 2w):** the writing runs the match first on every swipe and waits on the winner lane until a
  person picks, on the Studio board (Orders → Pick) or `winner_match.py pick <run> <winner> --why "..."`.
- `machine/winner_page.py --brand <b> --swipe <run> --out <page> --md <copy>` builds the owner's page from both.
