# OFFER — {offer_id}
### Built: {date}

> Built by `offer-agent`. Validate with `offer.py validate`, emit with `to-json`.
> THE ENVELOPE IS HUMAN-SET AND READ-ONLY HERE. No active envelope is a HARD STOP —
> absence of bounds is not an open field, it means nobody has decided what the brand
> can afford. SHOW THE MARGIN: arithmetic nobody can check is arithmetic nobody checked.

---

## METADATA

| Field | Value |
|---|---|
| Offer id | {offer_id} |
| Brand | |
| Avatar id | (AV-01 or AV-01.a — who this is for) |
| Window | (start - end) |
| Built by | |

---

## ENVELOPE

Copied from the human-set policy. Read-only. If there is no active envelope, STOP.

- **floor_margin_pct**:
- **max_discount_pct**:
- **allowed_terms**:
- **never_bundle**:
- **envelope_active**: yes | no

## PROVENANCE

- **finding**: the finding id whose evidence says customers want this
- **competitor**: the specimen id or dated snapshot that frames it
- **note**: (if either is "none", say why — a genuine first move in a category is rare)

## STRUCTURE

- **included**: what the customer actually gets
- **price**:
- **terms**:
- **risk_reversal**:

## MARGIN MATH

Every cell. Missing cost data stops the sheet — it does not get estimated.
Delete this instruction line.

| Unit price | Unit cost | COGS | Discount pct | Net take | Contribution | Margin pct |
|---|---|---|---|---|---|---|
| | | | | | | |

## ENVELOPE CHECK

One row per bound. Any BREACH stops here and escalates. Delete this instruction line.

| Bound | Envelope says | This offer | Verdict |
|---|---|---|---|
| floor_margin_pct | | | PASS \| BREACH |

## COLLISION

- **live_offers**: what else is running, with avatars and windows
- **overlap**: none | sequenced | deliberate
- **cannibalisation**: what this takes from
