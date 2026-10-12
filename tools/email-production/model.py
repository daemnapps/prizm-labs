#!/usr/bin/env python3
"""The email system's shape, as data. Read by build_system.py.

Scope, set by the owner 2026-08-27: **campaigns only**, and only three things —
brand context in, a dynamic calendar, an email out. Delivery, feedback and
flows are real and are parked on their own page, not dropped.

Two corrections from the same call, both kept here so they are not undone:
- Sender identity is not brand-root. It belongs to the email — a founder
  email is rich text with a name card, which is a FORMAT decision, and the
  sender follows from the format.
- Language upkeep is out of scope entirely. What matters is that the system
  can read the language that is there.
"""

# What the brand folder actually holds, read 2026-08-27 from
# the brand folder. bytes → whether it is real content or a stub.
BRAND = dict(
  what="The folder everything reads and nothing writes. Two lanes that never "
       "blend, each with its own avatar, objections, offers and language.",
  map="`chain-variables.md` is the contract: one variable, one file, zero "
      "variance. A run declares lane + lifecycle + product, and that picks "
      "the files. Nothing is guessed.",
  groups=[
    ("Who", ["core.md — the avatar, per lane",
             "11 sub-avatars (brotherhood)",
             "identity-anchors.md — who may appear"], "full"),
    ("What they say", ["language/ — split 9 ways by lifecycle",
                       "prospect · lead · customer (base, one-time, repeat, "
                       "loyal, vip, subscriber) · churned (×2)"], "thin"),
    ("What stops them", ["core-avatars/objection-bank.md, per lane"], "full"),
    ("What we sell", ["14 product files", "products/offer-bank.md, per lane"], "full"),
    ("What we already said", ["hook-ledger.md, per lane"], "stub"),
    ("What worked", ["existing-content/ — paid ads, organic posts, landing pages"], "thin"),
  ],
  fill=[
    ("brotherhood", "core", 14685, "full"), ("brotherhood", "objections", 14402, "full"),
    ("brotherhood", "offers", 6660, "full"), ("brotherhood", "hook ledger", 496, "stub"),
    ("brotherhood", "prospect", 1752, "thin"), ("brotherhood", "lead", 534, "stub"),
    ("brotherhood", "customer/base", 30734, "full"),
    ("brotherhood", "customer/one-time", 644, "stub"),
    ("brotherhood", "customer/repeat", 638, "stub"),
    ("brotherhood", "customer/loyal", 635, "stub"),
    ("brotherhood", "customer/vip", 629, "stub"),
    ("brotherhood", "customer/subscriber", 712, "stub"),
    ("brotherhood", "churned ×2", 637, "stub"),
    ("two-oh", "core", 10303, "full"), ("two-oh", "objections", 12963, "full"),
    ("two-oh", "offers", 5261, "full"), ("two-oh", "prospect", 33973, "full"),
    ("two-oh", "lead", 466, "stub"),
    ("two-oh", "customer/churned", 0, "none"),
  ],
  finding="**Each lane has exactly one full language bank and the rest are "
          "stubs.** brotherhood is deep on customers, two-oh is deep on cold "
          "prospects — which is right, they are at different stages. But it "
          "means lifecycle targeting is currently two banks, not nine. The "
          "fallback rules already handle it (`customer/*` falls back to "
          "`customer/base`), so nothing breaks — the calendar just cannot be "
          "more granular than the language behind it, and should not pretend "
          "to be.",
)

STAGES = [
 dict(key="1", name="The dynamic calendar", short="C",
   what="Brand context in, a list of slots out. A slot is one campaign, "
        "fully specified before anyone writes a word.",
   dynamic="A fixed calendar is a list of dates someone filled in. **A "
           "dynamic one composes slots out of the brand's own dimensions** — "
           "which lane, which lifecycle, which product, which job — and "
           "covers that space deliberately instead of repeating whatever went "
           "out last month.",
   dims=[("Lane", "2", "brotherhood · two-oh — never blended"),
         ("Lifecycle", "9", "structurally; 2 have real language today"),
         ("Product", "14", "each with its own file and offer"),
         ("Job", "—", "educate · prove · handle an objection · launch · offer")],
   flows=[
    ("C-1", "The year", "The brand's own moments and demand shape — which "
     "months lean, which maintain.", "part"),
    ("C-2", "Responsiveness per segment", "What each segment and avatar "
     "actually does when it is sent to — engagement, revenue per recipient, "
     "and what happens to both as frequency changes. This is what decides "
     "cadence; nothing is set by rule.", "miss"),
    ("C-3", "The audience vocabulary", "A fixed named set of segments, each "
     "one mapped to exactly one lifecycle — so a slot can name who it is for "
     "and the right language bank follows.", "decide"),
    ("C-4", "Compose the sequence", "Not a list of independent sends — an "
     "ordered arc. Each move knows what it earns, what it sets up, and what "
     "must follow it. The dynamic part.", "miss"),
    ("C-5", "Choose the source", "Which swiped email this slot gets built "
     "from.", "miss"),
   ]),
 dict(key="2", name="Email production", short="P",
   what="One slot and one source in; subject lines and a finished email out.",
   dynamic="",
   dims=[],
   flows=[
    ("P-1", "Resolve the context", "The slot's lane, lifecycle and product "
     "select the exact brand files this email reads. Automatic — that is what "
     "`chain-variables.md` is for.", "built"),
    ("P-2", "Choose the email's form", "Founder note, designed promo, plain "
     "text, editorial. **This is where sender identity is decided** — a "
     "founder email is rich text with a name card and goes out under a "
     "person; a promo is a built template and goes out under the brand. The "
     "form decides the sender, not the other way round.", "part"),
    ("P-3", "Run the chain", "Ten stages: triage, read, spec, scout, inject, "
     "place, subject lines, expand, close, build, brief.", "built"),
    ("P-4", "The pick", "You read the page, choose the subject line and its "
     "preview, approve or send it back.", "miss"),
   ]),
]

