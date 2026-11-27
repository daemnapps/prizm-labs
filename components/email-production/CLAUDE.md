# email-production — the writing, the pictures, the Klaviyo draft

**email-production** — takes **a calendar send**, makes **the email — copy,
pictures, layout — and a Klaviyo draft**, with an approval card. It **schedules**
only on the owner's Approve on the email approval page, and **never sends now**
(EP-3 (email approval card), 2026-10-12). Triggered by
`python3 run_month.py <calendar run> --only <send ids>` (a month or a week), or
`python3 email_line.py <source> --brand <brand> …` then
`python3 simple_email.py <run folder> --brand <brand>` for one email.

**Owner:** the owner · **Station:** `components/` — moved in 2026-09-19 ·
**Held-emails development:** the designer (2026-10-01, decision log; named here by
the developer, 2026-10-07, triage action 3 (definition lines and registry rows)) ·
**`adapter/`:** built by the owner; engine the designer after /system-review accepts it;
words the email lead (decision log 2026-10-22). It holds the team page's `sync.py` (was
`team-outlier/`) and the editor's emails flow (`ask.py`, `prepare.py`, `own_picture.py`,
`enrich.py`, was `lab/the email lead/the editor-email-page/`), moved 2026-10-22 on the developer's "go
lab-flow move"; both old folders are one-release forwarding stubs.

Runs by: both

Calendar handoffs use `calendar_handoff.py`: reviewed date/hour/local/audience travel together; explicit buyer language for leads and stale identities stop writing/design/approval. `reconcile_calendar.py --brand <brand> --month YYYY-MM [--from-date YYYY-MM-DD] --write` changes local card metadata only and writes `runs/email-production/<brand>/calendar-handoff-YYYY-MM/report.json`. Released card fields remain frozen with divergence held. This report distinguishes copy review, held drafts and existing platform work; it does not approve design or launch. Tests: `test_calendar_handoff.py`.

Hold an email with `state` and `manual_repair` on its card; never overwrite `klaviyo/email.html` with a placeholder. A held email keeps its last build until `design/build.py` replaces it, because the emails page reads that file.

> Moved from `lab/the owner/email-production/` on the owner's word, 2026-09-19:
> *"move these tools out of the lab… straight into the real production repo,
> components… so we can actually run QC on it as well… and everybody can have
> access to these things."* Settled by system review (the 2026-09-21 ruling: a
> move is the owner's act and a review follows it; email-production#14).

**Agreed rules checked in code (2026-11-23, the editor):** `design/rules_check.py` tests a Figma-look layout against the designer's agreed rules (no gold text on light,
normal-case buttons with no arrow, flat colours, no thin gold outlines, voice cards with stills, sections that alternate, the ruled top strip, no repeat of a
recent hero). `line.py` runs it inside `validate`, so a layout that breaks one goes back to the layout step once; by hand:
`python3 design/rules_check.py <run folder>`. Tests: `design/test_rules_check.py`.

**Wireframe on the team page (2026-11-20, the editor):** after a Figma-look layout, `design/wireframe.py` also writes `design/wireframe/email.html` and `card.json`
(never anything under `klaviyo/`). `adapter/sync.py` lists that wireframe, drawn with "PICTURE TO MAKE" boxes and held ("the pictures are not made yet"),
whenever it is newer than the built email or no built email exists; a real build newer than `design/email.json` replaces it on the page. It has no
Klaviyo state, so it can never be uploaded or approved. Tests: `adapter/test_wireframe_page.py`.

**One layout by default (2026-11-20, the editor):** for a brand whose look file says `"default_look": "figma"`, `design/line.py` weighs three structures
privately (teaching-first, offer-first, proof-first), delivers ONE layout the copy fits best, varied from the brand's recent emails (hero height,
colours, explaining block), carrying the owner's ruled top-strip and offer wording from `products/offer-bank.md` for the send date. The wireframe
view below is optional. The designer's art direction (`--art "..."`, saved as `design/art-direction.md`) is added to every picture's brief when the
pictures are made (`--pictures`).

