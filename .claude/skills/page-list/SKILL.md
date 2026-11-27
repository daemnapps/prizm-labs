---
name: page-list
description: Show your own pages — your live pages, your drafts, pages prepared for you, whether each is saved and shared, and the page families you have nothing in yet. Use when someone says "show my pages", "what pages do I have", "list my drafts", "which drafts do I have", "is my page saved", "where is my outlier draft", "page list", "/page-list". Reads only; writes nothing.
---

# page-list — your pages, as they are on disk

> **Activates component:** `components/page-features` — lists your pages.


A thin wrapper over PF-8 (show my pages). Reads only.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/page-features/features.py` — the `pages` verb (`pages.py` beside it).
- `platform/views/viewers/<you>/` and `platform/views/viewers/_templates/*.features.json`.

## Do this

1. Freshen the clone: `git pull --no-rebase -q origin main`. If the pull is refused,
   say so and go on with what is there ("not refreshed").
2. From the repo root run:
   ```
   python3 components/page-features/features.py pages
   ```
   The person is your git email's first part. If your viewers folder has a different
   name (the email lead's folder is `the email lead`), add `--person <folder>`.
3. Print the output as it is, in a code block. Do not re-sort or summarise it away.
   Each page line ends in its save state: `saved`, `not saved` (uncommitted) or
   `not shared` (committed, not pushed).
4. One line after it, only if it applies: a page that is `not saved` or `not shared`
   → "say 'save my pages' and I'll run `features.py autosave`"; an `available:`
   family → "say 'make a draft of the <family> template' to start one" (page-draft).

## Never

- Never write, commit or push anything here (autosave runs only when asked).
- Never list another person's pages unless they asked for that person by name.