PARKED = [
 ("Delivery", "Building it in the platform, images, links, QA, scheduling. "
  "Mechanical, and almost all of it is calls we can already make."),
 ("Feedback", "What each send earned, back onto the slot that asked for it; "
  "subjects onto the ledger; winners back into the swipe file."),
 ("Flows", "A different product entirely — installed once, sends forever on a "
  "trigger. Set up quarterly, and eventually per avatar."),
]

# What an email can be ABOUT. Four wells, each doing a different job on the
# relationship. the owner named all four; the ordering is his emphasis.
# ---------------------------------------------------------------------------
# CATEGORIES — recut 2026-08-27 after the owner caught the overlap.
#
# The first cut mixed three logics: some categories were cut by SUBJECT
# (skin = educational), some by INTENT (promotional = asks), some by SOURCE
# (community = customers). Mixed logic guarantees overlap — which is exactly
# why entertainment looked like cultural and mission looked like community.
#
# One logic now, and one test: WHOSE MATERIAL IS THIS EMAIL MADE OF?
# Every email has exactly one answer. Five categories, no overlap.
# ---------------------------------------------------------------------------

CUT_TEST = "Whose material is this email made of?"

WELLS = [
 dict(key="ask", name="Promotional", does="Made of our offer",
   what="A discount, a launch, a restock, a deadline. The material is the "
        "offer itself.",
   src="The offer bank, and the promo budget that says how many weeks a year "
       "may be one of these.",
   stock="stocked", detail="offer-bank per lane · 6.7k brotherhood, 5.3k two-oh",
   note="The only category that asks for money. Every one spent here is paid "
        "for by the other four."),
 dict(key="help", name="Educational", does="Made of our expertise",
   what="The skin, the problem, the mechanism — described the way THEY "
        "describe it, never in category language.",
   src="The language banks and the objection bank — 14,237 rows of real "
       "customer sentences, mined from 974 survey responses collected since "
       "April 2023 and still coming in.",
   stock="stocked",
   detail="14,237 language rows · 35k objection bank · 11k offer bank",
   note="An education email that ends with a link is still educational. The "
        "test is what it is MADE of, not whether it links."),
 dict(key="belong", name="Cultural", does="Made of the world outside",
   what="A moment, a season, a place, a subculture they are already inside. "
        "The summer sends that worked carried the NBA finals.",
   src="A moments file, per lane, built from what these sub-avatars actually "
       "follow. It does not exist yet.",
   stock="empty", detail="nothing on disk — the one empty category",
   note="The barbershop belongs here, and so does Texas. It is the world "
        "around the list, not the list itself."),
 dict(key="real", name="Community", does="Made of our customers",
   what="A named person and what happened to them. Not a testimonial block — "
        "someone from the room.",
   src="The quoted verbatims inside the language banks, each carrying its "
       "speaker and source. The 625-customer intelligence database that would "
       "stock this properly is NOT in this tree.",
   stock="thin",
   detail="verbatims yes · named customers with photos, results and "
          "transformation arcs: not here",
   note="Made of THEM — that is the line between this and Brand, and why "
        "mission does not live here. But a verbatim is not a person: this "
        "category needs customers with names, results and permission, and "
        "that source has not been brought into this tree."),
 dict(key="brand", name="Brand", does="Made of us",
   what="What we believe, what we are building, how it is made, what went "
        "wrong, who is behind it. Mission, the founder, the pharmacist, the "
        "position taken out loud.",
   src="Whatever is actually true and actually happening.",
   stock="thin", detail="a real founder and a real formulator · King's Month "
                        "is the nearest thing already sent",
   note="the owner asked whether mission is community. It is not: community is "
        "made of them, this is made of us. Same reason a founder note is not "
        "an education email even when it teaches something."),
]

