# Ship a web app (idea → live product with logins and payments)

**Higgsfield first:** a site with no AI inside → website-builder `type: website`; a product that generates images/video for its users → `type: app` (Sign in with Higgsfield, runs on their credits). Use the stack below when it needs its own logins, database and Stripe.

Ask once: what it does, who pays, how much.

| Stage | Tools | Output on the page |
|---|---|---|
| 1. Spec | coreyhaines31 `offers`, `pricing`; anthropic knowledge-work `product-management` skills | One-page spec + screens list → **he picks** |
| 2. Look | `premium-landing-page` stage 3 (frontend-design, ui-ux-pro-max) | Screen mockups → **he picks** |
| 3. Build | Next.js + Tailwind + shadcn (shadcn MCP); Context7 for current docs | Running locally, screenshots |
| 4. Data + logins | Supabase plugin (database, auth, storage) | Working sign-up |
| 5. Payments | Stripe plugin (products, prices, checkout) — test mode first | Test purchase receipt |
| 6. Email | Resend plugin + React Email | Welcome + receipt emails |
| 7. Test | Playwright + Chrome DevTools plugins: click every flow, phone + desktop | Screenshot strip |
| 8. Live | Vercel plugin, his domain → **he says go** | Live link |
| 9. Measure | PostHog plugin (funnels, replays) | Funnel view |

Logins only he can do (once each): Supabase, Stripe (business verification), Vercel, Resend (domain), PostHog.
