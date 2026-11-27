# Fill the grid

You fill rows of a creative matrix. One row is one picture (or one cut). You choose cells from lists; you invent no value.

Each row is for the person named. Read the person: every cell has to be something THIS person would stop for, and the reason is one of their own facts below.

{people}

## The values (a number is how often it is already used; take the unused ones that fit)

**awareness:** {awareness}
**argument** (the angle):
{angles}
**format:** {formats}
**setting:**
{settings}
**look:** {looks}
**face:** `none`, or `gender/age/ethnicity` with ages 18-24 25-34 35-44 45-54 55-64 65-plus and ethnicity black white latino east-asian southeast-asian south-asian middle-eastern mixed. Only faces the person's own demographics allow.

## Already fixed (your rows have to differ from these too)

{fixed}

## The rules, checked by code

- Any two rows, yours and the fixed ones, differ on at least 3 of the 7 columns, and on at least 2 of format, face, setting, look.
- No format, face, setting or look fills more than half of the rows.
- Rows for the same person share `who`, so they have to part on what is seen and on the argument or awareness.
- The setting has to be able to hold the format, and the format has to be able to carry the argument. A row nobody could picture is wrong.

Fill: {want}

Answer with one JSON object in a ```json fence:
{"rows":[{"who":"","awareness":"","argument":"","format":"","face":"","setting":"","look":"","picture":"what is seen, one plain sentence","fact":"the person's own fact this comes from"}]}
{note}
