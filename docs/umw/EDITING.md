# Don't Start From a Blank Page — the UMW talk (14 Oct 2026)

One copy, edited by Damon and Angie: `docs/umw/index.html` plus pictures in
`docs/umw/media/`. It is live at https://daemn.co/umw/ as soon as a change is
pushed to `main`.

- **The slides** are the `SLIDES` list near the top of the script in
  `index.html`. Each slide has an `eyebrow` (small label), `h` (headline),
  `p` (one sentence), optional `ex` (example box) and `tip` (what to touch).
- **Pictures** go in `docs/umw/media/` and are referenced as `media/<file>`.
- **Style** comes from the site's design system (`docs/studio.css`). The
  commit hook runs `tools/design-check.py`; a page off the system is refused.
- **Preview** by opening the page from a local web server at the repo root,
  or push and check https://daemn.co/umw/.
- **The claude.ai artifact copy** is built with
  `python3 tools/umw_artifact.py <folder>` and published from that folder.

Pull before you start, commit small, push often — two people edit this file.
