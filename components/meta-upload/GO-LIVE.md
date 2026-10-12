# Prizm Labs Meta uploader — the path to uploading into any ad account

*Researched 1 Oct 2026 against Meta's developer docs (Marketing API v25/v26), Meta's business help centre,
and four open-source uploaders read line by line. Page: Prizm Labs Meta Uploader. The old team app is out
of the picture; this is one new app owned by Prizm Labs.*

## How it fits together

- **One app:** "Prizm Labs", use case *Create & manage ads with Marketing API*.
- **One business:** the app, its system users and the verification all sit in the same Meta business portfolio.
- **Every brand's ad account, Page, pixel and Instagram** is shared into that business as a partner, then
  assigned to one system user.
- **One key** (`daemn-PRIZM_META_TOKEN`) reaches every shared account. A new brand = a share + an
  `account.json`; no code change.
- **The tool** (`upload.py`): Graph API v25, Meta's flexible ad format (`creative_asset_groups_spec` on the ad —
  every picture/video of a unit in one ad), every Advantage+ AI enhancement switched off, Advantage+ audience
  on, ids back to the ledger by name, nothing uploaded without an approval.

## What Meta requires, by level

| | Limited (automatic) | Full (after review) |
|---|---|---|
| Ad accounts | unlimited | unlimited |
| Writes per ad account per hour | 300 + 40 × active ads (≈100 ad writes) | 100,000 + 40 × active ads |
| System users | 1 + 1 admin | 10 + 1 admin |
| Needs | the app published | business verification + 500 API calls in 15 days at < 15% errors, then App Review (no screen recording since 4 May 2026; decision ~1 week) |

**Not settled by Meta's docs:** whether a Limited app may write to ad accounts owned by *another*
business (Brand B LLC's, Brand A's) once they are shared in. One page says "your ad account → standard
access is enough", another says "other people's ad accounts → advanced access". One test write settles it.

**Known from our own runs:** the 11 Sep old-app writes failed with error #3 while the app was unpublished;
Brand A's account returned "(#200) Ad account owner has NOT grant ads_management" — it was never shared.

**Verification needs a registered legal entity** with matching documents (articles, registration,
government tax document or business bank statement) and an HTTPS website; up to 14 working days. The
the company portfolio is already verified.

## The steps (★ = only the owner can click)

1. ★ Pick the business that hosts the app (the one open call — see the page).
2. ★ developers.facebook.com → Create app "Prizm Labs" → use case *Create & manage ads with Marketing API* → connect that business.
3. ★ App settings → Basic: privacy policy URL, data deletion URL, 1024×1024 icon, category → Publish.
4. ★ Business settings → System users: one admin + one regular system user → give it the Prizm Labs app (full control).
5. ★ In each brand's business → Partners → share to the host business: ad account (Manage campaigns), Page (Advertise), pixel, Instagram account. Accept on the host side; some shares ask a second admin to approve.
6. ★ Assign those assets to the system user.
7. ★ Generate token → never expires → ads_management, ads_read, business_management, pages_manage_ads, pages_read_engagement, pages_show_list, instagram_basic → paste into the pop-up on the Mac.
8. The session: one test write that nobody sees (a picture into an account's library), per brand.
9. ★ If step 8 is refused on the other businesses' accounts: business verification of the host business (skip if it is the already-verified the company one), then App Review — the session writes it, the owner presses Submit.
10. ★ First go on a drop. After that, approved drops upload by themselves.

## Off-the-shelf tools, checked

| Tool | What it covers | Gap |
|---|---|---|
| Meta's own Ads MCP (free beta since 29 Apr 2026) | no app needed; creates paused campaigns/ad sets/ads | creative = single-image link ad only; no video, no flexible ads, no file upload |
| Meta Ads CLI | uploads images/videos with a system-user key | uses our own app anyway; no flexible ads |
| Pipeboard (hosted $__–199/mo) | MCP over its own app | builds flexible ads the disputed way; up to 25 accounts on the top plan |
| AdManage £__/mo · Kitchn €__/mo · Ads Uploader ~$__–59/mo | bulk uploads through their own app | no naming join to our drops, no plan/approval/ledger |

## Decided 1 Oct 2026 — the company owns the app

the owner: "we'd just start with the company having the ownership since I already have an established
business manager, I just need to build a proper app and get approvals going."

- Site pages for the app form: daemn.co/privacy.html, daemn.co/terms.html, daemn.co/data-deletion.html (daemnapps/prizm-labs PR 12, the owner merges); icon `docs/media/prizm-labs-app-icon-1024.png` in that repo.
- App: "Prizm Labs", use case Create & manage ads with Marketing API, portfolio the company, category Business and pages.
- Key: the existing Conversions API System User in the company gets the Prizm Labs app (full control) + Brand B ad account + brand-b Page; token saved as `daemn-PRIZM_META_TOKEN`.
- Order: test on Brand B (own-business account) → record the review video on paused ads → App Review for ads_management + ads_read (answers on the page) → Brand A and others shared in as partners.

## 1 Oct 2026, 3:30pm — the key works

App published. Key saved as `daemn-PRIZM_META_TOKEN` (Conversions API System User, all seven permissions
granted). Reaches 1. Brand B (<META_AD_ACCOUNT_ID>) and the brand-b Page. **Write test passed:** one image into the
Brand B library (hash 2cb8ff66…) — the #3 block is gone. A validate-only paused campaign was accepted (nothing
created). Brand A still returns "(#200) Ad account owner has NOT grant ads_management" — not shared yet.

## 1 Oct 2026, evening — both brands connected

New system user "Prizm Labs" holds the key (`daemn-PRIZM_META_TOKEN`, 7 permissions). Reaches 1. Brand B and
Brand ASkin, Pages brand-b / Brand A Skincare / Brand A T. Write test + validate-only campaign passed on both —
no App Review needed. Page caps: brand-b 0/1,000; Brand A Skincare 80/1,000; Brand A T 5/250. Left for the owner:
remove the Prizm Labs app from the Conversions API System User (never revoke its tokens); the first go.

## 1 Oct 2026 — what a drop needs to upload
1 drop folder (pictures or videos; the ad-handoff gate now counts .mp4/.mov) · 2 copy.csv with primary/alt text + 2 headlines + 2 descriptions (`headlines` / `descriptions` columns, or the copywriter's HEADLINES/DESCRIPTIONS blocks) · 3 landing page by catalog link id · 4 hand-off folder · 5 the owner's go in approvals.json · 6 `upload.py --go`.
Brand B now uses Brand A's naming (campaign_brand-b_us_<product>_<funnel>_purchase_cbo; adset by avatar+angle) and has `brands/brand-b/web/funnels/funnels.json` (icon, store). Campaign product = the funnel's product, else the ad's own.

## The approval card (1 Oct 2026)
Every finished ad — video, image, carousel, creator — lands in `Shared Assets/meta/<brand>/1-check/<lane>/<ad name>/`
with a card. The approval page (http://localhost:8795, launch config "meta-approve") shows each one as the
standard card: media, words, page, where it goes in Meta, machine checks. **Approve → Meta** (off while a
check is red) sends it in. **Two buttons, no default (7 Oct 2026): Approve → On or Approve → Paused.** On also switches on the campaign and ad set the upload made; a paused one that already existed is flagged on the card. The Meta ids and Meta's own delivery status land on the card and the folder moves to
3-live. **Send back** takes your note. Your click is the go — no approvals list for this road.
Proved 1 Oct: Meta's dry run (validate only, nothing made) accepted a flexible ad and a carousel ad on both
1. Brand B and Brand ASkin.
