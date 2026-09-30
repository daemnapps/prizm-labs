# _TEMPLATE — the brand folder every brand copies

A new brand starts as a copy of this folder. Every tool in this kit reads a
brand through exactly these names, so a brand is set up once and never
explained again. This is the **v6 layout** (approved 25 Sep 2026): one layout
for every brand, the same names on GitHub and on the Drive — words here, media
on the Drive at the same path.

```
<brand>/
  README.md             what this brand is
  FOLDERS.json          new folder name -> the old names it replaced
  brand-identity/       story.md, position.md, the look (palette, fonts, web tokens, logos), voice, rules
  core-avatars/         the customer types, sub-avatars, their exact words, objections, research
  products/             one folder per product: facts here, photos and video on the Drive
  offers/               offers, guarantees, the standard box, the offer bank
  strategy/             calendar/ · angles.json (the one angle source) · goals/
  ai-elements/          everything AI-generated
    characters/         every AI character, filed like content-creators, with a talent card
    environments/       places and sets
    props/              objects used in shots
    element-facts.json  what is true of each element, appended to every prompt that uses it
  content-creators/     real creators and their footage, with a talent card each
  brand-assets/         photo shoots and brand videos (media on the Drive)
  intake/               what the brand already has: ads, organic, emails, landing pages, reviews
  ads/                  the ads that are live · formats/ · hooks/ · top/
  email-sms/            the emails and texts that are live · formats/ · hooks/ · top/
  web/                  the pages and live links · formats/ · hooks/ · top/
  competitors/          competitor brands, assigned per avatar
  variables/            every copy fill-in, one map per surface
  customer-experience/  support playbook, ticket themes, sentiment, NPS, social comments
  learnings/            results read and fed back into the rest of the folder
  briefs/               the editor brief queue
```

Every folder has a one-line `README.md` saying what goes in it.

**No loose files at the top.** Story and position live in `brand-identity/`.
There is no single hook ledger: ads, email-sms and web each keep their own
`hooks/`.

**Team-only folders are not part of this kit.** A team running this kit may
keep money, ad-account and working-notes folders beside these (`operations/`,
`meta/`, `context/`); they are never shared and no public tool needs them.

## Old folder names still work

`FOLDERS.json` maps each folder to the names it replaced (`identity` →
`brand-identity`, `ai-cast` → `ai-elements/characters`, `creators` →
`content-creators`, `email` → `email-sms`, `existing-content` → `intake`, …).
Every tool in this kit reads the new name first and the old one after, so a
brand that has not moved yet keeps working.

## The four axes a brand runs on

Everything a brand makes is one point in four independent axes
(`components/naming/MODEL.md`), and each axis has exactly one home:

| Axis | Answers | Lives in |
|---|---|---|
| **Avatar** | who is this for? | `core-avatars/<slug>/profile.md` |
| **Angle** | what are we claiming? | `strategy/angles.json` |
| **Channel** | where does it run? | shared, not per brand — `copy/bank/channel-map.json` |
| **Format** | how is it built? | each channel's `formats/` (`ads/`, `email-sms/`, `web/`) and the shared banks in `components/naming/registry.json` |

**An angle is channel-free and format-free.** The same claim runs as a paid
static, an organic video, an email and a landing page. A thing that only works
in one container is a format.

Rules that travel with the folder: brand context is read-only to tools during a
run · every fact derived, never typed · one variable vocabulary across tools ·
one avatar per piece.
