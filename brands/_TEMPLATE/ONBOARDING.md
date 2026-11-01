# Brand onboarding — the checklist

Everything the tools need to know about your brand, in the order Claude asks for it.
You don't need to do any of this by hand: open Claude Code in your copy of this repo and say
**activate Prizm Lab** (or **continue onboarding** to pick up where you left off).
Claude asks one question at a time, fetches what it can from your website and reviews,
fills in the files, and ticks each box here.

**23 items · 13 required · about 20–30 minutes.** Keys are only asked for right before the first tool that needs them — see [`.env.example`](../../.env.example).

## Brand basics

- [ ] **Your brand's name** — *required*
  - Why: Every tool files its work under your brand's folder and writes your name in ads.
  - How you give it: answer a question
  - Used by: every tool
- [ ] **Your website** — *required*
  - Why: Claude reads it to fill in most of the rest for you, so you type as little as possible.
  - How you give it: paste a link
  - Used by: onboarding (Claude reads it for the items below)
- [ ] **Your brand story** — *required*
  - Why: Video scripts, emails and stories are told through it.
  - How you give it: Claude drafts it from your website's About page; you confirm or correct it
  - Used by: video-teardown, story-machine, email-production, ad-variations, quality-checks
- [ ] **What you claim, and why it works** — *required*
  - Why: Every ad, page and brief is checked against it; it's the base everything else reads.
  - How you give it: Claude drafts it from your site and reviews; answer a few questions
  - Used by: video-teardown, video-production, copywriter, language-layer, creative-diversity, distinct-six
- [ ] **Your logo, colours and fonts** — *required*
  - Why: Pictures and videos come out on-brand instead of generic.
  - How you give it: drop files (logo — PNG or SVG); Claude reads colours from your product photos; Claude reads fonts from your website
  - Used by: image-production, image-teardown, image-edit, video-production, video-edit, email-production
- [ ] **The one message every ad carries** — *optional*
  - Why: Lets the creative tools check every ad says the same core thing.
  - How you give it: Claude proposes it from your position and reviews; you pick or reword
  - Used by: creative-diversity, distinct-six, meta-upload

## Products

- [ ] **Your best-selling product** — *required*
  - Why: Every brief, script and image is built around a real product with real facts.
  - How you give it: paste the product page link — Claude fetches the facts; drop product photos (or Claude saves them from the page)
  - Used by: video-teardown, video-production, image-production, image-teardown, copywriter, email-production, video-edit
- [ ] **Any other products you want ads for** — *optional*
  - Why: Lets you make ads for more than the best seller.
  - How you give it: paste product page links
  - Used by: same as the best seller
- [ ] **Your main offer** — *required*
  - Why: Every ad sells into one offer; tools use it for the call to action and to check links.
  - How you give it: paste the offer or landing page link; answer a question (price, deal, guarantee)
  - Used by: creative-diversity, meta-upload, email-production, naming
- [ ] **Your landing pages** — *optional*
  - Why: Briefs get matched to a page that actually sells that product.
  - How you give it: paste links
  - Used by: naming (page picker), meta-upload, handoff-standard

## Customers

- [ ] **Who your customer is** — *required*
  - Why: Every ad is written for one specific person, not 'everyone'.
  - How you give it: answer a few questions; Claude drafts the profile from your reviews
  - Used by: video-teardown, image-teardown, language-layer, email-production, research-gatherer, swipe-organic, swipe-paid, naming
- [ ] **Your customer reviews** — *required*
  - Why: The tools write in your customers' real words, with a receipt on every line.
  - How you give it: paste the reviews page link — Claude fetches them; or drop a reviews export (CSV)
  - Used by: language-layer, research-gatherer, copywriter, email-production
- [ ] **Your customers' words (built for you)** — *optional*
  - Why: The language bank every copy tool draws from.
  - How you give it: nothing to do — Claude builds it from your reviews
  - Used by: language-layer, copywriter, email-production, video-teardown
- [ ] **Surveys and support tickets** — *optional*
  - Why: More real customer words, pulled daily.
  - How you give it: answer a question (which survey sheet / which helpdesk)
  - Used by: research-gatherer, language-layer

## Creative

- [ ] **Your competitors** — *required*
  - Why: The swipe tools pull what's already working for them.
  - How you give it: answer a question (names or links/handles); Claude finds their sites and social accounts
  - Used by: swipe-organic, swipe-paid, my-feeds, copywriter, language-layer, video-production
- [ ] **Ads or posts you'd like to copy the structure of** — *required*
  - Why: This is what the teardown tools take apart and rebuild for your brand.
  - How you give it: paste links (TikTok, Instagram, Meta Ad Library, YouTube); or drop files
  - Used by: video-teardown, image-teardown
- [ ] **Your own past ads and content** — *optional*
  - Why: The tools learn what already works for you and avoid repeating what didn't.
  - How you give it: drop files; paste your Meta Ad Library page link; or a Drive folder link
  - Used by: copywriter, image-teardown, video-teardown, video-production
- [ ] **Photo shoots and brand videos** — *optional*
  - Why: Real footage and photos to cut into new ads.
  - How you give it: paste a Drive/Dropbox folder link; or drop files
  - Used by: video-edit, video-production, image-production
- [ ] **Creators you work with** — *optional*
  - Why: Briefs can be written for a specific creator's style and footage.
  - How you give it: paste their handles
  - Used by: editor-onboarding, video-teardown, image-production

## Accounts & keys

- [ ] **Keys for the tools you use** — *required*
  - Why: Each tool uses your own accounts — nothing is shared. Asked only right before a tool first needs one.
  - How you give it: Claude tells you which key, where to get it, and opens .env for you to paste it in
  - Used by: each tool lists its keys in its README
- [ ] **Google Drive (optional)** — *optional*
  - Why: Lets tools save Docs and files into your Drive instead of only on your computer.
  - How you give it: Claude walks you through it when you first want something saved to Drive
  - Used by: video-teardown, image-teardown, image-production, email-production
- [ ] **Your Meta ad account (optional)** — *optional*
  - Why: Only for uploading ads to Meta or reading how they performed.
  - How you give it: answer a question (ad account, page and pixel ids — Claude shows you where to find them)
  - Used by: meta-upload, meta-strategy

## First run

- [ ] **Your first teardown** — *required*
  - Why: Proves everything is set up, and gets you your first brief.
  - How you give it: nothing to do — Claude runs it on one of your swipes and shows you the result
  - Used by: video-teardown (or image-teardown for a picture ad)

---

The machine-readable version of this list is [`onboarding.json`](onboarding.json); progress for your brand is kept in `brands/<your-brand>/onboarding-progress.json`.
