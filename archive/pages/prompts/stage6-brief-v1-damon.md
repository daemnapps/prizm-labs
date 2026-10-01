Today is: {today}
Here is what triage decided: {triage}
Here is the page, end to end: {body}
Here is what the source page was: {source_reference}
Here is our offer: {offer_file}
The page is named `{page_name}`; format `{page_format}`, avatar `{page_avatar}`, sub-avatars `{page_subs}`, angle `{page_concept}`, hands off to `{page_next}`, built from swipe `{page_swipe}`.

The one document the person building the page opens. Everything upstream was working material; this is what leaves the building.

**Written to the builder, in plain language.** No stage names, no slot syntax, nothing about how it was made. They need to know what to build, what every section says, and what is still open.

Open with what this is, in three lines:

- **What it was built from** — the source page, named, and what kind of page it was.
- **The format**, in plain words, and what that means for where it sits in the funnel: a pre-sell that hands off to the offer page.
- **Whose voice it is in** — the narrator persona, named, and that she is a cast persona and not a customer.

Then:

**THE MANIFEST** — the front-matter block, exactly:

```yaml
page_name:    {page_name}
page_format:  {page_format}
page_avatar:  {page_avatar}
page_subs:    {page_subs}
page_concept: {page_concept}
page_swipe:   {page_swipe}
page_next:    {page_next}
narrator:     <the persona's name — a cast persona, not a customer>
```

**THE COPY** — every section in page order, each under a numbered heading in the form `## [n] <what the section is>`, the full text ready to build exactly as it should read. Reviews as `> REVIEW: "<text>" — <attribution>`. Anything the page cannot honestly carry as `[UNFILLED: <what>]` on its own line — never smoothed over, never deleted. Nothing else inside the text: no brackets that are not one of those two, no notes.

**THE OFFER IT HANDS TO** — price, packs and guarantee, verbatim from the offer file, so the builder can check the offer page matches what this page promises.

**WHAT TO WATCH** — two or three lines. What this page is betting on, and the thing that would tell you early it is not working.

**BEFORE YOU BUILD IT** — anything genuinely unresolved: a fact nobody supplied, a claim standing on contested ground, a collision an earlier stage escalated rather than decided. Each in one line, with what it would take to settle it. If there is nothing outstanding, say "nothing outstanding".

Give me the brief.
