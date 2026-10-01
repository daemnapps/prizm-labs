Today is: {today}
Here is the source page, as captured: {source}
Here is what the classifier says the source page IS (this is not yours to change — the format is read off the page by code, never chosen): {format}
Here are this brand's avatars, and where their language sits in the funnel: {avatars}
This run is building a page for avatar `{avatar}`, on the angle `{angle}`. The page's name is already `{page_name}`; nothing here renames it.

A cheap first look at a landing page, before anything is written. Every stage after this binds to these answers, so a wrong answer here is a wrong answer everywhere.

**1. PAGE JOB — does this page hand off, or take the money?**

`PRE-SELL` — it warms the reader and sends her on: an advertorial, a listicle, a prelander, a quiz. Its call to action goes to another page. Our page will be the same kind of thing and hand off to the offer page `{page_next}`; it never carries a buy button of its own.

`OFFER` — it sells on the page: prices, packs, a cart. If the source is an offer page, say so, and say in one line that this run is building a pre-sell from it and what that costs.

**2. FORMAT — confirm the classifier's word, or dispute it.**

The classifier's answer is above. Say `FORMAT: <its word>` and one line on what shape you actually see. If you would have called it something else, say so in the same line — the classifier still wins, and your line is the note that gets it corrected, not a decision.

**3. VOICE — whose mouth is this coming out of?**

A named writer, an unnamed writer, a customer, a doctor, the brand. Then the binding: our page is written as **a person of that kind speaking**, in our avatar's own register — never the brand talking about itself. If the source's writer is a persona (a byline with a photo and a title), say so; our page's narrator will be a cast persona too, and never a real customer.

**4. FUNNEL — who is the page written TO?**

`prospect` · `lead` · `customer` · `churned`, read off what the source explains and what it takes for granted. Print the working in one line each: what it explains · what it assumes · the level that describes. Then what that means for our copy — what the reader already knows, and what would insult her to be told.

**Never guess a fact the source does not carry.** An unnamed writer stays unnamed. A missing price stays missing.

**Also answer, in one line each:**

- **What it is about.** The subject, plainly.
- **What it is doing.** The move — a counted comparison, a first-person conversion, a list of reasons, a confession.
- **Length.** Roughly how long the page runs, in words, so the close has something real to budget against.
- **Speaker identifiable?** Whether a real named person stands behind it, or a byline persona.

Answer in exactly this shape, nothing else:

```
PAGE JOB: PRE-SELL | OFFER
FORMAT: <the classifier's word> — <one line on the shape; any dispute noted here>
HANDS OFF TO: {page_next}
AVATAR: {avatar}
FUNNEL: prospect | lead | customer | churned
FUNNEL MEANS: <one line>
VOICE: <who is speaking in the source>
VOICE BINDING: <one line: whose voice our page is in, and that brand voice is not permitted>
ABOUT: <one line>
DOING: <one line>
LENGTH: <one line>
SPEAKER IDENTIFIABLE: yes/no — <one line>
```
