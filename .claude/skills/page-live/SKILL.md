---
name: page-live
description: Make one of your page drafts your live page — the going-live check first, then (only on a pass) the draft's live form written to your live page, the old live kept as a dated draft, the change log carried over, committed and shared. Failures are listed by number and nothing moves. Use when someone says "make this draft live", "make drafts/<x> my working version", "go live with my run-detail draft", "is my draft ready to go live", "page live", "/page-live".
---

# page-live — check, then go live

> **Activates component:** `components/page-features` — makes a draft your live page.


A thin wrapper over PF-7 (working versions)'s `check-live` and `live` verbs.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/page-features/features.py` — `check-live` and `live` (`live.py` beside it).
- `platform/views/viewers/<you>/drafts/<family>--<name>.html` (the draft) and
  `platform/views/viewers/<you>/<family>.html` (the live page it becomes).

## Do this

1. Find the draft: the one they named, or "this draft" from the conversation. If it
   is ambiguous, list their drafts (`features.py pages`) and ask which. Only the
   person's own drafts; a live page or a template is not a draft.
2. Check:
   ```
   python3 components/page-features/features.py check-live <draft>
   ```
   (`--person <folder>` if your viewers folder name differs from your git email's
   first part; the email lead's is `the email lead`.)
   - `not ready to go live: N failures` (exit 2) → print every failure line as it is,
     numbered 1, 2, 3 …; each starts with its feature tag (D16: …) or `page:`. Say
     "fix these on the draft (page-change), then ask again." STOP — do not run `live`.
   - `refused: …` → show it and stop.
   - `ready to go live: <draft> → <live>` → go on. Keep the `note:` lines to show.
3. If they only asked "is it ready?", stop here with the answer. If they asked to
   make it live, run:
   ```
   python3 components/page-features/features.py live <draft>
   ```
   Print its lines as they are: the live path, "old live kept at …" or "first live",
   the change lines logged, notes, and `shared` / `not shared: <git's reason>`.
4. One line after: the live page is never edited directly; the next change starts
   with "make a draft of my live <family>" (page-draft).

## Never

- Never run `live` after a failing check, and never edit the draft to hide a
  failure (removing a number, faking data).
- Never edit the live page by hand.
