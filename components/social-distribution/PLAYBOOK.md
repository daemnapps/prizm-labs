# Running many accounts: the playbook

The aim is to scale how much proven-format content you make and how widely it
goes out, on accounts that stay up. Accounts that get banned in a sweep take
their reach and their data with them, so everything here is built to last.

## 1. Account portfolio: several real accounts per brand, each with a job

Don't run 50 copies of one account. Run a few accounts per brand, each with its
own angle. Each one finds its own audience, and together they're a built-in
test of which angle wins.

| Account | Angle | Example handle |
|---|---|---|
| Main brand | product, offers, social proof | @brand |
| Education | tips, myths, how-tos in your niche | @brand.tips |
| Results | before/afters, reviews, customer stories | @brand.results |
| Founder / face | a real person from the team, behind the scenes | @name.at.brand |
| Market | one per country or language you sell in | @brand.de |

Rules that keep them standing:
- **Real ownership.** Each account is on a company email you control and a
  phone number your team owns. Keep them in a password manager with 2FA.
- **Visibly yours.** The bio says it's run by the brand (e.g. "by @brand").
  Accounts that hide that they're the brand's, while selling your product, are
  what platform rules and the FTC/EU advertising rules go after.
- **One account, one phone, one proxy, one country.** Never share them, and
  never log the account in anywhere else.
- **Grow at a human pace.** Add accounts one at a time as you have content for
  them, not in batches.
- **Each account posts its own cut.** Re-edit each piece per account (different
  hook, text, crop, sound). The same file on 10 accounts gets flagged as
  duplicate and suppressed.

## 2. Clippers and creators: the scale layer

To go past what your own accounts can carry, scale through people:
- **Clippers** post your clips on their own accounts and get paid per 1,000
  views (Whop-style "content rewards" campaigns, or direct deals).
- **UGC creators and affiliates** post as themselves; TikTok Shop affiliates
  are paid per sale.
- Every one of them labels it as paid (#ad, or the platform's paid
  partnership toggle). Put that in the brief and the contract.
- Give each one their own link or code, so sales trace back to them.

This is how the big clipping programs actually reach millions of views. The
accounts belong to real people, so a ban wave can't wipe them all out at once.

## 3. The content engine

Production per week, per brand:
1. Take the 3–5 formats that are already winning (from teardowns in this repo).
2. Make 5–10 variations of each: new hook, first frame, on-screen text,
   length, sound.
3. Split them across accounts by angle (section 1) and send the clipper pack
   (section 2).
4. Fill one plan CSV for the week and queue it:
   `python3 geelark.py schedule week.csv`.

A sane posting cadence is 1–3 posts per account per day, spread across the day.

## 4. The learning loop: what makes it a machine

Every Monday:
1. **Pull results** per post: views, watch time / retention, shares, saves,
   profile clicks, link clicks, sales from that account's link or code.
2. **Tag each post** by format, hook type and angle, so you compare like with
   like.
3. **Promote winners.** Anything in the top ~10% gets 5 more variations next
   week, and goes to the paid team as a Spark Ad / partnership ad candidate.
4. **Cut losers.** Any format that's bottom-half three weeks running gets
   dropped.
5. **Watch account health.** Sudden view drops to under 200 on every post means
   the account is being held back. Pause it and check what changed (proxy,
   duplicate content, a strike) before posting more.

## 5. What not to build

- Accounts created in bulk by a script, or bought accounts.
- Tricks to get past phone/email checks, or anything meant to hide that
  accounts are linked.
- Fake likes, follows or comments between your own accounts.

These are what platform sweeps look for, and they put the real accounts at risk
too.
