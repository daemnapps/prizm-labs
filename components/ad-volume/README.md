# Ad volume

Hundreds of video ads a day per brand: micro dramas, song ads, AI skits. Volume and attention first, polish second;
the numbers decide what stays (`context` ruling 2026-11-15: swipes are inputs, our ads are outputs, volume first).

One command runs the day, with no hand steps between the stages:

```
python3 components/ad-volume/volume.py day <brand> [<brand> ...] --n 20      # writing → takes → versions → Studio → approval card (dry run)
python3 components/ad-volume/volume.py day <brand> --n 20 --go              # the same, and the cards are filed on the approval page
python3 components/ad-volume/volume.py price --concepts 40 --versions 5     # the cost table, priced live from the Higgsfield cost command
```

The stages also run one at a time (`plan`, `make`, `edit`, `studio`, `file`; `--help`).

## How one concept becomes many ads

| Stage | What it does | Where you see it |
|---|---|---|
| Writing (`plan`) | N concepts from the brand's winner (`brands/<brand>/winner.json`, its teardown), the language bank and the kit, spread across the formats in `formats/`. Each concept: beats, lines, cast from the kit, a take prompt of our beats only, 5 hooks, an end card, the bank ids used. Runs on the signed-in Claude plan (`prompts/concepts.md`). | The batch page: every writing prompt and its raw output |
| Take (`make`) | One take per concept at the test tier (`tiers.json`): the kit's cast, product and set pictures go in as references, so no new start picture is drawn. | The concept's stage page: the take prompt, references, route, credits, the take |
| Edit (`edit`) | Control + one version per hook: the hook's words for the first 2.5 s, the end card for the last 2 s, 1080×1920, -14 LUFS. | The Studio's Versions tab |
| Studio (`studio`) | Each concept is a production in the Video Studio (`vol-<date>-<brand>-cNN`) with its stage page (`stages.html`); the batch has `vol-<date>-<brand>/index.html`. | Studio menu; `/files/vol-<date>-<brand>/index.html` |
| Approval (`file`) | One card per concept, every version inside, through meta-upload's `feed_video.file_master`. Dry run unless `--go`. Approve stays the owner's click. | The approval page |

A concept of 5 hooks is 6 ads (control + 5). 40 concepts a brand = 240 ads a brand a day.

## Formats

`formats/micro-drama.json`, `formats/song-ad.json`, `formats/ai-skit.json`: beats with timing, cast roles, camera,
sound and the axes concepts vary on. A new format is a new file there; the writing picks it up.

## Tiers and money

| Tier | Route (house model) | Credits per 12 s take (read 15 Nov 2026) |
|---|---|---|
| `test` (default) | Wan 3.0, 480p, reference mode (house `clips.take_backup` model) | 12 |
| `test-seedance` | Seedance 2.5, 480p, draft (house `clips.take`) | 36 |
| `finish` | Seedance 2.5, 1080p — winners only | 192 |

Wan 3.0 720p 21, 1080p 42; Seedance 2.5 720p 84. Credits per dollar: 20 on the account's auto-refill, 17.39 on the
4,000 pack. `price` reads every number live.

The spend floor (`tiers.json` `spend_floor_credits`): the make step reads the balance before every take and holds the
take that would cross it. The account tops itself up with a paid refill below its refill line, so spending past the
floor is a purchase and is the owner's call (`--floor`). `--max-credits` caps one run.

## What the test tier leaves out (done on a winner, through the full production chain)

- No start picture through the 3D print and no motion chain: the take is made from the kit's pictures as references.
- Voices are the take's own; our voice reads come with the finish.
- Song ads are sung by the take itself; the song route in the model house makes the winner's song.
- No captions of the spoken lines (word timings are a finish step); hook words and the end card are laid.
- Covers: the filer reads the Studio's covers; a card with none is filed held on the cover check.

## Brand kit

`brands/<brand>/volume.json`: `avatar`, `product` (the approval card's product slug), `product_name`, `product_use`,
`brief`, `cast` (name, group = one demographic, file, looks, role), `product_refs`, `sets`. Files are written as
`Shared Assets/...` labels and found on the mount.