**Wireframe directions (2026-11-20, the editor):** `python3 design/line.py <brand> --run <run folder> --directions` lays one email out three ways
(a product still life, an abstract set, a new person as the hero; each in its own hero-height band, each checked against the brand's recent
emails so a hero height, palette or set is not repeated) as `design/direction-a|b|c.json` and one side-by-side `design/directions.html`. Every
picture stays a "PICTURE TO MAKE (w x h)" box: nothing is generated and no picture credit is spent. `--pick a|b|c` keeps one as `design/email.json`
(no model call); pictures are made only after that. A brand whose look file says `"default_look": "figma"` is laid out in the Figma look
(`figma_look.py`, its recipes and rules in the look file's `figma` block). Tests: `design/test_directions.py`, `design/test_figma_default.py`.

**Coverage: sends ahead with nothing written (2026-11-10).** `python3 coverage.py --brand <brand> [--from YYYY-MM-DD] [--days 14]`
lists every calendar send in the window (the reviewed plan, cut sends gone) whose email has no written version, every
text with no text written for its day and email (the calendar renumbers texts when it is re-planned), and every text
whose email is missing. A run is matched by the slot it records (`sms.recorded_slot`), never by its folder name;
off-page runs do not count. `run_month.py` prints it before choosing a batch and logs it after. Reads only. Tests:
`test_coverage.py`.

**SMS words (2026-11-03):** `python3 sms.py <calendar month> [--only ids] [--dry-run]` writes one text per
slot the calendar marks `channel: sms`, from `prompts/sms-v<N>-*.md` filled with the slot, the offer's own
bank section and the sender identity, then checks it in code (length with link and opt-out, one `{link}`,
prices only from the offer section, no code where the section says none). Output
`runs/email-production/<brand>/<brand>-<slot>-sms/`; `status: draft`, `state` says ready or held. Never sends
or schedules, on any platform. `run_month.py` skips SMS slots.

**SMS facts (2026-11-04):** `python3 sms_facts.py --brand <brand>` reads, GET only, what the brand's SMS
list holds on the platform its record names (`operations/brand.json` `sms_platform`; key by name,
`<PLATFORM>_<BRAND>_KEY`): Klaviyo SMS lists and segments with their sizes and the SMS campaigns on file;
Postscript subscriber records in all and with promotional `can_send` (its public API has no campaigns
endpoint). Counts only, no contact details: `runs/email-production/<brand>/sms-facts/`.

**A page not open yet (2026-11-04):** an offer the bank marks "hidden until …" (`simple_email.pages_hidden`) is written and carded, and Approve refuses it, email and SMS, until a person takes the mark out of the bank.

**SMS launch (2026-11-04):** `python3 sms_launch.py card <…-sms run>` makes the approval card beside a
written text — the link from the email it follows, the audience, the send time (the plan's day at the cadence
hour, each recipient's own time zone), the brand's `sms_platform`, a fingerprint; `dry` prints what launch
would do and calls nothing. The card shows on the email approval page (email_approve.py), and Approve runs
`sms_launch.approve`: the email gate's refusals (off-switch, approvers.json, not the mini or a worker job,
the checks again, the fingerprint, 30 minutes' lead), plus one more: every version of the email it follows
is approved or scheduled first — an SMS goes only with its email. Then Klaviyo: the draft SMS campaign and
its schedule (campaign-send-jobs), never a send now; Postscript: `postscript-handoff.md` for a person to
place (its public API has no campaign endpoint).

**Event tag on every draft (2026-11-26, the email lead):** `simple_email.create_draft` tags the Klaviyo campaign with its event,
`event_tag(slot)`: the calendar slot's `occasion` key title-cased plus the send's year ("Christmas 2026", "Gifting Season
2026"; Black Friday 2026 was tagged by hand the same way). No occasion, or one written as a sentence, gets no tag. The tag
is reused when it exists and made the first time; a refused tag is written as `tag_error` and never stops the draft.
Tests: `test_event_tag.py`.

**What the writer is held to (2026-11-04):** `offers.writer_rules` goes into `{offer_rule}`, so every writing step
reads it: the bank's guarantee lines word for word, the only deadline the plan gives (`--deadline`, `--order-by`, the
calendar's slot) and no clock time, the send's own type, and no code where the bank says none. A bank `- Saving:` line can mark the condition copy must state ("Copy stating the saving says it's <condition>."): writers are told it, and `offers.saving_problems` refuses a saving or a subscribed price without it, in a text, in an email's words and in its subject lines. Writers are also told a product file's older was-price is never used. And nothing is invented (LD-104 (no invented facts), 2026-11-04): no number, timeframe, guarantee term or named quote that is not in the brand's files, a count stated exactly as its file states it, a quote credited as its file credits it; a missing fact is written around, or marked `[UNFILLED: …]`. Step 6 (expansion) now reads `{offer_rule}` too. Tests: `test_ld104_no_invented_facts.py`.

**Pictures run on any person's machine with the keys (2026-11-04):** the "pictures on the email lead's Mac" note is the mini's rule
(its door passes `--no-images`); nothing else stops them. A product at rest waits on a 3D set a Higgsfield session builds.

**Stage two of the email line.** Stage one — brand record → calendar → review
→ hand-off — is `components/marketing-calendar/`. This component takes each
send that stage hands it and turns it into an email in a Klaviyo draft:

1. **Writing** — `email_line.py`, the steps its `STAGES` list declares, each with its own prompt in
   `prompts/` and its own model (Haiku reads, Sonnet checks, Opus designs; a
   prompt too big for a small model moves up on its own).
2. **Pictures** — the email picture chain, `design/picture_chain.py` (2026-10-29), which both
   `simple_email.py` and `design/line.py` call: email pictures are made the way picture ads are.
   A product comes from its product casting sheet; a product at rest is a 3D set built in
   Higgsfield 3D Jutsu and printed (image-production `picture_sets.py`), held with its set
   request in `media/sets/<label>.json` until a kept print names it; words a brief quotes are
   set on top, never drawn. The job card's concept and culture ride in every picture's recipe.
   `python3 design/picture_chain.py <brand> <run>` shows every picture's route, nothing spent.
3. **Layout** — the same simple shape for every email (the owner, 2026-09-19):
   logo, headline, hero picture, the copy, an optional offer picture, one
   button, sign-off, footer. Each brand's look is `brands/<brand>/email-sms/simple.json`,
   read off that brand's own last sent email.
   **Moving to formats (2026-10-08):** every send gets a format — a stack of
   sections with a fixed picture count, each picture from a real-life
   reference first. `EMAIL-FORMATS.md` is the map; `simple` is one of them.
4. **Klaviyo** — `simple_email.py --push`: a DRAFT campaign to the send's own
   segment, main subject line, set for the reviewed calendar's date, hour and
   recipient-time-zone rule. `klaviyo_upload.py` writes an approval
   card beside each draft (`email-card.json`). the owner's **Approve → Schedule** on
   `email_approve.py` (http://localhost:8797, launch config `email-approve`) —
   or his typed word to his own Claude acting on that page — schedules it. Every
   check is re-run first, the email must match its fingerprint, the send time
   must be at least 30 minutes away, the off-switch `send-switch.json`
   (the designer's) must be on, and it never runs on the mini or in a batch run.
   `--send` never schedules; `approvals.json` no longer counts (decision log
   2026-10-12).

The full chain, every prompt word for word and the knobs in order:
**The Email Chain** — https://claude.ai/artifact/U6zNmn1D8qCKVjtgaGnU4G
(`python3 chain_page.py` rebuilds it from the code).

## Running it

`--brand` is always named. There is no default brand anywhere in this folder —
a command without one stops and says so, and a run folder whose `run.json`
names no brand is an error that names the file.

    python3 run_month.py ../../runs/marketing-calendar/<brand>/2026-09 \
        --avatar <avatar> --from-date 2026-09-20 --push     # a week, into Klaviyo
    python3 copy_plan.py ../../runs/marketing-calendar/<brand>/2026-09   # what each send would be handed — no spend
    python3 simple_email.py <run folder> --brand <brand> [--push]     # one email
    python3 klaviyo_upload.py --handoff <folder> | --run <run folder> [--dry-run]  # checked DRAFT in Klaviyo + id written back
    python3 klaviyo_upload.py --run <run folder> --card                # a card for a draft that already exists
    python3 email_approve.py                                           # the email approval page, :8797

`run_month.py` ends `done · N built, M held, K failed · S skipped`; a held email
waits on a ruling and exits 0 — only a failed one exits 1 (HE-2 (held not failed)).
    python3 test_klaviyo_upload.py                                     # the uploader's tests — free
    python3 email_line.py <source> --brand <brand> --avatar <avatar> --dry-run   # the free check
    python3 doctor.py --brand <brand>                                  # is the brand wired — free
    python3 test_rollout.py                                            # the tests — free

**The dry run is free, and it writes nothing** (2026-09-20). `email_line.py --dry-run`
stops before step 0: no model call, no folder under `runs/`. It prints every
input with where it was found, the language rows each step would get, which
model each step would run on, and where the run would file. What only step 0
can know — lane, format, sender — is reported as "decided at triage". The
doctor uses the same dry run and no longer has anything to clean up.

**A send is checked for readiness before anything is spent** (LD-106 (readiness check), 2026-11-04).
`run_month.py` asks every version first (`readiness.py`) and prints `ready` or `NOT READY … because …`; a version
that is not ready is not written. Not ready: its product or its offer's product sold out or missing on the store as a
US shopper sees it (`<site>/products/<handle>.js?country=US`, cached two hours in
`runs/email-production/<brand>/readiness/stock-cache.json`, paced; a store that will not answer is a note), an offer
the bank refuses on that day or prices nowhere, a calendar send that will not bind (`calendar_handoff`). A missing
moment look or moment research is a note for the editor, never a stop (decision log 2026-11-04, decision 3). A version
already written whose calendar send changed is a note: the run rewrites it.
`python3 run_month.py <month> --only <ids> --readiness` prints the list and stops: nothing written, nothing spent.
Tests: `test_ld106_readiness.py` (no network: the store read is a seam).

**A retry re-runs only what failed** (LD-107 (retry failed only), 2026-11-04). Every batch writes `last-run.json` in
the calendar month's folder: the labels it built, held and failed, the ones not ready and the ones skipped.
`python3 run_month.py <month> --retry-failed` re-runs only the labels it names as failed; production.log opens the
retry with `=== retry of the failed only (last run <when>): <labels> ===`. No record is a stop, never a guess; nothing
failed is nothing run. A batch runner retries with this flag, never the whole batch. Tests: `test_ld107_retry_failed.py`.

**The send's type is checked before anything is spent.** A calendar send's
`type` is an email format. `brief.py` passes it to the chain as `--type`;
`copy_plan.py` blocks, `run_month.py` skips, and `email_line.py` refuses a type that
is in neither the element library (`components/elements`, `format/email`) nor
the brand's own `email-sms/email-types.json` — with the real ones named. The layout
(`simple`) is checked against `template/email`. Both are recorded in
`run.json` under `elements`.

**The old email's furniture never reaches the writer** (2026-09-20). Step 1
(`stage1-read-v2`) records THE MESSAGE, PAGE FURNITURE (logo row, nav, category
links, social row, footer, legal) and SOURCE DEFECTS (dropped letters, dead
merge tags, typos) under separate headings. Step 2 (`stage2-spec-v2`) builds
from the message only. Every step after step 2 is handed the record with the
furniture section taken out (`email.message_only`).

**Brand words live with the brand.** `machine/brand_facts.py` reads, at run
time: the brand's furniture words (`brands/<brand>/email-sms/simple.json` →
`furniture`, plus its name, tagline and sign-off), its product names
(`products/store.json` + the product files), its store and key names
(`email-sms/machine.json` → `shopify`, `loop_key`), and which brand a run belongs
to (the run's own `run.json`, never a folder-name prefix).

## The Klaviyo approval page (2026-10-09)

the owner: *"Similar to how I have an approval page for Meta, I need the same exact thing,
but for Klaviyo."* `approve_klaviyo.py` (http://localhost:8798, launch config
`klaviyo-approve`; `--fake-klaviyo` on 8799 for trials) shows every email card at
`runs/email-production/<brand>/<label>/klaviyo/card.json`: the email as it will go out,
its segments resolved through the audience matrix, the day and send hour, subject and
preview, every link with whether it answers, and the flags to see first. **Approve**
(held while a link is dead or a segment has no id) uploads the pictures to Klaviyo and
makes a DRAFT campaign through `simple_email.create_draft`; nothing is scheduled or sent.
**Send back** writes reasons + note to the card and `runs/email-production/<brand>/learnings.jsonl`.
Cards are built per week by the week's own builder (first: `runs/email-production/Brand A/week-2026-10-12/klaviyo_build.py`), then `final_check.py` writes each card's final check (links, subject/preview, unsubscribe tags, alt text, picture sizes, never-use names, product check, no picture shared across the week); Approve is held until it passes. The page's header reads the Klaviyo connection and each segment's size (read-only, kept 10 minutes).

## The design line, any brand (2026-10-17)

Designed emails run through `design/` for every brand: the calendar marks each send design or letter
(`components/marketing-calendar/machine/kinds.py`), `design/line.py` writes each send's job card and
layout from its finished copy (prompts `design1-jobcard-v1-owner.md`, `design2-layout-v1-owner.md`),
`design/engine.py` renders the layout in the brand's look (`brands/<brand>/email-sms/design-system.json`),
`design/build.py` cuts it for Klaviyo and writes the approval card, `design/check.py` runs the final
check across the batch. The whole process: `EMAIL-DESIGN.md`.
`design/repick.py <brand> --run <run>` (step 2b, prompt `design2b-repick-v1-the email lead.md`) chooses a laid-out email's
brand photos and customer pictures again by what each one shows, keeping every section and word, then rebuilds and
re-checks it (the email lead, 2026-10-28: layouts made before then picked photos by file name).
**A brand's house look** (LD-101 (Brand B house look), built 2026-10-30, told to the owner after): a look file with a
`house` block (`sections`, `styles`) gets its house sections offered to the layout, and the emails laid out from then
on are marked `"look": "house"`: engine.house() puts the house styles under each section's own (the email wins), every
picture is made at its box's shape, a person or a picture appears once, and customer sections show only customers'
words (`notes`) or creators cleared for email (`on_camera`, asset-index search use="email"). Emails laid out before
keep their own look. Tests: `design/test_ld101_house_look.py`. The Brand A week folder
(`runs/email-production/Brand A/week-2026-10-12/`) is where it was first built by hand, kept as history.

## The four questions (components rule, answered once)

- **Engine + owner** — `email_line.py`, `simple_email.py`, `run_month.py`,
  `copy_plan.py`, `brief.py`, and `machine/` (new code: `brand_facts.py`,
  `email_elements.py`). the owner. The older Python files stay at the folder root
  until the rollout's renaming pass, because the calendar's hand-off and two
  scheduled jobs call them there.
- **Definitions + curator** — `prompts/` (one per step in `email_line.py`'s `STAGES`) and each brand's
  `email-sms/simple.json`. the owner curates both; a prompt changes by a new `-vN-`
  file, and the highest wins.
- **The plane it emits** — `runs/email-production/<brand>/<label>/`: every
  step's prompt as sent beside its output, `run.json` (what the email was told
  to argue, which model wrote each step), and `deliverable/` — `email.json`,
  `preview.html`, `check.json`, `pushed.json`. Pictures are media and go to
  `Shared Assets/runs/email-production/<brand>/<label>/` on the Drive —
  through gdrive-creator by file id when GDRIVE_SA_KEY is in the environment,
  else through the shared mount, else kept in the run's `media/` with the
  reason printed (`drive_reach.py`, SI-38 (email Drive reach)). A records
  adapter onto `platform/data/records/` is owed.
  Brand facts the pull, sweep and refresh scripts make (offers, store,
  products, layouts, sends, the offer bank) are a PROPOSAL under
  `runs/email-production/<brand>/facts-<YYYY-MM-DD>/` (`PROPOSAL.md` names each
  `brands/` target and the copy command); the email lead folds them in by her own
  commit, and `paths.refuse_brand_write` refuses any write path under `brands/`
  (SI-21 (email facts proposals), K2 (brands write wall), 2026-10-07). Every
  reader keeps reading `brands/`.
- **Manifest per entry** — `run.json`: the assignment, the model per step, the
  prompt file and its hash per step.

## QC

The checks and the hold are the shared ones — `components/marketing-chain-checks`
(`import marketing_chain_checks as Q`). This folder keeps no copy of them.

- **The elements gate — before any spend.** The send's type and the layout are
  real ones (above). `email_line.py` exits `HELD at the elements gate`.
- **The delivery gate — before Klaviyo.** `simple_email.py` runs three shared
  checks, gives every problem an id (`Q.item`) and calls
  `Q.hold("delivery", kept, deliverable/, items=…, cleared=…)` — a problem a
  person's standing ruling clears is dropped and listed under `cleared` (HE-1 (fact rulings)):
  - `Q.price_check` + `Q.offer_block` — every price in the email is one the
    offer bank sells today for that send's offer. Added after the first email
    sold a size the store no longer carries.
  - `Q.read_check_block` — the chain's own check step (8c,
    `prompts/stage8c-check-v1-owner.md`): product facts, chopped thoughts, typos.
    An email with no step 8c is held too.
  - `Q.unfilled_check` — no `[UNFILLED …]` note in the finished email.
  - **One text** (LD-105 (check the designed email), 2026-11-04): where a run has `design/email.json`, the gate
    reads the designed email's words (`designed_email.py`), not the writer's copy: a step-8c finding whose line is
    gone from the page is listed under `cleared` "by the designed email", and every credited quote is checked against
    the brand's language bank and the language layer's lived-moments index (`quote-credit`: a Reddit or YouTube line
    credited to a customer holds, naming the source). `design/build.py`'s product check carries the same credit rows,
    so the editor's card shows them. An email with no design is read as before. Tests: `test_ld105_check_designed_email.py`.
  - `link-tags` — every link to the brand's own sites carries the tracking standard's email
    tags (the owner, 2026-10-12: stitch funnel data end to end). `simple_email.finished_html()`
    writes them (`machine/email_links.py` over `components/funnel-tracking`'s
    `standard.json` → `email_url`; nothing restated here): utm_source/utm_medium from the
    standard, utm_campaign = the send label, utm_content = `<label>.<section>` (logo, button,
    cta), utm_term = the send's segment(s), `funnel=` on a CPK funnel page. Unsubscribe,
    mailto/tel, merge-tag and partner links are left alone. The gate reads the finished HTML
    back and holds any own link missing a tag; `--push` and `klaviyo_upload.py` re-check the
    HTML that actually goes to Klaviyo, and every draft sets Klaviyo's own UTM tracking
    (`tracking_options`) to the same values. `section_email.py` tags its two outputs too.
    Tests: `python3 test_email_links.py` (no network).
  Anything found: nothing goes to Klaviyo, the command prints
  `HELD — not sent to Klaviyo:` with every problem, and
  `deliverable/check.json` says so in the shared, gate-keyed shape —
  `{"delivery": {"result": "pass" | "HELD", "problems": [...], "items": [{id, kind, quote, files_say, text}], "cleared": [{id, kind, ruling, by, at}]}}`.
  (It used to write `{"prices": "FAIL"}` whatever the failure was.) Rule on a
  held problem with `python3 ../quality-checks/rule.py <run folder> <id> <wrong|true|true-once|fill|not-ours> ["fact"] [--reason …] [--by …]`;
  prices are never ruled — fix the offer bank (decision log 2026-10-01).
- **The team's checks** (`components/qc-checks/`): run the text check and the
  voice check on a deliverable — `/qc-check runs/email-production/<brand>/<label>/deliverable`.

## History kept here, not live

`design_email.py`, `render_email.py`, `figma_*.py`, `render.py` and
`push_klaviyo.py` built the designed-template email. The simple shape replaced
them on 2026-09-19. They are kept because runs made with them point at them,
not because anything calls them. `results/` is the record of runs made before
output moved to `runs/` (2026-09-17) and is history. Since 2026-10-07
(email-production#19) compose, live_read research, affiliate, derive, the
drafts page and the review page also write under
`runs/email-production/<brand>/<label>/` through `paths.run_home`; `results/`
is read only as pre-move history.
