# Triage definitions: red tests (domain 2, draft)

The item: one declared test suite that is red (or timed out) on main, from the red-test reporter's record.

## Pass 1 — still true?
The source's own check: does the suite still fail at the commit under review? You may run it once (python3 <suite>, timeout 300 s) in the read-only worktree.

## Pass 2 — cause class and blocked_by (two fields; the team "ok" on triage design issue #3, 2026-10-02, 4b36a7a90)
`cause` — what is wrong, exactly one (split a suite into a/b rows only if it truly fails for two independent reasons):
- REAL: the code under test is wrong and the test is right.
- STALE: the test pins something that was deliberately changed (a later commit changed the behaviour or text on purpose).
- ENV: the failure depends on the machine, date/time, load, or live data rather than the code.

`blocked_by` — what stops the fix from starting, separately: `null`, or a card awaiting approval (`card:<id>`), or a pending decision (`decision:<who>: <the question>`). A decision is never a cause: a STALE suite whose re-pin waits on an approval is `cause: STALE, blocked_by: card:WM-106`.

## Pass 3 — group by the one action that clears it (fix_group)
A short kebab slug naming the ACTION. Reuse it for every item that action clears. Prefer naming the causing commit or shared mechanism, e.g. `fix-after-fc403711c`, `repin-after-d20151bec`, `approve-TI-21`, `relative-dates-in-tests`. One-offs: `unique`.

## Pass 4 — priority (the team "ok" on design issue #6, 2026-10-02, 4b36a7a90)
- P0: REAL and on a live path, with the evidence named (a run on record in the last 30 days, a grant on the mini, or a person's live use). Without that evidence it is P1, whatever the words say.
- P1: REAL but not live, or it blocks merges (a gate suite).
- P2: STALE (a re-pin).
- P3: ENV (flaky; fix the test's dependence).
- Age: a suite red more than 7 days with no card goes up one level, never past P1.
- Actions are ranked, not items: an action's score is the items it clears, weighted P0 8 · P1 4 · P2 2 · P3 1.

## Pass 5 — the three whos, in this order (the team, 2026-10-02: "Who can address directly (including in one batch); Who needs to make decision (if its different than #1); Who it impacts"; then "Put decides first before can do it")
1. decides: whoever `blocked_by` names, whose yes is needed before work starts; null if nobody's.
2. can_do: consider the list's TRIAGE OWNER first (the team: "even if the owners can do it, we should first consider if steph (the triage lead) can do it for them"; generalised the same day: "steph is replaced generally by the triage owner. Who might differ depending on who runs it generally"). For red tests the triage owner is DAYU, who sits in the lead seat and can card and dispatch. Tag each item with one of:
   - now: the triage owner can do it alone, today: for a red test, a re-pin or test fix the team cards and dispatches, or an approval the team types.
   - after: the triage owner can do it once someone else's ruling lands, because the work just applies it.
   - draft: the triage owner cards or prepares it, and the code's owner lands it or must say yes (their live code, their work in flight).
   - owner: only the code's owner can do it (a personal copy only they can rebuild, their account, a design call).
   Name an owner only for draft and owner items, always with the reason. An action is "ready" only when the triage owner can do all of it alone, now.
3. impacted: who feels the failure or the fix but isn't asked; an owner whose code the triage owner changes is told here.
The triage owner triages every action first and may close an item already fixed, with its evidence.
