# The Market Research System — from avatar to brief, on autopilot

the owner's frame (2026-08-30): a higher-level market research system, fleshed
out BEFORE any accounts get made. Multiple avatars → multiple persona
accounts → feeds → keep → download → teardown → brief. Test with one,
built for many. This doc is the blueprint; each station names what exists
and what's pending.

## The pipeline, end to end

```
 STATION 1          STATION 2           STATION 3         STATION 4
 PERSONAS           FEEDS               KEEP              TEARDOWN
 one trained        everything the      the posts worth   kept post →
 account per        avatar's world      copying get       downloaded →
 avatar, its FYP    serves, cataloged   flagged, and      transcribed →
 = the avatar's     w/ dates + rising   pulled down       teardown chain
 actual feed        signal              to Drive          → brand brief
 (pending: human    (BUILT)             (designed below)  (chain BUILT,
 makes accounts)                                          hookup pending)
```

Everything flows into the same per-avatar folders under
`records/avatar-feeds/` — the feed backend is the spine of the whole
system. New stations add fields and files; they never fork the data.

## Station 1 — the persona fleet

One dedicated account per avatar per platform (TikTok first — richest
signal; IG second — unlocks suggested-accounts; YT third). Each persona:

- **Starter kit** (BUILT: `records/persona-kits/<avatar>/`) — sourced
  follow list, hashtags, sounds, warm-up protocol.
- **Registry** (`records/personas/<avatar>/persona.json`) — handle,
  platform, status (warming | trained | flagged | retired), created
  date, device/IP note. **Never credentials** — logins live in the key
  file (`~/.daemn/keys.env` pattern), not in git.
- **Watch sessions**: scheduled browser sessions at human pace, 1–2/day.
  Watch-through = vote yes; fast skip = vote no; the kit's categories
  define which is which. Watch only — never post, comment, follow-spam.
- **Capture**: every post the FYP serves is recorded to the feed backend
  as source `kind: persona-fyp` — trained-algorithm output, the highest-
  value source in the system.

Ban math, stated honestly: automated viewing is against platform rules;
watchers are the quietest actors but flags happen. A lost persona costs
a free burner + 2 weeks retraining — never the brand (hard wall: no
brand follows, separate email, nothing linking back). Feeds keep
running on hashtags + hops during any gap.

## Station 2 — the feeds (BUILT)

`FEEDS.md` is the full spec: catalog / observations / sweeps / entry
rules / graph hops / probation sources / the self-rebuilding page.
Curation is signal-only — no human in the learning loop.

## Station 3 — keep, download, organize

Selection for PRODUCTION is a human/team call (distinct from feed
curation, which stays automatic): someone flags "this one's worth
copying."

- **Keep** = a status flip on the item in `items.json`
  (`status: kept`, plus `kept_by`, `kept_at`). The catalog already
  carries `status` human-owned by design. Interface for the team:
  pending decision — page button (needs a hosted page or artifact
  runtime) vs. flag-by-link. Whatever the interface, the record is the
  same field.
- **Download**: kept items get pulled down automatically (video +
  cover + caption) to Drive, mirroring the repo path —
  `Shared Assets/lab/swipe-organic/avatar-feeds/<avatar>/kept/<item-id>/`
  (media never in git; the item record gets a `**Drive:**` pointer).
- **Organize**: nothing new to invent — the item already carries its
  avatar (folder), category, source, receipt, and signal history. Kept
  items ARE the organized library, filterable on the feed page.

## Station 4 — teardown → brief

The teardown chain already exists (video teardown → replication spec →
brand injection; `new-workflow-design/builds/video-teardown/`). The
hookup: a kept item's downloaded video + transcript feed stage 1; the
item id rides through so every brief traces back to the exact post,
its signal history, and the persona/source that surfaced it. Output
lands beside the item (`teardown/` in its kept folder) and in the
brief bank for production. This hookup is next week's production-
pipeline work — the interface (kept item in, brief out) is fixed now
so the stations build independently.

## Launch plan

- **Phase 0 (now)**: this blueprint; kits built; registry scaffolded;
  feed spine live for avatar-two.
- **Phase 1 (one probe)**: the owner creates ONE TikTok account
  (avatar-two). 2-week warm-up per kit protocol. Prove: FYP locks onto
  the avatar (measure: % of served posts matching kit categories),
  capture flows into the backend, zero flags.
- **Phase 2 (fleet)**: one persona per avatar per platform, staggered
  creation (never a batch of signups from one device/IP in one day),
  one device profile each. Avatar-one and Brand A avatar-four next —
  their kits generate from the same data the moment their feeds exist.
- **Phase 3 (full loop)**: keep-interface live for the team, download
  + teardown hookup running, briefs flowing to production.

## The measure of the whole system

One number per avatar per week: **briefs shipped that trace to a
rising post the system surfaced**. Everything above exists to move it.
