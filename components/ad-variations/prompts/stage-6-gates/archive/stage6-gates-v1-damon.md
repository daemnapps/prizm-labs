You are stage 6 of the ad-variations chain: QC GATES. Each planned variation
must pass the gates that apply to it before it ships. Write, per variation,
which gates apply and the pass line for THIS variation — what exactly is
checked, on which seconds. Every example here is illustrative.

THE VARIATIONS AND THEIR RECIPES (stages 3 and 5)
{variations}

THE GATES (id · what passes · the automatic check that exists today)
{gates}

GATES THE MACHINE ALREADY FORCES (from the routes each recipe uses — keep
every one of these)
{forced}

THE BRAND'S RULES
{brand_rules}

Rules:
- Keep every forced gate. Add any other gate the variation needs; say why.
- "Doesn't look like an ad" applies to every cut meant to pass as native
  content.
- The pass line names the seconds and the thing checked ("the new reactor's
  face in 0.00–6.97 matches his cast sheet"), not the gate's general wording.
- If no automatic check exists for something that must be checked, say
  "manual" and what a person looks at.

Return one fenced json block and nothing else:

```json
{
  "gates": [
    {"id": "V01", "apply": [{"gate": "safe-zones", "pass_line": "", "check": "automatic | manual"}]}
  ]
}
```
