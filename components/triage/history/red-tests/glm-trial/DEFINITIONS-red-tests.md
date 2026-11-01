# Triage definitions: red tests (domain 2, draft)

The item: one declared test suite that is red (or timed out) on main, from the red-test reporter's record.

## Pass 1 — still true?
The source's own check: does the suite still fail at the commit under review? You may run it once (python3 <suite>, timeout 300 s) in the read-only worktree.

## Pass 2 — cause class (exactly one; split a suite into a/b rows only if it truly fails for two independent reasons)
- REAL: the code under test is wrong and the test is right.
- STALE: the test pins something that was deliberately changed (a later commit changed the behaviour or text on purpose).
- ENV: the failure depends on the machine, date/time, load, or live data rather than the code.
- RULING: it cannot be fixed until someone decides something (a card awaiting approval, a convention question).

## Pass 3 — group by the one action that clears it (fix_group)
A short kebab slug naming the ACTION. Reuse it for every item that action clears. Prefer naming the causing commit or shared mechanism, e.g. `fix-after-fc403711c`, `repin-after-d20151bec`, `approve-TI-21`, `relative-dates-in-tests`. One-offs: `unique`.

## Pass 4 — priority
- P0: REAL and on a live path (a person's or the mini's run crashes or gives wrong output today).
- P1: REAL but not live, or it blocks merges (a gate suite).
- P2: STALE (a re-pin).
- P3: ENV (flaky; fix the test's dependence).

## Pass 5 — lane and decider
- maker: a mechanical change any maker can do (most STALE re-pins, ENV test fixes).
- owner: the owner of the code under test decides or fixes (REAL). Name them from the component's CLAUDE.md / Residents row (components/CLAUDE.md) or the build folder's owner.
- decision: needs a ruling (RULING); name the decider.
