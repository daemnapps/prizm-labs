# components/feedback-forms — customer feedback forms, by stage

**feedback-forms** — takes **a brand's feedback config
(`brands/<brand>/operations/feedback-stages.json` + `feedback-questions.json`)**,
makes **the brand's one-question-at-a-time feedback page for every customer
stage, its previews and the Klaviyo install sheet**. Does not **send an email,
hold a secret key, or write the language bank**. Triggered by
`python3 components/feedback-forms/build.py check --brand <brand>`, then
`preview`, `install` or `cpk` (`all` runs check, preview and install for every
brand with a config).

**Owner:** the owner (engine and definitions both). Confirmed by the developer 2026-10-07
(triage action 3 (definition lines and registry rows); decision log). Built
2026-09-29 on the owner's ask; `README.md` holds the loop, the commands and the
rules the engine keeps.

## The four new-resident questions

- **Engine + owner.** `engine/feedback.js` + `engine/feedback.css` (the page),
  `build.py` (check · preview · install · cpk · all), `language_pass.py` (the
  wording pass, through `components/language-layer`) and `docs/make_page.py`
  (the docs page). `build.py` reads config and writes files: no network, no
  key. **the owner.**
- **Definitions + curator.** Per brand, never here:
  `brands/<brand>/operations/feedback-stages.json` (who gets it, when, what we
  already know) and `feedback-questions.json` (the questions, the look, the
  emails). **the owner** curates the questions.
- **The plane it emits.** Klaviyo events: every submission is ONE Klaviyo
  Client API event, metric "Submitted Feedback", on the brand's PUBLIC company
  id. The language-bank rows are written by `components/research-gatherer`
  (`gather.py feedback`), not here. Files land under
  `runs/feedback-forms/<brand>/` — `preview/<stage>.html`,
  `install/deliverable/feedback-klaviyo-install.md`, and the language pass's
  run folder with its proposal — and the docs page under
  `runs/feedback-forms/_system/`. `brands/` is read, never written.
- **What the manifest declares per entry.** Each question in
  `feedback-questions.json`: `id`, `n`, `type` (`choice` · `multi` · `scale` ·
  `text`), `text`, and by type `options` + `other`, `min`/`max`/`low`/`high`,
  `short`; plus `show_if`, `areas`, `yields` and `from_old` (README, "Question
  fields").

## Where the page goes, and who installs it

A campaign repo carries a COPY of the engine and the compiled config
(`build.py cpk`), sent to that brand's campaign-page-kit repo by pull request
for the email lead to review. **the email lead** installs the Klaviyo flows from the install
sheet; every flow is built in Draft.
