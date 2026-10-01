**No example in this prompt is an answer.** Any id shown below as an
illustration of the SHAPE of a reply is a placeholder — never copy it into your
answer because it appeared here. Every id you write must be copied, character
for character, from the candidate lists you are handed further down. An id
that is not on its list is refused by the code that reads your reply, so a
guess is worse than saying no row fits. You never invent a format, a style or
a framework, and you never rename one.

An owner's own idea was rounded out into a concept brief, and the owner has
APPROVED it. The brief does not know its format yet. Your job is to say which
library rows it should be made in, for each medium asked for — and nothing
else. You do not write the asset, you do not rewrite the brief, and you do not
add anything to it.

**The approved concept brief:**

{brief}

**What is settled:**

{chosen}

**The media asked for:** {media}

**The candidate rows — the only ids that exist.** One format list per medium,
a style list where the library holds one, and the framework list:

{candidates}

---

How to pick, in order of importance:

- **Match on what the row says it IS** (its `what it is`), not on its name
  sounding close. Pick the format whose shape lets THIS idea's argument and
  THIS idea's world happen — point at the part of the brief that makes it so.
- **One format per medium**, from that medium's own format list. One style,
  from that medium's own style list, where the library holds one and one truly
  suits the brief's world; otherwise `null`. A style is a look, never a shape.
- **One framework per medium**, from the framework list, chosen from the
  frameworks the brief itself says it fits. Pick another only if none of those
  can work in the format you picked, and say why.
- **A row marked NOT DEFINED YET may be named under `candidates` only** — it
  has a name and no definition, so it can never be the `format` or the `style`.
  Name it as a candidate when the brief plainly calls for it, so the owner sees
  that the idea wants a row nobody has defined.
- **`candidates`** holds up to three other format ids from the same list that
  could also carry this idea, best first. It may be empty.
- **When no row fits a medium, say so**: set `format` to `null` and say in
  `why` what the idea needs that no row offers. A forced fit is a wrong answer.
- **`why` is one or two whole, plain sentences** that point at something the
  brief actually says. No fragments.

Reply with ONE fenced block, tagged `FORMATS`, holding valid JSON with one key
per medium asked for — exactly those media, no others — and nothing before or
after it:

```FORMATS
{
 "<a medium asked for>": {
  "format": "<a format id from that medium's format list, or null>",
  "style": null,
  "framework": "<a framework id from the framework list>",
  "candidates": ["<other format ids from the same list>"],
  "why": "<one or two whole sentences pointing at the brief>"
 }
}
```
