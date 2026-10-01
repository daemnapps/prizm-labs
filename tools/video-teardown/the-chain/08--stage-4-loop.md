# Stage 4 — the DR transformation loop

> Five prompts, not one. **Because that is how the pass actually ran** — the
> June 24 session was four exchanges with a human reviewing between each, not a
> single instruction. A monolithic prompt does all seven moves shallowly.

## The loop

```
        ┌──────────────────────────────────────────┐
        ↓                                          │
   4a placement ──► 4b hook ──► 4c expansion ──► 4d close ──► 4e audit
    (decide)       (QA gate:   (gated moves,    (objection   (SHIP /
                    all hooks   priced against   + offer)     RE-RUN x /
                    test)       the budget)                   STOP)
```

| Pass | Does | Stops for a human? |
|---|---|---|
| **4a placement** | Lane · where the product enters · awareness entry → exit · whole-asset runtime budget | No — but read it, it's one page and everything depends on it |
| **4b hook** | A control + five variants, each a line **plus scroll stopper**, citing a customer verbatim | **QA only** (changed 2026-08-18, Damon — was "human picks one"). **All approved hooks ship to test**; 4c builds one body that carries any of them and flags misfits |
| **4c expansion** | The gated moves — each earns its way in against the baseline or stays out. Length is priced against 4a's budget, never doubled by default | No |
| **4d close** | Moves 6–7. The objection line, the offer. Optional move 8 as a separate variation | No |
| **4e audit** | Seven checks against the source and the rules. Returns SHIP, RE-RUN *specific pass*, or STOP | **Yes on RE-RUN** |

## Why decomposed

1. **It matches the real pass.** Hook, then five moves in one breath, then the
   speaker restructure — three separate instructions with review between.
2. **Different inputs per pass.** The hook needs the language bank and avatar.
   The mechanics need the product file. The objection needs the objection bank.
   One prompt carrying all of it dilutes each.
3. **The hook set is a test, not a menu** (changed 2026-08-18 — was "a
   human picks one"). All approved hooks run as test cells against the
   control; the body holds the format's register so any hook can head it.
   The human gate is QA; the market makes the pick.
4. **The audit can name a target.** "Re-run 4c, the usage at 0:40 describes a
   leave-on mask" is actionable. "Improve the mechanics" is not.

## The loop rule

**Two passes maximum before a human looks at it.** If the same check fails
twice, the problem is upstream — the placement plan, the brand material, or the
format itself. A third rewrite will not fix it, and the audit is told to say so
rather than try.

## What ends the loop

- **SHIP** — seven checks pass, slots flagged rather than invented, runtime
  matches the rungs.
- **STOP** — the format can't carry it. Some formats are hooks that hand off to
  another asset. Saying so is a correct answer.

## The constraint that holds across all five

> *"That's the only change."* — June 24
> *"Don't overcomplicate or over re-write. We're just injecting."* — July 20

Every move adds a beat or swaps a line. **None restructure the source format's
spine.** 4e check 1 exists to enforce exactly this.

## Not yet true of any of this

**Stage 4 has never been run as a prompt.** It has been run twice by hand, by
Damon, and once by me on Elena's Rank 5. These five files encode those runs;
the first real execution will find things they get wrong.
