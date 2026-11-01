# strategy/

The brand's plan: calendar/, angles.json (the one angle source) and goals/ (KPIs per function).

---

## strategy — the brand's claims

**`angles.json` is the one angle source.** Every page, ad and email names the
angle it argues; reports group on it. Nothing else in the brand folder may hold
a second list of angles.

## Where this sits in the model

An asset is one point in four independent axes
(`components/naming/MODEL.md`):

```
AVATAR  ×  ANGLE  ×  CHANNEL  ×  FORMAT  =  an asset
 who        what       where        how
            ^^^^
        this folder
```

The other three live elsewhere, and that separation is the whole point:

| Axis | Lives in | Brand-scoped? |
|---|---|---|
| Avatar | `core-avatars/` in this folder's parent | per brand |
| **Angle** | **`strategy/angles.json` — here** | **per brand** |
| Channel | `copy/bank/channel-map.json` | shared |
| Format | 25 banks, one per asset type — `components/naming/registry.json` | mixed |

## The three rules that keep this folder honest

1. **An angle is channel-free and format-free.** The same claim runs as a paid
   static, an organic video, an email and a landing page. **If it only works in
   one container, it is a format, not an angle.** This is the failure that
   filled <brand>'s bank with slide layouts — nine of its twenty entries turned
   out to be formats or channel observations.
2. **An angle is aimed at exactly ONE core avatar**, and may serve several
   sub-avatars — declared on the asset, never as a second angle. The same claim
   aimed at a narrower person is a sub-avatar, not a new row; two rows split the
   reporting on one claim.
3. **Only the brand's owner signs.** `status: draft` is the honest default and
   is not a demotion. A session may propose a candidate. A session may never
   sign, and may never write a receipt it has not opened — see
   `components/naming/FORMATS.md`, "A borrowed name with a new meaning".

## Before adding a row, ask

- Can I say it as one sentence a customer could **agree or disagree with**? If
  not, it is not an angle.
- Would it still work as an email? As a landing page? If not, it is a format.
- Is it the same claim as an existing row, aimed at a narrower person? Then it
  is a sub-avatar on that row.
- Does its receipt **resolve**, and does the source actually say what the claim
  says? Open it and check.
