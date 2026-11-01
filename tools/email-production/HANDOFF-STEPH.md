# Handoff: the email line, for the team (and the team's Claude)

From the owner, 18 Oct 2026. Read this first, then `EMAIL-LINE-MAP.md` and `EMAIL-DESIGN.md` in this folder.
The visual walkthrough is the **Email Line Map** page: (private page)
(a 12-level walkthrough with real <brand> and <brand> emails).
the owner's walkthrough video: https://www.tella.tv/video/email-marketing-automation-walkthrough-hmyj38tf

## What changed

Email design is now part of the chain, for both brands (<brand> and <brand>), and works the same way for any brand.
One trigger writes the copy, designs the email, makes the pictures, builds it for Klaviyo and checks it. the owner is
not in the loop for either brand.

## Who does what

| Who | Does | Where |
|---|---|---|
| **the team** | Plans and approves the sends, presses **Write it** | Outlier (127.0.0.1:8880) → Calendar → email drawer |
| the chain | Copy, moment research, concept, layout, Pinterest mood pins, pictures, Klaviyo build, final check | `run_month.py` → `design/line.py`, `design/build.py`, `design/check.py` |
| **the team** | Pictures and design only: swaps or edits a picture, adjusts the design, sends it back with a note, gives the **Go** (a Klaviyo draft) | Outlier → Decide → Emails |
| **the team** | **Final wording** on every line, then **schedules** it in Klaviyo | the Klaviyo draft |

Nothing sends or schedules by itself. The chain never invents an offer: no offer in the offer bank means the email is
held until a person sets one.

## The twelve stations

1. Calendar plans the sends (every two weeks; real dates, holidays, the avatar's culture moments). Each send is marked
   **designed** or **letter** (per brand: `brands/<brand>/email-sms/email-kinds.json`; <brand>: Wed letter, Fri designed).
2. the team approves and presses **Write it**; her note rides along.
3. Copy is written (thirteen steps; checked for wrong facts and invented offers).
4. The moment is researched (what she is doing that week, sourced).
5. One concept per email, from her culture; never repeated in a batch.
6. Layout from the brand's look, visual DNA and Figma-board sections; real customer and product photos first.
7. Pinterest mood board: three pins per picture to make, for light, styling and mood only (`design/pins.py`, about 6¢ a search).
8. Pictures made from the real product photos and judged (right product, right shape).
9. Built for Klaviyo, tracking on every link.
10. Checked: prices, claims, links, sizes, nothing repeated. Anything wrong holds the email and says why.
11. the team makes the pictures and design better and gives the Go.
12. the team does the final wording and schedules it.

## Learnings

Every change becomes a rule every later run reads, for every brand:
`components/run-kit/run_kit/learnings.py`, stored in `runs/learnings/`. the team's wording changes are stage `copy`;
the team's picture and design changes are stage `picture` or `design`. Fix the source, never just the one email.

## Your Outlier is a page, not a local server

the team's and the team's Outlier for emails is an artifact: publish `adapter/outlier-emails.html` once from
the team's Claude and share it with the team. `adapter/README.md` says how to publish it, fill it after each calendar
run, and apply the calls ("apply the email calls"). the owner's demo copy: (private page)

## Where the work happens in the owner's local Outlier

- **Designed emails wait in Outlier → Decide** (and on the classic page, `/classic#approvals` → Emails), marked
  "designed". The card says "ready for the team" or lists exactly why it is held.
- **Change words or pictures ↗** opens the editor: click a line to reword it, click a picture to describe a change
  or drop in a new one, then Save. Each change is saved as a learning (wording → the team, stage `copy`; pictures →
  the team, stage `picture`).
- **Send back** needs a note: the note becomes a learning, then the email is redesigned, rebuilt and checked with it.
- **Go · make the Klaviyo draft** uploads the pictures and makes the draft. It never schedules. A held email can't
  get a Go until what holds it is fixed.
- the team then does the final wording in the draft and schedules it in Klaviyo.

Code: `lab/damon/suite/approvals.py` (`designed_emails`, `act_designed`), `lab/damon/suite/email_edit.py`
(`learn_from_edit`), the preview and picture routes in `lab/damon/suite/suite_serve.py`.

## Still open

- <brand> has no Black Friday offer in its offer bank, so its Black Friday emails are held until one is set.
- The guarantee line on <brand>'s Black Friday emails waits for a person to confirm the exact words (that is what
  holds `<brand>-nov-34` today).

## The system fills gaps before anyone does (added 18 Oct)

- **Gaps** (`design/gaps.py`, runs before every build): unfilled prices are filled from the offer bank (never a sale
  price the bank doesn't have), unmade pictures are made, and anything else missing is closed by the smallest patch
  (`prompts/design4-patch-v1-damon.md`): only the gap changes; everything people ruled on stays.
- **Does it keep every promise** (`design/promises.py`, `prompts/design3-promises-v1-damon.md`, any brand/product/
  offer): reads the built email once, the way she will, and lists every promise it makes (a "two steps" with no step
  two, a price that contradicts the offer, a guarantee that's only a number). Rulings in the offer bank and past
  learnings outrank the job card. It can raise false alarms; check its reason before acting on it.
- **Every email's full index** is at `runs/email-production/<brand>/<label>/index.json` (every step, its prompt as
  sent, its output, its review, every picture's record), shown on the page's "How it was made" tab.
- **<brand> Black Friday** is set in the offer bank: buy 2 get 1 free, starting at $19 a tube; the Glow Duo at $58
  ($68 bought separately). The three Black Friday emails are held only on the guarantee wording: the team confirms it.

## Rules for the team's Claude

- Never send or schedule an email, and never message anyone on the team's behalf.
- Never invent an offer, a price or a claim.
- Machines never write into `brands/`; run output goes under `runs/`.
- Keys come from the environment by name (`components/keys/loader.py`); never paste one into a chat.
- A test runs in a throwaway folder, never on a real run.
