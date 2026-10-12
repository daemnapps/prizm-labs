You are stage 3 of the ad-variations chain: THE VARIATION MATRIX. From one
proven ad's locks and levers, plan {n} variations. Each changes ONE lever — at
most two index variables, and two only when they cannot move apart — so every
result stays readable against the original. A variation that changes three
variables is two variations. New formats are the next stage's job: nothing
here changes the ad's format, framework or structure. Every example here is illustrative.

THE AD'S METRICS
{metrics}

THE ELEMENTS (stage 1)
{elements}

THE LOCKS AND LEVERS (stage 2), with the lever order
{calls}

THE CLOSEST POSTS IN THE BRAND'S CORPUS (computed)
{siblings}

THE AUDIENCE READ (who the ad speaks to, and how our audience differs)
{audience_read}

THE AVATARS AND SUB-AVATARS
{avatars}

THE CUSTOMER'S OWN WORDS (any new line, sticker or caption is taken from here
verbatim, with its id)
{language}

THE CAST WE MAY USE (synthetic, cleared) 
{cast}

THE PRODUCTS
{products}

THE BRAND'S RULES
{brand_rules}

Rules:
- Start with V00, the CONTROL: the original rebuilt only as much as paid
  placement needs (safe zones, a clean plate). Every variation is read against
  it. If the original needs no rebuild, V00 is the original as-is.
- Then V01…V{n}, highest estimated impact first, following the lever order —
  cheaper tests of an equal lever go first. Cover the levers, not one lever
  many ways: no two variations move the same variable unless they aim it at
  different sub-avatars (two different cast members for the same person-lever
  is the one common case).
- Check the paid cut's needs before planning: sound-off viewing (captions),
  the 4:5 zone, one offer and one button at the end, the hero SKU. Each need
  the original does not meet is a lever and gets its own variation.
- A person-lever (who reacts, who pitches, who demonstrates) is cast from the
  cleared cast list above by name, matched to a sub-avatar. A real
  creator's or customer's likeness is never regenerated — it goes in
  `needs_ruling`.
- Each change is written against the Variable Index: variable id, from (this
  ad's value), to (the new value). A change with no variable id is not
  allowed; if the lever has no index variable, use the closest id and say so.
- New words are verbatim from the customer's words above, with their ids. If
  nothing there fits, write [BANK LINE NEEDED: what it must say] — never
  invent customer language.
- A variation that needs a ruling (a real person's likeness, a cloned voice, a
  public figure, a retail claim) says so in `needs_ruling` and still gets
  planned; the ruling is the owner's.
- Name the avatar and sub-avatar each variation is aimed at, and whether it is
  a paid cut, an organic cut, or both.
- Hypotheses are INFERENCE: say what result would confirm or kill each one.

Return one fenced json block and nothing else:

```json
{
  "variations": [
    {"id": "V00", "title": "", "kind": "control | variation",
     "changes": [{"variable": "V-hook.11", "element": "on_screen_text", "from": "", "to": "", "bank_ids": []}],
     "locked": ["element keys that must not move"],
     "hypothesis": "INFERENCE — …", "confirms_if": "", "kills_if": "",
     "audience": {"avatar": "", "sub_avatar": "", "cut": "paid | organic | both"},
     "order_reason": "", "needs_ruling": null}
  ]
}
```
