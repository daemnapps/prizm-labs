# the team's email page: history and background

The working instructions are in README.md (short on purpose: the team's Claude reads it every session). This file keeps how
the page got here and the full detail behind each step.

## Before 2026-10-21: the artifact page

**Retired 2026-10-21 (the team, call GMT20261021-110119, 00:11-00:17 and 00:32-00:37):** the artifact page below and its
5-minute `/loop` are replaced. the team works with her own Claude Code beside a page that shows her emails; every change
is asked for in Claude, by code or in plain words. The new page is the team's live page
`platform/views/viewers/pm/emails-demo.html`, opened through PF-4 (page starter kit) (see "Open the page for her").
What follows, down to "Requests from the email page", is kept as history.

Published 2026-10-20 from the team's company account: (private page) (replaces the 2026-10-19 page D5AjDHL7TrWyLvB73x54xL, published from her personal account, whose data company accounts cannot reach from Claude Code)

the owner's `tools/email-production/team-outlier/outlier-emails.html` with the team-facing wording: a "how this works"
guide per person, a to-do list per email for the team, plain button names ("Change this picture", "This part looks right",
"Make the missing parts for me", "Done: send to the team", "Redo the whole email"), statuses named for whoever is
looking. The data contract is unchanged (collections `emails`, `steps`, `calls`; the same call actions), so
`team-outlier/sync.py` list and apply work as written. Fill: `sync.py list --brand B > rows.json`, then `python3 lab/pm/designer-email-page/enrich.py rows.json` (each picture gets where it lives and a Drive link), then the rest as `team-outlier/README.md` says.

Republish from this file over the link above, never a second copy. If the owner's template changes, carry the
change here or fold these wording changes into his template (his call).

## the team's deadlines

Each email shows the team's deadline: the row's `eve_due` (YYYY-MM-DD) when set, else 5 working days (Mon-Fri) before `send_day`
(`EVE_WORKDAYS` in the page; the team, 2026-10-19). Set or move one with an ArtifactData `update` on that email's
row. <brand>-oct-20 carries `eve_due: 2026-10-27` (moved from the 26th by the team, 2026-10-20: she is off on the 26th).

## Requests from the email page (the team's Claude follows this)

From 2026-10-21. the team is a designer and does not use the terminal: do every step yourself, tell her in one plain
sentence what you did, and stop only for what only she can do (a file to drag in, a yes, what a picture shows).
Use a **new** Claude Code conversation each working session, opened in the workspace folder. Run `git pull` first.

**Open the page for her** (each working session, after `git pull`):

    python3 components/page-features/kit/serve.py platform/views/viewers/pm/emails-demo.html --open

It opens the emails page in her browser at http://127.0.0.1:8765/ with today's emails from her copy of the repo
(PF-4 (page starter kit), minimal form). Leave it running in the background; after each change she reloads the page
to see it. It is the team's live page: the same page for both of them (the "I'm the team / I'm the team" switch at the top).
If it says it can't read the emails, run `python3 tools/email-production/team-outlier/sync.py list --brand <brand>`
and tell the team the last line it prints. the team's deadlines live in `runs/email-production/<brand>/deadlines.json`
(the team sets them).

the team asks in one of two ways:

- **Pasted from the page.** Every button on the page copies one line that starts
  `Email request (lab/pm/designer-email-page/README.md):`, then the code, then the address in brackets, then what to do.
  Example: `Email request (…): oct-20 · P1 [<brand>/<brand>-oct-20, section 1, picture 0] · change this picture: warmer light`.
  The bracket is exact: brand / run label, the section's index in `design/email.json`, the picture's index inside it.
- **Said in her own words**, with or without a code: "oct-20 P2: warmer light", "the hero on the Halloween email looks
  too dark". A code is `<email> · P<n>` for a picture or `<email> · part <n>` for a part (part n = section index + 1).
  Find P numbers with `python3 lab/pm/designer-email-page/own_picture.py list <email>`. If her words could mean two
  pictures, show her the two codes and ask which one.

Then do what the request says:

| she asks | you run |
|---|---|
| use my own picture | the "Her own picture" steps below |
| change this picture, this part looks right, redesign this part, move this part up/down, remove this part, make the missing parts, Done: send to the team, redo the whole email | write one call into a JSON list in your scratchpad and run `python3 tools/email-production/team-outlier/sync.py apply <that file>`. A call: `{"id": "<anything>", "at": "<now, ISO>", "by": "the team", "brand": "<brand>", "label": "<run label>", "action": "<picture / ok / look / move / remove / fill / go / send_back>", "section": <index>, "picture": <index>, "note": "<her words>", "dir": "up/down"}`; leave out what the request doesn't name (whole-email calls have no section) |
| change the words (from the team) | a `words` call: `"action": "words", "edits": [{"path": "<field path>", "value": "<new words>"}]`. Then tell the team, every time: run `/review-request` asking the team to review "the team changed words in <code>", naming the run (`runs/email-production/<brand>/<label>/design/email.json`) and each line as before → after. Tell the team "the team has been told". Commit message starts `the team changed words: <code>`. Note: sync.py turns each words change into a copy rule for later emails |
| I scheduled it in Klaviyo | the team's request (action `scheduled`); the team's Claude does not run it |

After every change: open the rebuilt email for her (`open -a "Google Chrome" runs/email-production/<brand>/<label>/klaviyo/email.html`)
and say in one line what changed. `go` makes a Klaviyo DRAFT for the team; nothing is ever scheduled or sent.
Then commit what changed under `runs/email-production/<brand>/<label>/` and `runs/learnings/` (never a picture:
`runs/**/*.jpg` and other media are gitignored and live on the Drive), `git pull --rebase`, push. If the rebase or
push fails, stop and tell the team and the team; never force.

### Her own picture (Higgsfield, a photo, a designer's file)

1. Find the picture: `python3 lab/pm/designer-email-page/own_picture.py list <email>` (e.g. `oct-20`). Use the code
   or the bracket address from her request.
2. Get the file. She drags it into this window (you see its path on her Mac) or pastes a Google Drive link. Either
   works: a Drive link is read with her own `GDRIVE_SA_KEY`. HEIC, PNG, WEBP and JPG all work.
3. Look at the picture yourself and write the alt text: one plain sentence saying what it shows, for someone who
   can't see it (e.g. "A woman at her front door on Halloween night, holding a candy bowl with the two Glow Duo
   tubes in it."). Show it to her and use her correction if she gives one. Never reuse an old alt that no longer
   matches, and never a "To make…" prompt: the script refuses those.
4. Run:
   `python3 lab/pm/designer-email-page/own_picture.py place <email> <code, e.g. P1 or s1.0> "<file path or Drive link>" --alt "<the alt>" --made-with Higgsfield`
   (leave out `--made-with` for a real photo). It saves the picture as JPEG in the run's `media/` folder, puts it on
   the Drive at `Shared Assets/runs/email-production/<brand>/<label>/media/`, swaps it into `design/email.json`
   keeping the old picture in that picture's `history`, then rebuilds and checks the email. If the Drive step fails,
   nothing in the email changes: tell her and the team the line it printed.
5. The picture keeps its own shape by default. If she wants it cut to the shape the old photo had, add
   `--ratio slot`; to choose what a crop keeps, add `--focus x,y` (0 to 1, e.g. `0.5,0.3` keeps the upper middle).
6. Open the rebuilt email for her (step "After every change" above), then commit and push the same way.

Limits, said plainly: the step changes only `design/email.json` and the rebuilt `klaviyo/` folder of that one email;
it never deletes, never talks to Klaviyo. Its result printout names the old picture, so the team can put it back.