# Not categories. These cut across every category and were the source of the
# overlap — a funny email about the NBA is CULTURAL, treated with humour; a
# funny founder story is BRAND, treated with humour.
TREATMENTS = [
 ("Humour", "Entertainment is not a category — it is how a category is "
  "played. It has no material of its own, which is the giveaway. Ask what a "
  "funny email is made of and the answer is always one of the five."),
 ("A question", "Research — a poll, a survey, a vote. Also a mechanic rather "
  "than a category: asking about a product is promotional, asking about their "
  "skin is educational. Worth doing far more (2 sends in 308) but not a "
  "category of its own."),
 ("No ask", "An email with deliberately nothing to click. A treatment, and a "
  "load-bearing one — it is what proves the other four are not a wind-up."),
 ("Proof", "Photos, numbers, results. Attaches to any category rather than "
  "being one."),
]

# The space a slot lives in. Every count is real, read off the brand folder
# and the customer base on 2026-08-27.
AXES = [
 ("Lane", "2", "brotherhood · two-oh. Never blended."),
 ("Segment", "6", "Loyal 225 · Returning 163 · One-Time 98 · VIP 76 · "
  "High-Value One-Time 51 · Prospect 8"),
 ("Sub-avatar", "11", "barbershop regular · bald bumps · ingrown fighter · "
  "el rey cansado · el jefe · 3 teen avatars · 3 gift-buying moms"),
 ("Awareness", "4", "Unaware 249 · Problem-Aware 230 · Solution-Aware 120 · "
  "Product-Aware 26"),
 ("Pain point", "7", "the tagged conditions people actually reported"),
 ("Product", "14", "each with its own file and offer"),
 ("Angle", "10", "Identity 601 · Loyalty 301 · Sensation 274 · Social Proof "
  "149 · Competitor Switch 120 · Results 112 · Emotional 110 · Timeline 43 · "
  "Body Zone 42 · Simplicity 37"),
]

# What the calendar does that a list of dates cannot.
RULES = [
 ("Order, not ratio", "How many emails ask is the low-level question. The real "
  "one is where a type sits in the arc — and whether that specific thing needs "
  "a follow-up. An ask that stands alone has nothing behind it; a question with "
  "no answer email was extraction. The arc governs order.",
  "miss"),
 ("Cadence is derived, never set", "There is no target number of sends and no "
  "fixed share that may ask. What goes out is decided by measured "
  "responsiveness per segment and per avatar, and by what a send earns. "
  "Frequency is an output of the data, not an input to the plan.",
  "miss"),
 ("Coverage", "The calendar tracks which cells of the space above have been "
  "cold longest — which sub-avatar has not been spoken to, which pain point "
  "has not been addressed, which awareness level is being skipped — and fills "
  "toward the gaps rather than repeating last month.",
  "miss"),
 ("Freshness", "Nothing is proposed that the ledger records as spent. 308 "
  "subject lines are already on it, with their preview text.",
  "part"),
 ("Fit", "A slot only reaches a segment whose language bank can actually "
  "carry it. Today that is two real banks per lane, not nine — so the "
  "calendar must not promise a granularity the language cannot deliver.",
  "part"),
]

# What comes out the other end — the object production receives.
BRIEF = [
 ("Date and segment", "when it goes and exactly who receives it"),
 ("Well and occasion", "which well this draws from, and the specific "
  "occasion — this moment, this person, this problem"),
 ("Audience", "lane · sub-avatar · awareness level, so the language resolves"),
 ("Job", "what this email should do to the reader"),
 ("Product", "what is being sold, or explicitly nothing"),
 ("Offer permission", "what it may offer, or that it may not"),
 ("The source", "the swiped email whose shape it is built on"),
 ("What it may not reuse", "the ground the ledger says is spent"),
]

# Gaps are first-class. A thin category is information, not something to pad —
# the owner's call, 2026-08-27. Every line here is verified against disk or the
# derived pulls; anything indicative says so.
GAPS = [
 ("Cultural has no source at all", "verified",
  "Five of its six types have never been sent, and the reason is upstream: "
  "there is no moments file anywhere in the brand tree. The category cannot "
  "be drawn from until something stocks it."),
 ("The customer database is not in this tree", "verified",
  "Community is the category with the most obvious fuel — named customers, "
  "photos, transformation arcs — and none of it is here. What is here are "
  "quoted verbatims inside the language banks, which support proof but not a "
  "person with a name and a face."),
 ("Nine-tenths of customer language is unsegmented", "verified",
  "8,524 of avatar-one's 9,525 customer rows sit in `unsegmented`. The "
  "source explains why: the survey has no order count and no subscription "
  "status, so voice cannot be split by one-time / repeat / loyal / VIP. The "
  "folders exist; the evidence to fill them does not. A slot cannot target a "
  "lifecycle the language cannot carry."),
 ("Two of the three avatars are thin, correctly", "verified",
  "avatar-one 13,254 rows · avatar-two 753 · gift-buyer 230. That is not "
  "neglect — avatar-two is a market with almost no customers yet and gift-buyer "
  "is a small, distinct audience. It does mean a run against either is "
  "working from far less, and should say so."),
 ("No sender identity, no products, nothing to swipe", "verified",
  "Three files that do not exist: `sender-identity.md`, a `products/` folder, "
  "and any email in `existing-content/emails/`. The last one is why the chain "
  "has never been run end to end."),
]
