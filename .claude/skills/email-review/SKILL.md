---
name: email-review
description: Open YOUR OWN emails page and work it with Claude — the review loop for designed emails, for whoever asks (the editor, the email lead, the developer, anyone with a clone). Use whenever someone says "open my email page", "open my emails", "start my email session", "show me the emails", "I want to review the emails", "email review", "/email-review", pastes lines starting "Request (" or "Email request (", or asks for a change by code like "nov-02 P1: warmer light" or "oct-20 S2: move it up", or says "use my last Higgsfield picture for nov-02 P1". Opens the asker's own live page when they have one, else the shared page; carries out their requests through the email line's own commands; never sends or schedules anything.
---

# email-review — your emails page, and the requests you make on it

> **Activates component:** `components/email-production (adapter/) and components/page-features (kit/serve.py)` — the adapter README holds every step; this skill decides who is asking.


the developer, 2026-10-22 ("ok go"; named by the job, not the person: "what if someone else needs to also pull up their own
emails page?"). One skill for everyone who reviews emails; what differs per person is DATA (their own page, their
role), never a copy of these steps.

**The steps live in ONE place: `components/email-production/adapter/README.md`.** This skill decides WHO is asking
and WHICH page, then follows that README's sections. Where the two disagree, the README wins. Tell the email lead, its
owner, so this file can be corrected.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/email-production/adapter/README.md` — every command (start, requests, own picture, page changes).
- `components/page-features/kit/serve.py` — the local page server (PF-4 (page starter kit)).
- `team/people/<person>/identity.json` — who the asker is.

## 0. How to talk
The person may not use a terminal. Do every step yourself, and say in one plain sentence what each one is for. Stop
only for what only they can do: a file to drag in, a yes, what a picture shows. **Never print, open or paste a key
value.**

## 1. Who is asking (never guess)
- After LD-77 (one person resolver) merges, use its `whoami`.
- Until then: the person is the `team/people/<p>/` folder whose `identity.json` lists `git config user.email`. Match
  the exact address, case-insensitive, and **never the part before the @** (the email lead's is `the email lead@…`, and her
  folder is `the email lead`).
- No match: stop and say "your git email isn't on the team record; ask the developer or the email lead to add it".

## 2. Start ("open my email page", "start my email session")
1. **Python:** run every command below with `/usr/bin/python3`, never plain `python3`, even where the README still
   says `python3`. The page's email list needs Pillow, which is installed for `/usr/bin/python3`. If
   `/usr/bin/python3 -c "import PIL"` fails: `/usr/bin/python3 -m pip install --user Pillow`.
2. Follow the README's **"Start my email session"** step 1: pull, then `prepare.py` (it makes the email pictures on
   this Mac; slow only the first time).
3. **Which page:** `platform/views/viewers/<person>/emails.html` when it exists, else the shared
   `platform/views/viewers/_templates/emails.html`. With no page of their own, offer ONCE: "Want your own copy you
   can change? (yes / no)". A yes: `/page-draft emails`, then `/page-live` on that draft.
4. **Port:** start `serve.py <that page> --open` (README step 2), in the background, on port 8765. If 8765 is busy
   (the developer's MacBook uses it), use `--port 8767`, and say which address opened.
5. Say: "Your emails are open. Make your changes on the page and paste them here, or just tell me in words."

## 3. Requests, pasted or in words
Follow the README's **"When she pastes requests"** section exactly: `requests.py` for change lines, `ask.py` for
the rest, never both for one line. Codes: **P<n> is a picture, S<n> is a part.** If their words could mean two
things, show both codes and ask.

What each person may do comes from their role, and the email line's own scripts enforce it, not this skill:
- the Go to Klaviyo, and "I scheduled it in Klaviyo": the email lead only (ask.py refuses others);
- words: anyone, but every word change from anyone but the email lead sends the email lead a review request;
- pictures, looks, moves, removals, "this part looks right", Done: anyone reviewing.

## 4. Their own picture, and page changes
- "Use my picture": the README's **"Her own picture"** section.
- "Use my last Higgsfield picture for <code>": the README's **"A picture she made in Higgsfield"** section (through the Higgsfield connector; no download or drag).
- Changing the page itself: the README's page-changes section, on THEIR draft (`viewers/<person>/drafts/`), never
  someone else's.
- **Changing the design engine** (a new look, section style or option in `components/email-production/design/`,
  usually `engine.py`): every email is built by that file, so one misplaced line stops them all (2026-11-16: a
  style line landed inside the wrong section and no email could be built for nine hours). Before you commit an
  engine change: rebuild the email it was for (`design/build.py <run>`, then `design/check.py <run>`); that is the
  one the person looks at, as usual. Then rebuild one other email that does not use the change, only to confirm it
  still builds: nobody looks at it, and you do not show it to them. If either build fails, fix it first; never
  commit or push an engine change whose build failed. Commit the engine change in its own commit, naming the
  email it was for. (The push itself now refuses Python that does not compile, but only the rebuild shows a
  look that broke.)

## 5. Known limits (say these plainly if they come up; don't work around them)
- **Changing a picture** from its record needs the original picture and its references; since LD-81 (portable
  picture records) they are read from the Drive on any Mac. A picture whose record still names a file this Mac
  can't read comes back with "remake from the brief instead?": show the reason and the question word for word, and
  do nothing until they answer (the README says how a yes is sent).
- **A picture change asked in words is a TRY first** (LD-83 (picture try first)): numbered tries open on their
  screen and nothing goes into the email until they say "use try N". They may ask for again, options, "more like
  try 2", or another model; only the models the model house lists can be picked, and one with no door yet or no key
  on this Mac is refused by name, never swapped. Every try is a paid generation. The page's own "change this
  picture" button still changes the email straight away.
- Nothing here sends or schedules an email. Done is a review request to the email lead; the Go makes a Klaviyo DRAFT, and
  only the email lead schedules.
