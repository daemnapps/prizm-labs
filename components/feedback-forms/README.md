# components/feedback-forms — customer feedback forms, by stage


**What it is:** one branded, one-question-at-a-time feedback page per brand,
covering every customer stage (`?stage=`), sent from Klaviyo flows. Every
submission is ONE Klaviyo Client API event (metric **"Submitted Feedback"**,
the brand's PUBLIC company id — no secret key anywhere in a page). The research
gatherer's `feedback` mode reads those events back into the brand's language
bank, filed by stage and tagged by business area, so every answer is searchable.

Built 2026-09-29 on the owner's ask: *"I want to actually build out surveys … set it
up in our Klaviyo accounts for both brands based off those specific stages …
Anytime we get a response, that feedback goes directly into our system, is
filed properly, and we just get really, really searchable."*

| | |
|---|---|
| **engine + owner** | `engine/feedback.js`, `engine/feedback.css`, `build.py` — **the owner** (confirmed by the developer 2026-10-07, triage action 3 (definition lines and registry rows)) |
| **definitions + curator** | per brand, in `brands/<brand>/operations/feedback-stages.json` (who gets it, when, what we already know) and `feedback-questions.json` (the questions, the look, the emails) — **the owner** curates the questions |
| **who installs the Klaviyo flows** | **the email lead**, from `runs/feedback-forms/<brand>/install/deliverable/feedback-klaviyo-install.md` — generated, one section per stage, every flow built in Draft |
| **the plane it emits** | Klaviyo events (live); the language bank rows are written by `components/research-gatherer` (`gather.py feedback`), not here |

## Where the questions and the look come from

- **The questions** are written per brand by `write_questions.py` from its foundational research: what to ask from its
  people profiles (the parts still open), how to ask from its voice and its customers' own words (also the tap
  options). It writes a proposal under `runs/`; a person applies it on the owner's yes.
- **The look** is read at build time from the brand's design system (`design_system.py`: `email-sms/design-system.json`, the file its emails render with, by its standard keys; else the standard `web-tokens.md` table;
  and its logo). Nothing is guessed: a key the brand has not declared is listed as missing; a value in the brand's file overrides.
- **The starter set** (`brands/_TEMPLATE/operations/feedback-*.json`) is brand-neutral: eight stages for a store
  with an email platform; subscription and helpdesk stages apply only where the brand has them.

## The loop

```
Klaviyo flow (trigger + filters + wait)  →  email with one button
   →  the form page ?stage=<stage>&e={{ email|urlencode }}
   →  "Submitted Feedback" event on the profile (answers, stage, form version, what the flow already knew)
   →  gather.py feedback (daily, 05:30)  →  language bank rows: source survey_<brand>_feedback-<stage>,
      lane by relationship from the stage, business areas + tap answers on every row
   →  query_language.py --brand B --area website | --feedback-stage churned-refund
```

## Commands

```bash
python3 components/feedback-forms/write_questions.py --brand B   # every stage's questions from the brand's research (profiles, voice, customer words): a proposal
python3 components/feedback-forms/build.py check   --brand B    # the config is sound
python3 components/feedback-forms/build.py preview --brand B    # runs/feedback-forms/<B>/preview/<stage>.html (nothing sends)
python3 components/feedback-forms/build.py install --brand B    # runs/feedback-forms/<B>/install/deliverable/feedback-klaviyo-install.md
python3 components/feedback-forms/build.py cpk --brand B --dest <cpk checkout>/<campaign>/src/<slug>
python3 components/feedback-forms/build.py all                  # check + preview + install, every brand
python3 components/feedback-forms/docs/make_page.py             # the docs page + its Markdown mirror → runs/feedback-forms/_system/
python3 -m unittest discover -s components/feedback-forms/tests
```

A campaign repo carries a **copy** of the engine and the compiled config
(`assets/js/feedback.js`, `assets/js/feedback-config.js`). Change the source
here, rebuild with `cpk`, and send the campaign repo a pull request.

`cpk` writes a local checkout only. The commit, the push and the pull request to the
vendor's repo are a person's act, never a machine's or a session's: a push from the mini
would be an external send (feedback-forms#9 (cpk vendor push), 2026-10-08).

## Rules the engine keeps

- **The email never reaches an ad platform.** The page reads `e` (or `_kx`)
  once, wipes it from the address bar, loads no pixels, tag managers or
  Campaign Cart SDK, and sets `referrer` to `no-referrer`.
- **Known things are never asked.** What the flow already knows (order count,
  subscription, purchase status, lane) rides on the event as `known`.
- **Only open text is language.** Taps (choices, scores) ride on each row of the
  same submission as `feedback.taps`; a score also lands in `signal.rating`.
- **Test submissions are marked `test: true`** (the `_send-test.html` preview
  forces it) and the gatherer skips them unless `--include-tests`.
- **Brand-agnostic.** No brand is named in `engine/` or `build.py`; the tests check it.

## Question fields

`id` (stable slug) · `n` (its number — becomes `q-<nn>_…` in the bank) · `type`
(`choice` · `scale` · `text`) · `text` · `options` + `other` (choices) · `min`/`max`/`low`/`high`
(scales) · `short` (one-line text) · `show_if` `{q, in | not_in}` (a follow-up) · `areas`
(marketing · product · operations · customer-service · customer-experience · website) ·
`yields` (the bank tags the answers should give) · `from_old` (the old Google Form question it
descends from, when there is one).
