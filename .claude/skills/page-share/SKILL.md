---
name: page-share
description: Share your version of a page as the family's starting template — family owner only — after a check of what would not work on someone else's machine, listed as warnings with fixes by owner; only a button that calls lab code or an edited overlay stops it (PF-9c (share warns)). Use when someone says "share my <page>", "share my run-detail as the template", "make my draft the template", "can I share this page", "page share", "/page-share". Sharing to named people ("share my page with the email lead and the editor") is not built yet.
---

# page-share — your draft becomes the family template, if it works for others

> **Activates component:** `components/page-features` — shares a page as the family template.


A thin wrapper over PF-9 (share check)'s template mode, `features.py share`.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/page-features/features.py` — the `share` verb (`share.py` beside it).
- `platform/views/viewers/_templates/<family>.features.json` — its `owner` is the
  only person who may share the family template.

## Do this

1. **Names given** ("share my page with the email lead", "/page-share the editor the owner") → do NOT
   run anything. Say: "Sharing to named people is not built yet: it waits on PF-9
   (share check)'s named mode, which waits on PF-7 (working versions)'s PREPARED state.
   What exists today: share it as the family template (owner only), or publish a
   frozen snapshot for viewing." Stop.
2. **No names** → find the draft: the family they named, their own draft of it
   (`features.py pages`); several drafts → ask which. Template mode shares from your
   own DRAFT, not your live page.
3. Run:
   ```
   python3 components/page-features/features.py share <draft>
   ```
   (`--person <folder>` if your viewers folder name differs from your git email's
   first part; the email lead's is `the email lead`.)
4. Print the output as it is: the result, the "won't work on another machine yet"
   warnings with their fixes by owner, and the notes. Exit 0 = the draft is now
   `_templates/<family>.html`, shared — if there were warnings, say in one line that
   teammates' copies will show those numbers broken until they are fixed. Exit 2 =
   blocked (a button that calls lab code, or the overlay was edited) or refused,
   and NOTHING was written — say that in one line.
5. The page-address scan is system-integration's `page_scan.py` (PF-9b (page scan));
   the output's `note:` says whether it ran. Its findings are warnings, never blocks.

## Never

- Never copy a draft over `_templates/<family>.html` by hand, and never share a
  family you do not own (the command refuses; say who owns it).
- Never "fix" a failing number by deleting it from the page or the family list.
