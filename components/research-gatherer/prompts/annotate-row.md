# Annotate row — the gatherer's intake read

Used by `research_gatherer/annotate.py` for every row the gatherer files
(own ads + support inbox, comments on any post). One call per batch of up to
30 rows. The engine fills the `{{…}}` slots at run time; nothing
brand-specific is written here, and the use vocabulary is read from the
brand banks themselves.

This read does ONLY what an intake needs. Awareness, sophistication and the
lane the words point to are read by the language layer's own labeller
(`tools/language-layer/tools/label.py`, its newest
`label-awareness-v*.md` prompt) — the ruled reading in
`brands/language-schema.md`, called, never restated here.

---

You are reading real words people wrote — comments, support emails, forum
posts — so they can be filed into {{BRAND}}'s customer-language bank. The bank
is what ads, pages and emails are written from. "The product" always means
{{BRAND}}'s own product, never a competitor's.

The avatar these words are filed under, and its voice rules:

{{RULES}}

Its sub-avatars (use a slug only when the words carry a clear marker of that
sub-avatar; otherwise null — a wrong sub tag is worse than none):

{{SUBS}}

## Use tags — pick from the bank's existing vocabulary

{{VOCAB}}

Tags that feed joke hooks and the vibe read, when they fit:
transformation-reaction, result-language, taste, in-word, subculture, cringe,
laugh (the line is a joke, or reacts to one — "💀", "I'm crying", a roast,
a punchline), community-voice, role-claimed.

## Return

For EACH row, one JSON object. Return a JSON array of those objects and
nothing else — no prose, no code fence.

```
{"i": <the row's number>,
 "keep": true | false,
 "drop_why": "<only when keep is false: logistics | spam | auto-reply | vendor | too-short | not-the-person | other: …>",
 "exit": "cancel-subscription | refund-or-return | none",
 "use": ["<one or more tags from the vocabulary>"],
 "topics": ["<2–4 short kebab-case topics>"],
 "sub": "<a sub-avatar slug from the list, or null>",
 "ad_use": "hook | objection | proof | offer | question | none",
 "names": ["<every person's name in the text, exactly as written>"],
 "cut": "<the first 3–8 words, copied exactly, where a signature, job title, company line, footer, disclaimer or forwarded mail BEGINS — or \"\">"}
```

**keep** — false for address changes, order-status chasing, tracking,
"thank you" with nothing else, auto-replies, vendor pitches, spam, one-word
emoji, notifications forwarded from payment or marketplace services, and
anything not said by the person themselves. Keep a short row when the words
carry weight ("Recipe", "AI fake!", "I have plenty", "link?").

**exit** — the words cancel a subscription, or ask for a refund or return.

**ad_use** — `hook` words that could open an ad as they stand; `objection` a
doubt an ad has to answer; `proof` a result or experience to show; `offer`
words about price, quantity, shipping, discounts or subscription; `question`
something asked before buying; `none` kept for the record only.

**cut** — keep a sign-off like "Thank you" on the person's side of the cut.

Never change a word of the text. Names and the cut are applied by the engine.

Source of these rows: {{SOURCE}}

Rows (each tagged with what is known about the speaker's relationship):

{{ROWS}}
