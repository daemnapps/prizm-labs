# The onboarding desk — for whoever brings editors in

The editor's side is `SOP.md` and the page. This is the other side: what the
person onboarding them does, in order, and what to look at afterwards. It
takes about ten minutes per editor once the brand is set up.

## Once per brand — open the folders by link

No invitations. The brand folder opens for anyone with the link, so an
editor never waits on an account being added.

| folder | Share → General access | why |
|---|---|---|
| the brand folder | **Anyone with the link · Viewer** | they read products, cast, briefs |
| its `briefs/` folder | **Anyone with the link · Editor** | they claim in `claims/` and deliver into `delivered/` |
| `Shared Assets / onboarding` | **Anyone with the link · Viewer** | the walkthrough video plays on the page |

If "Anyone with the link" is greyed out, the shared drive needs *allow
sharing with non-members* turned on (Manage shared drive → Settings).

Keep the brand folder link where you can paste it; every editor gets it.

## Per editor — the message

Send this, filled in. It is the whole onboarding.

```message
Hi {NAME} — welcome. Everything you need is on one page:
https://daemn.co/onboarding.html

Watch the video once (17 min). Then the two prompts on that page are the job.

Your brand: {BRAND}
Your brand folder: {FOLDER LINK}

Type those two into the boxes on the page and copy the Day-one prompt into
Higgsfield Supercomputer. When it ends with "Set up for {BRAND} — N briefs
open", you're in. Ping me if a step doesn't match the video.
```

## The first session — what you watch for

1. **They connected both.** Google Drive and GitHub, in Supercomputer's
   Connectors. The Day-one prompt stops at step 1 if either is missing.
2. **The shortcut is in their own Drive.** Supercomputer only sees My Drive;
   the link alone is not enough — step 3 on the page.
3. **The queue showed.** "Set up for <brand> — N briefs open" is the finish
   line. If it found the wrong folder, the link goes straight into the prompt
   now — check they filled the second box.
4. **A claim file appeared.** `briefs/claims/<brief> — <their name>` in the
   brand folder within their first session. The queue flips to *claimed* on
   the hour.

## The first delivery — what good looks like

- Files in `briefs/delivered/<brief>/`, named `<brief>--<what>--v1`.
- A `DELIVERED.md` beside them: what was made, what was rerolled, what is
  still open for the owner.
- Everything at 9:16, faces and product and words inside the 4:5 crop.
  Nothing at 4:5 or 1:1.
- The asks present — stoppers, headlines, variations, the cutdown map — or
  a line saying which were refused and why.

Anything else means a step was skipped; the SOP names it.

## Bounties and due dates

You don't edit the queue. Tell the owner "<brief> $<amount> by <date>" and
it is set with `machine/queue.py set`; the queue shows it within the hour.
An editor never sees a bounty that isn't on the queue.

## Where to look

| for | where |
|---|---|
| what is open, claimed, delivered | `briefs/QUEUE.md` in the brand folder — rebuilt hourly |
| what they delivered | `briefs/delivered/<brief>/` |
| what they are stuck on | ask them for the last line Supercomputer said — it names the door that failed |
| the way we work, verbatim | `SOP.md`, and the prompts in `prompts/` |
