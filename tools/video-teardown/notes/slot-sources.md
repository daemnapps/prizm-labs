# The ten slots, and where each one comes from

**For the developer.** Every `[SLOT: …]` the chain emits is one fact nobody has supplied.
There are ten of them. This says exactly what each fact is and where it has to
come from, so the missing sources can actually be built.

Derived from `new-workflow-design/builds/video-teardown/slots/registry.json`
(2026-08-19), which is the machine-readable version — `check_slots.py` reads it
to gate a brief. If the two ever disagree, the registry is right.

**Goal this serves:** briefs going out end to end. Sorted by what stands in the
way of that.

---

## How to read it

| Kind | Meaning |
|---|---|
| **Build it** | No source exists. Something has to be created. |
| **Exists** | The source is already there; the chain just isn't reading it. |
| **Permanent** | Deliberately never filled from a file. Not a defect, ever. |
| **Deferred** | A known hole, ruled not to block for now, cost accepted. |

---

## Blocking briefs today

### 1. `[SLOT: customer_count]` — Exists

**What it is.** How many customers have bought, as a figure we can defend in an
ad. It is the single biggest hole in the chain: 50 of 108 slot instances.

**Where it comes from.** Two candidate sources, both real:

- Marketing Hub → **Product Intelligence** tab
  (Drive `<sheet id>`), Founder via the ops lead.
- **`order_economics`** — live in production, 2,525 orders from 2025-11-01,
  carries `customer_id`. A distinct count is one query.

**Caveat that matters.** `order_economics` starts 2025-11-01, so it yields
"customers since November", not all-time, and 2,525 is orders — distinct
customers is fewer. Whatever number is used must carry its definition and its
date; two unreconciled counts already exist.

**Cost of leaving it.** From the e2e brief's own internal doc: the
"X women are using it" clause was **cut from both concepts**, so neither video
carries any social proof at all. The only proof left is the scrub visibly
dissolving and the guarantee.

**Done when.** Either a defined, dated number is readable by the chain, or the
proof beat is rebuilt without a count (draft exists:
`the developer's lab/prompt-optimizer/prompts-drafts/stage4c-expansion-v3-DRAFT.md`).
the owner's ruling, open as T-33.

---

### 2. `[SLOT: identity_anchors — <role>]` — Half exists

**What it is.** Who appears on camera in each role, plus their reference photos
and their consent. Roles seen so far: `subject`, `second_user`, `third_user`,
`ugc_creator`, and a founder presenter. 28 instances across eight spellings.

**Where it comes from.**

- **Names**: the creator manager's Creator Tracker
  (Drive `<sheet id>`). Deliberately not
  mirrored into the repo.
- **Reference photos**: the shared drive. No agreed location yet.
- **Consent**: nowhere. Nothing records whether a person agreed to unretouched
  close-ups.

**Done when.** A role can be resolved to a named person, a photo, and a recorded
yes. The names half is the owner's (T-35); the photo location and the consent record
are the parts that need designing.

---

### 3. `[SLOT: source_post_url]` — Exists upstream, not plumbed through

**What it is.** The link to the creator's own post a concept was built from, so
she can open it and watch what the video is imitating. Added 2026-08-19 when the
brief was ruled to hand her the inspiration as a link, never as a caption she has
to recognise.

**Where it comes from.** The ingest already captures post URLs into the creator
dossier. They never reach
`brands/<brand>/channels/creators/<creator>.md` — the file stage 5 actually
reads — which names posts by rank and caption and carries **zero URLs**.

**Done when.** The creator profile carries the URL alongside each ranked post.
This is plumbing an existing value through one more file, not finding new data.
**This is the one that blocks the new brief format**, because every concept opens
with the link.

---

## Sources exist, the chain just isn't reading them

### 3. `[SLOT: timeframe]` — Exists

**What it is.** How long results take, phrased as something we can stand behind.

