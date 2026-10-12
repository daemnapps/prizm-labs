*v1 (2026-09-28, Damon: "The awareness map has only to do with the awareness levels. The format, product, cast, structure, all of that stays locked." And: "Once you've hit a winner, regardless of where it's at, you're going to control for that existing awareness stage for sure. In this, we want to also do the other awareness stages, and then each of those is going to go through the rest of its writing process.")*

Here is the doctrine read of this ad, as it was swiped (its framework, the sections it carries with their spans, the awareness it enters and exits on, the sophistication signature, the techniques): {doctrine_read}
Here is the reading of this ad (its lane, its opening beat, the awareness it enters on): {source_reading}
Here is the audience read (the avatar, the funnel, and the market state: awareness, sophistication, what the market leads with): {audience_read}
Here is the control, the proven ad's own script, unchanged: {baseline_injection}
Here is its replication spec, the construct of this script: {replication_spec}
Here are the five awareness levels, each with what it must and must not do:
{awareness_levels}
Here are the sections, what each one does, the techniques that build it, and the awareness levels it is needed at and usually skipped at:
{sections}
Here are the five sophistication stages:
{sophistication_stages}

# 4m · THE AWARENESS MAP

This ad already won. You are laying out the variation tree it grows into: one
branch for every awareness level. Each branch is later written through the
rest of the chain in its own runs: six hooks, then placement, expansion,
close, audit, spice and a brief for each hook. Your job is only the map.

**Only awareness moves.** The format, the product, the cast and the
structure stay locked. At each level you decide two things and nothing else:
what the opening speaks to, and which sections the ad carries.

## 1 · THE CONTROL LEVEL

The control is the level this ad enters on in the doctrine read (its
`awareness` → `entry`). It is cited, never improved. If the reading or the
audience read names a different level, print it and why, and still take the
doctrine read's entry as the control.

Print:
`CONTROL LEVEL: <level>`
`OTHER READS: <reading's level> (reading) · <audience read's level> (audience)`
`MARKET STAGE: <the sophistication stage from the audience read>`

## 2 · THE FIVE BRANCHES

For each level, in this order: unaware, problem-aware, solution-aware,
product-aware, most-aware. Print:

**<LEVEL>**`  (CONTROL)` on the control level only
- **The opening speaks to:** what the hook's content is at this level, taken
  from the Hook row of the sections above and this level's row in the
  awareness levels. Say it about this ad: its product, its avatar, its
  proven opening.
- **Sections, in order:** the section ids this branch carries.
- **Kept:** the control's sections this level keeps.
- **Added:** sections the control does not carry that this level needs.
  Each one cites the sections row that calls for it (`needed at`).
- **Dropped:** the control's sections this level does not call for. Each
  one cites the row (`usually skipped at`) or this level's must-not.
- **Product enters:** the earliest beat the level allows, from its "where
  the ad may begin" and "must not".

**How to decide the sections:**

1. **The control level's branch is the control, unchanged.** Its sections
   are exactly the ones the doctrine read says the ad carries, in that
   order, with repeats. Nothing is added or dropped at the control level.
2. **At every other level, start from the control's sections, in the
   control's order.** Keep each one the level allows. Drop each one the
   sections list marks `usually skipped` at this level, or that breaks this
   level's must-not. Add each section the list marks `needed` at this level
   that the control does not carry.
3. **Place added sections where the level's order needs them,** and never
   move a kept section out of the control's order. An added opening section
   (identification at unaware, for example) goes first. An added close
   section (offer, urgency, objections) goes before the last call to action.
4. **The market's stage counts.** At sophistication stage 3 or higher, the
   sections list says the unique mechanism is needed at every level. Carry it
   at every level where the stage calls for it, and say so.
5. **Use only section ids the sections list carries.** Never invent one, and
   never rename one.
6. **The hook and the call to action are carried at every level.**

## 3 · THE MAP, FOR THE MACHINE

End with exactly one fenced json block, and nothing after it:

```json
{
  "control_level": "<level>",
  "source_entry": "<the doctrine read's entry>",
  "market_stage": "<stage-n or null>",
  "levels": [
    {
      "level": "unaware",
      "is_control": false,
      "opening": "<what the opening speaks to, one line>",
      "sections": ["<id>", "..."],
      "kept": ["<id>", "..."],
      "added": [{"id": "<id>", "why": "<the row it cites>"}],
      "dropped": [{"id": "<id>", "why": "<the row or the must-not it cites>"}],
      "product_enters": "<one line>"
    }
  ]
}
```

The five levels go in the order above, each exactly once. `sections` is the
full ordered list the branch carries.
