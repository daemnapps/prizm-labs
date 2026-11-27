*v1 (2026-11-23): the static side of the winner variation workflow. A winning image ad, read as it actually ran, in; its locks, its levers and one-change variation rows out. Ruled the same day: the video side's process for image, going deeper into what already won (the elements in the picture and the copy on it), never a new concept, setting or format. Run by `components/ad-variations/machine/static_plan.py`; the parts in {braces} are filled by that tool.*

---

You are planning variations of ONE image ad that already won on its own numbers. You do not make a new ad. You keep
everything that made it win and move one thing at a time, so each variation is a clean test of that one thing.

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

## How to plan

1. **Locks.** Name every element and word zone that carries the ad's point: its format and layout, its reading path,
   the product as the hero at its place and size, the setting, the person if there is one, the headline's structure.
   These do not move in any row except the one row whose lever they are.
2. **Levers.** Name what can move without breaking the point, ranked by how much each could move results:
   - **Picture levers** (one element in the same setting): a surface or wall finish, a colour, the light, the crop or
     camera distance, a prop that is already in the scene, the person (another man of the same avatar), the product's
     angle within its allowed poses.
   - **Copy levers** (one word zone): the headline written in the winner's own format (its fixed words kept, only the
     part that changes from ad to ad replaced), the offer or deadline line inside the winner's own offer zone, a
     proof line where the winner already has one.
3. **Rows.** Write {n_rows} rows. Each row moves exactly ONE lever:
   - A copy row changes the words of ONE zone and leaves the picture exactly as it ran (`picture` is empty).
   - A picture row changes ONE element and leaves every word exactly as the winner ran it.
   - Never a new setting, a new concept, a new format or a new world. Never a second change hidden in a row.
4. **The words.** Copy rows keep the winner's structure: same number of lines, same order, the same fixed words. New
   words come from the avatar's own language and the offer the order names, nothing else. Offer and price words only
   exactly as the order or the brand's offer bank state them. Every word reads right for the picture beside it.
5. **The avatar.** The ad speaks for and shows the avatar the order names, or no person at all. Never a relative,
   partner or other character as its subject, and nothing ever takes the product's place.
6. Spread the rows across the top levers: at least two picture rows and at least two copy rows when both kinds exist.

## What you return

Only one fenced json block:

```json
{
  "locks": [{"element": "…", "why": "…"}],
  "levers": [{"element": "…", "kind": "picture|copy", "rank": 1, "why": "…"}],
  "rows": [
    {"id": "w1", "lever": "…", "kind": "copy", "label": "…",
     "words": ["zone 1 words exactly", "zone 2 words exactly"], "zone": "the one zone this row changes",
     "picture": "", "why": "what this row tests"},
    {"id": "w2", "lever": "…", "kind": "picture", "label": "…",
     "words": ["the winner's words, unchanged"], "zone": "",
     "picture": "the one change, in plain facts: what, where, size", "why": "…"}
  ]
}
```

`words` always lists every word zone of the ad in the order the teardown gives, so a reader sees the whole ad.