**Where it comes from.** The results-timeline rules already written in
`brands/<brand>/customer/language-bank.md`. They exist; they have never been
ruled, so no stage will commit to them.

**Done when.** The timeline rules are ruled once. Then it is permanent and the
slot never appears again.

---

### 4. `[SLOT: maker_voice]` — Exists

**What it is.** Who speaks the script — founder, contracted creator, or
generated.

**Where it comes from.** `{production_route}`, already a run-time variable. It
appears as a slot only because a run started without naming the route.

**Done when.** The runner requires a route before stage 3, instead of letting the
chain discover halfway through that it doesn't know whose voice it is writing.

---

### 5. `[SLOT: product_file — <product>]` — Build it

**What it is.** A product's ingredients and claims, for a product that has no
file. Seen for a second product (a body cream) while only the scrub has one.

**Where it comes from.** `brands/<brand>/products/<product>.md` — the file has to
be written, in the same shape as the existing body-scrub file.

**Done when.** The file exists. This is the one case where filling the slot is
the wrong fix — writing the file is the fix.

---

## Permanent by design — never fill these from a file

### 6. `[SLOT: current_promotion]` — Permanent

**What it is.** The live offer running when a brief goes out.

**Where it comes from.** The **Pricing Logic sheet**, read by a person at the
moment the brief is sent. Only the founder adds offers.

**Why it never becomes a file.** A promotion written into the repo is wrong the
day it changes. The slot surviving into the brief is the design, not a failure —
it is listed under *fill before send* and a human closes it on the way out.
(the owner, T-34; implemented in `stage5-brief-v2-DRAFT.md`.)

---

### 7. `[SLOT: price_claim]` — Permanent

**What it is.** Any price, discount or saving stated in a script.

**Where it comes from.** The Pricing Logic sheet, the ops lead's authority, at send
time. Same reasoning as above: a price in a repo file is a price that will be
wrong.

---

### 8. `[SLOT: maker_origin]` — Permanent

**What it is.** The creator's own one-line origin story, in her own words.

**Where it comes from.** Her, when she shoots. Stage 5 deliberately hands a
contracted creator directions rather than lines, because her wording is the
reason she works — and in the e2e run the alternative was worse: Creator F cannot
truthfully say a Thai family recipe is hers.

**Why it never becomes a source.** Writing it for her is the failure mode, not
the fix. Listed for visibility; never blocking; never ours.

---

## Deferred

### 9. `[SLOT: music_track]` — Deferred 2026-08-19 (the owner)

**What it is.** The actual track a video is cut to. Appeared five different ways
in a single run, each carrying different specifics (~30s, clean tail at 0:26,
low volume, full 34s).

**Where it will come from.** Generated — Suno or similar, plus a sound-effect
API — wired later. Not now; briefs going out end to end comes first.

**Meanwhile.** Briefs fall back to Instagram's in-app audio library.

**Known cost, accepted.** In-app audio carries no ad rights, so **a video cut to
it cannot be run as paid** without a re-cut against a licensed or generated
track. Recorded so the cost stays visible rather than being discovered later.

**Done when.** A generation or licensing route exists and the chain can name an
actual track. The canonical slot name applies from that day.

---

## Checking any brief

From `new-workflow-design/builds/video-teardown/`:

```bash
python3 slots/check_slots.py <path-to-brief>        # the ship gate
python3 slots/check_slots.py results/ --mode all    # everything still open
```

Exit `0` clear · `1` slots outstanding · `2` a slot it could not place.

That third one matters: an unregistered spelling makes the checker refuse a
verdict rather than pass. It is how a new fact gets caught the first time — which
is exactly how three of the nine above were found.

**One naming rule holds it together.** Canonical form is
`[SLOT: fact_id]` or `[SLOT: fact_id — detail]`, `fact_id` always lowercase
snake_case. Two reasons: 17 spellings for 6 facts meant no check could match
them, and the build's safety greps only match `[a-z_]+` — so a capital letter
makes a slot invisible to every check that exists.
