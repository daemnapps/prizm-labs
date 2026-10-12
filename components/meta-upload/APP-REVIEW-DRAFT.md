# The Meta app — unblocking Marketing API writes

**Nothing here has been submitted.** the owner reads it first (his instruction,
2026-09-11: "let's do the app review properly let me see it before submission").

## What is actually blocking

Reads work on every edge. Every write returns:

    (#3) Application does not have the capability to make this API call.

The token is not the problem — it is a valid, never-expiring system user token
with `ads_management`, `ads_read`, `business_management` all granted, and the
business portfolio is already **Verified**.

Two separate things are often confused here, and only the first is certainly
required:

| | what it is | needed for |
|---|---|---|
| **App published** | the app is currently **Unpublished** (development mode) | writing at all, most likely |
| **Marketing API Access Tier** | currently **Limited access** | higher rate limits and an unlimited number of ad accounts |

Meta's own upgrade dialog describes the tier as *"a higher rate limit and an
unlimited number of ad accounts"* — a scale control, not a write switch. The
Publish page lists the app being published as requirement one.

**So the cheap step comes first, and it may be the whole answer.**

## Step 1 — publish the app (minutes, no review)

The Publish page flags exactly one gap: a **Privacy policy URL**.

Proposed value: `https://brand-b.example/policies/privacy-policy` — live, returns
200, owned by the same business that owns the app and the ad account.

Then press Publish. Nothing about the app changes for anyone else: the app has
no public users, no login flow, no user data. Publishing is reversible.

Then re-run the write test. If `adimages` accepts a picture, we are done and
step 2 never happens.

## Step 2 — App Review, only if step 1 is not enough

Submitted against the **Create & manage ads with Marketing API** use case,
requesting the Marketing API Access Tier upgrade.

### How the app uses the permissions

> the app is an internal tool. It is used by one business, the company,
> to manage advertising on ad accounts that business owns. It has no public
> users, no consumer-facing surface, and no login flow. It does not request or
> store data belonging to anyone outside the business.
>
> The tool builds image advertisements for the company's own brands and places
> them into the company's own ad accounts. A production run produces a set of
> ad concepts; each concept has several image variations that belong in a
> single ad unit so Meta can optimise between them. The tool creates the
> images, the ad creative and the ads, always paused, for a human to review and
> switch on. It reads ad-level performance back so the team can tell which
> creative earned its spend.
>
> `ads_management` creates and updates campaigns, ad sets, ad creatives and
> ads on the business's own ad accounts.
> `ads_read` reads ad-level delivery and spend back for reporting.
> `business_management` resolves the business's own pages, pixels and ad
> accounts so the tool addresses the right ones.
>
> Access is held by a system user belonging to the business, scoped to a single
> ad account with Manage campaigns permission only. It cannot change billing,
> permissions, or any other account.

### Screencast — what it needs to show

1. The tool reading the ad account and listing its campaigns.
2. Creating an ad with several image variations in one ad unit, paused.
3. That ad appearing in Ads Manager, paused, with its creative.
4. Reading spend back at the ad level.

Recording it is blocked until writes work, which is the circularity: it can be
filmed on `1.2 Brand B 2`, which is a the company account and already
MCP-enabled, then submitted for the tier on the main account.

### Notes for the submission

- The business portfolio is already verified. Say so.
- The app is internal-only. Meta reviews these faster when that is explicit and
  obviously true — no login, no public surface, no third-party data.
- Annual re-review is required to keep the tier.

## A third door worth knowing about

The app also carries a **"Create & manage ads with ads MCP server"**
use case. `1. Brand B` is not yet enabled for the Ads MCP ("gradually being
rolled out"), but `1.2 Brand B 2` is. If Meta enables the main account, the MCP
writes without any of this — though its creative tool still has no flexible
format, only single image or static carousel.
