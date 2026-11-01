# Email design formats — <brand>

The brand's own email designs, registered and read. Stood up and maintained by
the email-teardown lane (`email-teardown/`) — its `INTAKE.md` is the
standard, and this shape is the same for every brand.

| | |
|---|---|
| `source.json` | the Figma file and every board — name, code, node id |
| `census.json` / `.md` | every email registered. The index: what do we have |
| `formats.md` | the named format set and each one's template spec |
| `components.json` | the brand's email skin — the tokens the renderer builds with |
| `sweep/` | per-board measurement and the defects found |

**Pictures are not here.** They mirror this path on Drive:
`Shared Assets/brands/<brand>/email-sms/formats/`.

**Every email has a permanent id** — its board's code plus its number,
`JAN26-04`. The same id names it in the census, in a format's member list and
in the folder of pictures. Never renumber a board.

## Standing this up

```
python3 tools/intake.py --brand <brand> --link "<figma board url>"
```

One link per board; the boards do not have to arrive together.
