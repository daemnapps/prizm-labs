---
name: page-compare
description: Compare the versions of one page family side by side, by number — every person's live page and drafts, which numbers each version kept, hid, changed or added. Use when someone says "compare the run-detail versions", "how do our outlier pages differ", "compare my page with the editor's", "which versions of this page exist", "what did the email lead change on her emails page", "page compare", "/page-compare <family>". Reads only.
---

# page-compare — every version of a page family, by number

> **Activates component:** `components/page-features` — `features.py compare`, PF-3c (family compare).

Reads only. Prints, per feature number of the family, what each version (each person's
live page and each draft) did with it, then one summary line per version.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/page-features/features.py` — `compare <family> [--json]`, built in
  `components/page-features/compare.py` (PF-3c (family compare)).
- `platform/views/viewers/` — one folder per person; `_templates/<family>.features.json`
  names the families and their numbers.

## Do this

1. Find the family they named (`ls platform/views/viewers/_templates/*.features.json`).
   If none was named, or the command answers exit 2 (unknown family, it names the ones
   that exist), list the families and stop.
2. From the repo root:
   ```
   python3 components/page-features/features.py compare FAMILY
   ```
   Add `--json` only when another step needs the data.
3. Answer with what they asked, from the table:
   - "compare mine with the editor's" → only those two columns, and only the numbers where they
     differ;
   - "how do our pages differ" → the summary lines first (n changed, n hidden, n added
     per version), then the numbers that differ in more than one version;
   - "which versions exist" → the summary lines alone (each names its file).
   Use the command's own words: kept · hidden · changed · added · "—" (on neither).
   Give each version as `<person>/live` or `<person>/<draft>`, with its path when they
   may want to open it.
4. If they want to bring a change from one version into theirs, hand them to
   /page-change on their own draft, naming the number. If their live page is behind
   today's template, /page-catch-up is the route.

## Never

- Never write anything. Never judge which version is better.
- Never compare by reading the HTML yourself in place of the command; if the command
  fails, say so with its message.
