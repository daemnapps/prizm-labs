# email-production — the writing, the pictures, the Klaviyo draft

**email-production** — takes **a calendar send**, makes **the email — copy,
pictures, layout — and a Klaviyo draft**. Does not **send**. Triggered by
`python3 run_month.py <calendar run> --only <send ids>` (a month or a week), or
`python3 email.py <source> --brand <brand> …` then
`python3 simple_email.py <run folder> --brand <brand>` for one email.

**Owner:** the owner · **Station:** `components/` — moved in 2026-09-19 ·
**Held-emails development:** the email lead (2026-10-01, decision log; named here by
the developer, 2026-10-07, triage action 3 (definition lines and registry rows))

Runs by: both

> Moved from `lab/email-production/` on the owner's word, 2026-09-19:
> *"move these tools out of the lab… straight into the real production repo,
> components… so we can actually run QC on it as well… and everybody can have
> access to these things."* Settled by system review (the 2026-09-21 ruling: a
> move is the owner's act and a review follows it; email-production#14).

**Stage two of the email line.** Stage one — brand record → calendar → review
→ hand-off — is `components/marketing-calendar/`. This component takes each
send that stage hands it and turns it into an email in a Klaviyo draft:

1. **Writing** — `email.py`, the steps its `STAGES` list declares, each with its own prompt in
   `prompts/` and its own model (Haiku reads, Sonnet checks, Opus designs; a
   prompt too big for a small model moves up on its own).
2. **Pictures** — `simple_email.py`: GPT makes the hero picture from the
   direction step 8 wrote, and the offer picture FROM the real product photo.
3. **Layout** — the same simple shape for every email (the owner, 2026-09-19):
   logo, headline, hero picture, the copy, an optional offer picture, one
   button, sign-off, footer. Each brand's look is `brands/<brand>/email-sms/simple.json`,
   read off that brand's own last sent email.
   **Moving to formats (2026-10-08):** every send gets a format — a stack of
   sections with a fixed picture count, each picture from a real-life
   reference first. `EMAIL-FORMATS.md` is the map; `simple` is one of them.
4. **Klaviyo** — `simple_email.py --push`: a DRAFT campaign to the send's own
   segment, main subject line, set for the calendar's day at the brand's send
   hour in each recipient's time zone. There is no send call. A person presses
   Schedule.

The full chain, every prompt word for word and the knobs in order:
**The Email Chain** — (team page)
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

`run_month.py` ends `done · N built, M held, K failed · S skipped`; a held email
waits on a ruling and exits 0 — only a failed one exits 1 (HE-2 (held not failed)).
    python3 test_klaviyo_upload.py                                     # the uploader's tests — free
    python3 email.py <source> --brand <brand> --avatar <avatar> --dry-run   # the free check
    python3 doctor.py --brand <brand>                                  # is the brand wired — free
    python3 test_rollout.py                                            # the tests — free

**The dry run is free, and it writes nothing** (2026-09-20). `email.py --dry-run`
stops before step 0: no model call, no folder under `runs/`. It prints every
input with where it was found, the language rows each step would get, which
model each step would run on, and where the run would file. What only step 0
can know — lane, format, sender — is reported as "decided at triage". The
doctor uses the same dry run and no longer has anything to clean up.

**The send's type is checked before anything is spent.** A calendar send's
`type` is an email format. `brief.py` passes it to the chain as `--type`;
`copy_plan.py` blocks, `run_month.py` skips, and `email.py` refuses a type that
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

## The four questions (components rule, answered once)

- **Engine + owner** — `email.py`, `simple_email.py`, `run_month.py`,
  `copy_plan.py`, `brief.py`, and `machine/` (new code: `brand_facts.py`,
  `email_elements.py`). the owner. The older Python files stay at the folder root
  until the rollout's renaming pass, because the calendar's hand-off and two
  scheduled jobs call them there.
- **Definitions + curator** — `prompts/` (one per step in `email.py`'s `STAGES`) and each brand's
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
  `brands/` target and the copy command); the brand editor folds them in by her own
  commit, and `paths.refuse_brand_write` refuses any write path under `brands/`
  (SI-21 (email facts proposals), K2 (brands write wall), 2026-10-07). Every
  reader keeps reading `brands/`.
- **Manifest per entry** — `run.json`: the assignment, the model per step, the
  prompt file and its hash per step.

## QC

The checks and the hold are the shared ones — `components/quality-checks`
(`import marketing_chain_checks as Q`). This folder keeps no copy of them.

- **The elements gate — before any spend.** The send's type and the layout are
  real ones (above). `email.py` exits `HELD at the elements gate`.
- **The delivery gate — before Klaviyo.** `simple_email.py` runs three shared
  checks, gives every problem an id (`Q.item`) and calls
  `Q.hold("delivery", kept, deliverable/, items=…, cleared=…)` — a problem a
  person's standing ruling clears is dropped and listed under `cleared` (HE-1 (fact rulings)):
  - `Q.price_check` + `Q.offer_block` — every price in the email is one the
    offer bank sells today for that send's offer. Added after the first email
    sold a size the store no longer carries.
  - `Q.read_check_block` — the chain's own check step (8c,
    `prompts/stage8c-check-v1-damon.md`): product facts, chopped thoughts, typos.
    An email with no step 8c is held too.
  - `Q.unfilled_check` — no `[UNFILLED …]` note in the finished email.
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
