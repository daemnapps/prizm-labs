*v2 (2026-11-24): v1's rows moved the light, the steam and the camera by a step, and the results looked like the same picture. v2: every row reads as a different ad at feed size; when the order names a moment, the winner is first re-dressed for it (the control) and every row builds on the control, with the moment seen as well as read; copy rows write from the avatar's own sentences; the product's own rules are in front of the planner. Run by `components/ad-variations/machine/static_plan.py`; the parts in {braces} are filled by that tool.*

---

You are planning variations of ONE image ad that already won on its own numbers. You do not make a new ad. You keep
everything that made it win, go deeper into it, and move one thing at a time. Each variation is a clean test of that one
thing, and a man scrolling past on a phone sees that it is a different ad.

## The winner, as it ran

Its numbers: {numbers}

The teardown of the exact picture that ran (every element, zone and word, measured off the picture):
{teardown}

Its copy architecture (each word zone, what it says, its job, its measure):
{copy}

The 3D set it was printed from (the set's props, signage and what was kept), when it has one:
{set}

## The order behind this round

{ask}

## The brand's rules

{rules}

## The product's own rules

{product}

## The avatar's own sentences

{language}

## How to plan

0. **The control.** When the order names a moment (a holiday, a sale), the winner's old moment is replaced first: same
   ad, its moment words swapped for the order's, and one thing in the scene that shows the moment without a word being
   read (the thing a person puts up, hangs, wraps or finds in that place at that time of year, large enough to see at
   feed size). That re-dressed winner is the control and every row builds on it. With no moment, the control is the
   winner exactly as it ran.

1. **Locks.** Name every element and word zone that carries the ad's point: its format and layout, its reading path,
   the product as the hero at its place and size, the setting, the person if there is one, the headline's structure.
   These do not move in any row except the one row whose lever they are.
2. **Levers.** Name what can move without breaking the point, ranked by how much each could move results:
   - **Picture levers** (one element in the same setting): the moment's own object (which one, where, how big), a
     surface or wall material, the whole ground colour, the real product's allowed companions, what the water, cloth or
     stone in the scene is doing, the person (another man of the same avatar, only when the order says one is cast).
   - **Copy levers** (one word zone): the headline written in the winner's own format (its fixed words kept, only the
     part that changes from ad to ad replaced), the offer or deadline line inside the winner's own offer zone, a
     proof line where the winner already has one.
3. **Rows.** Write {n_rows} rows. Each row moves exactly ONE lever:
   - A copy row changes the words of ONE zone and leaves the control's picture alone (`picture` is empty). That zone is
     one a reader takes in first or second (the headline, the hook line, the main bubble), and its new line says a
     different thing, not the same thing in other words. A swapped emoji or a synonym is not a row.
   - A picture row changes ONE element and leaves every word of the control.
   - **The feed test.** Shrink the control and the row to 2 cm wide, side by side. If they look like the same picture
     the row fails. Light, steam, haze, grade, exposure, a small scale change, a tilt or a crop always fail. A copy row
     passes when its line is the one read first and it says something new.
   - A new colour comes from the brand's palette or from the winner's own colours, never from outside both.
   - Never a new setting, a new concept, a new format or a new world. Never a second change hidden in a row.
4. **The words.** Copy rows keep the winner's structure: same number of lines, same order, the same fixed words. New
   words come from the avatar's own sentences above and the offer the order names, nothing else; a row that uses one
   cites its id in `from`. One clear point that can be read in a second, never clever for its own sake. Read the
   new line with the picture and the lines that sit next to it: if a stranger would ask what it means there, it fails. A
   line set as a person's own post is something that person would type. Offer and price words only
   exactly as the order or the brand's offer bank state them. Every word reads right for the picture beside it.
5. **The avatar.** The ad speaks for and shows the avatar the order names, or no person at all. Never a relative,
   partner or other character as its subject, and nothing ever takes the product's place. The product rests only as the
   winner shows it or as its own rules allow; its place and size are a lock.
6. Spread the rows across the top levers: at least two picture rows and at least two copy rows when both kinds exist. No row repeats one on the already-made list in
   the order.

## What you return

Only one fenced json block:

```json
{
  "locks": [{"element": "…", "why": "…"}],
  "control": {"words": ["every zone, with the moment's words in"], "picture": "what shows the moment, in plain facts: what, where, size (empty when no moment)"},
  "levers": [{"element": "…", "kind": "picture|copy", "rank": 1, "why": "…"}],
  "rows": [
    {"id": "w1", "lever": "…", "kind": "copy", "label": "…",
     "words": ["zone 1 words exactly", "zone 2 words exactly"], "zone": "the one zone this row changes",
     "picture": "", "from": "language id or empty", "why": "what this row tests"},
    {"id": "w2", "lever": "…", "kind": "picture", "label": "…",
     "words": ["the control's words, unchanged"], "zone": "",
     "picture": "the one change, in plain facts: what, where, size", "why": "…"}
  ]
}
```

`words` always lists every word zone of the ad in the order the teardown gives, so a reader sees the whole ad.
