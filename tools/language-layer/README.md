# language-layer — the customer-language query engine

The query over a brand's customer-language banks: rows in, filtered and ranked
rows out, per stage, provenance travelling on every row. It holds no stage map
and no brand — each chain hands in its own map (see
`tools/video-teardown/machine/language.py`).

    python3 query_language.py --brand <brand> --avatars
    python3 query_language.py --brand <brand> --stage hooks --profile <chain-profile>.json
    python3 query_language.py --brand <brand> --unused      # rows never used in an asset
    python3 query_language.py --brand <brand> --used-log    # every used row, the asset, where

Banks live at `brands/<brand>/core-avatars/<avatar>/language/*.json`
(`brands/_TEMPLATE/` shows the shape). Every rendered row carries its id in
[brackets], so a stage can cite what it used. Rows marked `retired` or `burned`
never come back.

## The used lane

`<avatar>/language/used/` holds one file per asset a chain wrote. It is a
record of use, never bank rows — the engine skips it when it loads the bank,
and no bank row is ever edited.

```json
{"schema": 1, "kind": "language-used",
 "asset": "<the ad's name once named, else the run + leaf label>",
 "run": "<the run folder>", "chain": "new-video | variation-video | framework",
 "written": "YYYY-MM-DD", "state": "drafted | shipped",
 "used": [{"row_id": "<bank row id>", "text": "<the words>",
           "where": "3 | 4b | 4d | 4e | 4g | 5", "how": "cited | matched",
           "results": null}]}
```

`cited` = a stage named the row in its `LANGUAGE USED` block; `matched` = the
words appear verbatim in the brief. `results` is filled from per-ad spend and
purchases joined on the ad name. The video chain's `mark_used.py` (stage 5u)
writes these files; its hooks query asks for unused rows first.

    python3 tests/test_used_lane.py

## Awareness, sophistication, origin — and repeats

Rows can carry the doctrine's awareness level (read in context — who said it,
where, in answer to what), a sophistication signal, the lane their words point
to, `origin` (internal: our own relationship with the customer and any
property where the brand is clearly named; external: everyone else's spaces)
and `voice` (audience or brand-written). `tools/label.py sample|apply` writes
them; `query(awareness=…)` reads them. Identical lines collapse when a query
answers ("said N× in this bank") and the count ranks like likes. A brand's own
accounts go in `brands/<brand>/channels/own-accounts.json`.
`tools/check_names.py --brand <b>` checks row and source ids against the
naming standard.
