# Stock check (inside promo-pack)

Say: **"check stock for the <moment> pack"**.

1. Read the stock runway for every item the offer sells or gives away, once at today's pace and once at the pace
   the offer will bring (a free gift on most orders moves the gift at the main item's pace).
2. Save the read as JSON rows: sku, name, available, backup, per_day, runs_out, reorder_by, status.
3. Build the pack with `--stock <that file>`.

A `LATE` or `ORDER THIS WEEK` item, or one that runs out inside the window, sits on top of the pack as a blocker
for the brand-operator, with its reorder date. Two items with the same count may be one shared part in the
warehouse: the pack says so, and the brand-operator confirms.

The stock runway itself is not in the toolkit yet; any read in that shape works.
