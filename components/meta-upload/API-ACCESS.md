# The Meta API — what is set up, and the one thing still blocking

> **1 Oct 2026:** the Keychain no longer holds `daemn-META_ADS_TOKEN`, and only Brand B was ever assigned
> to the system user. The way back, and the uploader that runs once it is back: `GO-LIVE.md`.

Set up 2026-09-11 so RUN-01 could be built as the owner actually wants it: one ad
unit per concept with its variations inside. The bulk sheet cannot express
that; the API can.

## Working

| piece | value |
|---|---|
| token | Keychain `daemn-META_ADS_TOKEN`, system user, **never expires** |
| identity | Conversions API System User (Meta caps unverified-second system users, so this one was extended rather than a new one created) |
| scopes | ads_management, ads_read, business_management — all granted |
| ad account | `1. Brand B` <META_AD_ACCOUNT_ID>, Manage campaigns only (no billing, no permissions) |
| page | brand-b <META_PAGE_ID>, Ads only |
| pixel | Brand B' Main Pixel <META_PIXEL_ID> |
| app | <META_APP_NAME> <META_APP_ID>, system user is app admin |
| client | `meta.py` — reads the token at call time, never stores or prints it |

**Reads work.** The client returns the account, the campaign, all six ad sets
with their pixel and Purchase event, and the ad list.

## Blocked

**Writes fail: `(#3) Application does not have the capability to make this
API call.`**

The cause is on the app, not the token. In the old app's Marketing API
settings:

> **Marketing API Access Tier: Limited**
> Requirements for higher access level:
> - App must be published
> - Marketing API Access Tier must be approved in App Review

The permissions themselves read "Ready for testing" — development-mode only.
The token is valid and correctly scoped; the app is not allowed to write ads.

Note the business portfolio IS verified (the company, green), so
verification is not the gap. The gap is app publication plus App Review of the
Marketing API Access Tier.

## The options, as they actually stand

1. **App Review.** Publish the app, submit the Marketing API Access Tier for
   review. Days of latency and a real submission (use case, screencast). The
   permanent answer: flexible ads, URL image uploads, ad-level spend read back
   on `ad_name`.
2. **The Ads MCP on `1.2 Brand B 2`.** Enabled today, writes today — but a
   different ad account with no history, and its creative tool has no flexible
   format either (single image, or static carousel).
3. **Keep hand-building in Ads Manager.** Works now, no waiting, but the
   variations go in one ad at a time and it is not repeatable.

Nothing here is a dead end; they differ in what they cost and when.
